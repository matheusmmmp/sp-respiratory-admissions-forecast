"""Série diária de METEOROLOGIA medida na superfície, da CETESB/QUALAR.

POR QUE ESTE MÓDULO EXISTE
--------------------------
O benchmark de 27/07/2026 (5 sementes, 20 comparações pareadas) mostrou que o
bloco METEO **piora** o modelo de forma consistente, p<0,001 em toda combinação
que o contém. Só que essa meteorologia vinha do **CAMS** — uma reanálise que
entrega uma célula de grade para 12 milhões de habitantes. Duas leituras
concorriam, e nenhuma podia ser separada da outra sem dado novo:

  (a) meteorologia não ajuda a prever internações neste desenho; ou
  (b) a meteorologia *do CAMS* é ruim.

Este módulo produz o dado que separa as duas: temperatura, umidade e vento
**medidos em estação de superfície**, agregados ao dia, no mesmo contrato das
séries de poluentes.

O QUE A LITERATURA PEDE, E O QUE ISSO MUDA NA AGREGAÇÃO
-------------------------------------------------------
Temperatura é o preditor meteorológico dominante em internação respiratória, e o
efeito é tipicamente **não-linear e assimétrico** — frio e calor extremos agem
por mecanismos diferentes, e o efeito do frio costuma ter defasagem de dias. Uma
média diária apaga justamente isso. Por isso saem, por dia:

    temp_media · temp_min · temp_max · temp_amplitude

`temp_amplitude` (max − min) é a variação térmica intradiária, associada na
literatura a agravamento respiratório de forma independente do nível médio.
Umidade e vento saem como média diária, que é o uso corrente.

⚠️ NÃO EXISTE D_t AQUI. O índice de dispersão espacial faz sentido para
poluente, que varia fortemente entre bairros. Temperatura é campo regional e
suave — a dispersão entre estações mede topografia e ilha de calor, não
exposição. Calcular `_dt` para meteorologia seria inventar um preditor.

⚠️ COBERTURA ESPACIAL É RUIM, E ISSO É PROPRIEDADE DA REDE
-----------------------------------------------------------
No município de São Paulo, apenas **Parque D.Pedro II e Marg.Tietê-Pte Remédios**
medem temperatura E umidade nos 6 anos. Capão Redondo mede só temperatura;
Pinheiros só umidade. Ver `data/cetesb/disponibilidade_meteo.csv`.

Por isso `--incluir-rmsp` existe: estações da Região Metropolitana
(Carapicuíba, Guarulhos, S.Bernardo, Taboão da Serra) entram como reforço.
Isso é defensável **para temperatura e umidade**, que são regionais, e é bem
mais frágil para vento, que responde a rugosidade local. Se usar, declare.

    python -m src.ingestion.cetesb_build_meteo --dir C:/Users/mathe/Downloads
    python -m src.ingestion.cetesb_build_meteo --incluir-rmsp
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.ingestion.cetesb_estacoes import estacoes_municipio_sp  # noqa: E402
from src.ingestion.cetesb_qualar_parser import MIN_HORAS_DIA, ler_qualquer  # noqa: E402

#: Os dois recortes saem em arquivos SEPARADOS, de propósito: são hipóteses
#: diferentes sobre o que representa a exposição da cidade, e sobrescrever um
#: com o outro esconderia qual foi usado no experimento.
SAIDA = RAIZ / "data" / "processed" / "cetesb_meteo_daily.csv"
SAIDA_RMSP = RAIZ / "data" / "processed" / "cetesb_meteo_daily_rmsp.csv"

#: prefixo como o QUALAR escreve -> nome curto de coluna
METEO = {"TEMP": "temp", "UR": "ur", "VV": "vv"}

#: Estações da RMSP fora do município, usadas só com --incluir-rmsp.
#: Defensáveis para temperatura/umidade (campo regional); frágeis para vento.
RMSP_PROXY = (
    "Carapicuíba", "Guarulhos-Paço Municipal", "Guarulhos-Pimentas",
    "S.Bernardo-Centro", "Taboão da Serra", "Osasco", "S.André-Capuava",
)


def _curto(rotulo: str) -> str | None:
    return METEO.get(str(rotulo).split("(")[0].strip())


def coletar(pasta: Path, incluir_rmsp: bool = False, padrao: str = "*.csv"):
    """Medições horárias de TEMP/UR/VV das estações aceitas."""
    nomes_ok = set(estacoes_municipio_sp()["nome_qualar"])
    if incluir_rmsp:
        nomes_ok |= set(RMSP_PROXY)

    partes, lidos, ignorados, fora = [], [], 0, set()
    for arq in sorted(pasta.glob(padrao)):
        try:
            h = ler_qualquer(arq)
        except Exception:  # noqa: BLE001 - CSV alheio ao QUALAR é esperado
            ignorados += 1
            continue
        h["var"] = h["parametro"].map(_curto)
        h = h[h["var"].notna()]
        if h.empty:
            continue
        est = h["estacao_nome"].iloc[0]
        if est not in nomes_ok:
            fora.add(est)
            continue
        partes.append(h)
        lidos.append(arq.name)

    if not partes:
        raise RuntimeError(f"nenhuma exportação com TEMP/UR/VV em {pasta}")

    todas = pd.concat(partes, ignore_index=True)
    antes = len(todas)
    todas = todas.drop_duplicates(
        ["estacao_nome", "var", "data", "hora_fim"], keep="first"
    ).reset_index(drop=True)
    todas = todas.dropna(subset=["valor"])

    rel = {
        "arquivos_usados": len(lidos),
        "arquivos_ignorados": ignorados,
        "estacoes_fora_do_recorte": sorted(fora),
        "registros_antes_dedup": int(antes),
        "repeticoes_descartadas": int(antes - len(todas)),
        "variaveis_encontradas": sorted(todas["var"].unique().tolist()),
        "estacoes": sorted(todas["estacao_nome"].unique().tolist()),
        "periodo": [str(todas["data"].min().date()), str(todas["data"].max().date())],
    }
    return todas, rel


def diario_por_estacao(horario: pd.DataFrame, var: str, min_horas: int) -> pd.DataFrame:
    """Estatísticas diárias por estação. Dia com cobertura baixa vira NaN."""
    sub = horario[horario["var"] == var]
    if sub.empty:
        return pd.DataFrame()
    g = sub.groupby(["estacao_nome", "data"], as_index=False).agg(
        media=("valor", "mean"), minimo=("valor", "min"),
        maximo=("valor", "max"), n_horas=("valor", "count"),
    )
    ruim = g["n_horas"] < min_horas
    g.loc[ruim, ["media", "minimo", "maximo"]] = np.nan
    g.attrs["dias_descartados_por_cobertura"] = int(ruim.sum())
    return g


def agregar_municipio(diario: pd.DataFrame, var: str) -> pd.DataFrame:
    """Média entre estações. Sem D_t — ver o cabeçalho do módulo."""
    val = diario.dropna(subset=["media"])
    if val.empty:
        return pd.DataFrame()
    g = val.groupby("data", as_index=False).agg(
        **{
            f"{var}_media": ("media", "mean"),
            f"{var}_n_estacoes": ("media", "count"),
        }
    )
    if var == "temp":
        extremos = val.groupby("data", as_index=False).agg(
            temp_min=("minimo", "mean"), temp_max=("maximo", "mean"),
        )
        g = g.merge(extremos, on="data")
        g["temp_amplitude"] = g["temp_max"] - g["temp_min"]
    return g.sort_values("data").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Série diária de meteorologia da CETESB")
    ap.add_argument("--dir", type=Path, default=Path.home() / "Downloads")
    ap.add_argument("--min-horas", type=int, default=MIN_HORAS_DIA)
    ap.add_argument("--incluir-rmsp", action="store_true",
                    help="agrega estações da Região Metropolitana como reforço")
    ap.add_argument("--saida", type=Path, default=None,
                    help="CSV de saída (padrão: data/processed/cetesb_meteo_daily[_rmsp].csv); o .meta.json vai ao lado")
    args = ap.parse_args()

    if not args.dir.is_dir():
        raise SystemExit(f"pasta inexistente: {args.dir}")

    horario, rel = coletar(args.dir, incluir_rmsp=args.incluir_rmsp)
    print("=" * 74)
    print("COLETA" + ("  (COM reforço da RMSP)" if args.incluir_rmsp else "  (só município)"))
    print("=" * 74)
    for k, v in rel.items():
        print(f"  {k}: {v}")

    frames, resumo, descartes = [], [], {}
    for var in sorted(horario["var"].unique()):
        d = diario_por_estacao(horario, var, args.min_horas)
        descartes[var] = int(d.attrs.get("dias_descartados_por_cobertura", 0))
        mun = agregar_municipio(d, var)
        if mun.empty:
            continue
        frames.append(mun.set_index("data"))
        resumo.append({
            "variavel": var,
            "estacoes": int(d["estacao_nome"].nunique()),
            "dias": int(len(mun)),
            "media": round(float(mun[f"{var}_media"].mean()), 2),
            "n_est_medio": round(float(mun[f"{var}_n_estacoes"].mean()), 2),
            "dias_1_estacao": int((mun[f"{var}_n_estacoes"] == 1).sum()),
        })

    print()
    print("=" * 74)
    print("SÉRIE DIÁRIA")
    print("=" * 74)
    print(pd.DataFrame(resumo).to_string(index=False))

    # sort=False explícito: o pandas 4 deixa de ordenar por padrão ao concatenar
    # DatetimeIndex, e a ordem do arquivo final não pode depender dessa mudança.
    largo = pd.concat(frames, axis=1, sort=False).sort_index()
    largo.index.name = "data"
    saida = args.saida or (SAIDA_RMSP if args.incluir_rmsp else SAIDA)
    meta = saida.parent / (saida.stem + ".meta.json")
    saida.parent.mkdir(parents=True, exist_ok=True)
    largo.to_csv(saida)

    esperado = pd.date_range(largo.index.min(), largo.index.max(), freq="D")
    buracos = int(len(esperado) - len(largo))

    meta.write_text(json.dumps({
        "fonte": "CETESB/QUALAR, tela 'Exportar Dados Avançado'",
        "recorte": "município de São Paulo" + (" + RMSP como reforço" if args.incluir_rmsp else ""),
        "regra_diaria": f"média/min/max das horas válidas, exigindo >= {args.min_horas} de 24",
        "sem_dt": ("D_t não é calculado: dispersão espacial de temperatura mede topografia "
                   "e ilha de calor, não exposição. Ver o cabeçalho do módulo."),
        "temp_amplitude": "temp_max - temp_min, variação térmica intradiária",
        "dias_sem_cobertura": buracos,
        "dias_descartados_por_cobertura": descartes,
        "limitacao_valido": "a tela Avançado não traz a coluna Válido",
        "extraido_em": datetime.now().isoformat(timespec="seconds"),
        "coleta": rel,
        "por_variavel": resumo,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    if buracos:
        print(f"  ATENÇÃO: {buracos} dias do intervalo sem nenhuma estação com cobertura")
    print(f"salvo: {saida}")
    print(f"meta : {meta}")


if __name__ == "__main__":
    main()
