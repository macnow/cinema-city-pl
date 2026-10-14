---
name: cinema-city-pl
description: >
  Obsługa kina Cinema City Poland — repertuar, seanse, wyszukiwanie filmów, dostępność
  i scoring najlepszych miejsc, wizualizacja sal (ASCII/PNG/HTML), oceny i metadane
  z Filmweb, podgląd rezerwacji (cennik, plan sali) oraz funkcje konta Unlimited.
  Używaj gdy użytkownik pyta o: co gra w kinie / repertuar / seanse / godziny filmu,
  najlepsze lub wolne miejsca, salę kinową / mapę miejsc / wizualizację, IMAX / 4DX /
  ScreenX / 3D, oceny Filmweb przy seansach, bilety / ceny biletów / rezerwację miejsc,
  kina Cinema City (lista, adresy, ulubione kino), pakiety Unlimited.
---

# Cinema City PL — Kinowy Agent

Narzędzie CLI (Python, bez logowania = publiczne API). Cały kod jest w `scripts/` obok tego pliku.
Źródło: https://github.com/macnow/cinema-city-pl

## Zasada zero-setup

Jednorazowo utwórz venv w katalogu repozytorium/skillu:

```bash
SKILL="<katalog z tym SKILL.md>"
PY="$SKILL/.venv/bin/python3"
if [ ! -x "$PY" ]; then
  python3 -m venv "$SKILL/.venv" && \
  "$SKILL/.venv/bin/pip" -q install -r "$SKILL/scripts/requirements.txt"
fi

cd "$SKILL"                     # cache ląduje w .cache/ obok SKILL.md
"$PY" scripts/main.py <komenda> ...
```

Zależności: `requests`, `click`, `tabulate`, `python-dotenv`, `Pillow`.
Cache działa automatycznie: seanse 24h, plany sal 30d, lista kin 7d;
status miejsc **zawsze live** — nigdy nie podawaj zajętości z pamięci.

## Mapa komend (main.py)

| Zadanie | Komenda |
|---|---|
| Lista kin (live z API) | `cinemas` |
| Daty z seansami | `dates --cinema-id <ID>` |
| Filmy dziś / na datę | `movies --cinema-id <ID> [--date YYYY-MM-DD]` |
| Seanse | `showtimes --cinema-id <ID> [--movie-id <MID>] [--date ...] [--time-from 18:00 --time-to 22:00] [--with-filmweb] [--with-availability]` |
| Szukaj filmu → movie ID | `search "tytuł"` |
| Szczegóły filmu (gatunki, trailer) | `film <KOD>` |
| Co gra ogólnie | `now-showing --cinema-id <ID>` / `featured --feed <now-playing\|coming-soon\|oscar-nominees\|family-friendly\|events\|watch-in-format>` |
| Atrybuty (IMAX, 3D, języki…) | `attributes [--group screening-type]` |
| Ocena Filmweb | `filmweb "tytuł" [--year RRRR] [--details]` |
| Pakiety Unlimited | `packages` |

## Miejsca i wizualizacja

We wszystkich przykładach niżej: `PY main.py` oznacza `"$PY" scripts/main.py` z sekcji
zero-setup (katalog roboczy = katalog skillu).

```bash
"$PY" scripts/find_best_seats.py --presentation-id <ID> --seats <N> [--visualize-ascii]
"$PY" scripts/quick_search.py "tytuł" --cinema-id <ID> [--seats N]   # film→seanse→miejsca
"$PY" scripts/main.py visualize --presentation-id <ID> --format ascii|png|html [--output plik.html]
"$PY" scripts/main.py booking-preview --presentation-id <ID>         # kroki 1-4: seans, sala, dostępność, cennik
```

Wizualizacje PNG/HTML generuj pliki do katalogu roboczego użytkownika (workspace), nie do katalogu skillu.

- `presentation_id` (kolumna **ID** w wynikach `showtimes`) identyfikuje seans.
- Klucz miejsca w API: `{sekcja}_{miejsce}_{rząd}` (np. `1_15_9`).
- Scoring: optymalna wysokość ~70% sali (waga 5×), centrum poziome (waga 0.5×).
  Oceny: ⭐⭐⭐ odchylenie <10%, ⭐⭐ <20%, ⭐ <35%.
- Sweet spot IMAX: rzędy 9–10. Dla 4DX: środek sali.

## Flow odpowiedzi na typowe pytania

1. **„Co gra dziś / w weekend?"** → `movies --cinema-id <ID> --date <data> [--with-filmweb]`.
   Jeśli użytkownik nie podał kina, zapytaj albo użyj `1097` (Wrocław Wroclavia) i zaznacz to.
2. **„Gdzie/kiedy gra X?"** → `search "X"` → `showtimes --cinema-id <ID> --movie-id <MID> [--date ...]`.
3. **„Znajdź dobre miejsca"** → weź `presentation_id` → `find_best_seats.py --seats N`.
   Dla pełnego obrazu dodaj `--visualize-ascii` albo wygeneruj HTML (`--format html`) i pokaż plik.
4. **„Co warto zobaczyć / randka / wieczór"** → rekomenduj: sortuj po ocenie Filmweb
   (`--with-filmweb`), filtruj po dostępności dobrych miejsc (`--with-availability`) i dogodnej
   godzinie; w opisie dodaj gatunki i zwiastun (`film <KOD>`).
5. **„Ile kosztuje / czy da się zarezerwować?"** → `booking-preview --presentation-id <ID>`.

Wyniki seansów podawaj jako czytelną tabelę: godzina, film, format/język, sala, ID seansu.
Kluczowe godziny w formacie 24h. Daty zawsze pełne (np. 14 października 2026).

## Granice możliwości (mów wprost, nie kombinuj)

- **Kupno/zakup biletów: NIEZAIMPLEMENTOWANE** — kroki 5–8 flow rezerwacji (blokada miejsca,
  koszyk, płatność) wymagają researchu API. `booking-preview` pokazuje tylko podgląd (kroki 1–4).
- **Logowanie Unlimited wymaga tokena reCaptcha v3** (ważny ~2 min, instrukcje:
  `references/workflows.md`). Bez tokena nie zalogujesz; funkcje konta (`profile`, `bookings`,
  `favourites`, `payment-methods`, `constraints`) działają dopiero po `login --email ... --password ... --recaptcha-token ...`.
- Nie zgaduj ID kin/miejsc — pobieraj z `cinemas` / wyników komend.

## Szczegółowe workflow

Do scenariuszy specjalistycznych czytaj [references/workflows.md](references/workflows.md):
IMAX sweet-spot finder, mostek Filmweb→Cinema City (weryfikacja przed seansem),
analiza dla grup (N miejsc obok siebie), funkcje konta Unlimited, obsługa flag językowych
(lektor/napisy/dubbing).
