"""Справочные константы астрологии: знаки, планеты, дома, аспекты.

Здесь только данные. Тексты трактовок — в interpretations.py.
"""

# --- Знаки зодиака (по порядку, каждый по 30°) ---
SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]

SIGN_RU = {
    "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы", "cancer": "Рак",
    "leo": "Лев", "virgo": "Дева", "libra": "Весы", "scorpio": "Скорпион",
    "sagittarius": "Стрелец", "capricorn": "Козерог", "aquarius": "Водолей",
    "pisces": "Рыбы",
}

SIGN_GLYPH = {
    "aries": "♈", "taurus": "♉", "gemini": "♊", "cancer": "♋",
    "leo": "♌", "virgo": "♍", "libra": "♎", "scorpio": "♏",
    "sagittarius": "♐", "capricorn": "♑", "aquarius": "♒",
    "pisces": "♓",
}

# Стихия и крест каждого знака
SIGN_ELEMENT = {
    "aries": "fire", "leo": "fire", "sagittarius": "fire",
    "taurus": "earth", "virgo": "earth", "capricorn": "earth",
    "gemini": "air", "libra": "air", "aquarius": "air",
    "cancer": "water", "scorpio": "water", "pisces": "water",
}

ELEMENT_RU = {"fire": "огонь", "earth": "земля", "air": "воздух", "water": "вода"}
# 🔥 огонь, 🪨 земля, 🌬️ воздух, 💧 вода (требование БТ №11: цвет+эмодзи стихии)
ELEMENT_EMOJI = {"fire": "\U0001F525", "earth": "\U0001FAA8", "air": "\U0001F32C️", "water": "\U0001F4A7"}


def sign_of(longitude: float) -> tuple[str, float]:
    """Вернуть (ключ знака, градус внутри знака) для эклиптической долготы."""
    lon = longitude % 360.0
    idx = int(lon // 30)
    return SIGNS[idx], lon - idx * 30


# --- Планеты, светила, узлы (то, что считаем через swisseph) ---
# Порядок задаёт и порядок вывода трактовок.
PLANETS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
]

PLANET_RU = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий", "venus": "Венера",
    "mars": "Марс", "jupiter": "Юпитер", "saturn": "Сатурн", "uranus": "Уран",
    "neptune": "Нептун", "pluto": "Плутон",
    "asc": "Асцендент", "mc": "Середина неба (MC)",
}

PLANET_GLYPH = {
    "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀",
    "mars": "♂", "jupiter": "♃", "saturn": "♄", "uranus": "♅",
    "neptune": "♆", "pluto": "♇", "asc": "Asc", "mc": "MC",
}

# --- Аспекты: точный угол и допустимый орбис ---
ASPECTS = {
    "conjunction": (0.0, 8.0),
    "sextile": (60.0, 4.0),
    "square": (90.0, 6.0),
    "trine": (120.0, 6.0),
    "opposition": (180.0, 8.0),
}

ASPECT_RU = {
    "conjunction": "соединение", "sextile": "секстиль", "square": "квадрат",
    "trine": "тригон", "opposition": "оппозиция",
}

ASPECT_GLYPH = {
    "conjunction": "☌", "sextile": "⚹", "square": "□",
    "trine": "△", "opposition": "☍",
}

# Гармоничные / напряжённые — для оценки тональности
HARMONIOUS_ASPECTS = {"sextile", "trine"}
TENSE_ASPECTS = {"square", "opposition"}
