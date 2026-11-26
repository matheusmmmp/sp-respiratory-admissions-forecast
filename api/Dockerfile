# syntax=docker/dockerfile:1.7
# ============================================================================
# api/Dockerfile — imagem ENXUTA da API de demonstração (FastAPI + XGBoost CPU),
# para o Hugging Face Spaces (sdk: docker) e para uso local (`make docker-api`).
#
# Contexto de build = RAIZ do repositório; todos os COPY usam caminhos relativos
# à raiz. deploy/hf_space/montar_space.py reproduz exatamente esse layout na
# pasta do Space, por isso este arquivo é copiado para lá SEM alteração.
#
#   docker build -f api/Dockerfile -t sp-respiratory-admissions-forecast:api .
#   docker run --rm -p 7860:7860 sp-respiratory-admissions-forecast:api
#   curl http://localhost:7860/health
#
# Exigências do HF Spaces: processo como usuário não-root (uid 1000) e servidor
# na porta 7860 (variável PORT). Nada de .env, .cdsapirc ou dados brutos entra:
# só os arquivos listados abaixo (os 4 de data/processed são conferidos por
# sha256 na subida da API contra models_demo/metadata.json).
# ============================================================================

ARG PYTHON_IMAGE=python:3.11-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13

FROM ${UV_IMAGE} AS uv-bin

# ---------------------------------------------------------------- builder
FROM ${PYTHON_IMAGE} AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0

COPY --from=uv-bin /uv /bin/uv
COPY api/requirements.txt /tmp/requirements.txt

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv \
    && uv pip install --python /opt/venv/bin/python --requirement /tmp/requirements.txt

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE} AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 user

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/user \
    PORT=7860

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv

# Código (só os módulos que a API importa; src/*/__init__.py são vazios).
COPY --chown=user:user api/__init__.py api/main.py api/
COPY --chown=user:user models_demo/__init__.py models_demo/comum.py models_demo/metadata.json models_demo/MODEL_CARD.md models_demo/
COPY --chown=user:user models_demo/xgboost_ar_cal_h1.ubj models_demo/xgboost_ar_cal_h7.ubj models_demo/xgboost_ar_cal_h30.ubj models_demo/
COPY --chown=user:user src/__init__.py src/
COPY --chown=user:user src/features/__init__.py src/features/forecasting_features.py src/features/
COPY --chown=user:user src/models/__init__.py src/models/base.py src/models/xgboost_model.py src/models/

# Configs dos três horizontes servidos (models_demo/comum.py::CONFIG_POR_HORIZONTE).
COPY --chown=user:user configs/h1_v02_cetesb_cetesb_classicos.yaml configs/
COPY --chown=user:user configs/multihorizonte/mh_h7_cetesb_cetesb.yaml configs/multihorizonte/mh_h30_cetesb_cetesb.yaml configs/multihorizonte/

# Dados agregados diários que o construtor de features abre (sha256 em metadata.json).
COPY --chown=user:user data/processed/sih_daily_lookahead.parquet data/processed/cams_daily_v2.csv data/processed/cetesb_poluentes_daily.csv data/processed/cetesb_meteo_daily.csv data/processed/

USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, sys, urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '7860'), timeout=3).status == 200 else 1)"

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
