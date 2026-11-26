# ============================================================================
# sp-respiratory-admissions-forecast — atalhos. Tudo via `uv run` (ambiente
# em .venv, dependências travadas em uv.lock). Receitas POSIX simples: valem
# em Linux/CI e no Git Bash do Windows.
#
#   make test         pytest (tests/; alguns minutos, inclui LSTM)
#   make smoke        teste de fumaça do pipeline (nunca é resultado)
#   make lint         ruff nos pacotes novos (app api tracking models_demo)
#   make app          Streamlit em http://localhost:8501
#   make api          FastAPI  em http://localhost:8000
#   make mlflow       MLflow UI em http://localhost:5000 (file store ./mlruns)
#
# Docker (exige o daemon; o CI roda tudo isto no job `docker`):
#   make docker-build imagem principal (Dockerfile da raiz, alvo runtime)
#   make docker-test  imagem `test`: pytest + smoke dentro do contêiner
#   make docker-api   imagem ENXUTA da API (api/Dockerfile, FastAPI + XGBoost CPU,
#                     sem TensorFlow) e sobe em http://localhost:7860 — a mesma
#                     imagem que vai para o Hugging Face Spaces
#   make up / down    docker compose (app 8501, api 8000, mlflow 5000)
#   make hf-space     monta a pasta do Space em $(HF_DESTINO) (fora do repo;
#                     ver deploy/hf_space/LEIA-ME.md; não faz push)
# ============================================================================

UV           ?= uv
PY           := $(UV) run python
SMOKE_CONFIG ?= configs/smoke.yaml
IMG          ?= sp-respiratory-admissions-forecast
HF_DESTINO   ?= ../sp-resp-forecast-space

# Código novo do portfólio (ruff bloqueante). src/ e tests/ são cópia curada da
# dissertação e acusam avisos de estilo (ver `make lint-legacy`), por isso não
# entram aqui. `wildcard` devolve só os diretórios que já existem.
LINT_PATHS := $(wildcard app api tracking models_demo deploy)

.PHONY: help sync test smoke lint lint-legacy format app api mlflow \
        docker-build docker-test docker-api up down hf-space precommit clean

help:
	@echo "alvos: test smoke lint lint-legacy format app api mlflow docker-build docker-test docker-api up down hf-space precommit clean"

sync:
	$(UV) sync --frozen --all-extras

test:
	$(UV) run pytest -q

smoke:
	$(PY) -m src.experiments.run_preliminary --config $(SMOKE_CONFIG) --smoke

lint:
ifeq ($(strip $(LINT_PATHS)),)
	@echo "lint: nenhum dos caminhos novos (app api tracking models_demo deploy) existe ainda; nada a verificar."
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
	MLFLOW_ALLOW_FILE_STORE=true $(UV) run mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri ./mlruns --default-artifact-root ./mlruns

# ---------------------------------------------------------------- Docker
docker-build:
	docker build -t $(IMG):local .

docker-test:
	docker build -t $(IMG):test --target test .
	docker run --rm $(IMG):test

# Imagem enxuta da API: contexto = raiz do repo, Dockerfile em api/. Ctrl-C derruba.
docker-api:
	docker build -f api/Dockerfile -t $(IMG):api .
	docker run --rm -p 7860:7860 $(IMG):api

up:
	docker compose up --build

down:
	docker compose down

# ---------------------------------------------------------------- Hugging Face Space
hf-space:
	$(PY) deploy/hf_space/montar_space.py --destino $(HF_DESTINO)

precommit:
	$(UV) run --with pre-commit pre-commit run --all-files

clean:
	$(PY) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', '.ruff_cache')]"
