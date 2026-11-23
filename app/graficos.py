"""Paleta e layout dos gráficos Plotly do app (skill `dataviz`).

- Cores categóricas em ordem fixa (nunca cicladas); a mesma cor para o mesmo modelo em todas as páginas.
- Paleta validada com `scripts/validate_palette.js` da skill (modo claro e escuro, 7 slots: PASS).
- Um eixo por gráfico; linhas 2 px; marcadores >= 8 px; barras <= 24 px; grade hairline sólida.
- Modo escuro: passos próprios (não é inversão automática), escolhidos por `st.context.theme`.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from i18n import separadores_plotly

# Slots categóricos (references/palette.md da skill dataviz), ordem fixa.
SLOTS = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"],
}
# Ordem fixa modelo -> slot (mesma cor em todas as páginas).
ORDEM_MODELOS = ["XGBoost", "SARIMAX", "LSTM", "INGARCH-NB", "GAM-NB", "Naïve", "Seasonal Naïve"]
# Séries do painel do sábado (entidades distintas dos modelos; slots 1–3 validam all-pairs).
# Os nomes de exibição ficam em i18n (`serie.<col>`).
ORDEM_SERIES = ["nao_eletivo", "eletivo", "cema"]

CHROME = {
    "light": dict(surface="#fcfcfb", text="#0b0b0b", text2="#52514e", muted="#898781", grid="#e1e0d9", axis="#c3c2b7"),
    "dark": dict(surface="#1a1a19", text="#f0efec", text2="#c3c2b7", muted="#898781", grid="#2c2c2a", axis="#383835"),
}
# Rampa sequencial azul (passos 100 -> 700 da skill).
RAMPA_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# Rampa sequencial laranja (segundo contexto sequencial, slot 2), uma hue só.
RAMPA_LARANJA = ["#fde3d6", "#f9bda0", "#f4976d", "#eb6834", "#c4501f", "#993b12", "#6e2908"]


def modo() -> str:
    """'light' ou 'dark' conforme o tema ativo do Streamlit (fallback: light)."""
    try:
        tipo = st.context.theme.type
    except Exception:  # noqa: BLE001 — fora de um ScriptRunContext (testes) não há tema
        tipo = None
    return "dark" if tipo == "dark" else "light"


def cores_modelos(m: str | None = None) -> dict[str, str]:
    m = m or modo()
    return {nome: SLOTS[m][i] for i, nome in enumerate(ORDEM_MODELOS)}


def cores_series(m: str | None = None) -> dict[str, str]:
    m = m or modo()
    cores = {nome: SLOTS[m][i] for i, nome in enumerate(ORDEM_SERIES)}
    cores["total"] = CHROME[m]["muted"]  # total é o agregado: de-ênfase, não um slot
    return cores


def escala_sequencial(m: str | None = None, hue: str = "azul") -> list[str]:
    """Baixo recua para a superfície: claro->escuro no modo claro, escuro->claro no escuro."""
    m = m or modo()
    rampa = RAMPA_AZUL if hue == "azul" else RAMPA_LARANJA
    return list(rampa) if m == "light" else list(reversed(rampa))


def layout(
    fig: go.Figure,
    titulo: str | None = None,
    y: str | None = None,
    x: str | None = None,
    hover: str = "x unified",
    altura: int = 380,
    legenda: bool = True,
    m: str | None = None,
) -> go.Figure:
    """Aplica o layout comum: fundo transparente, grade hairline, legenda no topo, um eixo."""
    m = m or modo()
    c = CHROME[m]
    fig.update_layout(
        template="none",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=13, color=c["text"]),
        title=dict(text=titulo, x=0, xanchor="left", font=dict(size=15, color=c["text"])) if titulo else None,
        hovermode=hover,
        hoverlabel=dict(bgcolor=c["surface"], font=dict(color=c["text"]), bordercolor=c["axis"]),
        margin=dict(l=56, r=20, t=64 if titulo else 32, b=44),
        height=altura,
        showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=c["text2"]), title=None),
        bargap=0.35,
        bargroupgap=0.08,
        separators=separadores_plotly(),
    )
    eixos = dict(
        gridcolor=c["grid"],
        gridwidth=1,
        zeroline=False,
        linecolor=c["axis"],
        linewidth=1,
        tickfont=dict(color=c["muted"]),
        title_font=dict(color=c["text2"]),
        showline=True,
    )
    fig.update_xaxes(**eixos, title_text=x)
    fig.update_yaxes(**eixos, title_text=y)
    return fig


def mostrar(fig: go.Figure, key: str | None = None) -> None:
    """Renderiza com o tema do próprio gráfico (cores validadas), largura total."""
    st.plotly_chart(fig, theme=None, width="stretch", key=key, config={"displaylogo": False})
