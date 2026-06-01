"""SynastryService — анализ совместимости двух карт (БТ №3, US-3.1).

Rule-based: считаем межкарточные аспекты (планета человека A к планете человека B),
раскладываем их вклад по пяти сферам и переводим в оценку 0–100 и звёзды 0–5.
Реализация Strategy-совместима: позже сюда можно подставить ML-оценку.
"""
from __future__ import annotations

from ..data.astro import (
    ASPECT_GLYPH,
    ASPECT_RU,
    ASPECTS,
    HARMONIOUS_ASPECTS,
    PLANET_GLYPH,
    PLANET_RU,
)
from ..domain.models import NatalChart, PlanetPosition

# Пять сфер совместимости и планеты-сигнификаторы каждой.
SPHERES = [
    ("emotions", "Эмоции", {"moon", "venus", "sun"}),
    ("intellect", "Интеллект", {"mercury", "jupiter", "uranus"}),
    ("daily", "Быт", {"mars", "saturn", "moon"}),
    ("values", "Ценности", {"venus", "sun", "jupiter"}),
    ("spirit", "Духовность", {"neptune", "pluto", "jupiter", "sun"}),
]

# Вес аспекта: гармоничные — в плюс, напряжённые — в минус.
ASPECT_WEIGHT = {
    "trine": 3.0, "sextile": 2.0, "conjunction": 2.0,
    "square": -2.0, "opposition": -2.0,
}

_BANDS = [
    (75, "очень высокая", "Здесь между вами много тепла и понимания — сильная сторона пары."),
    (60, "высокая", "Эта сфера складывается легко и поддерживает отношения."),
    (45, "средняя", "Нейтральная зона: всё зависит от вашего внимания друг к другу."),
    (30, "ниже среднего", "Возможны разногласия — потребуется терпение и разговор."),
    (0, "низкая", "Самая непростая сфера: важно проговаривать ожидания и идти на компромисс."),
]


def _aspect_between(lon1: float, lon2: float) -> tuple[str, float] | None:
    diff = abs(lon1 - lon2) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    for kind, (exact, orb) in ASPECTS.items():
        delta = abs(diff - exact)
        if delta <= orb:
            return kind, round(delta, 2)
    return None


def _real(chart: NatalChart) -> list[PlanetPosition]:
    return [p for p in chart.planets if p.name in PLANET_GLYPH and p.name not in ("asc", "mc")]


def _band(score: int) -> tuple[str, str]:
    for threshold, label, text in _BANDS:
        if score >= threshold:
            return label, text
    return _BANDS[-1][1], _BANDS[-1][2]


def analyze(chart_a: NatalChart, chart_b: NatalChart) -> dict:
    planets_a, planets_b = _real(chart_a), _real(chart_b)

    raw = {key: 0.0 for key, _, _ in SPHERES}
    cross: list[dict] = []
    for pa in planets_a:
        for pb in planets_b:
            res = _aspect_between(pa.longitude, pb.longitude)
            if res is None:
                continue
            kind, orb = res
            weight = ASPECT_WEIGHT[kind]
            for key, _, planets in SPHERES:
                if pa.name in planets or pb.name in planets:
                    raw[key] += weight
            cross.append({
                "a": PLANET_RU[pa.name], "a_glyph": PLANET_GLYPH[pa.name],
                "b": PLANET_RU[pb.name], "b_glyph": PLANET_GLYPH[pb.name],
                "kind": ASPECT_RU[kind], "glyph": ASPECT_GLYPH[kind],
                "harmony": "harmonious" if kind in HARMONIOUS_ASPECTS
                           else ("tense" if weight < 0 else "neutral"),
                "orb": orb, "_w": abs(weight), "_o": orb,
            })

    spheres_out = []
    for key, title, _ in SPHERES:
        score = max(8, min(96, round(50 + raw[key] * 4)))
        label, text = _band(score)
        spheres_out.append({
            "key": key, "title": title, "score": score,
            "stars": round(score / 20), "label": label, "text": text,
        })

    overall = round(sum(s["score"] for s in spheres_out) / len(spheres_out))
    # самые сильные межкарточные аспекты — по весу, затем по близости к точному
    cross.sort(key=lambda c: (-c["_w"], c["_o"]))
    for c in cross:
        del c["_w"], c["_o"]

    return {
        "overall": overall,
        "overall_stars": round(overall / 20),
        "spheres": spheres_out,
        "cross_aspects": cross[:10],
        "cross_count": len(cross),
    }
