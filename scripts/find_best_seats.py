#!/usr/bin/env python3
"""
Znajdź najlepsze miejsca w środku sali dla danego seansu
"""

from cinemacity import CinemaCityClient
import click


def find_center_seats(presentation_id: str, num_seats: int = 2, max_results: int = 10):
    """
    Znajdź najlepsze miejsca blisko środka sali

    Args:
        presentation_id: ID prezentacji/seansu
        num_seats: Liczba miejsc obok siebie (domyślnie 2)
        max_results: Maksymalna liczba wyników do pokazania

    Returns:
        Lista krotek (rząd, miejsca, odległość_od_środka)
    """
    client = CinemaCityClient()

    print(f"Analizuję dostępność miejsc dla seansu {presentation_id}...")

    # Pobierz dane
    presentation = client.get_presentation_details(presentation_id)
    p = presentation['presentation']

    venue_id = str(p['venueId'])
    seatplan_id = str(p['seatplanId'])

    seatplan = client.get_seat_plan(venue_id, seatplan_id)
    seats_status = client.get_seats_status(presentation_id)

    film_name = p['featureName']
    venue_name = p['venueName']
    show_time = p['dateTime']

    print(f"\n{'='*70}")
    print(f"  {film_name}")
    print(f"  {venue_name} - {show_time}")
    print(f"{'='*70}\n")

    # Znajdź wszystkie dostępne miejsca z ich współrzędnymi
    available_seats = []
    sections = seatplan.get('S', {})
    status_map = seats_status.get('seats', {})

    # Znajdź wymiary sali (min/max współrzędnych)
    min_x, max_x = float('inf'), float('-inf')
    min_y, max_y = float('inf'), float('-inf')

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

                    # POPRAWIONY format klucza: section_seatID_row
                    status_key = f"{section_id}_{seat_id}_{row_name}"

                    # POPRAWIONA LOGIKA: miejsce w API = dostępne
                    # (API zwraca TYLKO miejsca dostępne do rezerwacji)
                    if status_key in status_map:
                        available_seats.append({
                            'row': row_name,
                            'seat': seat_name,
                            'x': cx,
                            'y': cy,
                            'section': section_id
                        })

                        # Aktualizuj wymiary
                        min_x = min(min_x, cx)
                        max_x = max(max_x, cx)
                        min_y = min(min_y, cy)
                        max_y = max(max_y, cy)

    if not available_seats:
        print("❌ Brak dostępnych miejsc!")
        return []

    # Środek sali
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    print(f"📊 Wymiary sali: X({min_x:.0f}-{max_x:.0f}), Y({min_y:.0f}-{max_y:.0f})")
    print(f"🎯 Środek sali: ({center_x:.0f}, {center_y:.0f})")
    print(f"🪑 Dostępnych miejsc: {len(available_seats)}\n")

    # Grupuj miejsca po rzędach
    rows_dict = {}
    for seat in available_seats:
        row = seat['row']
        if row not in rows_dict:
            rows_dict[row] = []
        rows_dict[row].append(seat)

    # Dla każdego rzędu, sortuj miejsca po współrzędnej X
    for row in rows_dict:
        rows_dict[row].sort(key=lambda s: s['x'])

    # Znajdź grupy sąsiadujących miejsc
    best_groups = []

    for row, seats in rows_dict.items():
        # Znajdź ciągłe grupy wolnych miejsc
        for i in range(len(seats) - num_seats + 1):
            group = seats[i:i+num_seats]

            # Sprawdź czy miejsca są obok siebie (różnica X < 100 jednostek)
            is_continuous = True
            for j in range(len(group) - 1):
                x_diff = abs(group[j+1]['x'] - group[j]['x'])
                if x_diff > 100:  # Zbyt duża przerwa
                    is_continuous = False
                    break

            if not is_continuous:
                continue

            # Oblicz odległość środka grupy od środka sali
            group_center_x = sum(s['x'] for s in group) / len(group)
            group_center_y = sum(s['y'] for s in group) / len(group)

            # Odległość od centrum w poziomie (lewa-prawa)
            x_distance = abs(group_center_x - center_x)

            # Oblicz pełną odległość euklidesową od środka (dla backward compatibility)
            distance = ((group_center_x - center_x) ** 2 + (group_center_y - center_y) ** 2) ** 0.5

            # Oblicz % wysokości sali (0% = ekran, 100% = tył)
            total_height = max_y - min_y
            height_pct = ((group_center_y - min_y) / total_height * 100) if total_height > 0 else 0

            # SWEET SPOT dla IMAX: 66-75% wysokości (rzędy 9-10)
            # Im bliżej 70%, tym lepsze
            optimal_height = 70.0  # Środek sweet spot (między 66% a 75%)
            height_deviation_pct = abs(height_pct - optimal_height)  # % odchylenia od ideału

            # Oblicz % odchylenia od środka poziomego (jako % szerokości sali)
            total_width = max_x - min_x
            horizontal_deviation_pct = (x_distance / (total_width / 2) * 100) if total_width > 0 else 0

            # Scoring: mniejszy = lepszy
            # Priorytet: wysokość (waga 5) > centrum poziome (waga 0.5)
            height_penalty = height_deviation_pct * 5
            score = height_penalty + (x_distance * 0.5)

            best_groups.append({
                'row': row,
                'seats': [s['seat'] for s in group],
                'distance': distance,
                'score': score,
                'x': group_center_x,
                'y': group_center_y,
                'height_deviation_pct': height_deviation_pct,
                'horizontal_deviation_pct': horizontal_deviation_pct
            })

    # Sortuj po najlepszym scorze (najmniejszy = najlepszy)
    best_groups.sort(key=lambda g: g['score'])

    # Pokaż najlepsze wyniki
    print(f"🏆 TOP {max_results} najlepszych grup {num_seats} miejsc:\n")

    for i, group in enumerate(best_groups[:max_results], 1):
        seats_str = ', '.join(group['seats'])
        height_dev = group['height_deviation_pct']
        horizontal_dev = group['horizontal_deviation_pct']

        # Wizualizacja jakości na podstawie odchyleń
        # Wysokość ma większą wagę
        total_deviation = height_dev * 1.5 + horizontal_dev
        if total_deviation < 10:
            quality = "⭐⭐⭐ IDEALNE"
        elif total_deviation < 20:
            quality = "⭐⭐ BARDZO DOBRE"
        elif total_deviation < 35:
            quality = "⭐ DOBRE"
        else:
            quality = "OK"

        print(f"{i:2d}. Rząd {group['row']:>3} | Miejsca: {seats_str:20} | {quality}")
        print(f"     Wysokość: {height_dev:4.1f}% od ideału | Środek: {horizontal_dev:4.1f}% od centrum")
        print()

    return best_groups[:max_results]


@click.command()
@click.option('--presentation-id', required=True, help='ID prezentacji/seansu')
@click.option('--seats', default=2, help='Liczba miejsc obok siebie (domyślnie 2)')
@click.option('--max-results', default=10, help='Liczba wyników do pokazania')
@click.option('--visualize-ascii', is_flag=True, help='Pokaż ASCII mapę sali z zaznaczonymi propozycjami')
def main(presentation_id, seats, max_results, visualize_ascii):
    """Znajdź najlepsze miejsca w środku sali"""
    try:
        results = find_center_seats(presentation_id, seats, max_results)

        if results:
            if visualize_ascii:
                print(f"\n{'='*70}")
                print(f"📍 WIZUALIZACJA SALI Z PROPONOWANYMI MIEJSCAMI")
                print(f"{'='*70}\n")

                from visualize_seats_spatial_v3 import visualize_seats_spatial
                visualize_seats_spatial(presentation_id, recommended_seats=results)
            else:
                print(f"\n💡 Wskazówka: Użyj --visualize-ascii aby zobaczyć mapę sali z zaznaczonymi miejscami")
                print(f"   python3 find_best_seats.py --presentation-id {presentation_id} --seats {seats} --visualize-ascii")
    except Exception as e:
        print(f"❌ Błąd: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
