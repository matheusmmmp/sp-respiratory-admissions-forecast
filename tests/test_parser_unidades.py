#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de regressão para a whitelist de unidades do parser do QUALAR.

O QUE ACONTECEU
    Até 2026-07-27 o parser só aceitava concentrações (µg/m3, ppm). Quando a
    meteorologia medida na superfície entrou no escopo — porque o bloco METEO
    vindo do CAMS piorava o modelo (p<0,001) e ninguém tinha testado TEMP/UR
    reais — as 12 exportações de Parque D.Pedro II e Pinheiros foram todas
    recusadas com "unidade inesperada no parâmetro 'TEMP(...) - °C'".

    A whitelist foi ampliada para aceitar °C, % e m/s.

O QUE ESTE TESTE PROTEGE
    1. As três meteorológicas escalares passam.
    2. Concentrações continuam passando (não houve regressão).
    3. DIREÇÃO DO VENTO CONTINUA RECUSADA — e esta é a parte que importa.
       DV é grandeza circular: a média aritmética de 350° e 10° dá 180°, que
       aponta para o lado oposto do vento real. Todo o pipeline a jusante
       (agregação horária -> diária) assume que média aritmética faz sentido.
       Quem quiser DV precisa somar componentes vetoriais antes; deixar a
       unidade entrar na whitelist "para completar" produz número silencioso
       e errado, que é pior do que a falha.

COMO USAR
    Sem pytest:  python tests/test_parser_unidades.py
    Com pytest:  pytest tests/test_parser_unidades.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.ingestion.cetesb_qualar_parser import (  # noqa: E402
    UNIDADES_ACEITAS,
    UNIDADES_CONCENTRACAO,
    UNIDADES_METEOROLOGIA,
    _unidade_do_rotulo,
    ler_exportacao_avancada,
)

CABECALHO = (
    "Tipo de Monitoramento:;CETESB\n"
    "Tipo de Rede:;Automática\n"
    "Tipo de Dado:;Primários\n"
    "Código da estação:;72\n"
    "Nome da estação:;Parque D.Pedro II\n"
    "\n"
)


def _escreve(tmp: Path, rotulos: list[str], linhas: list[str]) -> Path:
    n = len(rotulos)
    arq = tmp / "export.csv"
    txt = (
        CABECALHO
        + "Data;Hora;" + ";".join(["Média Horária"] * n) + "\n"
        + ";;" + ";".join(rotulos) + "\n"
        + "\n".join(linhas) + "\n"
    )
    arq.write_text(txt, encoding="latin-1")
    return arq


def test_unidade_do_rotulo():
    assert _unidade_do_rotulo("TEMP(Temperatura do Ar) - °C") == "°C"
    assert _unidade_do_rotulo("UR(Umidade Relativa do Ar) - %") == "%"
    assert _unidade_do_rotulo("VV(Velocidade do Vento) - m/s") == "m/s"
    assert _unidade_do_rotulo("MP2.5(Partículas Inaláveis Finas) - µg/m3") == "µg/m3"


def test_meteorologia_escalar_e_aceita(tmp_path):
    """TEMP/UR/VV passam, com os valores lidos corretamente."""
    arq = _escreve(
        tmp_path,
        ["TEMP(Temperatura do Ar) - °C",
         "UR(Umidade Relativa do Ar) - %",
         "VV(Velocidade do Vento) - m/s"],
        ["01/01/2019;01:00;23,5;74;1,4",
         "01/01/2019;02:00;22,0;80;0,9"],
    )
    h = ler_exportacao_avancada(arq)
    assert len(h) == 6, h
    temp = h[h["parametro"].str.startswith("TEMP")]["valor"].tolist()
    assert temp == [23.5, 22.0], temp
    assert h["estacao_nome"].iloc[0] == "Parque D.Pedro II"


def test_concentracao_continua_aceita(tmp_path):
    """Não houve regressão no caso original do parser."""
    arq = _escreve(
        tmp_path,
        ["MP2.5(Partículas Inaláveis Finas) - µg/m3", "CO(Monóxido de Carbono) - ppm"],
        ["01/01/2019;01:00;17;0,6"],
    )
    h = ler_exportacao_avancada(arq)
    assert sorted(h["valor"].tolist()) == [0.6, 17.0]


def test_direcao_do_vento_e_recusada(tmp_path):
    """DV é circular. Aceitá-la produziria média aritmética silenciosamente errada."""
    arq = _escreve(
        tmp_path,
        ["DV(Direção do Vento) - graus"],
        ["01/01/2019;01:00;350", "01/01/2019;02:00;10"],
    )
    try:
        ler_exportacao_avancada(arq)
    except RuntimeError as exc:
        assert "unidade inesperada" in str(exc), exc
    else:
        raise AssertionError(
            "DV foi aceita. A média de 350° e 10° daria 180°, o oposto do vento "
            "real — o parser não pode deixar isso passar."
        )


def test_conjuntos_de_unidades_coerentes():
    assert UNIDADES_ACEITAS == UNIDADES_CONCENTRACAO | UNIDADES_METEOROLOGIA
    assert not (UNIDADES_CONCENTRACAO & UNIDADES_METEOROLOGIA)
    assert "graus" not in UNIDADES_ACEITAS


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        test_unidade_do_rotulo()
        test_meteorologia_escalar_e_aceita(tmp)
        test_concentracao_continua_aceita(tmp)
        test_direcao_do_vento_e_recusada(tmp)
        test_conjuntos_de_unidades_coerentes()
    print("ok")
