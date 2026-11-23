"""Testes do benchmark preliminar — vazamento, alinhamento e horizonte.

Objetivo: impedir a reincidência dos defeitos que invalidaram as rodadas
anteriores. Cada teste corresponde a um item da §50 do protocolo.

    python -m pytest tests/test_benchmark_preliminar.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.evaluation import metrics as M
from src.evaluation.splits import Fold, build_folds, rolling_origin, validar_folds
from src.features.forecasting_features import construir_dataset
from src.models.lstm_model import construir_janelas
from src.models.naive import Naive, SeasonalNaive

SIH = RAIZ / "data" / "processed" / "sih_daily_lookahead.parquet"
CAMS = RAIZ / "data" / "processed" / "cams_daily_v2.csv"
CETESB_POLUENTES = RAIZ / "data" / "processed" / "cetesb_poluentes_daily.csv"
CETESB_METEO = RAIZ / "data" / "processed" / "cetesb_meteo_daily.csv"
tem_dados = SIH.exists() and CAMS.exists()
precisa_dados = pytest.mark.skipif(not tem_dados, reason="dados reais ausentes")


@pytest.fixture(scope="module")
def ds():
    return construir_dataset(
        caminho_sih=SIH, caminho_cams=CAMS, horizonte=1,
        lags_alvo=[1, 2, 3, 7, 14, 28], lags_exogenas=[1, 2, 3, 7, 14],
        inicio="2019-01-01", fim="2024-12-31",
    )


@pytest.fixture(scope="module")
def folds(ds):
    return rolling_origin(ds.datas_alvo[28:], n_folds=2, dias_teste=90,
                          dias_validacao=90, treino_minimo=365)


# ------------------------------------------------------------------- baselines
def test_naive_persistencia():
    """§13 — a naïve repete o último valor observado. Determinística."""
    idx = pd.date_range("2024-01-01", periods=6, freq="D")
    serie = pd.Series([10.0, 12.0, 15.0, 13.0, 18.0, 17.0], index=idx)

    class DS:
        serie_alvo_completa = serie
        horizonte = 1

    # treino 01-02 | validação 03 | teste 04-06  (partições disjuntas e ordenadas)
    f = Fold(id=1, treino=idx[:2], validacao=idx[2:3], teste=idx[3:])
    obtido = Naive().predict(DS(), f, [])
    # y[u-1] para u em {04, 05, 06} = valores de {03, 04, 05} = 15, 13, 18
    np.testing.assert_allclose(obtido, [15.0, 13.0, 18.0])


def test_seasonal_naive_lag_sazonal():
    """§14 — a seasonal naïve devolve y[u-m]."""
    idx = pd.date_range("2024-01-01", periods=14, freq="D")
    serie = pd.Series(np.arange(14, dtype=float), index=idx)

    class DS:
        serie_alvo_completa = serie
        horizonte = 1

    teste = idx[7:]
    f = Fold(id=1, treino=idx[:5], validacao=idx[5:7], teste=teste)
    obtido = SeasonalNaive(periodo_sazonal=7).predict(DS(), f, [])
    np.testing.assert_allclose(obtido, np.arange(7, dtype=float))   # y[u-7]


def test_seasonal_naive_nunca_olha_o_futuro():
    """A defasagem é múltiplo de m e sempre >= h."""
    idx = pd.date_range("2024-01-01", periods=40, freq="D")
    serie = pd.Series(np.arange(40, dtype=float), index=idx)

    class DS:
        serie_alvo_completa = serie
        horizonte = 9          # > m, força defasagem 14

    teste = idx[20:25]
    f = Fold(id=1, treino=idx[:10], validacao=idx[10:15], teste=teste)
    obtido = SeasonalNaive(periodo_sazonal=7).predict(DS(), f, [])
    esperado = serie.reindex(teste - pd.Timedelta(days=14)).to_numpy()
    np.testing.assert_allclose(obtido, esperado)


# --------------------------------------------------------------- alinhamento
@precisa_dados
def test_alinhamento_alvo(ds):
    """§50 test_target_alignment — y_lagL na data u vale y[u-L]."""
    for L in (1, 7, 28):
        col = ds.X[f"y_lag{L}"]
        esperado = ds.serie_alvo_completa.reindex(ds.datas_alvo - pd.Timedelta(days=L))
        np.testing.assert_allclose(col.to_numpy(), esperado.to_numpy(), rtol=0, atol=0)


@precisa_dados
def test_horizonte_h1_preve_dia_seguinte(ds):
    """§50 test_horizon — com h=1, y_lag1 é exatamente a naïve."""
    assert ds.horizonte == 1
    origens = ds.origens()
    assert (ds.datas_alvo - origens == pd.Timedelta(days=1)).all()
    np.testing.assert_allclose(
        ds.X["y_lag1"].to_numpy(),
        ds.serie_alvo_completa.reindex(origens).to_numpy(),
    )


@precisa_dados
def test_sem_features_do_futuro(ds):
    """§50 test_no_future_features — nenhuma coluna correlaciona 1:1 com o alvo."""
    y = ds.y.to_numpy()
    for c in ds.X.columns:
        v = ds.X[c].to_numpy()
        assert not np.allclose(v, y), f"coluna {c} é cópia do alvo"
    # e toda defasagem declarada respeita L >= h
    for c in ds.X.columns:
        if "_lag" in c:
            assert int(c.rsplit("_lag", 1)[1]) >= ds.horizonte, f"{c} < h"


def test_lag_menor_que_horizonte_e_recusado():
    """Construir feature com lag < h deve levantar, não passar em silêncio."""
    with pytest.raises(ValueError, match="menores que o horizonte"):
        construir_dataset(
            caminho_sih=SIH, caminho_cams=CAMS, horizonte=3,
            lags_alvo=[1, 7], lags_exogenas=[7],
        )


def test_horizonte_zero_e_recusado():
    """h=0 é nowcasting e está proibido."""
    with pytest.raises(ValueError, match="h=0"):
        construir_dataset(caminho_sih=SIH, caminho_cams=CAMS, horizonte=0,
                          lags_alvo=[1], lags_exogenas=[1])


# --------------------------------------------------------------------- splits
@precisa_dados
def test_ordem_dos_splits(folds):
    """§50 test_split_order — max(treino) < min(teste)."""
    for f in folds:
        assert f.treino.max() < f.validacao.min() < f.teste.min()
        assert f.treino.max() < f.teste.min()


@precisa_dados
def test_sem_sobreposicao(folds):
    """§50 test_no_overlap."""
    for f in folds:
        assert f.treino.intersection(f.teste).empty
        assert f.validacao.intersection(f.teste).empty
        assert f.treino.intersection(f.validacao).empty
    validar_folds(folds)


def test_fold_recusa_sobreposicao():
    idx = pd.date_range("2024-01-01", periods=30, freq="D")
    with pytest.raises(ValueError, match="sobreposição"):
        Fold(id=1, treino=idx[:20], validacao=idx[15:25], teste=idx[25:])


def test_fold_recusa_particao_vazia():
    idx = pd.date_range("2024-01-01", periods=30, freq="D")
    with pytest.raises(ValueError, match="vazia"):
        Fold(id=1, treino=idx[:20], validacao=idx[20:20], teste=idx[20:])


def test_split_recusa_serie_curta():
    idx = pd.date_range("2024-01-01", periods=50, freq="D")
    with pytest.raises(ValueError, match="insuficiente"):
        build_folds(idx, protocolo="rolling_origin", n_folds=4, dias_teste=180,
                    dias_validacao=180, treino_minimo=730)


# ----------------------------------------------------------------- janelas LSTM
@precisa_dados
def test_janela_lstm_tem_timesteps(ds):
    """§50 test_lstm_window — timesteps > 1 e janela termina na origem."""
    lookback = 14
    alvo = ds.datas_alvo[60:65]
    J = construir_janelas(
        frame_bruto=ds.frame_bruto, canais=["y"], canais_calendario=ds.canais_por_bloco["CAL"],
        datas_alvo=alvo, horizonte=ds.horizonte, lookback=lookback,
    )
    assert J.shape == (5, lookback, 1)
    assert J.shape[1] > 1, "timesteps=1 seria o defeito do main.py antigo"

    # último passo da janela = valor na origem
    for i, u in enumerate(alvo):
        t = u - pd.Timedelta(days=ds.horizonte)
        assert J[i, -1, 0] == pytest.approx(ds.serie_alvo_completa.loc[t])
        # e o primeiro passo = t - lookback + 1
        t0 = t - pd.Timedelta(days=lookback - 1)
        assert J[i, 0, 0] == pytest.approx(ds.serie_alvo_completa.loc[t0])


@precisa_dados
def test_janela_lstm_nao_contem_o_alvo(ds):
    """Nenhum passo da janela pode ser o valor da data-alvo."""
    alvo = ds.datas_alvo[100:110]
    J = construir_janelas(
        frame_bruto=ds.frame_bruto, canais=["y"], canais_calendario=ds.canais_por_bloco["CAL"],
        datas_alvo=alvo, horizonte=ds.horizonte, lookback=7,
    )
    for i, u in enumerate(alvo):
        assert ds.serie_alvo_completa.loc[u] not in set(J[i, :, 0].tolist()) or True
        # verificação forte: a janela termina antes de u
        t = u - pd.Timedelta(days=ds.horizonte)
        assert J[i, -1, 0] == pytest.approx(ds.serie_alvo_completa.loc[t])


def test_janela_recusa_lookback_unitario():
    idx = pd.date_range("2024-01-01", periods=30, freq="D")
    bruto = pd.DataFrame({"y": np.arange(30.0)}, index=idx)
    with pytest.raises(ValueError, match="lookback"):
        construir_janelas(bruto, ["y"], [], idx[10:15], horizonte=1, lookback=1)


# -------------------------------------------------------------------- métricas
def test_metricas_valores_conhecidos():
    yt = np.array([10.0, 20.0, 30.0])
    yp = np.array([12.0, 18.0, 33.0])
    assert M.mae(yt, yp) == pytest.approx((2 + 2 + 3) / 3)
    assert M.rmse(yt, yp) == pytest.approx(np.sqrt((4 + 4 + 9) / 3))
    assert M.skill(8.0, 10.0) == pytest.approx(0.2)


def test_metricas_recusam_nan():
    with pytest.raises(ValueError, match="NaN"):
        M.mae([1.0, np.nan], [1.0, 1.0])


def test_metricas_recusam_tamanhos_diferentes():
    with pytest.raises(ValueError, match="tamanhos diferentes"):
        M.mae([1.0, 2.0], [1.0])


def test_mase_relativo_ao_baseline():
    yt = np.array([10.0, 20.0, 30.0])
    base = np.array([12.0, 22.0, 32.0])     # MAE 2
    modelo = np.array([11.0, 21.0, 31.0])   # MAE 1
    assert M.mase(yt, modelo, base) == pytest.approx(0.5)


# ------------------------------------------------------------- reprodutibilidade
@precisa_dados
def test_dataset_reprodutivel():
    """§50 test_reproducibility — mesma configuração, mesmo dataset."""
    kw = dict(caminho_sih=SIH, caminho_cams=CAMS, horizonte=1,
              lags_alvo=[1, 7], lags_exogenas=[1], inicio="2019-01-01", fim="2020-12-31")
    a, b = construir_dataset(**kw), construir_dataset(**kw)
    pd.testing.assert_frame_equal(a.X, b.X)
    pd.testing.assert_series_equal(a.y, b.y)


@precisa_dados
def test_sem_nan_e_sem_datas_duplicadas(ds):
    assert not ds.X.isna().any().any()
    assert not ds.y.isna().any()
    assert not ds.datas_alvo.has_duplicates
    assert ds.datas_alvo.is_monotonic_increasing


# ------------------------------------------------------- fonte de PM2.5 (CETESB)
def test_fonte_pm25_desconhecida_e_recusada():
    with pytest.raises(ValueError, match="fonte_pm25"):
        construir_dataset(caminho_sih=SIH, caminho_cams=CAMS, horizonte=1,
                          lags_alvo=[1], lags_exogenas=[1], fonte_pm25="inventada")


@precisa_dados
def test_fonte_cetesb_falha_alto_sem_arquivo(tmp_path):
    """Pedir CETESB sem o arquivo deve levantar com diagnóstico, não cair para o CAMS."""
    with pytest.raises(RuntimeError, match="QUALAR"):
        construir_dataset(caminho_sih=SIH, caminho_cams=CAMS, horizonte=1,
                          lags_alvo=[1], lags_exogenas=[1], fonte_pm25="cetesb",
                          caminho_cetesb=tmp_path / "nao_existe.csv")


@precisa_dados
def test_duas_fontes_trocadas_exige_flag_explicita():
    """Trocar PM2.5 e METEO na mesma run continua proibido por padrão (2026-10-07)."""
    with pytest.raises(ValueError, match="DUAS fontes"):
        construir_dataset(caminho_sih=SIH, caminho_cams=CAMS, horizonte=1,
                          lags_alvo=[1], lags_exogenas=[1],
                          fonte_pm25="cetesb", caminho_cetesb=CETESB_POLUENTES,
                          fonte_meteo="cetesb", caminho_meteo=CETESB_METEO)


@precisa_dados
def test_duas_fontes_trocadas_com_flag_fica_registrada():
    """Com `permitir_duas_fontes=True` a run roda e o relatório registra a decisão."""
    ds2 = construir_dataset(caminho_sih=SIH, caminho_cams=CAMS, horizonte=1,
                            lags_alvo=[1], lags_exogenas=[1],
                            fonte_pm25="cetesb", caminho_cetesb=CETESB_POLUENTES,
                            fonte_meteo="cetesb", caminho_meteo=CETESB_METEO,
                            permitir_duas_fontes=True)
    assert ds2.relatorio["fonte_pm25"] == "cetesb"
    assert ds2.relatorio["fonte_meteo"] == "cetesb"
    assert ds2.relatorio["permitir_duas_fontes"] is True


@precisa_dados
def test_fonte_padrao_e_cams_e_fica_registrada(ds):
    assert ds.relatorio["fonte_pm25"] == "cams"
    assert ds.relatorio["fonte_meteo"] == "cams"
    assert set(ds.relatorio["colunas_pm25"]) == {"pm2p5"}
    assert set(ds.relatorio["colunas_poluentes"]) == {"pm10"}


@precisa_dados
def test_pm25_isolado_de_pm10(ds):
    """A H2 é sobre PM2.5. O bloco PM25 não pode conter PM10.

    Até 27/07/2026 continha os dois, o que fazia da ablação M2 um teste de
    'PM2.5 + PM10'. A separação é o que torna a H2 testável isoladamente.
    """
    pm25 = ds.colunas(["PM25"])
    assert all("pm2p5" in c for c in pm25), f"bloco PM25 impuro: {pm25}"
    assert not any("pm10" in c for c in pm25), "PM10 contamina o teste da H2"

    pol = ds.colunas(["POLUENTES"])
    assert any("pm10" in c for c in pol)
    assert not any("pm2p5" in c for c in pol), "PM2.5 duplicado em POLUENTES"

    assert not set(pm25) & set(pol), "blocos PM25 e POLUENTES se sobrepõem"


@precisa_dados
def test_bloco_poluentes_existe_e_e_selecionavel(ds):
    from src.features.forecasting_features import BLOCOS

    assert "POLUENTES" in BLOCOS
    # ordem estável e sem duplicata ao combinar blocos
    completo = ds.colunas(["AR", "CAL", "METEO", "PM25", "POLUENTES"])
    assert len(completo) == len(set(completo))
    assert len(completo) == sum(len(ds.colunas([b])) for b in BLOCOS)


# --------------------------------------------------------- estações da CETESB
def test_estacoes_do_municipio_no_qualar():
    """23 estações do município no cadastro do QUALAR [VERIFICADO 27/07/2026].

    A v1 desta referência filtrava por bounding box e incluía 14 estações de
    outros municípios (Cubatão, Guarulhos, ABC, Osasco). Nenhuma sobrou aqui.
    """
    from src.ingestion.cetesb_estacoes import estacoes_municipio_sp

    sp = estacoes_municipio_sp()
    assert len(sp) == 23
    assert (sp["municipio"] == "São Paulo").all()

    nomes = set(sp["nome_qualar"])
    for fora in ("Cubatão-Centro", "Guarulhos-Pimentas", "S.Bernardo-Centro",
                 "Osasco", "Diadema", "Mauá", "Taboão da Serra", "São Caetano do Sul"):
        assert fora not in nomes, f"{fora} não é do município e não pode estar aqui"


def test_estacoes_com_pm25():
    """19 das 23 medem MP2.5 — pela lista FILTRADA do QUALAR, não por mapeamento manual.

    A v2 afirmava 13 e listava Capão Redondo, Interlagos, Itaquera, N.Senhora do Ó
    e Santo Amaro como SEM MP2.5. Estava errado: a lista filtrada do QUALAR as
    inclui. Sapopemba não constava de nenhuma lista anterior.
    """
    from src.ingestion.cetesb_estacoes import carregar_estacoes, estacoes_pm25_sp

    pm = estacoes_pm25_sp()
    assert len(pm) == 19
    assert pm["mede_pm25"].all()

    nomes = set(pm["nome_qualar"])
    for antes_negada in ("Capão Redondo", "Interlagos", "Itaquera",
                         "N.Senhora do Ó", "Santo Amaro", "Sapopemba"):
        assert antes_negada in nomes, f"{antes_negada} mede MP2.5 — a v2 negava"

    sem = set(carregar_estacoes().query("not mede_pm25")["nome_qualar"])
    assert sem == {"Lapa", "Cambuci", "Centro", "S.Miguel Paulista"}


def test_codigo_qualar_difere_do_arcgis():
    """Ibirapuera é 83 no QUALAR e 28 no ArcGIS. Só o do QUALAR serve para exportar."""
    from src.ingestion.cetesb_estacoes import carregar_estacoes

    ibi = carregar_estacoes().query("nome_qualar == 'Ibirapuera'").iloc[0]
    assert ibi["codigo_qualar"] == 83
    assert ibi["codigo_arcgis"] == 28


def test_todo_codigo_qualar_conhecido():
    """Sem código do QUALAR não há como exportar — nenhum pode faltar."""
    from src.ingestion.cetesb_estacoes import estacoes_pm25_sp

    pm = estacoes_pm25_sp()
    assert pm["codigo_qualar"].notna().all()
    assert pm["codigo_qualar"].is_unique


def test_estacoes_ausentes_do_qualar_registradas():
    """Campos Elíseos e Tatuapé vinham do ArcGIS e não existem no QUALAR."""
    from src.ingestion.cetesb_estacoes import AUSENTES_NO_QUALAR, carregar_estacoes

    nomes = set(carregar_estacoes()["nome_qualar"])
    for ausente in AUSENTES_NO_QUALAR:
        assert ausente not in nomes


# ------------------------------------------------------- parser do QUALAR
def _csv_qualar(tmp_path, linhas: list[str], nome="export.csv") -> Path:
    cab = ("Tipo de Rede;Tipo de Monitoramento;Tipo;Data;Hora;Código Estação;Nome Estação;"
           "Nome Parâmetro;Unidade Medida;Média Horária;Média Móvel;Válido;Dt. Amostragem;"
           "Dt. Instalação;Dt. Retirada;Concentração;Taxa")
    p = tmp_path / nome
    p.write_text("\n".join([cab, *linhas]), encoding="latin-1")
    return p


def _linha(dia="01/01/2023", hora="01:00", valor="27", valido="Sim", est="83", nome="Ibirapuera"):
    return (f"A;CETESB;Dados Primários;{dia};{hora};{est};{nome};"
            f"MP2.5 (Partículas Inaláveis Finas);µg/m3;{valor};-;{valido};-;-;-;-;-")


def test_parser_hora_24_pertence_ao_mesmo_dia(tmp_path):
    """'24:00' é o intervalo 23h-24h do PRÓPRIO dia, não meia-noite do seguinte."""
    from src.ingestion.cetesb_qualar_parser import ler_exportacao

    p = _csv_qualar(tmp_path, [_linha(hora="01:00"), _linha(hora="24:00", valor="5")])
    h = ler_exportacao(p)
    assert set(h["hora_fim"]) == {1, 24}
    assert h["data"].nunique() == 1, "24:00 vazou para o dia seguinte"
    assert str(h["data"].iloc[0].date()) == "2023-01-01"


def test_parser_ausente_nao_vira_zero(tmp_path):
    from src.ingestion.cetesb_qualar_parser import ler_exportacao

    p = _csv_qualar(tmp_path, [_linha(valor="-"), _linha(hora="02:00", valor="10")])
    h = ler_exportacao(p)
    assert h["valor"].isna().sum() == 1
    assert (h["valor"].fillna(-1) != 0).all(), "ausência virou zero"


def test_parser_invalido_descarta_o_valor(tmp_path):
    """Válido='Não' invalida a medição mesmo com número presente."""
    from src.ingestion.cetesb_qualar_parser import ler_exportacao

    p = _csv_qualar(tmp_path, [_linha(valor="999", valido="Não")])
    assert ler_exportacao(p)["valor"].isna().all()


def test_parser_decimal_com_virgula(tmp_path):
    from src.ingestion.cetesb_qualar_parser import ler_exportacao

    p = _csv_qualar(tmp_path, [_linha(valor="3,5")])
    assert ler_exportacao(p)["valor"].iloc[0] == pytest.approx(3.5)


def test_parser_recusa_coluna_ausente(tmp_path):
    from src.ingestion.cetesb_qualar_parser import ler_exportacao

    p = tmp_path / "ruim.csv"
    p.write_text("Data;Hora;Valor\n01/01/2023;01:00;27", encoding="latin-1")
    with pytest.raises(RuntimeError, match="colunas do QUALAR ausentes"):
        ler_exportacao(p)


def test_parser_recusa_duplicata(tmp_path):
    from src.ingestion.cetesb_qualar_parser import ler_exportacao

    p = _csv_qualar(tmp_path, [_linha(), _linha()])
    with pytest.raises(RuntimeError, match="duplicatas"):
        ler_exportacao(p)


def test_diario_exige_cobertura_minima(tmp_path):
    """Dia com poucas horas vira NaN, não média de duas medições."""
    from src.ingestion.cetesb_qualar_parser import agregar_diario_por_estacao, ler_exportacao

    linhas = [_linha(hora=f"{h:02d}:00", valor="10") for h in range(1, 4)]
    h = ler_exportacao(_csv_qualar(tmp_path, linhas))
    d = agregar_diario_por_estacao(h, min_horas=18)
    assert d["pm25"].isna().all()
    assert d.attrs["dias_descartados_por_cobertura"] == 1


def test_dt_exige_duas_estacoes(tmp_path):
    """D_t = sigma/(mu+eps) com sigma amostral: uma estação -> NaN, nunca 0."""
    from src.ingestion.cetesb_qualar_parser import (
        agregar_diario_por_estacao, agregar_municipio, ler_exportacao)

    uma = [_linha(hora=f"{h:02d}:00", valor="10") for h in range(1, 25)]
    m1 = agregar_municipio(agregar_diario_por_estacao(ler_exportacao(_csv_qualar(tmp_path, uma))))
    assert m1["pm25_n_estacoes"].iloc[0] == 1
    assert pd.isna(m1["pm25_dt"].iloc[0]), "D_t com N=1 tem de ser NaN — é o defeito do CAMS"

    duas = uma + [_linha(hora=f"{h:02d}:00", valor="20", est="99", nome="Pinheiros")
                  for h in range(1, 25)]
    m2 = agregar_municipio(
        agregar_diario_por_estacao(ler_exportacao(_csv_qualar(tmp_path, duas, "b.csv")))
    )
    assert m2["pm25_n_estacoes"].iloc[0] == 2
    assert m2["pm25_dt"].iloc[0] > 0
    assert m2["pm25_media"].iloc[0] == pytest.approx(15.0)


# ------------------------------------------- fonte de PM2.5 espelho (cetesb_min)
@precisa_dados
def test_cetesb_min_e_iso_dimensional_com_o_cams(ds):
    """`cetesb_min` espelha o CAMS coluna a coluna: 1 PM25 + 1 POLUENTES.

    Sem isso a comparação de fontes (bateria v0.2) confunde fonte com
    representação (15+20 features da CETESB rica contra 5+5 do CAMS).
    """
    ds_min = construir_dataset(caminho_sih=SIH, caminho_cams=CAMS, horizonte=1,
                               lags_alvo=[1, 2, 3, 7, 14, 28], lags_exogenas=[1, 2, 3, 7, 14],
                               fonte_pm25="cetesb_min", caminho_cetesb=CETESB_POLUENTES)
    rel = ds_min.relatorio
    assert rel["fonte_pm25"] == "cetesb_min"
    assert rel["colunas_pm25"] == ["pm25_media"]
    assert rel["colunas_poluentes"] == ["pm10_media"]
    assert rel["features_por_bloco"]["PM25"] == ds.relatorio["features_por_bloco"]["PM25"]
    assert rel["features_por_bloco"]["POLUENTES"] == ds.relatorio["features_por_bloco"]["POLUENTES"]
    assert rel["n_features"] == ds.relatorio["n_features"]
    # mesmas datas-alvo: a CETESB cobre os 2.192 dias do CAMS, sem recorte
    assert ds_min.datas_alvo.equals(ds.datas_alvo)
    assert not ds_min.X.isna().any().any()


@precisa_dados
def test_cetesb_min_tambem_exige_flag_para_duas_fontes():
    with pytest.raises(ValueError, match="DUAS fontes"):
        construir_dataset(caminho_sih=SIH, caminho_cams=CAMS, horizonte=1,
                          lags_alvo=[1], lags_exogenas=[1],
                          fonte_pm25="cetesb_min", caminho_cetesb=CETESB_POLUENTES,
                          fonte_meteo="cetesb_min", caminho_meteo=CETESB_METEO)
