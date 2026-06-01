"""Рендер круговой натальной карты в PNG (Enabler US-1.2 #1).

Чистый matplotlib, без внешних сервисов. Тёмная «космическая» тема под дизайн
приложения. Рисуем:
  - кольцо знаков с секторами, подкрашенными по стихии, и глифами;
  - кольцо домов с куспидами и номерами;
  - засечки градусов;
  - планеты глифами (с разведением слипающихся) и их градусами;
  - линии аспектов во внутреннем круге (цвет по типу аспекта).
Ориентация: Асцендент слева (180° экрана), карта раскручивается против часовой.
"""
from __future__ import annotations

import io
import math

import matplotlib

matplotlib.use("Agg")  # без GUI-бэкенда
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Wedge  # noqa: E402

from ..data.astro import (  # noqa: E402
    HARMONIOUS_ASPECTS,
    PLANET_GLYPH,
    PLANET_RU,
    PLANETS,
    SIGN_ELEMENT,
    SIGN_GLYPH,
    SIGNS,
)
from ..domain.models import NatalChart  # noqa: E402

# --- Палитра тёмной темы ---
BG = "#1b1726"
RING = "#4a4360"
RING_SOFT = "#332e47"
SIGN_GLYPH_COLOR = "#d8d2ec"
HOUSE_NUM = "#7c7593"
PLANET_COLOR = "#f3f0ff"
DEG_COLOR = "#9b95b3"
AXIS_COLOR = "#e0709a"

ELEMENT_FILL = {  # подсветка секторов знаков по стихии (низкая прозрачность)
    "fire": "#ff7a59",
    "earth": "#7bbf6a",
    "air": "#7cc7e8",
    "water": "#7c93e8",
}
ASPECT_COLOR = {
    "conjunction": "#b8a6e8",  # нейтральный лавандовый
    "sextile": "#5fd0c4",      # гармоничные — бирюза/зелёный
    "trine": "#5fd0c4",
    "square": "#ef6f6f",       # напряжённые — красный
    "opposition": "#ef6f6f",
}

R_OUT = 1.18
R_SIGN_IN = 1.00
R_HOUSE_IN = 0.84
R_PLANET = 0.72
R_ASPECT = 0.52   # внутренний круг, по которому проводятся линии аспектов


def _xy(angle_deg: float, radius: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return radius * math.cos(a), radius * math.sin(a)


def _declustered_radius(planets, screen_angle):
    """Развести слипающиеся планеты по радиусу, чтобы глифы не наезжали."""
    order = sorted(planets, key=lambda p: screen_angle(p.longitude) % 360.0)
    radii: dict[str, float] = {}
    last_ang = -999.0
    level = 0
    for p in order:
        a = screen_angle(p.longitude) % 360.0
        if a - last_ang < 8.0:
            level = min(level + 1, 3)
        else:
            level = 0
        radii[p.name] = R_PLANET - level * 0.082
        last_ang = a
    return radii


def render_png(chart: NatalChart, size_px: int = 1200) -> bytes:
    asc = chart.planet("asc")
    has_houses = bool(chart.houses)
    # При известном времени Асцендент слева; иначе ориентируем по 0° Овна слева.
    asc_lon = asc.longitude if asc is not None else 0.0

    def screen_angle(lon: float) -> float:
        return (lon - asc_lon) + 180.0

    dpi = 100
    # фигура выше квадрата — снизу полоса под легенду (глифы планет + аспекты)
    fig = plt.figure(figsize=(size_px / dpi, size_px * 1.42 / dpi), dpi=dpi, facecolor=BG)
    ax = fig.add_axes([0.02, 0.30, 0.96, 0.685])
    ax.set_xlim(-1.28, 1.28)
    ax.set_ylim(-1.28, 1.28)
    ax.set_aspect("equal")
    ax.set_facecolor(BG)
    ax.axis("off")

    real = [p for p in chart.planets if p.name not in ("asc", "mc")]

    # 1) Цветные секторы знаков по стихиям
    for i, sign in enumerate(SIGNS):
        a0 = screen_angle(i * 30)
        a1 = screen_angle((i + 1) * 30)
        ax.add_patch(Wedge((0, 0), R_SIGN_IN, min(a0, a1), max(a0, a1),
                           width=R_SIGN_IN - R_HOUSE_IN, facecolor="none"))
        ax.add_patch(Wedge((0, 0), R_OUT, a1, a0,  # против часовой
                           width=R_OUT - R_SIGN_IN,
                           facecolor=ELEMENT_FILL[SIGN_ELEMENT[sign]], alpha=0.16,
                           edgecolor="none"))

    # 2) Кольца
    for r in (R_OUT, R_SIGN_IN, R_HOUSE_IN, R_ASPECT):
        ax.add_patch(plt.Circle((0, 0), r, fill=False, color=RING, lw=1.2))

    # 3) Засечки градусов (каждые 5°, длиннее каждые 30°)
    for deg in range(0, 360, 5):
        ang = screen_angle(deg)
        inner = R_SIGN_IN - (0.05 if deg % 30 == 0 else 0.025)
        x1, y1 = _xy(ang, R_SIGN_IN)
        x2, y2 = _xy(ang, inner)
        ax.plot([x1, x2], [y1, y2], color=RING_SOFT, lw=1.0)

    # 4) Границы знаков и глифы
    for i, sign in enumerate(SIGNS):
        ang = screen_angle(i * 30)
        x1, y1 = _xy(ang, R_SIGN_IN)
        x2, y2 = _xy(ang, R_OUT)
        ax.plot([x1, x2], [y1, y2], color=RING, lw=1.0)
        gx, gy = _xy(screen_angle(i * 30 + 15), (R_SIGN_IN + R_OUT) / 2)
        ax.text(gx, gy, SIGN_GLYPH[sign], ha="center", va="center",
                fontsize=22, color=SIGN_GLYPH_COLOR)

    # 5) Куспиды домов и номера (только если время известно)
    for h in chart.houses:
        ang = screen_angle(h.longitude)
        x1, y1 = _xy(ang, R_ASPECT)
        x2, y2 = _xy(ang, R_SIGN_IN)
        angular = h.number in (1, 4, 7, 10)
        ax.plot([x1, x2], [y1, y2], color=(RING if angular else RING_SOFT),
                lw=1.8 if angular else 0.9)
        nx, ny = _xy(ang + 4, R_HOUSE_IN + 0.05)
        ax.text(nx, ny, str(h.number), ha="center", va="center",
                fontsize=11, color=HOUSE_NUM)

    # 6) Линии аспектов во внутреннем круге
    pos_by_name = {p.name: p for p in real}
    for asp in chart.aspects:
        p1, p2 = pos_by_name.get(asp.p1), pos_by_name.get(asp.p2)
        if not p1 or not p2:
            continue
        x1, y1 = _xy(screen_angle(p1.longitude), R_ASPECT)
        x2, y2 = _xy(screen_angle(p2.longitude), R_ASPECT)
        ax.plot([x1, x2], [y1, y2], color=ASPECT_COLOR[asp.kind],
                lw=1.6 if asp.kind in HARMONIOUS_ASPECTS or asp.kind == "conjunction" else 1.4,
                alpha=0.72, solid_capstyle="round")

    # 7) Планеты (с разведением по радиусу) + засечка истинного градуса
    radii = _declustered_radius(real, screen_angle)
    for p in real:
        ang = screen_angle(p.longitude)
        r = radii[p.name]
        # тонкий поводок от истинного градуса (на внутр. кромке домов) к глифу
        tx, ty = _xy(ang, R_HOUSE_IN)
        gx, gy = _xy(ang, r + 0.05)
        ax.plot([tx, gx], [ty, gy], color=RING_SOFT, lw=0.8)
        ax.scatter([tx], [ty], s=10, color=ELEMENT_FILL[SIGN_ELEMENT[p.sign]], zorder=5)
        ax.text(*_xy(ang, r), PLANET_GLYPH[p.name], ha="center", va="center",
                fontsize=19, color=PLANET_COLOR, zorder=6)
        dx, dy = _xy(ang, r - 0.10)
        ax.text(dx, dy, f"{int(p.sign_degree)}°", ha="center", va="center",
                fontsize=8, color=DEG_COLOR, zorder=6)

    # 8) Оси Asc / MC (только при известном времени)
    for key in ("asc", "mc") if has_houses else ():
        ap = chart.planet(key)
        ang = screen_angle(ap.longitude)
        x1, y1 = _xy(ang, R_HOUSE_IN)
        x2, y2 = _xy(ang, R_OUT)
        ax.plot([x1, x2], [y1, y2], color=AXIS_COLOR, lw=1.8)
        lx, ly = _xy(ang, R_OUT + 0.08)
        ax.text(lx, ly, PLANET_GLYPH[key], ha="center", va="center",
                fontsize=12, color=AXIS_COLOR, fontweight="bold")

    # 9) Легенда — в нижней полосе.
    # 9a) Глифы планет: название + символ, сеткой 5×2
    fig.text(0.5, 0.265, "Планеты", ha="center", va="center",
             fontsize=13, color=HOUSE_NUM, fontweight="bold")
    cols = 5
    col_w = 0.86 / cols
    for idx, key in enumerate(PLANETS):
        row, col = idx // cols, idx % cols
        x = 0.07 + col_w * (col + 0.5)
        y = 0.215 - row * 0.052
        fig.text(x, y, f"{PLANET_GLYPH[key]} {PLANET_RU[key]}", ha="center", va="center",
                 fontsize=14, color=SIGN_GLYPH_COLOR)

    # 9b) Цвета аспектов (и оси) — отдельной легендой ниже
    fig.text(0.5, 0.105, "Аспекты", ha="center", va="center",
             fontsize=13, color=HOUSE_NUM, fontweight="bold")
    handles = [
        Line2D([0], [0], color=ASPECT_COLOR["trine"], lw=2.4,
               label="Гармоничные аспекты (тригон, секстиль)"),
        Line2D([0], [0], color=ASPECT_COLOR["square"], lw=2.4,
               label="Напряжённые аспекты (квадрат, оппозиция)"),
        Line2D([0], [0], color=ASPECT_COLOR["conjunction"], lw=2.4,
               label="Соединение"),
    ]
    if has_houses:
        handles.append(Line2D([0], [0], color=AXIS_COLOR, lw=2.4, label="Оси Asc / MC"))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.02),
               ncol=2, frameon=False, fontsize=12.5, labelcolor=SIGN_GLYPH_COLOR,
               handlelength=2.2, columnspacing=2.6, labelspacing=0.9)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor=BG)
    plt.close(fig)
    return buf.getvalue()
