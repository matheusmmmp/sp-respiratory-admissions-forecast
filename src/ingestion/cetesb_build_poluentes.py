"""Série diária MULTI-POLUENTE da CETESB, a partir das exportações do QUALAR.

Generaliza `cetesb_build_daily.py`, que só monta MP2.5. Aqui sai um frame largo
com uma coluna por poluente disponível, mais a contagem de estações e o `D_t` de
cada um.

Motivação: a literatura de epidemiologia ambiental atribui efeito a PM10, NO2,
SO2, O3 e CO, não só ao PM2.5. O projeto nunca testou nenhum deles — o CAMS
nunca entregou os gases (o fallback degradava a requisição em silêncio) e a
CETESB estava vazia. O NO2 veio de carona nas exportações de MP10+MP2.5+NO2 e
está em disco sem ter sido integrado.

Saída: data/processed/cetesb_poluentes_daily.csv
    data · <pol>_media · <pol>_n_estacoes · <pol>_dt   para cada poluente

    python -m src.ingestion.cetesb_build_poluentes --dir C:/Users/mathe/Downloads
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.ingestion.cetesb_estacoes import estacoes_municipio_sp  # noqa: E402
from src.ingestion.cetesb_qualar_parser import (  # noqa: E402
    MIN_HORAS_DIA, agregar_diario_por_estacao, agregar_municipio, ler_qualquer,
)

SAIDA = RAIZ / "data" / "processed" / "cetesb_poluentes_daily.csv"
META = RAIZ / "data" / "processed" / "cetesb_poluentes_daily.meta.json"

#: prefixo como o QUALAR escreve -> nome curto de coluna
POLUENTES = {
    "MP10": "pm10", "MP2.5": "pm25", "NO2": "no2",
    "SO2": "so2", "O3": "o3", "CO": "co",
}


def _curto(rotulo: str) -> str | None:
    base = str(rotulo).split("(")[0].strip()
    return POLUENTES.get(base)


def coletar(pasta: Path, padrao: str = "*.csv") -> tuple[pd.DataFrame, dict]:
    """Todas as medições horárias de poluentes-alvo, estações do município."""
    nomes_ok = set(estacoes_municipio_sp()["nome_qualar"])
    partes, lidos, ignorados, fora = [], [], 0, set()

    for arq in sorted(pasta.glob(padrao)):
        try:
            h = ler_qualquer(arq)
        except Exception:  # noqa: BLE001 - CSV alheio ao QUALAR é esperado
            ignorados += 1
            continue
        h["pol"] = h["parametro"].map(_curto)
        h = h[h["pol"].notna()]
        if h.empty:
            continue
        est = h["estacao_nome"].iloc[0]
        if est not in nomes_ok:
            fora.add(est)
            continue
        partes.append(h)
        lidos.append(arq.name)

    if not partes:
        raise RuntimeError(f"nenhuma exportação com poluente-alvo em {pasta}")

    todas = pd.concat(partes, ignore_index=True)
    antes = len(todas)
    todas = todas.drop_duplicates(
        ["estacao_nome", "pol", "data", "hora_fim"], keep="first"
    ).reset_index(drop=True)

    rel = {
        "arquivos_usados": len(lidos),
        "arquivos_ignorados": ignorados,
        "estacoes_fora_do_municipio": sorted(fora),
        "registros_antes_dedup": int(antes),
        "registros_apos_dedup": int(len(todas)),
        "repeticoes_descartadas": int(antes - len(todas)),
        "poluentes_encontrados": sorted(todas["pol"].unique().tolist()),
        "periodo": [str(todas["data"].min().date()), str(todas["data"].max().date())],
    }
    return todas, rel


def main() -> None:
    ap = argparse.ArgumentParser(description="Série diária multi-poluente da CETESB")
    ap.add_argument("--dir", type=Path, default=Path.home() / "Downloads")
    ap.add_argument("--min-horas", type=int, default=MIN_HORAS_DIA)
    ap.add_argument("--saida", type=Path, default=SAIDA,
                    help="CSV de saída (padrão: data/processed/cetesb_poluentes_daily.csv); o .meta.json vai ao lado")
    args = ap.parse_args()
    saida = args.saida
    meta = saida.parent / (saida.stem + ".meta.json")

    if not args.dir.is_dir():
        raise SystemExit(f"pasta inexistente: {args.dir}")

    horario, rel = coletar(args.dir)
    print("=" * 74)
    print("COLETA")
    print("=" * 74)
    for k, v in rel.items():
        print(f"  {k}: {v}")

    frames, resumo = [], []
    for pol in sorted(horario["pol"].unique()):
        sub = horario[horario["pol"] == pol]
        diario = agregar_diario_por_estacao(sub, min_horas=args.min_horas)
        mun = agregar_municipio(diario).rename(
            columns={
                "pm25_media": f"{pol}_media",
                "pm25_n_estacoes": f"{pol}_n_estacoes",
                "pm25_dt": f"{pol}_dt",
            }
        )
        frames.append(mun.set_index("data"))
        resumo.append(
            {
                "poluente": pol,
                "estacoes": int(sub["estacao_nome"].nunique()),
                "dias": int(len(mun)),
                "media": round(float(mun[f"{pol}_media"].mean()), 2),
                "dias_com_dt": int(mun[f"{pol}_dt"].notna().sum()),
                "n_est_medio": round(float(mun[f"{pol}_n_estacoes"].mean()), 2),
            }
        )

    print()
    print("=" * 74)
    print("SÉRIE DO MUNICÍPIO, POR POLUENTE")
    print("=" * 74)
    print(pd.DataFrame(resumo).to_string(index=False))

    largo = pd.concat(frames, axis=1).sort_index()
    largo.index.name = "data"
    saida.parent.mkdir(parents=True, exist_ok=True)
    largo.to_csv(saida)

    faltando = [c for c in POLUENTES.values() if f"{c}_media" not in largo.columns]
    meta.write_text(
        json.dumps(
            {
                "fonte": "CETESB/QUALAR, tela 'Exportar Dados Avançado'",
                "regra_diaria": f"média das horas válidas, exigindo >= {args.min_horas} de 24",
                "regra_dt": "sigma amostral (ddof=1)/(media+1e-9), exigindo >= 2 estações",
                "poluentes_presentes": sorted(horario["pol"].unique().tolist()),
                "poluentes_ausentes": faltando,
                "motivo_ausentes": (
                    "SO2, O3 e CO ficaram nas 22 exportações interrompidas por HTTP 503 do QUALAR. "
                    "O CAMS nunca os entregou (fallback silencioso do downloader)."
                ),
                "limitacao_valido": (
                    "a tela Avançado não traz a coluna Válido; se ela exclui inválidos como a "
                    "tela simples permanece [EM ABERTO]"
                ),
                "extraido_em": datetime.now().isoformat(timespec="seconds"),
                "coleta": rel,
                "por_poluente": resumo,
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    if faltando:
        print(f"  AUSENTES (nunca obtidos): {faltando}")
    print(f"salvo: {saida}")
    print(f"meta : {meta}")


if __name__ == "__main__":
    main()
