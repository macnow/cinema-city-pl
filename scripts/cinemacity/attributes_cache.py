"""
Cache atrybutów Cinema City
Generowany automatycznie z API
"""
import requests
from typing import Dict, List, Optional


_attributes_cache: Optional[Dict] = None


def fetch_attributes() -> Dict:
    """
    Pobierz atrybuty z API Cinema City

    Returns:
        Dict z grupami atrybutów
    """
    url = 'https://www.cinema-city.pl/pl/data-api-service/v1/quickbook/10103/attributes'
    headers = {
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers, params={'lang': 'pl_PL'})
    response.raise_for_status()
    data = response.json()

    return data.get('body', {}).get('attributes', [])


def get_attributes() -> Dict:
    """
    Pobierz atrybuty (z cache)

    Returns:
        Dict z grupami atrybutów
    """
    global _attributes_cache

    if _attributes_cache is None:
        _attributes_cache = fetch_attributes()

    return _attributes_cache


def get_attribute_info(attr_id: str) -> Optional[Dict]:
    """
    Pobierz informacje o konkretnym atrybucie

    Args:
        attr_id: ID atrybutu (np. "imax", "3d", "dubbed")

    Returns:
        Dict z info o atrybucie lub None jeśli nie znaleziono
    """
    attributes = get_attributes()

    for group in attributes:
        for item in group['items']:
            if item['id'] == attr_id:
                return {
                    'id': item['id'],
                    'group': group['group-name'],
                    'icon_url': item.get('url'),
                    'visible': item.get('visible', True),
                }

    return None


def get_attributes_by_group(group_name: str) -> List[str]:
    """
    Pobierz listę ID atrybutów dla danej grupy

    Args:
        group_name: Nazwa grupy (age-restriction, screening-type, etc.)

    Returns:
        Lista ID atrybutów
    """
    attributes = get_attributes()

    for group in attributes:
        if group['group-name'] == group_name:
            return [item['id'] for item in group['items']]

    return []


# Mapowanie popularnych atrybutów na polskie nazwy
ATTRIBUTE_DISPLAY_NAMES = {
    # Screening type
    '2d': '2D',
    '3d': '3D',
    'dolby-atmos': 'Dolby Atmos',
    'laser-barco': 'Laser',

    # Special type
    'imax': 'IMAX',
    'imax-3d': 'IMAX 3D',
    '4dx': '4DX',
    'screenx': 'ScreenX',
    'vip': 'VIP',

    # Language
    'dubbed': 'Dubbing',
    'subbed': 'Napisy',
    'original': 'Oryginalna wersja',

    # Extra
    'ladies-night': 'Ladies Night',
    'special-event': 'Wydarzenie specjalne',
    'event': 'Wydarzenie',
    'marathon': 'Maraton',

    # Screening addons
    'hfr': 'HFR (High Frame Rate)',
    'dmr': 'DMR',
}


def get_display_name(attr_id: str) -> str:
    """
    Pobierz czytelną nazwę atrybutu

    Args:
        attr_id: ID atrybutu

    Returns:
        Czytelna nazwa lub ID jeśli nie znaleziono
    """
    return ATTRIBUTE_DISPLAY_NAMES.get(attr_id.lower(), attr_id.upper())
