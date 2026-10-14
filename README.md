# cinema-city-pl

Skill/CLI dla agentów AI do obsługi **Cinema City Polska** (publiczne API): kina, repertuar, seanse, formaty (IMAX, 4DX, ScreenX, 3D, VIP, Dolby Atmos), wersje językowe, dostępność i najlepsze miejsca z mapą sali (ASCII/PNG/HTML), podgląd cennika, oceny z Filmwebu.

## Setup

```bash
git clone https://github.com/macnow/cinema-city-pl.git
cd cinema-city-pl
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
.venv/bin/python3 scripts/main.py cinemas
```

## Komendy (przykłady)

```bash
.venv/bin/python3 scripts/main.py movies --cinema-id 1097            # 1097 = Wrocław Wroclavia
.venv/bin/python3 scripts/main.py showtimes --cinema-id 1097 --with-filmweb
.venv/bin/python3 scripts/main.py search "tytuł"
.venv/bin/python3 scripts/find_best_seats.py --presentation-id <ID> --seats 2 --visualize-ascii
.venv/bin/python3 scripts/main.py visualize --presentation-id <ID> --format html --output sala.html
.venv/bin/python3 scripts/main.py booking-preview --presentation-id <ID>
```

Pełny opis dla agenta: [SKILL.md](SKILL.md), scenariusze: [references/workflows.md](references/workflows.md).

## Ograniczenia

- Brak zakupu biletów i blokady miejsc (tylko podgląd rezerwacji: seans, sala, dostępność, cennik).
- Logowanie do konta Unlimited wymaga świeżego tokena reCaptcha v3 (~2 min ważności).
- Nieoficjalne narzędzie, niezwiązane z Cinema City.
