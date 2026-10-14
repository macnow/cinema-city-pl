# Workflow specjalistyczne — Cinema City PL

Kod jest związany ze skillem: `scripts/` obok SKILL.md. Ustaw `PY` i katalog roboczy
zgodnie z sekcją „Zasada zero-setup" w SKILL.md; poniżej `python3 main.py` = `"$PY" scripts/main.py`.

## Spis treści
1. IMAX sweet-spot finder
2. Filmweb → Cinema City (weryfikacja przed seansem)
3. Miejsca dla grupy (N miejsc obok siebie)
4. Interpretacja flag językowych i formatów
5. Konto Unlimited (logowanie, funkcje, granice)
6. Tłumienie błędów i diagnostyka

## 1. IMAX sweet-spot finder

Gdy użytkownik chce seansu IMAX z najlepszymi miejscami:

```bash
.venv/bin/python3 scripts/main.py showtimes --cinema-id <ID> | grep -i imax   # znajdź seanse IMAX
.venv/bin/python3 find_best_seats.py --presentation-id <PID> --seats <N> --visualize-ascii
```

- Priorytet: rzędy 9–10 (~66–75% wysokości sali; optimum ~70%).
- Ranking seansów: dostępność miejsc w sweet spocie > godzina > cena.
- W rekomendacji wyjaśnij krótko czemu rzędy 9–10 (ekran wypełnia pole widzenia bez konieczności odchylania głowy).

## 2. Filmweb → Cinema City

Użytkownik zna tytuł (może nieprecyzyjny) — zweryfikuj zanim pokażesz seanse:

```bash
.venv/bin/python3 scripts/main.py filmweb "tytuł" --details        # ocena, rok, obsada
.venv/bin/python3 scripts/main.py search "dokładny tytuł"          # → movie ID
.venv/bin/python3 scripts/main.py showtimes --cinema-id <ID> --movie-id <MID> --with-filmweb
```

- Rok produkcji rozróżnia remake/sequele/oryginały (`filmweb --year RRRR`).
- W podsumowaniu: ocena Filmweb + gatunki + link do zwiastuna z `film <KOD>`.

## 3. Miejsca dla grupy

- `--seats N` w `find_best_seats.py` i `quick_search.py` szuka N **sąsiadujących** miejsc.
- Jeśli brak grup obok siebie, pokaż najbliższe alternatywy (2+2 w tym samym rzędzie) i powiedz wprost.
- Duże grupy (6+): sprawdź dostępność (`--with-availability`) zanim zaproponujesz seans.

## 4. Flagi językowe i formaty

- `NAPISY` = Oryginalna ścieżka + napisy PL; `LEKTOR` = lektor PL; `DUBBING` = dubbing PL (typowo filmy familijne).
- Formaty: 2D/3D, IMAX (także IMAX 3D), 4DX (ruchome fotele, efekty — pytaj o wrażliwość na ruch), ScreenX (ekrany boczne), Dolby Atmos = dźwięk, nie format obrazu.
- Gdy użytkownik prosi o „oryginał/VO", filtruj po NAPISY i potwierdź, że to nie jest 4DX/ScreenX jeśli nie prosił.

## 5. Konto Unlimited

Logowanie — token reCaptcha v3 jest ZAWSZE wymagany:

```bash
# Token z przeglądarki (DevTools → Network → oauth/token?reCaptcha=...) — ważny ~2 min.
# Metoda automatyczna: .venv/bin/python3 scripts/recaptcha_helper.py <email> <hasło>
.venv/bin/python3 scripts/main.py login --email <E> --password <P> --recaptcha-token <TOKEN>
```

Po zalogowaniu: `profile`, `bookings [--time PAST] [--booking-id N]`, `favourites`,
`constraints`, `payment-methods`, `set-favourite-cinema --cinema-id <ID>`,
`update-consents --marketing --premium`. Token dostępu w sesji; refresh flow nie jest zaimplementowany — przy wygasnięciu zaloguj ponownie.

**Granice:** nie da się kupić biletu (brak kroków 5–8), nie zmienisz danych wymagających reCaptcha bez świeżego tokena.

## 6. Diagnostyka

- `ModuleNotFoundError` → używasz złego Pythona; użyj `.venv/bin/python3`.
- Pusta lista seansów na datę → sprawdź `dates --cinema-id <ID>` zamiast zgadywać.
- 4xx/5xx z API → odczekaj i powtórz; przy trwałym błędzie endpointu odnotuj w odpowiedzi (API Cinema City bywa niestabilne poza godzinami szczytu).
- Lista kin zmienia się w czasie (nowe kina) — zawsze bierz z `cinemas`, nie z pamięci/README.
