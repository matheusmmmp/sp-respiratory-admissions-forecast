"""Monta a série diária de PM2.5 da CETESB a partir das exportações do QUALAR.

Produz o contrato que `src/features/forecasting_features.py` consome quando
`fonte_pm25: cetesb`:

    data · pm25_media · pm25_n_estacoes · pm25_dt

`pm25_dt` é o índice de dispersão espacial D_t = sigma/(mu+eps), com sigma
amostral (ddof=1). Exige N >= 2 estações no dia — é a mesma divisão por (N-1)
que torna o índice **impossível** sobre o CAMS, que entrega uma célula de grade.

DEDUPLICAÇÃO ENTRE ARQUIVOS
---------------------------
As exportações se sobrepõem: há arquivos de 2022 de uma captura anterior e
arquivos 2019-2024 de outra, cobrindo o mesmo período. Uma medição repetida em
dois arquivos é a MESMA medição, não duas. Aqui a chave
(estação, parâmetro, data, hora) é deduplicada mantendo a primeira ocorrência, e
o número de repetições descartadas entra no relatório — não é silencioso.

    python -m src.ingestion.cetesb_build_daily --dir C:/Users/mathe/Downloads
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

from src.ingestion.cetesb_estacoes import estacoes_pm25_sp  # noqa: E402
from src.ingestion.cetesb_qualar_parser import (  # noqa: E402
    MIN_HORAS_DIA, agregar_diario_por_estacao, agregar_municipio, ler_qualquer,
)

SAIDA = RAIZ / "data" / "processed" / "cetesb_pm25_daily.csv"
META = RAIZ / "data" / "processed" / "cetesb_pm25_daily.meta.json"


def coletar_mp25(pasta: Path, padrao: str = "*.csv") -> tuple[pd.DataFrame, dict]:
    """Lê todas as exportações, mantém só MP2.5 das estações do município."""
    nomes_ok = set(estacoes_pm25_sp()["nome_qualar"])
    partes, lidos, ignorados, fora = [], [], [], set()

    for arq in sorted(pasta.glob(padrao)):
        try:
            h = ler_qualquer(arq)
        except Exception:  # noqa: BLE001 - CSV alheio ao QUALAR é esperado na pasta
            ignorados.append(arq.name)
            continue

        mp = h[h["parametro"].str.startswith("MP2.5")].copy()
        if mp.empty:
            continue
        est = mp["estacao_nome"].iloc[0]
        if est not in nomes_ok:
            fora.add(est)
            continue
        partes.append(mp)
        lidos.append(arq.name)

    if not partes:
        raise RuntimeError(
            f"nenhuma exportação com MP2.5 de estação do município em {pasta}.\n"
            f"Arquivos ignorados por formato: {len(ignorados)}"
        )

    todas = pd.concat(partes, ignore_index=True)
    antes = len(todas)
    chave = ["estacao_nome", "parametro", "data", "hora_fim"]
    todas = todas.drop_duplicates(chave, keep="first").reset_index(drop=True)
    repetidas = antes - len(todas)

    rel = {
        "arquivos_com_mp25": len(lidos),
        "arquivos_ignorados_outro_formato": len(ignorados),
        "estacoes_fora_do_municipio_descartadas": sorted(fora),
        "registros_horarios_antes_da_dedup": int(antes),
        "registros_horarios_apos_dedup": int(len(todas)),
        "repeticoes_entre_arquivos_descartadas": int(repetidas),
        "estacoes": sorted(todas["estacao_nome"].unique().tolist()),
        "periodo": [str(todas["data"].min().date()), str(todas["data"].max().date())],
    }
    return todas, rel


def main() -> None:
    ap = argparse.ArgumentParser(description="Série diária de PM2.5 da CETESB")
    ap.add_argument("--dir", type=Path, default=Path.home() / "Downloads")
    ap.add_argument("--min-horas", type=int, default=MIN_HORAS_DIA)
    ap.add_argument("--min-estacoes", type=int, default=2)
    args = ap.parse_args()

    if not args.dir.is_dir():
        raise SystemExit(f"pasta inexistente: {args.dir}")

    horario, rel = coletar_mp25(args.dir)
    print("=" * 74)
    print("COLETA")
    print("=" * 74)
    for k, v in rel.items():
        print(f"  {k}: {v}")

    diario_est = agregar_diario_por_estacao(horario, min_horas=args.min_horas)
    print()
    print("=" * 74)
    print(f"DIÁRIO POR ESTAÇÃO (exige >= {args.min_horas}h de 24)")
    print("=" * 74)
    porest = diario_est.groupby("estacao_nome").agg(
        dias=("pm25", "size"), validos=("pm25", "count"),
        media=("pm25", "mean"), minimo=("pm25", "min"), maximo=("pm25", "max"),
    ).round(2)
    porest["%_valido"] = (100 * porest["validos"] / porest["dias"]).round(1)
    print(porest.to_string())
    print(f"\n  dias-estação descartados por cobertura: "
          f"{diario_est.attrs['dias_descartados_por_cobertura']}")

    municipio = agregar_municipio(diario_est, min_estacoes=args.min_estacoes)
    print()
    print("=" * 74)
    print("SÉRIE DO MUNICÍPIO")
    print("=" * 74)
    print(f"  dias           : {len(municipio)}")
    print(f"  período        : {municipio['data'].min().date()} .. {municipio['data'].max().date()}")
    print(f"  média PM2.5    : {municipio['pm25_media'].mean():.2f} ug/m3")
    print(f"  dias com D_t   : {int(municipio['pm25_dt'].notna().sum())} "
          f"({100*municipio['pm25_dt'].notna().mean():.1f}%)")
    print(f"  D_t médio      : {municipio['pm25_dt'].mean():.4f}")
    print()
    print(municipio.groupby(municipio["data"].dt.year).agg(
        dias=("pm25_media", "size"), media=("pm25_media", "mean"),
        n_est_medio=("pm25_n_estacoes", "mean"), dt_medio=("pm25_dt", "mean"),
    ).round(3).to_string())

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    municipio.to_csv(SAIDA, index=False)

    meta = {
        "fonte": "CETESB/QUALAR — exportações manuais e assistidas, tela 'Exportar Dados Avançado'",
        "parametro": "MP2.5 (Partículas Inaláveis Finas), µg/m3",
        "criterio_espacial": "estações do município de São Paulo com MP2.5 no cadastro do QUALAR",
        "regra_diaria": f"média das horas válidas, exigindo >= {args.min_horas} de 24",
        "regra_dt": f"sigma amostral (ddof=1) / (media + 1e-9), exigindo >= {args.min_estacoes} estações",
        "convencao_hora": "rótulos 01:00..24:00 são o FIM do intervalo; as 24 horas são do mesmo dia",
        "limitacao_valido": (
            "a tela 'Avançado' NÃO traz a coluna Válido. O padrão do QUALAR é excluir "
            "inválidos (a tela simples tem a caixa 'Incluir Dados Inválidos', desmarcada "
            "por default), mas se o Avançado segue o mesmo padrão permanece [EM ABERTO]."
        ),
        "extraido_em": datetime.now().isoformat(timespec="seconds"),
        "coleta": rel,
        "dias": int(len(municipio)),
        "dias_com_dt": int(municipio["pm25_dt"].notna().sum()),
        "media_pm25": float(municipio["pm25_media"].mean()),
        "por_estacao": json.loads(porest.reset_index().to_json(orient="records")),
        "totais_anuais": {
            str(a): {"dias": int(g.size), "media": round(float(g.mean()), 3)}
            for a, g in municipio.groupby(municipio["data"].dt.year)["pm25_media"]
        },
    }
    META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"salvo: {SAIDA}")
    print(f"meta : {META}")


if __name__ == "__main__":
    main()
