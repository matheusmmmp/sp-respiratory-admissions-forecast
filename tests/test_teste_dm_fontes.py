"""Testes do Holm com p indefinido em src/experiments/teste_dm_fontes.py (correção de 2026-10-24).

Rodar:  pytest tests/test_teste_dm_fontes.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.experiments.teste_dm_fontes import holm_finitos  # noqa: E402
from src.experiments.teste_dm_v02 import holm  # noqa: E402


def test_holm_finitos_ignora_p_indefinido_e_reduz_m():
    ps = [0.0015, float("nan"), 0.30, 0.02]
    out = holm_finitos(ps)
    assert np.isnan(out[1])
    esperado = holm([0.0015, 0.30, 0.02])  # m = 3, não 4
    assert out[0] == pytest.approx(esperado[0]) and out[2] == pytest.approx(esperado[1]) and out[3] == pytest.approx(esperado[2])
    assert out[0] == pytest.approx(3 * 0.0015)


def test_holm_finitos_sem_nan_igual_ao_holm():
    ps = [0.01, 0.04, 0.03, 0.5]
    assert holm_finitos(ps) == pytest.approx(holm(ps))


def test_holm_finitos_todos_indefinidos():
    out = holm_finitos([float("nan"), float("nan")])
    assert all(np.isnan(out))


def _run_sintetica(raiz: Path, run: str, desloc: float) -> None:
    """Run mínima: Naïve idêntico nas duas runs; xgboost em AR_CAL e AR_CAL_PM25 com erro deslocado por `desloc`."""
    import json

    import pandas as pd

    rng = np.random.default_rng(0)
    datas = pd.date_range("2025-03-06", periods=40, freq="D")
    y = 100 + rng.normal(0, 5, len(datas))
    ruido = rng.normal(0, 3, len(datas))
    linhas = []
    for m, fs, erro in (("naive", "baseline", ruido), ("xgboost", "AR_CAL", ruido + desloc + rng.normal(0, 1, len(datas))),
                        ("xgboost", "AR_CAL_PM25", ruido + desloc + rng.normal(0, 1, len(datas)))):
        for t, yt, e in zip(datas, y, erro):
            linhas.append(dict(run_id=run, model=m, feature_set=fs, seed=42, fold=1, target_date=t.date().isoformat(),
                               horizon=1, y_true=yt, y_pred=yt + e, residual=-e, abs_error=abs(e)))
    d = raiz / run
    d.mkdir(parents=True)
    pd.DataFrame(linhas).to_csv(d / "predictions.csv", index=False)
    pd.DataFrame([dict(fold=1, teste_inicio=datas[0].date().isoformat(), teste_fim=datas[-1].date().isoformat())]).to_csv(
        d / "folds.csv", index=False)
    (d / "manifest.json").write_text(json.dumps({"modo": "full", "dataset_sih_sha256": "x", "sementes": [42]}), encoding="utf-8")


@pytest.mark.parametrize("testar", [False, True])
def test_testar_sem_ambiente_poe_ar_cal_no_teste(tmp_path, monkeypatch, testar):
    import pandas as pd

    from src.experiments import teste_dm_fontes as tf

    monkeypatch.setattr(tf, "EXP", tmp_path)
    _run_sintetica(tmp_path, "A", 0.0)
    _run_sintetica(tmp_path, "B", 4.0)
    ctrl = {"baseline"} if testar else set(tf.CONTROLES)
    tf.executar("A", "A", [("B", "B")], tmp_path / "saida", controles=ctrl)
    t = pd.read_csv(tmp_path / "saida" / "dm_entre_bases.csv")
    ag = t[t.escopo == "agrupado"].set_index("conjunto")
    assert ag.loc["baseline", "tipo"] == "controle" and ag.loc["baseline", "max_abs_d"] == 0
    assert ag.loc["AR_CAL_PM25", "tipo"] == "teste"
    if testar:
        assert ag.loc["AR_CAL", "tipo"] == "teste" and np.isfinite(ag.loc["AR_CAL", "p"])
        assert int(ag.loc["AR_CAL", "m_familia_holm"]) == 2  # AR_CAL e AR_CAL_PM25 na mesma família
    else:
        assert ag.loc["AR_CAL", "tipo"] == "controle" and ag.loc["AR_CAL", "max_abs_d"] > 0
        assert int(ag.loc["AR_CAL_PM25", "m_familia_holm"]) == 1
