"""Data and limitations — sources, construction rules, what is (and is not) in this repository."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dados  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import ui  # noqa: E402
from i18n import fmt_num, t  # noqa: E402

ui.configurar_pagina("dl.titulo_aba", "📚")
st.title(t("dl.titulo"))
ui.aviso_provisorio()

meta_t = dados.carregar_meta_alvo("total")
meta_u = dados.carregar_meta_alvo("urgencia")
meta_p = dados.carregar_meta_poluentes()

st.header(t("dl.h_fontes"))
st.markdown(t("dl.fontes"))

st.header(t("dl.h_alvo"))
st.markdown(
    t(
        "dl.alvo",
        espacial=meta_t["criterio_espacial"],
        cid=meta_t["regra_cid"],
        campo_data=meta_t["campo_data"],
        lookahead=meta_t["look_ahead_competencias"],
        ini=meta_t["periodo_epidemiologico"][0],
        fim=meta_t["periodo_epidemiologico"][1],
        adm_ini=meta_t["periodo_administrativo"][0],
        adm_fim=meta_t["periodo_administrativo"][1],
        justificativa=meta_t["look_ahead_justificativa"],
        regra_urg=meta_u["regra_contagem"],
    )
)


def _linhas(meta: dict) -> dict:
    # A coluna mistura contagens e a data de extração: tudo vira str (números via fmt_num), para que o Arrow
    # não precise adivinhar o tipo da coluna (o Streamlit Cloud logava "Serialization ... unsuccessful").
    return {
        t("dl.lin_linhas"): fmt_num(meta["total_linhas_somadas"], 0),
        t("dl.lin_aih"): fmt_num(meta["total_aih_distintas"], 0),
        t("dl.lin_dup"): fmt_num(meta["duplicatas_entre_competencias"], 0),
        t("dl.lin_invalidas"): fmt_num(meta["dt_inter_invalidas"], 0),
        t("dl.lin_dias"): fmt_num(meta["dias"], 0),
        t("dl.lin_zero"): fmt_num(meta["dias_com_zero"], 0),
        t("dl.lin_extraido"): str(meta["extraido_em"]),
    }


comp = pd.DataFrame({t("dl.col_total"): _linhas(meta_t), t("dl.col_urg"): _linhas(meta_u)}).astype(str)
st.dataframe(comp, width="stretch")
ui.fonte(dados.rel_meta_alvo("total"), dados.rel_meta_alvo("urgencia"))

st.header(t("dl.h_cetesb"))
st.markdown(
    t(
        "dl.cetesb",
        fonte=meta_p["fonte"],
        regra=meta_p["regra_diaria"],
        regra_dt=meta_p["regra_dt"],
        poluentes=", ".join(meta_p["poluentes_presentes"]),
        limitacao=meta_p["limitacao_valido"],
    )
)
pp = pd.DataFrame(meta_p["por_poluente"]).set_index("poluente")
ui.tabela(pp, casas=2, width="stretch")
ui.fonte(dados.REL_META_POLUENTES)

st.header(t("dl.h_protocolo"))
run_ref = dados.run_de("total", 1)
cfg = dados.carregar_config(run_ref)
st.markdown(
    t(
        "dl.protocolo",
        n_folds=cfg["split"]["n_folds"],
        dias_teste=cfg["split"]["dias_teste"],
        dias_val=cfg["split"]["dias_validacao"],
        treino_min=cfg["split"]["treino_minimo"],
        lags_alvo=cfg["experimento"]["lags_alvo"],
        lags_exog=cfg["experimento"]["lags_exogenas"],
        m=cfg["experimento"]["periodo_sazonal"],
        sementes=cfg["run"]["sementes"],
    )
)
ui.fonte(dados.rel_run(run_ref, "config.json"), run=run_ref)

st.header(t("dl.h_runs"))
runs = dados.resumo_runs()
st.dataframe(runs, hide_index=True, width="stretch")
ui.fonte(
    f"{dados.DIR_RUNS}/<run_id>/manifest.json",
    f"{dados.DIR_RUNS}/<run_id>/config.json",
    f"{dados.DIR_RUNS}/<run_id>/data_quality.json",
)
st.markdown(t("dl.status"))

st.header(t("dl.h_limites"))
st.markdown(t("dl.limites"))
