"""Ponto de entrada ÚNICO do benchmark preliminar.

    python -m src.experiments.run_preliminary --config configs/preliminary_h1.yaml --smoke
    python -m src.experiments.run_preliminary --config configs/preliminary_h1.yaml --full

Orquestra: dataset compartilhado -> folds compartilhados -> os quatro modelos
-> métricas compartilhadas -> artefatos rastreáveis.

O runner não conhece o interior de nenhum modelo, e nenhum modelo conhece
splits ou métricas.

Falha alto (§39): fold vazio, timestamps divergentes entre modelos, previsão
incompleta, modelo obrigatório indisponível.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.data.validation import validar_serie_diaria  # noqa: E402
from src.evaluation import metrics as M          # noqa: E402
from src.evaluation.splits import build_folds, validar_folds  # noqa: E402
from src.experiments import selecao_progressiva as SP  # noqa: E402
from src.features.forecasting_features import construir_dataset  # noqa: E402
from src.models.gam_nb import GAMNBForecaster  # noqa: E402
from src.models.ingarch_nb import INGARCHNBForecaster  # noqa: E402
from src.models.lstm_model import LSTMForecaster  # noqa: E402
from src.models.naive import Naive, SeasonalNaive  # noqa: E402
from src.models.sarimax_model import SARIMAXForecaster  # noqa: E402
from src.models.xgboost_model import XGBoostForecaster  # noqa: E402

MODELOS_OBRIGATORIOS = ("naive", "seasonal_naive", "xgboost", "lstm")
#: Trilha clássica (PROTOCOLO §0.8). Entram quando `modelos.<nome>.ativo: true`;
#: o modo full não os exige, porque as runs v0.2 fecharam sem eles.
MODELOS_OPCIONAIS = ("sarimax", "gam_nb", "ingarch_nb")

#: Comandos de reconstrução, na ordem. Usados por `--data-mode rebuild`.
#: Cada entrada é (rótulo, módulo, argumentos, arquivo que deve existir depois).
PIPELINES_INGESTAO = (
    ("CETESB poluentes", "src.ingestion.cetesb_build_poluentes",
     ["--dir", "{downloads}"], "data/processed/cetesb_poluentes_daily.csv"),
    ("CETESB meteorologia", "src.ingestion.cetesb_build_meteo",
     ["--dir", "{downloads}"], "data/processed/cetesb_meteo_daily.csv"),
)


# ------------------------------------------------------------------ utilidades
def _git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=RAIZ, capture_output=True, text=True, timeout=15
        ).stdout.strip() or None
    except Exception:  # noqa: BLE001 - proveniência é best-effort
        return None


def _hash_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _caminho_dados(caminho: str | Path) -> Path:
    """Resolve um caminho declarado em `dados.*` da config.

    Relativo -> relativo à RAIZ do repositório (comportamento histórico).
    Absoluto -> usado como está. Permite apontar para um arquivo fora do repo
    (ex.: o CAMS rebaixado em D:/Project/dados_rebaixa_2026-10/) sem copiá-lo
    para data/processed/, que é o canônico e não deve ser tocado.
    """
    p = Path(caminho)
    return p if p.is_absolute() else RAIZ / p


def _caminho_no_manifesto(caminho: Path) -> str:
    """Como o manifesto registra um arquivo: relativo à RAIZ quando está dentro
    do repo (idêntico ao histórico), absoluto quando está fora."""
    try:
        return str(caminho.relative_to(RAIZ))
    except ValueError:
        return str(caminho)


def _versoes() -> dict:
    import scipy
    import sklearn
    import statsmodels

    import xgboost
    import tensorflow as tf

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "xgboost": xgboost.__version__,
        "tensorflow": tf.__version__,
        "scikit-learn": sklearn.__version__,
        "statsmodels": statsmodels.__version__,
        "scipy": scipy.__version__,
        "plataforma": platform.platform(),
    }


def _ler_frame_datado(caminho: Path) -> pd.DataFrame:
    """Lê um CSV com coluna `data` e devolve indexado por ela — só para o gate."""
    df = pd.read_csv(caminho)
    df["data"] = pd.to_datetime(df["data"])
    return df.set_index("data").sort_index()


def cams_frame_para_gate(caminho: Path) -> pd.DataFrame:
    return _ler_frame_datado(caminho)


def _ambiente_txt() -> str:
    """Congela a pilha realmente instalada — não a declarada nos manifestos.

    O projeto tem divergência conhecida entre `requirements.txt` (era TF 2.13) e
    o venv que executa (TF 2.20). Registrar o que rodou é a única forma de a run
    ser reproduzível apesar disso.
    """
    try:
        saida = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, timeout=120,
        ).stdout
    except Exception as exc:  # noqa: BLE001 - proveniência é best-effort
        saida = f"# pip freeze indisponível: {type(exc).__name__}: {exc}\n"
    cabecalho = (
        f"# executável: {sys.executable}\n"
        f"# python: {platform.python_version()}\n"
        f"# plataforma: {platform.platform()}\n"
        f"# gerado em: {datetime.now().isoformat(timespec='seconds')}\n\n"
    )
    return cabecalho + saida


def _reconstruir_dados(downloads: Path) -> list[dict]:
    """Executa os pipelines de ingestão. Só chamado com --data-mode rebuild."""
    registro = []
    for rotulo, modulo, args, produto in PIPELINES_INGESTAO:
        argv = [a.format(downloads=str(downloads)) for a in args]
        print(f"  reconstruindo {rotulo} ({modulo}) ...", flush=True)
        proc = subprocess.run(
            [sys.executable, "-m", modulo, *argv],
            cwd=RAIZ, capture_output=True, text=True,
        )
        ok = proc.returncode == 0 and (RAIZ / produto).exists()
        registro.append({
            "pipeline": rotulo, "modulo": modulo, "argv": argv,
            "returncode": proc.returncode, "produto": produto, "ok": ok,
            "stderr_final": proc.stderr.strip()[-400:] if proc.stderr else "",
        })
        if not ok:
            raise RuntimeError(
                f"ingestão '{rotulo}' falhou (returncode={proc.returncode}).\n"
                f"Produto esperado: {produto}\n"
                f"stderr: {proc.stderr.strip()[-800:]}"
            )
        print(f"    ok -> {produto}", flush=True)
    return registro


# Chaves que cada modelo realmente consome. Mantida em sincronia manual com os
# cfg.get() de _instanciar: se você acrescentar um cfg.get novo, acrescente aqui.
# Existe porque o construtor lê chave por chave e, sem esta verificação, uma chave
# nova no YAML seria descartada em silêncio — foi o que aconteceu com `objetivo`
# até 2026-09-20. O projeto prefere raise a degradação silenciosa.
CHAVES_POR_MODELO: dict[str, set[str]] = {
    "naive": set(),
    "seasonal_naive": set(),
    "xgboost": {
        "objetivo", "selecionar_objetivo", "n_estimators", "max_depth",
        "learning_rate", "subsample", "colsample_bytree", "min_child_weight",
        "reg_lambda", "early_stopping_rounds",
    },
    "lstm": {
        "unidades", "dropout", "learning_rate", "epocas", "batch_size",
        "paciencia", "blocos_customizados", "screening", "smoke",
    },
    "sarimax": {"grade", "truncar_negativos", "excluir_blocos", "maxiter", "n_jobs"},
    "gam_nb": {"k_splines", "lags_ar", "grade_penalizacao", "max_iter_alpha"},
    "ingarch_nb": {"excluir_blocos", "maxiter", "limite_alpha1", "tol"},
}
#: Classe de cada modelo — usada para consultar atributos de classe
#: (`usa_semente`) antes de instanciar.
CLASSE_POR_MODELO: dict[str, type] = {
    "naive": Naive,
    "seasonal_naive": SeasonalNaive,
    "xgboost": XGBoostForecaster,
    "lstm": LSTMForecaster,
    "sarimax": SARIMAXForecaster,
    "gam_nb": GAMNBForecaster,
    "ingarch_nb": INGARCHNBForecaster,
}
# Chaves de controle do runner, válidas em qualquer modelo.
CHAVES_DE_CONTROLE: set[str] = {"ativo"}


def _validar_chaves(nome: str, cfg: dict) -> None:
    """Rejeita chave de configuração que o construtor não leria.

    Sem isto, `modelos.lstm.recurrent_dropout: 0.2` no YAML não chegaria ao
    modelo e nada avisaria — o experimento rodaria com outra configuração que a
    declarada, e o capítulo de metodologia descreveria algo que não aconteceu.
    """
    conhecidas = CHAVES_POR_MODELO.get(nome, set()) | CHAVES_DE_CONTROLE
    desconhecidas = sorted(set(cfg) - conhecidas)
    if desconhecidas:
        raise ValueError(
            f"modelos.{nome}: chave(s) de configuração não consumida(s) pelo "
            f"construtor: {desconhecidas}. O valor seria ignorado em silêncio. "
            f"Chaves aceitas: {sorted(conhecidas)}. "
            f"Se a chave é nova, acrescente o cfg.get() correspondente em "
            f"_instanciar e registre-a em CHAVES_POR_MODELO."
        )


def _instanciar(nome: str, cfg: dict, seed: int, periodo_sazonal: int, lookback: int):
    _validar_chaves(nome, cfg)
    if nome == "naive":
        return Naive()
    if nome == "seasonal_naive":
        return SeasonalNaive(periodo_sazonal=periodo_sazonal)
    if nome == "xgboost":
        return XGBoostForecaster(
            objetivo=cfg.get("objetivo", "reg:squarederror"),
            selecionar_objetivo=cfg.get("selecionar_objetivo", False),
            seed=seed,
            n_estimators=cfg.get("n_estimators", 600),
            max_depth=cfg.get("max_depth", 5),
            learning_rate=cfg.get("learning_rate", 0.05),
            subsample=cfg.get("subsample", 0.8),
            colsample_bytree=cfg.get("colsample_bytree", 0.8),
            min_child_weight=cfg.get("min_child_weight", 5),
            reg_lambda=cfg.get("reg_lambda", 1.0),
            early_stopping_rounds=cfg.get("early_stopping_rounds", 50),
        )
    if nome == "lstm":
        return LSTMForecaster(
            lookback=lookback,
            unidades=cfg.get("unidades", 32),
            dropout=cfg.get("dropout", 0.2),
            learning_rate=cfg.get("learning_rate", 1e-3),
            epocas=cfg.get("epocas", 150),
            batch_size=cfg.get("batch_size", 32),
            paciencia=cfg.get("paciencia", 15),
            seed=seed,
        )
    if nome == "sarimax":
        return SARIMAXForecaster(
            periodo_sazonal=periodo_sazonal,
            grade=cfg.get("grade"),
            truncar_negativos=cfg.get("truncar_negativos", False),
            maxiter=cfg.get("maxiter", 200),
            n_jobs=cfg.get("n_jobs", 1),
        )
    if nome == "gam_nb":
        kw = {}
        if cfg.get("lags_ar") is not None:
            kw["lags_ar"] = cfg["lags_ar"]
        if cfg.get("grade_penalizacao") is not None:
            kw["grade_penalizacao"] = cfg["grade_penalizacao"]
        return GAMNBForecaster(
            k_splines=cfg.get("k_splines", 5),
            max_iter_alpha=cfg.get("max_iter_alpha", 10),
            **kw,
        )
    if nome == "ingarch_nb":
        return INGARCHNBForecaster(
            maxiter=cfg.get("maxiter", 2000),
            limite_alpha1=cfg.get("limite_alpha1", 0.99),
            tol=cfg.get("tol", 1e-9),
        )
    raise ValueError(
        f"modelo desconhecido: {nome!r}. Aceitos: {MODELOS_OBRIGATORIOS + MODELOS_OPCIONAIS}"
    )


def _colunas_para(ds, nome_modelo: str, blocos, mcfg: dict) -> list[str]:
    """Quais colunas/canais do dataset cada modelo recebe para um conjunto de blocos."""
    if nome_modelo == "lstm":
        return ds.canais(blocos)
    if nome_modelo == "xgboost":
        return ds.colunas(blocos)
    if nome_modelo in ("sarimax", "ingarch_nb"):
        # exógenas = colunas defasadas do conjunto; `excluir_blocos` permite ao
        # pesquisador retirar, p.ex., o bloco AR (redundante com o polinômio AR
        # do próprio SARIMAX) sem mudar o conjunto para os outros modelos.
        # No INGARCH-NB o padrão (chave ausente) já é [AR]: o termo
        # log(y_{t-1}+1) e a realimentação de mu são a memória do alvo.
        padrao = ["AR"] if nome_modelo == "ingarch_nb" else []
        bruto = mcfg.get("excluir_blocos")
        excluir = set(padrao if bruto is None else bruto)
        desconhecidos = sorted(excluir - set(ds.ordem_blocos))
        if desconhecidos:
            raise ValueError(f"modelos.{nome_modelo}.excluir_blocos: blocos desconhecidos {desconhecidos}")
        restantes = [b for b in blocos if b not in excluir]
        return ds.colunas(restantes) if restantes else []
    if nome_modelo == "gam_nb":
        # todas as colunas defasadas do conjunto; o modelo decide o papel de
        # cada uma (linear, categórica, spline ou descartada) e registra no manifesto
        return ds.colunas(blocos)
    return []


# ----------------------------------------------------------------------- runner
def executar(caminho_config: Path, modo: str, data_mode: str = "cache",
             downloads: Path | None = None, mlflow_opcoes: dict | None = None) -> Path:
    cfg = yaml.safe_load(caminho_config.read_text(encoding="utf-8"))
    if modo not in ("smoke", "screening", "full"):
        raise ValueError(f"modo desconhecido: {modo!r}")
    smoke = modo == "smoke"

    seed = int(cfg["run"]["seed"])
    # §4.1: >=5 sementes, reportar média e dispersão. Nunca a melhor semente.
    sementes = [int(s) for s in cfg["run"].get("sementes", [seed])]
    exp = cfg["experimento"]
    split_cfg = dict(cfg["split"])
    sets_cfg = dict(cfg["feature_sets"])
    modelos_cfg = {k: dict(v) for k, v in cfg["modelos"].items()}

    if smoke:
        s = cfg.get("smoke", {})
        split_cfg.update(
            {k: s[k] for k in ("n_folds", "dias_teste", "dias_validacao", "treino_minimo") if k in s}
        )
        if "sementes" in s:
            sementes = [int(v) for v in s["sementes"]]
        if "epocas" in s:
            modelos_cfg["lstm"]["epocas"] = s["epocas"]
            modelos_cfg["lstm"]["paciencia"] = max(2, int(s["epocas"]) // 2)
        if "n_estimators" in s:
            modelos_cfg["xgboost"]["n_estimators"] = s["n_estimators"]
            modelos_cfg["xgboost"]["early_stopping_rounds"] = 10
        if "feature_sets" in s:
            sets_cfg = {k: v for k, v in sets_cfg.items() if k in s["feature_sets"]}
        # grade reduzida do SARIMAX no smoke: a grade completa tem 124 ordens
        if "sarimax_grade" in s and "sarimax" in modelos_cfg:
            modelos_cfg["sarimax"]["grade"] = dict(s["sarimax_grade"])

    if modo == "screening":
        s = cfg.get("screening", {})
        split_cfg.update(
            {k: s[k] for k in ("n_folds", "dias_teste", "dias_validacao", "treino_minimo") if k in s}
        )
        if "sementes" in s:
            sementes = [int(v) for v in s["sementes"]]
        for m in ("xgboost", "lstm"):
            for k in ("epocas", "n_estimators", "early_stopping_rounds", "paciencia"):
                if f"{m}_{k}" in s:
                    modelos_cfg[m][k] = s[f"{m}_{k}"]
        # a triagem pode desligar modelos: é o ponto dela
        for m, ligado in (s.get("modelos") or {}).items():
            if m in modelos_cfg:
                modelos_cfg[m]["ativo"] = bool(ligado)
        # e pode restringir os feature sets — usado na fase de CONFIRMAÇÃO, em
        # que só os candidatos aprovados na triagem larga vão para a LSTM
        if "feature_sets" in s:
            pedidos = list(s["feature_sets"])
            faltantes = [k for k in pedidos if k not in sets_cfg]
            if faltantes:
                raise RuntimeError(
                    f"screening.feature_sets pede {faltantes}, que não existem em "
                    f"feature_sets. Disponíveis: {sorted(sets_cfg)}"
                )
            sets_cfg = {k: sets_cfg[k] for k in pedidos}

    ativos = [
        m for m in MODELOS_OBRIGATORIOS + MODELOS_OPCIONAIS
        if modelos_cfg.get(m, {}).get("ativo", False)
    ]
    desconhecidos = sorted(set(modelos_cfg) - set(MODELOS_OBRIGATORIOS + MODELOS_OPCIONAIS))
    if desconhecidos:
        raise ValueError(
            f"modelos.{desconhecidos} não existem no runner. "
            f"Aceitos: {MODELOS_OBRIGATORIOS + MODELOS_OPCIONAIS}"
        )
    faltando = [m for m in MODELOS_OBRIGATORIOS if m not in ativos]
    if faltando and modo == "full":
        raise RuntimeError(f"modo full exige os quatro modelos; inativos: {faltando}")
    # A triagem dispensa os quatro, mas não dispensa a naive: MASE e skill são
    # definidos contra ela, e sem baseline a tabela perde a referência.
    if modo == "screening" and "naive" not in ativos:
        raise RuntimeError(
            "modo screening exige ao menos 'naive' ativo: MASE e skill são "
            "calculados contra ela. Inativos: " + str(faltando)
        )

    # ---------------------------------------------- proveniência, no INÍCIO
    #
    # Capturado ANTES de qualquer trabalho, e não junto do manifesto no fim.
    # Uma run longa pode terminar horas depois de começar; se o commit for lido
    # no fim, ele registra o estado do repositório NAQUELE momento — que pode
    # ser outro commit inteiramente. A run `preliminar_h1_full_20260727-161742`
    # tem exatamente esse defeito: começou 16:17, terminou depois de um commit
    # feito 16:32, e o manifesto atribui a ela um código que ela não executou.
    proveniencia = {
        "git_commit_no_inicio": _git("rev-parse", "HEAD"),
        "git_branch_no_inicio": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_sujo_no_inicio": bool(_git("status", "--porcelain")),
        "inicio": datetime.now().isoformat(timespec="seconds"),
    }

    # ------------------------------------------------------------- run id / saída
    carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{cfg['run']['nome']}_{modo}_{carimbo}"
    saida = RAIZ / "reports" / "experiments" / run_id
    (saida / "figures").mkdir(parents=True, exist_ok=True)
    print(f"RUN_ID: {run_id}\nsaída : {saida}\n", flush=True)

    # --mlflow: só registra (tracking/registro_mlflow.py); sem a opção, nada é importado
    reg = None
    if mlflow_opcoes:
        from tracking import registro_mlflow
        reg = registro_mlflow.iniciar(
            mlflow_opcoes, run_id=run_id, modo=modo, cfg=cfg, caminho_config=caminho_config,
            proveniencia=proveniencia, split=split_cfg, modelos=modelos_cfg, feature_sets=sets_cfg,
            sementes=sementes, ativos=ativos,
        )

    # ------------------------------------------------------------------ ingestão
    #
    # cache   — reutiliza o que existe, mas NÃO por existir: o gate de qualidade
    #           logo abaixo é que decide se o arquivo serve.
    # rebuild — reexecuta os pipelines de ingestão antes de seguir.
    registro_ingestao: list[dict] = []
    if data_mode == "rebuild":
        alvo_downloads = downloads or (Path.home() / "Downloads")
        print(f"--data-mode rebuild: reconstruindo a partir de {alvo_downloads}", flush=True)
        registro_ingestao = _reconstruir_dados(alvo_downloads)
    elif data_mode != "cache":
        raise ValueError(f"data_mode desconhecido: {data_mode!r}; use 'cache' ou 'rebuild'")

    # ------------------------------------------------------------------- dataset
    p_sih = _caminho_dados(cfg["dados"]["sih"])
    p_cams = _caminho_dados(cfg["dados"]["cams"])
    for p in (p_sih, p_cams):
        if not p.exists():
            raise RuntimeError(f"arquivo de dados ausente: {p}")

    fonte_pm25 = cfg["dados"].get("fonte_pm25", "cams")
    caminho_cetesb = cfg["dados"].get("cetesb")
    fonte_meteo = cfg["dados"].get("fonte_meteo", "cams")
    caminho_meteo = cfg["dados"].get("meteo")
    permitir_duas_fontes = bool(cfg["dados"].get("permitir_duas_fontes", False))
    ds = construir_dataset(
        caminho_sih=p_sih,
        caminho_cams=p_cams,
        horizonte=int(exp["horizonte"]),
        lags_alvo=exp["lags_alvo"],
        lags_exogenas=exp["lags_exogenas"],
        inicio=cfg["dados"].get("inicio"),
        fim=cfg["dados"].get("fim"),
        fonte_pm25=fonte_pm25,
        caminho_cetesb=_caminho_dados(caminho_cetesb) if caminho_cetesb else None,
        fonte_meteo=fonte_meteo,
        caminho_meteo=_caminho_dados(caminho_meteo) if caminho_meteo else None,
        blocos_customizados=cfg.get("blocos_customizados"),
        permitir_duas_fontes=permitir_duas_fontes,
    )
    print(f"fonte PM2.5: {fonte_pm25}  ·  fonte METEO: {fonte_meteo}"
          f"  ·  duas fontes trocadas: {permitir_duas_fontes}", flush=True)
    print("dataset:", json.dumps(ds.relatorio, ensure_ascii=False, indent=2), flush=True)

    # ------------------------------------------------------- DATA QUALITY GATE
    #
    # Roda sobre a série do desfecho no recorte efetivamente usado, e sobre a
    # cobertura de cada fonte exógena. FAIL aborta a run: seguir em frente com
    # dado reprovado produziria número sem valor científico.
    # O CAMS só entra no gate quando alguma fonte o usa (PROTOCOLO §0.22): numa base
    # CETESB/CETESB ele não alimenta feature nenhuma e não cobre 2025–2026.
    usa_cams = fonte_pm25 in ("cams", "hibrida") or fonte_meteo in ("cams", "hibrida")
    covariaveis = {"cams": cams_frame_para_gate(p_cams)} if usa_cams else {}
    if fonte_pm25 != "cams" and caminho_cetesb:
        covariaveis["cetesb_poluentes"] = _ler_frame_datado(_caminho_dados(caminho_cetesb))
    if fonte_meteo != "cams" and caminho_meteo:
        covariaveis["cetesb_meteo"] = _ler_frame_datado(_caminho_dados(caminho_meteo))

    laudo = validar_serie_diaria(
        alvo=ds.serie_alvo_completa,
        covariaveis=covariaveis,
        inicio=cfg["dados"].get("inicio"),
        fim=cfg["dados"].get("fim"),
    )
    print()
    laudo.imprimir()
    (saida / "data_quality.json").write_text(
        json.dumps(laudo.to_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    if laudo.reprovado:
        raise RuntimeError(
            "DATA QUALITY: FAIL — a modelagem não prossegue.\n"
            + "\n".join(f"  - {c.nome}: {c.detalhe}" for c in laudo.por_status("FAIL"))
            + f"\n\nLaudo completo: {saida / 'data_quality.json'}"
        )

    # A LSTM precisa de `lookback` dias ANTES da origem; apara-se o início para
    # que toda data-alvo tenha janela completa.
    lookback = int(exp["lookback"])
    recuo = lookback + int(exp["horizonte"]) - 1
    datas_validas = ds.datas_alvo[recuo:]
    if len(datas_validas) == 0:
        raise RuntimeError("nenhuma data-alvo com janela completa para a LSTM")

    folds = build_folds(datas_validas, **split_cfg)
    validar_folds(folds)
    print("\nfolds:")
    for f in folds:
        print("  ", json.dumps(f.resumo(), ensure_ascii=False), flush=True)

    # ------------------------------------- seleção progressiva (PROTOCOLO §0.24, Fase 2)
    #
    # Um conjunto pode ser uma especificação `selecao_progressiva` em vez de uma
    # lista de blocos: o conjunto é escolhido em cada fold sem tocar o teste
    # (src/experiments/selecao_progressiva.py). O primeiro conjunto tem de ser
    # uma lista: é nele que os baselines rodam.
    specs_selecao = {
        k: SP.validar_spec(k, v, ds.ordem_blocos, ativos) for k, v in sets_cfg.items() if SP.eh_selecao(v)
    }
    if specs_selecao and SP.eh_selecao(sets_cfg[list(sets_cfg)[0]]):
        raise ValueError("o primeiro feature set não pode ser de seleção progressiva (é o dos baselines)")
    selecoes: list[dict] = []

    # --------------------------------------------------------------- experimentos
    linhas_pred: list[pd.DataFrame] = []
    registros: list[dict] = []
    params_usados: dict = {}

    for nome_set, blocos_set in sets_cfg.items():
        spec_sel = specs_selecao.get(nome_set)
        for nome_modelo in ativos:
            mcfg = modelos_cfg[nome_modelo]
            # baselines não consomem feature set: rodam uma vez, no set de referência
            if nome_modelo in ("naive", "seasonal_naive") and nome_set != list(sets_cfg)[0]:
                continue
            if spec_sel is not None and nome_modelo not in spec_sel["modelos"]:
                continue

            for fold in folds:
                # Modelos deterministicos (baselines, SARIMAX): uma semente
                # basta. Modelos estocasticos rodam N sementes, porque a §4.1
                # exige media e dispersao — e porque as diferencas entre feature
                # sets sao da ordem do ruido de semente.
                sementes_aqui = sementes if CLASSE_POR_MODELO[nome_modelo].usa_semente else [seed]
                if spec_sel is None:
                    blocos = blocos_set
                else:
                    def _prever_interno(bl, fi, sd, _m=nome_modelo, _c=mcfg):
                        mod = _instanciar(_m, _c, sd, int(exp["periodo_sazonal"]), lookback)
                        cc = _colunas_para(ds, _m, bl, _c)
                        mod.fit(ds, fi, cc)
                        return mod.predict(ds, fi, cc)

                    sel = SP.selecionar(fold, spec_sel, sementes_aqui, _prever_interno,
                                        ds.y.loc[fold.validacao].to_numpy(dtype=float), ds.horizonte)
                    blocos = sel["blocos"]
                    selecoes.append({"model": nome_modelo, "feature_set": nome_set, **sel})
                    print(f"  sel {nome_modelo:15s} {nome_set:24s} fold{fold.id} -> "
                          f"{'+'.join(sel['acrescentados']) or '(só a base)'}", flush=True)
                cols = _colunas_para(ds, nome_modelo, blocos, mcfg)

                for sd in sementes_aqui:
                    modelo = _instanciar(
                        nome_modelo, mcfg, sd, int(exp["periodo_sazonal"]), lookback
                    )
                    if modelo.treinavel:
                        modelo.fit(ds, fold, cols)
                    pred = np.asarray(modelo.predict(ds, fold, cols), dtype=float)

                    if pred.shape[0] != len(fold.teste):
                        raise RuntimeError(
                            f"{nome_modelo}/{nome_set}/fold{fold.id}/seed{sd}: "
                            f"{pred.shape[0]} previsões para {len(fold.teste)} timestamps"
                        )
                    if np.isnan(pred).any():
                        raise RuntimeError(
                            f"{nome_modelo}/{nome_set}/fold{fold.id}/seed{sd}: previsões com NaN"
                        )

                    y_true = ds.y.loc[fold.teste].to_numpy(dtype=float)
                    rotulo = "baseline" if not modelo.treinavel else nome_set
                    linhas_pred.append(
                        pd.DataFrame(
                            {
                                "run_id": run_id,
                                "model": nome_modelo,
                                "feature_set": rotulo,
                                "seed": sd,
                                "fold": fold.id,
                                "forecast_origin": fold.teste - pd.Timedelta(days=ds.horizonte),
                                "target_date": fold.teste,
                                "horizon": ds.horizonte,
                                "y_true": y_true,
                                "y_pred": pred,
                            }
                        )
                    )
                    params_usados[f"{nome_modelo}|{rotulo}|fold{fold.id}|seed{sd}"] = modelo.params()
                    registros.append(
                        {"model": nome_modelo, "feature_set": rotulo, "seed": sd,
                         "fold": fold.id, "n_teste": len(fold.teste)}
                    )
                    if reg is not None:
                        reg.registrar_modelo(modelo, nome_modelo, rotulo, fold, sd, ds, cols, lookback)
                print(
                    f"  ok {nome_modelo:15s} {rotulo:24s} fold{fold.id} "
                    f"({len(sementes_aqui)} semente(s))",
                    flush=True,
                )

    pred_df = pd.concat(linhas_pred, ignore_index=True)
    pred_df["residual"] = pred_df["y_pred"] - pred_df["y_true"]
    pred_df["abs_error"] = pred_df["residual"].abs()

    # -------------------------------- §12: todos avaliados nos MESMOS timestamps
    referencia: dict = {}
    for (mdl, fset, sd, fld), g in pred_df.groupby(
        ["model", "feature_set", "seed", "fold"], sort=True
    ):
        carimbos = pd.DatetimeIndex(sorted(g["target_date"]))
        if fld not in referencia:
            referencia[fld] = carimbos
        elif not referencia[fld].equals(carimbos):
            raise RuntimeError(
                f"timestamps divergentes: {mdl}/{fset}/seed{sd}/fold{fld} difere da referência "
                f"do fold {fld}. A comparação entre modelos seria inválida."
            )

    # ------------------------------------------------------------------ métricas
    base = pred_df[pred_df["model"] == "naive"].set_index(["fold", "target_date"])["y_pred"]
    if base.empty:
        raise RuntimeError("naive ausente: MASE e skill não podem ser calculados")

    # nível mais fino: (modelo, feature set, semente, fold)
    por_fold: list[dict] = []
    for (mdl, fset, sd, fld), g in pred_df.groupby(
        ["model", "feature_set", "seed", "fold"], sort=True
    ):
        g = g.sort_values("target_date")
        yb = base.loc[fld].reindex(g["target_date"]).to_numpy(dtype=float)
        if np.isnan(yb).any():
            raise RuntimeError(f"baseline incompleto no fold {fld}")
        m = M.compute_all(g["y_true"].to_numpy(), g["y_pred"].to_numpy(), yb)
        por_fold.append(
            {
                "model": mdl, "feature_set": fset, "seed": sd, "fold": fld,
                "teste_inicio": str(g["target_date"].min().date()),
                "teste_fim": str(g["target_date"].max().date()),
                "n": len(g), **m,
            }
        )
    fold_df = pd.DataFrame(por_fold)

    # Média entre sementes DENTRO de cada fold: separa a dispersão de semente
    # (instabilidade do modelo) da dispersão entre folds (variação temporal).
    por_fold_medio = (
        fold_df.groupby(["model", "feature_set", "fold"], as_index=False)
        .agg(MAE=("MAE", "mean"), RMSE=("RMSE", "mean"), R2=("R2", "mean"),
             MASE=("MASE", "mean"), skill_MAE=("skill_MAE", "mean"),
             skill_RMSE=("skill_RMSE", "mean"), n_sementes=("seed", "nunique"))
    )

    #: dispersão ENTRE SEMENTES, dentro do fold — o que a §4.1 exige reportar
    disp_semente = (
        fold_df.groupby(["model", "feature_set", "fold"])["MAE"].std()
        .groupby(level=[0, 1]).mean().rename("MAE_std_semente").reset_index()
    )

    agg = (
        por_fold_medio.groupby(["model", "feature_set"])
        .agg(
            MAE_medio=("MAE", "mean"), MAE_std_fold=("MAE", "std"),
            RMSE_medio=("RMSE", "mean"), RMSE_std_fold=("RMSE", "std"),
            R2_medio=("R2", "mean"), MASE_medio=("MASE", "mean"),
            skill_MAE_medio=("skill_MAE", "mean"), skill_RMSE_medio=("skill_RMSE", "mean"),
            n_folds=("fold", "nunique"), n_sementes=("n_sementes", "max"),
        )
        .reset_index()
        .merge(disp_semente, on=["model", "feature_set"], how="left")
        .sort_values("MAE_medio")
    )

    # ----------------------------------------------------------------- artefatos
    status = (
        "PRELIMINARY_VALIDATED_TARGET"
        if cfg["dados"]["alvo"].get("validado_contra_fonte_oficial", False)
        else "PRELIMINARY_UNVALIDATED_TARGET"
    )

    # ------------------------------------------------------- ablação de features
    #
    # Recorta a tabela agregada para os modelos treináveis e mede, para cada um,
    # o efeito de cada bloco em relação à referência autorregressiva AR. É a
    # tabela que responde "de onde vem o sinal preditivo?".
    ablacao = _tabela_ablacao(agg, sets_cfg)
    ablacao.to_csv(saida / "feature_ablation.csv", index=False)

    # folds em CSV, além do manifesto — pedido explícito do protocolo
    pd.DataFrame([f.resumo() for f in folds]).to_csv(saida / "folds.csv", index=False)
    (saida / "environment.txt").write_text(_ambiente_txt(), encoding="utf-8")

    if selecoes:
        (saida / "selecao_progressiva.json").write_text(
            json.dumps({"specs": specs_selecao, "selecoes": selecoes}, ensure_ascii=False, indent=2, default=float),
            encoding="utf-8",
        )
        pd.DataFrame([
            {"model": s["model"], "feature_set": s["feature_set"], "fold": s["fold"],
             "acrescentados": "+".join(s["acrescentados"]), "n_passos": len(s["passos"])}
            for s in selecoes
        ]).to_csv(saida / "selecao_progressiva.csv", index=False)
    pred_df.to_csv(saida / "predictions.csv", index=False)
    fold_df.to_csv(saida / "metrics_by_fold.csv", index=False)
    agg.to_csv(saida / "model_comparison.csv", index=False)
    (saida / "model_comparison.tex").write_text(
        agg.to_latex(index=False, float_format="%.3f"), encoding="utf-8"
    )
    # default=str: o YAML converte `2019-01-01` em datetime.date, que o json
    # não serializa nativamente.
    (saida / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    (saida / "metrics.json").write_text(
        json.dumps(
            {"status": status, "modo": modo, "por_fold": por_fold,
             "agregado": agg.to_dict(orient="records")},
            ensure_ascii=False, indent=2, default=str,
        ),
        encoding="utf-8",
    )

    manifesto = {
        "run_id": run_id,
        "modo": modo,
        "status": status,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        # ⚠️ O que vale para reprodutibilidade é o estado NO INÍCIO: é o código
        # que a run efetivamente carregou. Os campos `*_no_fim` ficam só para
        # revelar se o repositório mudou durante a execução.
        "git_commit": proveniencia["git_commit_no_inicio"],
        "git_branch": proveniencia["git_branch_no_inicio"],
        "git_sujo": proveniencia["git_sujo_no_inicio"],
        "proveniencia": {
            **proveniencia,
            "fim": datetime.now().isoformat(timespec="seconds"),
            "git_commit_no_fim": _git("rev-parse", "HEAD"),
            "git_sujo_no_fim": bool(_git("status", "--porcelain")),
            "repositorio_mudou_durante_a_run": (
                _git("rev-parse", "HEAD") != proveniencia["git_commit_no_inicio"]
            ),
        },
        "dataset_sih": _caminho_no_manifesto(p_sih),
        "dataset_sih_sha256": _hash_arquivo(p_sih),
        "dataset_cams": _caminho_no_manifesto(p_cams),
        "dataset_cams_sha256": _hash_arquivo(p_cams),
        "fonte_pm25": fonte_pm25,
        "fonte_meteo": fonte_meteo,
        "permitir_duas_fontes": permitir_duas_fontes,
        "dataset_cetesb": caminho_cetesb,
        "dataset_cetesb_sha256": (
            _hash_arquivo(_caminho_dados(caminho_cetesb))
            if caminho_cetesb and _caminho_dados(caminho_cetesb).exists() else None
        ),
        "dataset_meteo": caminho_meteo,
        "dataset_meteo_sha256": (
            _hash_arquivo(_caminho_dados(caminho_meteo))
            if caminho_meteo and _caminho_dados(caminho_meteo).exists() else None
        ),
        "alvo": cfg["dados"]["alvo"],
        "relatorio_dataset": ds.relatorio,
        "folds": [f.resumo() for f in folds],
        "seed": seed,
        "sementes": sementes,
        "data_mode": data_mode,
        "ingestao_reexecutada": registro_ingestao,
        "data_quality": laudo.to_dict(),
        "config_sha256": hashlib.sha256(
            caminho_config.read_bytes()
        ).hexdigest(),
        "feature_sets": sets_cfg,
        "selecao_progressiva": [
            {"model": s["model"], "feature_set": s["feature_set"], "fold": s["fold"], "blocos": s["blocos"]}
            for s in selecoes
        ],
        "modelos": ativos,
        "modelos_deterministicos": [m for m in ativos if not CLASSE_POR_MODELO[m].usa_semente],
        # PROTOCOLO §0.18 [PROPOSTO]: contagem de previsões negativas sempre
        # registrada, truncamento só por config. Somado a partir de params().
        "previsoes_negativas_por_modelo": _resumo_negativos(params_usados),
        "parametros_por_execucao": params_usados,
        "versoes": _versoes(),
        "n_predicoes": int(len(pred_df)),
    }
    (saida / "manifest.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    diagnostico = _diagnostico_temporal(ds.serie_alvo_completa)
    (saida / "diagnostico_temporal.json").write_text(
        json.dumps(diagnostico, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    maiores_erros = (
        pred_df.sort_values("abs_error", ascending=False)
        .head(15)[["model", "feature_set", "fold", "target_date", "y_true", "y_pred", "abs_error"]]
        .copy()
    )
    maiores_erros["target_date"] = maiores_erros["target_date"].astype(str).str.slice(0, 10)

    _figuras(pred_df, fold_df, agg, saida / "figures")
    _summary(saida, run_id, modo, status, cfg, ds, folds, agg, fold_df,
             laudo=laudo, ablacao=ablacao, diagnostico=diagnostico,
             sementes=sementes, maiores_erros=maiores_erros)
    if reg is not None:
        reg.finalizar(status=status, manifesto=manifesto, por_fold=por_fold,
                      agregado=agg.to_dict(orient="records"), saida=saida)

    print("\n" + "=" * 78)
    print(f"STATUS: {status}")
    print("=" * 78)
    print(agg.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    print(f"\nartefatos em: {saida}")
    return saida


# ------------------------------------------------------------------- artefatos
def _resumo_negativos(params_usados: dict) -> dict:
    """Soma, por modelo, as previsões negativas e truncadas declaradas em params()."""
    out: dict[str, dict] = {}
    for chave, p in params_usados.items():
        if not isinstance(p, dict) or "n_previsoes_negativas" not in p:
            continue
        modelo = chave.split("|")[0]
        acc = out.setdefault(modelo, {"n_previsoes_negativas": 0, "n_previsoes_truncadas": 0,
                                      "truncar_negativos": bool(p.get("truncar_negativos", False))})
        acc["n_previsoes_negativas"] += int(p.get("n_previsoes_negativas") or 0)
        acc["n_previsoes_truncadas"] += int(p.get("n_previsoes_truncadas") or 0)
    return out


def _tabela_ablacao(agg: pd.DataFrame, sets_cfg: dict) -> pd.DataFrame:
    """Efeito de cada feature set em relação a AR, por modelo treinável.

    `delta_MAE` negativo = o bloco MELHORA (erro menor que a referência AR).
    A referência é o menor feature set disponível na run — normalmente `AR`.
    """
    treinaveis = agg[agg["feature_set"] != "baseline"].copy()
    if treinaveis.empty:
        return pd.DataFrame()

    ordem = list(sets_cfg)
    referencia = "AR" if "AR" in ordem else ordem[0]
    linhas = []
    for modelo, g in treinaveis.groupby("model"):
        base = g[g["feature_set"] == referencia]
        mae_ref = float(base["MAE_medio"].iloc[0]) if len(base) else float("nan")
        for r in g.itertuples():
            linhas.append({
                "model": modelo,
                "feature_set": r.feature_set,
                "blocos": (
                    "selecao_progressiva" if SP.eh_selecao(sets_cfg.get(r.feature_set))
                    else "+".join(sets_cfg.get(r.feature_set, []))
                ),
                "MAE_medio": r.MAE_medio,
                "MAE_std_fold": r.MAE_std_fold,
                "MAE_std_semente": getattr(r, "MAE_std_semente", float("nan")),
                "referencia": referencia,
                "MAE_referencia": mae_ref,
                "delta_MAE": r.MAE_medio - mae_ref,
                # o delta só é interpretável se for maior que o ruído de semente
                # modelo determinístico (uma semente) tem std NaN: ruído zero
                "delta_maior_que_ruido_semente": (
                    abs(r.MAE_medio - mae_ref) > _ruido(getattr(r, "MAE_std_semente", 0))
                ),
                "skill_MAE_vs_naive": r.skill_MAE_medio,
            })
    return pd.DataFrame(linhas).sort_values(["model", "MAE_medio"])


def _ruido(v) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if np.isnan(v) else v


def _diagnostico_temporal(serie: pd.Series, lags=(1, 2, 3, 7, 14, 28)) -> dict:
    """ACF nos lags de interesse — responde 'por que o baseline funciona?'."""
    s = serie.dropna().astype(float)
    x = s.to_numpy()
    x = x - x.mean()
    denom = float((x * x).sum())
    acf = {}
    for L in lags:
        if L >= len(x):
            continue
        acf[f"lag{L}"] = round(float((x[L:] * x[:-L]).sum() / denom), 4) if denom else float("nan")
    por_dow = s.groupby(s.index.dayofweek).mean()
    return {
        "acf": acf,
        "media_por_dia_semana": {
            d: round(float(v), 2)
            for d, v in zip(["seg", "ter", "qua", "qui", "sex", "sab", "dom"], por_dow.to_numpy())
        },
        "amplitude_semanal": round(float(por_dow.max() - por_dow.min()), 2),
        "desvio_serie": round(float(s.std(ddof=1)), 2),
    }


def _figuras(pred_df, fold_df, agg, dirfig: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    melhor_set = agg.iloc[0]["feature_set"]
    sel = pred_df[(pred_df["feature_set"].isin([melhor_set, "baseline"]))]

    # observado x previsto
    fig, ax = plt.subplots(figsize=(14, 5))
    um = sel[sel["model"] == "naive"].sort_values("target_date")
    ax.plot(um["target_date"], um["y_true"], color="black", lw=1.2, label="observado")
    for mdl in sorted(sel["model"].unique()):
        g = sel[sel["model"] == mdl].sort_values("target_date")
        ax.plot(g["target_date"], g["y_pred"], lw=0.9, alpha=0.8, label=mdl)
    ax.set_title("Observado x previsto (blocos de teste)")
    ax.set_ylabel("internações/dia")
    ax.legend(ncol=5, fontsize=8)
    fig.tight_layout()
    fig.savefig(dirfig / "observado_vs_previsto.png", dpi=130)
    plt.close(fig)

    # resíduos no tempo
    fig, ax = plt.subplots(figsize=(14, 4))
    for mdl in sorted(sel["model"].unique()):
        g = sel[sel["model"] == mdl].sort_values("target_date")
        ax.plot(g["target_date"], g["residual"], lw=0.7, alpha=0.75, label=mdl)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Resíduos ao longo do tempo")
    ax.legend(ncol=5, fontsize=8)
    fig.tight_layout()
    fig.savefig(dirfig / "residuos_tempo.png", dpi=130)
    plt.close(fig)

    # distribuição dos erros
    fig, ax = plt.subplots(figsize=(9, 5))
    dados = [sel[sel["model"] == m]["residual"].to_numpy() for m in sorted(sel["model"].unique())]
    ax.boxplot(dados, tick_labels=sorted(sel["model"].unique()), showfliers=False)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Distribuição dos resíduos")
    fig.tight_layout()
    fig.savefig(dirfig / "distribuicao_erros.png", dpi=130)
    plt.close(fig)

    # MAE por modelo/feature set
    fig, ax = plt.subplots(figsize=(11, 5))
    rot = agg["model"] + " | " + agg["feature_set"]
    # barra de erro = dispersão ENTRE FOLDS; a de semente vai na tabela
    ax.barh(rot, agg["MAE_medio"], xerr=agg["MAE_std_fold"].fillna(0))
    ax.invert_yaxis()
    ax.set_xlabel("MAE médio entre folds")
    ax.set_title("Comparação de MAE")
    fig.tight_layout()
    fig.savefig(dirfig / "comparacao_mae.png", dpi=130)
    plt.close(fig)

    # erro por dia da semana
    fig, ax = plt.subplots(figsize=(10, 5))
    tmp = sel.copy()
    tmp["dow"] = pd.to_datetime(tmp["target_date"]).dt.dayofweek
    piv = tmp.pivot_table(index="dow", columns="model", values="abs_error", aggfunc="mean")
    piv.plot(ax=ax, marker="o")
    ax.set_xticks(range(7))
    ax.set_xticklabels(["seg", "ter", "qua", "qui", "sex", "sáb", "dom"])
    ax.set_ylabel("MAE")
    ax.set_title("Erro por dia da semana")
    fig.tight_layout()
    fig.savefig(dirfig / "erro_por_dia_semana.png", dpi=130)
    plt.close(fig)

    # erro por mês
    fig, ax = plt.subplots(figsize=(10, 5))
    tmp["mes"] = pd.to_datetime(tmp["target_date"]).dt.month
    pivm = tmp.pivot_table(index="mes", columns="model", values="abs_error", aggfunc="mean")
    pivm.plot(ax=ax, marker="o")
    ax.set_xticks(range(1, 13))
    ax.set_ylabel("MAE")
    ax.set_xlabel("mês")
    ax.set_title("Erro por mês")
    fig.tight_layout()
    fig.savefig(dirfig / "erro_por_mes.png", dpi=130)
    plt.close(fig)

    # desempenho por fold
    fig, ax = plt.subplots(figsize=(10, 5))
    pivf = fold_df.pivot_table(index="fold", columns="model", values="MAE", aggfunc="mean")
    pivf.plot(ax=ax, marker="o")
    ax.set_ylabel("MAE")
    ax.set_title("MAE por fold (variação temporal)")
    fig.tight_layout()
    fig.savefig(dirfig / "erro_por_fold.png", dpi=130)
    plt.close(fig)

    # desempenho durante picos: erro contra o nível observado
    fig, ax = plt.subplots(figsize=(10, 5))
    for mdl in sorted(sel["model"].unique()):
        g = sel[sel["model"] == mdl]
        ax.scatter(g["y_true"], g["abs_error"], s=6, alpha=0.35, label=mdl)
    ax.set_xlabel("internações observadas no dia")
    ax.set_ylabel("erro absoluto")
    ax.set_title("Erro versus nível observado (comportamento em picos)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(dirfig / "erro_vs_nivel.png", dpi=130)
    plt.close(fig)


def cfg_modelos_ativos(cfg: dict) -> list[str]:
    return [m for m, c in cfg.get("modelos", {}).items() if isinstance(c, dict) and c.get("ativo")]


def _summary(saida, run_id, modo, status, cfg, ds, folds, agg, fold_df,
             laudo=None, ablacao=None, diagnostico=None, sementes=(), maiores_erros=None) -> None:
    alvo = cfg["dados"]["alvo"]
    linhas = [
        f"# Benchmark preliminar — `{run_id}`",
        "",
        f"**STATUS: `{status}`**",
        "",
        "> Números gerados por esta run. Nenhuma afirmação abaixo vem de outra fonte.",
        "",
        "## Dataset",
        f"- SIH: `{cfg['dados']['sih']}`",
        f"- CAMS: `{cfg['dados']['cams']}`",
        f"- Período das datas-alvo: {ds.relatorio['primeira_data_alvo']} a {ds.relatorio['ultima_data_alvo']}",
        f"- Linhas após warmup: {ds.relatorio['linhas_apos_warmup']} "
        f"(removidas {ds.relatorio['linhas_removidas']} — {ds.relatorio['motivo_remocao']})",
        "",
        "## Alvo",
        *[f"- `{k}`: {v}" for k, v in alvo.items()],
        "",
        "## Protocolo",
        f"- Horizonte: h={ds.horizonte}",
        f"- Split: {cfg['split']['protocolo']}, {len(folds)} fold(s)",
        f"- Seed: {cfg['run']['seed']}",
        f"- Lags do alvo: {ds.relatorio['lags_alvo']}",
        f"- Lags exógenas: {ds.relatorio['lags_exogenas']}",
        f"- Lookback da LSTM: {cfg['experimento']['lookback']}",
        "",
        "## Folds",
        "",
        pd.DataFrame([f.resumo() for f in folds]).to_markdown(index=False),
        "",
        "## Resultados agregados",
        "",
        agg.to_markdown(index=False, floatfmt=".3f"),
        "",
        "## Por fold",
        "",
        fold_df.to_markdown(index=False, floatfmt=".3f"),
        "",
    ]

    # -------------------------------------------------------------- comparação
    base = agg[agg["model"] == "naive"]
    if len(base):
        mae_naive = float(base["MAE_medio"].iloc[0])
        linhas += [
            "## Comparação com a Naïve",
            "",
            f"MAE da Naïve: **{mae_naive:.3f}**. `skill > 0` significa erro menor que o dela.",
            "",
            agg[["model", "feature_set", "MAE_medio", "MASE_medio",
                 "skill_MAE_medio", "skill_RMSE_medio"]]
            .to_markdown(index=False, floatfmt=".3f"),
            "",
        ]

    if ablacao is not None and len(ablacao):
        linhas += [
            "## Feature ablation",
            "",
            "`delta_MAE` negativo = o bloco melhora sobre a referência AR. "
            "A coluna `delta_maior_que_ruido_semente` diz se a diferença sobrevive "
            "à dispersão entre sementes — quando `False`, não há o que interpretar.",
            "",
            ablacao.to_markdown(index=False, floatfmt=".3f"),
            "",
        ]

    if diagnostico:
        linhas += [
            "## Diagnóstico temporal",
            "",
            f"Desvio da série: {diagnostico['desvio_serie']}",
            f"Amplitude entre dias da semana: {diagnostico['amplitude_semanal']}",
            "",
            "| lag | ACF |", "|---|---|",
            *[f"| {k} | {v} |" for k, v in diagnostico["acf"].items()],
            "",
            "Média por dia da semana: "
            + ", ".join(f"{d}={v}" for d, v in diagnostico["media_por_dia_semana"].items()),
            "",
        ]

    if maiores_erros is not None and len(maiores_erros):
        linhas += [
            "## Análise de erros — maiores erros absolutos",
            "",
            maiores_erros.to_markdown(index=False, floatfmt=".2f"),
            "",
            "Figuras: `figures/observado_vs_previsto.png`, `residuos_tempo.png`, "
            "`distribuicao_erros.png`, `erro_por_dia_semana.png`, `erro_por_mes.png`, "
            "`erro_por_fold.png`, `erro_vs_nivel.png`, `comparacao_mae.png`.",
            "",
        ]

    # ----------------------------------------------------------- data quality
    if laudo is not None:
        d = laudo.to_dict()
        linhas += [
            "## Data quality",
            "",
            f"**Veredito: `{d['veredito']}`** — {d['n_pass']} PASS, "
            f"{d['n_warn']} WARN, {d['n_fail']} FAIL.",
            "",
            "| checagem | status | detalhe |", "|---|---|---|",
            *[f"| `{c['nome']}` | {c['status']} | {c['detalhe']} |" for c in d["checagens"]],
            "",
        ]

    # --------------------------------------------------------------- limitações
    linhas += ["## Limitações", ""]
    if status == "PRELIMINARY_UNVALIDATED_TARGET":
        linhas.append(
            "- **O alvo NÃO foi validado contra fonte oficial (TabNet).** Estes números não "
            "podem ser apresentados como resultado da dissertação."
        )
    linhas += [
        f"- Modelos desta run: {', '.join(cfg_modelos_ativos(cfg))}. TCN e TCN–LSTM fora de escopo.",
        "- Busca de hiperparâmetros mínima; nenhuma seleção usou o conjunto de teste.",
    ]
    # A limitação sobre sementes é DERIVADA da run, não fixa: a versão anterior
    # afirmava "uma única semente" mesmo quando a run usava cinco.
    n_sem = len(sementes)
    if n_sem <= 1:
        linhas.append(
            f"- Uma única semente por configuração ({list(sementes)}). Sem dispersão entre "
            f"sementes: diferenças entre feature sets não são separáveis de ruído de inicialização."
        )
    else:
        linhas.append(
            f"- {n_sem} sementes por configuração treinável ({list(sementes)}); a coluna "
            f"`MAE_std_semente` traz a dispersão. Baselines são determinísticos e rodam com uma."
        )
    linhas += [
        "- Determinismo bit-a-bit não é garantido: TensorFlow em CPU/GPU pode variar na última "
        "casa por ordem de redução em ponto flutuante. As sementes fixam a inicialização, não a "
        "aritmética.",
        "- Covariáveis ambientais entram apenas defasadas: prever `t+1` com meteorologia de `t+1` "
        "exigiria previsão meteorológica, que não está no escopo.",
    ]
    if modo == "smoke":
        linhas.append("- **SMOKE TEST**: folds e épocas reduzidos. Não é resultado científico.")
    if modo == "screening":
        linhas.append(
            "- **TRIAGEM**: protocolo possivelmente reduzido e subconjunto de modelos. "
            "Serve para ordenar candidatos, não para afirmar desempenho."
        )
        linhas.append(
            "- Blocos que diferem só pelas defasagens (`AR_L1` × `AR_CURTO`) produzem o "
            "MESMO canal para a LSTM, que enxerga a janela inteira de lookback. "
            "Ablação de defasagem só é interpretável no XGBoost."
        )

    linhas += ["", "## Status", "", f"`{status}`", ""]
    if modo == "smoke":
        linhas.append("`SMOKE_ONLY` — não entra em tabela de resultado preliminar.")
    elif modo == "screening":
        linhas.append(
            "`SCREENING_ONLY` — triagem para descobrir QUAIS variáveis merecem ser "
            "testadas a fundo. Pode rodar com subconjunto de modelos e protocolo "
            "reduzido. **Não é resultado de fechamento** e não entra na tabela da "
            "dissertação; o que passar no filtro precisa ser confirmado em `--full`."
        )
    else:
        linhas.append("`PRELIMINARY_FRAMEWORK_V0_1`")
    (saida / "summary.md").write_text("\n".join(linhas), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark preliminar h=1")
    ap.add_argument("--config", required=True, type=Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--smoke", action="store_true", help="execução rápida de sanidade")
    g.add_argument("--screening", action="store_true",
                   help="triagem: muitos feature sets, subconjunto de modelos. "
                        "Artefatos saem carimbados SCREENING_ONLY.")
    g.add_argument("--full", action="store_true", help="protocolo preliminar completo")
    ap.add_argument(
        "--data-mode", choices=("cache", "rebuild"), default="cache",
        help="cache: reutiliza os processados (ainda assim validados pelo gate). "
             "rebuild: reexecuta os pipelines de ingestão antes de rodar.",
    )
    ap.add_argument(
        "--downloads", type=Path, default=None,
        help="pasta dos CSV do QUALAR, usada só com --data-mode rebuild "
             "(padrão: ~/Downloads)",
    )
    ap.add_argument("--mlflow", action="store_true",
                    help="registra a execução no MLflow (run mãe, filhas por modelo/conjunto e um "
                         "modelo salvo por fold e semente); só registra, não muda a saída")
    ap.add_argument("--mlflow-uri", default=None,
                    help="tracking URI do MLflow, p.ex. sqlite:///mlruns/mlflow.db "
                         "(padrão: variável MLFLOW_TRACKING_URI)")
    ap.add_argument("--mlflow-experimento", default=None,
                    help="nome do experimento MLflow (padrão: run.nome do config)")
    args = ap.parse_args()
    modo = "smoke" if args.smoke else ("screening" if args.screening else "full")
    mlflow_opcoes = None
    if args.mlflow:
        uri = args.mlflow_uri or os.environ.get("MLFLOW_TRACKING_URI")
        if not uri:
            ap.error("--mlflow exige --mlflow-uri ou a variável de ambiente MLFLOW_TRACKING_URI")
        mlflow_opcoes = {"uri": uri, "experimento": args.mlflow_experimento}
    elif args.mlflow_uri or args.mlflow_experimento:
        ap.error("--mlflow-uri e --mlflow-experimento só valem com --mlflow")
    try:
        executar(
            args.config,
            modo,
            data_mode=args.data_mode,
            downloads=args.downloads,
            mlflow_opcoes=mlflow_opcoes,
        )
    except BaseException:
        if mlflow_opcoes:
            from tracking import registro_mlflow
            registro_mlflow.abortar_ativo()
        raise


if __name__ == "__main__":
    main()
