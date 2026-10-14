"""
Cinema City API Client
Handles all HTTP requests to Cinema City API
"""
import requests
import base64
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .cinemas_mapping import get_cinema_info, get_all_cinemas
from cache_manager import get_cache_manager


class CinemaCityClient:
    """Client for Cinema City Poland API"""

    BASE_URL = "https://www.cinema-city.pl"
    API_BASE = "https://www.cinema-city.pl/pl/data-api-service/v1"
    CUSTOMER_API_BASE = "https://www.cinema-city.pl/pl/group-customer-service/v1"
    BOOKING_API_BASE = "https://www.cinema-city.pl/pl/booking-router"
    TICKETS_API_BASE = "https://tickets.cinema-city.pl/api"
    QUICKBOOK_ID = "10103"  # ID dla quickbook API

    def __init__(self, use_cache: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self.auth_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.use_cache = use_cache
        self.cache = get_cache_manager() if use_cache else None
        self.booking_session_id: Optional[str] = None  # Session ID dla rezerwacji
        self.booking_uuid: Optional[str] = None  # UUID dla rezerwacji

    def get_cinemas(self, use_api: bool = True) -> List[Dict]:
        """
        Pobierz listę dostępnych kin

        Args:
            use_api: Jeśli True, pobierz z API; jeśli False, użyj lokalnego mapowania

        Returns:
            Lista kin z nazwami, miastami i adresami
        """
        if use_api:
            return self.get_cinemas_from_api()
        else:
            return get_all_cinemas()

    def get_cinemas_from_api(self, days_ahead: int = 365) -> List[Dict]:
        """
        Pobierz listę kin z API (kina które mają seanse w najbliższym czasie)

        Args:
            days_ahead: Ile dni do przodu sprawdzić (domyślnie rok)

        Returns:
            Lista kin ze szczegółami
        """
        # Sprawdź cache (TTL: 7 dni)
        if self.use_cache and self.cache:
            cached = self.cache.get_cinemas()
            if cached:
                return cached

        from datetime import datetime, timedelta

        until_date = (datetime.now() + timedelta(days=days_ahead)).date()
        url = f"{self.API_BASE}/quickbook/{self.QUICKBOOK_ID}/cinemas/with-event/until/{until_date}"

        params = {
            'attr': '',
            'lang': 'pl_PL'
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        cinemas_raw = data.get('body', {}).get('cinemas', [])

        # Formatuj dane
        cinemas = []
        for cinema in cinemas_raw:
            addr = cinema.get('addressInfo', {})
            cinemas.append({
                'id': cinema['id'],
                'name': cinema['displayName'],
                'city': addr.get('city', ''),
                'address': addr.get('address1', ''),
                'postal_code': addr.get('postalCode', ''),
                'latitude': cinema.get('latitude'),
                'longitude': cinema.get('longitude'),
                'link': cinema.get('link', ''),
                'image_url': cinema.get('imageUrl', ''),
            })

        # Sortuj po nazwie
        cinemas = sorted(cinemas, key=lambda x: x['name'])

        # Zapisz do cache
        if self.use_cache and self.cache:
            self.cache.set_cinemas(cinemas)

        return cinemas

    def get_available_dates(self, cinema_id: str, days_ahead: int = 365) -> List[str]:
        """
        Pobierz dostępne daty z seansami dla danego kina

        Args:
            cinema_id: ID kina
            days_ahead: Ile dni do przodu sprawdzić (domyślnie rok)

        Returns:
            Lista dat w formacie YYYY-MM-DD
        """
        # Sprawdź cache (TTL: 6h - aktualizowane często)
        if self.use_cache and self.cache:
            cached = self.cache.get_dates(cinema_id)
            if cached:
                return cached

        until_date = (datetime.now() + timedelta(days=days_ahead)).date()
        url = f"{self.API_BASE}/quickbook/{self.QUICKBOOK_ID}/dates/in-cinema/{cinema_id}/until/{until_date}"

        params = {
            'attr': '',
            'lang': 'pl_PL'
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        dates = data.get('body', {}).get('dates', [])

        # Zapisz w cache
        if self.use_cache and self.cache:
            self.cache.set_dates(cinema_id, dates)

        return dates

    def get_movies(self, cinema_id: str, date: str = None) -> List[Dict]:
        """
        Pobierz repertuar filmów dla danego kina na konkretną datę

        Args:
            cinema_id: ID kina
            date: Data w formacie YYYY-MM-DD (domyślnie dziś)

        Returns:
            Lista filmów z informacjami
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        url = f"{self.API_BASE}/quickbook/{self.QUICKBOOK_ID}/film-events/in-cinema/{cinema_id}/at-date/{date}"

        params = {
            'attr': '',
            'lang': 'pl_PL'
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        films = data.get('body', {}).get('films', [])

        # Formatuj dane filmów
        movies = []
        for film in films:
            movies.append({
                'id': film['id'].upper(),
                'title': film['name'],
                'duration': film['length'],
                'year': film.get('releaseYear'),
                'rating': film.get('posterLink', ''),  # Rating nie jest w API, trzeba z Filmweb
                'link': film.get('link'),
                'video_link': film.get('videoLink'),
            })

        return movies

    def get_film_details(self, film_code: str) -> Dict:
        """
        Pobierz szczegółowe informacje o filmie po kodzie dystrybutora

        Args:
            film_code: Kod dystrybutora filmu (np. '7650S2R')

        Returns:
            Dict ze szczegółowymi informacjami o filmie
        """
        # Sprawdź cache (TTL: 24h)
        if self.use_cache and self.cache:
            cached = self.cache.get_film(film_code)
            if cached:
                return cached

        url = f"{self.API_BASE}/{self.QUICKBOOK_ID}/films/byDistributorCode/{film_code}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            result = data.get('body', {})

            # Zapisz do cache
            if self.use_cache and self.cache:
                self.cache.set_film(film_code, result)

            return result
        except Exception as e:
            raise Exception(f"Błąd pobierania szczegółów filmu: {str(e)}")

    def get_showtimes(self, cinema_id: str, movie_id: str = None, date: str = None) -> List[Dict]:
        """
        Pobierz seanse dla danego kina (opcjonalnie filtrowane po filmie)

        Args:
            cinema_id: ID kina
            movie_id: ID filmu (opcjonalne - jeśli None, zwraca wszystkie seanse)
            date: Data w formacie YYYY-MM-DD (domyślnie dziś)

        Returns:
            Lista seansów z nazwami filmów
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # Sprawdź cache (TTL: 24h - repertuar stabilny po opublikowaniu)
        if self.use_cache and self.cache:
            cached = self.cache.get_showtimes(cinema_id, date, movie_id)
            if cached:
                return cached

        url = f"{self.API_BASE}/quickbook/{self.QUICKBOOK_ID}/film-events/in-cinema/{cinema_id}/at-date/{date}"

        params = {
            'attr': '',
            'lang': 'pl_PL'
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        events = data.get('body', {}).get('events', [])
        films = data.get('body', {}).get('films', [])

        # Stwórz mapowanie ID filmu -> nazwa
        film_names = {film['id'].upper(): film['name'] for film in films}

        # Formatuj dane seansów
        showtimes = []
        for event in events:
            # Jeśli podano movie_id, filtruj tylko ten film
            if movie_id and event['filmId'].upper() != movie_id.upper():
                continue

            attr_ids = event.get('attributeIds', [])
            attr_str = ','.join(attr_ids)

            film_id = event['filmId'].upper()
            movie_name = film_names.get(film_id, event.get('filmName', 'Nieznany'))

            showtimes.append({
                'id': event['id'],
                'cinema_id': event['cinemaId'],
                'movie_id': film_id,
                'movie_name': movie_name,
                'date': event['eventDateTime'],
                'time': event['eventDateTime'].split('T')[1][:5],  # HH:MM
                'screen': str(event.get('auditorium', '')).replace('Sala ', '').zfill(2),
                'booking_link': event.get('bookingLink'),
                'sold_out': event.get('soldOut', False),
                # Atrybuty seansu
                'attributes': attr_ids,
                'imax': 'imax' in attr_str.lower(),
                '3d': '3d' in attr_str.lower(),
                'vip': 'vip' in attr_str.lower(),
                '4dx': '4dx' in attr_str.lower(),
                'screenx': 'screenx' in attr_str.lower(),
                'subtitles': 'subbed' in attr_str.lower(),
                'dubbing': 'dubbed' in attr_str.lower(),
            })

        # Zapisz w cache
        if self.use_cache and self.cache:
            self.cache.set_showtimes(cinema_id, date, movie_id, showtimes)

        return showtimes

    def search_movie(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Wyszukaj film po nazwie

        Args:
            query: Nazwa filmu
            max_results: Maksymalna liczba wyników

        Returns:
            Lista filmów
        """
        url = f"{self.BASE_URL}/q"

        params = {
            'q': query,
            'start': 0,
            'max': max_results,
            'json': 1
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        return data.get('feats', [])

    def get_feed_categories(self) -> List[Dict]:
        """
        Pobierz dostępne kategorie feedów (teraz grane, wkrótce, etc.)

        Returns:
            Lista kategorii z kluczami i placements
        """
        url = f"{self.API_BASE}/feed/{self.QUICKBOOK_ID}/allFeedNames"

        response = self.session.get(url)
        response.raise_for_status()
        data = response.json()

        return data.get('body', [])

    def get_feed(self, feed_name: str) -> List[Dict]:
        """
        Pobierz filmy z konkretnego feeda

        Args:
            feed_name: Nazwa feeda (np. 'now-playing', 'coming-soon', 'oscar-nominees')

        Returns:
            Lista filmów z plakatami i szczegółami
        """
        url = f"{self.API_BASE}/feed/{self.QUICKBOOK_ID}/byName/{feed_name}"

        params = {'lang': 'pl_PL'}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        posters = data.get('body', {}).get('posters', [])

        # Formatuj dane
        movies = []
        for poster in posters:
            movies.append({
                'id': poster.get('code', '').upper(),
                'title': poster.get('featureTitle'),
                'poster_url': poster.get('posterSrc'),
                'url': poster.get('url'),
                'date_started': poster.get('dateStarted'),
                'attributes': poster.get('attributes', []),
                'weight': poster.get('weight', 0),  # Priorytet wyświetlania
            })

        return movies

    def login(self, email: str, password: str, recaptcha_token: str = None) -> Dict:
        """
        Zaloguj się do Cinema City Unlimited używając OAuth2 password grant

        Args:
            email: Email konta Unlimited
            password: Hasło konta Unlimited
            recaptcha_token: Token reCaptcha v3 (opcjonalny, ale może być wymagany przez API)

        Returns:
            Dict z danymi autentykacji lub None jeśli błąd
        """
        url = f"{self.BASE_URL}/pl/group-customer-service/oauth/token"

        # Basic Auth credentials dla Cinema City website client
        client_id = "website"
        client_secret = "website-password"
        basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        # Dodaj reCaptcha token do URL jeśli podany
        if recaptcha_token:
            url += f"?reCaptcha={recaptcha_token}"

        headers = {
            'Authorization': f'Basic {basic_auth}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Origin': 'https://www.cinema-city.pl',
            'Referer': 'https://www.cinema-city.pl/konto',
        }

        data = {
            'grant_type': 'password',
            'username': email,
            'password': password
        }

        try:
            response = self.session.post(url, headers=headers, data=data)
            response.raise_for_status()

            auth_data = response.json()

            # Zapisz tokeny
            self.auth_token = auth_data.get('access_token')
            self.refresh_token = auth_data.get('refresh_token')

            # Dodaj access token do domyślnych headerów sesji
            if self.auth_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })

            return auth_data

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f": {error_data.get('error_description', error_data.get('error', str(error_data)))}"
            except:
                error_msg += f": {e.response.text[:200]}"

            raise Exception(error_msg)
        except Exception as e:
            raise Exception(f"Błąd logowania: {str(e)}")

    def get_current_user(self) -> Dict:
        """
        Pobierz informacje o zalogowanym użytkowniku
        Wymaga wcześniejszego zalogowania (Bearer token)

        Returns:
            Dict z danymi użytkownika
        """
        if not self.auth_token:
            raise Exception("Musisz się najpierw zalogować (użyj metody login())")

        url = f"{self.CUSTOMER_API_BASE}/customers/current"

        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Accept': 'application/json'
        }

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd pobierania danych użytkownika: {str(e)}")

    def update_profile(self, profile_data: Dict, recaptcha_token: str = None) -> Dict:
        """
        Zaktualizuj profil użytkownika
        Wymaga wcześniejszego zalogowania (Bearer token)

        Args:
            profile_data: Dict z danymi do zaktualizowania (pełny profil z GET /customers/current)
            recaptcha_token: Token reCaptcha v3 (opcjonalny, ale może być wymagany)

        Returns:
            Dict ze zaktualizowanymi danymi użytkownika

        Example:
            # Pobierz aktualny profil
            profile = client.get_current_user()
            # Zmień imię
            profile['firstName'] = 'Nowe Imię'
            # Zaktualizuj
            updated = client.update_profile(profile, recaptcha_token="...")
        """
        if not self.auth_token:
            raise Exception("Musisz się najpierw zalogować (użyj metody login())")

        url = f"{self.CUSTOMER_API_BASE}/customers/current"

        # Dodaj reCaptcha token do body jeśli podany
        if recaptcha_token:
            profile_data['recaptcha'] = recaptcha_token

        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json;charset=UTF-8',
            'Accept': 'application/json'
        }

        try:
            response = self.session.put(url, headers=headers, json=profile_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f": {error_data.get('error_description', error_data.get('error', str(error_data)))}"
            except:
                error_msg += f": {e.response.text[:200]}"
            raise Exception(error_msg)
        except Exception as e:
            raise Exception(f"Błąd aktualizacji profilu: {str(e)}")

    def update_favourite_cinema(self, cinema_id: str, recaptcha_token: str = None) -> Dict:
        """
        Zaktualizuj ulubione kino użytkownika (helper method)

        Args:
            cinema_id: ID kina do ustawienia jako ulubione
            recaptcha_token: Token reCaptcha v3 (opcjonalny)

        Returns:
            Dict ze zaktualizowanym profilem
        """
        profile = self.get_current_user()
        profile['favouriteCinemaId'] = cinema_id
        return self.update_profile(profile, recaptcha_token)

    def update_consents(self, marketing: bool = None, premium_marketing: bool = None,
                       recaptcha_token: str = None) -> Dict:
        """
        Zaktualizuj zgody marketingowe (helper method)

        Args:
            marketing: Zgoda na marketing (opcjonalne)
            premium_marketing: Zgoda na premium marketing (opcjonalne)
            recaptcha_token: Token reCaptcha v3 (opcjonalny)

        Returns:
            Dict ze zaktualizowanym profilem
        """
        profile = self.get_current_user()

        if marketing is not None:
            profile.setdefault('consents', {})['marketingConsent'] = marketing
        if premium_marketing is not None:
            profile.setdefault('consents', {})['premiumMarketingConsent'] = premium_marketing

        return self.update_profile(profile, recaptcha_token)

    def get_bookings(self, time_filter: str = "FUTURE") -> List[Dict]:
        """
        Pobierz rezerwacje użytkownika
        Wymaga wcześniejszego zalogowania (Bearer token)

        Args:
            time_filter: 'FUTURE' dla przyszłych, 'PAST' dla historycznych

        Returns:
            Lista rezerwacji
        """
        if not self.auth_token:
            raise Exception("Musisz się najpierw zalogować (użyj metody login())")

        url = f"{self.CUSTOMER_API_BASE}/bookings"

        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Accept': 'application/json'
        }

        params = {'time': time_filter}

        try:
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get('bookings', [])
        except Exception as e:
            raise Exception(f"Błąd pobierania rezerwacji: {str(e)}")

    def get_booking_details(self, booking_id: str) -> Dict:
        """
        Pobierz szczegóły konkretnej rezerwacji po ID
        Wymaga wcześniejszego zalogowania (Bearer token)

        Args:
            booking_id: ID rezerwacji

        Returns:
            Dict ze szczegółami rezerwacji
        """
        if not self.auth_token:
            raise Exception("Musisz się najpierw zalogować (użyj metody login())")

        url = f"{self.CUSTOMER_API_BASE}/bookings/{booking_id}"

        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Accept': 'application/json'
        }

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd pobierania szczegółów rezerwacji: {str(e)}")

    def get_favourite_cinemas(self) -> List[Dict]:
        """
        Pobierz ulubione kina użytkownika
        Wymaga cookies z sesji (accessToken w cookie)

        Returns:
            Lista ulubionych kin
        """
        url = f"{self.CUSTOMER_API_BASE}/favourite_cinemas"

        # Ten endpoint używa Basic Auth zamiast Bearer
        client_id = "website"
        client_secret = "website-password"
        basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        headers = {
            'Authorization': f'Basic {basic_auth}',
            'Accept': 'application/json'
        }

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get('cinemas', [])
        except Exception as e:
            raise Exception(f"Błąd pobierania ulubionych kin: {str(e)}")

    def get_customer_constraints(self) -> Dict:
        """
        Pobierz ograniczenia konta użytkownika (limity Unlimited, etc.)
        Wymaga cookies z sesji

        Returns:
            Dict z ograniczeniami konta
        """
        url = f"{self.CUSTOMER_API_BASE}/customer_constraints"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd pobierania ograniczeń konta: {str(e)}")

    def get_signup_options(self) -> List[Dict]:
        """
        Pobierz dostępne opcje subskrypcji/pakietów Unlimited

        Returns:
            Lista opcji subskrypcji
        """
        url = f"{self.CUSTOMER_API_BASE}/signup_options"

        # Ten endpoint używa Basic Auth
        client_id = "website"
        client_secret = "website-password"
        basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        headers = {
            'Authorization': f'Basic {basic_auth}',
            'Accept': 'application/json'
        }

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get('options', [])
        except Exception as e:
            raise Exception(f"Błąd pobierania opcji subskrypcji: {str(e)}")

    def get_payment_methods(self) -> List[Dict]:
        """
        Pobierz zapisane metody płatności użytkownika
        Wymaga wcześniejszego zalogowania (Bearer token)

        Returns:
            Lista metod płatności
        """
        if not self.auth_token:
            raise Exception("Musisz się najpierw zalogować (użyj metody login())")

        url = f"{self.CUSTOMER_API_BASE}/payment_methods"

        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Accept': 'application/json'
        }

        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get('paymentMethods', [])
        except Exception as e:
            raise Exception(f"Błąd pobierania metod płatności: {str(e)}")

    def get_movies_by_showing_type(self, showing_type: str = "SHOWING",
                                    cinema_id: str = None, ordering: str = "desc") -> List[Dict]:
        """
        Pobierz filmy według typu wyświetlania (obecnie grane, wkrótce, etc.)

        Args:
            showing_type: Typ wyświetlania (SHOWING, COMING_SOON, etc.)
            cinema_id: ID kina do filtrowania (opcjonalne)
            ordering: Kolejność sortowania (desc/asc)

        Returns:
            Lista plakatów filmów
        """
        url = f"{self.API_BASE}/poster/{self.QUICKBOOK_ID}/by-showing-type/{showing_type}"

        params = {
            'lang': 'pl_PL',
            'ordering': ordering
        }

        if cinema_id:
            params['cinemaId'] = cinema_id

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('body', {}).get('posters', [])
        except Exception as e:
            raise Exception(f"Błąd pobierania filmów: {str(e)}")

    def _generate_booking_uuid(self) -> str:
        """Generuj UUID dla sesji rezerwacji"""
        import uuid
        return str(uuid.uuid4())

    def get_presentation_details(self, presentation_id: str) -> Dict:
        """
        Pobierz szczegóły prezentacji/seansu (krok 4 flow)

        Args:
            presentation_id: ID prezentacji

        Returns:
            Dict ze szczegółami seansu (film, data, sala, venueId, seatplanId, etc.)
        """
        url = f"{self.TICKETS_API_BASE}/presentations/{presentation_id}"
        params = {'referralMiniSiteId': 0}

        # Generuj UUID jeśli nie ma
        if not self.booking_uuid:
            self.booking_uuid = self._generate_booking_uuid()

        headers = {'uuid': self.booking_uuid}

        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd pobierania szczegółów seansu: {str(e)}")

    def get_seat_plan(self, venue_id: str, seatplan_id: str) -> Dict:
        """
        Pobierz plan sali (krok 5 flow)

        Args:
            venue_id: ID miejsca/kina
            seatplan_id: ID planu sali

        Returns:
            Dict z layoutem sali i miejscami
        """
        # Sprawdź cache (TTL: 30 dni - plany sal nie zmieniają się)
        if self.use_cache and self.cache:
            cached = self.cache.get_seatplan(venue_id, seatplan_id)
            if cached:
                return cached

        url = f"{self.TICKETS_API_BASE}/seats/seatplanV2"
        params = {
            'venueId': venue_id,
            'seatplanId': seatplan_id
        }

        headers = {'uuid': self.booking_uuid}

        try:
            response = self.session.post(url, params=params, headers=headers, json={})
            response.raise_for_status()
            result = response.json()

            # Zapisz w cache
            if self.use_cache and self.cache:
                self.cache.set_seatplan(venue_id, seatplan_id, result)

            return result
        except Exception as e:
            raise Exception(f"Błąd pobierania planu sali: {str(e)}")

    def get_seats_status(self, presentation_id: str, venue_type_id: int = 1) -> Dict:
        """
        Pobierz status miejsc (zajęte/wolne) (krok 6 flow)

        Args:
            presentation_id: ID prezentacji
            venue_type_id: Typ miejsca (domyślnie 1)

        Returns:
            Dict ze statusem miejsc
        """
        url = f"{self.TICKETS_API_BASE}/seats/seats-statusV2"
        params = {
            'presentationId': presentation_id,
            'venueTypeId': venue_type_id,
            'isReserved': 1
        }

        headers = {
            'uuid': self.booking_uuid,
            'Origin': 'https://www.cinema-city.pl',
            'Referer': 'https://www.cinema-city.pl/'
        }

        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd pobierania statusu miejsc: {str(e)}")

    def get_ticket_groups(self, presentation_id: str) -> List[Dict]:
        """
        Pobierz dostępne grupy biletów i ceny (krok 7 flow)

        Args:
            presentation_id: ID prezentacji

        Returns:
            Lista grup biletów z cenami
        """
        url = f"{self.TICKETS_API_BASE}/presentations/{presentation_id}/ticketGroups"
        params = {
            'membershipLoyaltyId': 0,
            'referralMiniSiteId': 0
        }

        headers = {'uuid': self.booking_uuid}

        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd pobierania grup biletów: {str(e)}")

    def create_cart_token(self, recaptcha_token: str) -> Dict:
        """
        Utwórz token koszyka (krok 8 flow)

        Args:
            recaptcha_token: Token reCaptcha v3

        Returns:
            Dict z tokenem koszyka
        """
        url = f"{self.TICKETS_API_BASE}/cart/token"

        headers = {
            'uuid': self.booking_uuid,
            'Content-Type': 'application/json'
        }

        data = {'recaptchaToken': recaptcha_token}

        try:
            response = self.session.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd tworzenia tokenu koszyka: {str(e)}")

    def lock_seat(self, presentation_id: int, venue_id: int, seatplan_id: int,
                 section_id: str, ticket_group_id: int,
                 x_coordinate: str, y_coordinate: str) -> Dict:
        """
        Zablokuj wybrane miejsce (krok 9 flow)

        Args:
            presentation_id: ID prezentacji
            venue_id: ID miejsca/kina
            seatplan_id: ID planu sali
            section_id: ID sekcji
            ticket_group_id: ID grupy biletów
            x_coordinate: Współrzędna X miejsca
            y_coordinate: Współrzędna Y miejsca

        Returns:
            Dict z potwierdzeniem blokady miejsca
        """
        url = f"{self.TICKETS_API_BASE}/seats/lock-seat"

        headers = {
            'uuid': self.booking_uuid,
            'Content-Type': 'application/json'
        }

        data = {
            'recaptchaToken': None,
            'seat': {
                'PresentationId': presentation_id,
                'VenueId': venue_id,
                'VenueSeatplanId': seatplan_id,
                'VenueSectionId': section_id,
                'TicketGroupId': ticket_group_id,
                'XCoordinate': x_coordinate,
                'YCoordinate': y_coordinate
            }
        }

        try:
            response = self.session.put(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd blokowania miejsca: {str(e)}")

    def add_to_cart(self, presentations: List[Dict], vouchers: List[Dict] = None) -> Dict:
        """
        Dodaj miejsca do koszyka i sfinalizuj wybór (krok 10 flow)

        Args:
            presentations: Lista miejsc z informacjami o biletach
            vouchers: Lista voucherów (opcjonalne)

        Returns:
            Dict z potwierdzeniem koszyka

        Example presentation item:
        {
            "XCoordinate": "8",
            "YCoordinate": "2",
            "RowName": "2",
            "SeatName": "8",
            "isFirstAddonSelected": false,
            "ticket": {
                "prsntId": 1216396,
                "ticketGroupId": 1,
                "venueId": 379,
                "seatplanId": 1,
                "sectionId": "1",
                "ticketId": 16,
                "membershipLoyaltyId": 0,
                "membershipLoyaltyTicketId": 0,
                "amount": 0,
                "serviceCharge": 0,
                "pricePolicyId": null,
                "allocationId": 0,
                "code": "2946973839",  # Unlimited card number
                "oldPrice": 0,
                "selectedAddons": [],
                "discountId": null,
                "appliedDiscount": 0,
                "systemVoucher": "uuid"  # For Unlimited
            },
            "seatModifiers": []
        }
        """
        url = f"{self.TICKETS_API_BASE}/cart"

        headers = {
            'uuid': self.booking_uuid,
            'Content-Type': 'application/json'
        }

        data = {
            'cart': {
                'presentations': presentations,
                'vouchers': vouchers or []
            },
            'uuid': self.booking_uuid
        }

        try:
            response = self.session.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Błąd dodawania do koszyka: {str(e)}")

    def start_booking(self, presentation_code: str, cinema_id: str,
                     booking_type: str = "PG") -> Dict:
        """
        Inicjalizuj proces rezerwacji biletów (krok 1)
        Wymaga wcześniejszego zalogowania (access token)

        Args:
            presentation_code: Kod prezentacji/seansu (event ID)
            cinema_id: ID kina
            booking_type: Typ rezerwacji ("PG" dla standardowej, "UNLIMITED" dla członków)

        Returns:
            Dict z danymi sesji rezerwacji i dostępnymi miejscami

        Flow rezerwacji:
        1. start_booking() - inicjalizacja sesji rezerwacji
        2. select_seats() - wybór miejsc (TODO)
        3. confirm_booking() - potwierdzenie rezerwacji (TODO)
        4. payment/unlimited confirm (TODO)
        """
        if not self.auth_token:
            raise Exception("Musisz się najpierw zalogować (użyj metody login())")

        url = f"{self.BOOKING_API_BASE}/booking"

        params = {'lang': 'pl_PL'}

        # Access token w custom headerze (NIE Bearer!)
        headers = {
            'access-token': self.auth_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json;charset=utf-8, application/json',
            'Access-Control-Allow-Origin': '*'
        }

        # Booking URL format
        booking_url = f"{self.TICKETS_API_BASE}/order/{presentation_code}"

        data = {
            'type': booking_type,
            'bookingUrl': booking_url,
            'cinemaId': cinema_id,
            'params': {
                'lang': 'pl-PL'
            },
            'presentationCode': presentation_code,
            'salesBlocked': False,
            'salesBlockEndDate': None
        }

        try:
            response = self.session.post(url, params=params, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f": {error_data.get('error_description', error_data.get('message', str(error_data)))}"
            except:
                error_msg += f": {e.response.text[:200]}"
            raise Exception(error_msg)
        except Exception as e:
            raise Exception(f"Błąd inicjalizacji rezerwacji: {str(e)}")

    def book_tickets(self, showtime_id: str, seats: int) -> bool:
        """
        Zarezerwuj bilety na seans (high-level wrapper)
        TODO: Implementacja pełnego flow rezerwacji
        Flow rezerwacji wymaga kilku kroków:
        1. start_booking() - inicjalizacja sesji ✅
        2. Wybór miejsc
        3. Rezerwacja
        4. Płatność (lub potwierdzenie Unlimited)
        """
        raise NotImplementedError("Pełny flow rezerwacji w trakcie implementacji. Użyj start_booking() dla kroku 1.")
