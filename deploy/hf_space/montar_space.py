"""Monta, numa pasta FORA do repositório, o conteúdo exato de um Hugging Face
Space do tipo Docker com a API de demonstração (api/Dockerfile).

    uv run python deploy/hf_space/montar_space.py --destino ../sp-resp-forecast-space

O que vai para a pasta de destino (layout relativo idêntico ao do repositório,
porque ``models_demo/comum.py`` resolve ``RAIZ = parents[1]`` e o Dockerfile
copia caminhos relativos à raiz):

* ``Dockerfile``            <- ``api/Dockerfile`` (conferido linha a linha: toda
  origem de ``COPY`` precisa existir no destino; o arquivo não muda);
* ``api/``, ``models_demo/``, ``src/`` (só o que a API importa), ``configs/``
  dos três horizontes e os quatro arquivos de ``data/processed`` — dados e
  modelos ``.ubj`` conferidos por sha256 contra ``models_demo/metadata.json``
  (a mesma conferência que a API faz ao subir);
* ``README.md`` com o cabeçalho YAML do HF (sdk: docker, app_port: 7860);
* ``.gitattributes`` marcando ``*.ubj`` e ``*.parquet`` para Git LFS/Xet.

Falha alto (exceção, exit != 0) se faltar qualquer arquivo, se um sha256 não
bater, se o destino estiver dentro do repositório ou já tiver conteúdo (use
``--sobrescrever`` para limpar antes). Nunca cria conta, Space ou faz push.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
METADATA = RAIZ / "models_demo" / "metadata.json"
DOCKERFILE_API = RAIZ / "api" / "Dockerfile"

REPO_GITHUB = "https://github.com/matheusmmmp/sp-respiratory-admissions-forecast"
APP_STREAMLIT = "https://sp-respiratory-admissions-forecast.streamlit.app/"

#: (origem relativa à raiz do repositório, destino relativo à raiz do Space)
ARQUIVOS: tuple[tuple[str, str], ...] = (
    ("api/Dockerfile", "Dockerfile"),
    ("api/requirements.txt", "api/requirements.txt"),
    ("api/__init__.py", "api/__init__.py"),
    ("api/main.py", "api/main.py"),
    ("models_demo/__init__.py", "models_demo/__init__.py"),
    ("models_demo/comum.py", "models_demo/comum.py"),
    ("models_demo/metadata.json", "models_demo/metadata.json"),
    ("models_demo/MODEL_CARD.md", "models_demo/MODEL_CARD.md"),
    ("models_demo/xgboost_ar_cal_h1.ubj", "models_demo/xgboost_ar_cal_h1.ubj"),
    ("models_demo/xgboost_ar_cal_h7.ubj", "models_demo/xgboost_ar_cal_h7.ubj"),
    ("models_demo/xgboost_ar_cal_h30.ubj", "models_demo/xgboost_ar_cal_h30.ubj"),
    ("src/__init__.py", "src/__init__.py"),
    ("src/features/__init__.py", "src/features/__init__.py"),
    ("src/features/forecasting_features.py", "src/features/forecasting_features.py"),
    ("src/models/__init__.py", "src/models/__init__.py"),
    ("src/models/base.py", "src/models/base.py"),
    ("src/models/xgboost_model.py", "src/models/xgboost_model.py"),
    ("configs/h1_v02_cetesb_cetesb_classicos.yaml", "configs/h1_v02_cetesb_cetesb_classicos.yaml"),
    ("configs/multihorizonte/mh_h7_cetesb_cetesb.yaml", "configs/multihorizonte/mh_h7_cetesb_cetesb.yaml"),
    ("configs/multihorizonte/mh_h30_cetesb_cetesb.yaml", "configs/multihorizonte/mh_h30_cetesb_cetesb.yaml"),
    ("data/processed/sih_daily_lookahead.parquet", "data/processed/sih_daily_lookahead.parquet"),
    ("data/processed/cams_daily_v2.csv", "data/processed/cams_daily_v2.csv"),
    ("data/processed/cetesb_poluentes_daily.csv", "data/processed/cetesb_poluentes_daily.csv"),
    ("data/processed/cetesb_meteo_daily.csv", "data/processed/cetesb_meteo_daily.csv"),
)

GITATTRIBUTES = """\
# Hugging Face: binários grandes via Git LFS / Xet.
*.ubj filter=lfs diff=lfs merge=lfs -text
*.parquet filter=lfs diff=lfs merge=lfs -text
* text=auto eol=lf
# Dados e configs: bytes preservados (sem conversão de fim de linha), porque a API confere o
# sha256 de cada arquivo de dados contra models_demo/metadata.json e se recusa a subir se mudar.
# Sem isto, um Git com core.autocrlf (padrão no Windows) trocaria CRLF por LF no push.
data/** -text
configs/** -text
"""

README_TEMPLATE = """\
---
title: SP Respiratory Admissions Forecast API
emoji: 🫁
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Demo API — daily respiratory admissions, São Paulo
---

# SP respiratory admissions forecast — demo API

**Demonstration, not a dissertation result.** This Space serves the FastAPI
demo of [sp-respiratory-admissions-forecast]({repo}): an XGBoost `AR_CAL`
model (single seed, trained on the whole 2019–2024 history) that forecasts the
daily count of respiratory hospital admissions (ICD-10 J00–J99) in São Paulo
city 1, 7 or 30 days ahead. Model version `{versao}`; features built by the
same canonical code as the dissertation benchmark. All numbers are
**provisional**; the evaluated results live in the GitHub repository.

* `GET /health` — status, model version, horizons and valid origin ranges.
* `GET /forecast?h=7&origem=2024-06-01` — point forecast for `origem + h`.
* `GET /docs` — interactive OpenAPI documentation.

Links: [source code and results]({repo}) · [Streamlit app]({app}) ·
model card in `models_demo/MODEL_CARD.md`.

Data: SIH/SUS (DATASUS) daily aggregates and CETESB/QUALAR daily air-quality and
weather aggregates — no record-level data. Built from the repository with
`deploy/hf_space/montar_space.py`.
"""


def sha256_arquivo(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _hashes_esperados(metadata: dict) -> dict[str, str]:
    """Caminho relativo -> sha256 registrado no treino: os 4 arquivos de dados
    (``entradas``) e os 3 modelos ``.ubj`` (``modelos[h].arquivo_sha256``) — os
    mesmos que ``api/main.py`` confere na subida. Os configs não têm hash
    registrado; deles exige-se só a existência (``comum.carregar_config``
    valida horizonte e feature set em tempo de execução)."""
    esperados: dict[str, str] = {}
    for ent in metadata["entradas"].values():
        if isinstance(ent, dict) and "arquivo" in ent:
            esperados[ent["arquivo"]] = ent["sha256"]
    for m in metadata["modelos"].values():
        esperados[m["arquivo"]] = m["arquivo_sha256"]
    return esperados


def _conferir_destino(destino: Path, sobrescrever: bool) -> None:
    destino = destino.resolve()
    if destino == RAIZ or destino.is_relative_to(RAIZ):
        raise ValueError(f"o destino deve ficar FORA do repositório ({RAIZ}); recebido: {destino}")
    if destino.exists():
        if not destino.is_dir():
            raise NotADirectoryError(destino)
        if any(destino.iterdir()):
            if not sobrescrever:
                raise FileExistsError(f"{destino} não está vazio; use --sobrescrever para limpar antes")
            for filho in destino.iterdir():
                if filho.name == ".git":
                    continue  # preserva o clone do Space, se o autor já clonou
                shutil.rmtree(filho) if filho.is_dir() else filho.unlink()


def _conferir_dockerfile(destino: Path, dockerfile: Path) -> list[str]:
    """Toda origem de COPY (exceto --from=<stage>) precisa existir no destino. Devolve as origens."""
    origens: list[str] = []
    for linha in dockerfile.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha.startswith("COPY ") or "--from=" in linha:
            continue
        partes = [p for p in linha.split()[1:] if not p.startswith("--")]
        for origem in partes[:-1]:
            if not (destino / origem).exists():
                raise FileNotFoundError(f"Dockerfile copia '{origem}', que não existe no Space montado")
            origens.append(origem)
    if not origens:
        raise RuntimeError("nenhuma instrução COPY encontrada no Dockerfile — arquivo errado?")
    return origens


def montar(destino: Path, sobrescrever: bool = False, arquivos=ARQUIVOS) -> dict:
    """Monta o Space em ``destino`` e devolve um resumo (arquivos, bytes, versão)."""
    destino = Path(destino)
    if not METADATA.exists():
        raise FileNotFoundError(f"faltando {METADATA.relative_to(RAIZ).as_posix()}: rode models_demo/treinar.py")
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    esperados = _hashes_esperados(metadata)

    faltando = [o for o, _ in arquivos if not (RAIZ / o).is_file()]
    if faltando:
        raise FileNotFoundError("arquivos ausentes no repositório: " + ", ".join(faltando))
    divergentes = [o for o, _ in arquivos if o in esperados and sha256_arquivo(RAIZ / o) != esperados[o]]
    if divergentes:
        raise RuntimeError("sha256 diferente do registrado em models_demo/metadata.json: " + ", ".join(divergentes))
    nao_cobertos = [a for a in esperados if a not in {o for o, _ in arquivos}]
    if nao_cobertos:
        raise RuntimeError("metadata.json referencia arquivos que o Space não copia: " + ", ".join(nao_cobertos))

    _conferir_destino(destino, sobrescrever)
    destino.mkdir(parents=True, exist_ok=True)

    total = 0
    for origem, dest in arquivos:
        alvo = destino / dest
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RAIZ / origem, alvo)
        total += alvo.stat().st_size

    (destino / ".gitattributes").write_text(GITATTRIBUTES, encoding="utf-8", newline="\n")
    readme = README_TEMPLATE.format(repo=REPO_GITHUB, app=APP_STREAMLIT, versao=metadata["versao"])
    (destino / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    origens = _conferir_dockerfile(destino, destino / "Dockerfile")
    cabecalho = re.match(r"^---\n(.*?)\n---\n", readme, re.S)
    if not cabecalho or "sdk: docker" not in cabecalho.group(1) or "app_port: 7860" not in cabecalho.group(1):
        raise RuntimeError("README.md do Space sem cabeçalho YAML válido (sdk: docker, app_port: 7860)")

    return {
        "destino": str(destino.resolve()),
        "arquivos": [dest for _, dest in arquivos] + [".gitattributes", "README.md"],
        "bytes_copiados": total,
        "versao_modelo": metadata["versao"],
        "origens_dockerfile": origens,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--destino", required=True, type=Path, help="pasta de saída, FORA do repositório")
    ap.add_argument("--sobrescrever", action="store_true", help="esvazia o destino antes (preserva .git)")
    args = ap.parse_args(argv)
    resumo = montar(args.destino, sobrescrever=args.sobrescrever)
    print(f"Space montado em {resumo['destino']}")
    mb = resumo["bytes_copiados"] / 1e6
    print(f"  modelo {resumo['versao_modelo']} - {len(resumo['arquivos'])} arquivos - {mb:.1f} MB")
    print("  próximo passo: deploy/hf_space/LEIA-ME.md (git add/commit/push para o repositório do Space)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
