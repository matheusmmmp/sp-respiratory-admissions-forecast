"""Protocolo temporal — IMPLEMENTAÇÃO ÚNICA do projeto.

Nenhum modelo define o próprio conjunto de teste. Todos consomem os folds daqui,
e por construção avaliam EXATAMENTE os mesmos timestamps.

Dois protocolos:
  fixed_holdout  — um corte cronológico único (diagnóstico rápido)
  rolling_origin — janela expansiva, vários folds (protocolo preliminar real)

Dentro de cada fold de treino há um recorte FINAL cronológico para validação
interna (early stopping / seleção de hiperparâmetro). O teste nunca é validação.

Falha alto: fold vazio, sobreposição treino/teste, ordem invertida, validação
maior que o treino.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

__all__ = ["Fold", "fixed_holdout", "rolling_origin", "build_folds", "validar_folds"]


@dataclass(frozen=True)
class Fold:
    """Um fold. Todos os índices são DatetimeIndex de DATAS-ALVO."""

    id: int
    treino: pd.DatetimeIndex
    validacao: pd.DatetimeIndex
    teste: pd.DatetimeIndex

    def __post_init__(self) -> None:
        for nome, idx in (("treino", self.treino), ("validacao", self.validacao), ("teste", self.teste)):
            if len(idx) == 0:
                raise ValueError(f"fold {self.id}: partição '{nome}' vazia")
            if not idx.is_monotonic_increasing:
                raise ValueError(f"fold {self.id}: '{nome}' não está ordenada")

        if self.treino.intersection(self.teste).size:
            raise ValueError(f"fold {self.id}: sobreposição treino/teste")
        if self.validacao.intersection(self.teste).size:
            raise ValueError(f"fold {self.id}: sobreposição validacao/teste")
        if self.treino.intersection(self.validacao).size:
            raise ValueError(f"fold {self.id}: sobreposição treino/validacao")

        if self.treino.max() >= self.validacao.min():
            raise ValueError(f"fold {self.id}: treino não precede validacao")
        if self.validacao.max() >= self.teste.min():
            raise ValueError(f"fold {self.id}: validacao não precede teste")

    @property
    def treino_completo(self) -> pd.DatetimeIndex:
        """Treino + validação — para modelos que não precisam de validação interna."""
        return self.treino.union(self.validacao)

    def resumo(self) -> dict:
        return {
            "fold": self.id,
            "treino_inicio": self.treino.min().date().isoformat(),
            "treino_fim": self.treino.max().date().isoformat(),
            "n_treino": len(self.treino),
            "validacao_inicio": self.validacao.min().date().isoformat(),
            "validacao_fim": self.validacao.max().date().isoformat(),
            "n_validacao": len(self.validacao),
            "teste_inicio": self.teste.min().date().isoformat(),
            "teste_fim": self.teste.max().date().isoformat(),
            "n_teste": len(self.teste),
        }


def _fatiar_validacao(treino_bruto: pd.DatetimeIndex, dias_validacao: int) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    if dias_validacao <= 0:
        raise ValueError("dias_validacao deve ser > 0")
    if dias_validacao >= len(treino_bruto):
        raise ValueError(
            f"validação ({dias_validacao}d) >= treino disponível ({len(treino_bruto)}d)"
        )
    return treino_bruto[:-dias_validacao], treino_bruto[-dias_validacao:]


def fixed_holdout(
    datas: pd.DatetimeIndex, dias_teste: int, dias_validacao: int
) -> list[Fold]:
    """Um corte cronológico único no fim da série."""
    datas = pd.DatetimeIndex(datas).sort_values()
    if dias_teste <= 0:
        raise ValueError("dias_teste deve ser > 0")
    if dias_teste + dias_validacao >= len(datas):
        raise ValueError(
            f"teste ({dias_teste}) + validação ({dias_validacao}) >= série ({len(datas)})"
        )
    teste = datas[-dias_teste:]
    treino_bruto = datas[:-dias_teste]
    treino, validacao = _fatiar_validacao(treino_bruto, dias_validacao)
    return [Fold(id=1, treino=treino, validacao=validacao, teste=teste)]


def rolling_origin(
    datas: pd.DatetimeIndex,
    n_folds: int,
    dias_teste: int,
    dias_validacao: int,
    treino_minimo: int,
) -> list[Fold]:
    """Janela EXPANSIVA: cada fold treina em tudo que veio antes do seu teste.

    Os blocos de teste são contíguos e não se sobrepõem, cobrindo o final da
    série. Fold 1 testa o bloco mais antigo.
    """
    datas = pd.DatetimeIndex(datas).sort_values()
    if n_folds <= 0:
        raise ValueError("n_folds deve ser > 0")

    necessario = treino_minimo + dias_validacao + n_folds * dias_teste
    if necessario > len(datas):
        raise ValueError(
            f"série insuficiente: precisa de {necessario} dias "
            f"(treino_minimo {treino_minimo} + validação {dias_validacao} + "
            f"{n_folds} folds x {dias_teste}d), tem {len(datas)}"
        )

    inicio_testes = len(datas) - n_folds * dias_teste
    folds: list[Fold] = []
    for k in range(n_folds):
        ini = inicio_testes + k * dias_teste
        teste = datas[ini : ini + dias_teste]
        treino_bruto = datas[:ini]
        treino, validacao = _fatiar_validacao(treino_bruto, dias_validacao)
        folds.append(Fold(id=k + 1, treino=treino, validacao=validacao, teste=teste))
    return folds


def build_folds(datas: pd.DatetimeIndex, protocolo: str, **kwargs) -> list[Fold]:
    """Ponto de entrada único. `protocolo` vem da configuração do experimento."""
    if protocolo == "fixed_holdout":
        return fixed_holdout(
            datas,
            dias_teste=kwargs["dias_teste"],
            dias_validacao=kwargs["dias_validacao"],
        )
    if protocolo == "rolling_origin":
        return rolling_origin(
            datas,
            n_folds=kwargs["n_folds"],
            dias_teste=kwargs["dias_teste"],
            dias_validacao=kwargs["dias_validacao"],
            treino_minimo=kwargs["treino_minimo"],
        )
    raise ValueError(f"protocolo desconhecido: {protocolo!r}")


def validar_folds(folds: list[Fold]) -> None:
    """Checagens que valem para o conjunto, não para um fold isolado."""
    if not folds:
        raise ValueError("nenhum fold gerado")
    for a, b in zip(folds, folds[1:]):
        if a.teste.max() >= b.teste.min():
            raise ValueError(f"folds {a.id} e {b.id}: blocos de teste fora de ordem")
        if a.teste.intersection(b.teste).size:
            raise ValueError(f"folds {a.id} e {b.id}: blocos de teste sobrepostos")
