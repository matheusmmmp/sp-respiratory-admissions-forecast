#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blocos declarados por configuração — a base da ablação por variável.

POR QUE EXISTEM ESTES TESTES
----------------------------
A ablação monolítica não consegue separar "meteorologia não tem sinal" de
"20-30 features correlacionadas custam mais variância do que entregam". Blocos
customizados existem para testar UMA VARIÁVEL POR VEZ.

Mas eles abrem duas portas para erro silencioso, e é isso que se protege aqui:

  1. **Vazamento por defasagem menor que o horizonte.** Um bloco customizado
     que declarasse `lags: [0]` criaria uma feature do próprio dia-alvo. A
     regra `lag >= h` tem de valer para os customizados exatamente como vale
     para os padrão — não pode haver porta dos fundos.

  2. **Feature duplicada em blocos sobrepostos.** `TEMP` está contido em
     `METEO`. Selecionar os dois não pode entregar `temp_media_lag1` duas
     vezes: o XGBoost aceitaria calado, e a contagem de features do relatório
     mentiria.

E uma armadilha de interpretação que precisa ficar registrada em teste, não só
em comentário: blocos que diferem apenas nas defasagens produzem o MESMO canal
para a LSTM, que enxerga a janela inteira de lookback.

Rodar:  pytest tests/test_blocos_customizados.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.features.forecasting_features import BLOCOS, construir_dataset  # noqa: E402

CAMINHO_SIH = RAIZ / "data" / "processed" / "sih_daily_lookahead.parquet"
CAMINHO_CAMS = RAIZ / "data" / "processed" / "cams_daily_v2.csv"
CAMINHO_METEO = RAIZ / "data" / "processed" / "cetesb_meteo_daily.csv"
TEM_DADOS = CAMINHO_SIH.exists() and CAMINHO_CAMS.exists()
precisa_dados = pytest.mark.skipif(not TEM_DADOS, reason="dados processados ausentes")


def _montar(blocos=None, **kw):
    base = dict(
        caminho_sih=CAMINHO_SIH,
        caminho_cams=CAMINHO_CAMS,
        horizonte=1,
        lags_alvo=[1, 2, 3, 7],
        lags_exogenas=[1, 2, 3],
        inicio="2019-01-01",
        fim="2024-12-31",
        blocos_customizados=blocos,
    )
    base.update(kw)
    return construir_dataset(**base)


@pytest.fixture(scope="module")
def ds_meteo():
    if not (TEM_DADOS and CAMINHO_METEO.exists()):
        pytest.skip("meteorologia da CETESB ausente")
    return _montar(
        blocos={
            "TEMP": {"fonte": "meteo", "colunas": ["temp_media"], "lags": [1, 2, 3]},
            "UR": {"fonte": "meteo", "colunas": ["ur_media"], "lags": [1, 2, 3]},
            "AR_L1": {"fonte": "alvo", "lags": [1]},
            "AR_CURTO": {"fonte": "alvo", "lags": [1, 2, 3]},
            "CAL_DOW": {"fonte": "calendario", "colunas": ["dow", "fim_de_semana"]},
        },
        fonte_meteo="cetesb",
        caminho_meteo=CAMINHO_METEO,
    )


# =============================================== 1. a regra anti-vazamento
def test_bloco_customizado_recusa_lag_menor_que_horizonte():
    """Sem porta dos fundos: `lag >= h` vale igual para bloco customizado."""
    with pytest.raises(ValueError, match="menores que o horizonte"):
        _montar(blocos={"VAZA": {"fonte": "alvo", "lags": [0]}})


@precisa_dados
def test_bloco_customizado_recusa_lag_negativo():
    with pytest.raises(ValueError, match="menores que o horizonte"):
        _montar(blocos={"FUTURO": {"fonte": "alvo", "lags": [-1]}})


# ==================================================== 2. validação de entrada
def test_fonte_desconhecida_e_recusada():
    with pytest.raises(ValueError, match="fonte .* desconhecida"):
        _montar(blocos={"X": {"fonte": "inventada", "lags": [1]}})


@precisa_dados
def test_coluna_inexistente_e_recusada():
    with pytest.raises(ValueError, match="não estão na fonte"):
        _montar(blocos={"X": {"fonte": "pm25", "colunas": ["nao_existe"], "lags": [1]}})


@precisa_dados
def test_nome_que_colide_com_bloco_padrao_e_recusado():
    """Sobrescrever METEO em silêncio invalidaria toda comparação com o passado."""
    with pytest.raises(ValueError, match="colide com um bloco padrão"):
        _montar(blocos={"METEO": {"fonte": "pm25", "lags": [1]}})


# ============================================== 3. contagem correta de features
@precisa_dados
def test_contagem_de_features_por_bloco(ds_meteo):
    assert len(ds_meteo.colunas(["TEMP"])) == 3        # 1 variável × 3 defasagens
    assert len(ds_meteo.colunas(["UR"])) == 3
    assert len(ds_meteo.colunas(["AR_L1"])) == 1
    assert len(ds_meteo.colunas(["AR_CURTO"])) == 3
    assert len(ds_meteo.colunas(["CAL_DOW"])) == 2     # calendário não é defasado


@precisa_dados
def test_bloco_de_uma_variavel_e_muito_menor_que_o_bloco_cheio(ds_meteo):
    """É o ponto do exercício: 3 features contra as 18 do METEO da CETESB."""
    assert len(ds_meteo.colunas(["TEMP"])) < len(ds_meteo.colunas(["METEO"]))


# ===================================================== 4. blocos sobrepostos
@precisa_dados
def test_selecao_nao_duplica_feature_de_blocos_sobrepostos(ds_meteo):
    """TEMP está dentro de METEO: pedir os dois não pode duplicar coluna."""
    so_meteo = ds_meteo.colunas(["METEO"])
    juntos = ds_meteo.colunas(["METEO", "TEMP"])
    assert len(juntos) == len(set(juntos)), "há feature repetida na seleção"
    assert set(juntos) == set(so_meteo), "TEMP deveria estar contido em METEO"


@precisa_dados
def test_x_nao_tem_coluna_duplicada(ds_meteo):
    assert not ds_meteo.X.columns.duplicated().any()


# ============================================ 5. ordem estável e independente
@precisa_dados
def test_ordem_da_selecao_nao_depende_da_ordem_pedida(ds_meteo):
    a = ds_meteo.colunas(["TEMP", "AR", "CAL"])
    b = ds_meteo.colunas(["CAL", "TEMP", "AR"])
    assert a == b


@precisa_dados
def test_bloco_desconhecido_na_selecao_e_recusado(ds_meteo):
    with pytest.raises(ValueError, match="blocos desconhecidos"):
        ds_meteo.colunas(["NAO_EXISTE"])


# ================================ 6. a armadilha de interpretação da LSTM
@precisa_dados
def test_blocos_de_lag_diferente_dao_o_mesmo_canal_para_a_lstm(ds_meteo):
    """Registrado em teste porque é fonte de conclusão errada.

    `AR_L1` e `AR_CURTO` diferem só nas defasagens. Para o XGBoost são 1 e 3
    features; para a LSTM são o MESMO canal `y`, porque ela recebe a janela
    inteira de lookback. Comparar os dois na LSTM não mede nada.
    """
    assert ds_meteo.canais(["AR_L1"]) == ds_meteo.canais(["AR_CURTO"]) == ["y"]
    assert len(ds_meteo.colunas(["AR_L1"])) != len(ds_meteo.colunas(["AR_CURTO"]))


# ====================================== 7. o padrão continua reproduzindo o passado
@precisa_dados
def test_sem_blocos_customizados_o_comportamento_e_o_de_antes():
    ds = _montar(blocos=None)
    assert tuple(ds.ordem_blocos) == BLOCOS
    assert ds.relatorio["blocos_customizados"] == {}
    assert len(ds.colunas(["AR"])) == 4          # lags_alvo = [1,2,3,7]
    assert len(ds.colunas(["CAL"])) == 8


@precisa_dados
def test_bloco_vazio_e_recusado():
    with pytest.raises(ValueError):
        _montar(blocos={"NADA": {"fonte": "calendario", "colunas": []}})


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
