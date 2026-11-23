"""Parser das exportações do QUALAR/CETESB — escrito contra o formato REAL.

O pipeline anterior assumiu formato e produziu 33 arquivos vazios. Este módulo
foi escrito depois de inspecionar uma exportação de verdade
(Ibirapuera, MP2.5, jan/2023, 744 linhas).

FORMATO OBSERVADO **[VERIFICADO]**
----------------------------------
    separador : ';'
    encoding  : ISO-8859-1 (latin-1), sem BOM
    colunas   : Tipo de Rede · Tipo de Monitoramento · Tipo · Data · Hora ·
                Código Estação · Nome Estação · Nome Parâmetro · Unidade Medida ·
                Média Horária · Média Móvel · Válido · Dt. Amostragem ·
                Dt. Instalação · Dt. Retirada · Concentração · Taxa
    Data      : DD/MM/AAAA
    ausente   : '-'

A ARMADILHA DAS HORAS
---------------------
As horas vão de **01:00 a 24:00**, não de 00:00 a 23:00. A convenção é o
intervalo que TERMINA no rótulo: '01:00' é 00h–01h, '24:00' é 23h–24h. Portanto
**as 24 horas pertencem ao mesmo dia** e a agregação diária é um groupby direto
por `Data`, sem deslocamento.

Parsear '24:00' com `pd.to_datetime` levanta — e o caminho ingênuo de tratá-lo
como meia-noite jogaria a última hora para o dia seguinte. Aqui a hora vira
`hora_fim` (1..24) e a data permanece a do rótulo.

CÓDIGOS DE ESTAÇÃO
------------------
O QUALAR usa numeração **diferente** da do serviço ArcGIS: Ibirapuera é **83**
no QUALAR e **28** no `stations_bbox.csv`. Os dois sistemas coexistem. Este
parser guarda o código do QUALAR como veio; não tente casar com
`cetesb_estacoes.py` pelo número.

Falha alto: coluna ausente, unidade inesperada, data inválida, hora fora de
1..24, duplicata de (estação, data, hora).

PARÂMETROS ACEITOS
------------------
Concentrações (µg/m3, ppm) e as três meteorológicas **escalares** medidas pela
rede: TEMP (°C), UR (%) e VV (m/s). Direção do vento é recusada de propósito —
veja `UNIDADES_METEOROLOGIA`.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    "COLUNAS_QUALAR", "ler_exportacao", "ler_exportacao_avancada", "ler_qualquer",
    "ler_varias", "agregar_diario_por_estacao", "agregar_municipio", "relatorio",
    "MIN_HORAS_DIA", "UNIDADES_CONCENTRACAO", "UNIDADES_METEOROLOGIA", "UNIDADES_ACEITAS",
]

COLUNAS_QUALAR = (
    "Tipo de Rede", "Tipo de Monitoramento", "Tipo", "Data", "Hora",
    "Código Estação", "Nome Estação", "Nome Parâmetro", "Unidade Medida",
    "Média Horária", "Média Móvel", "Válido",
)

#: Convenção usual em qualidade do ar: média diária exige 75% das horas.
MIN_HORAS_DIA = 18

_AUSENTES = {"-", "", "nan", "None", "NaN"}

#: Unidades de concentração — o caso original deste parser.
UNIDADES_CONCENTRACAO = frozenset({"µg/m3", "ug/m3", "µg/m³", "ppm"})

#: Unidades meteorológicas aceitas: TEMP (°C), UR (%) e VV (m/s).
#:
#: A lista é curta de propósito. Tudo aqui é escalar, então a média horária e a
#: agregação diária significam a mesma coisa que para concentração. Direção do
#: vento (DV/DVG, em graus) fica **de fora**: é grandeza circular, e a média
#: aritmética de 350° e 10° dá 180° — o oposto do vento real. Quem precisar de
#: DV tem de somar componentes vetoriais antes, e este parser não faz isso.
UNIDADES_METEOROLOGIA = frozenset({"°C", "%", "m/s"})

UNIDADES_ACEITAS = UNIDADES_CONCENTRACAO | UNIDADES_METEOROLOGIA


def _unidade_do_rotulo(rotulo: str) -> str:
    """'TEMP(Temperatura do Ar) - °C' -> '°C'. Sem ' - ', devolve o rótulo todo."""
    return rotulo.rsplit(" - ", 1)[-1].strip() if " - " in rotulo else rotulo.strip()


def _numero(v) -> float:
    """'27' -> 27.0 · '3,5' -> 3.5 · '-' -> NaN. Nunca devolve 0 por ausência."""
    s = str(v).strip()
    if s in _AUSENTES:
        return np.nan
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return np.nan


def ler_exportacao(caminho) -> pd.DataFrame:
    """Lê UM CSV do QUALAR e devolve o horário tidy, validado."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise RuntimeError(f"exportação não encontrada: {caminho}")

    df = pd.read_csv(caminho, sep=";", encoding="latin-1", dtype=str)

    faltando = [c for c in COLUNAS_QUALAR if c not in df.columns]
    if faltando:
        raise RuntimeError(
            f"{caminho.name}: colunas do QUALAR ausentes: {faltando}\n"
            f"Colunas presentes: {list(df.columns)}\n"
            f"Se o QUALAR mudou o layout, este parser precisa ser revisto — "
            f"não adivinhe a correspondência."
        )

    unidades = set(df["Unidade Medida"].dropna().str.strip().unique())
    if not unidades <= UNIDADES_ACEITAS:
        raise RuntimeError(
            f"{caminho.name}: unidade inesperada {unidades - UNIDADES_ACEITAS}. "
            f"Aceitas: {sorted(UNIDADES_ACEITAS)}. Direção do vento é circular e "
            f"não pode ser promediada por este parser — veja UNIDADES_METEOROLOGIA."
        )

    # ---- hora: 01..24, o rótulo é o FIM do intervalo; o dia não desloca
    hora_fim = df["Hora"].str.strip().str.slice(0, 2)
    if not hora_fim.str.fullmatch(r"\d{2}").all():
        ruins = df.loc[~hora_fim.str.fullmatch(r"\d{2}").fillna(False), "Hora"].unique()
        raise RuntimeError(f"{caminho.name}: horas em formato inesperado: {ruins[:5]}")
    hora_fim = hora_fim.astype(int)
    if not hora_fim.between(1, 24).all():
        raise RuntimeError(
            f"{caminho.name}: horas fora de 1..24: {sorted(hora_fim[~hora_fim.between(1,24)].unique())[:5]}"
        )

    data = pd.to_datetime(df["Data"].str.strip(), format="%d/%m/%Y", errors="coerce")
    if data.isna().any():
        ruins = df.loc[data.isna(), "Data"].unique()
        raise RuntimeError(f"{caminho.name}: datas inválidas: {list(ruins[:5])}")

    valido = df["Válido"].str.strip().str.lower().eq("sim")
    valor = df["Média Horária"].map(_numero)
    # 'Válido' != 'Sim' invalida a medição, mesmo com número presente
    valor = valor.where(valido, np.nan)

    out = pd.DataFrame(
        {
            "data": data,
            "hora_fim": hora_fim,
            "estacao_codigo": df["Código Estação"].str.strip(),
            "estacao_nome": df["Nome Estação"].str.strip(),
            "parametro": df["Nome Parâmetro"].str.strip(),
            "valor": valor,
            "valido": valido,
            "arquivo": caminho.name,
        }
    )

    dup = out.duplicated(["estacao_codigo", "data", "hora_fim"])
    if dup.any():
        ex = out.loc[dup, ["estacao_codigo", "data", "hora_fim"]].head(3).to_dict("records")
        raise RuntimeError(f"{caminho.name}: {int(dup.sum())} duplicatas (estação,data,hora). Ex.: {ex}")

    return out.sort_values(["estacao_codigo", "data", "hora_fim"]).reset_index(drop=True)


def ler_exportacao_avancada(caminho) -> pd.DataFrame:
    """Lê o CSV de "Exportar Dados AVANÇADO" — formato LARGO, diferente do simples.

    O QUALAR tem duas telas de exportação e elas produzem layouts distintos.
    A avançada permite até 3 parâmetros por arquivo e sai assim::

        Tipo de Monitoramento:;CETESB
        Tipo de Rede:;Automática
        Tipo de Dado:;Primários
        Código da estação:;83
        Nome da estação:;Ibirapuera
        <linha vazia>
        Data;Hora;Média Horária;Média Horária;Média Horária
        ;;MP10(...) - µg/m3;MP2.5(...) - µg/m3;NO2(...) - µg/m3
        01/01/2019;01:00;;17;

    Uma coluna por parâmetro; célula vazia é ausência. A estação vem nos
    metadados, não repetida por linha.

    ⚠️ **Este formato NÃO traz a coluna `Válido`.** O export simples traz. Aqui
    não há como distinguir "medição inválida" de "medição válida", então todo
    número presente é aceito. Declare essa limitação se usar esta via.

    Devolve o MESMO formato tidy de `ler_exportacao`, para os agregadores não
    precisarem saber de qual tela o arquivo veio.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise RuntimeError(f"exportação não encontrada: {caminho}")

    linhas = caminho.read_text(encoding="latin-1").splitlines()
    if len(linhas) < 9:
        raise RuntimeError(f"{caminho.name}: só {len(linhas)} linhas; formato avançado esperado")

    # ------------------------------------------------------------- metadados
    meta: dict[str, str] = {}
    for ln in linhas[:6]:
        if ";" in ln:
            k, _, v = ln.partition(";")
            meta[k.strip().rstrip(":").lower()] = v.strip()

    cod = meta.get("código da estação") or meta.get("codigo da estacao")
    nome = meta.get("nome da estação") or meta.get("nome da estacao")
    if not cod or not nome:
        raise RuntimeError(
            f"{caminho.name}: metadados da estação não encontrados nas 6 primeiras linhas.\n"
            f"Lido: {meta}"
        )

    # --------------------------------------- localizar as duas linhas de cabeçalho
    i_cab = next((i for i, ln in enumerate(linhas) if ln.startswith("Data;Hora")), None)
    if i_cab is None or i_cab + 1 >= len(linhas):
        raise RuntimeError(f"{caminho.name}: cabeçalho 'Data;Hora' não encontrado")

    rotulos = linhas[i_cab + 1].split(";")[2:]        # nomes dos parâmetros
    parametros = [r.strip() for r in rotulos]
    if not parametros or not any(parametros):
        raise RuntimeError(f"{caminho.name}: linha de parâmetros vazia: {linhas[i_cab + 1]!r}")

    for p in parametros:
        if p and _unidade_do_rotulo(p) not in UNIDADES_ACEITAS:
            raise RuntimeError(
                f"{caminho.name}: unidade inesperada no parâmetro {p!r} "
                f"(unidade lida: {_unidade_do_rotulo(p)!r}). "
                f"Aceitas: {sorted(UNIDADES_ACEITAS)}. Direção do vento é circular e "
                f"não pode ser promediada por este parser — veja UNIDADES_METEOROLOGIA."
            )

    # ------------------------------------------------------------------- dados
    registros = []
    for n, ln in enumerate(linhas[i_cab + 2:], start=i_cab + 3):
        if not ln.strip():
            continue
        campos = ln.split(";")
        if len(campos) < 2 + len(parametros):
            raise RuntimeError(
                f"{caminho.name}: linha {n} tem {len(campos)} campos, "
                f"esperava {2 + len(parametros)}: {ln!r}"
            )
        d_txt, h_txt = campos[0].strip(), campos[1].strip()
        for p, v in zip(parametros, campos[2 : 2 + len(parametros)]):
            if not p:
                continue
            registros.append((d_txt, h_txt, p, v))

    if not registros:
        raise RuntimeError(f"{caminho.name}: nenhuma linha de dado após o cabeçalho")

    df = pd.DataFrame(registros, columns=["Data", "Hora", "parametro", "valor_txt"])

    hora_fim = df["Hora"].str.slice(0, 2)
    if not hora_fim.str.fullmatch(r"\d{2}").all():
        raise RuntimeError(f"{caminho.name}: horas em formato inesperado")
    hora_fim = hora_fim.astype(int)
    if not hora_fim.between(1, 24).all():
        raise RuntimeError(f"{caminho.name}: horas fora de 1..24")

    data = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    if data.isna().any():
        raise RuntimeError(f"{caminho.name}: datas inválidas: {df.loc[data.isna(),'Data'].unique()[:5]}")

    out = pd.DataFrame(
        {
            "data": data,
            "hora_fim": hora_fim,
            "estacao_codigo": str(cod),
            "estacao_nome": str(nome),
            "parametro": df["parametro"],
            "valor": df["valor_txt"].map(_numero),
            # sem coluna Válido neste formato: assume-se válido o que tem número
            "valido": df["valor_txt"].map(lambda v: str(v).strip() not in _AUSENTES),
            "arquivo": caminho.name,
        }
    )

    dup = out.duplicated(["estacao_codigo", "parametro", "data", "hora_fim"])
    if dup.any():
        raise RuntimeError(f"{caminho.name}: {int(dup.sum())} duplicatas (estação,parâmetro,data,hora)")

    return out.sort_values(["parametro", "data", "hora_fim"]).reset_index(drop=True)


def ler_qualquer(caminho) -> pd.DataFrame:
    """Detecta qual das duas telas gerou o arquivo e usa o leitor certo."""
    caminho = Path(caminho)
    primeira = caminho.read_text(encoding="latin-1").splitlines()[:1]
    if primeira and primeira[0].startswith("Tipo de Rede;"):
        return ler_exportacao(caminho)          # export simples, formato longo
    if primeira and primeira[0].startswith("Tipo de Monitoramento:"):
        return ler_exportacao_avancada(caminho)  # export avançado, formato largo
    raise RuntimeError(
        f"{caminho.name}: primeira linha não corresponde a nenhum dos dois formatos "
        f"conhecidos do QUALAR: {primeira[:1]}"
    )


def ler_varias(caminhos) -> pd.DataFrame:
    """Concatena várias exportações. Duplicata entre arquivos é erro."""
    partes = [ler_exportacao(c) for c in caminhos]
    if not partes:
        raise RuntimeError("nenhuma exportação informada")
    todas = pd.concat(partes, ignore_index=True)
    dup = todas.duplicated(["estacao_codigo", "data", "hora_fim"], keep=False)
    if dup.any():
        arqs = sorted(todas.loc[dup, "arquivo"].unique())
        raise RuntimeError(
            f"{int(dup.sum())} registros duplicados entre arquivos: {arqs}. "
            f"Exportações sobrepostas — remova a repetição antes de agregar."
        )
    return todas.sort_values(["estacao_codigo", "data", "hora_fim"]).reset_index(drop=True)


def agregar_diario_por_estacao(horario: pd.DataFrame, min_horas: int = MIN_HORAS_DIA) -> pd.DataFrame:
    """Média diária por estação, exigindo cobertura mínima de horas.

    Dia com menos de `min_horas` medições válidas vira NaN — **não vira zero**,
    e não é descartado em silêncio: sai no relatório com a contagem.
    """
    if min_horas < 1 or min_horas > 24:
        raise ValueError(f"min_horas deve estar em 1..24, recebido {min_horas}")

    g = horario.groupby(["estacao_codigo", "estacao_nome", "data"], as_index=False).agg(
        pm25=("valor", "mean"),
        n_horas=("valor", "count"),
    )
    insuficientes = int((g["n_horas"] < min_horas).sum())
    g.loc[g["n_horas"] < min_horas, "pm25"] = np.nan
    g.attrs["dias_descartados_por_cobertura"] = insuficientes
    g.attrs["min_horas"] = min_horas
    return g


def agregar_municipio(diario_estacao: pd.DataFrame, min_estacoes: int = 2, eps: float = 1e-9) -> pd.DataFrame:
    """Agrega as estações num único registro diário do município.

    Produz o contrato consumido por `forecasting_features.py`:
        data · pm25_media · pm25_n_estacoes · pm25_dt

    `pm25_dt` é o índice de dispersão espacial D_t = sigma/(mu+eps), com sigma
    amostral (ddof=1). **Exige pelo menos 2 estações no dia** — é exatamente a
    divisão por (N−1) que torna o D_t impossível sobre o CAMS, que tem N=1.
    Dias com menos estações recebem NaN em `pm25_dt`, nunca zero.
    """
    val = diario_estacao.dropna(subset=["pm25"])
    g = val.groupby("data", as_index=False).agg(
        pm25_media=("pm25", "mean"),
        pm25_n_estacoes=("pm25", "count"),
        _sigma=("pm25", lambda s: s.std(ddof=1)),
    )
    g["pm25_dt"] = np.where(
        g["pm25_n_estacoes"] >= max(2, min_estacoes),
        g["_sigma"] / (g["pm25_media"] + eps),
        np.nan,
    )
    return g.drop(columns="_sigma").sort_values("data").reset_index(drop=True)


def relatorio(horario: pd.DataFrame, diario: pd.DataFrame, municipio: pd.DataFrame) -> dict:
    return {
        "registros_horarios": int(len(horario)),
        "estacoes": sorted(horario["estacao_nome"].unique().tolist()),
        "codigos_qualar": sorted(horario["estacao_codigo"].unique().tolist()),
        "parametros": sorted(horario["parametro"].unique().tolist()),
        "periodo": [str(horario["data"].min().date()), str(horario["data"].max().date())],
        "horas_invalidas": int((~horario["valido"]).sum()),
        "horas_sem_valor": int(horario["valor"].isna().sum()),
        "dias_estacao": int(len(diario)),
        "dias_descartados_por_cobertura": int(diario.attrs.get("dias_descartados_por_cobertura", 0)),
        "min_horas_exigidas": int(diario.attrs.get("min_horas", MIN_HORAS_DIA)),
        "dias_municipio": int(len(municipio)),
        "dias_com_dt": int(municipio["pm25_dt"].notna().sum()),
        "media_pm25": float(municipio["pm25_media"].mean()) if len(municipio) else None,
    }
