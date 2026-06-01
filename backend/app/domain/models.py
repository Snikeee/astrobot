"""Доменные сущности натальной карты (Domain layer).

Чистые структуры данных без зависимостей от расчётного движка, рендера и БД —
ими оперируют все верхние слои.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlanetPosition:
    """Положение планеты (или светила/угла) в карте."""

    name: str            # внутренний ключ, напр. "sun"
    longitude: float     # эклиптическая долгота 0..360
    sign: str            # ключ знака, напр. "leo"
    sign_degree: float   # градус внутри знака 0..30
    house: int           # номер дома 1..12 (0 — если дома не считались)
    retrograde: bool = False


@dataclass
class HouseCusp:
    number: int          # 1..12
    longitude: float
    sign: str


@dataclass
class Aspect:
    p1: str              # ключ первой планеты
    p2: str              # ключ второй планеты
    kind: str            # ключ аспекта: conjunction/sextile/square/trine/opposition
    angle: float         # фактический угол между планетами
    orb: float           # отклонение от точного аспекта


@dataclass
class BirthData:
    """То, что ввёл пользователь. Намеренно не персистится (приватность)."""

    date: str            # ДД.ММ.ГГГГ
    time: str            # ЧЧ:ММ (если время неизвестно — берём 12:00)
    place: str
    latitude: float
    longitude: float
    tz_name: str
    utc_offset_hours: float
    time_known: bool = True  # False → дома и Асцендент не рассчитываются


@dataclass
class NatalChart:
    birth: BirthData
    planets: list[PlanetPosition] = field(default_factory=list)
    houses: list[HouseCusp] = field(default_factory=list)
    aspects: list[Aspect] = field(default_factory=list)

    def planet(self, name: str) -> PlanetPosition | None:
        return next((p for p in self.planets if p.name == name), None)
