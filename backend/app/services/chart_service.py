"""ChartService — фасад прикладного уровня (паттерн Facade из доки).

Скрывает за одним методом всю цепочку: геокодинг → расчёт → рендер → трактовка.
Презентационный слой (FastAPI) знает только про него.

prepare_chart() вынесен отдельно — его переиспользует SynastryService.
"""
from __future__ import annotations

import base64

from . import geocoder
from .calculator import NatalChartCalculator
from .chart_image import render_png
from .interpreter import Interpreter, RuleBasedInterpreter
from ..data.astro import (
    ASPECT_GLYPH,
    ASPECT_RU,
    ELEMENT_EMOJI,
    HARMONIOUS_ASPECTS,
    PLANET_GLYPH,
    PLANET_RU,
    SIGN_ELEMENT,
    SIGN_RU,
    TENSE_ASPECTS,
)
from ..domain.models import BirthData, NatalChart

_calc = NatalChartCalculator()


def prepare_chart(
    date: str,
    time: str,
    place: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    time_unknown: bool = False,
) -> NatalChart:
    """Геокодинг + расчёт. Без рендера и трактовки — общая часть для всех сценариев."""
    eff_time = "12:00" if time_unknown else time
    if lat is not None and lon is not None:
        latitude, longitude, tz_name, offset = geocoder.from_coords(lat, lon, date, eff_time)
        place_label = place or f"{lat:.4f}, {lon:.4f}"
    else:
        latitude, longitude, tz_name, offset = geocoder.resolve(place, date, eff_time)
        place_label = place

    birth = BirthData(
        date=date, time=eff_time, place=place_label,
        latitude=latitude, longitude=longitude,
        tz_name=tz_name, utc_offset_hours=offset,
        time_known=not time_unknown,
    )
    return _calc.calculate(birth)


class ChartService:
    def __init__(self, interpreter: Interpreter | None = None):
        self._interpreter = interpreter or RuleBasedInterpreter()

    def build(
        self,
        date: str,
        time: str,
        place: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        time_unknown: bool = False,
        level: str = "beginner",
    ) -> dict:
        chart = prepare_chart(date, time, place, lat, lon, time_unknown)
        png = render_png(chart)
        interp = self._interpreter.interpret(chart, level=level)

        notice = None
        if not chart.birth.time_known:
            notice = ("Время рождения не указано: дома и Асцендент не рассчитаны, "
                      "а положение Луны может отличаться на несколько градусов.")

        return {
            "birth": {
                "date": chart.birth.date,
                "time": None if not chart.birth.time_known else chart.birth.time,
                "place": chart.birth.place,
                "tz": chart.birth.tz_name,
                "utc_offset": chart.birth.utc_offset_hours,
                "time_known": chart.birth.time_known,
            },
            "notice": notice,
            "level": level,
            "positions": positions_payload(chart),
            "aspects": aspects_payload(chart),
            "interpretation": {
                "summary": interp.summary,
                "aspects": interp.aspects,
                "strengths": interp.strengths,
                "growth": interp.growth,
                "emotions": interp.emotions,
                "recommendations": interp.recommendations,
                "aspect_count": interp.aspect_count(),
            },
            "image_base64": "data:image/png;base64," + base64.b64encode(png).decode(),
        }


def positions_payload(chart: NatalChart) -> list[dict]:
    out = []
    for p in chart.planets:
        out.append({
            "planet": PLANET_RU[p.name],
            "glyph": PLANET_GLYPH[p.name],
            "sign": SIGN_RU[p.sign],
            "element_emoji": ELEMENT_EMOJI[SIGN_ELEMENT[p.sign]],
            "degree": round(p.sign_degree, 1),
            "house": p.house,
            "retrograde": p.retrograde,
        })
    return out


def _harmony(kind: str) -> str:
    if kind in HARMONIOUS_ASPECTS:
        return "harmonious"
    if kind in TENSE_ASPECTS:
        return "tense"
    return "neutral"


def aspects_payload(chart: NatalChart) -> list[dict]:
    return [
        {
            "from": PLANET_RU[a.p1],
            "from_glyph": PLANET_GLYPH[a.p1],
            "to": PLANET_RU[a.p2],
            "to_glyph": PLANET_GLYPH[a.p2],
            "kind": ASPECT_RU[a.kind],
            "glyph": ASPECT_GLYPH[a.kind],
            "harmony": _harmony(a.kind),
            "orb": a.orb,
        }
        for a in chart.aspects
    ]
