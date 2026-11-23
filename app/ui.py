"""Elementos de interface comuns: seletor de idioma, rótulo provisório, caption de origem, tabelas."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from i18n import IDIOMAS, PADRAO, idioma, t


def _aplicar_idioma() -> None:
    st.session_state["lang"] = st.session_state["lang_sel"]
    st.query_params["lang"] = st.session_state["lang"]


def _iniciar_idioma() -> None:
    """Lê `?lang=` na primeira execução. Chamado antes de set_page_config para o título da aba sair traduzido."""
    if "lang" not in st.session_state:
        param = st.query_params.get("lang")
        st.session_state["lang"] = param if param in IDIOMAS else PADRAO


def seletor_idioma() -> str:
    """Radio 'Language / Idioma' na barra lateral; persiste em `st.session_state['lang']` e em `?lang=`."""
    _iniciar_idioma()
    # Mantém ?lang= na URL ao navegar entre páginas (a navegação lateral descarta os query params).
    if st.session_state["lang"] != PADRAO and st.query_params.get("lang") != st.session_state["lang"]:
        st.query_params["lang"] = st.session_state["lang"]
    codigos = list(IDIOMAS)
    st.sidebar.radio(
        t("ui.idioma"),
        options=codigos,
        index=codigos.index(idioma()),
        format_func=IDIOMAS.get,
        key="lang_sel",
        on_change=_aplicar_idioma,
    )
    return idioma()


def configurar_pagina(chave_titulo: str, icone: str = "📈") -> str:
    """set_page_config + seletor de idioma; devolve o idioma corrente. Chamar primeiro em toda página."""
    _iniciar_idioma()
    st.set_page_config(page_title=f"{t(chave_titulo)} · {t('app.curto')}", page_icon=icone, layout="wide")
    return seletor_idioma()


def aviso_provisorio() -> None:
    st.warning(t("ui.aviso"), icon="⚠️")


def fonte(*rels: str, run: str | None = None, nota: str | None = None) -> None:
    """Caption de rastreabilidade: arquivo(s) de origem, id da run e rótulo provisório."""
    partes = [t("ui.fonte") + " " + " · ".join(f"`{r}`" for r in rels)]
    if run:
        partes.append(f"{t('ui.run')} `{run}`")
    if nota:
        partes.append(nota)
    partes.append(t("ui.provisorio"))
    st.caption(" — ".join(partes))


def tabela(df: pd.DataFrame, casas: int = 3, **kw) -> None:
    """Tabela com números arredondados para leitura (os valores completos ficam no arquivo de origem)."""
    num = df.select_dtypes("number").columns
    sep = dict(thousands=".", decimal=",") if idioma() == "pt" else dict(thousands=",", decimal=".")
    st.dataframe(df.style.format({c: f"{{:.{casas}f}}" for c in num}, na_rep="", **sep), **kw)
