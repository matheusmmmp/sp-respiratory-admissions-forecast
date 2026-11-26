"""Testes do montador do Hugging Face Space (deploy/hf_space/montar_space.py).

Não criam Space nem fazem push: montam a pasta num diretório temporário e
conferem conteúdo, cabeçalho do README, .gitattributes e os COPY do Dockerfile.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "deploy" / "hf_space" / "montar_space.py"


def _carregar_modulo():
    spec = importlib.util.spec_from_file_location("montar_space", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ms():
    return _carregar_modulo()


@pytest.fixture
def space(ms, tmp_path):
    destino = tmp_path / "space"
    resumo = ms.montar(destino)
    return destino, resumo


def test_todos_os_arquivos_copiados_e_identicos(ms, space):
    destino, resumo = space
    for origem, dest in ms.ARQUIVOS:
        a, b = RAIZ / origem, destino / dest
        assert b.is_file(), dest
        assert hashlib.sha256(a.read_bytes()).hexdigest() == hashlib.sha256(b.read_bytes()).hexdigest(), dest
    assert resumo["bytes_copiados"] == sum((destino / d).stat().st_size for _, d in ms.ARQUIVOS)


def test_dockerfile_na_raiz_do_space_sem_alteracao(space):
    destino, resumo = space
    assert (destino / "Dockerfile").read_bytes() == (RAIZ / "api" / "Dockerfile").read_bytes()
    assert resumo["origens_dockerfile"], "o Dockerfile precisa ter COPY conferidos"
    for origem in resumo["origens_dockerfile"]:
        assert (destino / origem).exists(), origem


def test_readme_com_cabecalho_hf(space):
    destino, resumo = space
    texto = (destino / "README.md").read_text(encoding="utf-8")
    cab = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    assert cab, "README sem cabeçalho YAML"
    campos = dict(linha.split(": ", 1) for linha in cab.group(1).splitlines())
    assert campos["sdk"] == "docker"
    assert campos["app_port"] == "7860"
    assert campos["pinned"] == "false"
    assert campos["license"] == "mit"
    assert len(campos["short_description"]) <= 60
    for chave in ("title", "emoji", "colorFrom", "colorTo"):
        assert chave in campos
    assert resumo["versao_modelo"] in texto
    assert "https://github.com/" in texto and "streamlit.app" in texto
    assert "not a dissertation result" in texto


def test_gitattributes_marca_lfs(space):
    destino, _ = space
    linhas = (destino / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "*.ubj filter=lfs diff=lfs merge=lfs -text" in linhas
    assert "*.parquet filter=lfs diff=lfs merge=lfs -text" in linhas


def test_sha256_confere_com_metadata(ms, space):
    destino, _ = space
    meta = json.loads((destino / "models_demo" / "metadata.json").read_text(encoding="utf-8"))
    for ent in meta["entradas"].values():
        if isinstance(ent, dict) and "arquivo" in ent:
            assert ms.sha256_arquivo(destino / ent["arquivo"]) == ent["sha256"], ent["arquivo"]
    for m in meta["modelos"].values():
        assert ms.sha256_arquivo(destino / m["arquivo"]) == m["arquivo_sha256"], m["arquivo"]
        assert (destino / m["config"]).is_file(), m["config"]


def test_falha_alto_se_faltar_arquivo(ms, tmp_path):
    arquivos = ms.ARQUIVOS + (("models_demo/nao_existe.ubj", "models_demo/nao_existe.ubj"),)
    with pytest.raises(FileNotFoundError, match="nao_existe"):
        ms.montar(tmp_path / "space", arquivos=arquivos)


def test_recusa_destino_dentro_do_repo(ms):
    with pytest.raises(ValueError, match="FORA do repositório"):
        ms.montar(RAIZ / "deploy" / "hf_space" / "_saida_proibida")
    assert not (RAIZ / "deploy" / "hf_space" / "_saida_proibida").exists()


def test_recusa_destino_nao_vazio_sem_sobrescrever(ms, tmp_path):
    destino = tmp_path / "space"
    destino.mkdir()
    (destino / "lixo.txt").write_text("x")
    with pytest.raises(FileExistsError):
        ms.montar(destino)
    ms.montar(destino, sobrescrever=True)
    assert not (destino / "lixo.txt").exists() and (destino / "Dockerfile").exists()


def test_gitattributes_preserva_bytes_dos_dados(space):
    """A API confere o sha256 dos dados: o Space não pode normalizar fim de linha dos CSV."""
    destino = space[0] if isinstance(space, tuple) else space
    linhas = (destino / ".gitattributes").read_text(encoding="utf-8").splitlines()
    assert "data/** -text" in linhas
    assert "configs/** -text" in linhas
    # a regra -text precisa vir depois de '* text=auto' para prevalecer
    assert linhas.index("data/** -text") > linhas.index("* text=auto eol=lf")
