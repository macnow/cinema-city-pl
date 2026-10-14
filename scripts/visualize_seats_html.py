#!/usr/bin/env python3
"""
Wizualizacja sali kinowej w HTML/SVG (bez dodatkowych zależności)
"""

from cinemacity import CinemaCityClient
import sys


def visualize_seats_html(presentation_id: str, output_file: str = "sala.html"):
    """
    Generuje interaktywną wizualizację HTML/SVG

    Args:
        presentation_id: ID prezentacji/seansu
        output_file: Nazwa pliku wyjściowego (domyślnie sala.html)
    """
    client = CinemaCityClient()

    # Pobierz dane
    print(f"Pobieranie danych dla seansu {presentation_id}...")

    presentation = client.get_presentation_details(presentation_id)
    p = presentation['presentation']

    venue_id = str(p['venueId'])
    seatplan_id = str(p['seatplanId'])

    seatplan = client.get_seat_plan(venue_id, seatplan_id)
    seats_status = client.get_seats_status(presentation_id)

    film_name = p['featureName']
    venue_name = p['venueName']
    show_time = p['dateTime']

    # Przygotuj dane miejsc
    seats_data = []
    sections = seatplan.get('S', {})
    status_map = seats_status.get('seats', {})

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

                    # POPRAWIONY FORMAT: section_seatID_row
                    status_key = f"{section_id}_{seat_id}_{row_name}"

                    # POPRAWIONA LOGIKA: miejsce w API = dostępne
                    if status_key in status_map:
                        status = 'available'
                    else:
                        # NIE w API = zajęte/niedostępne
                        status = 'taken'

                    seats_data.append({
                        'x': cx,
                        'y': cy,
                        'name': seat_name,
                        'row': row_name,
                        'status': status
                    })

    # Statystyki
    available_count = sum(1 for s in seats_data if s['status'] == 'available')
    taken_count = sum(1 for s in seats_data if s['status'] == 'taken')
    unavailable_count = sum(1 for s in seats_data if s['status'] == 'unavailable')

    # Generuj HTML
    width = seatplan['rd']['width']
    height = seatplan['rd']['height']

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{film_name} - {venue_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #fff;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #4CAF50;
            margin-bottom: 10px;
        }}
        .info {{
            text-align: center;
            color: #aaa;
            margin-bottom: 20px;
        }}
        .stats {{
            text-align: center;
            margin-bottom: 20px;
            font-size: 18px;
        }}
        .stats span {{
            margin: 0 20px;
        }}
        .available {{ color: #4CAF50; }}
        .taken {{ color: #f44336; }}
        svg {{
            display: block;
            margin: 0 auto;
            background: #2a2a2a;
            border: 2px solid #444;
            border-radius: 10px;
        }}
        .seat {{
            cursor: pointer;
            transition: all 0.2s;
        }}
        .seat:hover {{
            opacity: 0.7;
            stroke: white;
            stroke-width: 2;
        }}
        .screen {{
            fill: #333;
            stroke: #666;
            stroke-width: 3;
        }}
        .screen-text {{
            fill: #999;
            font-size: 24px;
            font-weight: bold;
            text-anchor: middle;
        }}
        .seat-label {{
            fill: white;
            font-size: 10px;
            font-weight: bold;
            text-anchor: middle;
            pointer-events: none;
        }}
        .legend {{
            text-align: center;
            margin-top: 20px;
            font-size: 16px;
        }}
        .legend-item {{
            display: inline-block;
            margin: 0 20px;
        }}
        .legend-circle {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            vertical-align: middle;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{film_name}</h1>
        <div class="info">{venue_name} | {show_time}</div>
        <div class="stats">
            <span class="available">🟢 Dostępne: {available_count}</span>
            <span class="taken">🔴 Zajęte: {taken_count}</span>
            <span style="color: #999;">⚪ Niedostępne: {unavailable_count}</span>
            <span>W sprzedaży: {available_count + taken_count} | Wszystkich: {len(seats_data)}</span>
        </div>

        <svg width="{width + 100}" height="{height + 200}" viewBox="-50 -150 {width + 100} {height + 200}">
            <!-- Ekran -->
            <rect x="50" y="-120" width="{width - 100}" height="40" class="screen" rx="5"/>
            <text x="{width/2}" y="-90" class="screen-text">E K R A N</text>

            <!-- Miejsca -->
"""

    # Dodaj miejsca
    for seat in seats_data:
        if seat['status'] == 'available':
            color = '#4CAF50'
            opacity = '0.8'
            status_text = "Dostępne"
        elif seat['status'] == 'taken':
            color = '#f44336'
            opacity = '0.6'
            status_text = "Zajęte"
        else:  # unavailable
            color = '#999999'
            opacity = '0.4'
            status_text = "Niedostępne (VIP/niepełnosprawni)"

        title = f"Rząd {seat['row']}, Miejsce {seat['name']}"

        html += f"""            <circle cx="{seat['x']}" cy="{seat['y']}" r="18"
                    fill="{color}" opacity="{opacity}" class="seat">
                <title>{title} - {status_text}</title>
            </circle>
            <text x="{seat['x']}" y="{seat['y'] + 4}" class="seat-label">{seat['name']}</text>
"""

    html += f"""        </svg>

        <div class="legend">
            <div class="legend-item">
                <span class="legend-circle" style="background: #4CAF50;"></span>
                Dostępne
            </div>
            <div class="legend-item">
                <span class="legend-circle" style="background: #f44336;"></span>
                Zajęte
            </div>
            <div class="legend-item">
                <span class="legend-circle" style="background: #999999;"></span>
                Niedostępne (VIP, niepełnosprawni, zablokowane)
            </div>
        </div>
    </div>

    <script>
        // Dodaj interaktywność
        document.querySelectorAll('.seat').forEach(seat => {{
            seat.addEventListener('click', function() {{
                const title = this.querySelector('title').textContent;
                alert(title);
            }});
        }});
    </script>
</body>
</html>
"""

    # Zapisz do pliku
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✓ Zapisano wizualizację do: {output_file}")
    print(f"✓ Otwórz plik w przeglądarce aby zobaczyć interaktywną mapę sali")

    return output_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Wizualizacja sali kinowej w HTML")
        print("\nUżycie:")
        print("  python3 visualize_seats_html.py <presentation_id> [output.html]")
        print("\nPrzykład:")
        print("  python3 visualize_seats_html.py 1218388 sala.html")
        sys.exit(1)

    presentation_id = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "sala.html"

    visualize_seats_html(presentation_id, output_file)
