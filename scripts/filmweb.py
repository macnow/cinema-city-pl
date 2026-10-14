#!/usr/bin/env python3
"""
Klient API Filmweb - wyszukiwanie filmów, oceny, informacje
"""

import requests
from typing import List, Dict, Optional
import urllib.parse
from cache_manager import get_cache_manager


class FilmwebClient:
    """Klient do API Filmweb"""

    BASE_URL = "https://www.filmweb.pl/api/v1"

    def __init__(self, use_cache: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            'accept': '*/*',
            'accept-language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
            'x-locale': 'pl_PL',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'referer': 'https://www.filmweb.pl/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
        })
        self.use_cache = use_cache
        self.cache = get_cache_manager() if use_cache else None

    def search(self, query: str, page_size: int = 12) -> List[Dict]:
        """
        Wyszukaj filmy na Filmweb

        Args:
            query: Zapytanie wyszukiwania (tytuł filmu)
            page_size: Liczba wyników (domyślnie 12)

        Returns:
            Lista słowników z informacjami o filmach
        """
        url = f"{self.BASE_URL}/live/search"
        params = {
            'query': query,
            'pageSize': page_size
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Wyciągnij tylko filmy (nie seriale, osoby, etc.)
            results = []
            search_hits = data.get('searchHits', [])

            for item in search_hits:
                if item.get('type') == 'film':
                    film_info = self._parse_film(item)
                    if film_info:
                        results.append(film_info)

            return results

        except requests.exceptions.RequestException as e:
            print(f"❌ Błąd podczas wyszukiwania na Filmweb: {e}")
            return []

    def _parse_film(self, item: Dict) -> Optional[Dict]:
        """
        Parsuj dane filmu z odpowiedzi API

        Args:
            item: Surowe dane z API

        Returns:
            Słownik z przetworzonymi informacjami o filmie
        """
        try:
            # Podstawowe info z search API (ograniczone dane)
            film_id = item.get('id')
            title = item.get('matchedTitle', 'Nieznany tytuł')
            matched_lang = item.get('matchedLang')

            # Obsada (jeśli dostępna)
            cast = []
            if 'filmMainCast' in item:
                cast = [actor.get('name') for actor in item['filmMainCast'] if actor.get('name')]

            # URL do strony filmu
            filmweb_url = f"https://www.filmweb.pl/film/{film_id}"

            return {
                'id': film_id,
                'title': title,
                'matched_lang': matched_lang,
                'cast': cast[:3],  # Pierwsze 3 osoby z obsady
                'filmweb_url': filmweb_url,
                'type': 'film'
            }

        except Exception as e:
            print(f"⚠️  Błąd parsowania filmu: {e}")
            return None

    def get_film_details(self, film_id: int, release_date: Optional[str] = None) -> Optional[Dict]:
        """
        Pobierz szczegółowe informacje o filmie

        Args:
            film_id: ID filmu na Filmweb
            release_date: Opcjonalna data premiery (YYYY-MM-DD) dla smart TTL

        Returns:
            Słownik ze szczegółowymi informacjami (tytuł, rok, ocena, poster)
        """
        # Sprawdź cache (smart TTL: 24h dla nowych filmów, 7d dla starszych)
        if self.use_cache and self.cache:
            cached = self.cache.get_filmweb(film_id, release_date)
            if cached:
                return cached

        try:
            # Podstawowe info
            info_url = f"{self.BASE_URL}/film/{film_id}/info"
            info_response = self.session.get(info_url, timeout=10)
            info_response.raise_for_status()
            info_data = info_response.json()

            # Oceny
            rating_url = f"{self.BASE_URL}/film/{film_id}/rating"
            rating_response = self.session.get(rating_url, timeout=10)
            rating_response.raise_for_status()
            rating_data = rating_response.json()

            # Połącz dane
            details = {
                'id': film_id,
                'title': info_data.get('title'),
                'original_title': info_data.get('originalTitle'),
                'year': info_data.get('year'),
                'type': info_data.get('type'),
                'sub_type': info_data.get('subType'),
                'poster_path': info_data.get('posterPath'),
                'poster_url': f"https://fwcdn.pl/fpo{info_data.get('posterPath')}" if info_data.get('posterPath') else None,
                'rating': rating_data.get('rate'),
                'rating_count': rating_data.get('count'),
                'want_to_see_count': rating_data.get('countWantToSee'),
                'filmweb_url': f"https://www.filmweb.pl/film/{film_id}"
            }

            # Zapisz w cache
            if self.use_cache and self.cache:
                self.cache.set_filmweb(film_id, details)

            return details

        except requests.exceptions.RequestException as e:
            print(f"❌ Błąd podczas pobierania szczegółów filmu {film_id}: {e}")
            return None

    def search_by_title_year(self, title: str, year: int, page_size: int = 12) -> List[Dict]:
        """
        Wyszukaj film po tytule i roku (bardziej precyzyjne)

        Args:
            title: Tytuł filmu
            year: Rok produkcji
            page_size: Liczba wyników do pobrania

        Returns:
            Lista filmów z danego roku, posortowana według trafności
        """
        # Wyszukaj po tytule + rok
        query = f"{title} {year}"
        search_results = self.search(query, page_size=page_size)

        # Pobierz szczegóły dla każdego wyniku i filtruj po roku
        detailed_results = []
        for film in search_results:
            details = self.get_film_details(film['id'])
            if details and details.get('year') == year:
                detailed_results.append(details)

        return detailed_results


if __name__ == '__main__':
    # Test
    import sys

    if len(sys.argv) < 2:
        print("Użycie: python3 filmweb.py <zapytanie>")
        print("Przykład: python3 filmweb.py 'Avatar 2024'")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])

    client = FilmwebClient()
    results = client.search(query)

    print(f"\n🎬 Wyniki wyszukiwania dla: '{query}'")
    print(f"Znaleziono: {len(results)} filmów\n")
    print("=" * 80)

    for i, film in enumerate(results, 1):
        title = film['title']
        matched_lang = film.get('matched_lang', '')
        cast = film.get('cast', [])
        film_id = film.get('id')

        print(f"\n{i}. {title}")
        if matched_lang:
            print(f"   Język: {matched_lang}")

        if cast:
            print(f"   Obsada: {', '.join(cast)}")

        print(f"   🆔 Film ID: {film_id}")
        print(f"   🔗 {film['filmweb_url']}")

    print("\n" + "=" * 80)
