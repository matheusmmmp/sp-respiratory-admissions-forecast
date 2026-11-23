"""Leitura dos artefatos agregados usados pelo app Streamlit.

Regras:
- só lê `data/processed`, `results/` e `notebooks/dados_painel` (agregados; nenhum microdado);
- caminhos relativos à raiz do repositório (`RAIZ`);
- falha alto (`FileNotFoundError`) quando um arquivo esperado não existe — nunca contorna;
- cada função devolve dados de UM arquivo identificável; o caminho relativo é exposto por `rel_*`
  para que as páginas mostrem a origem de cada número.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]

DIR_PROCESSED = "data/processed"
DIR_RUNS = "results/runs"
DIR_DM = "results/testes_dm"
DIR_MH = "results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118"
DIR_URG = "results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118"
DIR_PAINEL = "notebooks/dados_painel"

# Nome de exibição por chave de modelo usada nos artefatos (model_comparison.csv, dm_contrastes.csv, ...).
NOME_MODELO = {
    "xgboost": "XGBoost",
    "sarimax": "SARIMAX",
    "lstm": "LSTM",
    "ingarch_nb": "INGARCH-NB",
    "gam_nb": "GAM-NB",
    "naive": "Naïve",
    "seasonal_naive": "Seasonal Naïve",
}
ORDEM_MODELOS = list(NOME_MODELO.values())
ALVOS = ("total", "urgencia")  # rótulos de exibição em i18n (`alvo.<alvo>`)
HORIZONTES = [1, 5, 7, 15, 30]


def caminho(rel: str) -> Path:
    """Caminho absoluto de um artefato; `FileNotFoundError` se não existir."""
    p = RAIZ / rel
    if not p.exists():
        raise FileNotFoundError(f"Expected artifact not found: {rel} (repo root: {RAIZ})")
    return p


@st.cache_data(show_spinner=False)
def ler_json(rel: str) -> dict:
    with open(caminho(rel), encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def ler_texto(rel: str) -> str:
    return caminho(rel).read_text(encoding="utf-8")


@st.cache_data(show_spinner=False)
def ler_csv(rel: str, **kw) -> pd.DataFrame:
    return pd.read_csv(caminho(rel), **kw)


# ---------------------------------------------------------------------------
# Alvo (SIH/SUS) e PM2,5 (CETESB)
# ---------------------------------------------------------------------------
def rel_alvo(alvo: str) -> str:
    if alvo == "total":
        return f"{DIR_PROCESSED}/sih_daily_lookahead.parquet"
    if alvo == "urgencia":
        return f"{DIR_PROCESSED}/sih_daily_lookahead_urgencia.parquet"
    raise ValueError(f"Unknown target: {alvo!r}")


def rel_meta_alvo(alvo: str) -> str:
    return rel_alvo(alvo).replace(".parquet", ".meta.json")


@st.cache_data(show_spinner=False)
def carregar_alvo(alvo: str) -> pd.DataFrame:
    """Série diária do alvo: índice `data` (datetime), coluna `internacoes`."""
    df = pd.read_parquet(caminho(rel_alvo(alvo)))
    if "internacoes" not in df.columns:
        raise ValueError(f"{rel_alvo(alvo)}: column 'internacoes' missing")
    out = df[["internacoes"]].copy()
    out.index = pd.to_datetime(out.index)
    out.index.name = "data"
    return out


def carregar_meta_alvo(alvo: str) -> dict:
    return ler_json(rel_meta_alvo(alvo))


REL_POLUENTES = f"{DIR_PROCESSED}/cetesb_poluentes_daily.csv"
REL_META_POLUENTES = f"{DIR_PROCESSED}/cetesb_poluentes_daily.meta.json"


@st.cache_data(show_spinner=False)
def carregar_pm25() -> pd.DataFrame:
    """PM2,5 diário da CETESB: índice `data`, colunas `pm25_media`, `pm25_n_estacoes`, `pm25_dt`."""
    df = pd.read_csv(caminho(REL_POLUENTES), parse_dates=["data"]).set_index("data")
    cols = ["pm25_media", "pm25_n_estacoes", "pm25_dt"]
    faltam = [c for c in cols if c not in df.columns]
    if faltam:
        raise ValueError(f"{REL_POLUENTES}: columns missing {faltam}")
    return df[cols]


def carregar_meta_poluentes() -> dict:
    return ler_json(REL_META_POLUENTES)


# ---------------------------------------------------------------------------
# Runs e seus artefatos
# ---------------------------------------------------------------------------
REL_PROVENIENCIA_URG = f"{DIR_URG}/proveniencia.json"


@st.cache_data(show_spinner=False)
def carregar_runs_por_horizonte() -> dict[str, dict[int, str]]:
    """{alvo: {h: run_id}} lido de `proveniencia.json` da análise de urgência (nunca digitado)."""
    prov = ler_json(REL_PROVENIENCIA_URG)
    return {alvo: {int(h): run for h, run in runs.items()} for alvo, runs in prov["runs"].items()}


def run_de(alvo: str, h: int) -> str:
    runs = carregar_runs_por_horizonte()
    try:
        return runs[alvo][int(h)]
    except KeyError as e:
        raise KeyError(f"No run registered for target={alvo!r}, h={h}") from e


def rel_run(run_id: str, arquivo: str) -> str:
    return f"{DIR_RUNS}/{run_id}/{arquivo}"


@st.cache_data(show_spinner=False)
def listar_runs() -> list[str]:
    base = caminho(DIR_RUNS)
    return sorted(p.name for p in base.iterdir() if p.is_dir())


def carregar_manifest(run_id: str) -> dict:
    return ler_json(rel_run(run_id, "manifest.json"))


def carregar_config(run_id: str) -> dict:
    return ler_json(rel_run(run_id, "config.json"))


def carregar_data_quality(run_id: str) -> dict:
    return ler_json(rel_run(run_id, "data_quality.json"))


@st.cache_data(show_spinner=False)
def carregar_folds(run_id: str) -> pd.DataFrame:
    df = pd.read_csv(caminho(rel_run(run_id, "folds.csv")))
    for c in ("treino_inicio", "treino_fim", "validacao_inicio", "validacao_fim", "teste_inicio", "teste_fim"):
        df[c] = pd.to_datetime(df[c])
    return df


@st.cache_data(show_spinner=False)
def carregar_model_comparison(run_id: str) -> pd.DataFrame:
    df = pd.read_csv(caminho(rel_run(run_id, "model_comparison.csv")))
    df["modelo"] = df["model"].map(NOME_MODELO).fillna(df["model"])
    return df


@st.cache_data(show_spinner=False)
def resumo_runs() -> pd.DataFrame:
    """Uma linha por run em results/runs, só com campos lidos de manifest/config/data_quality."""
    linhas = []
    for run_id in listar_runs():
        m = carregar_manifest(run_id)
        c = carregar_config(run_id)
        dq = carregar_data_quality(run_id)
        alvo = c["dados"]["alvo"].get("carater_internacao", "total")
        linhas.append(
            {
                "run_id": run_id,
                "target": "urgencia" if alvo == "nao_eletivo" else "total",
                "h": int(c["experimento"]["horizonte"]),
                "mode": m["modo"],
                "status": m["status"],
                "commit": str(m["git_commit"])[:7],
                "dirty_tree": bool(m["git_sujo"]),
                "quality_gate": dq["veredito"],
                "n_predictions": int(m["n_predicoes"]),
                "seeds": len(m["sementes"]),
                "pm25_source": m["fonte_pm25"],
                "meteo_source": m["fonte_meteo"],
            }
        )
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Métricas por horizonte
# ---------------------------------------------------------------------------
REL_MODELOS_POR_H = f"{DIR_MH}/A_modelos_por_h.csv"
REL_DM_RESUMO_POR_H = f"{DIR_MH}/A2_dm_modelos_por_h.csv"
REL_ARCAL_DOIS_ALVOS = f"{DIR_URG}/arcal_por_horizonte_dois_alvos.csv"
REL_ERRO_SABADO_H1 = f"{DIR_URG}/erro_sabado_h1.csv"


@st.cache_data(show_spinner=False)
def carregar_modelos_por_h() -> pd.DataFrame:
    """A_modelos_por_h.csv filtrado em base == 'cetesb' (alvo total), com nome de exibição do modelo."""
    df = pd.read_csv(caminho(REL_MODELOS_POR_H))
    df = df[df["base"] == "cetesb"].copy()
    if df.empty:
        raise ValueError(f"{REL_MODELOS_POR_H}: no rows with base == 'cetesb'")
    df["modelo_nome"] = df["modelo"].map(NOME_MODELO).fillna(df["modelo"])
    return df


@st.cache_data(show_spinner=False)
def carregar_arcal_dois_alvos() -> pd.DataFrame:
    """arcal_por_horizonte_dois_alvos.csv: alvo, h, modelo (nome de exibição), MAE, MASE."""
    df = pd.read_csv(caminho(REL_ARCAL_DOIS_ALVOS))
    esperadas = {"alvo", "h", "modelo", "MAE", "MASE"}
    if not esperadas.issubset(df.columns):
        raise ValueError(f"{REL_ARCAL_DOIS_ALVOS}: columns {esperadas - set(df.columns)} missing")
    return df


@st.cache_data(show_spinner=False)
def tabela_arcal(alvo: str) -> pd.DataFrame:
    """Tabela unificada (h, modelo, MAE, MASE, skill, naive, snaive, run) para um alvo.

    - total: MAE/MASE/skill_vs_ref lidos de A_modelos_por_h.csv; Naïve/Seasonal Naïve de suas colunas.
    - urgencia: MAE/MASE lidos de arcal_por_horizonte_dois_alvos.csv; skill calculado como
      1 − MAE / min(MAE Naïve, MAE Seasonal Naïve) do mesmo h (mesma definição de skill_vs_ref).
    """
    runs = carregar_runs_por_horizonte()[alvo]
    base = carregar_arcal_dois_alvos()
    base = base[base["alvo"] == alvo].copy()
    if base.empty:
        raise ValueError(f"{REL_ARCAL_DOIS_ALVOS}: no rows for target {alvo!r}")
    ref = (
        base[base["modelo"].isin(["Naïve", "Seasonal Naïve"])]
        .pivot(index="h", columns="modelo", values="MAE")
        .rename(columns={"Naïve": "naive", "Seasonal Naïve": "snaive"})
    )
    df = base.merge(ref, left_on="h", right_index=True, how="left")
    df["skill_vs_ref"] = 1.0 - df["MAE"] / df[["naive", "snaive"]].min(axis=1)
    if alvo == "total":
        # Para o alvo total o skill vem pronto do arquivo da análise multi-horizonte.
        a = carregar_modelos_por_h()[["h", "modelo_nome", "skill_vs_ref", "dp_fold", "dp_sem"]].rename(
            columns={"modelo_nome": "modelo", "skill_vs_ref": "skill_arquivo"}
        )
        df = df.merge(a, on=["h", "modelo"], how="left")
        tem = df["skill_arquivo"].notna()
        df.loc[tem, "skill_vs_ref"] = df.loc[tem, "skill_arquivo"]
        df = df.drop(columns=["skill_arquivo"])
    df["run"] = df["h"].map(runs)
    if df["run"].isna().any():
        raise KeyError(f"Run missing for some h of target {alvo!r}: {sorted(df.loc[df['run'].isna(), 'h'])}")
    df["modelo"] = pd.Categorical(df["modelo"], categories=ORDEM_MODELOS, ordered=True)
    return df.sort_values(["h", "modelo"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def carregar_dm_resumo_por_h() -> pd.DataFrame:
    df = pd.read_csv(caminho(REL_DM_RESUMO_POR_H))
    df = df[df["base"].isin(["cetesb", "urgencia"])].copy()
    df["target"] = df["base"].map({"cetesb": "total", "urgencia": "urgencia"})
    df["lider_nome"] = df["lider"].map(NOME_MODELO).fillna(df["lider"])
    return df


@st.cache_data(show_spinner=False)
def carregar_erro_sabado_h1() -> pd.DataFrame:
    return pd.read_csv(caminho(REL_ERRO_SABADO_H1))


# ---------------------------------------------------------------------------
# Diebold–Mariano
# ---------------------------------------------------------------------------
def rel_dm(run_id: str, arquivo: str) -> str:
    return f"{DIR_DM}/TESTES_DM_{run_id}/{arquivo}"


@st.cache_data(show_spinner=False)
def carregar_dm_contrastes(run_id: str) -> pd.DataFrame:
    df = pd.read_csv(caminho(rel_dm(run_id, "dm_contrastes.csv")))
    esperadas = {"familia", "contraste", "A", "B", "escopo", "DM", "p", "p_holm"}
    if not esperadas.issubset(df.columns):
        raise ValueError(f"{rel_dm(run_id, 'dm_contrastes.csv')}: columns {esperadas - set(df.columns)} missing")
    return df


@st.cache_data(show_spinner=False)
def dm_modelos_arcal(run_id: str) -> pd.DataFrame:
    """Contrastes agrupados (T = 720) da família `modelos_AR_CAL`, com nomes de exibição."""
    df = carregar_dm_contrastes(run_id)
    df = df[(df["familia"] == "modelos_AR_CAL") & (df["escopo"] == "agrupado")].copy()
    if df.empty:
        raise ValueError(f"{rel_dm(run_id, 'dm_contrastes.csv')}: no grouped rows for modelos_AR_CAL")
    chave = lambda s: NOME_MODELO.get(str(s).split(":")[0], str(s).split(":")[0])  # noqa: E731
    df["A_nome"] = df["A"].map(chave)
    df["B_nome"] = df["B"].map(chave)
    df["distinguishable_holm"] = df["p_holm"] < 0.05
    df["favors"] = df.apply(lambda r: r["A_nome"] if r["DM"] < 0 else r["B_nome"], axis=1)
    return df


def carregar_dm_relatorio(run_id: str) -> str:
    return ler_texto(rel_dm(run_id, "RELATORIO_DM.md"))


# ---------------------------------------------------------------------------
# Painel "o caso do sábado" (notebooks/dados_painel)
# ---------------------------------------------------------------------------
def rel_painel(arquivo: str) -> str:
    return f"{DIR_PAINEL}/{arquivo}"


@st.cache_data(show_spinner=False)
def carregar_painel_diario() -> pd.DataFrame:
    df = pd.read_csv(caminho(rel_painel("diario.csv")), parse_dates=["data"]).set_index("data")
    esperadas = {"total", "nao_eletivo", "eletivo", "cema", "sens_nao_eletivo", "sens_eletivo"}
    if not esperadas.issubset(df.columns):
        raise ValueError(f"diario.csv: columns {esperadas - set(df.columns)} missing")
    return df


@st.cache_data(show_spinner=False)
def carregar_painel_grupos_cid() -> pd.DataFrame:
    return pd.read_csv(caminho(rel_painel("grupos_cid.csv")))


@st.cache_data(show_spinner=False)
def carregar_painel_estabelecimentos() -> pd.DataFrame:
    # Células com < 5 internações já vêm suprimidas (vazias) — não preencher.
    return pd.read_csv(caminho(rel_painel("estabelecimentos_ano.csv")), dtype={"CNES": str})


@st.cache_data(show_spinner=False)
def carregar_painel_perfil() -> pd.DataFrame:
    return pd.read_csv(caminho(rel_painel("perfil.csv"))).set_index("recorte")


@st.cache_data(show_spinner=False)
def carregar_painel_atraso() -> pd.DataFrame:
    return pd.read_csv(caminho(rel_painel("atraso_registro_2022_mais.csv"))).set_index("dow")


@st.cache_data(show_spinner=False)
def carregar_painel_erros_modelos() -> pd.DataFrame:
    df = pd.read_csv(caminho(rel_painel("erros_modelos_ar_cal.csv")), parse_dates=["target_date"])
    df["modelo"] = df["model"].map(NOME_MODELO).fillna(df["model"])
    df["erro"] = df["y"] - df["y_prev"]
    return df


def carregar_painel_manifest() -> dict:
    return ler_json(rel_painel("manifest.json"))
