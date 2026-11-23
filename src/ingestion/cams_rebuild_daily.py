#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reagrega o CAMS EAC4 a partir dos NetCDF JÁ BAIXADOS em data/raw/, corrigindo os
defeitos identificados na auditoria de 2026-07-25:

  1. Dias de borda parciais. A conversão UTC -> America/Sao_Paulo desloca o
     primeiro registro (2019-01-01T00:00Z) para 2018-12-31 21:00 local, criando
     um dia com 1 de 8 observações. A agregação anterior tratava esse dia como
     completo.
  2. Umidade relativa ausente. O download de 2026-01 perdeu `d2m`; o de 2025-08
     o preservou. Funde os dois conjuntos e deriva RH pela fórmula de Magnus.
  3. Unidades. pm2p5/pm10 vinham em kg/m3; converte para ug/m3 (x1e9).
  4. Descarte silencioso. Emite n_obs por dia e um relatorio de completude em
     vez de dropar linhas sem aviso.

NAO faz download. Apenas relê o que já está no disco.

Uso:
    python src/ingestion/cams_rebuild_daily.py
    python src/ingestion/cams_rebuild_daily.py --min-obs 8 --tz America/Sao_Paulo

    # 2026-10-19 — reagregar um download NOVO feito em diretório separado e
    # comparar com o canônico (sai com código 2 se divergir):
    python -m src.ingestion.cams_rebuild_daily \
        --raw-dir D:/Project/dados_rebaixa_2026-10/raw \
        --conjuntos cams_expanded_daily_2026-10-19 \
        --saida D:/Project/dados_rebaixa_2026-10/processed/cams_daily_v2.csv \
        --relatorio D:/Project/dados_rebaixa_2026-10/processed/cams_daily_v2_report.json \
        --comparar data/processed/cams_daily_v2.csv
"""

import argparse
import glob
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

RAW_DIR = Path("data") / "raw"
OUT_CSV = Path("data") / "processed" / "cams_daily_v2.csv"
OUT_REPORT = Path("reports") / "data_quality" / "cams_daily_v2_report.json"

# Conjuntos de NetCDF já baixados. O primeiro traz d2m; os demais trazem sp.
SOURCE_DIRS = [
    "cams_expanded_daily - 26-08-2025",
    "cams_expanded_daily_2026-01-23",
]

# Observações esperadas por dia: EAC4 é 3-horário (00,03,...,21).
EXPECTED_OBS_PER_DAY = 8

KG_M3_TO_UG_M3 = 1e9


def magnus_saturation_pressure(temp_c):
    """Pressão de vapor de saturação (hPa) — Magnus-Tetens."""
    return 6.112 * np.exp(17.67 * temp_c / (temp_c + 243.5))


def relative_humidity(t2m_c, d2m_c):
    """RH (%) a partir de temperatura e ponto de orvalho, ambos em °C."""
    rh = 100.0 * magnus_saturation_pressure(d2m_c) / magnus_saturation_pressure(t2m_c)
    return rh.clip(0.0, 100.0)


def load_dir_to_frame(dirname: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Lê todos os .nc de um diretório e devolve um DataFrame horário indexado por UTC."""
    files = sorted(glob.glob(str(raw_dir / dirname / "*.nc")))
    if not files:
        raise FileNotFoundError(f"Nenhum .nc em {raw_dir / dirname}")

    frames = []
    for path in files:
        with xr.open_dataset(path) as ds:
            # A grade tem 1 célula; squeeze remove latitude/longitude.
            df = ds.squeeze(drop=True).to_dataframe()
            frames.append(df)

    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    out.index = pd.to_datetime(out.index, utc=True)
    out.index.name = "time_utc"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tz", default="America/Sao_Paulo")
    ap.add_argument(
        "--min-obs",
        type=int,
        default=6,
        help="Mínimo de observações intradiárias para manter o dia (default 6 de 8)",
    )
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR,
                    help="pasta que contém os conjuntos de NetCDF (padrão: data/raw)")
    ap.add_argument("--conjuntos", nargs="+", default=SOURCE_DIRS,
                    help="subpastas de --raw-dir a fundir, na ordem (padrão: os dois downloads históricos)")
    ap.add_argument("--saida", type=Path, default=OUT_CSV, help="CSV diário de saída")
    ap.add_argument("--relatorio", type=Path, default=OUT_REPORT, help="JSON de completude")
    ap.add_argument("--comparar", type=Path, default=None,
                    help="CSV canônico para comparar dia a dia; código de saída 2 se divergir")
    args = ap.parse_args()
    out_csv, out_report = args.saida, args.relatorio
    if args.comparar is not None and args.comparar.resolve() == out_csv.resolve():
        raise SystemExit("--comparar aponta para a própria --saida: a comparação sobrescreveria o canônico")

    print("Lendo NetCDF já baixados (sem download)...")
    frames = {}
    for d in args.conjuntos:
        frames[d] = load_dir_to_frame(d, args.raw_dir)
        cols = sorted(c for c in frames[d].columns)
        print(f"  {d}: {len(frames[d])} registros, vars={cols}")

    # Funde os conjuntos: a união das colunas cobre pm2p5, pm10, t2m, d2m, u10, v10, sp.
    merged = None
    for d, df in frames.items():
        merged = df if merged is None else merged.combine_first(df)

    print(f"\nFundido: {len(merged)} registros horários, vars={sorted(merged.columns)}")

    # --- unidades e derivadas ---------------------------------------------
    for col in ("pm2p5", "pm10"):
        if col in merged.columns:
            merged[col] = merged[col] * KG_M3_TO_UG_M3  # kg/m3 -> ug/m3

    if "t2m" in merged.columns:
        merged["t2m_c"] = merged["t2m"] - 273.15
    if "d2m" in merged.columns:
        merged["d2m_c"] = merged["d2m"] - 273.15
    if {"t2m_c", "d2m_c"} <= set(merged.columns):
        merged["rh"] = relative_humidity(merged["t2m_c"], merged["d2m_c"])
    if {"u10", "v10"} <= set(merged.columns):
        merged["ws10"] = np.sqrt(merged["u10"] ** 2 + merged["v10"] ** 2)

    # --- fuso horário ------------------------------------------------------
    local = merged.tz_convert(args.tz)

    # --- agregação diária com contagem explícita ---------------------------
    value_cols = [c for c in local.columns if pd.api.types.is_numeric_dtype(local[c])]
    daily = local[value_cols].resample("D").mean()
    n_obs = local[value_cols[0]].resample("D").size().rename("n_obs")
    daily = daily.join(n_obs)
    daily.index = daily.index.tz_localize(None)
    daily.index.name = "data"

    daily["complete"] = daily["n_obs"] >= EXPECTED_OBS_PER_DAY

    # --- relatório ANTES de descartar qualquer coisa -----------------------
    partial = daily[~daily["complete"]]
    dropped = daily[daily["n_obs"] < args.min_obs]
    kept = daily[daily["n_obs"] >= args.min_obs]

    report = {
        "generated_from": list(args.conjuntos),
        "raw_dir": str(args.raw_dir),
        "tz": args.tz,
        "expected_obs_per_day": EXPECTED_OBS_PER_DAY,
        "min_obs_to_keep": args.min_obs,
        "utc_range": [str(merged.index.min()), str(merged.index.max())],
        "local_day_range": [str(daily.index.min().date()), str(daily.index.max().date())],
        "n_days_total": int(len(daily)),
        "n_days_complete": int(daily["complete"].sum()),
        "n_days_partial": int((~daily["complete"]).sum()),
        "n_days_dropped": int(len(dropped)),
        "n_days_kept": int(len(kept)),
        "partial_days": {
            str(d.date()): int(n) for d, n in partial["n_obs"].items()
        },
        "variables": sorted(value_cols),
        "units": {
            "pm2p5": "ug/m3",
            "pm10": "ug/m3",
            "t2m": "K",
            "t2m_c": "degC",
            "d2m": "K",
            "d2m_c": "degC",
            "rh": "%",
            "u10": "m/s",
            "v10": "m/s",
            "ws10": "m/s",
            "sp": "Pa",
        },
        "missing_by_variable": {
            c: int(kept[c].isna().sum()) for c in value_cols
        },
        "summary": {
            c: {
                "mean": float(kept[c].mean()),
                "std": float(kept[c].std()),
                "min": float(kept[c].min()),
                "max": float(kept[c].max()),
            }
            for c in value_cols
        },
    }

    # --- falha alta em vez de descarte silencioso --------------------------
    expected_days = pd.date_range(
        kept.index.min(), kept.index.max(), freq="D"
    )
    gaps = sorted(set(expected_days) - set(kept.index))
    report["n_internal_gaps"] = len(gaps)
    report["internal_gaps"] = [str(g.date()) for g in gaps[:50]]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_report.parent.mkdir(parents=True, exist_ok=True)

    final = kept.drop(columns=["complete"])
    codigo = 0
    if args.comparar is not None:
        report["comparacao"] = comparar_com_canonico(final, args.comparar)
        codigo = 0 if report["comparacao"]["identico"] else 2

    final.to_csv(out_csv)
    with open(out_report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n--- Relatório de completude ---")
    print(f"  janela UTC        : {report['utc_range'][0]} -> {report['utc_range'][1]}")
    print(f"  dias locais       : {report['local_day_range'][0]} -> {report['local_day_range'][1]}")
    print(f"  total             : {report['n_days_total']}")
    print(f"  completos (8 obs) : {report['n_days_complete']}")
    print(f"  parciais          : {report['n_days_partial']}  {report['partial_days']}")
    print(f"  descartados       : {report['n_days_dropped']}")
    print(f"  mantidos          : {report['n_days_kept']}")
    print(f"  lacunas internas  : {report['n_internal_gaps']}")
    print(f"\n  variáveis: {report['variables']}")
    if "comparacao" in report:
        c = report["comparacao"]
        print(f"\n--- Comparação com {c['referencia']} ---")
        print(f"  dias comuns {c['dias_comuns']} · só no novo {c['dias_so_no_novo']} · só no canônico {c['dias_so_no_canonico']}")
        for col, d in c["por_coluna"].items():
            print(f"  {col:8s} max|Δ| = {d['max_abs_diff']:.3e}  (rel {d['max_rel_diff']:.3e})  dias≠ {d['dias_diferentes']}")
        print(f"  idêntico (tolerância relativa {c['tolerancia_relativa']}): {c['identico']}")
    print(f"\nCSV     -> {out_csv}")
    print(f"Relatório -> {out_report}")
    raise SystemExit(codigo)


def comparar_com_canonico(novo: pd.DataFrame, canonico: Path, tol_rel: float = 1e-6) -> dict:
    """Compara coluna a coluna, dia a dia, o CSV reagregado com o canônico.

    Tolerância relativa de 1e-6 absorve diferença de arredondamento de gravação; qualquer
    coisa acima disso é DIVERGÊNCIA e deve ser explicada (versão do ADS, grade, período).
    """
    ref = pd.read_csv(canonico, parse_dates=["data"]).set_index("data")
    comuns = novo.index.intersection(ref.index)
    out = {
        "referencia": str(canonico),
        "tolerancia_relativa": tol_rel,
        "dias_comuns": int(len(comuns)),
        "dias_so_no_novo": [str(d.date()) for d in novo.index.difference(ref.index)[:20]],
        "dias_so_no_canonico": [str(d.date()) for d in ref.index.difference(novo.index)[:20]],
        "colunas_so_no_novo": sorted(set(novo.columns) - set(ref.columns)),
        "colunas_so_no_canonico": sorted(set(ref.columns) - set(novo.columns)),
        "por_coluna": {},
    }
    identico = not out["dias_so_no_novo"] and not out["dias_so_no_canonico"] and not out["colunas_so_no_canonico"]
    for col in sorted(set(novo.columns) & set(ref.columns)):
        a = pd.to_numeric(novo.loc[comuns, col], errors="coerce")
        b = pd.to_numeric(ref.loc[comuns, col], errors="coerce")
        diff = (a - b).abs()
        escala = b.abs().clip(lower=1e-12)
        rel = (diff / escala)
        dias_dif = int((rel > tol_rel).sum())
        out["por_coluna"][col] = {
            "max_abs_diff": float(diff.max()) if len(diff) else 0.0,
            "max_rel_diff": float(rel.max()) if len(rel) else 0.0,
            "dias_diferentes": dias_dif,
            "exemplos": {str(d.date()): [float(a[d]), float(b[d])] for d in rel[rel > tol_rel].index[:5]},
        }
        identico = identico and dias_dif == 0
    out["identico"] = bool(identico)
    return out


if __name__ == "__main__":
    import sys
    for fluxo in (sys.stdout, sys.stderr):  # console Windows e cp1252; ver cams_download_chunked
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    main()
