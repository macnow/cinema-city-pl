#!/usr/bin/env python3
"""
Cache Manager - zarządzanie cache'owaniem danych z API
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any, Dict


class CacheManager:
    """Manager do cache'owania danych z różnymi TTL"""

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Utwórz podkatalogi
        (self.cache_dir / "films").mkdir(exist_ok=True)
        (self.cache_dir / "filmweb").mkdir(exist_ok=True)
        (self.cache_dir / "seatplans").mkdir(exist_ok=True)
        (self.cache_dir / "dates").mkdir(exist_ok=True)
        (self.cache_dir / "showtimes").mkdir(exist_ok=True)

    def _get_cache_file(self, category: str, key: str) -> Path:
        """Zwróć ścieżkę do pliku cache"""
        if category in ["films", "filmweb", "seatplans", "dates", "showtimes"]:
            return self.cache_dir / category / f"{key}.json"
        else:
            return self.cache_dir / f"{key}.json"

    def _is_expired(self, timestamp: float, ttl_hours: int) -> bool:
        """Sprawdź czy cache wygasł"""
        cache_time = datetime.fromtimestamp(timestamp)
        expiry_time = cache_time + timedelta(hours=ttl_hours)
        return datetime.now() > expiry_time

    def get(self, category: str, key: str, ttl_hours: int = 24) -> Optional[Any]:
        """
        Pobierz dane z cache jeśli są świeże

        Args:
            category: Kategoria cache (films, filmweb, seatplans, dates, cinemas)
            key: Klucz (np. film_id, cinema_id)
            ttl_hours: Time to live w godzinach

        Returns:
            Dane z cache lub None jeśli brak/wygasły
        """
        cache_file = self._get_cache_file(category, key)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            timestamp = cached.get('timestamp', 0)

            # Sprawdź czy nie wygasł
            if self._is_expired(timestamp, ttl_hours):
                # Wygasł - usuń
                cache_file.unlink(missing_ok=True)
                return None

            return cached.get('data')

        except (json.JSONDecodeError, KeyError, OSError):
            # Uszkodzony cache - usuń
            cache_file.unlink(missing_ok=True)
            return None

    def set(self, category: str, key: str, data: Any) -> None:
        """
        Zapisz dane do cache

        Args:
            category: Kategoria cache
            key: Klucz
            data: Dane do zapisania
        """
        cache_file = self._get_cache_file(category, key)

        cached = {
            'timestamp': datetime.now().timestamp(),
            'data': data
        }

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)
        except OSError as e:
            # Błąd zapisu - nie krytyczny, po prostu pomijamy cache
            pass

    def get_filmweb(self, film_id: int, release_date: Optional[str] = None) -> Optional[Dict]:
        """
        Pobierz dane z Filmweb z inteligentnym TTL

        Args:
            film_id: ID filmu na Filmweb
            release_date: Data premiery filmu (YYYY-MM-DD)

        Returns:
            Dane z cache lub None
        """
        # Oblicz TTL na podstawie daty premiery
        ttl_hours = 24  # Domyślnie 24h

        if release_date:
            try:
                release = datetime.strptime(release_date, '%Y-%m-%d')
                days_since_release = (datetime.now() - release).days

                if days_since_release < 0:
                    # Film jeszcze nie miał premiery - cache na 7 dni
                    ttl_hours = 24 * 7
                elif days_since_release < 14:
                    # Nowy film (<2 tygodnie) - cache na 24h (oceny się zmieniają)
                    ttl_hours = 24
                else:
                    # Starszy film (>2 tygodnie) - cache na 7 dni (oceny stabilne)
                    ttl_hours = 24 * 7
            except ValueError:
                pass

        return self.get("filmweb", str(film_id), ttl_hours=ttl_hours)

    def set_filmweb(self, film_id: int, data: Dict) -> None:
        """Zapisz dane Filmweb do cache"""
        self.set("filmweb", str(film_id), data)

    def get_film(self, film_code: str) -> Optional[Dict]:
        """Pobierz szczegóły filmu z Cinema City (TTL: 24h)"""
        return self.get("films", film_code, ttl_hours=24)

    def set_film(self, film_code: str, data: Dict) -> None:
        """Zapisz szczegóły filmu do cache"""
        self.set("films", film_code, data)

    def get_seatplan(self, venue_id: str, seatplan_id: str) -> Optional[Dict]:
        """
        Pobierz plan sali (TTL: 30 dni - plany sal się nie zmieniają)
        """
        key = f"{venue_id}_{seatplan_id}"
        return self.get("seatplans", key, ttl_hours=24 * 30)

    def set_seatplan(self, venue_id: str, seatplan_id: str, data: Dict) -> None:
        """Zapisz plan sali do cache"""
        key = f"{venue_id}_{seatplan_id}"
        self.set("seatplans", key, data)

    def get_cinemas(self) -> Optional[list]:
        """Pobierz listę kin (TTL: 7 dni - kina rzadko się zmieniają)"""
        return self.get("cinemas", "list", ttl_hours=24 * 7)

    def set_cinemas(self, data: list) -> None:
        """Zapisz listę kin do cache"""
        self.set("cinemas", "list", data)

    def get_dates(self, cinema_id: str) -> Optional[list]:
        """Pobierz dostępne daty (TTL: 6h - aktualizowane często)"""
        return self.get("dates", cinema_id, ttl_hours=6)

    def set_dates(self, cinema_id: str, data: list) -> None:
        """Zapisz dostępne daty do cache"""
        self.set("dates", cinema_id, data)

    def get_showtimes(self, cinema_id: str, date: str, movie_id: Optional[str] = None) -> Optional[list]:
        """
        Pobierz seanse (TTL: 24h - repertuar stabilny po opublikowaniu)

        Args:
            cinema_id: ID kina
            date: Data (YYYY-MM-DD)
            movie_id: Opcjonalne ID filmu (None = wszystkie filmy)

        Returns:
            Lista seansów lub None jeśli brak/wygasły
        """
        key = f"{cinema_id}_{date}_{movie_id or 'all'}"
        return self.get("showtimes", key, ttl_hours=24)

    def set_showtimes(self, cinema_id: str, date: str, movie_id: Optional[str], data: list) -> None:
        """Zapisz seanse do cache"""
        key = f"{cinema_id}_{date}_{movie_id or 'all'}"
        self.set("showtimes", key, data)

    def clear_expired(self) -> int:
        """
        Usuń wszystkie wygasłe pliki cache

        Returns:
            Liczba usuniętych plików
        """
        removed = 0

        for cache_file in self.cache_dir.rglob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)

                timestamp = cached.get('timestamp', 0)

                # Sprawdź z domyślnym TTL 24h
                if self._is_expired(timestamp, 24):
                    cache_file.unlink()
                    removed += 1

            except (json.JSONDecodeError, KeyError, OSError):
                # Uszkodzony - usuń
                cache_file.unlink(missing_ok=True)
                removed += 1

        return removed

    def clear_all(self) -> int:
        """
        Usuń cały cache

        Returns:
            Liczba usuniętych plików
        """
        removed = 0

        for cache_file in self.cache_dir.rglob("*.json"):
            cache_file.unlink(missing_ok=True)
            removed += 1

        return removed

    def get_stats(self) -> Dict[str, int]:
        """
        Statystyki cache

        Returns:
            Dict z liczbą plików w każdej kategorii
        """
        stats = {
            'films': len(list((self.cache_dir / "films").glob("*.json"))),
            'filmweb': len(list((self.cache_dir / "filmweb").glob("*.json"))),
            'seatplans': len(list((self.cache_dir / "seatplans").glob("*.json"))),
            'dates': len(list((self.cache_dir / "dates").glob("*.json"))),
            'showtimes': len(list((self.cache_dir / "showtimes").glob("*.json"))),
            'other': len([f for f in self.cache_dir.glob("*.json")])
        }
        stats['total'] = sum(stats.values())
        return stats


# Singleton instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Pobierz globalny cache manager (singleton)"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


if __name__ == '__main__':
    # Test
    cache = CacheManager()

    # Test podstawowy
    cache.set("films", "test123", {"name": "Test Film", "year": 2025})
    result = cache.get("films", "test123")
    print(f"Test get/set: {result}")

    # Test Filmweb z różnymi TTL
    cache.set_filmweb(603081, {"rating": 7.1, "title": "Avatar"})

    # Nowy film - 24h
    fresh = cache.get_filmweb(603081, release_date="2025-12-19")
    print(f"Nowy film (24h TTL): {fresh}")

    # Stary film - 7 dni
    old = cache.get_filmweb(603081, release_date="2020-01-01")
    print(f"Stary film (7d TTL): {old}")

    # Statystyki
    stats = cache.get_stats()
    print(f"\nStatystyki cache: {stats}")
