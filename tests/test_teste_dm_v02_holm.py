"""Testes do DM/Holm de src/experiments/teste_dm_v02.py com perdas idênticas (correção de 2026-11-18).

Caso real: em h = 7 o Naïve (y_{t-7}) e o Seasonal Naïve (m = 7) dão a mesma previsão; d_t ≡ 0, o DM é indefinido e,
antes da correção, a família `modelos_AR_CAL` inteira ficava sem p Holm.

Rodar:  pytest tests/test_teste_dm_v02_holm.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.experiments.teste_dm_v02 import PERDAS_IDENTICAS, aplicar_holm, dm, holm  # noqa: E402


def _c(nome, p, nota=None):
    g = {"p": p}
    if nota:
        g["nota"] = nota
    return {"contraste": nome, "A": f"{nome}:A", "B": f"{nome}:B", "agrupado": g}


def test_dm_perdas_identicas_marca_nota():
    r = dm(np.zeros(180), h=7)
    assert np.isnan(r["p"]) and r["nota"] == PERDAS_IDENTICAS and r["d_medio"] == 0.0


def test_dm_d_nao_nulo_nao_marca_nota():
    rng = np.random.default_rng(0)
    r = dm(rng.normal(size=180), h=7)
    assert np.isfinite(r["p"]) and "nota" not in r


def test_aplicar_holm_exclui_perdas_identicas_e_reduz_m():
    fam = [_c("a", 0.01), _c("naive − seasonal_naive", np.nan, PERDAS_IDENTICAS), _c("b", 0.04), _c("c", 0.30)]
    fora = aplicar_holm({"modelos_AR_CAL": fam})
    assert fora == ["modelos_AR_CAL: naive − seasonal_naive (naive − seasonal_naive:A vs naive − seasonal_naive:B)"]
    esperado = holm([0.01, 0.04, 0.30])  # m = 3, não 4
    assert [fam[i]["agrupado"]["p_holm"] for i in (0, 2, 3)] == pytest.approx(esperado)
    assert "p_holm" not in fam[1]["agrupado"]


def test_aplicar_holm_sem_indefinidos_igual_ao_holm():
    ps = [0.01, 0.04, 0.03, 0.5]
    fam = [_c(str(i), p) for i, p in enumerate(ps)]
    assert aplicar_holm({"f": fam}) == []
    assert [c["agrupado"]["p_holm"] for c in fam] == pytest.approx(holm(ps))


def test_aplicar_holm_p_indefinido_por_outro_motivo_falha_alto():
    fam = [_c("a", 0.01), _c("b", np.nan, "d_t constante")]
    with pytest.raises(RuntimeError, match="Holm da família indefinido"):
        aplicar_holm({"f": fam})
