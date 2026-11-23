"""Reconstrói o ALVO da dissertação a partir dos microdados do SIH/SUS — script canônico.

    python -m src.ingestion.sih_build_lookahead --destino D:/Project/dados_rebaixa_2026-10
    python -m src.ingestion.sih_build_lookahead --destino <dir> --so-processar      # sem baixar
    python -m src.ingestion.sih_build_lookahead --destino <dir> --sem-referencia    # sem comparar

POR QUE ESTE MÓDULO EXISTE
--------------------------
`data/processed/sih_daily_lookahead.parquet` (+ `.meta.json`) é o alvo de todas as runs, mas o
script que o gerou em 2026-07-26 não estava em `src/` (PROTOCOLO §0.12, ROADMAP A3.11). O
pipeline versionado (`sih_datasus_pipeline.py`) conta LINHAS, não AIH distintas, e não tem
look-ahead de competências — não reproduz o alvo. Este módulo é a reconstrução, com as
regras declaradas no `.meta.json` canônico:

  * fonte: AIH-RD (grupo RD), UF SP, competências 2019-01 a 2025-06 (período epidemiológico
    2019-01-01 a 2024-12-31 + 6 competências de look-ahead, porque a AIH de uma internação
    pode ser apresentada meses depois);
  * filtro: `MUNIC_RES` começa com 355030 (residência em São Paulo) e `DIAG_PRINC` começa com
    "J" (CID-10 J00–J99); data = `DT_INTER`;
  * contagem: **`N_AIH` distintas por dia de internação**. A mesma AIH que aparece em duas
    competências é UMA internação; a primeira ocorrência (ordem de competência) vence;
  * nada é imputado; dias sem AIH ficam com zero e são contados (`dias_com_zero`).

O QUE ELE FAZ
-------------
1. Baixa os 78 arquivos `RDSPaamm.dbc` do FTP público do DATASUS para
   `<destino>/raw/datasus/sih-rd/<AAAAMM>/sih-rd_<AAAAMM>-sp_<data-do-arquivo-no-FTP>.dbc`
   (mesma convenção de nome do `datasus-fetcher`, que gerou a captura original mas não lista
   competências de 2025 — falha silenciosa documentada no meta). Pula o que já está no disco
   com o mesmo tamanho.
2. Descomprime DBC → DBF (`datasus_dbc`; fallback `dbctodbf`), lê com `dbfread`, agrega, e
   apaga o DBF (150 MB cada) salvo `--manter-dbf`.
3. Escreve `<destino>/processed/sih_daily_lookahead.parquet` (índice `data`; colunas
   `internacoes` = AIH distintas, `linhas_brutas` = linhas antes da deduplicação) e o
   `.meta.json` no mesmo esquema do canônico.
4. Compara com a referência (`--referencia`, padrão: o canônico em `data/processed/`): totais
   anuais, AIH distintas, série dia a dia. **Sai com código 2 se divergir** — o arquivo novo é
   escrito mesmo assim, para inspeção, mas nunca sobrescreve o canônico.

NUNCA escreve dentro de `data/` do repositório: o destino é obrigatório e deve ficar fora dele.
Falha alto em arquivo ausente, DBF sem as colunas, data inválida ou download incompleto.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import ftplib
import hashlib
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SIHSUS/200801_/Dados"
COLUNAS_OBRIGATORIAS = ("N_AIH", "DT_INTER", "DIAG_PRINC", "MUNIC_RES", "IDENT")
REFERENCIA_PADRAO = RAIZ / "data" / "processed" / "sih_daily_lookahead.parquet"
#: Tabela de Caráter de Atendimento (Portaria SAS/MS 719/2007, art. 4º): 01 eletivo, 02 urgência,
#: 03 acidente no local de trabalho, 04 acidente no trajeto, 05 outros acidentes de trânsito,
#: 06 outras lesões e envenenamentos.
CARATER_TABELA = ("01", "02", "03", "04", "05", "06")
#: alvo de urgência (PROTOCOLO §0.23): caráter não eletivo = urgência + categorias de acidente/lesão
CARATER_NAO_ELETIVO = ("02", "03", "04", "05", "06")


# ------------------------------------------------------------------ competências
def competencias_do_periodo(inicio: str, fim: str, look_ahead: int) -> list[str]:
    """`AAAAMM` do mês de `inicio` ao mês de `fim` mais `look_ahead` meses."""
    a = pd.Timestamp(inicio).to_period("M")
    b = pd.Timestamp(fim).to_period("M") + int(look_ahead)
    if b < a:
        raise ValueError("fim anterior ao início")
    return [str(p).replace("-", "") for p in pd.period_range(a, b, freq="M")]


def nome_ftp(competencia: str, uf: str) -> str:
    return f"RD{uf.upper()}{competencia[2:]}.dbc"


# ------------------------------------------------------------------------- FTP
def _conectar() -> ftplib.FTP:
    ftp = ftplib.FTP(FTP_HOST, timeout=120)
    ftp.login()
    ftp.cwd(FTP_DIR)
    return ftp


def baixar_competencias(competencias: list[str], uf: str, raw: Path, tentativas: int = 3) -> dict[str, Path]:
    """Baixa cada `RDUFaamm.dbc`; devolve {competencia: caminho_local}. Falha alto se faltar algum."""
    locais: dict[str, Path] = {}
    ftp = _conectar()
    try:
        for comp in competencias:
            remoto = nome_ftp(comp, uf)
            try:
                mdtm = ftp.sendcmd(f"MDTM {remoto}").split()[-1][:8]  # AAAAMMDD
                tamanho = ftp.size(remoto)
            except ftplib.error_perm as e:
                raise RuntimeError(f"{remoto} não existe no FTP do DATASUS ({e}). "
                                   f"Competência {comp} ainda não publicada?") from e
            pasta = raw / "sih-rd" / comp
            pasta.mkdir(parents=True, exist_ok=True)
            destino = pasta / f"sih-rd_{comp}-{uf.lower()}_{mdtm}.dbc"
            if destino.exists() and destino.stat().st_size == tamanho:
                print(f"  [{comp}] já no disco ({tamanho/1e6:.1f} MB) — pulando", flush=True)
                locais[comp] = destino
                continue
            for antigo in pasta.glob(f"sih-rd_{comp}-{uf.lower()}_*.dbc"):
                if antigo != destino:
                    print(f"  [{comp}] versão antiga no disco ({antigo.name}); o FTP publica {destino.name}", flush=True)
            for k in range(1, tentativas + 1):
                tmp = destino.with_suffix(".part")
                t0 = time.time()
                try:
                    with open(tmp, "wb") as fh:
                        ftp.retrbinary(f"RETR {remoto}", fh.write, blocksize=1 << 16)
                    if tmp.stat().st_size != tamanho:
                        raise IOError(f"tamanho {tmp.stat().st_size} != {tamanho} anunciado")
                    tmp.replace(destino)
                    print(f"  [{comp}] {remoto} -> {destino.name} ({tamanho/1e6:.1f} MB, {time.time()-t0:.0f}s)", flush=True)
                    break
                except (ftplib.all_errors, IOError) as e:  # noqa: PERF203
                    tmp.unlink(missing_ok=True)
                    print(f"  [{comp}] tentativa {k}/{tentativas} falhou: {e}", flush=True)
                    if k == tentativas:
                        raise RuntimeError(f"download de {remoto} falhou após {tentativas} tentativas") from e
                    time.sleep(5 * k)
                    try:
                        ftp.quit()
                    except Exception:  # noqa: BLE001
                        pass
                    ftp = _conectar()
            locais[comp] = destino
    finally:
        try:
            ftp.quit()
        except Exception:  # noqa: BLE001
            pass
    return locais


def localizar_competencias(competencias: list[str], uf: str, raw: Path) -> dict[str, Path]:
    locais = {}
    for comp in competencias:
        achados = sorted((raw / "sih-rd" / comp).glob(f"sih-rd_{comp}-{uf.lower()}_*.dbc"))
        if not achados:
            raise FileNotFoundError(f"competência {comp}: nenhum DBC em {raw / 'sih-rd' / comp} (rode sem --so-processar)")
        locais[comp] = achados[-1]
    return locais


# ------------------------------------------------------------------ DBC → DBF
def descomprimir(dbc: Path, dbf: Path) -> None:
    if dbf.exists() and dbf.stat().st_size > 0:
        return
    try:
        from datasus_dbc import decompress  # type: ignore
        decompress(str(dbc), str(dbf))
    except ImportError:
        from dbctodbf import DBCDecompress  # type: ignore
        DBCDecompress().decompressFile(str(dbc), str(dbf))
    if not dbf.exists() or dbf.stat().st_size == 0:
        raise RuntimeError(f"descompressão de {dbc.name} não produziu DBF")


# ------------------------------------------------------------------- leitura
def iterar_registros(dbf: Path, extras: tuple[str, ...] = ()):
    """Gera dicts com as colunas obrigatórias (+ `extras`). Falha alto se faltar coluna."""
    from dbfread import DBF
    tabela = DBF(str(dbf), encoding="latin1", ignore_missing_memofile=True, load=False)
    faltam = [c for c in COLUNAS_OBRIGATORIAS + tuple(extras) if c not in tabela.field_names]
    if faltam:
        raise RuntimeError(f"{dbf.name}: colunas ausentes {faltam}. Presentes: {tabela.field_names[:40]}…")
    for rec in tabela:
        yield rec


def agregar_registros(registros, municipio: str, inicio: pd.Timestamp, fim: pd.Timestamp,
                      vistos: dict[str, pd.Timestamp], acumulado: dict,
                      carater: tuple[str, ...] | None = None) -> dict:
    """Aplica filtro, deduplica por N_AIH e acumula contagens. Puro: testável sem DBF.

    `vistos` é o dicionário global N_AIH -> data (persiste entre competências).
    `acumulado` tem `linhas` (Counter por dia), `distintas` (Counter por dia), `ident` (Counter),
    `fora_periodo`, `dt_invalidas`.

    `carater` (opcional; alvo de urgência, PROTOCOLO §0.23): códigos de `CAR_INT` aceitos — para
    `--carater nao_eletivo`, `CARATER_NAO_ELETIVO` = 02..06. A deduplicação continua valendo sobre
    TODAS as AIH J/município: a primeira ocorrência do N_AIH decide a data e o caráter, e a AIH só é
    contada se esse caráter estiver em `carater`. Com o filtro ativo, `CAR_INT` vazio ou fora da
    tabela oficial 01–06 (Portaria SAS 719/2007) falha alto — nada é imputado. As primeiras ocorrências
    são contadas por código em `acumulado["car_int"]`. Sem `carater`, o comportamento é idêntico ao do
    alvo canônico.
    """
    stats = {"registros_lidos": 0, "J_e_municipio": 0, "aih_novas": 0, "aih_repetidas": 0}
    if carater is not None:
        stats["aih_excluidas_carater"] = 0
        acumulado.setdefault("car_int", Counter())
    for rec in registros:
        stats["registros_lidos"] += 1
        cid = str(rec.get("DIAG_PRINC") or "").strip().upper()
        if not cid.startswith("J"):
            continue
        if not str(rec.get("MUNIC_RES") or "").strip().startswith(municipio):
            continue
        stats["J_e_municipio"] += 1
        bruto = str(rec.get("DT_INTER") or "").strip()
        if len(bruto) != 8 or not bruto.isdigit():
            acumulado["dt_invalidas"] += 1
            continue
        try:
            data = pd.Timestamp(int(bruto[:4]), int(bruto[4:6]), int(bruto[6:]))
        except ValueError:
            acumulado["dt_invalidas"] += 1
            continue
        if data < inicio or data > fim:
            acumulado["fora_periodo"] += 1
            continue
        passa = True
        if carater is not None:
            car = str(rec.get("CAR_INT") or "").strip()
            if car not in CARATER_TABELA:
                raise RuntimeError(f"registro J/município com CAR_INT {car!r} fora da tabela 01–06 "
                                   "(filtro de caráter ativo)")
            passa = car in carater
        if passa:
            acumulado["linhas"][data] += 1
            acumulado["ident"][str(rec.get("IDENT") or "").strip()] += 1
        aih = str(rec.get("N_AIH") or "").strip()
        if not aih:
            raise RuntimeError("registro J/município sem N_AIH — regra de contagem inaplicável")
        if aih in vistos:
            stats["aih_repetidas"] += 1
            continue
        vistos[aih] = data
        if carater is not None:
            acumulado["car_int"][car] += 1
        if not passa:
            stats["aih_excluidas_carater"] += 1
            continue
        acumulado["distintas"][data] += 1
        stats["aih_novas"] += 1
    return stats


def serie_diaria(acumulado: dict, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    idx = pd.date_range(inicio, fim, freq="D", name="data")
    df = pd.DataFrame({
        "internacoes": pd.Series(acumulado["distintas"]).reindex(idx, fill_value=0).astype("int64"),
        "linhas_brutas": pd.Series(acumulado["linhas"]).reindex(idx, fill_value=0).astype("int64"),
    }, index=idx)
    return df


# ---------------------------------------------------------------- comparação
def comparar(novo: pd.DataFrame, referencia: Path) -> dict:
    ref = pd.read_parquet(referencia)
    if "internacoes" not in ref.columns:
        raise RuntimeError(f"{referencia}: sem coluna 'internacoes'")
    ref.index = pd.to_datetime(ref.index)
    comum = novo.index.intersection(ref.index)
    a = novo.loc[comum, "internacoes"]
    b = ref.loc[comum, "internacoes"]
    dif = (a - b)
    dias_dif = dif[dif != 0]
    out = {
        "referencia": str(referencia),
        "dias_comparados": int(len(comum)),
        "dias_so_no_novo": int(len(novo.index.difference(ref.index))),
        "dias_so_na_referencia": int(len(ref.index.difference(novo.index))),
        "total_novo": int(novo["internacoes"].sum()),
        "total_referencia": int(ref["internacoes"].sum()),
        "dias_divergentes": int(len(dias_dif)),
        "maior_divergencia_absoluta": int(dias_dif.abs().max()) if len(dias_dif) else 0,
        "exemplos_divergencia": {str(d.date()): int(v) for d, v in dias_dif.head(10).items()},
        "totais_anuais_novo": {str(k): int(v) for k, v in novo["internacoes"].groupby(novo.index.year).sum().items()},
        "totais_anuais_referencia": {str(k): int(v) for k, v in ref["internacoes"].groupby(ref.index.year).sum().items()},
    }
    out["identico"] = (out["dias_divergentes"] == 0 and out["dias_so_no_novo"] == 0
                       and out["dias_so_na_referencia"] == 0 and out["total_novo"] == out["total_referencia"])
    return out


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# --------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--destino", required=True, type=Path,
                    help="diretório FORA do repositório; recebe raw/ e processed/")
    ap.add_argument("--inicio", default="2019-01-01")
    ap.add_argument("--fim", default="2024-12-31")
    ap.add_argument("--look-ahead", type=int, default=6, help="competências após o fim (meta canônico: 6)")
    ap.add_argument("--uf", default="sp")
    ap.add_argument("--municipio", default="355030", help="prefixo de MUNIC_RES (6 dígitos IBGE)")
    ap.add_argument("--so-processar", action="store_true", help="não baixa; usa os DBC já em <destino>/raw")
    ap.add_argument("--manter-dbf", action="store_true", help="não apaga o DBF após processar (~150 MB cada)")
    ap.add_argument("--referencia", type=Path, default=REFERENCIA_PADRAO,
                    help="parquet canônico para comparar (padrão: data/processed/sih_daily_lookahead.parquet)")
    ap.add_argument("--sem-referencia", action="store_true", help="não compara com o canônico")
    ap.add_argument("--carater", choices=("todos", "nao_eletivo"), default="todos",
                    help="'todos' = alvo canônico (padrão); 'nao_eletivo' = alvo de urgência, CAR_INT 02–06 (PROTOCOLO §0.23)")
    ap.add_argument("--nome-saida", default="sih_daily_lookahead.parquet",
                    help="nome do parquet em <destino>/processed (padrão: o do alvo canônico)")
    args = ap.parse_args(argv)
    carater = CARATER_NAO_ELETIVO if args.carater == "nao_eletivo" else None

    destino = args.destino.resolve()
    try:
        destino.relative_to(RAIZ / "data")
        raise SystemExit("--destino não pode ficar dentro de data/ do repositório: use outro diretório")
    except ValueError:
        pass
    raw = destino / "raw" / "datasus"
    processed = destino / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    inicio, fim = pd.Timestamp(args.inicio), pd.Timestamp(args.fim)
    competencias = competencias_do_periodo(args.inicio, args.fim, args.look_ahead)
    print(f"destino: {destino}\ncompetências: {competencias[0]}..{competencias[-1]} ({len(competencias)})", flush=True)

    t_ini = time.time()
    if args.so_processar:
        locais = localizar_competencias(competencias, args.uf, raw)
    else:
        print("== download (FTP público do DATASUS)", flush=True)
        locais = baixar_competencias(competencias, args.uf, raw)

    print("== processamento", flush=True)
    vistos: dict[str, pd.Timestamp] = {}
    acumulado = {"linhas": Counter(), "distintas": Counter(), "ident": Counter(), "fora_periodo": 0, "dt_invalidas": 0}
    por_competencia: dict[str, dict] = {}
    for comp in competencias:
        dbc = locais[comp]
        dbf = dbc.with_suffix(".dbf")
        t0 = time.time()
        descomprimir(dbc, dbf)
        stats = agregar_registros(iterar_registros(dbf, ("CAR_INT",) if carater else ()), args.municipio,
                                  inicio, fim, vistos, acumulado, carater)
        stats["arquivo"] = dbf.name
        stats["dbc_sha256"] = _sha256(dbc)
        stats["segundos"] = round(time.time() - t0, 1)
        por_competencia[comp] = stats
        if not args.manter_dbf:
            dbf.unlink()
        print(f"  [{comp}] lidos {stats['registros_lidos']:>7}  J&mun {stats['J_e_municipio']:>5}  "
              f"novas {stats['aih_novas']:>5}  repetidas {stats['aih_repetidas']:>3}  {stats['segundos']:.1f}s", flush=True)

    df = serie_diaria(acumulado, inicio, fim)
    saida = processed / args.nome_saida
    df.to_parquet(saida)
    linhas = int(df["linhas_brutas"].sum())
    distintas = int(df["internacoes"].sum())
    meta = {
        "fonte": "SIH/SUS - DATASUS, AIH-RD (microdados)",
        "obtido_por": f"src/ingestion/sih_build_lookahead.py — FTP público {FTP_HOST}{FTP_DIR}"
                      + (" (arquivos já em disco; --so-processar)" if args.so_processar else ""),
        "dataset": "sih-rd", "grupo": "RD", "uf": args.uf.upper(),
        "municipio_ibge": args.municipio + ("8" if args.municipio == "355030" else ""),
        "criterio_espacial": f"MUNIC_RES (residencia) startswith {args.municipio}",
        "campo_data": "DT_INTER", "campo_cid": "DIAG_PRINC",
        "regra_cid": "str(DIAG_PRINC).strip().upper().startswith('J')",
        "regra_contagem": "N_AIH distintas por dia de internacao (primeira ocorrencia na ordem das competencias)",
        **({"filtro_carater_internacao": {
            "modo": args.carater, "campo": "CAR_INT", "codigos_aceitos": list(carater),
            "tabela_oficial": "Portaria SAS/MS 719/2007, art. 4: 01 eletivo, 02 urgencia, 03-06 acidentes/lesoes",
            "regra": "a primeira ocorrencia do N_AIH (entre todas as AIH J/municipio) decide data e carater; "
                     "conta so se CAR_INT estiver nos codigos aceitos; vazio ou fora de 01-06 falha alto",
            "aih_por_car_int_primeira_ocorrencia": dict(sorted(acumulado["car_int"].items())),
            "aih_excluidas_carater": sum(s.get("aih_excluidas_carater", 0) for s in por_competencia.values()),
            "protocolo": "PROTOCOLO §0.23 (alvo de urgencia para a pergunta do PM2,5, [PROPOSTO])"}} if carater else {}),
        "periodo_epidemiologico": [args.inicio, args.fim],
        "periodo_administrativo": [competencias[0], competencias[-1]],
        "look_ahead_competencias": args.look_ahead,
        "extraido_em": _dt.datetime.now().isoformat(timespec="seconds"),
        "total_linhas_somadas": linhas,
        "total_aih_distintas": distintas,
        "duplicatas_entre_competencias": linhas - distintas,
        "dt_inter_invalidas": acumulado["dt_invalidas"],
        "registros_fora_do_periodo": acumulado["fora_periodo"],
        "dias": int(len(df)),
        "dias_com_zero": int((df["internacoes"] == 0).sum()),
        "ident_distribuicao": dict(sorted(acumulado["ident"].items())),
        "totais_anuais": {str(k): int(v) for k, v in df["internacoes"].groupby(df.index.year).sum().items()},
        "parquet_sha256": _sha256(saida),
        "segundos_total": round(time.time() - t_ini, 1),
        "competencias": por_competencia,
    }
    codigo = 0
    if not args.sem_referencia:
        if not args.referencia.exists():
            raise FileNotFoundError(f"referência {args.referencia} não existe; use --sem-referencia")
        meta["comparacao_com_referencia"] = comparar(df, args.referencia)
        c = meta["comparacao_com_referencia"]
        print("== comparação com a referência")
        print(f"  dias comparados {c['dias_comparados']}  divergentes {c['dias_divergentes']}  "
              f"total novo {c['total_novo']}  total ref {c['total_referencia']}  idêntico: {c['identico']}")
        if not c["identico"]:
            print(f"  exemplos (novo − ref): {c['exemplos_divergencia']}")
            codigo = 2
    saida.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"== escrito: {saida}\n   AIH distintas {distintas} · linhas {linhas} · dias {len(df)} · "
          f"zeros {meta['dias_com_zero']} · {meta['segundos_total']:.0f}s", flush=True)
    return codigo


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
