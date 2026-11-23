"""Forecast API — demonstration service (FastAPI + pydantic).

Endpoints
---------
``GET /health``
    Service status, model version, horizons available and the range of valid
    origins per horizon.
``GET /forecast?h=<1|7|30>&origem=<YYYY-MM-DD>``
    Point forecast of daily respiratory admissions (ICD-10 J00-J99, São Paulo
    city) for the target date ``origem + h`` days, using only information
    observed up to ``origem``.

Origin x target
---------------
The canonical feature builder (``src/features/forecasting_features.py``)
indexes its frame by the TARGET date ``u`` and defines the origin as
``t = u - h``; every lagged feature ``<var>_lag<L>`` has ``L >= h`` (enforced
with ``raise`` in the builder), so the row for target ``u`` only contains values
observed up to ``t``. The API therefore maps ``origem`` to ``u = origem + h``,
takes that row of the canonical frame and feeds it to the model for ``h``.

Models and feature frames are loaded once, in the lifespan, and every input
file is checked against the sha256 recorded at training time. Any mismatch
aborts the startup: the service never serves a model whose data changed.

Everything served here is a demonstration (see ``models_demo/MODEL_CARD.md``):
single seed, whole-history training, and only target dates inside the history
can be materialised by the builder, so forecasts are in-sample by construction.
"""

from __future__ import annotations

import json
import math
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from xgboost import XGBRegressor

from models_demo import comum
from src.features.forecasting_features import DatasetExperimental

TITULO = "SP respiratory admissions forecast — demo API"
VERSAO_API = "0.1.0"


# ------------------------------------------------------------------ schemas
class JanelaOrigens(BaseModel):
    primeira: date = Field(description="Earliest origin with enough history for the lags of this horizon.")
    ultima: date = Field(description="Latest origin whose target date is inside the historical series.")


class HealthResponse(BaseModel):
    status: str
    modelo: str
    versao: str = Field(description="Model version: short sha256 of the target parquet + training date.")
    feature_set: str
    horizontes: list[int]
    historico: dict[str, date] = Field(description="First and last observed date of the target series.")
    origens_validas: dict[str, JanelaOrigens] = Field(description="Valid origin window per horizon (keys are h).")
    aviso: str


class ForecastResponse(BaseModel):
    h: int
    origem: date
    data_alvo: date
    previsao: float = Field(description="Expected number of admissions on data_alvo (point forecast, not rounded).")
    modelo: str
    versao: str
    aviso: str


# ------------------------------------------------------------------ service
@dataclass
class ModeloHorizonte:
    h: int
    ds: DatasetExperimental
    colunas: list[str]
    modelo: XGBRegressor
    primeira_data_alvo: pd.Timestamp
    ultima_data_alvo: pd.Timestamp

    @property
    def primeira_origem(self) -> date:
        return (self.primeira_data_alvo - pd.Timedelta(days=self.h)).date()

    @property
    def ultima_origem(self) -> date:
        return (self.ultima_data_alvo - pd.Timedelta(days=self.h)).date()


class ServicoPrevisao:
    def __init__(self, meta: dict, por_h: dict[int, ModeloHorizonte]):
        self.meta = meta
        self.por_h = por_h
        serie = next(iter(por_h.values())).ds.serie_alvo_completa
        self.hist_inicio: date = serie.index.min().date()
        self.hist_fim: date = serie.index.max().date()

    # ---- loading (fails loud) --------------------------------------------
    @classmethod
    def carregar(cls) -> "ServicoPrevisao":
        if not comum.CAMINHO_METADATA.exists():
            raise RuntimeError(
                f"{comum.caminho_relativo(comum.CAMINHO_METADATA)} not found; train the demo models with "
                "`uv run python -m models_demo.treinar`"
            )
        meta = json.loads(comum.CAMINHO_METADATA.read_text(encoding="utf-8"))

        # the data on disk must be the data the models were trained on
        for nome, info in meta["entradas"].items():
            if nome == "periodo":
                continue
            p = comum.RAIZ / info["arquivo"]
            if not p.exists():
                raise RuntimeError(f"input file missing: {info['arquivo']}")
            atual = comum.sha256_arquivo(p)
            if atual != info["sha256"]:
                raise RuntimeError(
                    f"{info['arquivo']} changed since the demo models were trained "
                    f"(sha256 {atual[:12]}… != {info['sha256'][:12]}…); retrain with `uv run python -m models_demo.treinar`"
                )

        por_h: dict[int, ModeloHorizonte] = {}
        for h in meta["horizontes"]:
            h = int(h)
            m = meta["modelos"][str(h)]
            ds, colunas, _ = comum.construir_para(h)
            if list(colunas) != list(m["features"]):
                raise RuntimeError(
                    f"h={h}: feature columns built now differ from the ones recorded at training time "
                    f"({len(colunas)} vs {len(m['features'])}); retrain"
                )
            p_modelo = comum.caminho_modelo(h)
            if not p_modelo.exists():
                raise RuntimeError(
                    f"model file missing: {comum.caminho_relativo(p_modelo)}; train with `uv run python -m models_demo.treinar`"
                )
            sha = comum.sha256_arquivo(p_modelo)
            if sha != m["arquivo_sha256"]:
                raise RuntimeError(
                    f"{comum.caminho_relativo(p_modelo)} does not match metadata.json (sha256 {sha[:12]}…); retrain"
                )
            modelo = comum.carregar_modelo(h)
            if int(modelo.n_features_in_) != len(colunas):
                raise RuntimeError(f"h={h}: model expects {modelo.n_features_in_} features, frame has {len(colunas)}")
            por_h[h] = ModeloHorizonte(
                h=h,
                ds=ds,
                colunas=list(colunas),
                modelo=modelo,
                primeira_data_alvo=ds.datas_alvo.min(),
                ultima_data_alvo=ds.datas_alvo.max(),
            )
        return cls(meta, por_h)

    # ---- serving ----------------------------------------------------------
    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            modelo=self.meta["modelo"],
            versao=self.meta["versao"],
            feature_set=self.meta["feature_set"],
            horizontes=sorted(self.por_h),
            historico={"inicio": self.hist_inicio, "fim": self.hist_fim},
            origens_validas={
                str(h): JanelaOrigens(primeira=mh.primeira_origem, ultima=mh.ultima_origem)
                for h, mh in sorted(self.por_h.items())
            },
            aviso=self.meta["aviso"],
        )

    def prever(self, h: int, origem: date) -> ForecastResponse:
        if h not in self.por_h:
            raise HTTPException(
                status_code=422,
                detail=f"h={h} is not served; available horizons: {sorted(self.por_h)}",
            )
        mh = self.por_h[h]
        if not (self.hist_inicio <= origem <= self.hist_fim):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"origem={origem} is outside the historical series "
                    f"({self.hist_inicio}..{self.hist_fim}); the demo can only forecast from observed origins"
                ),
            )
        alvo = origem + timedelta(days=h)
        if origem < mh.primeira_origem:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"origem={origem} has insufficient history for the lags of h={h} "
                    f"(the lags need {(mh.primeira_origem - self.hist_inicio).days} days of data before the origin); "
                    f"first valid origin for h={h}: {mh.primeira_origem}"
                ),
            )
        if origem > mh.ultima_origem:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"target date {alvo} (origem {origem} + {h} days) is beyond the end of the historical series "
                    f"({self.hist_fim}); the canonical feature builder only materialises observed target dates, "
                    f"so the last valid origin for h={h} is {mh.ultima_origem}"
                ),
            )
        previsao = comum.prever_direto(mh.modelo, mh.ds, mh.colunas, alvo)
        if not math.isfinite(previsao):
            raise HTTPException(status_code=500, detail=f"model returned a non-finite forecast for {alvo}")
        return ForecastResponse(
            h=h,
            origem=origem,
            data_alvo=alvo,
            previsao=previsao,
            modelo=self.meta["modelo"],
            versao=self.meta["versao"],
            aviso=self.meta["aviso"],
        )


# ------------------------------------------------------------------ app
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.servico = ServicoPrevisao.carregar()
    yield
    app.state.servico = None


app = FastAPI(
    title=TITULO,
    version=VERSAO_API,
    description=(
        "Demonstration API for the daily forecast of respiratory hospital admissions (ICD-10 J00-J99) "
        "in São Paulo city. XGBoost AR_CAL models, horizons 1, 7 and 30 days. "
        "Demonstration model, not a dissertation result (see models_demo/MODEL_CARD.md)."
    ),
    lifespan=lifespan,
)


def _servico(request: Request) -> ServicoPrevisao:
    servico = getattr(request.app.state, "servico", None)
    if servico is None:
        raise HTTPException(status_code=503, detail="models not loaded")
    return servico


@app.get("/health", response_model=HealthResponse, summary="Service status and model version")
def health(request: Request) -> HealthResponse:
    return _servico(request).health()


@app.get("/forecast", response_model=ForecastResponse, summary="Point forecast for origem + h days")
def forecast(
    request: Request,
    h: int = Query(..., description="Forecast horizon in days: 1, 7 or 30."),
    origem: date = Query(..., description="Forecast origin (YYYY-MM-DD); only data up to this date is used."),
) -> ForecastResponse:
    return _servico(request).prever(h, origem)
