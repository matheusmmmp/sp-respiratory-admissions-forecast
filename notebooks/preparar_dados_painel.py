"""Gera o pacote de dados AGREGADOS do painel (caráter da internação e sábado; PROTOCOLO §0.23).

Entrada: microdados do alvo (aih_alvo_enriquecido.parquet, fora do repositório) e predictions.csv das runs CETESB rica.
Saída: dados_painel/*.csv + manifest.json e dados_painel.zip. Nada em nível de registro: só contagens por dia,
grupo, estabelecimento × ano e perfis resumidos; células de estabelecimento × ano com menos de 5 internações são
suprimidas. Rodar com o Python oficial do projeto (env\\.venv311).
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
AQUI = Path(__file__).resolve().parent
MICRO = Path(r"D:\Project\dados_extensao_2026-11\analise_dow\aih_alvo_enriquecido.parquet")
REPO = Path(r"D:\Project\dataspell_workspace_template")
ALVO = REPO / "data" / "processed" / "sih_daily_lookahead_2019_2026.parquet"
EXP = REPO / "reports" / "experiments"
RUNS = {1: "h1_v02_cetesb_cetesb_classicos_full_20261022-211834",
        5: "mh_h5_cetesb_cetesb_full_20261110-211453",
        7: "mh_h7_cetesb_cetesb_full_20261111-030322",
        15: "mh_h15_cetesb_cetesb_full_20261111-070926",
        30: "mh_h30_cetesb_cetesb_full_20261113-104814"}
CEMA = "2091550"
GRUPOS = [("J00–J06 infecções agudas das vias aéreas sup.", 0, 6, True), ("J09–J11 influenza", 9, 11, True),
          ("J12–J18 pneumonias", 12, 18, True), ("J20–J22 bronquite e bronquiolite agudas", 20, 22, True),
          ("J30–J39 outras doenças das vias aéreas sup.", 30, 39, False),
          ("J40–J47 crônicas das vias aéreas inf. (DPOC, asma)", 40, 47, True),
          ("J60–J70 doenças por agentes externos", 60, 70, False), ("J80–J84 intersticiais", 80, 84, False),
          ("J85–J86 supurativas", 85, 86, False), ("J90–J94 pleura", 90, 94, False),
          ("J95–J99 outras (pós-proced., insuf. resp.)", 95, 99, False)]
OUT = AQUI / "dados_painel"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    a = pd.read_parquet(MICRO)
    alvo = pd.read_parquet(ALVO).internacoes
    a["dt"] = pd.to_datetime(a.DT_INTER, format="%Y%m%d")
    idx = pd.date_range(a.dt.min(), a.dt.max())
    conf = a.groupby("dt").size().reindex(pd.to_datetime(alvo.index), fill_value=0)
    if len(a) != 368758 or int((conf.values != alvo.values).sum()):
        raise SystemExit("microdados não reproduzem o alvo — pare")
    a["n"] = a.DIAG_PRINC.str[1:3].astype(int)
    a["eletiva"] = a.CAR_INT == "01"
    a["grupo"] = ""
    a["sensivel"] = False
    for rot, i, f, s in GRUPOS:
        m = (a.n >= i) & (a.n <= f)
        a.loc[m, "grupo"] = rot
        a.loc[m, "sensivel"] = s
    a["idade"] = np.select([a.COD_IDADE == "4", a.COD_IDADE.isin(["2", "3"]), a.COD_IDADE == "5"],
                           [pd.to_numeric(a.IDADE, errors="coerce"), 0, 100 + pd.to_numeric(a.IDADE, errors="coerce")],
                           np.nan)
    a["perm"] = pd.to_numeric(a.DIAS_PERM, errors="coerce")
    cmpt = pd.to_datetime(a.ANO_CMPT + a.MES_CMPT + "01", format="%Y%m%d")
    a["atraso"] = ((cmpt.dt.year - a.dt.dt.year) * 12 + (cmpt.dt.month - a.dt.dt.month)).clip(upper=4)

    def dia(m):
        return a[m].groupby("dt").size().reindex(idx, fill_value=0)
    d = pd.DataFrame({"total": dia(slice(None)), "nao_eletivo": dia(~a.eletiva), "eletivo": dia(a.eletiva),
                      "cema": dia(a.CNES == CEMA), "sens_nao_eletivo": dia(a.sensivel & ~a.eletiva),
                      "sens_eletivo": dia(a.sensivel & a.eletiva)}, index=idx)
    d.index.name = "data"
    d.to_csv(OUT / "diario.csv")

    g = a.groupby(["grupo", "sensivel"]).agg(total=("N_AIH", "size"), eletivas=("eletiva", "sum")).reset_index()
    g["eletivas_cema"] = g.grupo.map(a[a.eletiva & (a.CNES == CEMA)].groupby("grupo").size()).fillna(0).astype(int)
    g.to_csv(OUT / "grupos_cid.csv", index=False)

    a["ano"] = a.dt.dt.year
    a["sabado"] = a.dt.dt.dayofweek == 5
    top = a[a.eletiva & a.sabado].CNES.value_counts().head(15).index
    e = (a[a.CNES.isin(top)].groupby(["CNES", "ano"])
         .agg(total=("N_AIH", "size"), eletivas=("eletiva", "sum"),
              eletivas_sabado=("sabado", lambda s: int((s & a.loc[s.index, "eletiva"]).sum()))).reset_index())
    for c in ["total", "eletivas", "eletivas_sabado"]:
        e[c] = e[c].astype(float).where(e[c] >= 5)  # supressão de células pequenas
    e["nome"] = np.where(e.CNES == CEMA, "Instituto CEMA (CNES 2091550)", "CNES " + e.CNES)
    e.to_csv(OUT / "estabelecimentos_ano.csv", index=False)

    def perfil(x):
        return pd.Series({"internacoes": len(x), "idade_mediana": x.idade.median(),
                          "pct_menor_15": 100 * (x.idade < 15).mean(), "permanencia_mediana": x.perm.median(),
                          "pct_permanencia_ate_1_dia": 100 * (x.perm <= 1).mean(),
                          "pct_obito": 100 * (x.MORTE == "1").mean()})
    p = pd.concat({"Eletiva": perfil(a[a.eletiva]), "Não eletiva": perfil(a[~a.eletiva]),
                   "Eletiva, sábado, CNES 2091550": perfil(a[a.eletiva & a.sabado & (a.CNES == CEMA)]),
                   "Eletiva nos grupos sensíveis": perfil(a[a.eletiva & a.sensivel])}, axis=1).T.round(1)
    p.index.name = "recorte"
    p.to_csv(OUT / "perfil.csv")

    t = a[a.ano >= 2022].groupby([a.dt.dt.dayofweek.rename("dow"), "atraso"]).size().unstack(fill_value=0)
    (100 * t.div(t.sum(1), axis=0)).round(2).to_csv(OUT / "atraso_registro_2022_mais.csv")

    lidos = {str(MICRO): sha(MICRO), str(ALVO): sha(ALVO)}
    linhas = []
    for h, rid in RUNS.items():
        f = EXP / rid / "predictions.csv"
        lidos[str(f)] = sha(f)
        pr = pd.read_csv(f, usecols=["model", "feature_set", "target_date", "y_true", "y_pred"])
        pr = pr[pr.feature_set.isin(["AR_CAL", "baseline"])]
        pr = pr.groupby(["model", "target_date"]).agg(y=("y_true", "first"), y_prev=("y_pred", "mean")).reset_index()
        pr["h"], pr["run"] = h, rid
        linhas.append(pr)
    pd.concat(linhas).to_csv(OUT / "erros_modelos_ar_cal.csv", index=False)

    man = {"gerado_em": datetime.now().isoformat(timespec="seconds"), "script": str(Path(__file__)),
           "entradas_sha256": lidos, "runs_por_horizonte": RUNS, "cnes_destacado": CEMA,
           "regras": ["só agregados; nenhum N_AIH", "estabelecimento × ano com < 5 internações suprimido",
                      "erros: conjunto AR_CAL, previsões médias das sementes por data",
                      "2025–2026: alvo sem conferência contra o TabNet (PROTOCOLO §0.22)"]}
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.make_archive(str(AQUI / "dados_painel"), "zip", OUT)
    for f in sorted(OUT.iterdir()):
        print(f.name, f.stat().st_size)


if __name__ == "__main__":
    main()
