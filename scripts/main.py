#!/usr/bin/env python3
"""
Cinema City PL - CLI tool for browsing and booking tickets
"""
import click
from dotenv import load_dotenv
from cinemacity import CinemaCityClient
from cinemacity.attributes_cache import get_attributes, get_attributes_by_group
from cli import display_cinemas, display_movies, display_showtimes

load_dotenv()


@click.group()
@click.pass_context
def cli(ctx):
    """Cinema City PL - narzędzie do przeglądania i rezerwacji biletów"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = CinemaCityClient()


@cli.command()
@click.pass_context
def cinemas(ctx):
    """Wyświetl listę dostępnych kin"""
    client = ctx.obj['client']
    cinemas = client.get_cinemas()
    display_cinemas(cinemas)


@cli.command()
@click.option('--cinema-id', required=True, help='ID kina')
@click.option('--days', default=30, help='Ile dni do przodu (domyślnie 30)')
@click.pass_context
def dates(ctx, cinema_id, days):
    """Wyświetl dostępne daty z seansami"""
    client = ctx.obj['client']
    available_dates = client.get_available_dates(cinema_id, days)
    if available_dates:
        click.echo(f"Dostępne daty ({len(available_dates)}):")
        for date in available_dates:
            click.echo(f"  • {date}")
    else:
        click.echo("Brak dostępnych dat")


@cli.command()
@click.option('--cinema-id', required=True, help='ID kina')
@click.option('--date', default=None, help='Data (YYYY-MM-DD), domyślnie dziś')
@click.option('--with-filmweb', is_flag=True, help='Dodaj oceny z Filmweb')
@click.pass_context
def movies(ctx, cinema_id, date, with_filmweb):
    """Wyświetl listę filmów w repertuarze"""
    client = ctx.obj['client']
    movies = client.get_movies(cinema_id, date)

    # Jeśli --with-filmweb, pobierz oceny z Filmweb
    if with_filmweb:
        from filmweb import FilmwebClient
        filmweb = FilmwebClient()

        click.echo("Pobieranie ocen z Filmweb...")
        for movie in movies:
            title = movie.get('title', '')
            year = movie.get('year')

            if title and year:
                try:
                    # Konwertuj rok na int (Cinema City zwraca string)
                    year_int = int(year) if isinstance(year, str) else year

                    # Spróbuj znaleźć film po tytule + rok
                    results = filmweb.search_by_title_year(title, year_int, page_size=10)

                    if results:
                        # Znajdź najlepsze dopasowanie (dokładny tytuł lub pierwszy wynik)
                        best_match = None
                        for result in results:
                            if result.get('title', '').lower() == title.lower():
                                best_match = result
                                break

                        # Jeśli brak dokładnego dopasowania, weź pierwszy wynik
                        if not best_match and results:
                            best_match = results[0]

                        if best_match:
                            movie['filmweb_rating'] = best_match.get('rating')
                            movie['filmweb_rating_count'] = best_match.get('rating_count')
                            movie['filmweb_title'] = best_match.get('title')  # Dla debugowania

                except Exception as e:
                    # Jeśli błąd, po prostu pomiń
                    pass

    display_movies(movies, with_filmweb=with_filmweb)


@cli.command()
@click.argument('film_code')
@click.pass_context
def film(ctx, film_code):
    """Wyświetl szczegółowe informacje o filmie po kodzie"""
    client = ctx.obj['client']
    try:
        film = client.get_film_details(film_code)
        click.echo(click.style(f'\n=== {film.get("name", "Film")} ===\n', fg='cyan', bold=True))
        click.echo(f"Kod: {film.get('id', 'N/A')}")
        click.echo(f"Tytuł: {film.get('name', 'N/A')}")
        click.echo(f"Rok: {film.get('releaseYear', 'N/A')}")
        click.echo(f"Długość: {film.get('length', 'N/A')} min")
        click.echo(f"Gatunek: {', '.join(film.get('genres', []))}")
        click.echo(f"Reżyser: {film.get('director', 'N/A')}")
        click.echo(f"Obsada: {', '.join(film.get('cast', []))}")

        if film.get('synopsis'):
            click.echo(f"\nOpis:\n{film.get('synopsis')}")

        if film.get('posterLink'):
            click.echo(f"\nPlakat: {film.get('posterLink')}")

        if film.get('trailerLink'):
            click.echo(f"Zwiastun: {film.get('trailerLink')}")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.argument('query')
@click.pass_context
def search(ctx, query):
    """Wyszukaj film po nazwie"""
    client = ctx.obj['client']
    results = client.search_movie(query)
    if results:
        click.echo(f"Znaleziono {len(results)} filmów:")
        for film in results:
            name = film.get('fn', film.get('name', 'Nieznany'))
            film_id = film.get('id', 'N/A')
            release = film.get('reldatef', 'brak daty')
            click.echo(f"  • {name} ({film_id}) - {release}")
    else:
        click.echo("Nie znaleziono filmów")


@cli.command()
@click.option('--feed', default='now-playing', help='Nazwa feeda (now-playing, coming-soon, oscar-nominees, etc.)')
@click.pass_context
def featured(ctx, feed):
    """Wyświetl filmy z wybranego feeda"""
    client = ctx.obj['client']
    movies = client.get_feed(feed)
    if movies:
        click.echo(f"Feed '{feed}' ({len(movies)} filmów):\n")
        for movie in movies[:20]:  # Pierwszych 20
            title = movie.get('title', 'Nieznany')
            movie_id = movie.get('id', '')
            date = movie.get('date_started', '')[:10] if movie.get('date_started') else 'N/A'
            click.echo(f"  • {title} ({movie_id}) - od {date}")
    else:
        click.echo(f"Brak filmów w feedzie '{feed}'")


@cli.command()
@click.option('--group', default=None, help='Nazwa grupy (screening-type, special-type, language, etc.)')
def attributes(group):
    """Wyświetl dostępne atrybuty seansów"""
    if group:
        # Pokaż atrybuty z konkretnej grupy
        attrs = get_attributes_by_group(group)
        if attrs:
            click.echo(f"Atrybuty w grupie '{group}' ({len(attrs)}):\n")
            for attr_id in sorted(attrs):
                click.echo(f"  • {attr_id}")
        else:
            click.echo(f"Grupa '{group}' nie istnieje")
    else:
        # Pokaż wszystkie grupy
        all_attrs = get_attributes()
        click.echo(f"Dostępne grupy atrybutów ({len(all_attrs)}):\n")
        for attr_group in all_attrs:
            group_name = attr_group['group-name']
            items_count = len(attr_group['items'])
            click.echo(f"  • {group_name}: {items_count} atrybutów")
        click.echo("\nUżyj: python3 main.py attributes --group <nazwa> aby zobaczyć szczegóły")


@cli.command()
@click.option('--cinema-id', required=True, help='ID kina')
@click.option('--movie-id', default=None, help='ID filmu (opcjonalne)')
@click.option('--date', default=None, help='Data (YYYY-MM-DD), domyślnie dziś')
@click.option('--time-from', default=None, help='Godzina od (HH:MM), np. 18:00')
@click.option('--time-to', default=None, help='Godzina do (HH:MM), np. 23:00')
@click.option('--with-filmweb', is_flag=True, help='Dodaj oceny z Filmweb')
@click.option('--with-availability', is_flag=True, help='Sprawdź dostępność dobrych miejsc (% zapełnienia górnych rzędów)')
@click.pass_context
def showtimes(ctx, cinema_id, movie_id, date, time_from, time_to, with_filmweb, with_availability):
    """Wyświetl seanse dla danego filmu lub wszystkie seanse"""
    client = ctx.obj['client']
    showtimes = client.get_showtimes(cinema_id, movie_id, date)

    # Filtruj po zakresie godzinowym
    if time_from or time_to:
        filtered = []
        for st in showtimes:
            show_time = st.get('time', '')

            # Sprawdź czy w zakresie
            if time_from and show_time < time_from:
                continue
            if time_to and show_time > time_to:
                continue

            filtered.append(st)

        showtimes = filtered

        if time_from and time_to:
            click.echo(f"Filtrowanie: {time_from} - {time_to}")
        elif time_from:
            click.echo(f"Filtrowanie: od {time_from}")
        elif time_to:
            click.echo(f"Filtrowanie: do {time_to}")

    # Dodaj oceny z Filmweb + szczegóły z Cinema City (gatunki, zwiastun)
    if with_filmweb and showtimes:
        from filmweb import FilmwebClient
        filmweb = FilmwebClient()

        click.echo("Pobieranie danych filmów (Filmweb + Cinema City)...")

        # Cache dla obu źródeł - klucz: movie_id
        movies_cache = {}

        for st in showtimes:
            movie_name = st.get('movie_name', '')
            movie_id = st.get('movie_id', '')

            # Użyj movie_id jako klucza cache
            if movie_id and movie_id not in movies_cache:
                movie_data = {}

                # 1. Pobierz szczegóły z Cinema City (gatunki, zwiastun)
                try:
                    cc_details = client.get_film_details(movie_id)
                    film_info = cc_details.get('filmDetails', {})

                    movie_data['genres'] = film_info.get('categoriesAttributes', [])
                    movie_data['trailer'] = film_info.get('videoLink')
                    movie_data['year'] = film_info.get('releaseYear')
                except Exception as e:
                    pass
                # 2. Pobierz oceny z Filmweb
                year = movie_data.get('year')
                if year:
                    year = int(year) if isinstance(year, str) else year

                # Usuń potencjalny rok z tytułu
                import re
                clean_title = re.sub(r'\s*\(\d{4}\)\s*$', '', movie_name).strip()

                try:
                    if year:
                        results = filmweb.search_by_title_year(clean_title, year, page_size=10)
                    else:
                        # Bez roku - spróbuj samo wyszukiwanie
                        search_results = filmweb.search(clean_title, page_size=3)
                        results = []
                        for sr in search_results:
                            details = filmweb.get_film_details(sr['id'])
                            if details:
                                results.append(details)

                    if results:
                        # Znajdź najlepsze dopasowanie
                        best_match = None
                        for result in results:
                            if result.get('title', '').lower() == clean_title.lower():
                                best_match = result
                                break

                        if not best_match and results:
                            best_match = results[0]

                        if best_match:
                            movie_data['rating'] = best_match.get('rating')
                            movie_data['rating_count'] = best_match.get('rating_count')
                except Exception as e:
                    pass

                # Zapisz do cache
                movies_cache[movie_id] = movie_data

        # Przypisz dane do seansów z cache
        for st in showtimes:
            movie_id = st.get('movie_id', '')
            if movie_id in movies_cache:
                cached = movies_cache[movie_id]
                st['filmweb_rating'] = cached.get('rating')
                st['filmweb_rating_count'] = cached.get('rating_count')
                st['movie_genres'] = cached.get('genres', [])
                st['movie_trailer'] = cached.get('trailer')

    # Sprawdź dostępność miejsc
    if with_availability and showtimes:
        click.echo("Sprawdzanie dostępności miejsc...")

        for st in showtimes:
            presentation_id = st.get('id')

            try:
                # Pobierz szczegóły prezentacji
                presentation = client.get_presentation_details(presentation_id)
                p = presentation.get('presentation', {})

                venue_id = str(p.get('venueId'))
                seatplan_id = str(p.get('seatplanId'))

                # Pobierz plan sali i status miejsc
                seatplan = client.get_seat_plan(venue_id, seatplan_id)
                seats_status = client.get_seats_status(presentation_id)

                # Przeanalizuj miejsca
                sections = seatplan.get('S', {})
                status_map = seats_status.get('seats', {})

                # Znajdź min/max Y (wysokość sali)
                all_seats = []
                for section_id, section in sections.items():
                    groups = section.get('G', {})
                    for group_id, group in groups.items():
                        rows = group.get('R', {})
                        for row_id, row in rows.items():
                            row_name = row.get('n', row_id)
                            seats = row.get('S', {})

                            for seat_id, seat in seats.items():
                                coords = seat.get('rd', {})
                                cx = coords.get('cx', 0)
                                cy = coords.get('cy', 0)
                                seat_name = seat.get('n', seat_id)

                                status_key = f"{section_id}_{seat_id}_{row_name}"
                                is_available = status_key in status_map

                                all_seats.append({
                                    'x': cx,
                                    'y': cy,
                                    'available': is_available
                                })

                if all_seats:
                    # Znajdź wymiary sali
                    min_y = min(s['y'] for s in all_seats)
                    max_y = max(s['y'] for s in all_seats)
                    mid_y = (min_y + max_y) / 2

                    min_x = min(s['x'] for s in all_seats)
                    max_x = max(s['x'] for s in all_seats)
                    width = max_x - min_x

                    # Granice środkowej części (50% szerokości)
                    # Środek +/- 25% = 50% środkowej części
                    center_x = (min_x + max_x) / 2
                    quarter_width = width / 4
                    center_left = center_x - quarter_width
                    center_right = center_x + quarter_width

                    # Tylko miejsca w górnej połowie (>50% wysokości) I środkowej części (50% szerokości)
                    good_seats = [
                        s for s in all_seats
                        if s['y'] >= mid_y  # Górna połowa
                        and center_left <= s['x'] <= center_right  # Środek (50% szerokości)
                    ]

                    if good_seats:
                        total_good = len(good_seats)
                        taken_good = sum(1 for s in good_seats if not s['available'])
                        occupied_pct = (taken_good / total_good * 100) if total_good > 0 else 0

                        st['availability_pct'] = occupied_pct
                        st['good_seats_total'] = total_good
                        st['good_seats_taken'] = taken_good

            except Exception as e:
                # Jeśli błąd, po prostu pomiń
                pass

    display_showtimes(showtimes, with_filmweb=with_filmweb, with_availability=with_availability)


@cli.command()
@click.option('--email', required=True, help='Email Unlimited')
@click.option('--password', required=True, help='Hasło Unlimited')
@click.option('--recaptcha-token', default=None, help='Token reCaptcha v3 (opcjonalny, może być wymagany)')
@click.pass_context
def login(ctx, email, password, recaptcha_token):
    """Zaloguj się do Cinema City Unlimited"""
    client = ctx.obj['client']
    try:
        auth_data = client.login(email, password, recaptcha_token)
        click.echo(click.style('✓ Zalogowano pomyślnie', fg='green'))
        click.echo(f"\nAccess Token: {auth_data.get('access_token', 'N/A')[:50]}...")
        click.echo(f"Token Type: {auth_data.get('token_type', 'N/A')}")
        click.echo(f"Expires In: {auth_data.get('expires_in', 'N/A')} sekund")
        if auth_data.get('refresh_token'):
            click.echo(f"Refresh Token: {auth_data.get('refresh_token')[:50]}...")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd logowania: {str(e)}', fg='red'))


@cli.command()
@click.pass_context
def profile(ctx):
    """Wyświetl profil zalogowanego użytkownika"""
    client = ctx.obj['client']
    try:
        user = client.get_current_user()
        click.echo(click.style('\n=== Profil użytkownika ===\n', fg='cyan', bold=True))
        click.echo(f"ID: {user.get('id', 'N/A')}")
        click.echo(f"Email: {user.get('email', 'N/A')}")
        click.echo(f"Imię: {user.get('firstName', 'N/A')}")
        click.echo(f"Nazwisko: {user.get('lastName', 'N/A')}")
        click.echo(f"Telefon: {user.get('phoneNumber', 'N/A')}")
        click.echo(f"Data urodzenia: {user.get('birthDate', 'N/A')}")
        click.echo(f"Ulubione kino ID: {user.get('favouriteCinemaId', 'N/A')}")

        # Zgody marketingowe
        consents = user.get('consents', {})
        click.echo(f"\nZgody:")
        click.echo(f"  Marketing: {'✓' if consents.get('marketingConsent') else '✗'}")
        click.echo(f"  Premium Marketing: {'✓' if consents.get('premiumMarketingConsent') else '✗'}")

        # Unlimited membership
        memberships = user.get('memberships', {})
        unlimited = memberships.get('unlimited', {})
        if unlimited:
            click.echo(f"\nUnlimited:")
            click.echo(f"  Numer karty: {unlimited.get('cardNumber', 'N/A')}")
            click.echo(f"  Status: {unlimited.get('status', 'N/A')}")
            click.echo(f"  Data ważności: {unlimited.get('expirationDate', 'N/A')}")
            click.echo(f"  Typ: {unlimited.get('signupType', 'N/A')} ({unlimited.get('signupDuration', 'N/A')})")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.option('--cinema-id', required=True, help='ID kina do ustawienia jako ulubione')
@click.option('--recaptcha-token', default=None, help='Token reCaptcha v3 (opcjonalny)')
@click.pass_context
def set_favourite_cinema(ctx, cinema_id, recaptcha_token):
    """Ustaw ulubione kino"""
    client = ctx.obj['client']
    try:
        client.update_favourite_cinema(cinema_id, recaptcha_token)
        click.echo(click.style(f'✓ Ustawiono kino {cinema_id} jako ulubione', fg='green'))
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.option('--marketing/--no-marketing', default=None, help='Zgoda na marketing')
@click.option('--premium/--no-premium', default=None, help='Zgoda na premium marketing')
@click.option('--recaptcha-token', default=None, help='Token reCaptcha v3 (opcjonalny)')
@click.pass_context
def update_consents(ctx, marketing, premium, recaptcha_token):
    """Zaktualizuj zgody marketingowe"""
    client = ctx.obj['client']
    try:
        client.update_consents(marketing, premium, recaptcha_token)
        click.echo(click.style('✓ Zaktualizowano zgody marketingowe', fg='green'))
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.option('--time', default='FUTURE', type=click.Choice(['FUTURE', 'PAST']), help='Filtruj rezerwacje')
@click.option('--booking-id', default=None, help='Pokaż szczegóły konkretnej rezerwacji')
@click.pass_context
def bookings(ctx, time, booking_id):
    """Wyświetl rezerwacje użytkownika lub szczegóły konkretnej rezerwacji"""
    client = ctx.obj['client']
    try:
        # Jeśli podano booking_id, pokaż szczegóły
        if booking_id:
            booking = client.get_booking_details(booking_id)
            click.echo(click.style(f'\n=== Szczegóły rezerwacji {booking_id} ===\n', fg='cyan', bold=True))
            click.echo(f"ID: {booking.get('id', 'N/A')}")
            click.echo(f"Film: {booking.get('filmName', 'N/A')}")
            click.echo(f"Kino: {booking.get('cinemaName', 'N/A')}")
            click.echo(f"Data: {booking.get('showDateTime', 'N/A')}")
            click.echo(f"Sala: {booking.get('auditorium', 'N/A')}")
            click.echo(f"Miejsca: {', '.join(booking.get('seats', []))}")
            click.echo(f"Status: {booking.get('status', 'N/A')}")
            click.echo(f"Kod QR: {booking.get('qrCode', 'N/A')}")
            if booking.get('ticketUrl'):
                click.echo(f"Link do biletu: {booking.get('ticketUrl')}")
        else:
            # Pokaż listę rezerwacji
            bookings = client.get_bookings(time)
            if bookings:
                click.echo(click.style(f'\n=== Rezerwacje ({time.lower()}) ===\n', fg='cyan', bold=True))
                for booking in bookings:
                    click.echo(f"ID: {booking.get('id', 'N/A')}")
                    click.echo(f"Film: {booking.get('filmName', 'N/A')}")
                    click.echo(f"Kino: {booking.get('cinemaName', 'N/A')}")
                    click.echo(f"Data: {booking.get('showDateTime', 'N/A')}")
                    click.echo(f"Miejsca: {', '.join(booking.get('seats', []))}")
                    click.echo(f"Status: {booking.get('status', 'N/A')}")
                    click.echo("---")
            else:
                click.echo(f"Brak rezerwacji ({time.lower()})")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.pass_context
def favourites(ctx):
    """Wyświetl ulubione kina"""
    client = ctx.obj['client']
    try:
        cinemas = client.get_favourite_cinemas()
        if cinemas:
            click.echo(click.style('\n=== Ulubione kina ===\n', fg='cyan', bold=True))
            for cinema in cinemas:
                click.echo(f"• {cinema.get('name', 'N/A')} (ID: {cinema.get('id', 'N/A')})")
        else:
            click.echo("Brak ulubionych kin")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.pass_context
def constraints(ctx):
    """Wyświetl ograniczenia konta Unlimited"""
    client = ctx.obj['client']
    try:
        constraints = client.get_customer_constraints()
        click.echo(click.style('\n=== Ograniczenia konta ===\n', fg='cyan', bold=True))
        click.echo(constraints)
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
def packages():
    """Wyświetl dostępne pakiety Unlimited"""
    client = CinemaCityClient()
    try:
        options = client.get_signup_options()
        if options:
            click.echo(click.style('\n=== Pakiety Unlimited ===\n', fg='cyan', bold=True))
            for option in options:
                name = option.get('name', 'N/A')
                price = option.get('price', 'N/A')
                description = option.get('description', '')
                click.echo(f"• {name} - {price} PLN/mies.")
                if description:
                    click.echo(f"  {description}")
                click.echo()
        else:
            click.echo("Brak dostępnych pakietów")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.pass_context
def payment_methods(ctx):
    """Wyświetl zapisane metody płatności"""
    client = ctx.obj['client']
    try:
        methods = client.get_payment_methods()
        if methods:
            click.echo(click.style('\n=== Metody płatności ===\n', fg='cyan', bold=True))
            for method in methods:
                method_type = method.get('type', 'N/A')
                last4 = method.get('last4', 'N/A')
                brand = method.get('brand', 'N/A')
                is_default = method.get('isDefault', False)
                default_tag = ' (domyślna)' if is_default else ''
                click.echo(f"• {brand} ****{last4} ({method_type}){default_tag}")
        else:
            click.echo("Brak zapisanych metod płatności")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.option('--showing-type', default='SHOWING', help='Typ wyświetlania (SHOWING, COMING_SOON)')
@click.option('--cinema-id', default=None, help='ID kina do filtrowania')
@click.pass_context
def now_showing(ctx, showing_type, cinema_id):
    """Wyświetl filmy według typu wyświetlania"""
    client = ctx.obj['client']
    try:
        movies = client.get_movies_by_showing_type(showing_type, cinema_id)
        if movies:
            click.echo(click.style(f'\n=== {showing_type} ({len(movies)} filmów) ===\n', fg='cyan', bold=True))
            for movie in movies[:20]:  # Pierwsze 20
                title = movie.get('featureTitle', 'Nieznany')
                code = movie.get('code', 'N/A')
                click.echo(f"• {title} ({code})")
        else:
            click.echo(f"Brak filmów typu {showing_type}")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.option('--presentation-code', required=True, help='Kod prezentacji/seansu (event ID)')
@click.option('--cinema-id', required=True, help='ID kina')
@click.option('--type', default='PG', type=click.Choice(['PG', 'UNLIMITED']), help='Typ rezerwacji')
@click.pass_context
def start_booking(ctx, presentation_code, cinema_id, type):
    """Inicjalizuj proces rezerwacji (krok 1)"""
    client = ctx.obj['client']
    try:
        result = client.start_booking(presentation_code, cinema_id, type)
        click.echo(click.style('✓ Sesja rezerwacji zainicjalizowana', fg='green'))
        click.echo(f"\nDane sesji:")

        # Wyświetl podstawowe informacje
        if result.get('sessionId'):
            click.echo(f"Session ID: {result.get('sessionId')}")
        if result.get('bookingUrl'):
            click.echo(f"Booking URL: {result.get('bookingUrl')}")

        # Wyświetl informacje o seansie
        if result.get('presentation'):
            pres = result.get('presentation')
            click.echo(f"\nSeans:")
            click.echo(f"  Film: {pres.get('filmName', 'N/A')}")
            click.echo(f"  Data: {pres.get('showDateTime', 'N/A')}")
            click.echo(f"  Sala: {pres.get('auditorium', 'N/A')}")

        # Wyświetl informacje o dostępnych miejscach
        if result.get('seats') or result.get('seatLayout'):
            click.echo(f"\nDostępne miejsca: dane otrzymane")
            click.echo("Użyj tych danych do wyboru miejsc w następnym kroku")

        # Pokaż strukturę response dla debugowania
        click.echo(f"\nPełna odpowiedź (klucze): {list(result.keys())}")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.option('--presentation-id', required=True, help='ID prezentacji/seansu')
@click.pass_context
def booking_preview(ctx, presentation_id):
    """Podgląd procesu rezerwacji (kroki 1-4, bez reCaptcha)"""
    client = ctx.obj['client']
    try:
        click.echo(click.style('\n=== PODGLĄD REZERWACJI ===\n', fg='cyan', bold=True))

        # Krok 1: Szczegóły seansu
        click.echo('[1/4] Pobieranie szczegółów seansu...')
        pres = client.get_presentation_details(presentation_id)
        p = pres['presentation']

        click.echo(click.style(f'\n✓ Film: {p["featureName"]}', fg='green'))
        click.echo(f'  Czas: {p["dateTime"]}')
        click.echo(f'  Sala: {p["venueName"]}')
        click.echo(f'  Kino: {p["locationName"]}')

        # Krok 2: Plan sali
        click.echo('\n[2/4] Pobieranie planu sali...')
        seatplan = client.get_seat_plan(str(p['venueId']), str(p['seatplanId']))
        click.echo(click.style(f'✓ Plan sali: {seatplan["rd"]["width"]}x{seatplan["rd"]["height"]}px', fg='green'))

        # Krok 3: Status miejsc
        click.echo('\n[3/4] Sprawdzanie dostępności miejsc...')
        status = client.get_seats_status(presentation_id)
        seats = status['seats']
        available = sum(1 for s in seats.values() if s == 0)
        click.echo(click.style(f'✓ Dostępnych miejsc: {available}/{len(seats)}', fg='green'))

        # Krok 4: Cennik
        click.echo('\n[4/4] Pobieranie cennika...')
        tickets = client.get_ticket_groups(presentation_id)
        for group in tickets['ticketGroups'].values():
            click.echo(click.style(f'\n✓ {group["name"]}:', fg='green'))
            for ticket in group['tickets']:
                click.echo(f'  • {ticket["name"]}: {ticket["price"]} PLN')

        click.echo(click.style('\n✓ Wszystkie kroki działają BEZ reCaptcha!', fg='green', bold=True))
        click.echo('\nDalsze kroki (blokada miejsca, płatność) wymagają researchu.')

    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.option('--presentation-id', required=True, help='ID prezentacji/seansu')
@click.option('--format', default='ascii', type=click.Choice(['ascii', 'html', 'png']), help='Format wizualizacji')
@click.option('--output', help='Plik wyjściowy (domyślnie: sala.html dla HTML, /tmp/cinemacity_seats_{id}.png dla PNG)')
@click.pass_context
def visualize(ctx, presentation_id, format, output):
    """Wizualizuj salę kinową i dostępność miejsc"""
    try:
        if format == 'ascii':
            # Importuj i uruchom wizualizację ASCII (spatial v3 - ulepszona)
            from visualize_seats_spatial_v3 import visualize_seats_spatial
            visualize_seats_spatial(presentation_id)
        elif format == 'png':
            # Importuj i uruchom wizualizację PNG
            from visualize_seats_png import visualize_seats_png
            output_file = visualize_seats_png(presentation_id, output_path=output)
            click.echo(f"\n✓ Wygenerowano PNG: {output_file}")
            click.echo(f"  Otwórz: open \"{output_file}\"")
        else:  # html
            # Importuj i uruchom wizualizację HTML
            from visualize_seats_html import visualize_seats_html
            output_file = visualize_seats_html(presentation_id, output or 'sala.html')
            click.echo(f"\n✓ Możesz otworzyć plik: open {output_file}")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command()
@click.option('--showtime-id', required=True, help='ID seansu')
@click.option('--seats', required=True, help='Liczba miejsc')
@click.pass_context
def book(ctx, showtime_id, seats):
    """Zarezerwuj bilety na seans (pełny flow - TODO)"""
    client = ctx.obj['client']
    try:
        result = client.book_tickets(showtime_id, int(seats))
        if result:
            click.echo(click.style(f'✓ Zarezerwowano {seats} bilet(ów)', fg='green'))
        else:
            click.echo(click.style('✗ Błąd rezerwacji', fg='red'))
    except NotImplementedError as e:
        click.echo(click.style(f'⚠ {str(e)}', fg='yellow'))
        click.echo(f"\nAlternatywnie użyj:")
        click.echo(f"  python3 main.py booking-preview --presentation-id {showtime_id}")
    except Exception as e:
        click.echo(click.style(f'✗ Błąd: {str(e)}', fg='red'))


@cli.command('filmweb')
@click.argument('title')
@click.option('--year', type=int, help='Rok produkcji (opcjonalnie dla precyzyjnego wyszukiwania)')
@click.option('--details', is_flag=True, help='Pokaż szczegółowe informacje z ocenami')
def filmweb_search(title, year, details):
    """Wyszukaj film na Filmweb"""
    from filmweb import FilmwebClient

    client = FilmwebClient()

    if year:
        # Precyzyjne wyszukiwanie po tytule + roku
        results = client.search_by_title_year(title, year, page_size=10)
        click.echo(f"\n🎬 Filmy '{title}' z {year} roku:")
    else:
        # Podstawowe wyszukiwanie
        results = client.search(title, page_size=10)

        if details:
            # Pobierz szczegóły dla każdego wyniku
            detailed_results = []
            for film in results:
                film_details = client.get_film_details(film['id'])
                if film_details:
                    detailed_results.append(film_details)
            results = detailed_results

        click.echo(f"\n🎬 Wyniki wyszukiwania '{title}':")

    if not results:
        click.echo("❌ Nie znaleziono filmów")
        return

    click.echo(f"Znaleziono: {len(results)} filmów\n")
    click.echo("=" * 80)

    for i, film in enumerate(results, 1):
        title_text = film.get('title', 'Nieznany tytuł')
        film_id = film.get('id')
        year_text = film.get('year', '')

        # Wyświetl tytuł + rok
        if year_text:
            click.echo(f"\n{i}. {title_text} ({year_text})")
        else:
            click.echo(f"\n{i}. {title_text}")

        # Tytuł oryginalny
        original = film.get('original_title')
        if original and original != title_text:
            click.echo(f"   Tytuł oryginalny: {original}")

        # Ocena (jeśli dostępna - tylko w trybie --details lub search_by_title_year)
        rating = film.get('rating')
        rating_count = film.get('rating_count')
        if rating:
            stars = "⭐" * int(round(float(rating) / 2))
            click.echo(f"   Ocena: {rating:.2f}/10 {stars} ({rating_count:,} ocen)")

        # Obsada (podstawowe wyszukiwanie)
        cast = film.get('cast', [])
        if cast:
            click.echo(f"   Obsada: {', '.join(cast)}")

        # "Chcą zobaczyć" (tylko szczegóły)
        want_to_see = film.get('want_to_see_count')
        if want_to_see:
            click.echo(f"   👁️  Chcą zobaczyć: {want_to_see:,}")

        # URL
        click.echo(f"   🆔 Film ID: {film_id}")
        click.echo(f"   🔗 {film.get('filmweb_url', f'https://www.filmweb.pl/film/{film_id}')}")

    click.echo("\n" + "=" * 80)
    click.echo(f"\n💡 Wskazówka: Sprawdź czy film gra w Cinema City:")
    click.echo(f"   python3 main.py search '{results[0]['title']}'")


if __name__ == '__main__':
    cli(obj={})
