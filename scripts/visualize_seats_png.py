#!/usr/bin/env python3
"""
Generowanie nowoczesnej graficznej wizualizacji PNG sali kinowej
"""

from cinemacity import CinemaCityClient
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import tempfile
import sys


def create_gradient_circle(draw, x, y, radius, color_center, color_edge):
    """Rysuje koło z gradientem radialnym (efekt 3D)"""
    for i in range(radius, 0, -1):
        # Interpolacja koloru od krawędzi do środka
        factor = i / radius
        r = int(color_edge[0] * factor + color_center[0] * (1 - factor))
        g = int(color_edge[1] * factor + color_center[1] * (1 - factor))
        b = int(color_edge[2] * factor + color_center[2] * (1 - factor))
        draw.ellipse([x - i, y - i, x + i, y + i], fill=(r, g, b))


def hex_to_rgb(hex_color):
    """Konwertuje kolor hex na tuple RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def visualize_seats_png(presentation_id: str, recommended_seats=None, output_path=None):
    """Generuje nowoczesny graficzny PNG z wizualizacją sali kinowej

    Args:
        presentation_id: ID prezentacji/seansu
        recommended_seats: Lista dict z 'row' i 'seats' dla zaznaczenia proponowanych miejsc
        output_path: Ścieżka wyjściowa (domyślnie: /tmp/cinemacity_seats_{id}.png)

    Returns:
        str: Ścieżka do wygenerowanego pliku PNG
    """
    # Przygotuj set z rekomendowanymi miejscami
    recommended_set = set()
    if recommended_seats:
        for group in recommended_seats:
            row = str(group['row'])
            for seat in group['seats']:
                recommended_set.add((row, str(seat)))

    # Pobierz dane z API
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

    # Organizuj miejsca według współrzędnych
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
                    cy = coords.get('cy', 0)
                    has_hc = seat.get('hc', 0)

                    status_key = f"{section_id}_{seat_id}_{row_name}"

                    # Określ kategorię miejsca
                    if has_hc == 1 or 'N' in str(seat_name):
                        category = 'handicapped'
                    elif status_key in status_map:
                        category = 'available'
                    else:
                        category = 'taken'

                    # Sprawdź czy to rekomendowane miejsce
                    is_recommended = (row_name, seat_name) in recommended_set

                    rows_data[row_name].append({
                        'name': seat_name,
                        'x': cx,
                        'y': cy,
                        'category': category,
                        'recommended': is_recommended
                    })

    # Znajdź wymiary sali
    all_seats = []
    for row_name, seats in rows_data.items():
        all_seats.extend(seats)

    min_x = min(s['x'] for s in all_seats)
    max_x = max(s['x'] for s in all_seats)
    min_y = min(s['y'] for s in all_seats)
    max_y = max(s['y'] for s in all_seats)

    # Parametry renderowania
    seat_radius = 14  # Promień miejsca (większy dla lepszej widoczności)
    margin_top = 180
    margin_bottom = 180
    margin_left = 120
    margin_right = 120

    # Skala do konwersji współrzędnych API na piksele
    # Zmniejszona skala Y aby zredukować przerwę
    scale_x = 0.6
    scale_y = 0.75  # Zmniejszone z 0.8 na 0.75 aby zbić rzędy

    # Wymiary obrazu
    img_width = int((max_x - min_x) * scale_x) + margin_left + margin_right
    img_height = int((max_y - min_y) * scale_y) + margin_top + margin_bottom

    # Stwórz obraz z gradientem tła
    img = Image.new('RGB', (img_width, img_height), color='#0a0a0a')
    draw = ImageDraw.Draw(img)

    # Gradient tła (od góry do dołu)
    for y in range(img_height):
        # Od ciemnego na górze do jeszcze ciemniejszego na dole
        factor = y / img_height
        r = int(15 * (1 - factor) + 8 * factor)
        g = int(15 * (1 - factor) + 8 * factor)
        b = int(20 * (1 - factor) + 10 * factor)
        draw.line([(0, y), (img_width, y)], fill=(r, g, b))

    # Załaduj fonty
    try:
        font_title = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 32)
        font_subtitle = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 18)
        font_small = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 9)
        font_legend = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 16)
    except:
        try:
            font_title = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 32)
            font_subtitle = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
            font_small = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 9)
            font_legend = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 16)
        except:
            try:
                font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
                font_subtitle = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
                font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)
                font_legend = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
            except:
                font_title = ImageFont.load_default()
                font_subtitle = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_legend = ImageFont.load_default()

    # Narysuj header z cieniem
    # Cień dla tytułu
    draw.text((img_width // 2 + 2, 42), film_name, fill='#000000', font=font_title, anchor='mm')
    # Tytuł
    draw.text((img_width // 2, 40), film_name, fill='#ffffff', font=font_title, anchor='mm')

    # Subtitle
    draw.text((img_width // 2, 75), f'{venue_name} • {show_time}',
              fill='#888888', font=font_subtitle, anchor='mm')

    # Narysuj nowoczesny ekran z perspektywą
    screen_width = 500
    screen_height = 12
    screen_top_width = 600  # Szerszy na górze dla efektu perspektywy

    screen_center_x = img_width // 2
    screen_y = margin_top - 60

    # Ekran jako trapez (perspektywa)
    screen_polygon = [
        (screen_center_x - screen_top_width // 2, screen_y),  # Lewy górny
        (screen_center_x + screen_top_width // 2, screen_y),  # Prawy górny
        (screen_center_x + screen_width // 2, screen_y + screen_height),  # Prawy dolny
        (screen_center_x - screen_width // 2, screen_y + screen_height)   # Lewy dolny
    ]

    # Gradient dla ekranu (srebrny metaliczny)
    for i in range(screen_height):
        factor = i / screen_height
        r = int(240 - 40 * abs(factor - 0.5))
        g = int(240 - 40 * abs(factor - 0.5))
        b = int(245 - 45 * abs(factor - 0.5))

        y_pos = screen_y + i
        left_x = int(screen_center_x - screen_top_width // 2 +
                     (screen_top_width - screen_width) // 2 * (i / screen_height))
        right_x = int(screen_center_x + screen_top_width // 2 -
                      (screen_top_width - screen_width) // 2 * (i / screen_height))
        draw.line([(left_x, y_pos), (right_x, y_pos)], fill=(r, g, b), width=1)

    # Ramka ekranu
    draw.polygon(screen_polygon, outline='#666666', width=2)

    # Tekst "EKRAN"
    draw.text((screen_center_x, screen_y + screen_height // 2), 'E K R A N',
              fill='#333333', font=font_small, anchor='mm')

    # Glow pod ekranem
    glow_y = screen_y + screen_height + 5
    for i in range(20):
        alpha = int(30 * (1 - i / 20))
        r, g, b = 200, 200, 210
        draw.line([(screen_center_x - screen_width // 2, glow_y + i),
                   (screen_center_x + screen_width // 2, glow_y + i)],
                  fill=(r, g, b, alpha) if alpha > 0 else (r, g, b))

    # Paleta kolorów - nowoczesne, kinowe kolory
    colors = {
        'available': {
            'center': hex_to_rgb('#10b981'),  # Jasny zielony
            'edge': hex_to_rgb('#059669')      # Ciemny zielony
        },
        'taken': {
            'center': hex_to_rgb('#ef4444'),   # Jasny czerwony
            'edge': hex_to_rgb('#b91c1c')      # Ciemny czerwony
        },
        'handicapped': {
            'center': hex_to_rgb('#3b82f6'),   # Jasny niebieski
            'edge': hex_to_rgb('#1d4ed8')      # Ciemny niebieski
        },
        'recommended': {
            'center': hex_to_rgb('#fbbf24'),   # Jasny złoty
            'edge': hex_to_rgb('#d97706')      # Ciemny złoty
        }
    }

    # Liczniki
    counts = {
        'available': 0,
        'taken': 0,
        'handicapped': 0,
        'recommended': 0
    }

    # Narysuj miejsca
    for row_name, seats in sorted(rows_data.items(), key=lambda x: int(x[0])):
        # Sortuj miejsca po X
        seats.sort(key=lambda s: s['x'])

        # Narysuj numer rzędu po lewej z lepszym stylem
        first_seat = seats[0]
        row_y = margin_top + int((first_seat['y'] - min_y) * scale_y)

        # Tło dla numeru rzędu
        row_label = f'Rząd {row_name}'
        bbox = draw.textbbox((50, row_y), row_label, font=font_small, anchor='rm')
        padding = 4
        draw.rounded_rectangle(
            [bbox[0] - padding, bbox[1] - padding, bbox[2] + padding, bbox[3] + padding],
            radius=4, fill='#1a1a1a', outline='#333333', width=1
        )
        draw.text((50, row_y), row_label, fill='#999999', font=font_small, anchor='rm')

        # Narysuj miejsca
        for seat in seats:
            x = margin_left + int((seat['x'] - min_x) * scale_x)
            y = margin_top + int((seat['y'] - min_y) * scale_y)

            # Wybierz kolory
            if seat['recommended']:
                color_scheme = colors['recommended']
                counts['recommended'] += 1
            else:
                color_scheme = colors[seat['category']]
                counts[seat['category']] += 1

            # Narysuj cień
            shadow_offset = 3
            for i in range(shadow_offset, 0, -1):
                alpha = int(50 * (1 - i / shadow_offset))
                draw.ellipse([x - seat_radius + i, y - seat_radius + i,
                             x + seat_radius + i, y + seat_radius + i],
                            fill=(0, 0, 0))

            # Narysuj miejsce z gradientem
            create_gradient_circle(draw, x, y, seat_radius,
                                 color_scheme['center'], color_scheme['edge'])

            # Ciemna ramka
            draw.ellipse([x - seat_radius, y - seat_radius,
                         x + seat_radius, y + seat_radius],
                        outline='#1a1a1a', width=2)

            # Narysuj numer miejsca
            if seat['category'] == 'available' or seat['recommended']:
                # Cień tekstu
                draw.text((x + 1, y + 1), str(seat['name']),
                         fill='#000000', font=font_small, anchor='mm')
                # Tekst
                draw.text((x, y), str(seat['name']),
                         fill='#ffffff', font=font_small, anchor='mm')

    # Narysuj nowoczesną legendę
    legend_y = img_height - margin_bottom + 60

    # Nagłówek legendy
    draw.text((img_width // 2, legend_y - 40), 'Legenda',
              fill='#ffffff', font=font_legend, anchor='mm')

    legend_items = [
        ('available', 'Dostępne', counts['available']),
        ('taken', 'Zajęte', counts['taken']),
        ('handicapped', 'Dla niepełnosprawnych', counts['handicapped'])
    ]

    if counts['recommended'] > 0:
        legend_items.insert(0, ('recommended', 'Proponowane', counts['recommended']))

    # Oblicz szerokość dla wycentrowania
    item_width = 220
    total_width = len(legend_items) * item_width
    legend_x_start = (img_width - total_width) // 2

    legend_x = legend_x_start
    for cat, label, count in legend_items:
        # Tło dla elementu legendy
        draw.rounded_rectangle(
            [legend_x - 5, legend_y - 5, legend_x + item_width - 15, legend_y + 30],
            radius=8, fill='#1a1a1a', outline='#333333', width=1
        )

        # Kolorowy kółko z gradientem (miniatura fotela)
        mini_radius = 10
        create_gradient_circle(draw, legend_x + mini_radius, legend_y + 12, mini_radius,
                             colors[cat]['center'], colors[cat]['edge'])
        draw.ellipse([legend_x, legend_y + 2, legend_x + mini_radius * 2, legend_y + 22],
                    outline='#1a1a1a', width=1)

        # Tekst
        draw.text((legend_x + 30, legend_y + 12), f'{label}: {count}',
                 fill='#cccccc', font=font_legend, anchor='lm')
        legend_x += item_width

    # Podsumowanie
    total = sum(counts.values())
    in_sale = counts['available'] + counts['taken'] + counts['recommended']

    # Tło dla podsumowania
    summary_text = f'W sprzedaży: {in_sale}  •  Wszystkich miejsc: {total}'
    bbox = draw.textbbox((img_width // 2, legend_y + 60), summary_text,
                         font=font_legend, anchor='mm')
    padding = 10
    draw.rounded_rectangle(
        [bbox[0] - padding, bbox[1] - padding, bbox[2] + padding, bbox[3] + padding],
        radius=8, fill='#0d0d0d', outline='#444444', width=1
    )
    draw.text((img_width // 2, legend_y + 60), summary_text,
             fill='#888888', font=font_legend, anchor='mm')

    # Określ ścieżkę wyjściową
    if output_path is None:
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f'cinemacity_seats_{presentation_id}.png')

    # Zapisz obraz
    img.save(output_path, quality=95)

    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Użycie: python3 visualize_seats_png.py <presentation_id> [output_path]')
        sys.exit(1)

    presentation_id = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result_path = visualize_seats_png(presentation_id, output_path=output_path)
    print(f'\n✓ Wygenerowano PNG: {result_path}')
    print(f'  Otwórz: open "{result_path}"')
