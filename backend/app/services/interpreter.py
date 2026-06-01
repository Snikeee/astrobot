"""Генерация текстовой трактовки личности.

Паттерн Strategy (как заложено в доке): Interpreter — абстрактный интерфейс,
RuleBasedInterpreter — бесплатная офлайн-реализация для MVP. Позже сюда можно
добавить LLMInterpreter (локальная Ollama или внешний API) без изменений в API.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass

from ..data.astro import PLANET_RU, SIGN_ELEMENT, SIGN_RU
from ..data.interpretations import (
    ELEMENT_ADVICE,
    ELEMENT_GROWTH,
    ELEMENT_STRENGTH,
    HOUSE_AREA,
    MOON_EMOTION,
    PLANET_MEANING,
    SIGN_TRAIT,
)
from ..domain.models import NatalChart


@dataclass
class Interpretation:
    summary: str                 # короткое резюме (Солнце/Луна/Асцендент)
    aspects: list[str]           # ≥10 интерпретаций «планета в знаке/доме»
    strengths: str
    growth: str
    emotions: str
    recommendations: str

    def aspect_count(self) -> int:
        return len(self.aspects)


class Interpreter(ABC):
    @abstractmethod
    def interpret(self, chart: NatalChart, level: str = "beginner") -> Interpretation: ...


class RuleBasedInterpreter(Interpreter):
    """Собирает трактовку из словарей по правилам. Детерминированно и быстро.

    level: "beginner" — короткие простые формулировки; "expert" — с домами,
    ретроградностью и более подробным описанием (US-2.2).
    """

    def interpret(self, chart: NatalChart, level: str = "beginner") -> Interpretation:
        expert = level == "expert"
        sun = chart.planet("sun")
        moon = chart.planet("moon")
        asc = chart.planet("asc")

        if asc is not None:
            summary = (
                f"Солнце в знаке {SIGN_RU[sun.sign]}, Луна в знаке {SIGN_RU[moon.sign]}, "
                f"Асцендент — {SIGN_RU[asc.sign]}. "
                "Это три опоры характера: суть, чувства и то, какими тебя видят."
            )
        else:
            summary = (
                f"Солнце в знаке {SIGN_RU[sun.sign]}, Луна в знаке {SIGN_RU[moon.sign]}. "
                "Асцендент и дома не рассчитаны — для них нужно точное время рождения."
            )

        # По одной трактовке на каждую планету — это ≥10 пунктов в обоих режимах.
        aspects: list[str] = []
        for p in chart.planets:
            if p.name not in PLANET_MEANING:
                continue  # asc/mc пропускаем — они в резюме
            house_part = f" ({p.house} дом)" if p.house else ""
            if expert:
                line = (
                    f"{PLANET_RU[p.name]} в знаке {SIGN_RU[p.sign]}{house_part}: "
                    f"{PLANET_MEANING[p.name]} проявляется {SIGN_TRAIT[p.sign]}."
                )
                if p.house:
                    line += f" Это особенно влияет на сферу «{HOUSE_AREA[p.house]}»."
                if p.retrograde:
                    line += " Планета ретроградна — тема работает скорее вовнутрь, чем напоказ."
            else:
                line = f"{PLANET_RU[p.name]} в знаке {SIGN_RU[p.sign]} — {SIGN_TRAIT[p.sign]}."
            aspects.append(line)

        # Доминирующая стихия — по знакам всех планет.
        elements = Counter(SIGN_ELEMENT[p.sign] for p in chart.planets if p.name in PLANET_MEANING)
        dominant = elements.most_common(1)[0][0]

        strengths = ELEMENT_STRENGTH[dominant]
        growth = ELEMENT_GROWTH[dominant]
        emotions = MOON_EMOTION[moon.sign]
        recommendations = ELEMENT_ADVICE[dominant]

        return Interpretation(
            summary=summary,
            aspects=aspects,
            strengths=strengths,
            growth=growth,
            emotions=emotions,
            recommendations=recommendations,
        )
