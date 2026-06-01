"""FastAPI-приложение AstraBot (Presentation layer).

Эндпоинты:
  GET  /            — отдаёт фронт (React без сборки, из static/index.html)
  GET  /health      — health-check для мониторинга (US-T-2)
  POST /api/chart   — построить карту по данным рождения

Сервис намеренно stateless: данные рождения не сохраняются на сервере
(требование приватности БТ №4 / US-T-1).
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .data.geo_cities import suggest as suggest_cities
from .services import synastry
from .services.chart_service import ChartService, prepare_chart
from .services.geocoder import GeocodeError

app = FastAPI(title="AstraBot", version="0.2.0-mvp")
_service = ChartService()

_STATIC = Path(__file__).parent / "static"

_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


class ChartRequest(BaseModel):
    date: str = Field(..., examples=["15.08.1990"])
    time: str = Field("12:00", examples=["13:45"])
    place: str | None = Field(None, examples=["Москва"])
    lat: float | None = None
    lon: float | None = None
    time_unknown: bool = False
    level: str = "beginner"  # beginner | expert


class CompatRequest(BaseModel):
    a: ChartRequest
    b: ChartRequest


def _validate(req: ChartRequest) -> None:
    if not _DATE_RE.match(req.date):
        raise HTTPException(422, "Неверный формат даты. Введите ДД.ММ.ГГГГ.")
    try:
        parsed = datetime.strptime(req.date, "%d.%m.%Y").date()  # реальная валидность даты
    except ValueError:
        raise HTTPException(422, "Такой даты не существует.")
    if parsed > date.today():
        raise HTTPException(422, "Дата рождения не может быть в будущем.")
    if not req.time_unknown:
        if not _TIME_RE.match(req.time):
            raise HTTPException(422, "Неверный формат времени. Введите ЧЧ:ММ (00:00–23:59).")
        hh, mm = (int(x) for x in req.time.split(":"))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise HTTPException(422, "Время должно быть в диапазоне 00:00–23:59.")
    if req.place is None and (req.lat is None or req.lon is None):
        raise HTTPException(422, "Укажите место рождения (город) или координаты.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/cities")
def cities(q: str = "") -> dict:
    """Автоподсказка городов из офлайн-справочника."""
    return {"items": suggest_cities(q)}


@app.post("/api/chart")
def build_chart(req: ChartRequest) -> dict:
    _validate(req)
    try:
        return _service.build(
            date=req.date, time=req.time,
            place=req.place, lat=req.lat, lon=req.lon,
            time_unknown=req.time_unknown, level=req.level,
        )
    except GeocodeError as e:
        raise HTTPException(404, str(e))
    except Exception as e:  # последний рубеж — не роняем сервис
        raise HTTPException(500, f"Не удалось построить карту: {e}")


@app.post("/api/compatibility")
def compatibility(req: CompatRequest) -> dict:
    _validate(req.a)
    _validate(req.b)
    try:
        chart_a = prepare_chart(req.a.date, req.a.time, req.a.place,
                                req.a.lat, req.a.lon, req.a.time_unknown)
        chart_b = prepare_chart(req.b.date, req.b.time, req.b.place,
                                req.b.lat, req.b.lon, req.b.time_unknown)
        return synastry.analyze(chart_a, chart_b)
    except GeocodeError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Не удалось рассчитать совместимость: {e}")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


# прочие статические файлы (если появятся)
app.mount("/static", StaticFiles(directory=_STATIC), name="static")
