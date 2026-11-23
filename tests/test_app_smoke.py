"""Teste de fumaça do app Streamlit: Home e cada página rodam sem exceção (streamlit.testing.v1.AppTest).

Também exercita as trocas de alvo/horizonte das páginas, para cobrir os dois alvos e todas as runs.
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app"
PAGINAS = sorted((APP / "pages").glob("*.py"))
TIMEOUT = 120


def _rodar(caminho: Path) -> AppTest:
    at = AppTest.from_file(str(caminho), default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _mudar_radio(at: AppTest, key: str, valor) -> None:
    at.radio(key=key).set_value(valor).run()
    assert not at.exception, [e.value for e in at.exception]


def test_home_abre_sem_excecao():
    at = _rodar(APP / "Home.py")
    assert any("provisional" in w.value.lower() for w in at.warning)
    assert at.metric, "Home must show at least one metric read from a file"


@pytest.mark.parametrize("pagina", PAGINAS, ids=[p.stem for p in PAGINAS])
def test_cada_pagina_abre_sem_excecao(pagina: Path):
    at = _rodar(pagina)
    assert any("provisional" in w.value.lower() for w in at.warning), "every page carries the provisional label"
    assert any("Source:" in c.value for c in at.caption), "every page shows the source file of its numbers"


def test_overview_alvo_urgencia():
    at = _rodar(APP / "pages" / "1_Overview.py")
    _mudar_radio(at, "ov_alvo", "urgencia")
    assert any("sih_daily_lookahead_urgencia" in c.value for c in at.caption)


@pytest.mark.parametrize("alvo", ["total", "urgencia"])
def test_modelos_por_horizonte_todos_os_h(alvo: str):
    at = _rodar(APP / "pages" / "2_Models_by_horizon.py")
    _mudar_radio(at, "mh_alvo", alvo)
    for h in [1, 5, 7, 15, 30]:
        _mudar_radio(at, "mh_h", h)
        _mudar_radio(at, "ab_h", h)
        _mudar_radio(at, "dm_h", h)
    _mudar_radio(at, "ab_metrica", "MASE_medio")


def test_sabado_controles():
    at = _rodar(APP / "pages" / "3_The_Saturday_case.py")
    _mudar_radio(at, "sab_periodo", "2019–2021")
    _mudar_radio(at, "sab_estab", "Total")
    _mudar_radio(at, "sab_metr", "Bias")
    for h in [5, 7, 15, 30]:
        _mudar_radio(at, "sab_h", h)


def test_leitura_falha_alto_se_faltar_arquivo():
    import sys

    sys.path.insert(0, str(APP))
    import dados

    with pytest.raises(FileNotFoundError):
        dados.caminho("results/runs/run_que_nao_existe/metrics.json")


def test_skill_total_bate_com_arquivo():
    """O skill calculado a partir dos MAEs (fórmula do app) reproduz o skill_vs_ref do arquivo (alvo total)."""
    import sys

    sys.path.insert(0, str(APP))
    import dados

    tab = dados.tabela_arcal("total")
    base = dados.carregar_arcal_dois_alvos()
    base = base[base["alvo"] == "total"]
    ref = base[base["modelo"].isin(["Naïve", "Seasonal Naïve"])].groupby("h")["MAE"].min()
    for _, r in tab[~tab["modelo"].isin(["Naïve", "Seasonal Naïve"])].iterrows():
        assert abs((1 - r["MAE"] / ref[r["h"]]) - r["skill_vs_ref"]) < 1e-9
