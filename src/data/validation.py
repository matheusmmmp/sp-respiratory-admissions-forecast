"""DATA QUALITY GATE — roda ANTES da modelagem e pode reprovar a run.

POR QUE ISTO É UM MÓDULO SEPARADO
---------------------------------
`construir_dataset` já levanta em várias condições ruins (data duplicada, buraco
na série, NaN no alvo). Mas ele levanta e morre: não deixa **registro** do que
foi verificado nem do que passou raspando. Uma run científica precisa provar
quais checagens correram e com que resultado, não só que não explodiu.

Este módulo produz um laudo estruturado (`data_quality.json`) com uma linha por
checagem. Nada aqui corrige dado. Detectar e relatar é o trabalho; consertar em
silêncio seria justamente o defeito que se quer evitar.

SEVERIDADE
----------
FAIL  — invalida a modelagem. O runner aborta.
WARN  — não invalida, mas precisa aparecer no relatório e ser lido.
PASS  — verificado e correto.

⚠️ OUTLIER NÃO É FAIL, E NÃO É REMOVIDO. Pico de internação respiratória é o
fenômeno de interesse, não sujeira. Marcamos e seguimos.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

__all__ = ["Checagem", "LaudoQualidade", "validar_serie_diaria"]

FAIL, WARN, PASS = "FAIL", "WARN", "PASS"


@dataclass
class Checagem:
    nome: str
    status: str
    detalhe: str
    dados: dict


@dataclass
class LaudoQualidade:
    checagens: list[Checagem]

    @property
    def reprovado(self) -> bool:
        return any(c.status == FAIL for c in self.checagens)

    @property
    def veredito(self) -> str:
        return "FAIL" if self.reprovado else "PASS"

    def por_status(self, status: str) -> list[Checagem]:
        return [c for c in self.checagens if c.status == status]

    def to_dict(self) -> dict:
        return {
            "veredito": self.veredito,
            "n_checagens": len(self.checagens),
            "n_fail": len(self.por_status(FAIL)),
            "n_warn": len(self.por_status(WARN)),
            "n_pass": len(self.por_status(PASS)),
            "checagens": [asdict(c) for c in self.checagens],
        }

    def imprimir(self) -> None:
        print("=" * 78)
        print("DATA QUALITY")
        print("=" * 78)
        for c in self.checagens:
            marca = {"FAIL": "FAIL", "WARN": "WARN", "PASS": " ok "}[c.status]
            print(f"  [{marca}] {c.nome:32s} {c.detalhe}")
        print(f"\nDATA QUALITY: {self.veredito}")


def _ck(nome, status, detalhe, **dados) -> Checagem:
    return Checagem(nome=nome, status=status, detalhe=detalhe, dados=dados)


def validar_serie_diaria(
    alvo: pd.Series,
    covariaveis: dict[str, pd.DataFrame] | None = None,
    inicio=None,
    fim=None,
    z_outlier: float = 5.0,
) -> LaudoQualidade:
    """Valida a série do desfecho e a cobertura das covariáveis.

    `alvo` deve vir indexado por data. `covariaveis` mapeia rótulo -> frame
    indexado por data, e serve para medir cobertura por fonte.
    """
    cks: list[Checagem] = []
    idx = pd.DatetimeIndex(alvo.index)

    # ------------------------------------------------------------------- datas
    cks.append(
        _ck("indice_e_data", PASS if isinstance(alvo.index, pd.DatetimeIndex) else FAIL,
            f"tipo={type(alvo.index).__name__}", tipo=type(alvo.index).__name__)
    )
    cks.append(
        _ck("datas_crescentes", PASS if idx.is_monotonic_increasing else FAIL,
            "ordenada" if idx.is_monotonic_increasing else "FORA DE ORDEM",
            monotonica=bool(idx.is_monotonic_increasing))
    )

    dups = idx[idx.duplicated()].unique()
    cks.append(
        _ck("datas_unicas", PASS if len(dups) == 0 else FAIL,
            "sem duplicadas" if len(dups) == 0 else f"{len(dups)} duplicadas, ex.: {[str(d.date()) for d in dups[:5]]}",
            n_duplicadas=int(len(dups)))
    )

    # ---------------------------------------------------------------- período
    esperado = pd.date_range(idx.min(), idx.max(), freq="D")
    buracos = esperado.difference(idx)
    cks.append(
        _ck("frequencia_diaria", PASS if len(buracos) == 0 else FAIL,
            f"{len(idx)} dias de {len(esperado)} esperados"
            + ("" if len(buracos) == 0 else f"; {len(buracos)} ausentes, ex.: {[str(d.date()) for d in buracos[:5]]}"),
            n_dias=int(len(idx)), n_esperados=int(len(esperado)),
            n_buracos=int(len(buracos)),
            buracos=[str(d.date()) for d in buracos[:50]])
    )

    detalhe_periodo = f"{idx.min().date()} a {idx.max().date()}"
    status_periodo = PASS
    if inicio is not None and idx.min() > pd.Timestamp(inicio):
        status_periodo = WARN
        detalhe_periodo += f" (começa depois do pedido {pd.Timestamp(inicio).date()})"
    if fim is not None and idx.max() < pd.Timestamp(fim):
        status_periodo = WARN
        detalhe_periodo += f" (termina antes do pedido {pd.Timestamp(fim).date()})"
    cks.append(
        _ck("periodo_coberto", status_periodo, detalhe_periodo,
            inicio=str(idx.min().date()), fim=str(idx.max().date()),
            pedido_inicio=str(inicio) if inicio else None,
            pedido_fim=str(fim) if fim else None)
    )

    # ------------------------------------------------------------------- alvo
    n_na = int(alvo.isna().sum())
    cks.append(
        _ck("alvo_sem_missing", PASS if n_na == 0 else FAIL,
            "sem NaN" if n_na == 0 else f"{n_na} NaN — zero NÃO é missing, investigue",
            n_nan=n_na)
    )

    finito = alvo.dropna()
    n_neg = int((finito < 0).sum())
    cks.append(
        _ck("alvo_nao_negativo", PASS if n_neg == 0 else FAIL,
            "todos >= 0" if n_neg == 0 else f"{n_neg} valores negativos",
            n_negativos=n_neg)
    )

    n_zero = int((finito == 0).sum())
    cks.append(
        _ck("alvo_zeros", PASS if n_zero == 0 else WARN,
            "nenhum dia com zero internações"
            if n_zero == 0
            else f"{n_zero} dias com zero — confirme se é real e não missing mascarado",
            n_zeros=n_zero)
    )

    # --------------------------------------------------------------- outliers
    mu, sd = float(finito.mean()), float(finito.std(ddof=1))
    z = (finito - mu) / sd if sd > 0 else finito * 0
    extremos = finito[np.abs(z) > z_outlier]
    cks.append(
        _ck("alvo_outliers", PASS if len(extremos) == 0 else WARN,
            f"{len(extremos)} dias com |z| > {z_outlier} (NÃO removidos: pico é o fenômeno)"
            + ("" if len(extremos) == 0 else f", ex.: {[str(d.date()) for d in extremos.index[:5]]}"),
            n_outliers=int(len(extremos)), z_limite=z_outlier,
            media=round(mu, 3), desvio=round(sd, 3),
            minimo=float(finito.min()), maximo=float(finito.max()),
            datas=[str(d.date()) for d in extremos.index[:50]])
    )

    # ------------------------------------------------- cobertura das covariáveis
    for rotulo, frame in (covariaveis or {}).items():
        fidx = pd.DatetimeIndex(frame.index)
        comum = idx.intersection(fidx)
        cobertura = len(comum) / len(idx) if len(idx) else 0.0
        nans = int(frame.reindex(idx).isna().sum().sum())
        status = PASS if cobertura == 1.0 and nans == 0 else (WARN if cobertura > 0 else FAIL)
        cks.append(
            _ck(f"cobertura_{rotulo}", status,
                f"{len(comum)}/{len(idx)} dias ({cobertura:.1%}), {nans} células NaN",
                n_dias_comuns=int(len(comum)), cobertura=round(cobertura, 6),
                n_celulas_nan=nans, colunas=list(frame.columns))
        )

    return LaudoQualidade(checagens=cks)
