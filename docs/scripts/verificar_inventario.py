"""Verify docs/INVENTARIO_FASE0.tsv against the files of this checkout.

The TSV records the sha256 of every file as it was copied from the dissertation
repository (Windows working copy, CRLF line endings for text files). Data,
results, configs and the Saturday panel are stored byte for byte (``-text`` in
``.gitattributes``), so their sha256 must match exactly in any checkout. Code and
docs are normalised to LF by Git, so for them the comparison is made after
mapping CRLF to LF. Files edited on purpose after the copy are listed in
``EDITADOS_DEPOIS``; anything else that differs is an error.

    uv run python docs/scripts/verificar_inventario.py
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TSV = RAIZ / "docs" / "INVENTARIO_FASE0.tsv"
#: files deliberately changed after the copy (owner, reason)
EDITADOS_DEPOIS = {
    "notebooks/gerar_notebook.py": "WP3: reads notebooks/dados_painel/ by default instead of Google Drive",
    "src/ingestion/cetesb_build_poluentes.py": "manager: user-name path removed from the usage example in the docstring",
    "src/ingestion/cetesb_build_meteo.py": "manager: user-name path removed from the usage example in the docstring",
    "src/ingestion/cetesb_build_daily.py": "manager: user-name path removed from the usage example in the docstring",
    "src/experiments/run_preliminary.py": "phase B (D9): opt-in --mlflow flag; output byte-identical without it",
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    exatos = normalizados = editados = 0
    erros: list[str] = []
    with open(TSV, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            p = RAIZ / r["destino"]
            if not p.exists():
                erros.append(f"AUSENTE  {r['destino']}")
                continue
            b = p.read_bytes()
            if sha(b) == r["sha256"]:
                exatos += 1
            elif sha(b.replace(b"\r\n", b"\n")) == r["sha256"] or sha(b.replace(b"\n", b"\r\n")) == r["sha256"]:
                normalizados += 1
            elif r["destino"] in EDITADOS_DEPOIS:
                editados += 1
            else:
                erros.append(f"DIFERE   {r['destino']}")
    print(f"exatos={exatos} iguais_apos_eol={normalizados} editados_declarados={editados} erros={len(erros)}")
    for e in erros:
        print(" ", e)
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
