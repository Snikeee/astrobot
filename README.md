# ✨ AstraBot — MVP

Веб-приложение: по дате, времени и месту рождения строит **натальную карту**,
рисует её круговой диаграммой и выдаёт **текстовую трактовку личности**.

Покрывает базовые требования Kano: расчёт + изображение карты, трактовка личности
(с уровнями «Начинающий/Эксперт»), совместимость двух людей по 5 сферам, опция
«время неизвестно». Без истории, PDF и геймификации (следующие итерации).

## Стек

- **Бэкенд:** FastAPI (Python 3.12)
- **Фронтенд:** React через CDN, без сборки (отдаётся самим FastAPI)
- **Астрорасчёт:** `pyswisseph` в режиме Moshier (эфемериды встроены, интернет не нужен)
- **Карта:** `matplotlib` → PNG
- **Геокодинг:** Nominatim (`geopy`) + офлайн-таймзоны (`timezonefinder`)
- **Хранение:** нет. Сервис stateless — данные рождения нигде не сохраняются
  (требование приватности БТ №4 / US-T-1).

## Архитектура (слои)

```
Presentation     app/main.py                 FastAPI, валидация, роуты
Application       app/services/chart_service  ChartService (Facade)
Domain            app/domain/models.py        NatalChart, Planet, House, Aspect
Infrastructure    app/services/calculator     pyswisseph
                  app/services/geocoder       Nominatim + timezonefinder
                  app/services/chart_image    matplotlib → PNG
                  app/services/interpreter    Interpreter (Strategy) + RuleBased
                  app/data/                    справочники и тексты трактовок
```

ML-трактовка спрятана за интерфейсом `Interpreter` (паттерн Strategy). Сейчас —
бесплатный офлайн `RuleBasedInterpreter`. Позже без изменений в API можно
добавить `LLMInterpreter` (локальная Ollama или внешний бесплатный API).

## Запуск

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Открыть http://127.0.0.1:8000

## API

`POST /api/chart`

```json
{ "date": "15.08.1990", "time": "13:45", "place": "Москва" }
```

или с координатами (фолбэк, если геокодер недоступен):

```json
{ "date": "15.08.1990", "time": "13:45", "lat": 55.7558, "lon": 37.6173 }
```

Ответ: позиции планет, аспекты, трактовка (резюме + ≥10 разборов + блоки
сильные стороны / зоны роста / эмоции / рекомендации) и карта в base64-PNG.

Доп. параметры `/api/chart`:
- `time_unknown: true` — время неизвестно: карта строится на 12:00 без домов и
  Асцендента, в ответе `notice` и `birth.time_known=false`.
- `level: "beginner" | "expert"` — глубина трактовки (US-2.2).

`POST /api/compatibility` — синастрия двух людей (US-3.1):

```json
{ "a": { "date": "...", "time": "...", "place": "..." },
  "b": { "date": "...", "place": "...", "time_unknown": true } }
```

Ответ: общая совместимость `overall` (%/звёзды), оценки по 5 сферам (эмоции,
интеллект, быт, ценности, духовность) и ключевые межкарточные аспекты.

`GET /api/cities?q=` — автоподсказка городов из офлайн-справочника.

`GET /health` — health-check для мониторинга (US-T-2).

## Известные ограничения MVP

- Геокодинг: крупные города России/СНГ/мира резолвятся офлайн из встроенного
  справочника (`data/geo_cities.py`). Для остальных — онлайн-фолбэк Nominatim;
  если он недоступен, доступен ввод координат (`lat`/`lon`).
- Трактовка rule-based: связная и читаемая, но менее «живая», чем LLM.
- Дома — Placidus; для высоких широт возможны искажения (общее свойство системы).
