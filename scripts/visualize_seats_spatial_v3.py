#!/usr/bin/env python3
"""
Wizualizacja z dokładnymi pozycjami przestrzennymi (aisle = pusta przestrzeń)
"""

from cinemacity import CinemaCityClient
import sys


def generate_ascii_lines(presentation_id: str, recommended_seats=None):
    """Generuje linie ASCII dla wizualizacji sali

    Args:
        presentation_id: ID prezentacji/seansu
        recommended_seats: Lista dict z 'row' i 'seats' dla zaznaczenia proponowanych miejsc

    Returns:
        tuple: (lines, metadata) gdzie:
            - lines: lista stringów (linie ASCII)
            - metadata: dict z informacjami (film_name, venue_name, show_time, counts)
    """
    recommended_set = set()
    if recommended_seats:
        for group in recommended_seats:
            row = str(group['row'])
            for seat in group['seats']:
                recommended_set.add((row, str(seat)))

    client = CinemaCityClient()

    presentation = client.get_presentation_details(presentation_id)
    p = presentation['presentation']

    venue_id = str(p['venueId'])
    seatplan_id = str(p['seatplanId'])

    seatplan = client.get_seat_plan(venue_id, seatplan_id)
    seats_status = client.get_seats_status(presentation_id)

    film_name = p['featureName']
    venue_name = p['venueName']
    show_time = p['dateTime']

    lines = []

    # Header
    lines.append('')
    lines.append('=' * 80)
    lines.append(f'  {film_name}')
    lines.append(f'  {venue_name} - {show_time}')
    lines.append('=' * 80)
    lines.append('')

    # Ekran
    lines.append(' ' * 30 + '╔' + '═' * 21 + '╗')
    lines.append(' ' * 30 + '║      E K R A N      ║')
    lines.append(' ' * 30 + '╚' + '═' * 21 + '╝')
    lines.append('')

    # Organizuj miejsca z uwzględnieniem współrzędnych
    sections = seatplan.get('S', {})
    status_map = seats_status.get('seats', {})

    rows_data = {}

    for section_id, section in sections.items():
        groups = section.get('G', {})
        for group_id, group in groups.items():
            rows = group.get('R', {})
            for row_id, row in rows.items():
                row_name = row.get('n', row_id)
                seats = row.get('S', {})

                if row_name not in rows_data:
                    rows_data[row_name] = []

                for seat_id, seat in seats.items():
                    seat_name = seat.get('n', seat_id)
                    coords = seat.get('rd', {})
                    cx = coords.get('cx', 0)
                    has_hc = seat.get('hc', 0)

                    # POPRAWIONY FORMAT: section_seatID_row
                    status_key = f"{section_id}_{seat_id}_{row_name}"

                    # POPRAWIONA LOGIKA:
                    # API zwraca TYLKO miejsca dostępne do rezerwacji
                    # Miejsca w seatplan ALE NIE w API = zajęte przez innych
                    if has_hc == 1:
                        category = 'handicapped'
                    elif 'N' in str(seat_name):
                        category = 'handicapped'
                    elif status_key in status_map:
                        # Miejsce jest w API = dostępne do rezerwacji
                        category = 'available'
                    else:
                        # Miejsce w seatplan ALE NIE w API = zajęte/zarezerwowane
                        category = 'taken'

                    rows_data[row_name].append({
                        'name': seat_name,
                        'x': cx,
                        'category': category
                    })

    # Znajdź zakres X dla całej sali
    all_x = []
    for row_name, seats in rows_data.items():
        all_x.extend([s['x'] for s in seats])

    min_x = min(all_x)
    max_x = max(all_x)

    # Skala: 1 emoji (2 znaki) = 60 jednostek X
    scale = 60

    # Renderuj z dokładnymi pozycjami
    sorted_rows = sorted(rows_data.items(), key=lambda x: int(x[0]))

    counts = {
        'available': 0,
        'taken': 0,
        'handicapped': 0,
        'unavailable': 0,
        'recommended': 0
    }

    symbols = {
        'available': '🟢',
        'taken': '🔴',
        'handicapped': '♿',
        'unavailable': '⚪',
        'recommended': '🔵'  # Dla zaznaczenia proponowanych miejsc
    }

    for row_name, seats in sorted_rows:
        # Sortuj miejsca po X ROSNĄCO
        # Niskie X (lewa strona) = wysokie numery miejsc (26, 25...)
        # Wysokie X (prawa strona) = niskie numery miejsc (10, 11...)
        seats.sort(key=lambda s: s['x'])

        row_str = f'  Rząd {row_name:>2} │ '

        # Renderuj miejsca z dokładnymi pozycjami
        current_pos = 0  # Pozycja w znakach (emoji = 2 znaki)

        for seat in seats:
            cat = seat['category']

            # Sprawdź czy miejsce jest w rekomendacjach
            is_recommended = (row_name, seat['name']) in recommended_set

            # Licz tylko raz - albo jako recommended, albo jako oryginalną kategorię
            if is_recommended:
                counts['recommended'] += 1
            else:
                counts[cat] += 1

            # Oblicz docelową pozycję (w znakach)
            # Sortowanie rosnące po X daje: niskie X (lewa) → wysokie X (prawa)
            # Co odpowiada: wysokie numery miejsc → niskie numery miejsc
            target_pos = int((seat['x'] - min_x) / scale) * 2

            # Dodaj spacje aby osiągnąć pozycję
            while current_pos < target_pos:
                row_str += ' '
                current_pos += 1

            # Dodaj odpowiedni symbol
            if is_recommended:
                row_str += symbols['recommended']
            else:
                row_str += symbols.get(cat, '⚫')
            current_pos += 2  # Emoji zajmuje 2 pozycje znakowe

        lines.append(row_str)

    # Legenda
    total = sum(counts.values())
    in_sale = counts["available"] + counts["taken"] + counts["recommended"]

    lines.append('')
    lines.append('=' * 80)
    lines.append('  Legenda:')
    if counts['recommended'] > 0:
        lines.append(f'    🔵 Proponowane ({counts["recommended"]})')
    lines.append(f'    🟢 Dostępne ({counts["available"]})')
    lines.append(f'    🔴 Zajęte ({counts["taken"]})')
    lines.append(f'    ♿ Niepełnosprawni ({counts["handicapped"]})')
    lines.append(f'  W sprzedaży: {in_sale} | Wszystkich: {total}')
    lines.append('=' * 80)
    lines.append('')

    metadata = {
        'film_name': film_name,
        'venue_name': venue_name,
        'show_time': show_time,
        'counts': counts,
        'total': total,
        'in_sale': in_sale
    }

    return lines, metadata


def visualize_seats_spatial(presentation_id: str, recommended_seats=None):
    """Wizualizacja z dokładnymi koordynatami X

    Args:
        presentation_id: ID prezentacji/seansu
        recommended_seats: Lista dict z 'row' i 'seats' dla zaznaczenia proponowanych miejsc
    """
    lines, metadata = generate_ascii_lines(presentation_id, recommended_seats)

    # Wydrukuj wszystkie linie
    for line in lines:
        print(line)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Użycie: python3 visualize_seats_spatial_v3.py <presentation_id>')
        sys.exit(1)

    visualize_seats_spatial(sys.argv[1])
