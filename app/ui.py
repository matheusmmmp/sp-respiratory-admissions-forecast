"""Elementos de interface comuns: rótulo provisório, caption de origem, formatação."""

from __future__ import annotations

import pandas as pd
import streamlit as st

PROVISIONAL = "provisional (pre-defense)"


def configurar_pagina(titulo: str, icone: str = "📈") -> None:
    st.set_page_config(page_title=f"{titulo} · SP respiratory admissions", page_icon=icone, layout="wide")


def aviso_provisorio() -> None:
    st.warning(
        "**All results on this page are provisional (pre-defense).** Every number is read from an aggregated "
        "artifact in this repository and labelled with its file path and the full id of the run that produced it. "
        "Nothing here is a final result of the dissertation.",
        icon="⚠️",
    )


def fonte(*rels: str, run: str | None = None, nota: str | None = None) -> None:
    """Caption de rastreabilidade: arquivo(s) de origem, id da run e rótulo provisório."""
    partes = ["Source: " + " · ".join(f"`{r}`" for r in rels)]
    if run:
        partes.append(f"run `{run}`")
    if nota:
        partes.append(nota)
    partes.append(PROVISIONAL)
    st.caption(" — ".join(partes))


def tabela(df: pd.DataFrame, casas: int = 3, **kw) -> None:
    """Tabela com números arredondados para leitura (os valores completos ficam no arquivo de origem)."""
    num = df.select_dtypes("number").columns
    st.dataframe(df.style.format({c: f"{{:.{casas}f}}" for c in num}, na_rep=""), **kw)


def fmt(v: float, casas: int = 1) -> str:
    return f"{v:,.{casas}f}"
