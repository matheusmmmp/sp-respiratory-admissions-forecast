"""Optional model source for the API: the MLflow Model Registry (off by default).

By default the API reads the ``.ubj`` files in ``models_demo/`` (``api/main.py``), and this
module is not even imported. It is used only when the environment says so::

    MODELO_FONTE=mlflow
    MLFLOW_TRACKING_URI=sqlite:///mlruns/mlflow.db   # the registry filled by tracking/registrar_modelos_demo.py

Then, for each horizon ``h``, :func:`carregar_modelo` resolves
``models:/sp-resp-forecast-xgb-h{h}@champion`` and returns an ``XGBRegressor`` equivalent to the
``.ubj`` file. It fails loud (``RuntimeError``) when

* the version's tag ``sha256_modelo`` differs from ``models_demo/metadata.json``;
* the downloaded model file differs from that sha256 (the MLflow xgboost flavor stores the same
  UBJSON bytes as ``models_demo/``, so the check is byte for byte);
* the signature's input columns differ from the features recorded in ``metadata.json``.

``mlflow`` is imported only inside this path: the slim image of the API (``api/Dockerfile``,
``api/requirements.txt``) has no mlflow and never takes it.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from xgboost import XGBRegressor

from models_demo import comum

APELIDO = "champion"
FONTES = ("ubj", "mlflow")


def nome_registrado(h: int) -> str:
    # same rule as tracking/registrar_modelos_demo.nome_registrado (not imported: that module needs mlflow at import)
    return f"sp-resp-forecast-xgb-h{int(h)}"


def fonte() -> str:
    """``"ubj"`` (default, also when ``MODELO_FONTE`` is unset or empty) or ``"mlflow"``."""
    valor = os.environ.get("MODELO_FONTE", "").strip().lower() or "ubj"
    if valor not in FONTES:
        raise RuntimeError(f"MODELO_FONTE={valor!r} is not supported; use one of {list(FONTES)} or leave it unset")
    return valor


def carregar_modelo(h: int, info_modelo: dict) -> XGBRegressor:
    """Model for horizon ``h`` from the Registry (``MODELO_FONTE=mlflow``).

    ``info_modelo`` is ``metadata.json["modelos"][str(h)]``: its ``arquivo_sha256`` and
    ``features`` are what the registered version must match.
    """
    if fonte() != "mlflow":
        raise RuntimeError("api.registro.carregar_modelo is only for MODELO_FONTE=mlflow")
    uri = os.environ.get("MLFLOW_TRACKING_URI", "").strip()
    if not uri:
        raise RuntimeError("MODELO_FONTE=mlflow requires MLFLOW_TRACKING_URI (e.g. sqlite:///mlruns/mlflow.db)")

    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    os.environ.setdefault("MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR", "false")
    import mlflow
    import mlflow.xgboost
    from mlflow import MlflowClient
    from mlflow.exceptions import MlflowException

    nome = nome_registrado(h)
    esperado = info_modelo["arquivo_sha256"]
    client = MlflowClient(uri)
    try:
        versao = client.get_model_version_by_alias(nome, APELIDO)
    except MlflowException as e:
        raise RuntimeError(
            f"h={h}: models:/{nome}@{APELIDO} not found in the registry; register the demo models with "
            "`uv run python -m tracking.registrar_modelos_demo --tracking-uri <uri>`"
        ) from e
    tag = versao.tags.get("sha256_modelo")
    if tag != esperado:
        raise RuntimeError(
            f"h={h}: models:/{nome}@{APELIDO} (v{versao.version}) has sha256_modelo {str(tag)[:12]}… "
            f"but metadata.json says {esperado[:12]}…; re-register the demo models"
        )

    # pin the version resolved above (the alias could move between the check and the download)
    uri_versao = f"models:/{nome}/{versao.version}"
    mlflow.set_tracking_uri(uri)
    colunas = mlflow.models.get_model_info(uri_versao).signature.inputs.input_names()
    if list(colunas) != list(info_modelo["features"]):
        raise RuntimeError(
            f"h={h}: signature of {uri_versao} has columns {colunas}, metadata.json has {info_modelo['features']}"
        )
    with tempfile.TemporaryDirectory(prefix="modelo_registry_") as tmp:
        local = Path(mlflow.artifacts.download_artifacts(artifact_uri=uri_versao, dst_path=tmp))
        arquivos = sorted(local.glob("model.*"))
        if len(arquivos) != 1:
            raise RuntimeError(f"h={h}: expected one model file in {uri_versao}, found {[p.name for p in arquivos]}")
        sha = comum.sha256_arquivo(arquivos[0])
        if sha != esperado:
            raise RuntimeError(
                f"h={h}: model file of {uri_versao} does not match metadata.json (sha256 {sha[:12]}… != {esperado[:12]}…)"
            )
        modelo = mlflow.xgboost.load_model(str(local))
    if not isinstance(modelo, XGBRegressor):
        raise RuntimeError(f"h={h}: {uri_versao} loaded as {type(modelo).__name__}, expected XGBRegressor")
    return modelo
