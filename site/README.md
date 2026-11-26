# site/ — project page (GitHub Pages)

Static page, no backend, no CDN, no key. Future URL: <https://matheusmmmp.github.io/sp-respiratory-admissions-forecast/> (English) and `index.pt-BR.html` (Portuguese). Not published yet: enabling GitHub Pages is a pending author decision (`docs/DECISOES.md`, D10).

**Do not edit the generated files by hand.** Edit `docs/scripts/build_site.py` (texts, template, figures) and rebuild:

```bash
uv run python docs/scripts/build_site.py          # rewrites the generated files; a second run changes nothing
uv run python docs/scripts/build_site.py --check  # builds into a temp folder and compares with site/ (exit 1 if stale)
uv run pytest tests/test_build_site.py -q         # the same comparison plus the content checks
```

To view it locally (the results explorer needs HTTP, not `file://`): `uv run python -m http.server 8000 --directory site`, then open port 8000 on your machine.

## What is generated and from what

| File | Generated from |
|---|---|
| `index.html`, `index.pt-BR.html` | `results/runs/<RUN_ID>/model_comparison.csv`, `manifest.json`, `folds.csv` (10 runs), `results/analise_multihorizonte/.../A_modelos_por_h.csv`, `A2_dm_modelos_por_h.csv`, `results/numeros_texto_urgencia/.../arcal_por_horizonte_dois_alvos.csv`; texts from `README.md` / `README.pt-BR.md` (summary, protocol paragraph, "What is in the box", "What this repository is not"), `data/README.md` (sources, licences, attribution) and `CITATION.cff` (title, BibTeX) |
| `static/images/fig_*_{en,pt}.png` + `.prov.json` | the same CSVs plus `metrics_by_fold.csv` and `config.json` of the h = 1 runs and `erro_sabado_h1.csv`; every `.prov.json` lists the source files with sha256, the run ids and the package versions |
| `static/images/pipeline_{en,pt}.svg` | the Mermaid block of `README.md` / `README.pt-BR.md` (parsed; the build fails if a node is not in the layout) |
| `data/a_modelos_por_h.json` | read by `static/js/results_explorer.js` (target × horizon × metric; MASE one horizon at a time) |
| `data/*.csv`, `data/runs/<RUN_ID>/*.csv` | byte copies of the files in `results/`, sha256 checked after copying |
| `build_provenance.json` | every input and output with sha256, the run ids and the list of cross-checks |

Before writing anything the build checks every `results/` file against `docs/INVENTARIO_FASE0.tsv`, requires `model_comparison.csv`, `A_modelos_por_h.csv` and `arcal_por_horizonte_dois_alvos.csv` to agree to 1e-9 on both targets (through `docs/scripts/tabela_readme.py`), and raises on any divergence. JSON files keep their `gerado_em` timestamp when nothing else changed, so rebuilding is a no-op.

## Not generated

- `static/images/app_screenshot.png`: headless Chrome capture of the public Streamlit app on 2026-11-26 (command, crop and sha256 in `app_screenshot.prov.json`). The build only checks its sha256 and size.
- `static/css/bulma.min.css`, `static/css/fontawesome.all.min.css`, `static/webfonts/`: third-party files, versions and licences in `static/VENDOR.md`.
- `static/css/site.css` (adapted from the Nerfies template, CC BY-SA 4.0) and `static/js/results_explorer.js` (MIT, like the rest of the code).

## Rules the page follows

- "Provisional (pre-defence)" at the top and next to every results table and figure block; the dissertation button is disabled ("in preparation"); no paper, preprint, venue or DOI is claimed.
- Only the main base (CETESB/QUALAR, rich representation) and the two targets of `results/`; no figure from the mirror, CAMS or hybrid runs of the dissertation (`docs/DECISOES.md`, D13).
- Vocabulary: always "fold" (also on the Portuguese page). Decimal point in tables in both languages (as in the source files); Portuguese captions use decimal commas.
- PNG below 300 KB each; no PDF.

## Publishing (author only; nothing here has been run)

See `docs/DECISOES.md`, D10. Enable Pages with "Source: GitHub Actions", then run the "Project page" workflow (`.github/workflows/pages.yml`) by hand.
