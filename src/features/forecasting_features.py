"""Dataset experimental canônico — ETAPA COMPARTILHADA por todos os modelos.

CONVENÇÃO DE DEFASAGEM (a regra que impede vazamento)
-----------------------------------------------------
O frame é indexado pela DATA-ALVO `u`. Para horizonte `h`, a origem da previsão
é `t = u - h`, e só pode entrar informação observada até `t`.

Toda defasagem é medida a partir da DATA-ALVO:

    <var>_lag<L>  =  var[u - L]        e exige-se  L >= h

Com h=1: `y_lag1 = y[u-1] = y[t]`, que é exatamente a Naïve; e `y_lag7 = y[u-7]`,
exatamente a Seasonal Naïve. A regra `L >= h` é verificada em tempo de execução
e levanta se violada — é o que torna impossível criar uma feature do futuro.

Calendário é exceção legítima: dia da semana e feriado de `u` são conhecidos com
antecedência arbitrária, então entram sem defasagem.

BLOCOS
------
AR     — histórico do próprio desfecho
CAL    — calendário (conhecido no futuro)
METEO  — meteorologia observada, defasada
PM25   — poluição observada, defasada

Falha alto: coluna ausente, período fora de cobertura, data duplicada,
NaN inesperado, lag < h.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = ["DatasetExperimental", "construir_dataset", "BLOCOS", "feriados_brasil"]

#: `PM25` contém SOMENTE PM2.5, porque a H2 é formulada sobre ele e precisa ser
#: testável isoladamente. Os demais poluentes vivem em `POLUENTES`.
#:
#: ⚠️ MUDANÇA DE CONTRATO (27/07/2026). Antes `PM25` continha pm2p5 **e** pm10, o
#: que tornava a ablação M2 do benchmark um teste de "PM2.5 + PM10", não de
#: PM2.5. A run `preliminar_h1_full_20260727-054503` tem esse defeito: onde ela
#: diz PM25, leia "PM2.5 e PM10 juntos".
BLOCOS = ("AR", "CAL", "METEO", "PM25", "POLUENTES")

# Colunas do cams_daily_v2.csv, ja em unidades fisicas (ug/m3, C, %).
COLUNAS_METEO = ("t2m_c", "rh", "ws10", "sp")
COLUNAS_PM25_CAMS = ("pm2p5",)
#: ⚠️ SONDADO CONTRA O ADS EM 27/07/2026. O comentário anterior dizia "o CAMS
#: nunca entregou NO2, SO2, O3, CO", o que induzia a leitura errada de que era
#: falha nossa de download, corrigível refazendo a requisição. Não é.
#:
#: No EAC4 **single-level** — que é o produto que este projeto usa — os gases
#: NÃO EXISTEM como concentração de superfície. `nitrogen_dioxide` é recusado
#: pelo ADS; o que existe é COLUNA TOTAL (`tcno2`, `gtco3`, `tcco`, `tcso2`),
#: em kg/m², que é integral vertical e não se compara à medição da CETESB.
#:
#: Obter gás de superfície pelo CAMS exigiria o produto de níveis de modelo
#: (60 níveis no EAC4; o mais baixo a ~10 m do chão) e
#: conversão por densidade do ar — outro dataset e outro pipeline. Como a CETESB
#: entrega os seis poluentes medidos na superfície, com 2192 dias e 7 a 13
#: estações contra uma célula de 0,75°, não compensa.
#:
#: Consequência prática: comparação de fonte CAMS × CETESB é possível para
#: PM2.5, PM10 e temperatura, e IMPOSSÍVEL para NO2, O3, CO e SO2.
COLUNAS_POLUENTES_CAMS = ("pm10",)

# Retrocompatibilidade: nome antigo, antes de a fonte virar parametrizavel.
COLUNAS_PM25 = COLUNAS_PM25_CAMS

# ---------------------------------------------------------------- fontes PM2.5
#
# O bloco PM25 é intercambiável porque a pergunta "PM2.5 acrescenta sinal?" não
# pode ser respondida por uma fonte só. O benchmark de 27/07/2026 usou CAMS e
# concluiu que PM2.5 NÃO ajuda — mas o CAMS EAC4 entrega **uma única célula de
# grade** para São Paulo, com viés de nível de ~2x contra medição de superfície.
# Erro de exposição atenua associação. A conclusão defensável era sobre a
# reanálise, não sobre o poluente.
#
# Trocar a fonte e refazer a mesma ablação é o teste que separa as duas coisas.
#
#
# ⚠️ A TROCA `cetesb` NÃO É ISO-DIMENSIONAL (mesma ressalva do bloco METEO):
# o CAMS entrega 1 coluna em PM25 (`pm2p5`) e 1 em POLUENTES (`pm10`); a CETESB
# entrega 3 em PM25 (média, nº de estações, D_t) e até 4 em POLUENTES (pm10,
# no2, o3, co). Com defasagens, são 5+5 features contra 15+20. Uma diferença de
# desempenho entre `cams` e `cetesb` portanto confunde FONTE com REPRESENTAÇÃO.
# `cetesb_min` espelha o CAMS coluna a coluna (PM25 = `pm25_media`; POLUENTES =
# `pm10_media`) para que a comparação de fontes seja só de fonte — item A2.7 do
# `docs/ROADMAP_2026-10.md`, implementado em 2026-10-19.
FONTES_PM25 = ("cams", "cetesb", "cetesb_min", "hibrida")
#: Configuração HÍBRIDA (2026-10-22): as duas fontes lado a lado, SEM preenchimento de uma pela outra
#: (as duas cobrem os mesmos 2.192 dias; não há lacuna a preencher). As colunas do CAMS entram com o
#: prefixo `cams_` para que a proveniência fique no nome da feature e para que o GAM-NB não aplique
#: spline a dois PM2.5 (os splines seguem só em `pm25_media` e `temp_media`, da CETESB; o CAMS entra
#: linear). Exige `fonte_pm25 == fonte_meteo == "hibrida"` e `permitir_duas_fontes: true`.
PREFIXO_CAMS_HIBRIDO = "cams_"

#: Contrato do arquivo diário da CETESB para o bloco PM25 — só PM2.5.
#: `pm25_dt` é o índice de dispersão espacial. Ele foi calculado e **não tem
#: sinal** (r = −0,034, p = 0,37 contra o resíduo de AR+calendário); fica no
#: contrato porque é resultado negativo documentado, não porque se espera ganho.
COLUNAS_PM25_CETESB = ("pm25_media", "pm25_n_estacoes", "pm25_dt")
#: Espelho do CAMS para o bloco PM25: só a média municipal medida.
COLUNAS_PM25_CETESB_MIN = ("pm25_media",)
#: Espelho do CAMS para o bloco POLUENTES: só PM10 (o único poluente que o
#: CAMS single-level entrega em superfície — ver COLUNAS_POLUENTES_CAMS).
POLUENTES_CETESB_MIN = ("pm10",)

#: Bloco POLUENTES sobre a CETESB. Presentes hoje: pm10 e no2.
#: SO2, O3 e CO ficaram nas exportações interrompidas por HTTP 503 e entram
#: sozinhos quando o arquivo os trouxer — a seleção é por disponibilidade.
#:
#: Medido em 27/07/2026 (`teste_valor_incremental_poluentes.py`), valor
#: incremental sobre AR+calendário, num resíduo de desvio 21,55:
#:     no2   R²=0,0158  p=5,7e-09   <- o melhor dos poluentes
#:     pm10  R²=0,0087  p=2,6e-05
#:     pm25  R²=0,0082  p=9,9e-05
#: São fortemente colineares (pm25×pm10 r=0,93; pm10×no2 r=0,81): fonte comum,
#: tráfego. Somá-los não soma informação independente.
POLUENTES_CETESB_CANDIDATOS = ("pm10", "no2", "so2", "o3", "co")
CAMINHO_PADRAO_CETESB = "data/processed/cetesb_poluentes_daily.csv"

# --------------------------------------------------------------- fontes METEO
#
# Mesma lógica do bloco PM25, pela mesma razão. O benchmark de 27/07/2026
# concluiu que METEO **piora** o modelo (p<0,001 em toda combinação). Só que
# aquela meteorologia era do CAMS, e a conclusão defensável era sobre a
# reanálise, não sobre meteorologia.
#
# ⚠️ MEDIDO EM 27/07/2026, E MUDA A LEITURA: a temperatura do CAMS acompanha a
# medida na superfície com r = 0,958 e viés de +0,36 °C em 2192 dias. Isso é
# MUITO melhor que o PM2.5 do CAMS (r = 0,775, viés de escala 2,54x). Ou seja,
# a hipótese "METEO piora porque o CAMS é ruim" NÃO se sustenta para
# temperatura. Não sobrou como testar isso para umidade e vento: o
# `cams_sp_2019_2024.csv` só tem pm2p5, t2m, sp e t2m_c.
#
# O que a CETESB acrescenta não é temperatura melhor — é o que a média diária
# do CAMS apaga: mínima, máxima e amplitude térmica intradiária. A literatura
# atribui efeito respiratório ao frio e ao calor extremos por mecanismos
# distintos e com defasagens distintas.
#
# ⚠️ A TROCA NÃO É ISO-DIMENSIONAL. CAMS entrega 4 canais (t2m_c, rh, ws10,
# sp); a CETESB entrega 6, e não tem pressão. Uma diferença de desempenho
# portanto NÃO isola "fonte" — isola "fonte + representação". Para o teste de
# fonte pura existe `cetesb_min`, que espelha o CAMS em média/umidade/vento.
FONTES_METEO = ("cams", "cetesb", "cetesb_min", "hibrida")

#: Contrato do arquivo diário de meteorologia da CETESB.
COLUNAS_METEO_CETESB = (
    "temp_media", "temp_min", "temp_max", "temp_amplitude", "ur_media", "vv_media",
)
#: Espelho do CAMS, sem pressão: para separar efeito de FONTE de efeito de
#: REPRESENTAÇÃO. Se `cetesb` ganhar de `cetesb_min`, o ganho é dos extremos.
COLUNAS_METEO_CETESB_MIN = ("temp_media", "ur_media", "vv_media")
CAMINHO_PADRAO_METEO = "data/processed/cetesb_meteo_daily.csv"


# --------------------------------------------------------------------- feriados
def _pascoa(ano: int) -> _dt.date:
    """Algoritmo gregoriano anônimo. Sem dependência externa."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return _dt.date(ano, mes, dia + 1)


def feriados_brasil(anos) -> set[_dt.date]:
    """Feriados nacionais + municipais de São Paulo. Conhecidos a priori."""
    out: set[_dt.date] = set()
    for ano in anos:
        pascoa = _pascoa(ano)
        out.update(
            {
                _dt.date(ano, 1, 1),    # Confraternização
                _dt.date(ano, 1, 25),   # Aniversário de São Paulo (municipal)
                _dt.date(ano, 4, 21),   # Tiradentes
                _dt.date(ano, 5, 1),    # Trabalho
                _dt.date(ano, 9, 7),    # Independência
                _dt.date(ano, 10, 12),  # Aparecida
                _dt.date(ano, 11, 2),   # Finados
                _dt.date(ano, 11, 15),  # República
                _dt.date(ano, 11, 20),  # Consciência Negra
                _dt.date(ano, 12, 25),  # Natal
                pascoa - _dt.timedelta(days=48),  # Carnaval (segunda)
                pascoa - _dt.timedelta(days=47),  # Carnaval (terça)
                pascoa - _dt.timedelta(days=2),   # Sexta-feira Santa
                pascoa + _dt.timedelta(days=60),  # Corpus Christi
            }
        )
    return out


# --------------------------------------------------------------------- contrato
@dataclass
class DatasetExperimental:
    """Contrato único consumido por todos os modelos."""

    X: pd.DataFrame                  # indexado por data-alvo, JÁ defasado
    y: pd.Series                     # indexado por data-alvo
    horizonte: int
    colunas_por_bloco: dict[str, list[str]]
    serie_alvo_completa: pd.Series   # série bruta, para os baselines
    #: observações BRUTAS alinhadas por data de observação — a LSTM monta as
    #: janelas a partir daqui. NÃO é defasado: quem defasa é o construtor de
    #: sequências, respeitando a origem da previsão.
    frame_bruto: pd.DataFrame = field(default_factory=pd.DataFrame)
    #: canais brutos por bloco, para a ablação da LSTM
    canais_por_bloco: dict[str, list[str]] = field(default_factory=dict)
    #: Ordem estável de TODOS os blocos deste dataset — os cinco padrão mais os
    #: customizados declarados na configuração. Existe para a seleção não
    #: depender da ordem em que o usuário listou os blocos.
    ordem_blocos: tuple[str, ...] = BLOCOS
    relatorio: dict = field(default_factory=dict)

    @property
    def datas_alvo(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.X.index)

    def origens(self) -> pd.DatetimeIndex:
        return self.datas_alvo - pd.Timedelta(days=self.horizonte)

    def colunas(self, blocos) -> list[str]:
        """Colunas tabulares (defasadas) de um subconjunto de blocos — XGBoost."""
        return self._selecionar(blocos, self.colunas_por_bloco, "colunas")

    def canais(self, blocos) -> list[str]:
        """Canais brutos de um subconjunto de blocos — sequências da LSTM.

        ⚠️ Blocos que se distinguem APENAS pelas defasagens (`AR_L1` contra
        `AR_CURTO`, por exemplo) devolvem o MESMO canal aqui. A LSTM enxerga a
        janela inteira de `lookback` dias; a estrutura de defasagem não chega
        até ela. Ablação de defasagem só é interpretável no XGBoost.
        """
        return self._selecionar(blocos, self.canais_por_bloco, "canais")

    def _selecionar(self, blocos, mapa: dict[str, list[str]], rotulo: str) -> list[str]:
        desconhecidos = set(blocos) - set(self.ordem_blocos)
        if desconhecidos:
            raise ValueError(
                f"blocos desconhecidos: {sorted(desconhecidos)}. "
                f"Conhecidos: {sorted(self.ordem_blocos)}"
            )
        out: list[str] = []
        vistos: set[str] = set()
        for b in self.ordem_blocos:      # ordem estável, independente do input
            if b not in blocos:
                continue
            for c in mapa[b]:
                # blocos customizados podem se sobrepor (TEMP e METEO compartilham
                # colunas); a seleção não pode duplicar feature
                if c not in vistos:
                    vistos.add(c)
                    out.append(c)
        if not out:
            raise ValueError(f"seleção de blocos {sorted(blocos)} não produz {rotulo}")
        return out


# --------------------------------------------------------------------- builder
def _colunas_do_spec(nome: str, spec: dict, padrao: list[str]) -> list[str]:
    """Colunas de um bloco customizado, distinguindo "omitido" de "vazio".

    `colunas` ausente significa "todas as da fonte". `colunas: []` significa que
    alguém escreveu uma lista vazia — quase certamente engano de YAML — e vira
    erro. Sem esta distinção, um `or` trataria os dois casos igual e entregaria
    o bloco inteiro onde se pediu nada.
    """
    if "colunas" not in spec:
        return list(padrao)
    cols = spec["colunas"]
    if not isinstance(cols, (list, tuple)) or len(cols) == 0:
        raise ValueError(
            f"bloco {nome!r}: 'colunas' foi declarado vazio. Omita a chave para usar "
            f"todas as da fonte ({padrao}), ou liste as que quer."
        )
    return list(cols)


def _exigir_colunas(df: pd.DataFrame, cols, origem: str) -> None:
    faltando = [c for c in cols if c not in df.columns]
    if faltando:
        raise RuntimeError(f"{origem}: colunas obrigatórias ausentes: {faltando}. Presentes: {list(df.columns)}")


def construir_dataset(
    caminho_sih,
    caminho_cams,
    horizonte: int,
    lags_alvo,
    lags_exogenas,
    inicio=None,
    fim=None,
    fonte_pm25: str = "cams",
    caminho_cetesb=None,
    fonte_meteo: str = "cams",
    caminho_meteo=None,
    blocos_customizados: dict | None = None,
    permitir_duas_fontes: bool = False,
) -> DatasetExperimental:
    """Monta o frame experimental. Toda a preparação de dados vive aqui.

    `fonte_pm25` escolhe de onde vem o bloco PM25:
      "cams"   — reanálise CAMS EAC4, uma célula de grade (padrão)
      "cetesb" — medição de superfície agregada das estações do município
                 (PM25 = média, nº de estações, D_t; POLUENTES = todos os
                 poluentes utilizáveis)
      "cetesb_min" — medição de superfície espelhando o CAMS coluna a coluna
                 (PM25 = média; POLUENTES = pm10), para comparar só a FONTE
      "hibrida" — CETESB rica + CAMS lado a lado (PM25 = média, nº de estações,
                 D_t e `cams_pm2p5`; POLUENTES = pm10, no2, o3, co e `cams_pm10`);
                 só com fonte_meteo="hibrida"

    `fonte_meteo` escolhe de onde vem o bloco METEO:
      "cams"       — t2m_c, rh, ws10, sp (padrão)
      "cetesb"     — medida: média/mín/máx/amplitude de temp, umidade, vento
      "cetesb_min" — medida, espelhando o CAMS: só média de temp, umidade, vento
      "hibrida"    — as 6 variáveis da CETESB + `cams_t2m_c`, `cams_rh`, `cams_ws10`, `cams_sp`

    ⚠️ Troque UMA fonte por vez. Trocar PM25 e METEO na mesma run impede
    atribuir a diferença a qualquer uma das duas.
    """
    if horizonte < 1:
        raise ValueError(f"horizonte deve ser >= 1 (h=0 é nowcasting, proibido). Recebido: {horizonte}")
    if fonte_pm25 not in FONTES_PM25:
        raise ValueError(f"fonte_pm25 {fonte_pm25!r} desconhecida; use uma de {FONTES_PM25}")
    if fonte_meteo not in FONTES_METEO:
        raise ValueError(f"fonte_meteo {fonte_meteo!r} desconhecida; use uma de {FONTES_METEO}")
    if fonte_pm25 != "cams" and fonte_meteo != "cams" and not permitir_duas_fontes:
        raise ValueError(
            f"fonte_pm25={fonte_pm25!r} junto com fonte_meteo={fonte_meteo!r} troca DUAS fontes na mesma "
            "run. A diferença de desempenho ficaria inatribuível. Rode uma troca por vez — ou, "
            "se esta run faz parte de uma bateria que também contém as duas trocas isoladas, "
            "declare `dados.permitir_duas_fontes: true` no config (decisão de 2026-10-07, "
            "docs/PROTOCOLO.md v0.2 §3)."
        )

    if (fonte_pm25 == "hibrida") != (fonte_meteo == "hibrida"):
        raise ValueError(
            f"fonte_pm25={fonte_pm25!r} e fonte_meteo={fonte_meteo!r}: a configuração híbrida vale para as duas "
            "fontes ao mesmo tempo (CETESB + CAMS em todos os blocos ambientais) ou para nenhuma."
        )

    lags_alvo = sorted(set(int(v) for v in lags_alvo))
    lags_exogenas = sorted(set(int(v) for v in lags_exogenas))

    for rotulo, lags in (("lags_alvo", lags_alvo), ("lags_exogenas", lags_exogenas)):
        ruins = [L for L in lags if L < horizonte]
        if ruins:
            raise ValueError(
                f"{rotulo}: lags {ruins} são menores que o horizonte h={horizonte}. "
                f"Usariam informação posterior à origem da previsão. Mínimo permitido: {horizonte}."
            )

    # ------------------------------------------------------------- carregar SIH
    sih = pd.read_parquet(caminho_sih)
    if "internacoes" not in sih.columns:
        raise RuntimeError(f"{caminho_sih}: coluna 'internacoes' ausente. Colunas: {list(sih.columns)}")
    sih.index = pd.to_datetime(sih.index)
    sih = sih.sort_index()
    if sih.index.has_duplicates:
        dups = sih.index[sih.index.duplicated()].unique()
        raise RuntimeError(f"SIH: {len(dups)} datas duplicadas, ex.: {list(dups[:5])}")
    alvo = sih["internacoes"].astype(float)
    if alvo.isna().any():
        raise RuntimeError(f"SIH: alvo contém {int(alvo.isna().sum())} NaN. Zero não é missing — investigue.")

    # ------------------------------------------------------------ carregar CAMS
    cams = pd.read_csv(caminho_cams)
    if "data" not in cams.columns:
        raise RuntimeError(f"{caminho_cams}: coluna 'data' ausente")
    cams["data"] = pd.to_datetime(cams["data"])
    cams = cams.set_index("data").sort_index()
    if cams.index.has_duplicates:
        raise RuntimeError("CAMS: datas duplicadas")
    if fonte_meteo in ("cams", "hibrida"):
        _exigir_colunas(cams, COLUNAS_METEO, str(caminho_cams))
    if fonte_pm25 in ("cams", "hibrida"):
        _exigir_colunas(cams, COLUNAS_PM25_CAMS + COLUNAS_POLUENTES_CAMS, str(caminho_cams))

    # ------------------------------------------------- fonte do bloco METEO
    meteo_frame, colunas_meteo = cams, list(COLUNAS_METEO)
    if fonte_meteo != "cams":
        p_met = Path(caminho_meteo or CAMINHO_PADRAO_METEO)
        if not p_met.is_absolute():
            p_met = Path(caminho_sih).resolve().parents[2] / p_met
        if not p_met.exists():
            raise RuntimeError(
                f"fonte_meteo={fonte_meteo!r} pedida, mas {p_met} não existe.\n"
                f"Gere o arquivo com:\n"
                f"  python -m src.ingestion.cetesb_build_meteo --dir <pasta dos CSV>\n"
                f"Colunas esperadas: 'data' + {list(COLUNAS_METEO_CETESB)}"
            )
        met = pd.read_csv(p_met)
        if "data" not in met.columns:
            raise RuntimeError(f"{p_met}: coluna 'data' ausente")
        met["data"] = pd.to_datetime(met["data"])
        met = met.set_index("data").sort_index()
        if met.index.has_duplicates:
            raise RuntimeError(f"{p_met}: datas duplicadas")
        cols = (COLUNAS_METEO_CETESB if fonte_meteo in ("cetesb", "hibrida") else COLUNAS_METEO_CETESB_MIN)
        _exigir_colunas(met, cols, str(p_met))
        meteo_frame, colunas_meteo = met, list(cols)
        if fonte_meteo == "hibrida":
            # junção interna por data; as colunas do CAMS ganham o prefixo e NÃO preenchem nada da CETESB
            extra = cams[list(COLUNAS_METEO)].add_prefix(PREFIXO_CAMS_HIBRIDO)
            meteo_frame = met.join(extra, how="inner")
            colunas_meteo = list(cols) + list(extra.columns)

    # -------------------------------- fonte dos blocos PM25 e POLUENTES
    pm_frame, colunas_pm = cams, list(COLUNAS_PM25_CAMS)
    pol_frame, colunas_pol = cams, list(COLUNAS_POLUENTES_CAMS)
    poluentes_descartados: dict = {}
    if fonte_pm25 in ("cetesb", "cetesb_min", "hibrida"):
        espelho_cams = fonte_pm25 == "cetesb_min"
        p_cet = Path(caminho_cetesb or CAMINHO_PADRAO_CETESB)
        if not p_cet.is_absolute():
            p_cet = Path(caminho_sih).resolve().parents[2] / p_cet
        if not p_cet.exists():
            raise RuntimeError(
                f"fonte_pm25='cetesb' pedida, mas {p_cet} não existe.\n"
                f"O histórico da CETESB vem do QUALAR, que exige login. Gere o arquivo com:\n"
                f"  python -m src.ingestion.cetesb_build_poluentes --dir <pasta dos CSV>\n"
                f"Colunas esperadas: 'data' + {list(COLUNAS_PM25_CETESB)} + <pol>_media"
            )
        cet = pd.read_csv(p_cet)
        if "data" not in cet.columns:
            raise RuntimeError(f"{p_cet}: coluna 'data' ausente")
        cet["data"] = pd.to_datetime(cet["data"])
        cet = cet.set_index("data").sort_index()
        if cet.index.has_duplicates:
            raise RuntimeError(f"{p_cet}: datas duplicadas")
        _exigir_colunas(cet, COLUNAS_PM25_CETESB, str(p_cet))
        extra_cams: list[str] = []
        if fonte_pm25 == "hibrida":
            extra = cams[list(COLUNAS_PM25_CAMS + COLUNAS_POLUENTES_CAMS)].add_prefix(PREFIXO_CAMS_HIBRIDO)
            cet = cet.join(extra, how="inner")
            extra_cams = list(extra.columns)

        # POLUENTES por USABILIDADE, não por mera presença da coluna.
        #
        # A versão anterior selecionava só por "coluna existe", e o arquivo com
        # os seis poluentes derrubava a run mais adiante, na checagem de NaN.
        # Concretamente: `so2_media` tem 2 NaN (2021-01-10 e 11), dias em que
        # NENHUMA estação atingiu as 18 horas mínimas — o SO2 tem rede fraca,
        # 3,12 estações em média contra 10,6 do PM2.5.
        #
        # Descartar aqui, com registro, é melhor que morrer depois: a ausência
        # de um poluente esparso não deve impedir os outros cinco de rodarem.
        # E o descarte VAI para o relatório — não é silencioso.
        candidatos = POLUENTES_CETESB_MIN if espelho_cams else POLUENTES_CETESB_CANDIDATOS
        presentes = [
            f"{p}_media" for p in candidatos if f"{p}_media" in cet.columns
        ]
        recorte = cet.loc[cet.index.isin(alvo.index)] if len(cet) else cet
        descartados = {}
        disponiveis = []
        for c in presentes:
            n_nan = int(recorte[c].isna().sum())
            if n_nan:
                datas = [str(d.date()) for d in recorte.index[recorte[c].isna()][:5]]
                descartados[c] = {"n_nan": n_nan, "exemplos": datas}
            else:
                disponiveis.append(c)

        if not disponiveis:
            raise RuntimeError(
                f"{p_cet}: nenhum poluente utilizável para o bloco POLUENTES.\n"
                f"Presentes mas com NaN: {descartados}\n"
                f"Candidatos: {[f'{p}_media' for p in candidatos]}\n"
                f"Colunas do arquivo: {list(cet.columns)}"
            )
        if descartados:
            print(
                f"  [aviso] bloco POLUENTES: {len(descartados)} poluente(s) descartado(s) por "
                f"NaN no recorte — {', '.join(descartados)}. "
                f"Detalhe no relatório do dataset (`poluentes_descartados`)."
            )
        pm_frame = cet
        colunas_pm = list(COLUNAS_PM25_CETESB_MIN if espelho_cams else COLUNAS_PM25_CETESB)
        pol_frame, colunas_pol = cet, disponiveis
        if fonte_pm25 == "hibrida":
            colunas_pm = colunas_pm + [c for c in extra_cams if c.endswith(COLUNAS_PM25_CAMS)]
            colunas_pol = disponiveis + [c for c in extra_cams if c.endswith(COLUNAS_POLUENTES_CAMS)]
        poluentes_descartados = descartados

    # ------------------------------------------------------------- interseção
    # O CAMS só restringe o recorte quando alguma fonte o usa (cams ou hibrida).
    # Numa base CETESB/CETESB o arquivo do CAMS não entra em nenhuma feature; cruzar
    # com ele cortaria a extensão 2025–2026 (PROTOCOLO §0.22) sem motivo. Para as
    # runs 2019–2024 o recorte é o mesmo de antes (CAMS e SIH cobrem os mesmos dias).
    usa_cams = fonte_pm25 in ("cams", "hibrida") or fonte_meteo in ("cams", "hibrida")
    idx = alvo.index.intersection(cams.index) if usa_cams else alvo.index
    if pm_frame is not cams:
        antes = len(idx)
        idx = idx.intersection(pm_frame.index)
        if len(idx) < antes:
            print(
                f"  [aviso] a fonte PM2.5 '{fonte_pm25}' cobre menos dias que o CAMS: "
                f"{antes} -> {len(idx)}. A comparação entre fontes deve usar o MESMO recorte."
            )
    if meteo_frame is not cams:
        antes = len(idx)
        idx = idx.intersection(meteo_frame.index)
        if len(idx) < antes:
            print(
                f"  [aviso] a fonte METEO '{fonte_meteo}' cobre menos dias que o CAMS: "
                f"{antes} -> {len(idx)}. A comparação entre fontes deve usar o MESMO recorte."
            )
    if inicio is not None:
        idx = idx[idx >= pd.Timestamp(inicio)]
    if fim is not None:
        idx = idx[idx <= pd.Timestamp(fim)]
    if len(idx) == 0:
        raise RuntimeError("interseção do alvo com as fontes vazia no período pedido")

    esperado = pd.date_range(idx.min(), idx.max(), freq="D")
    buracos = esperado.difference(idx)
    if len(buracos):
        raise RuntimeError(
            f"série não é diária contínua: {len(buracos)} dias ausentes, ex.: {list(buracos[:5])}"
        )

    alvo = alvo.reindex(idx)
    cams = cams.reindex(idx)
    pm_frame = pm_frame.reindex(idx)
    pol_frame = pol_frame.reindex(idx)
    meteo_frame = meteo_frame.reindex(idx)

    nans_meteo = meteo_frame[colunas_meteo].isna().sum()
    if nans_meteo.any():
        raise RuntimeError(
            f"bloco METEO, fonte {fonte_meteo!r}, contém NaN — zero não é missing, e imputar "
            f"aqui esconderia falha de cobertura:\n{nans_meteo[nans_meteo > 0]}"
        )
    for rotulo, frame, cols in (("PM25", pm_frame, colunas_pm), ("POLUENTES", pol_frame, colunas_pol)):
        nans = frame[cols].isna().sum()
        if nans.any():
            raise RuntimeError(
                f"bloco {rotulo}, fonte '{fonte_pm25}', contém NaN — zero não é missing, "
                f"e imputar aqui esconderia falha de cobertura:\n{nans[nans > 0]}"
            )

    # -------------------------------------------------------------- montar X
    partes: dict[str, pd.DataFrame] = {}

    # AR — histórico do desfecho, defasado a partir da data-alvo
    ar = pd.DataFrame(index=idx)
    for L in lags_alvo:
        ar[f"y_lag{L}"] = alvo.shift(L)
    partes["AR"] = ar

    # CAL — conhecido no futuro, sem defasagem
    cal = pd.DataFrame(index=idx)
    cal["dow"] = idx.dayofweek
    cal["mes"] = idx.month
    fer = feriados_brasil(range(idx.min().year, idx.max().year + 1))
    cal["feriado"] = np.array([1 if d.date() in fer else 0 for d in idx], dtype=int)
    cal["fim_de_semana"] = (idx.dayofweek >= 5).astype(int)
    doy = idx.dayofyear.to_numpy(dtype=float)
    for k in (1, 2):
        cal[f"sin{k}"] = np.sin(2 * np.pi * k * doy / 365.25)
        cal[f"cos{k}"] = np.cos(2 * np.pi * k * doy / 365.25)
    partes["CAL"] = cal

    # METEO e PM25 — observadas, defasadas
    meteo = pd.DataFrame(index=idx)
    for c in colunas_meteo:
        for L in lags_exogenas:
            meteo[f"{c}_lag{L}"] = meteo_frame[c].shift(L)
    partes["METEO"] = meteo

    pm = pd.DataFrame(index=idx)
    for c in colunas_pm:
        for L in lags_exogenas:
            pm[f"{c}_lag{L}"] = pm_frame[c].shift(L)
    partes["PM25"] = pm

    # POLUENTES: separado de PM25 para a H2 continuar testável isoladamente
    pol = pd.DataFrame(index=idx)
    for c in colunas_pol:
        for L in lags_exogenas:
            pol[f"{c}_lag{L}"] = pol_frame[c].shift(L)
    partes["POLUENTES"] = pol

    # ---------------------------------------------- blocos customizados
    #
    # Declarados na configuração, para a ablação poder testar UMA VARIÁVEL POR
    # VEZ. Sem isto, METEO só existe como bloco de 20 a 30 features, e não há
    # como separar "meteorologia não tem sinal" de "20 features correlacionadas
    # custam mais variância do que entregam".
    #
    # Reaproveitam as MESMAS fontes já carregadas e validadas acima — não abrem
    # arquivo nem refazem defasagem por conta própria.
    fontes_disponiveis = {
        "alvo": (None, None),
        "calendario": (cal, list(cal.columns)),
        "meteo": (meteo_frame, colunas_meteo),
        "pm25": (pm_frame, colunas_pm),
        "poluentes": (pol_frame, colunas_pol),
    }
    partes_custom: dict[str, pd.DataFrame] = {}
    canais_custom: dict[str, list[str]] = {}
    #: defasagens introduzidas por blocos customizados; entram no cálculo do
    #: warmup, senão um bloco com lag maior que os padrão quebraria a asserção
    lags_customizados: set[int] = set()

    for nome, spec in (blocos_customizados or {}).items():
        if nome in BLOCOS:
            raise ValueError(
                f"bloco customizado {nome!r} colide com um bloco padrão {BLOCOS}. Escolha outro nome."
            )
        fonte = spec.get("fonte")
        if fonte not in fontes_disponiveis:
            raise ValueError(
                f"bloco {nome!r}: fonte {fonte!r} desconhecida; use uma de "
                f"{sorted(fontes_disponiveis)}"
            )
        lags_bloco = sorted(set(int(v) for v in spec.get("lags", lags_exogenas)))
        ruins = [L for L in lags_bloco if L < horizonte]
        if ruins:
            raise ValueError(
                f"bloco {nome!r}: defasagens {ruins} menores que o horizonte h={horizonte}. "
                f"Usariam informação posterior à origem da previsão."
            )

        bloco = pd.DataFrame(index=idx)
        if fonte == "alvo":
            for L in lags_bloco:
                bloco[f"y_lag{L}"] = alvo.shift(L)
            canais_custom[nome] = ["y"]
        elif fonte == "calendario":
            # `colunas: []` é erro, não "use todas". Sem esta distinção um bloco
            # declarado vazio por engano viraria o bloco inteiro em silêncio.
            cols = _colunas_do_spec(nome, spec, list(cal.columns))
            faltando = [c for c in cols if c not in cal.columns]
            if faltando:
                raise ValueError(
                    f"bloco {nome!r}: colunas de calendário inexistentes: {faltando}. "
                    f"Disponíveis: {list(cal.columns)}"
                )
            for c in cols:               # calendário NÃO é defasado: é conhecido a priori
                bloco[c] = cal[c]
            canais_custom[nome] = list(cols)
        else:
            frame, disponiveis_fonte = fontes_disponiveis[fonte]
            cols = _colunas_do_spec(nome, spec, list(disponiveis_fonte))
            faltando = [c for c in cols if c not in disponiveis_fonte]
            if faltando:
                raise ValueError(
                    f"bloco {nome!r}: colunas {faltando} não estão na fonte {fonte!r}. "
                    f"Disponíveis: {list(disponiveis_fonte)}"
                )
            for c in cols:
                for L in lags_bloco:
                    bloco[f"{c}_lag{L}"] = frame[c].shift(L)
            canais_custom[nome] = list(cols)

        if bloco.shape[1] == 0:
            raise ValueError(f"bloco customizado {nome!r} não produziu nenhuma coluna")
        partes_custom[nome] = bloco
        lags_customizados.update(lags_bloco)

    ordem_blocos = BLOCOS + tuple(partes_custom)
    partes.update(partes_custom)

    X = pd.concat([partes[b] for b in ordem_blocos], axis=1)
    # colunas repetidas entre blocos sobrepostos (TEMP dentro de METEO) apareceriam
    # duas vezes no frame; a seleção já deduplica, mas o X não pode ter duplicata
    X = X.loc[:, ~X.columns.duplicated()]
    colunas_por_bloco = {b: list(partes[b].columns) for b in ordem_blocos}

    # ------------------------------------------- aparar o warmup, com relatório
    max_lag = max(lags_alvo + lags_exogenas + sorted(lags_customizados))
    n_antes = len(X)
    validas = X.notna().all(axis=1)
    primeira_valida = X.index[validas.to_numpy().argmax()] if validas.any() else None
    if primeira_valida is None:
        raise RuntimeError("nenhuma linha completa após a construção de defasagens")

    esperada = idx[max_lag] if max_lag < len(idx) else None
    if esperada is not None and primeira_valida != esperada:
        raise RuntimeError(
            f"perda de linhas inesperada: primeira linha completa em {primeira_valida.date()}, "
            f"esperava {esperada.date()} (max_lag={max_lag}). Investigue antes de prosseguir."
        )

    X = X.loc[primeira_valida:]
    y = alvo.loc[primeira_valida:]
    if X.isna().any().any():
        ruins = X.columns[X.isna().any()].tolist()
        raise RuntimeError(f"NaN remanescente após o warmup nas colunas: {ruins}")

    # ------------------------- frame BRUTO alinhado, para as janelas da LSTM
    # Indexado por data de OBSERVAÇÃO, sem defasagem alguma. Quem respeita a
    # origem da previsão é o construtor de janelas em lstm_model.py.
    bruto = pd.DataFrame(index=idx)
    bruto["y"] = alvo
    for c in colunas_meteo:
        bruto[c] = meteo_frame[c]
    for c in colunas_pm:
        bruto[c] = pm_frame[c]
    for c in colunas_pol:
        if c not in bruto.columns:
            bruto[c] = pol_frame[c]
    for c in cal.columns:
        bruto[c] = cal[c]
    canais_por_bloco = {
        "AR": ["y"],
        "CAL": list(cal.columns),
        "METEO": list(colunas_meteo),
        "PM25": list(colunas_pm),
        "POLUENTES": list(colunas_pol),
        **canais_custom,
    }

    relatorio = {
        "linhas_antes_do_warmup": int(n_antes),
        "linhas_apos_warmup": int(len(X)),
        "linhas_removidas": int(n_antes - len(X)),
        "motivo_remocao": f"warmup de defasagens (max_lag={max_lag})",
        "primeira_data_alvo": str(X.index.min().date()),
        "ultima_data_alvo": str(X.index.max().date()),
        "n_features": int(X.shape[1]),
        "features_por_bloco": {b: len(c) for b, c in colunas_por_bloco.items()},
        "horizonte": horizonte,
        "lags_alvo": lags_alvo,
        "lags_exogenas": lags_exogenas,
        "fonte_pm25": fonte_pm25,
        "colunas_pm25": colunas_pm,
        "colunas_poluentes": colunas_pol,
        # descarte NUNCA silencioso: fica no manifesto da run
        "poluentes_descartados": poluentes_descartados,
        "fonte_meteo": fonte_meteo,
        "permitir_duas_fontes": bool(permitir_duas_fontes),
        "colunas_meteo": colunas_meteo,
        # proveniência coluna a coluna (importa na configuração híbrida; redundante nas demais)
        "proveniencia_colunas": {
            **{c: ("cams" if fonte_meteo == "cams" or c.startswith(PREFIXO_CAMS_HIBRIDO) else "cetesb")
               for c in colunas_meteo},
            **{c: ("cams" if fonte_pm25 == "cams" or c.startswith(PREFIXO_CAMS_HIBRIDO) else "cetesb")
               for c in list(colunas_pm) + list(colunas_pol)},
        },
        "blocos_customizados": {
            n: {"n_features": len(partes_custom[n].columns),
                "canais": canais_custom[n],
                "spec": blocos_customizados[n]}
            for n in partes_custom
        },
        "ordem_blocos": list(ordem_blocos),
    }

    return DatasetExperimental(
        X=X,
        y=y,
        horizonte=horizonte,
        colunas_por_bloco=colunas_por_bloco,
        serie_alvo_completa=alvo,
        frame_bruto=bruto,
        canais_por_bloco=canais_por_bloco,
        ordem_blocos=ordem_blocos,
        relatorio=relatorio,
    )
