# Dev container / GitHub Codespaces

`devcontainer.json` é JSON puro (sem comentários), validado no CI (`job lint`).
Decisões:

- **Imagem** `mcr.microsoft.com/devcontainers/python:1-3.11-bookworm` — Python
  3.11 como o `pyproject.toml` exige (`>=3.11,<3.12`), Debian bookworm com
  `libgomp1` (XGBoost) e `pipx` já instalados.
- **uv via `pipx install uv==0.13.7`** no `postCreateCommand`, em vez da feature
  de terceiros `ghcr.io/va-h/devcontainers-features/uv`: `pipx` faz parte da
  imagem oficial e a versão fica fixada na mesma minor que gerou o `uv.lock`
  (0.13.x), sem depender de um repositório externo de features.
- `postCreateCommand` continua com `uv sync --frozen --all-extras` — o mesmo
  comando que o job `test` do CI exercita.
- `postAttachCommand` sobe o app Streamlit (`app/Home.py`) sem CORS/XSRF, como
  o Codespaces precisa para o preview da porta 8501.
- Portas 8501 (app, abre preview), 8000 (API: `make api`) e 5000 (MLflow:
  `make mlflow`), rotuladas.
- `UV_LINK_MODE=copy` evita avisos de hardlink entre o cache do uv e o volume
  do workspace; `MLFLOW_ALLOW_FILE_STORE=true` é exigido pelo MLflow >= 3.18
  para o file store `./mlruns`.
- Extensões: Python, Pylance e Ruff (formatador padrão para `.py`).

Primeiro `uv sync` demora alguns minutos (TensorFlow 2.20 + nvidia-nccl do
lock Linux, ~1 GB de wheels).
