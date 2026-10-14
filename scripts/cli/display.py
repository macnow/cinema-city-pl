"""
CLI Display utilities for formatting output
"""
from typing import List, Dict
from tabulate import tabulate
import click


def display_cinemas(cinemas: List[Dict]):
    """Wyświetl listę kin w formacie tabeli"""
    if not cinemas:
        click.echo("Brak dostępnych kin")
        return

    headers = ["ID", "Nazwa", "Adres"]
    rows = []
    for c in cinemas:
        # Formatuj adres
        addr_parts = []
        if c.get('address'):
            addr_parts.append(c['address'])
        if c.get('city'):
            addr_parts.append(c['city'])
        address = ', '.join(addr_parts) if addr_parts else 'N/A'

        rows.append([c.get('id'), c.get('name'), address])

    click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
    click.echo(f"\nŁącznie: {len(cinemas)} kin")


def display_movies(movies: List[Dict], with_filmweb: bool = False):
    """Wyświetl listę filmów w formacie tabeli"""
    if not movies:
        click.echo("Brak filmów w repertuarze")
        return

    if with_filmweb:
        headers = ["ID", "Tytuł", "Czas trwania", "Rok", "Ocena Filmweb"]
        rows = []
        for m in movies:
            # Formatuj ocenę Filmweb
            rating = m.get('filmweb_rating')
            rating_count = m.get('filmweb_rating_count')

            if rating:
                rating_str = f"{rating:.1f}/10"
                if rating_count:
                    rating_str += f" ({rating_count:,})"
            else:
                rating_str = "---"

            rows.append([
                m.get('id'),
                m.get('title'),
                f"{m.get('duration')} min" if m.get('duration') else 'N/A',
                m.get('year', 'N/A'),
                rating_str
            ])
    else:
        headers = ["ID", "Tytuł", "Czas trwania", "Rok"]
        rows = [
            [
                m.get('id'),
                m.get('title'),
                f"{m.get('duration')} min" if m.get('duration') else 'N/A',
                m.get('year', 'N/A')
            ]
            for m in movies
        ]

    click.echo(tabulate(rows, headers=headers, tablefmt='simple'))


def display_showtimes(showtimes: List[Dict], with_filmweb: bool = False, with_availability: bool = False):
    """Wyświetl listę seansów w formacie tabeli"""
    if not showtimes:
        click.echo("Brak dostępnych seansów")
        return

    # Buduj nagłówki dynamicznie
    headers = ["Godzina", "Film"]

    if with_filmweb:
        headers.append("Ocena")
        headers.append("Gatunek")

    if with_availability:
        headers.append("Zapełnienie")

    headers.extend(["Sala", "Typ", "ID"])

    rows = []
    for s in showtimes:
        # Zbierz atrybuty seansu
        attrs = []
        if s.get('imax'):
            attrs.append('IMAX')
        if s.get('3d'):
            attrs.append('3D')
        if s.get('4dx'):
            attrs.append('4DX')
        if s.get('screenx'):
            attrs.append('ScreenX')
        if s.get('vip'):
            attrs.append('VIP')
        if s.get('subtitles'):
            attrs.append('NAPISY')
        if s.get('dubbing'):
            attrs.append('DUBBING')
        if s.get('sold_out'):
            attrs.append('WYPRZEDANE')

        attr_str = ', '.join(attrs) if attrs else '2D'

        movie_name = s.get('movie_name', s.get('movie_id'))[:35]  # Skróć tytuł

        row = [
            s.get('time'),
            movie_name,
        ]

        # Dodaj ocenę Filmweb jeśli włączona
        if with_filmweb:
            rating = s.get('filmweb_rating')

            if rating:
                rating_str = f"{rating:.1f}/10"
            else:
                rating_str = "---"

            row.append(rating_str)

            # Dodaj gatunki
            genres = s.get('movie_genres', [])
            if genres:
                # Przetłumacz nazwy gatunków na polski
                genre_translations = {
                    'adventure': 'Przygodowy',
                    'sci-fi': 'Sci-Fi',
                    'action': 'Akcja',
                    'drama': 'Dramat',
                    'comedy': 'Komedia',
                    'thriller': 'Thriller',
                    'horror': 'Horror',
                    'animation': 'Animacja',
                    'fantasy': 'Fantasy',
                    'romance': 'Romans',
                    'crime': 'Kryminalny',
                    'mystery': 'Tajemnica',
                    'war': 'Wojenny',
                    'documentary': 'Dokument',
                    'biography': 'Biografia',
                    'musical': 'Musical',
                    'western': 'Western',
                    'family': 'Rodzinny'
                }
                translated = [genre_translations.get(g, g.title()) for g in genres[:2]]  # Maksymalnie 2 gatunki
                genre_str = ', '.join(translated)
            else:
                genre_str = "---"

            row.append(genre_str)

        # Dodaj dostępność miejsc jeśli włączona
        if with_availability:
            availability_pct = s.get('availability_pct')

            if availability_pct is not None:
                # Formatuj z kolorem/wskaźnikiem
                if availability_pct < 30:
                    # Mało zajętych - świetnie! 🟢
                    avail_str = f"🟢 {availability_pct:.0f}%"
                elif availability_pct < 60:
                    # Średnio - jeszcze OK 🟡
                    avail_str = f"🟡 {availability_pct:.0f}%"
                elif availability_pct < 90:
                    # Dużo zajętych - zostało mało 🟠
                    avail_str = f"🟠 {availability_pct:.0f}%"
                else:
                    # Prawie pełne 🔴
                    avail_str = f"🔴 {availability_pct:.0f}%"
            else:
                avail_str = "---"

            row.append(avail_str)

        row.extend([
            s.get('screen'),
            attr_str,
            s.get('id', 'N/A')  # Pełne ID
        ])

        rows.append(row)

    click.echo(tabulate(rows, headers=headers, tablefmt='simple'))
    click.echo(f"\nŁącznie seansów: {len(showtimes)}")

    # Pokaż linki do zwiastunów jeśli dostępne
    if with_filmweb:
        trailers = {}
        for s in showtimes:
            movie_name = s.get('movie_name', '')
            trailer = s.get('movie_trailer')
            if trailer and movie_name not in trailers:
                trailers[movie_name] = trailer

        if trailers:
            click.echo("\n🎬 Zwiastuny:")
            for movie_name, trailer_url in list(trailers.items())[:5]:  # Max 5
                click.echo(f"  • {movie_name[:40]}: {trailer_url}")
