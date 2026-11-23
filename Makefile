# ============================================================================
# sp-respiratory-admissions-forecast — atalhos. Tudo via `uv run` (ambiente
# em .venv, dependências travadas em uv.lock). Receitas POSIX simples: valem
# em Linux/CI e no Git Bash do Windows.
#
#   make test     pytest (tests/; ~5 min, inclui LSTM)
#   make smoke    teste de fumaça do pipeline (nunca é resultado)
#   make lint     ruff nos pacotes novos (app api tracking models_demo)
#   make app      Streamlit em http://localhost:8501
#   make api      FastAPI  em http://localhost:8000
#   make mlflow   MLflow UI em http://localhost:5000 (file store ./mlruns)
# ============================================================================

UV           ?= uv
PY           := $(UV) run python
SMOKE_CONFIG ?= configs/smoke.yaml

# Código novo do portfólio (ruff bloqueante). src/ e tests/ são cópia curada da
# dissertação e acusam avisos de estilo (ver `make lint-legacy`), por isso não
# entram aqui. `wildcard` devolve só os diretórios que já existem.
LINT_PATHS := $(wildcard app api tracking models_demo)

.PHONY: help sync test smoke lint lint-legacy format app api mlflow \
        docker-build docker-test up down precommit clean

help:
	@echo "alvos: test smoke lint lint-legacy format app api mlflow docker-build docker-test up down precommit clean"

sync:
	$(UV) sync --frozen --all-extras

test:
	$(UV) run pytest -q

smoke:
	$(PY) -m src.experiments.run_preliminary --config $(SMOKE_CONFIG) --smoke

lint:
ifeq ($(strip $(LINT_PATHS)),)
	@echo "lint: nenhum dos caminhos novos (app api tracking models_demo) existe ainda; nada a verificar."
else
	$(UV) run ruff check $(LINT_PATHS)
	$(UV) run ruff format --check $(LINT_PATHS)
endif

# Informativo: código herdado da dissertação (não bloqueia; não corrigir sem decisão do gerente).
lint-legacy:
	-$(UV) run ruff check src tests --statistics

format:
ifeq ($(strip $(LINT_PATHS)),)
	@echo "format: nenhum dos caminhos novos existe ainda."
else
	$(UV) run ruff check --fix $(LINT_PATHS)
	$(UV) run ruff format $(LINT_PATHS)
endif

app:
	$(UV) run streamlit run app/Home.py --server.port 8501

api:
	$(UV) run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

mlflow:
	$(UV) run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri ./mlruns --default-artifact-root ./mlruns

# Docker (exige o daemon; não disponível na máquina do autor em 2026-11-23).
docker-build:
	docker build -t sp-respiratory-admissions-forecast:local .

docker-test:
	docker build -t sp-respiratory-admissions-forecast:test --target test .
	docker run --rm sp-respiratory-admissions-forecast:test

up:
	docker compose up --build

down:
	docker compose down

precommit:
	$(UV) run --with pre-commit pre-commit run --all-files

clean:
	$(PY) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', '.ruff_cache')]"
