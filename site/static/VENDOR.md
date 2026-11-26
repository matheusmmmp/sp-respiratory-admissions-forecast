# Third-party files in `site/static/`

Downloaded on 2026-11-26 from the jsDelivr mirror of the official npm packages, unmodified (only renamed where noted). No CDN, font service or API key is used at run time: the page loads everything from this folder.

| File here | Package and version | Source URL | sha256 | Licence |
|---|---|---|---|---|
| `css/bulma.min.css` | `bulma` 0.9.4 | `https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css` | `ad3a5d3b41d7042369ade00772eead0763e9839d79568fb91ad612b2734bcfef` | MIT (Copyright (c) 2022 Jeremy Thomas) |
| `css/fontawesome.all.min.css` (renamed from `all.min.css`) | `@fortawesome/fontawesome-free` 6.5.2 | `https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.2/css/all.min.css` | `5ceaaba22d75b58e04150311f596306562a3e595e27ed4b1dfa451b82dda9e50` | Code: MIT |
| `webfonts/fa-solid-900.woff2` | same | `.../fontawesome-free@6.5.2/webfonts/fa-solid-900.woff2` | `ae17c16afbea216707b2203ea1cf9bdb45b9bfe47d0f4ae3258ddbc6294dd02f` | Fonts: SIL OFL 1.1; icons: CC BY 4.0 |
| `webfonts/fa-brands-400.woff2` | same | `.../fontawesome-free@6.5.2/webfonts/fa-brands-400.woff2` | `232c6f6a7678304f9efaa26f30b1610debc2ba9f4cd636b5e6751c8d73761b92` | Fonts: SIL OFL 1.1; icons: CC BY 4.0 |
| `webfonts/fa-regular-400.woff2` | same | `.../fontawesome-free@6.5.2/webfonts/fa-regular-400.woff2` | `c27da6f833431da5aa295c44540bfac0fd8270ba6a3c4346427006d8a7b34b76` | Fonts: SIL OFL 1.1; icons: CC BY 4.0 |

Notes

- Font Awesome's `all.min.css` also declares `.ttf` fallbacks and the `fa-v4compatibility` font; those files are not copied (every browser that renders this page reads `woff2`, and no v4 icon name is used).
- Academicons (used by the Nerfies template for the arXiv icon) is **not** included: this project has no arXiv preprint, paper or DOI yet, so no academic icon is needed.
- Licence texts: Bulma, <https://github.com/jgthms/bulma/blob/0.9.4/LICENSE>; Font Awesome Free, <https://fontawesome.com/license/free>.
- Page layout and the CSS in `css/site.css` are adapted from the Nerfies project page template (<https://github.com/nerfies/nerfies.github.io>, CC BY-SA 4.0), following the structure of <https://deeppersona-ai.github.io/> (itself adapted from AgentFlow). `css/site.css` is therefore distributed under CC BY-SA 4.0; the rest of this repository's code is MIT.

Note on the two CSS files: the repository's pre-commit end-of-file hook adds one trailing newline to each. The sha256 column above is the upstream file; the committed copies differ only by that final newline:

| File here | sha256 of the committed copy |
|---|---|
| `css/bulma.min.css` | `ccf74eb259a35a6e7492b2afb8bfa62181deb169fcf16772aed28bb83f3c8ad2` |
| `css/fontawesome.all.min.css` | `95dd6c1c93e3272f812f82429c1c0ccaeb57afaafc6e00237c2057d39be87a55` |
