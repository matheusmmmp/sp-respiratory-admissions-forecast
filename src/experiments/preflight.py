"""PREFLIGHT — verifica o ambiente ANTES de baixar dado ou treinar modelo.

    python -m src.experiments.preflight
    python -m src.experiments.preflight --config configs/preliminary_h1.yaml

Existe para transformar "quebrou na terceira hora de treino porque faltava o
xgboost" em "falhou em 2 segundos dizendo o que falta". Não baixa nada, não
treina nada e não escreve em `reports/`.

Sai com código 1 se houver qualquer FAIL. Segredo nenhum é impresso: de
variáveis de ambiente sensíveis só se informa PRESENTE/AUSENTE.
"""
from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

FAIL, WARN, PASS = "FAIL", "WARN", " ok "

#: (módulo, versão mínima aceitável ou None, obrigatório?)
PACOTES = [
    ("numpy", None, True),
    ("pandas", None, True),
    ("yaml", None, True),
    ("sklearn", None, True),
    ("xgboost", None, True),      # §31: obrigatório, nunca "pula se faltar"
    ("tensorflow", None, True),
    ("statsmodels", None, True),  # SARIMAX (trilha clássica); o runner importa no topo
    ("matplotlib", None, True),
    ("tabulate", None, True),     # summary.md usa DataFrame.to_markdown
    ("pyarrow", None, True),      # o SIH é parquet
    ("pytest", None, False),
]

#: Variáveis usadas pelos pipelines de ingestão. Só reportamos presença.
CREDENCIAIS = ["CDSAPI_KEY", "CDSAPI_URL"]


def _linha(status: str, nome: str, detalhe: str) -> tuple[str, str]:
    print(f"  [{status}] {nome:26s} {detalhe}")
    return status, nome


def credencial_ads() -> tuple[bool, str]:
    """Onde a credencial do ADS foi encontrada — sem jamais devolver o valor.

    ⚠️ Checar só variáveis de ambiente dava FALSO NEGATIVO. `cams_download*.py`
    resolve a credencial na ordem env -> `~/.cdsapirc` -> `./.cdsapirc`, e esta
    máquina tem o `~/.cdsapirc`. O preflight dizia "AUSENTE" para uma credencial
    perfeitamente utilizável, o que sugeria erradamente que o download do CAMS
    estava bloqueado.
    """
    if os.environ.get("CDSAPI_URL") and os.environ.get("CDSAPI_KEY"):
        return True, "variáveis de ambiente"

    for rc in (Path.home() / ".cdsapirc", RAIZ / ".cdsapirc"):
        if not rc.is_file():
            continue
        try:
            texto = rc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Só a PRESENÇA das chaves. O valor nunca é lido para memória nem impresso.
        tem_url = any(l.strip().startswith("url:") for l in texto.splitlines())
        tem_key = any(l.strip().startswith("key:") for l in texto.splitlines())
        if tem_url and tem_key:
            return True, str(rc)
        if tem_url or tem_key:
            return False, f"{rc} incompleto (url={tem_url}, key={tem_key})"

    return False, "não encontrada em env, ~/.cdsapirc nem ./.cdsapirc"


def main() -> None:
    ap = argparse.ArgumentParser(description="Verificação de ambiente do framework v0.1")
    ap.add_argument("--config", type=Path, default=None,
                    help="se dado, também confere os arquivos de dados que ele referencia")
    args = ap.parse_args()

    falhas: list[str] = []
    avisos: list[str] = []

    print("=" * 78)
    print("PREFLIGHT — framework preliminar v0.1")
    print("=" * 78)

    # ------------------------------------------------------------------ python
    print("\nINTERPRETADOR")
    v = sys.version_info
    ok_py = (v.major, v.minor) >= (3, 10)
    st, _ = _linha(PASS if ok_py else FAIL, "python",
                   f"{platform.python_version()} ({sys.executable})")
    if not ok_py:
        falhas.append("python < 3.10")
    _linha(PASS, "plataforma", platform.platform())

    # ----------------------------------------------------------------- pacotes
    print("\nPACOTES")
    for nome, _minimo, obrigatorio in PACOTES:
        try:
            mod = importlib.import_module(nome)
            ver = getattr(mod, "__version__", "?")
            _linha(PASS, nome, str(ver))
        except Exception as exc:  # noqa: BLE001 - queremos o motivo exato
            if obrigatorio:
                _linha(FAIL, nome, f"AUSENTE — {type(exc).__name__}: {str(exc)[:60]}")
                falhas.append(f"pacote obrigatório ausente: {nome}")
            else:
                _linha(WARN, nome, "ausente (opcional)")
                avisos.append(f"pacote opcional ausente: {nome}")

    # --------------------------------------------------------------------- GPU
    print("\nACELERAÇÃO (opcional)")
    try:
        import tensorflow as tf

        gpus = tf.config.list_physical_devices("GPU")
        _linha(PASS if gpus else WARN, "gpu",
               f"{len(gpus)} GPU(s)" if gpus else "nenhuma — a LSTM roda em CPU, apenas mais devagar")
    except Exception as exc:  # noqa: BLE001
        _linha(WARN, "gpu", f"não foi possível consultar: {type(exc).__name__}")

    # --------------------------------------------------------------- diretórios
    print("\nDIRETÓRIOS")
    for rel in ("data/processed", "reports/experiments", "configs", "src", "tests"):
        p = RAIZ / rel
        existe = p.is_dir()
        _linha(PASS if existe else WARN, rel, str(p) if existe else "ausente (será criado se necessário)")
        if not existe and rel in ("configs", "src"):
            falhas.append(f"diretório essencial ausente: {rel}")

    # ------------------------------------------------------------- credenciais
    print("\nCREDENCIAIS (só presença; nenhum valor é impresso)")
    tem_ads, origem_ads = credencial_ads()
    _linha(PASS if tem_ads else WARN, "ADS (CAMS)",
           f"PRESENTE — {origem_ads}" if tem_ads
           else f"AUSENTE — {origem_ads}. Só necessária para baixar/reconstruir o CAMS")
    if not tem_ads:
        avisos.append("credencial do ADS ausente: o CAMS não pode ser rebaixado")

    # ------------------------------------------------------------------ config
    if args.config:
        print("\nCONFIGURAÇÃO E DADOS")
        if not args.config.exists():
            _linha(FAIL, "config", f"{args.config} não existe")
            falhas.append("config inexistente")
        else:
            import yaml

            cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
            _linha(PASS, "config", str(args.config))

            dados = cfg.get("dados", {})
            obrigatorios = [("sih", True), ("cams", True)]
            fonte_pm25 = dados.get("fonte_pm25", "cams")
            fonte_meteo = dados.get("fonte_meteo", "cams")
            if fonte_pm25 in ("cetesb", "cetesb_min", "hibrida"):
                obrigatorios.append(("cetesb", True))
            if fonte_meteo in ("cetesb", "cetesb_min", "hibrida"):
                obrigatorios.append(("meteo", True))

            for chave, preciso in obrigatorios:
                rel = dados.get(chave)
                if rel is None:
                    _linha(FAIL if preciso else WARN, chave, "não declarado na config")
                    if preciso:
                        falhas.append(f"config sem 'dados.{chave}'")
                    continue
                p = Path(rel) if Path(rel).is_absolute() else RAIZ / rel
                if p.exists():
                    _linha(PASS, chave, f"{rel} ({p.stat().st_size/1e6:.1f} MB)")
                else:
                    _linha(FAIL, chave, f"{rel} AUSENTE — rode a ingestão (--data-mode rebuild)")
                    falhas.append(f"arquivo de dados ausente: {rel}")

            _linha(PASS, "fonte_pm25", fonte_pm25)
            _linha(PASS, "fonte_meteo", fonte_meteo)

            alvo = dados.get("alvo", {})
            validado = alvo.get("validado_contra_fonte_oficial", False)
            _linha(PASS if validado else WARN, "gate_do_alvo",
                   "PRELIMINARY_VALIDATED_TARGET" if validado
                   else "PRELIMINARY_UNVALIDATED_TARGET — resultados não são finais")
            if not validado:
                avisos.append("alvo não validado contra fonte oficial")

    # ---------------------------------------------------------------- veredito
    print("\n" + "=" * 78)
    if falhas:
        print(f"PREFLIGHT: FAIL ({len(falhas)} problema(s))")
        for f in falhas:
            print(f"  - {f}")
        print("=" * 78)
        sys.exit(1)
    print(f"PREFLIGHT: PASS" + (f" ({len(avisos)} aviso(s))" if avisos else ""))
    for a in avisos:
        print(f"  aviso: {a}")
    print("=" * 78)


if __name__ == "__main__":
    main()
