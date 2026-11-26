"""Registra os três modelos XGBoost de demonstração (``models_demo/``) no Model Registry do MLflow.

Uso::

    uv run python -m tracking.registrar_modelos_demo --tracking-uri sqlite:///mlruns/mlflow.db

Para cada h em ``metadata.json["horizontes"]`` (1, 7, 30):

1. confere o sha256 de ``models_demo/xgboost_ar_cal_h{h}.ubj`` contra ``metadata.json``
   (``modelos[h].arquivo_sha256``) e **falha alto** se divergir; reconstrói a matriz de features
   pelo caminho canônico (``models_demo.comum.construir_para(h)``) e confere a ordem das colunas
   contra ``metadata.json``;
2. se o modelo registrado ``sp-resp-forecast-xgb-h{h}`` já tem uma versão com a tag
   ``sha256_modelo`` igual, **não cria nada** (nem run, nem versão): só garante que o apelido
   ``champion`` aponta para ela (idempotência);
3. senão, cria uma run no experimento ``modelos_demo`` (params: hiperparâmetros, lags, features,
   versão; tags ``versao``, ``sha256_modelo``, ``demonstracao``, ``provisorio``, ``horizonte``,
   ``fonte``; o model card e o ``metadata.json`` como artefatos), faz ``mlflow.xgboost.log_model``
   com assinatura inferida da matriz de features e um exemplo de entrada de 5 linhas, registra a
   versão (tags ``versao_dados``, ``sha256``, ``sha256_modelo``, ``horizonte``) e define o apelido
   ``champion`` nela.

Um modelo registrado por horizonte porque as features diferem (``y_lag1..`` em h = 1,
``y_lag30..`` em h = 30). Nada aqui treina, avalia ou calcula métrica: são modelos de
**demonstração**, não resultado da dissertação (``models_demo/MODEL_CARD.md``).

O Model Registry exige backend em banco: use ``sqlite:///...`` (o file store está em manutenção
no MLflow 3.18). Com ``sqlite:///<pasta>/mlflow.db`` e experimento novo, os artefatos vão para
``<pasta>/mlartifacts/`` (mesma regra de ``tracking/registro_mlflow.py``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR", "false")

import mlflow  # noqa: E402
import mlflow.xgboost  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from mlflow import MlflowClient  # noqa: E402
from mlflow.models.signature import infer_signature  # noqa: E402

from models_demo import comum  # noqa: E402
from tracking.registro_mlflow import _experimento, _requisitos, _silencio_mlflow  # noqa: E402

EXPERIMENTO_PADRAO = "modelos_demo"
APELIDO = "champion"
URL_MODEL_CARD = "https://github.com/matheusmmmp/sp-respiratory-admissions-forecast/blob/main/models_demo/MODEL_CARD.md"
LINHAS_EXEMPLO = 5


def nome_registrado(h: int) -> str:
    return f"sp-resp-forecast-xgb-h{int(h)}"


def descricao(h: int, meta: dict) -> str:
    m = meta["modelos"][str(h)]
    return (
        "**Demonstration model, not a dissertation result.** "
        f"XGBoost `{meta['feature_set']}` (objective `{m['hiperparametros']['objective']}`), horizon h = {h} days, "
        "daily respiratory admissions (ICD-10 J00-J99) of São Paulo city; trained on the whole 2019-2024 history "
        f"with a single seed ({meta['seed']}) for the API demo, which is not the dissertation protocol. "
        f"Model card: {URL_MODEL_CARD}"
    )


def _carregar_metadata() -> dict:
    if not comum.CAMINHO_METADATA.exists():
        raise RuntimeError(
            f"{comum.caminho_relativo(comum.CAMINHO_METADATA)} não existe; treine com `uv run python -m models_demo.treinar`"
        )
    return json.loads(comum.CAMINHO_METADATA.read_text(encoding="utf-8"))


def _conferir_modelo(h: int, meta: dict) -> str:
    """sha256 do ``.ubj`` == ``metadata.json``; devolve o sha256. Falha alto se divergir."""
    m = meta["modelos"][str(h)]
    p = comum.caminho_modelo(h)
    if not p.exists():
        raise RuntimeError(f"modelo ausente: {comum.caminho_relativo(p)}")
    sha = comum.sha256_arquivo(p)
    if sha != m["arquivo_sha256"]:
        raise RuntimeError(
            f"{comum.caminho_relativo(p)} diverge de metadata.json (sha256 {sha[:12]}… != {m['arquivo_sha256'][:12]}…); "
            "nada foi registrado"
        )
    return sha


def _frame_features(h: int, meta: dict) -> pd.DataFrame:
    """Matriz de features de ``comum.construir_para(h)`` (float32, ordem do treino) como DataFrame."""
    ds, colunas, _ = comum.construir_para(h)
    if list(colunas) != list(meta["modelos"][str(h)]["features"]):
        raise RuntimeError(f"h={h}: colunas construídas agora diferem das de metadata.json; retreine")
    X = comum.matriz(ds, colunas)
    df = pd.DataFrame(X, index=ds.X.index, columns=pd.Index([str(c) for c in colunas], dtype=object))
    # Index de colunas `object`: o MLflow 3.18 compara `df.columns == range(n)` ao salvar o exemplo,
    # o que o Index de strings do pandas 3 não implementa (mesma nota de registro_mlflow._normalizar_tipos).
    return df.reset_index(drop=True)


def _params(h: int, meta: dict) -> dict[str, str]:
    m = meta["modelos"][str(h)]
    p = {f"hp.{k}": str(v) for k, v in m["hiperparametros"].items()}
    p.update(
        {
            "horizonte": str(h),
            "versao": meta["versao"],
            "modelo": meta["modelo"],
            "feature_set": m["feature_set"],
            "blocos": ",".join(m["blocos"]),
            "lags_alvo": ",".join(str(x) for x in m["lags_alvo"]),
            "lags_exogenas": ",".join(str(x) for x in m["lags_exogenas"]),
            "features": ",".join(m["features"]),
            "n_features": str(len(m["features"])),
            "lag_minimo_das_features": str(m["lag_minimo_das_features"]),
            "n_linhas_treino": str(m["n_linhas_treino"]),
            "primeira_data_alvo": m["primeira_data_alvo"],
            "ultima_data_alvo": m["ultima_data_alvo"],
            "config": m["config"],
            "data_treino": meta["data_treino"],
            "seed": str(meta["seed"]),
        }
    )
    return p


def _tags_run(h: int, meta: dict, sha: str) -> dict[str, str]:
    return {
        "versao": meta["versao"],
        "sha256_modelo": sha,
        "demonstracao": "true",
        "provisorio": "true",
        "horizonte": str(h),
        "fonte": "models_demo/metadata.json",
        "mlflow.note.content": descricao(h, meta),
    }


def _tags_versao(h: int, meta: dict, sha: str) -> dict[str, str]:
    return {
        "versao_dados": meta["versao"],
        "sha256": sha,
        "sha256_modelo": sha,
        "horizonte": str(h),
        "demonstracao": "true",
        "provisorio": "true",
    }


def _garantir_modelo_registrado(client: MlflowClient, nome: str, h: int, meta: dict) -> None:
    tags = {"horizonte": str(h), "demonstracao": "true", "provisorio": "true", "feature_set": meta["feature_set"]}
    if client.search_registered_models(filter_string=f"name = '{nome}'"):
        client.update_registered_model(nome, description=descricao(h, meta))
    else:
        client.create_registered_model(nome, tags=tags, description=descricao(h, meta))


def _versao_existente(client: MlflowClient, nome: str, sha: str):
    iguais = [v for v in client.search_model_versions(f"name = '{nome}'") if v.tags.get("sha256_modelo") == sha]
    if len(iguais) > 1:
        raise RuntimeError(
            f"{nome}: {len(iguais)} versões com sha256_modelo {sha[:12]}…; o Registry está inconsistente"
        )
    return iguais[0] if iguais else None


def _garantir_apelido(client: MlflowClient, nome: str, versao: str) -> str:
    """Aponta ``champion`` para ``versao``; devolve o que aconteceu (``mantido``/``definido``/``movido de N``)."""
    try:
        atual = client.get_model_version_by_alias(nome, APELIDO).version
    except mlflow.exceptions.MlflowException:
        atual = None
    if str(atual) == str(versao):
        return "mantido"
    client.set_registered_model_alias(nome, APELIDO, str(versao))
    return "definido" if atual is None else f"movido de v{atual}"


def _registrar_h(client: MlflowClient, exp_id: str, h: int, meta: dict) -> dict:
    nome = nome_registrado(h)
    sha = _conferir_modelo(h, meta)
    _garantir_modelo_registrado(client, nome, h, meta)

    existente = _versao_existente(client, nome, sha)
    if existente is not None:
        acao = _garantir_apelido(client, nome, existente.version)
        return {"h": h, "nome": nome, "versao": int(existente.version), "criada": False, "apelido": acao}

    modelo = comum.carregar_modelo(h)
    X = _frame_features(h, meta)
    saida = modelo.predict(X.to_numpy(dtype=np.float32))
    assinatura = infer_signature(X, saida)
    exemplo = X.head(LINHAS_EXEMPLO)

    with mlflow.start_run(experiment_id=exp_id, run_name=f"{meta['modelo']}_h{h}__{meta['versao']}") as run:
        mlflow.log_params(_params(h, meta))
        mlflow.set_tags(_tags_run(h, meta, sha))
        mlflow.log_artifact(str(comum.PASTA_MODELOS / "MODEL_CARD.md"))
        mlflow.log_artifact(str(comum.CAMINHO_METADATA))
        with _silencio_mlflow():
            info = mlflow.xgboost.log_model(
                modelo,
                name=f"{meta['modelo']}_h{h}",
                signature=assinatura,
                input_example=exemplo,
                model_format="ubj",
                pip_requirements=_requisitos("xgboost", "scikit-learn"),
                tags={"sha256_modelo": sha, "versao": meta["versao"], "demonstracao": "true", "horizonte": str(h)},
            )
        mv = client.create_model_version(
            nome,
            source=info.model_uri,
            run_id=run.info.run_id,
            tags=_tags_versao(h, meta, sha),
            description=descricao(h, meta),
            model_id=info.model_id,
        )
    acao = _garantir_apelido(client, nome, mv.version)
    return {"h": h, "nome": nome, "versao": int(mv.version), "criada": True, "apelido": acao}


def registrar(tracking_uri: str, experimento: str = EXPERIMENTO_PADRAO, meta: dict | None = None) -> list[dict]:
    """Registra (ou confere) os modelos de demonstração; devolve um resumo por horizonte.

    ``meta`` existe para os testes (padrão: ``models_demo/metadata.json``). Antes de escrever
    qualquer coisa no MLflow, confere o sha256 dos três ``.ubj``: um divergente aborta tudo.
    """
    meta = meta if meta is not None else _carregar_metadata()
    horizontes = [int(h) for h in meta["horizontes"]]
    for h in horizontes:
        _conferir_modelo(h, meta)

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri)
    exp_id = _experimento(client, experimento, tracking_uri)
    return [_registrar_h(client, exp_id, h, meta) for h in horizontes]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--tracking-uri",
        default=os.environ.get("MLFLOW_TRACKING_URI"),
        help="backend em banco, ex.: sqlite:///mlruns/mlflow.db (padrão: MLFLOW_TRACKING_URI)",
    )
    ap.add_argument("--experimento", default=EXPERIMENTO_PADRAO)
    args = ap.parse_args(argv)
    if not args.tracking_uri:
        ap.error("informe --tracking-uri ou defina MLFLOW_TRACKING_URI")
    if not args.tracking_uri.startswith(("sqlite:", "postgresql", "mysql", "mssql", "http://", "https://")):
        ap.error("o Model Registry exige backend em banco (ex.: sqlite:///mlruns/mlflow.db)")
    db = args.tracking_uri[len("sqlite:///") :] if args.tracking_uri.startswith("sqlite:///") else None
    if db:
        Path(db).parent.mkdir(parents=True, exist_ok=True)

    for r in registrar(args.tracking_uri, args.experimento):
        estado = "versão nova" if r["criada"] else "já registrada (sha256 igual)"
        print(f"{r['nome']}: v{r['versao']} - {estado}; @{APELIDO} {r['apelido']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
