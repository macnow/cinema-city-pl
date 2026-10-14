"""
Mapowanie ID kin Cinema City Poland na nazwy i lokalizacje

Aby dodać nowe kino:
1. Znajdź ID poprzez scan_cinema_ids.py
2. Sprawdź adres na stronie cinema-city.pl
3. Dodaj do CINEMAS_MAP

Znane ID kin: 1060-1099 (około 40 aktywnych)
"""

CINEMAS_MAP = {
    # Warszawa
    "1067": {"name": "Sadyba", "city": "Warszawa", "address": "Galeria Sadyba"},
    "1097": {"name": "Mokotów", "city": "Warszawa", "address": "Galeria Mokotów"},
    "1079": {"name": "Arkadia", "city": "Warszawa", "address": "Arkadia"},
    "1085": {"name": "Białołęka", "city": "Warszawa", "address": "Galeria Białołęka"},
    "1089": {"name": "Targówek", "city": "Warszawa", "address": "Galeria Targówek"},

    # Kraków
    "1060": {"name": "Bonarka", "city": "Kraków", "address": "Galeria Bonarka"},
    "1061": {"name": "Galeria Krakowska", "city": "Kraków", "address": "Galeria Krakowska"},
    "1062": {"name": "Plaza", "city": "Kraków", "address": "Plaza Kraków"},

    # Wrocław
    "1064": {"name": "Korona", "city": "Wrocław", "address": "Korona"},
    "1065": {"name": "Magnolia Park", "city": "Wrocław", "address": "Magnolia Park"},
    "1068": {"name": "Wroclavia", "city": "Wrocław", "address": "Wroclavia"},

    # Poznań
    "1074": {"name": "Kinepolis", "city": "Poznań", "address": "Kinepolis"},
    "1075": {"name": "Stary Browar", "city": "Poznań", "address": "Stary Browar"},
    "1076": {"name": "Plaza", "city": "Poznań", "address": "Plaza"},

    # Łódź
    "1077": {"name": "Manufaktura", "city": "Łódź", "address": "Manufaktura"},
    "1078": {"name": "Port Łódź", "city": "Łódź", "address": "Port Łódź"},

    # Gdańsk, Gdynia, Sopot
    "1080": {"name": "Manhattan", "city": "Gdańsk", "address": "Manhattan"},
    "1081": {"name": "Riviera", "city": "Gdynia", "address": "Riviera"},
    "1082": {"name": "Alfa Centrum", "city": "Gdańsk", "address": "Alfa Centrum"},

    # Katowice i okolice
    "1083": {"name": "Punkt 44", "city": "Katowice", "address": "Punkt 44"},
    "1084": {"name": "Silesia", "city": "Katowice", "address": "Silesia City Center"},
    "1086": {"name": "Sosnowiec", "city": "Sosnowiec", "address": "Sosnowiec Plaza"},

    # Pozostałe większe miasta
    "1087": {"name": "Lublin Plaza", "city": "Lublin", "address": "Lublin Plaza"},
    "1088": {"name": "Szczecin Galaxy", "city": "Szczecin", "address": "Galaxy"},
    "1090": {"name": "Bydgoszcz", "city": "Bydgoszcz", "address": "Zielone Arkady"},
    "1091": {"name": "Kielce", "city": "Kielce", "address": "Galeria Echo"},
    "1092": {"name": "Toruń Plaza", "city": "Toruń", "address": "Toruń Plaza"},
    "1093": {"name": "Rzeszów", "city": "Rzeszów", "address": "Galeria Rzeszów"},
    "1094": {"name": "Olsztyn", "city": "Olsztyn", "address": "Galeria Warmińska"},
    "1095": {"name": "Opole", "city": "Opole", "address": "Solaris Center"},
    "1096": {"name": "Gliwice", "city": "Gliwice", "address": "Forum Gliwice"},
    "1098": {"name": "Zabrze", "city": "Zabrze", "address": "Platan"},
    "1099": {"name": "Częstochowa", "city": "Częstochowa", "address": "Galeria Jurajska"},
}


def get_cinema_info(cinema_id: str) -> dict:
    """
    Pobierz informacje o kinie na podstawie ID

    Args:
        cinema_id: ID kina (string lub int)

    Returns:
        Dict z polami: name, city, address
        Jeśli kino nieznane, zwraca generyczne info
    """
    cinema_id = str(cinema_id)
    if cinema_id in CINEMAS_MAP:
        return CINEMAS_MAP[cinema_id]
    else:
        return {
            "name": f"Cinema City {cinema_id}",
            "city": "Nieznane",
            "address": "Nieznane"
        }


def get_all_cinemas() -> list:
    """
    Zwraca listę wszystkich znanych kin

    Returns:
        Lista dict z polami: id, name, city, address
    """
    cinemas = []
    for cinema_id, info in CINEMAS_MAP.items():
        cinemas.append({
            "id": cinema_id,
            **info
        })
    return sorted(cinemas, key=lambda x: (x['city'], x['name']))
