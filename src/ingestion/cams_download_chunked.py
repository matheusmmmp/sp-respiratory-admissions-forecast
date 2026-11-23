#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cams_download_chunked.py (robusto p/ ADS/CAMS EAC4)
Baixa CAMS Global Reanalysis (EAC4) em janelas (chunks), agrega para DIÁRIO e exporta CSV único.

✅ Ajustes principais vs sua versão:
- Usa o fato de que o EAC4 é 3-hourly (00,03,06,09,12,15,18,21) — isso reduz custo e evita combinações inválidas.
- Variáveis com nomes mais prováveis no ADS para EAC4 (evita tco3/tcno2/tcso2/tcco e "r" que costumam dar 400).
- Fallback real: se der 400 em um payload, tenta o próximo (antes você “raise” e não chegava no req_B/req_C).
- Agregação diária respeitando timezone (--tz) antes de resample.
- Se o download passar mas a conversão falhar, imprime variáveis disponíveis no NetCDF para debug rápido.

Uso (PowerShell/PyCharm Terminal):
  python .\src\ingestion\cams_download_chunked.py `
    --ini 2019-01-01 `
    --fim 2024-12-31 `
    --saida .\data\processed\cams_expanded_daily.csv `
    --chunk-meses 1 `
    --area -23.3 -46.8 -23.9 -46.3 `
    --tz America/Sao_Paulo

Requisitos:
  pip install cdsapi xarray netCDF4 pandas numpy

Credenciais (resolvidas nesta ordem; a primeira que estiver completa vence):
  1) Variáveis de ambiente CDSAPI_URL e CDSAPI_KEY   <- recomendado, nada em disco
  2) ~/.cdsapirc  (fora do repositório)
  3) ./.cdsapirc  (raiz do projeto)  <- LEGADO, não use: o .gitignore cobre, mas
                                        já houve vazamento desta credencial por
                                        este caminho. Emite aviso se for usado.

  Formato do arquivo, para a pilha atual do ADS (url terminando em /api):
    url: https://ads.atmosphere.copernicus.eu/api
    key: SEU_PERSONAL_ACCESS_TOKEN

  A pilha antiga (/api/v2) usava `key: UID:APIKEY`. Se o seu token tem o prefixo
  UID:, ele é do formato antigo e não vale para /api.
"""

import argparse
import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
import xarray as xr

DATASET = "cams-global-reanalysis-eac4"

# EAC4 entrega 3-hourly (conforme docs/treinamentos CAMS) — isso também reduz custo.
TIMES_3H = ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]

# ⚠️ SONDADO CONTRA O ADS EM 27/07/2026 — não editar por suposição.
#
# `nitrogen_dioxide`, `sulphur_dioxide`, `ozone` e `carbon_monoxide` estavam
# nesta lista e **o EAC4 single-level os RECUSA**. Não é erro de digitação: no
# single-level esses gases só existem como COLUNA TOTAL (`tcno2`, `gtco3`,
# `tcco`, `tcso2`, todos em kg/m²), que é integral vertical e **não** é
# concentração de superfície. Incomparável com a medição da CETESB.
#
# Pior: pedidos numa lista com outras variáveis eram DESCARTADOS EM SILÊNCIO —
# o ADS devolvia só as variáveis válidas, sem erro. Foi por isso que os 84
# NetCDF em data/raw/ nunca tiveram gás nenhum, e por isso que o projeto
# concluiu que "o CAMS nunca entregou" os gases.
#
# Concentração de superfície de gás exigiria o produto de NÍVEIS DE MODELO
# (o EAC4 tem 60 níveis; o mais baixo fica a ~10 m do chão) e
# conversão por densidade do ar — outro dataset, outro pipeline. Como a CETESB
# já entrega os seis poluentes medidos na superfície, com 2192 dias e 7 a 13
# estações, não compensa. Ver src/ingestion/cams_sonda_gases.py.
#
# ⚠️ 2026-10-19 — `relative_humidity` NÃO existe no EAC4 single-level e era
# descartada em silêncio (o NetCDF voltava com 6 das 7 variáveis pedidas). O
# `cams_daily_v2.csv` canônico obteve a umidade derivando-a do PONTO DE ORVALHO
# (`d2m`, fórmula de Magnus em `cams_rebuild_daily.py`), que só estava no
# download de 2025-08. Por isso a lista pede `2m_dewpoint_temperature`, e
# `exigir_variaveis()` falha alto se qualquer variável obrigatória faltar
# (PROTOCOLO §3.2: "todo download deve falhar alto quando a lista de variáveis
# retornada divergir da requisitada").
VARS_CORE = [
    "particulate_matter_2.5um",
    "particulate_matter_10um",
    "2m_temperature",
    "2m_dewpoint_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "surface_pressure",
]

#: nome longo (pedido ao ADS) -> nome curto (no NetCDF) das variáveis obrigatórias
CORE_CURTO = {
    "particulate_matter_2.5um": "pm2p5",
    "particulate_matter_10um": "pm10",
    "2m_temperature": "t2m",
    "2m_dewpoint_temperature": "d2m",
    "10m_u_component_of_wind": "u10",
    "10m_v_component_of_wind": "v10",
    "surface_pressure": "sp",
}


def exigir_variaveis(nc_path: str, pedidas: list) -> None:
    """Falha alto se o NetCDF não trouxer TODAS as variáveis obrigatórias pedidas."""
    with xr.open_dataset(nc_path) as ds:
        presentes = set(ds.data_vars)
    obrigatorias = {CORE_CURTO[v] for v in pedidas if v in CORE_CURTO}
    faltam = sorted(obrigatorias - presentes)
    if faltam:
        raise RuntimeError(
            f"{os.path.basename(nc_path)}: o ADS devolveu {sorted(presentes)}; faltam as variáveis "
            f"obrigatórias {faltam}. O download NÃO pode seguir em silêncio (PROTOCOLO §3.2)."
        )
    opcionais_ausentes = sorted({v for v in pedidas if v not in CORE_CURTO} - presentes)
    if opcionais_ausentes:
        print(f"   [aviso] variáveis opcionais não entregues: {opcionais_ausentes}")

# Coluna total dos gases. Disponíveis e baixáveis, mas NÃO são superfície.
# Ficam registradas para quem quiser usá-las com plena ciência do que são.
VARS_COLUNA_TOTAL = [
    "total_column_nitrogen_dioxide",   # tcno2, kg/m2
    "total_column_sulphur_dioxide",    # tcso2, kg/m2
    "total_column_ozone",              # gtco3, kg/m2
    "total_column_carbon_monoxide",    # tcco,  kg/m2
]

# ⚠️ CAIXA GEOGRÁFICA — o padrão antigo QUEBROU e ninguém percebeu.
#
# A caixa usada até aqui, `-23.3 -46.8 -23.9 -46.3`, hoje faz o ADS responder
# HTTP 400 "request area contains no grid points". O EAC4 tem grade de 0,75°,
# com pontos em latitude -23.25 e -24.0 e longitude -47.25 e -46.5 — nenhum
# deles cai dentro daquela caixa. Ela funcionou quando os arquivos atuais foram
# baixados porque o ADS fazia snap para o ponto mais próximo; não faz mais.
#
# Esta caixa contém exatamente o ponto (-23.25, -46.5), o nó da grade de 0,75°
# mais próximo do centro do município (~36 km a NE da Sé).
#
# ⚠️ CORRIGIDO EM 2026-10-19 — a afirmação anterior de que este era "o mesmo
# ponto único que está nos NetCDF históricos" é FALSA. Lendo as coordenadas de
# todos os 156 arquivos em data/raw/:
#   - cams_expanded_daily - 26-08-2025 (12 arquivos, fonte de pm2p5/pm10/t2m/d2m/u10/v10
#     do cams_daily_v2.csv canônico): lat -23.7, lon -46.8  (~24 km a SO da Sé)
#   - cams_expanded_daily_2026-01-22/-23 (72 arquivos cada, fonte de sp do canônico):
#     lat -23.9, lon -46.8  (~42 km a S/SO, Serra do Mar)
#   - download de 2026-10-19 com esta caixa: lat -23.25, lon -46.5
# Nenhum dos pontos históricos é nó da grade: o ADS antigo interpolava para a
# borda da caixa pedida. Consequência: o canônico NÃO é reproduzível com o ADS
# atual, e um download novo dá uma série 35% mais alta em PM2.5 (r diário 0,95),
# pressão 5 kPa menor (altitude coerente com a cidade) e vento 12% menor.
# Ver docs/REBAIXA_DADOS_2026-10-19.md §2.3 e PROTOCOLO §0.17.
AREA_SP_GRADE = (-23.2, -46.6, -23.3, -46.4)   # N, W, S, E

# Se existir, usamos; se não existir, o fallback tenta sem ela.
VARS_OPTIONAL = [
    "total_precipitation",
]

# ---------------- util ----------------

def ensure_dir(path: str):
    if path:
        os.makedirs(path, exist_ok=True)

def _read_rc(rc_path: str):
    url = key = None
    if os.path.isfile(rc_path):
        with open(rc_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s.startswith("url:"):
                    url = s.split("url:", 1)[1].strip()
                elif s.startswith("key:"):
                    key = s.split("key:", 1)[1].strip()
    return url, key

def load_cds_credentials():
    """
    Resolve credenciais do ADS na ordem: env vars -> ~/.cdsapirc -> ./.cdsapirc.
    Devolve (url, key, origem). Não imprime nem retorna o valor da chave em log.
    """
    url, key = os.environ.get("CDSAPI_URL"), os.environ.get("CDSAPI_KEY")
    if url and key:
        return url, key, "variáveis de ambiente CDSAPI_URL/CDSAPI_KEY"

    home_rc = os.path.join(os.path.expanduser("~"), ".cdsapirc")
    url, key = _read_rc(home_rc)
    if url and key:
        return url, key, home_rc

    project_rc = os.path.join(os.getcwd(), ".cdsapirc")
    url, key = _read_rc(project_rc)
    if url and key:
        print("⚠️  Credencial lida de DENTRO do projeto. Mova para ~/.cdsapirc ou")
        print("   para as variáveis CDSAPI_URL/CDSAPI_KEY — este caminho já vazou uma vez.")
        return url, key, project_rc

    raise SystemExit(
        "❌ Nenhuma credencial do ADS encontrada. Configure UMA destas opções:\n"
        "   1) CDSAPI_URL e CDSAPI_KEY no ambiente (recomendado); no conda:\n"
        "      conda env config vars set -n eda-lstm-pm25 "
        "CDSAPI_URL=https://ads.atmosphere.copernicus.eu/api CDSAPI_KEY=<token>\n"
        f"   2) criar {home_rc} com as linhas 'url:' e 'key:'\n"
        "   Formato da chave para /api: apenas o Personal Access Token, sem prefixo UID:."
    )

def normalize_urls(url: str):
    u = url.rstrip("/")
    # user pode ter url com /api ou /api/v2
    if u.endswith("/api/v2"):
        return [u, u[:-3]]     # /api/v2, /api
    if u.endswith("/api"):
        return [u, u + "/v2"]  # /api, /api/v2
    return [u + "/api", u + "/api/v2"]

def new_client(url: str, key: str):
    os.environ["CDSAPI_URL"] = url
    os.environ["CDSAPI_KEY"] = key
    import cdsapi
    return cdsapi.Client(quiet=True)

def chunk_ranges(start_date: str, end_date: str, months: int = 1):
    """
    Gera chunks por meses, com fim INCLUSIVO (último dia do chunk).
    Ex.: 2019-01-01..2019-01-31, 2019-02-01..2019-02-28, ...
    """
    start = pd.to_datetime(start_date).normalize()
    end = pd.to_datetime(end_date).normalize()
    cur = start

    while cur <= end:
        nxt = (cur + pd.DateOffset(months=months)).normalize()
        chunk_end = min(end, nxt - pd.Timedelta(days=1))
        yield cur.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
        cur = nxt

def candidate_requests(ini: str, fim: str, area_list, variables: list):
    """
    Gera variações de request (ADS/CADS muda chave de formato dependendo do backend).
    Também tenta com/sem 'type' por robustez (alguns exemplos antigos usavam).
    """
    base = {
        "date": f"{ini}/{fim}",
        "time": TIMES_3H,
        "variable": variables,
    }
    if area_list is not None:
        base["area"] = area_list

    # Variações de "formato": alguns aceitam data_format, outros format.
    reqs = []

    r1 = dict(base); r1["data_format"] = "netcdf"
    reqs.append(("data_format + time (3h)", r1))

    r2 = dict(base); r2["format"] = "netcdf"
    reqs.append(("format + time (3h)", r2))

    # Algumas APIs/rotas antigas aceitam/esperam 'type'; deixamos como fallback.
    r3 = dict(r1); r3["type"] = "reanalysis"
    reqs.append(("data_format + time + type=reanalysis", r3))

    r4 = dict(r2); r4["type"] = "reanalysis"
    reqs.append(("format + time + type=reanalysis", r4))

    return reqs

def retrieve_with_fallback(client_urls, key, dataset, reqs, target_path):
    """
    Tenta endpoints (/api e /api/v2) e, dentro de cada um, tenta cada payload.
    Diferente do seu script anterior: 400 agora tenta o próximo payload (não dá raise imediato).
    """
    last_err = None

    for base in client_urls:
        try:
            cli = new_client(base, key)
        except Exception as e:
            last_err = e
            continue

        for label, req in reqs:
            try:
                print(f"   → endpoint {base} | payload: {label}")
                cli.retrieve(dataset, req, target_path)
                return
            except Exception as e:
                last_err = e
                msg = str(e).lower()

                # 404/endpoint inválido → tenta próximo endpoint/payload
                if "endpoint not found" in msg or "404" in msg:
                    print("     ⚠️  404/endpoint: tentando próxima variação…")
                    continue

                # 400 invalid request → tentar próximo payload
                if "400" in msg or "invalid request" in msg:
                    print("     ⚠️  400/invalid request: tentando próximo payload…")
                    continue

                # 403 / cost limits / quota etc → sobe erro (o usuário deve reduzir)
                raise

    raise last_err

def open_ds(nc_path: str) -> xr.Dataset:
    # tenta abrir de forma simples; netCDF4 engine costuma ser o mais compatível
    try:
        return xr.open_dataset(nc_path)
    except Exception:
        return xr.open_dataset(nc_path, engine="netcdf4")

def nc_to_daily_df(nc_path: str, tz: str) -> pd.DataFrame:
    ds = open_ds(nc_path)

    # Alguns arquivos vêm com 'valid_time' em vez de 'time'
    if "time" not in ds.coords and "valid_time" in ds.coords:
        ds = ds.rename({"valid_time": "time"})

    # Média espacial (se tiver grid)
    lat_key = "latitude" if ("latitude" in ds.dims or "latitude" in ds.coords) else ("lat" if ("lat" in ds.dims or "lat" in ds.coords) else None)
    lon_key = "longitude" if ("longitude" in ds.dims or "longitude" in ds.coords) else ("lon" if ("lon" in ds.dims or "lon" in ds.coords) else None)
    if lat_key and lon_key and lat_key in ds.dims and lon_key in ds.dims:
        ds = ds.mean(dim=[lat_key, lon_key], skipna=True)

    present_vars = list(ds.data_vars)
    if not present_vars:
        raise ValueError("Dataset sem data_vars (inesperado).")

    # Aceita nomes longos E curtos
    alias = {
        # longos -> curtos
        "particulate_matter_2.5um": "pm2p5",
        "particulate_matter_10um": "pm10",
        "nitrogen_dioxide": "no2",
        "sulphur_dioxide": "so2",
        "ozone": "o3",
        "carbon_monoxide": "co",
        "2m_temperature": "t2m",
        "2m_dewpoint_temperature": "d2m",
        "relative_humidity": "rh",
        "10m_u_component_of_wind": "u10",
        "10m_v_component_of_wind": "v10",
        "surface_pressure": "sp",
        "total_precipitation": "tp",
        # curtos -> curtos
        "pm2p5": "pm2p5",
        "pm10": "pm10",
        "t2m": "t2m",
        "d2m": "d2m",
        "u10": "u10",
        "v10": "v10",
        "sp": "sp",
        "rh": "rh",
        "tp": "tp",
        "no2": "no2",
        "so2": "so2",
        "o3": "o3",
        "co": "co",
    }

    df = ds.to_dataframe().reset_index()

    # Se 'time' veio como índice com outro nome, tenta recuperar
    if "time" not in df.columns:
        if "valid_time" in df.columns:
            df = df.rename(columns={"valid_time": "time"})
        else:
            raise ValueError(f"Não encontrei coluna temporal. Colunas: {list(df.columns)}")

    # Mantém somente time + variáveis que existem no DF e são reconhecidas
    alias_values = set(alias.values())
    keep_vars = [c for c in df.columns if (c in alias) or (c in alias_values)]
    df = df[["time"] + keep_vars].copy()

    if len(keep_vars) == 0:
        raise ValueError(f"Nenhuma variável reconhecida. Vars no arquivo: {present_vars}")

    # --- FORÇA DatetimeIndex corretamente (isso resolve o RangeIndex no resample) ---
    # 1) converte para datetime; assume UTC quando vier sem tz
    t = pd.to_datetime(df["time"], errors="coerce", utc=True)
    df = df.dropna(subset=["time"])
    # se a linha acima não removeu NaT por causa do objeto antigo:
    df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
    df = df.dropna(subset=["time"])

    # 2) converte para TZ local antes de agregar por dia
    df["time"] = df["time"].dt.tz_convert(tz)

    # 3) index datetime
    df = df.set_index("time").sort_index()

    # renomeia colunas longas para curtas
    rename_map = {c: alias[c] for c in df.columns if c in alias}
    df = df.rename(columns=rename_map)

    # agregação diária
    agg = {c: ("sum" if c == "tp" else "mean") for c in df.columns}
    df_day = df.resample("D").agg(agg)

    # derivadas
    if "t2m" in df_day.columns:
        df_day["t2m_c"] = df_day["t2m"] - 273.15
    if "u10" in df_day.columns and "v10" in df_day.columns:
        df_day["ws10"] = np.sqrt(df_day["u10"] ** 2 + df_day["v10"] ** 2)

    df_day.index = df_day.index.tz_localize(None)
    df_day.index.name = "data"
    return df_day.reset_index()

# ---------------- main ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ini", required=True)
    ap.add_argument("--fim", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--chunk-meses", type=int, default=1)
    ap.add_argument("--area", nargs=4, type=float, metavar=("N", "W", "S", "E"),
                    default=list(AREA_SP_GRADE),
                    help="N W S E. O padrão contém o ponto de grade de São Paulo; "
                         "ver AREA_SP_GRADE antes de mudar.")
    ap.add_argument("--tz", default="America/Sao_Paulo")
    ap.add_argument("--rawdir-base", default="data/raw")
    ap.add_argument("--raw-dir", default=None,
                    help="pasta exata dos NetCDF (para retomar um download de outro dia); "
                         "se omitida, usa <rawdir-base>/<nome da saída>_<data de hoje>")
    args = ap.parse_args()

    ensure_dir(os.path.dirname(args.saida))

    today_tag = datetime.now().strftime("%Y-%m-%d")
    base_name = os.path.splitext(os.path.basename(args.saida))[0] or "cams_download"
    raw_dir = args.raw_dir or os.path.join(args.rawdir_base, f"{base_name}_{today_tag}")
    ensure_dir(raw_dir)

    url, key, cred_origem = load_cds_credentials()
    print(f"🔎 Credenciais: {cred_origem}")
    if ":" in key and url.rstrip("/").endswith("/api"):
        print("⚠️  A chave tem prefixo 'UID:' (formato antigo) mas a url é /api (pilha nova).")
        print("   Se o download falhar com 401, gere um Personal Access Token novo no ADS.")

    client_urls = normalize_urls(url)
    area_list = args.area if args.area is not None else None

    # Monta lista de variáveis com fallback:
    # tenta primeiro CORE+OPTIONAL; se der 400, tenta só CORE.
    var_sets = [
        ("CORE+OPTIONAL", VARS_CORE + VARS_OPTIONAL),
        ("CORE", VARS_CORE),
    ]

    dfs = []
    for ini, fim in chunk_ranges(args.ini, args.fim, months=args.chunk_meses):
        out_nc = os.path.join(raw_dir, f"eac4_{ini}_to_{fim}.nc")

        # RETOMADA (2026-10-19): um chunk já baixado e íntegro é reaproveitado — a fila do
        # ADS pode travar por horas e um download de 72 meses não pode recomeçar do zero.
        # "Íntegro" = abre e tem todas as variáveis obrigatórias; senão, baixa de novo.
        if os.path.isfile(out_nc) and os.path.getsize(out_nc) > 0:
            try:
                exigir_variaveis(out_nc, var_sets[0][1])
                print(f"↻ Reaproveitando {os.path.basename(out_nc)} (já no disco, variáveis obrigatórias presentes)")
                dfs.append(nc_to_daily_df(out_nc, tz=args.tz))
                continue
            except Exception as e:  # noqa: BLE001
                print(f"   ⚠️  {os.path.basename(out_nc)} existe mas não serve ({e}); baixando de novo.")
                os.remove(out_nc)

        # baixa (com retries)
        tries, backoff = 0, 20
        while True:
            tries += 1
            try:
                print(f"→ Requisitando {DATASET} {ini}..{fim} | chunk={args.chunk_meses} mês(es) | tz={args.tz}")

                downloaded = False
                last_exc = None

                for label_vars, var_list in var_sets:
                    reqs = candidate_requests(ini, fim, area_list, var_list)
                    try:
                        print(f"   Vars: {label_vars} ({len(var_list)} vars)")
                        retrieve_with_fallback(client_urls, key, DATASET, reqs, out_nc)
                        exigir_variaveis(out_nc, var_list)
                        downloaded = True
                        break
                    except Exception as e:
                        last_exc = e
                        msg = str(e).lower()
                        # se for 400/invalid request, tenta próximo var_set
                        if "400" in msg or "invalid request" in msg:
                            print("   ⚠️  400 com esse conjunto de variáveis; tentando conjunto menor…")
                            continue
                        # outros erros sobem
                        raise

                if not downloaded:
                    raise last_exc if last_exc else RuntimeError("Falha ao baixar chunk (sem erro detalhado).")

                # converte para diário e acumula
                dfd = nc_to_daily_df(out_nc, tz=args.tz)
                dfs.append(dfd)

                print("   ✅ Chunk OK. Colunas:", ", ".join([c for c in dfd.columns if c != "data"]))
                break

            except Exception as e:
                print(f"⚠️ Erro no chunk {ini}..{fim}: {e}")

                # Se for cost limit, a ação correta é reduzir o chunk ou variáveis
                if "cost limits exceeded" in str(e).lower() or "too large" in str(e).lower() or "403" in str(e).lower():
                    print("   ❌ Erro de COST LIMIT/403. Sugestões:")
                    print("   - Use --chunk-meses 1 (ou menor) e reduza variáveis.")
                    print("   - Garanta que 'time' está 3-hourly (já está).")
                    raise

                if tries <= 3:
                    print(f"   Retry em {backoff}s ({tries}/3)…")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    # debug rápido: se baixou arquivo corrompido/parcial, listar vars pode ajudar
                    if os.path.isfile(out_nc):
                        try:
                            ds_dbg = open_ds(out_nc)
                            print("   🔎 Vars no NetCDF baixado:", list(ds_dbg.data_vars))
                        except Exception:
                            pass
                    raise

    if not dfs:
        print("Nenhum chunk processado — verifique parâmetros/intervalos.")
        sys.exit(2)

    df = pd.concat(dfs, axis=0).sort_values("data").drop_duplicates(subset=["data"]).reset_index(drop=True)

    # reordena colunas (se existirem)
    prefer = ["data", "pm2p5", "pm10", "no2", "so2", "o3", "co", "t2m", "t2m_c", "rh", "u10", "v10", "ws10", "sp", "tp"]
    cols = [c for c in prefer if c in df.columns] + [c for c in df.columns if c not in prefer]
    df = df[cols]

    df.to_csv(args.saida, index=False, float_format="%.8g")

    print(f"📁 Diretório de brutos (NetCDF): {raw_dir}")
    print(f"✅ CSV diário salvo em: {args.saida}")
    print("   Colunas:", ", ".join(df.columns))

if __name__ == "__main__":
    # Console do Windows e cp1252 por padrao e os prints usam emoji: sem isto o
    # script morria em UnicodeEncodeError ANTES de fazer qualquer requisicao
    # (constatado em 2026-10-19 ao reexecutar o download em diretorio separado).
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    main()
