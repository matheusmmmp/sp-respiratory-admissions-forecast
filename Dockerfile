# syntax=docker/dockerfile:1.7
# ============================================================================
# sp-respiratory-admissions-forecast — imagem única para pytest, smoke, app
# (Streamlit), API (FastAPI) e UI do MLflow.
#
# Multi-stage com uv (https://docs.astral.sh/uv/guides/integration/docker/):
#   builder  -> resolve o ambiente a partir de pyproject.toml + uv.lock (--frozen),
#               sem dependências de desenvolvimento; copia o código.
#   runtime  -> (alvo padrão) só o venv pronto + código; CMD = smoke.
#   test     -> runtime + grupo dev (pytest, ruff); CMD = pytest && smoke.
#
#   docker build -t sp-resp-forecast .                      # runtime
#   docker build -t sp-resp-forecast:test --target test .   # testes
#   docker run --rm sp-resp-forecast                        # roda o smoke
#   docker run --rm sp-resp-forecast:test                   # pytest + smoke
#
# Observações:
# - pyproject tem `package = false`: `uv sync` instala só as dependências, e o
#   código é usado a partir de /app (pythonpath "." já está no pytest.ini_options;
#   PYTHONPATH=/app cobre `python -m src...`, uvicorn e streamlit).
# - Os extras `app`, `api` e `tracking` são preenchidos pelo gerente (WP2–WP4);
#   enquanto estiverem vazios o sync segue funcionando, só sem esses pacotes.
# - Sem `git` na imagem: o manifesto do runner grava commit = null (best-effort,
#   ver _git() em src/experiments/run_preliminary.py). Smoke nunca é resultado.
# - libgomp1: exigido em Linux pelos wheels do XGBoost/scikit-learn (OpenMP).
# - O lock Linux do TensorFlow 2.20 puxa nvidia-nccl-cu12 (~340 MB): a imagem
#   é grande por decisão de versões travadas da dissertação, não por este arquivo.
# ============================================================================

ARG PYTHON_IMAGE=python:3.11-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13

# ---------------------------------------------------------------- builder
FROM ${UV_IMAGE} AS uv-bin

FROM ${PYTHON_IMAGE} AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=uv-bin /uv /uvx /bin/

WORKDIR /app

# Camada de dependências (cacheada enquanto pyproject.toml/uv.lock não mudam).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --extra app --extra api --extra tracking

# Código e dados agregados (o que entra é controlado por .dockerignore:
# nunca .env, .cdsapirc, .git, .venv, reports/, mlruns/, dados brutos).
COPY . /app

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE} AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLBACKEND=Agg \
    TF_CPP_MIN_LOG_LEVEL=2

WORKDIR /app
COPY --from=builder /app /app

# Portas dos serviços do docker-compose.yml (Streamlit, FastAPI, MLflow).
EXPOSE 8501 8000 5000

# Padrão: smoke do pipeline (nunca é resultado; escreve em /app/reports).
CMD ["python", "-m", "src.experiments.run_preliminary", "--config", "configs/smoke.yaml", "--smoke"]

# ---------------------------------------------------------------- test
FROM runtime AS test

COPY --from=uv-bin /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Acrescenta o grupo dev (pytest, ruff) ao mesmo venv, ainda a partir do lock.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra app --extra api --extra tracking

CMD ["sh", "-c", "pytest -q && python -m src.experiments.run_preliminary --config configs/smoke.yaml --smoke"]
