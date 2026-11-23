"""Caminhos de `dados.*` na config: relativo à RAIZ ou absoluto (fora do repo).

Motivação (2026-10-19): a run de teste `h1_v02_cams_cams_rebaixa` aponta
`dados.cams` para D:/Project/dados_rebaixa_2026-10/processed/cams_daily_v2.csv,
fora do repositório, porque `data/processed/` é o canônico e não deve ser tocado.
Antes, o manifesto chamava `relative_to(RAIZ)` e quebrava com caminho absoluto.
O comportamento para caminhos relativos não muda.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.experiments.run_preliminary import (  # noqa: E402
    RAIZ as RAIZ_RUNNER,
    _caminho_dados,
    _caminho_no_manifesto,
)


def test_raiz_do_runner_e_o_repositorio():
    assert RAIZ_RUNNER == RAIZ


def test_relativo_resolve_contra_a_raiz():
    p = _caminho_dados("data/processed/cams_daily_v2.csv")
    assert p == RAIZ / "data" / "processed" / "cams_daily_v2.csv"
    assert p.is_absolute()


def test_relativo_no_manifesto_fica_relativo_como_antes():
    p = _caminho_dados("data/processed/cams_daily_v2.csv")
    assert _caminho_no_manifesto(p) == str(Path("data/processed/cams_daily_v2.csv"))


def test_absoluto_e_usado_como_esta(tmp_path):
    alvo = tmp_path / "fora_do_repo" / "cams_daily_v2.csv"
    assert alvo.is_absolute()
    assert _caminho_dados(str(alvo)) == alvo
    assert _caminho_dados(alvo) == alvo


def test_absoluto_fora_do_repo_no_manifesto_fica_absoluto(tmp_path):
    alvo = tmp_path / "cams_daily_v2.csv"
    assert _caminho_no_manifesto(alvo) == str(alvo)


def test_absoluto_dentro_do_repo_no_manifesto_fica_relativo():
    p = RAIZ / "data" / "processed" / "sih_daily_lookahead.parquet"
    assert _caminho_no_manifesto(p) == str(Path("data/processed/sih_daily_lookahead.parquet"))
