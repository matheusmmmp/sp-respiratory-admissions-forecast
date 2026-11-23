"""Referência das estações CETESB — QUALAR como autoridade.

HISTÓRICO DESTA REFERÊNCIA (importa, porque ela já esteve errada duas vezes)
----------------------------------------------------------------------------
**v1** filtrava por *bounding box* (o mesmo retângulo do CAMS). Capturava 34
estações, das quais 14 ficavam em outros municípios — Cubatão, Guarulhos,
Diadema, Osasco, São Bernardo, Santo André, Mauá, São Caetano e Taboão da Serra.
Se o download tivesse funcionado, o `D_t` teria sido calculado sobre a Baixada
Santista e o ABC misturados à capital.

**v2** corrigiu o recorte usando o `stations_bbox.csv` do serviço ArcGIS e a
lista de MP2.5 mapeada manualmente. Ficou com 20 estações e 13 com MP2.5.
**Também estava errada:** o cadastro do ArcGIS é incompleto e a lista manual
subestimava o MP2.5.

**v3, esta.** Fonte: o próprio QUALAR, lido em 27/07/2026 — o dropdown do
"Exportar Dados Avançado" (todas as estações, com código) e a lista **filtrada
por MP2.5** da tela "Exportar Dados", que só mostra estações que medem o
parâmetro. **[VERIFICADO]**

O QUE MUDOU DA v2 PARA A v3
---------------------------
- **19 estações do município medem MP2.5**, não 13. Entraram Capão Redondo,
  Interlagos, Itaquera, N.Senhora do Ó, Santo Amaro e Sapopemba.
- **Sapopemba** não aparecia em nenhuma lista anterior.
- **Campos Elíseos e Tatuapé não existem no cadastro atual do QUALAR** — vinham
  do ArcGIS. Provavelmente desativadas. Removidas daqui.
- Todos os **códigos do QUALAR** agora são conhecidos, não só o de Ibirapuera.

DOIS SISTEMAS DE CÓDIGO
-----------------------
O QUALAR e o serviço ArcGIS usam numerações **diferentes**: Ibirapuera é **83 no
QUALAR** e **28 no ArcGIS**. Só o código do QUALAR serve para exportar. O do
ArcGIS ficou registrado onde é conhecido, apenas para rastrear a origem das
coordenadas.

⚠️ MEDIR ≠ TER DADO NO PERÍODO
------------------------------
`mede_pm25` significa que a estação aparece na lista filtrada do QUALAR, ou seja
que o parâmetro existe no cadastro dela — **não** que haja série em 2019–2024.
Ibirapuera oferece MP10 e veio com **0% de preenchimento em 2019**. Só o download
revela a cobertura real; use `src.ingestion.cetesb_inventario` para medi-la.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

__all__ = [
    "ESTACOES", "carregar_estacoes", "estacoes_municipio_sp", "estacoes_pm25_sp",
    "MUNICIPIO_SP_IBGE",
]

MUNICIPIO_SP_IBGE = "3550308"

# Estações do MUNICÍPIO DE SÃO PAULO presentes no cadastro do QUALAR.
#   codigo_qualar : usado para exportar. [VERIFICADO no dropdown do QUALAR]
#   mede_pm25     : aparece na lista filtrada por MP2.5. [VERIFICADO]
#   codigo_arcgis : numeração do outro serviço, onde conhecida. NÃO serve para exportar.
#   lat/lon       : de data/cetesb/stations_bbox.csv (ArcGIS). None onde ausente.
ESTACOES: list[dict] = [
    {"codigo_qualar":  63, "nome_qualar": "Santana",                     "mede_pm25": True,  "codigo_arcgis":  63, "lat": -23.505993, "lon": -46.628960},
    {"codigo_qualar":  64, "nome_qualar": "Santo Amaro",                  "mede_pm25": True,  "codigo_arcgis":  64, "lat": -23.654977, "lon": -46.709998},
    {"codigo_qualar":  72, "nome_qualar": "Parque D.Pedro II",            "mede_pm25": True,  "codigo_arcgis":  48, "lat": -23.544846, "lon": -46.627676},
    {"codigo_qualar":  73, "nome_qualar": "Congonhas",                    "mede_pm25": True,  "codigo_arcgis":  15, "lat": -23.616320, "lon": -46.663466},
    {"codigo_qualar":  83, "nome_qualar": "Ibirapuera",                   "mede_pm25": True,  "codigo_arcgis":  28, "lat": -23.591842, "lon": -46.660688},
    {"codigo_qualar":  84, "nome_qualar": "Lapa",                         "mede_pm25": False, "codigo_arcgis": None, "lat": None,       "lon": None},
    {"codigo_qualar":  85, "nome_qualar": "Mooca",                        "mede_pm25": True,  "codigo_arcgis":  44, "lat": -23.549734, "lon": -46.600417},
    {"codigo_qualar":  90, "nome_qualar": "Cambuci",                      "mede_pm25": False, "codigo_arcgis": None, "lat": None,       "lon": None},
    {"codigo_qualar":  91, "nome_qualar": "Cerqueira César",              "mede_pm25": True,  "codigo_arcgis":  12, "lat": -23.553543, "lon": -46.672705},
    {"codigo_qualar":  94, "nome_qualar": "Centro",                       "mede_pm25": False, "codigo_arcgis": None, "lat": None,       "lon": None},
    {"codigo_qualar":  95, "nome_qualar": "Cid.Universitária-USP-Ipen",   "mede_pm25": True,  "codigo_arcgis":  14, "lat": -23.566342, "lon": -46.737414},
    {"codigo_qualar":  96, "nome_qualar": "N.Senhora do Ó",               "mede_pm25": True,  "codigo_arcgis":  45, "lat": -23.480099, "lon": -46.692052},
    {"codigo_qualar":  97, "nome_qualar": "Itaquera",                     "mede_pm25": True,  "codigo_arcgis":  32, "lat": -23.580015, "lon": -46.466651},
    {"codigo_qualar":  98, "nome_qualar": "Grajaú-Parelheiros",           "mede_pm25": True,  "codigo_arcgis":  23, "lat": -23.776266, "lon": -46.696961},
    {"codigo_qualar":  99, "nome_qualar": "Pinheiros",                    "mede_pm25": True,  "codigo_arcgis":  54, "lat": -23.561460, "lon": -46.702017},
    {"codigo_qualar": 236, "nome_qualar": "S.Miguel Paulista",            "mede_pm25": False, "codigo_arcgis": None, "lat": None,       "lon": None},
    {"codigo_qualar": 262, "nome_qualar": "Interlagos",                   "mede_pm25": True,  "codigo_arcgis":  30, "lat": -23.680508, "lon": -46.675043},
    {"codigo_qualar": 266, "nome_qualar": "Itaim Paulista",               "mede_pm25": True,  "codigo_arcgis":  31, "lat": -23.501547, "lon": -46.420737},
    {"codigo_qualar": 269, "nome_qualar": "Capão Redondo",                "mede_pm25": True,  "codigo_arcgis":   9, "lat": -23.668356, "lon": -46.780043},
    {"codigo_qualar": 270, "nome_qualar": "Marg.Tietê-Pte Remédios",      "mede_pm25": True,  "codigo_arcgis":  40, "lat": -23.518706, "lon": -46.743320},
    {"codigo_qualar": 284, "nome_qualar": "Pico do Jaraguá",              "mede_pm25": True,  "codigo_arcgis":  53, "lat": -23.456269, "lon": -46.766098},
    {"codigo_qualar": 293, "nome_qualar": "Perus",                        "mede_pm25": True,  "codigo_arcgis": None, "lat": None,       "lon": None},
    {"codigo_qualar": 295, "nome_qualar": "Sapopemba",                    "mede_pm25": True,  "codigo_arcgis": None, "lat": None,       "lon": None},
]

#: Estações do ArcGIS que NÃO constam do cadastro atual do QUALAR. Provavelmente
#: desativadas. Registradas para explicar a diferença entre as duas fontes.
AUSENTES_NO_QUALAR = ("Campos Elíseos", "Tatuapé")


def carregar_estacoes() -> pd.DataFrame:
    df = pd.DataFrame(ESTACOES)
    if df["codigo_qualar"].duplicated().any():
        raise RuntimeError("códigos do QUALAR duplicados na referência")
    if df["nome_qualar"].duplicated().any():
        raise RuntimeError("nomes do QUALAR duplicados na referência")
    df["municipio"] = "São Paulo"
    return df.sort_values("codigo_qualar").reset_index(drop=True)


def estacoes_municipio_sp() -> pd.DataFrame:
    """As 23 estações do município presentes no QUALAR."""
    return carregar_estacoes()


def estacoes_pm25_sp() -> pd.DataFrame:
    """As 19 do município que medem MP2.5 — o recorte que alimenta o D_t."""
    df = carregar_estacoes()
    sel = df[df["mede_pm25"]].copy()
    if sel.empty:
        raise RuntimeError("nenhuma estação com MP2.5 na referência")
    return sel.reset_index(drop=True)


def _relatorio() -> str:
    df = carregar_estacoes()
    pm = estacoes_pm25_sp()
    sem_coord = pm[pm["lat"].isna()]
    linhas = [
        f"município de São Paulo no QUALAR : {len(df)}",
        f"medem MP2.5                      : {len(pm)}",
        f"NÃO medem MP2.5                  : {len(df) - len(pm)}  "
        f"-> {', '.join(df.loc[~df['mede_pm25'], 'nome_qualar'])}",
        f"sem coordenada                   : {len(sem_coord)}  "
        f"-> {', '.join(sem_coord['nome_qualar']) or '-'}",
        f"no ArcGIS e ausentes do QUALAR   : {', '.join(AUSENTES_NO_QUALAR)}",
        "",
        "Estações com MP2.5 (nome e código para exportar no QUALAR):",
    ]
    linhas += [f"  {r.codigo_qualar:>3}  {r.nome_qualar}" for r in pm.itertuples()]
    linhas += [
        "",
        "ATENÇÃO: 'mede_pm25' vem do cadastro, não garante série em 2019-2024.",
        "Meça a cobertura real com src.ingestion.cetesb_inventario.",
    ]
    return "\n".join(linhas)


if __name__ == "__main__":
    print(_relatorio())
    destino = Path(__file__).resolve().parents[2] / "data" / "cetesb" / "estacoes_municipio_sp.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    carregar_estacoes().to_csv(destino, index=False, encoding="utf-8")
    print(f"\nsalvo: {destino}")
