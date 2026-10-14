#!/usr/bin/env python3
"""
Szybkie wyszukiwanie filmów i najlepszych miejsc
"""

import click
from cinemacity import CinemaCityClient
from datetime import datetime, timedelta


def quick_movie_search(movie_query: str, cinema_id: str = "1097", num_seats: int = 2):
    """
    Kompleksowe wyszukiwanie: film → seanse → najlepsze miejsca

    Args:
        movie_query: Nazwa filmu do wyszukania
        cinema_id: ID kina (domyślnie 1097 = Wrocław Magnolia Park)
        num_seats: Liczba miejsc obok siebie
    """
    client = CinemaCityClient()

    print(f"\n{'='*70}")
    print(f"🎬 Wyszukiwanie: {movie_query}")
    print(f"📍 Kino: {cinema_id}")
    print(f"🪑 Liczba miejsc: {num_seats}")
    print(f"{'='*70}\n")

    # Krok 1: Wyszukaj film
    print("1️⃣ Wyszukuję film...")
    search_results = client.search_movie(movie_query)

    if not search_results:
        print(f"❌ Nie znaleziono filmu: {movie_query}")
        return

    # Pokaż wyniki wyszukiwania
    print(f"\n✓ Znaleziono {len(search_results)} filmów:")
    for i, film in enumerate(search_results[:5], 1):
        name = film.get('fn', film.get('name', 'Nieznany'))
        film_id = film.get('id', 'N/A')
        print(f"  {i}. {name} (ID: {film_id})")

    # Użyj pierwszego wyniku
    first_film = search_results[0]
    film_id = first_film.get('id')
    film_name = first_film.get('fn', first_film.get('name', 'Nieznany'))

    print(f"\n📽️  Wybrany film: {film_name} (ID: {film_id})")

    # Krok 2: Pobierz seanse
    print(f"\n2️⃣ Pobieram seanse dla {film_name}...")

    # Sprawdź dzisiaj i najbliższe dni
    showtimes_all = []
    for day_offset in range(7):  # Sprawdź 7 dni
        date = datetime.now() + timedelta(days=day_offset)
        date_str = date.strftime('%Y-%m-%d')

        showtimes = client.get_showtimes(cinema_id, film_id, date_str)
        if showtimes:
            for st in showtimes:
                st['date'] = date_str
            showtimes_all.extend(showtimes)

    if not showtimes_all:
        print(f"❌ Brak seansów dla {film_name} w najbliższych 7 dniach")
        return

    # Pokaż seanse
    print(f"\n✓ Znaleziono {len(showtimes_all)} seansów:\n")
    for i, st in enumerate(showtimes_all[:10], 1):
        date = st.get('date', 'N/A')
        time = st.get('time', 'N/A')
        screen = st.get('screen', 'N/A')
        attrs = []

        if st.get('imax'):
            attrs.append('IMAX')
        if st.get('3d'):
            attrs.append('3D')
        if st.get('4dx'):
            attrs.append('4DX')
        if st.get('sold_out'):
            attrs.append('❌ WYPRZEDANE')

        attr_str = ', '.join(attrs) if attrs else '2D'
        presentation_id = st.get('id')

        print(f"  {i:2d}. {date} {time} | {screen:20} | {attr_str:20} | ID: {presentation_id}")

    # Krok 3: Dla każdego seansu, znajdź najlepsze miejsca
    print(f"\n3️⃣ Analizuję dostępność miejsc...\n")

    from find_best_seats import find_center_seats

    results_summary = []

    for st in showtimes_all[:5]:  # Sprawdź pierwsze 5 seansów
        presentation_id = st.get('id')
        date = st.get('date', 'N/A')
        time = st.get('time', 'N/A')
        screen = st.get('screen', 'N/A')

        print(f"{'─'*70}")
        print(f"📅 {date} {time} | {screen}")

        try:
            best_seats = find_center_seats(presentation_id, num_seats, max_results=3)

            if best_seats:
                top_seat = best_seats[0]
                seats_str = ', '.join(top_seat['seats'])

                results_summary.append({
                    'date': date,
                    'time': time,
                    'screen': screen,
                    'presentation_id': presentation_id,
                    'row': top_seat['row'],
                    'seats': seats_str,
                    'quality': '⭐⭐⭐' if top_seat['distance'] < 100 else '⭐⭐'
                })

                print(f"  ✓ Najlepsze miejsca: Rząd {top_seat['row']}, miejsca {seats_str}")
                print(f"  📊 Odległość od środka: {top_seat['distance']:.1f}")
            else:
                print(f"  ❌ Brak dostępnych miejsc")

        except Exception as e:
            print(f"  ⚠️  Błąd podczas analizy: {str(e)}")

        print()

    # Podsumowanie
    if results_summary:
        print(f"\n{'='*70}")
        print(f"📋 PODSUMOWANIE - Najlepsze opcje:")
        print(f"{'='*70}\n")

        for i, res in enumerate(results_summary, 1):
            print(f"{i}. {res['date']} {res['time']} | {res['screen']}")
            print(f"   🪑 Rząd {res['row']}, miejsca {res['seats']} {res['quality']}")
            print(f"   🔗 ID: {res['presentation_id']}")
            print()

        print(f"💡 Wizualizacja sali:")
        if results_summary:
            best = results_summary[0]
            print(f"   .venv/bin/python3 main.py visualize --presentation-id {best['presentation_id']}")


@click.command()
@click.argument('movie_query')
@click.option('--cinema-id', default='1097', help='ID kina (domyślnie 1097 = Wrocław)')
@click.option('--seats', default=2, help='Liczba miejsc obok siebie')
def main(movie_query, cinema_id, seats):
    """
    Szybkie wyszukiwanie filmów i miejsc

    Przykład:
        python3 quick_search.py "Avatar"
        python3 quick_search.py "Avatar" --cinema-id 1090 --seats 3
    """
    try:
        quick_movie_search(movie_query, cinema_id, seats)
    except Exception as e:
        print(f"\n❌ Błąd: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
