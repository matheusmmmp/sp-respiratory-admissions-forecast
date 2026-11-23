# Forecast API (demonstration)

FastAPI service that serves the demonstration XGBoost `AR_CAL` models in
`models_demo/` (horizons 1, 7 and 30 days). **Demonstration, not a
dissertation result** — read `models_demo/MODEL_CARD.md` before quoting any
number.

## Run

Train the demo models once (a few seconds on CPU; they are versioned, so this
is only needed after the data changes):

```
uv run python -m models_demo.treinar
```

Start the server (the `api` extra in `pyproject.toml` provides `fastapi` and
`uvicorn`):

```
uv run uvicorn api.main:app --reload --port 8000
```

or, with the project's Docker Compose, `docker compose up api` (service `api`,
port 8000, `uvicorn api.main:app --host 0.0.0.0 --port 8000`). Interactive docs
at `http://localhost:8000/docs`.

At startup the service builds the canonical feature frames with
`src/features/forecasting_features.py`, verifies the sha256 of every input
file and model against `models_demo/metadata.json`, and loads the three models
once. Any mismatch aborts the startup (no silent fallback).

## Endpoints

### `GET /health`

```
curl -s localhost:8000/health
```

```json
{
  "status": "ok",
  "modelo": "xgboost_ar_cal",
  "versao": "ba6d6c40-20261123",
  "feature_set": "AR_CAL",
  "horizontes": [1, 7, 30],
  "historico": {"inicio": "2019-01-01", "fim": "2024-12-31"},
  "origens_validas": {
    "1":  {"primeira": "2019-01-28", "ultima": "2024-12-30"},
    "7":  {"primeira": "2019-01-28", "ultima": "2024-12-24"},
    "30": {"primeira": "2019-01-28", "ultima": "2024-12-01"}
  },
  "aviso": "demonstration model: ..."
}
```

### `GET /forecast?h=<1|7|30>&origem=<YYYY-MM-DD>`

Point forecast of the number of respiratory admissions on `origem + h` days,
using only information observed up to `origem`.

```
curl -s "localhost:8000/forecast?h=1&origem=2024-06-30"
curl -s "localhost:8000/forecast?h=7&origem=2024-06-30"
curl -s "localhost:8000/forecast?h=30&origem=2024-06-30"
```

```json
{
  "h": 7,
  "origem": "2024-06-30",
  "data_alvo": "2024-07-07",
  "previsao": 171.52,
  "modelo": "xgboost_ar_cal",
  "versao": "ba6d6c40-20261123",
  "aviso": "demonstration model: trained on the whole 2019-2024 history with a single seed ..."
}
```

(`previsao` above is illustrative; the real value comes from the model.)

### Errors (HTTP 422, with a message naming the valid bound)

| case | example |
|---|---|
| `h` not in {1, 7, 30} | `curl -s "localhost:8000/forecast?h=2&origem=2024-06-30"` |
| origin outside 2019-01-01..2024-12-31 | `curl -s "localhost:8000/forecast?h=1&origem=2025-01-01"` |
| not enough history for the lags | `curl -s "localhost:8000/forecast?h=30&origem=2019-01-01"` |
| target `origem + h` beyond 2024-12-31 | `curl -s "localhost:8000/forecast?h=7&origem=2024-12-31"` |
| malformed date | `curl -s "localhost:8000/forecast?h=1&origem=30/06/2024"` |

## Origin × target (how leakage is prevented)

The feature builder indexes rows by the **target date** `u` and defines the
origin as `t = u − h`. Every lagged feature `<var>_lag<L>` has `L ≥ h`
(the builder raises otherwise), so the row for `u` only contains values
observed up to `t`; calendar columns describe `u` and are known in advance.
The API maps `origem → u = origem + h` and feeds that row to the model for `h`.

Because the builder only materialises target dates that exist in the history,
the demo can only answer for origins whose target lies on or before
2024-12-31, and all such dates were in the training set (see "Limitations" in
the model card).

## Tests

```
uv run pytest tests/test_api_forecast.py -q
```

The tests do not train; they fail (not skip) if `models_demo/` is empty.
