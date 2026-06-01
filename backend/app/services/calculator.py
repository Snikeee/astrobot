"""NatalChartCalculator — астрологический расчёт через pyswisseph (Enabler US-1.1 #2).

Используется эфемерида Moshier (FLG_MOSEPH) — она встроена в pyswisseph и не
требует скачивания файлов эфемерид, что удобно для офлайн-MVP. Точность Moshier
для натальных карт достаточна (погрешность долей угловой минуты).
"""
from __future__ import annotations

import swisseph as swe

from ..data.astro import ASPECTS, PLANETS, sign_of
from ..domain.models import Aspect, BirthData, HouseCusp, NatalChart, PlanetPosition

# swisseph-идентификаторы планет
_SWE_ID = {
    "sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY, "venus": swe.VENUS,
    "mars": swe.MARS, "jupiter": swe.JUPITER, "saturn": swe.SATURN,
    "uranus": swe.URANUS, "neptune": swe.NEPTUNE, "pluto": swe.PLUTO,
}

_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED


def _julian_day_ut(birth: BirthData) -> float:
    """Перевести местное время рождения в UT и вернуть юлианский день."""
    day, month, year = (int(x) for x in birth.date.split("."))
    hour, minute = (int(x) for x in birth.time.split(":"))
    local_hours = hour + minute / 60.0
    ut_hours = local_hours - birth.utc_offset_hours
    return swe.julday(year, month, day, ut_hours, swe.GREG_CAL)


def _house_of(longitude: float, cusps: list[float]) -> int:
    """Номер дома (1..12), в котором лежит долгота, по куспидам Placidus."""
    lon = longitude % 360.0
    for i in range(12):
        start = cusps[i] % 360.0
        end = cusps[(i + 1) % 12] % 360.0
        if start <= end:
            if start <= lon < end:
                return i + 1
        else:  # сектор пересекает 0°
            if lon >= start or lon < end:
                return i + 1
    return 1


def _compute_aspects(planets: list[PlanetPosition]) -> list[Aspect]:
    aspects: list[Aspect] = []
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1, p2 = planets[i], planets[j]
            diff = abs(p1.longitude - p2.longitude) % 360.0
            if diff > 180.0:
                diff = 360.0 - diff
            for kind, (exact, orb) in ASPECTS.items():
                delta = abs(diff - exact)
                if delta <= orb:
                    aspects.append(Aspect(p1.name, p2.name, kind, round(diff, 2), round(delta, 2)))
                    break
    return aspects


class NatalChartCalculator:
    """Фасад над swisseph: на входе BirthData, на выходе NatalChart."""

    def calculate(self, birth: BirthData) -> NatalChart:
        swe.set_ephe_path(None)  # Moshier, файлы эфемерид не нужны
        jd = _julian_day_ut(birth)

        # Дома и угловые точки считаем только при известном времени:
        # Асцендент/MC/куспиды меняются ~1° за 4 минуты, без времени бессмысленны.
        cusp_list: list[float] = []
        ascmc = None
        if birth.time_known:
            cusps, ascmc = swe.houses(jd, birth.latitude, birth.longitude, b"P")
            cusp_list = list(cusps)

        planets: list[PlanetPosition] = []
        for key in PLANETS:
            xx, _ = swe.calc_ut(jd, _SWE_ID[key], _FLAGS)
            lon = xx[0]
            speed = xx[3]
            sign, deg = sign_of(lon)
            house = _house_of(lon, cusp_list) if cusp_list else 0
            planets.append(PlanetPosition(
                name=key, longitude=lon, sign=sign, sign_degree=deg,
                house=house, retrograde=speed < 0,
            ))

        houses: list[HouseCusp] = []
        if ascmc is not None:
            asc_sign, asc_deg = sign_of(ascmc[0])
            mc_sign, mc_deg = sign_of(ascmc[1])
            planets.append(PlanetPosition("asc", ascmc[0], asc_sign, asc_deg, 1))
            planets.append(PlanetPosition("mc", ascmc[1], mc_sign, mc_deg, 10))
            for i, c in enumerate(cusp_list, start=1):
                s, _ = sign_of(c)
                houses.append(HouseCusp(i, c, s))

        # Аспекты считаем только между настоящими планетами (без asc/mc)
        real_planets = [p for p in planets if p.name in _SWE_ID]
        aspects = _compute_aspects(real_planets)

        return NatalChart(birth=birth, planets=planets, houses=houses, aspects=aspects)
