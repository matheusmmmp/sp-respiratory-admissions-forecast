#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de regressão contra o defeito mais grave da auditoria de 2026-07-26.

O QUE ACONTECEU
    build_supervised() no branch master (src/main.py, linhas 336-337) fazia:

        X = X.dropna().reset_index(drop=True)
        y = y.iloc[X.index].reset_index(drop=True)

    Depois do reset_index, X.index é um RangeIndex 0..n-1, então `y.iloc[X.index]`
    devolve os PRIMEIROS n rótulos — não os rótulos que sobreviveram ao dropna.
    Como o dropna descarta as `max(lag)` primeiras linhas, X e y ficam
    desalinhados em exatamente max(lag) dias.

    Com lags [1,2,3,7], o desalinhamento é 7, e a consequência é que a coluna
    `y_lag7` passa a ser numericamente IDÊNTICA ao rótulo. Um modelo linear
    atinge R² ≈ 1,0 copiando essa coluna. Verificado empiricamente.

    O master nunca foi executado, então nenhum número publicado foi contaminado.
    Este teste existe para que o defeito não sobreviva à reconciliação dos
    branches — as partes boas do master (calendário, seed, scaler no treino)
    devem ser portadas, esta não.

COMO USAR
    Sem pytest:  python tests/test_alinhamento_xy.py
    Com pytest:  pytest tests/test_alinhamento_xy.py

    O teste não depende de nenhuma dependência além de numpy e pandas, e não
    lê nada de data/. Roda em qualquer máquina, em menos de um segundo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Marcador de dia embutido nas features e no alvo. Escolhidos para que o dia
# implícito seja recuperável de ambos os lados sem ambiguidade.
BASE_ALVO = 1000.0
LAGS_PADRAO = (1, 2, 3, 7)


# --------------------------------------------------------------------------
# Fixture sintética
# --------------------------------------------------------------------------

def frame_sintetico(n: int = 60) -> pd.DataFrame:
    """
    Série diária onde o dia é recuperável de qualquer coluna:
        marcador[t] = t
        y[t]        = BASE_ALVO + t
    Qualquer desalinhamento entre X e y aparece como uma diferença constante.
    """
    return pd.DataFrame(
        {
            "data": pd.date_range("2020-01-01", periods=n, freq="D"),
            "y": BASE_ALVO + np.arange(n, dtype=float),
            "marcador": np.arange(n, dtype=float),
        }
    )


# --------------------------------------------------------------------------
# Invariantes — é isto que qualquer construtor de matriz supervisionada
# do projeto precisa satisfazer, independente de implementação.
# --------------------------------------------------------------------------

def invariante_tamanhos(X: pd.DataFrame, y: pd.Series) -> None:
    assert len(X) == len(y), f"len(X)={len(X)} != len(y)={len(y)}"
    assert len(X) > 0, "conjunto supervisionado vazio"


def invariante_alinhamento(X: pd.DataFrame, y: pd.Series, h: int) -> None:
    """
    Para horizonte h, a linha de X referente ao dia t deve ter como rótulo
    y[t+h]. Traduzido nos marcadores: (rótulo - BASE_ALVO) - marcador == h.
    """
    dia_feature = np.asarray(X["marcador"], dtype=float)
    dia_rotulo = np.asarray(y, dtype=float) - BASE_ALVO
    deltas = np.unique(dia_rotulo - dia_feature)

    assert len(deltas) == 1, (
        f"desalinhamento inconsistente entre linhas: deltas={deltas[:10]}"
    )
    assert deltas[0] == h, (
        f"X do dia t está pareado com y do dia t+{deltas[0]:.0f}, "
        f"mas o horizonte declarado é h={h}. "
        f"Diferença de {deltas[0] - h:.0f} dia(s) — este é exatamente o defeito "
        f"de build_supervised() no branch master."
    )


def invariante_sem_copia_do_alvo(X: pd.DataFrame, y: pd.Series) -> None:
    """
    Nenhuma coluna de X pode ser igual ao rótulo. Um lag do desfecho é
    legítimo (Lu et al. 2020); ser idêntico ao rótulo não é — é vazamento.
    """
    alvo = np.asarray(y, dtype=float)
    culpadas = [
        c for c in X.columns
        if pd.api.types.is_numeric_dtype(X[c])
        and np.allclose(np.asarray(X[c], dtype=float), alvo)
    ]
    assert not culpadas, (
        f"coluna(s) de X idêntica(s) ao alvo: {culpadas}. "
        f"Vazamento perfeito — um modelo linear atinge R²=1,0 copiando a coluna."
    )


def verifica_construtor(construtor, h: int, n: int = 60) -> None:
    """Aplica os três invariantes a um construtor (df, h) -> (X, y)."""
    X, y = construtor(frame_sintetico(n), h)
    invariante_tamanhos(X, y)
    invariante_alinhamento(X, y, h)
    invariante_sem_copia_do_alvo(X, y)


# --------------------------------------------------------------------------
# Referências: um construtor errado (o do master) e um correto.
# O errado existe para provar que os invariantes têm dentes.
# --------------------------------------------------------------------------

def construtor_defeituoso(df: pd.DataFrame, h: int) -> tuple[pd.DataFrame, pd.Series]:
    """Reproduz o padrão de src/main.py:336-337 no branch master."""
    d = df.copy().sort_values("data").reset_index(drop=True)
    y = d["y"].astype(float)

    X = d[["marcador"]].copy()
    for lag in LAGS_PADRAO:
        X[f"marcador_lag{lag}"] = d["marcador"].shift(lag)
        X[f"y_lag{lag}"] = y.shift(lag)

    # >>> o defeito <<<
    X = X.dropna().reset_index(drop=True)
    y = y.iloc[X.index].reset_index(drop=True)
    return X, y


def construtor_correto(df: pd.DataFrame, h: int) -> tuple[pd.DataFrame, pd.Series]:
    """
    Referência mínima correta: alinha por índice temporal, nunca por posição,
    e desloca o alvo pelo horizonte antes de descartar linhas incompletas.
    """
    d = df.copy().sort_values("data").reset_index(drop=True)

    X = d[["marcador"]].copy()
    for lag in LAGS_PADRAO:
        X[f"marcador_lag{lag}"] = d["marcador"].shift(lag)
        X[f"y_lag{lag}"] = d["y"].shift(lag)

    # alvo em t+h; features usam informação até t
    alvo = d["y"].shift(-h).rename("alvo")

    # concatena e descarta em UMA operação, preservando a correspondência
    junto = pd.concat([X, alvo], axis=1).dropna()
    return junto.drop(columns=["alvo"]), junto["alvo"]


# --------------------------------------------------------------------------
# Testes
# --------------------------------------------------------------------------

def test_invariantes_pegam_o_defeito_do_master():
    """Se este teste falhar, os invariantes perderam os dentes."""
    try:
        verifica_construtor(construtor_defeituoso, h=1)
    except AssertionError:
        return  # esperado
    raise AssertionError(
        "os invariantes NÃO detectaram o defeito conhecido do master — "
        "revise invariante_alinhamento/invariante_sem_copia_do_alvo"
    )


def test_defeito_do_master_e_desalinhamento_de_7_dias():
    """Documenta a magnitude exata, para o caso de alguém 'consertar' errado."""
    lag_max = max(LAGS_PADRAO)
    X, y = construtor_defeituoso(frame_sintetico(60), h=1)
    delta = np.unique(np.asarray(y, float) - BASE_ALVO - np.asarray(X["marcador"], float))
    assert delta.tolist() == [-lag_max], (
        f"esperado desalinhamento de -{lag_max} dias, obtido {delta.tolist()}"
    )
    assert np.allclose(np.asarray(X[f"y_lag{lag_max}"], float),
                       np.asarray(y, float)), (
        f"esperado que y_lag{lag_max} fosse idêntico ao rótulo neste construtor"
    )


def test_construtor_correto_passa_em_varios_horizontes():
    for h in (1, 2, 7):
        verifica_construtor(construtor_correto, h=h)


def test_construtor_do_projeto_quando_existir():
    """
    Assim que o construtor consolidado existir, aponte para ele aqui e
    remova o skip. A assinatura esperada é (df, h) -> (X, y), com a coluna
    de data chamada 'data' e o alvo 'y'.
    """
    try:
        from src.features.build import build_supervised  # noqa: F401
    except Exception:
        print("  [skip] src/features/build.py ainda não existe — Fase 4 do plano")
        return
    verifica_construtor(lambda df, h: build_supervised(df, horizonte=h), h=1)


# --------------------------------------------------------------------------

def main() -> int:
    testes = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhas = 0
    for t in testes:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            falhas += 1
            print(f"  FALHA {t.__name__}\n        {e}")
    print(f"\n{len(testes) - falhas}/{len(testes)} passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
