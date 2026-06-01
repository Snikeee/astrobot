"""Геокодинг места рождения: город → координаты + часовой пояс.

- Координаты: бесплатный Nominatim (OpenStreetMap) через geopy. Требует интернет.
- Часовой пояс: timezonefinder — полностью офлайн, по координатам.
- utc-смещение на дату рождения берём из zoneinfo (учитывает исторический DST).

Если город не найден — поднимаем GeocodeError, чтобы хэндлер предложил ввести
координаты вручную (негативный сценарий из US-1.1).
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from ..data.geo_cities import lookup as offline_lookup

_tf = TimezoneFinder()
# короткий таймаут: если Nominatim недоступен — быстро падаем в понятную ошибку
_geolocator = Nominatim(user_agent="astrobot-mvp", timeout=4)


class GeocodeError(Exception):
    pass


def _utc_offset_hours(lat: float, lon: float, date: str, time: str) -> tuple[str, float]:
    tz_name = _tf.timezone_at(lat=lat, lng=lon)
    if not tz_name:
        # Грубый фолбэк по долготе, если точка вне базы таймзон (океан и т.п.)
        return "UTC", round(lon / 15.0)
    day, month, year = (int(x) for x in date.split("."))
    hour, minute = (int(x) for x in time.split(":"))
    dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz_name))
    offset = dt.utcoffset()
    return tz_name, offset.total_seconds() / 3600.0 if offset else 0.0


def resolve(place: str, date: str, time: str) -> tuple[float, float, str, float]:
    """Вернуть (lat, lon, tz_name, utc_offset_hours) по названию места.

    Сначала офлайн-справочник (быстро, без сети), затем онлайн-фолбэк Nominatim.
    """
    hit = offline_lookup(place)
    if hit is not None:
        lat, lon = hit
        tz_name, offset = _utc_offset_hours(lat, lon, date, time)
        return lat, lon, tz_name, offset

    # Фолбэк: онлайн-геокодер (может быть недоступен — обрабатываем мягко)
    try:
        loc = _geolocator.geocode(place, language="ru")
    except Exception:
        raise GeocodeError(
            f"Город «{place}» не найден в офлайн-справочнике, а онлайн-поиск сейчас "
            "недоступен. Укажите крупный ближайший город или введите координаты."
        )
    if loc is None:
        raise GeocodeError(
            f"Место «{place}» не найдено. Попробуйте уточнить название или ввести координаты."
        )
    tz_name, offset = _utc_offset_hours(loc.latitude, loc.longitude, date, time)
    return loc.latitude, loc.longitude, tz_name, offset


def from_coords(lat: float, lon: float, date: str, time: str) -> tuple[float, float, str, float]:
    """Тот же результат, но координаты заданы вручную (фолбэк)."""
    tz_name, offset = _utc_offset_hours(lat, lon, date, time)
    return lat, lon, tz_name, offset
