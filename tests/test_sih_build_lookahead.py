"""Testes da reconstrução do alvo (`src/ingestion/sih_build_lookahead.py`) — partes puras.

O download e a leitura de DBF são exercitados pela execução real (ver o `.meta.json` gerado
com `comparacao_com_referencia`); aqui ficam as regras de contagem, que não dependem de rede.
"""
from collections import Counter

import pandas as pd
import pytest

from src.ingestion.sih_build_lookahead import (
    CARATER_NAO_ELETIVO,
    agregar_registros,
    competencias_do_periodo,
    nome_ftp,
    serie_diaria,
)


def _acc():
    return {"linhas": Counter(), "distintas": Counter(), "ident": Counter(), "fora_periodo": 0, "dt_invalidas": 0}


def test_competencias_com_look_ahead_reproduzem_o_meta_canonico():
    comps = competencias_do_periodo("2019-01-01", "2024-12-31", 6)
    assert comps[0] == "201901" and comps[-1] == "202506" and len(comps) == 78
    assert nome_ftp("201901", "sp") == "RDSP1901.dbc"


def test_filtro_cid_e_municipio_e_dedup_por_n_aih():
    ini, fim = pd.Timestamp("2019-01-01"), pd.Timestamp("2019-12-31")
    regs_c1 = [
        {"N_AIH": "1", "DT_INTER": "20190105", "DIAG_PRINC": "J189", "MUNIC_RES": "355030", "IDENT": "1"},
        {"N_AIH": "2", "DT_INTER": "20190105", "DIAG_PRINC": "J459", "MUNIC_RES": "355030", "IDENT": "1"},
        {"N_AIH": "3", "DT_INTER": "20190105", "DIAG_PRINC": "K921", "MUNIC_RES": "355030", "IDENT": "1"},  # não-J
        {"N_AIH": "4", "DT_INTER": "20190105", "DIAG_PRINC": "J189", "MUNIC_RES": "350280", "IDENT": "1"},  # outro município
        {"N_AIH": "5", "DT_INTER": "20181230", "DIAG_PRINC": "J189", "MUNIC_RES": "355030", "IDENT": "1"},  # fora do período
        {"N_AIH": "6", "DT_INTER": "2019010", "DIAG_PRINC": "J189", "MUNIC_RES": "355030", "IDENT": "1"},   # data inválida
    ]
    regs_c2 = [
        {"N_AIH": "1", "DT_INTER": "20190105", "DIAG_PRINC": "J189", "MUNIC_RES": "355030", "IDENT": "5"},  # repetida
        {"N_AIH": "7", "DT_INTER": "20190106", "DIAG_PRINC": "j00", "MUNIC_RES": "3550308", "IDENT": "1"},   # minúscula, 7 dígitos
    ]
    vistos, acc = {}, _acc()
    s1 = agregar_registros(regs_c1, "355030", ini, fim, vistos, acc)
    s2 = agregar_registros(regs_c2, "355030", ini, fim, vistos, acc)
    assert s1 == {"registros_lidos": 6, "J_e_municipio": 4, "aih_novas": 2, "aih_repetidas": 0}
    assert s2 == {"registros_lidos": 2, "J_e_municipio": 2, "aih_novas": 1, "aih_repetidas": 1}
    assert acc["fora_periodo"] == 1 and acc["dt_invalidas"] == 1
    assert acc["ident"] == {"1": 3, "5": 1}
    df = serie_diaria(acc, ini, fim)
    assert len(df) == 365
    assert df.loc["2019-01-05", "internacoes"] == 2 and df.loc["2019-01-05", "linhas_brutas"] == 3
    assert df.loc["2019-01-06", "internacoes"] == 1
    assert int(df["internacoes"].sum()) == 3 and int(df["linhas_brutas"].sum()) == 4
    assert int((df["internacoes"] == 0).sum()) == 363


def test_registro_sem_n_aih_falha_alto():
    with pytest.raises(RuntimeError, match="N_AIH"):
        agregar_registros([{"N_AIH": "", "DT_INTER": "20190105", "DIAG_PRINC": "J189", "MUNIC_RES": "355030", "IDENT": "1"}],
                          "355030", pd.Timestamp("2019-01-01"), pd.Timestamp("2019-12-31"), {}, _acc())


# ------------------------------------------------- filtro de caráter (PROTOCOLO §0.23, alvo de urgência)
def _reg(aih, data, car, cid="J189", mun="355030"):
    return {"N_AIH": aih, "DT_INTER": data, "DIAG_PRINC": cid, "MUNIC_RES": mun, "IDENT": "1", "CAR_INT": car}


def test_sem_filtro_de_carater_comportamento_canonico_inalterado():
    ini, fim = pd.Timestamp("2019-01-01"), pd.Timestamp("2019-12-31")
    regs = [_reg("1", "20190105", "01"), _reg("2", "20190105", "02")]
    acc, vistos = _acc(), {}
    s = agregar_registros(regs, "355030", ini, fim, vistos, acc)
    assert acc["distintas"][pd.Timestamp("2019-01-05")] == 2
    assert "aih_excluidas_carater" not in s


def test_filtro_de_carater_conta_so_urgencia_e_primeira_ocorrencia_decide():
    ini, fim = pd.Timestamp("2019-01-01"), pd.Timestamp("2019-12-31")
    acc, vistos = _acc(), {}
    c1 = [_reg("1", "20190105", "01"),   # eletiva: excluída
          _reg("2", "20190105", "02"),   # urgência: conta
          _reg("3", "20190106", "02", cid="K921")]  # não-J: ignorada antes do filtro
    c2 = [_reg("1", "20190105", "02"),   # mesma AIH reapresentada como urgência: a 1ª ocorrência (eletiva) vence
          _reg("4", "20190107", "02")]
    s1 = agregar_registros(c1, "355030", ini, fim, vistos, acc, CARATER_NAO_ELETIVO)
    s2 = agregar_registros(c2, "355030", ini, fim, vistos, acc, CARATER_NAO_ELETIVO)
    assert acc["distintas"][pd.Timestamp("2019-01-05")] == 1
    assert acc["distintas"][pd.Timestamp("2019-01-07")] == 1
    assert sum(acc["distintas"].values()) == 2
    assert s1["aih_excluidas_carater"] == 1 and s1["aih_novas"] == 1
    assert s2["aih_repetidas"] == 1 and s2["aih_novas"] == 1
    assert sum(acc["linhas"].values()) == 3  # linhas brutas que passam no filtro (2, 1-reapresentada, 4)
    assert acc["car_int"] == {"01": 1, "02": 2}  # primeiras ocorrências por código


def test_nao_eletivo_aceita_acidentes_e_lesoes():
    acc = _acc()
    regs = [_reg(str(i), "20190105", c) for i, c in enumerate(["01", "02", "03", "04", "05", "06"])]
    agregar_registros(regs, "355030", pd.Timestamp("2019-01-01"), pd.Timestamp("2019-12-31"), {}, acc,
                      CARATER_NAO_ELETIVO)
    assert acc["distintas"][pd.Timestamp("2019-01-05")] == 5


@pytest.mark.parametrize("car", ["", "07", "1"])
def test_filtro_de_carater_codigo_fora_da_tabela_falha_alto(car):
    with pytest.raises(RuntimeError, match="CAR_INT"):
        agregar_registros([_reg("1", "20190105", car)], "355030", pd.Timestamp("2019-01-01"),
                          pd.Timestamp("2019-12-31"), {}, _acc(), CARATER_NAO_ELETIVO)
