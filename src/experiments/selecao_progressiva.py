"""Seleção progressiva de blocos dentro do fold — PROTOCOLO §0.24, Fase 2 [PROPOSTO].

Um conjunto de `feature_sets` pode ser, em vez de uma lista de blocos, uma especificação:

    SELECAO_METEO:
      selecao_progressiva:
        base: [AR, CAL]
        candidatos: [M_TMED, M_TMIN, M_TMAX, M_TAMP, M_UR, M_VV]
        modelos: [xgboost, sarimax]
        alfa: 0.05

Para cada fold do runner e cada modelo listado, o conjunto é escolhido **sem tocar o teste do fold**:

  * fold interno: treino = `fold.treino` menos os últimos `len(fold.validacao)` dias; validação interna (early stopping) =
    esses dias; janela de escolha = `fold.validacao`;
  * forward: a cada passo, o candidato que mais reduz o MAE na janela de escolha entra se Δ < 0, o DM unilateral tiver
    p < `alfa` e, havendo mais de uma semente, o ganho médio por semente superar o desvio entre sementes. Senão, para.

O runner retreina o conjunto escolhido no fold externo e prevê o teste, como qualquer outro conjunto. Este módulo não
conhece modelos: recebe `prever(blocos, fold_interno, semente) -> ndarray` do runner.
"""
from __future__ import annotations

import numpy as np

from src.evaluation.splits import Fold
from src.experiments.teste_dm_v02 import dm

CHAVE = "selecao_progressiva"
MODELOS_SUPORTADOS = ("xgboost", "sarimax")


def eh_selecao(spec) -> bool:
    return isinstance(spec, dict) and CHAVE in spec


def validar_spec(nome_set: str, spec: dict, blocos_conhecidos, ativos) -> dict:
    """Normaliza e valida; qualquer chave desconhecida ou bloco inexistente falha alto."""
    if set(spec) != {CHAVE}:
        raise ValueError(f"feature_sets.{nome_set}: só a chave {CHAVE!r} é aceita; veio {sorted(spec)}")
    s = dict(spec[CHAVE])
    aceitas = {"base", "candidatos", "modelos", "alfa"}
    if set(s) - aceitas or not {"base", "candidatos", "modelos"} <= set(s):
        raise ValueError(f"feature_sets.{nome_set}.{CHAVE}: chaves {sorted(s)}; exigidas base, candidatos, modelos; "
                         f"opcional alfa")
    base, cand, mods = list(s["base"]), list(s["candidatos"]), list(s["modelos"])
    desconhecidos = sorted(set(base + cand) - set(blocos_conhecidos))
    if desconhecidos:
        raise ValueError(f"feature_sets.{nome_set}: blocos desconhecidos {desconhecidos}")
    if set(base) & set(cand) or len(set(cand)) != len(cand) or not cand:
        raise ValueError(f"feature_sets.{nome_set}: candidatos vazios, repetidos ou já na base")
    fora = sorted(set(mods) - set(MODELOS_SUPORTADOS))
    if fora:
        raise ValueError(f"feature_sets.{nome_set}: seleção não implementada para {fora}; aceitos {MODELOS_SUPORTADOS}")
    inativos = sorted(set(mods) - set(ativos))
    if inativos:
        raise ValueError(f"feature_sets.{nome_set}: modelos da seleção inativos na run: {inativos}")
    alfa = float(s.get("alfa", 0.05))
    if not 0 < alfa < 1:
        raise ValueError(f"feature_sets.{nome_set}: alfa {alfa} fora de (0, 1)")
    return {"base": base, "candidatos": cand, "modelos": mods, "alfa": alfa}


def fold_interno(fold: Fold) -> Fold:
    nv = len(fold.validacao)
    if len(fold.treino) <= nv:
        raise ValueError(f"fold {fold.id}: treino ({len(fold.treino)}) não comporta validação interna de {nv} dias")
    return Fold(id=fold.id, treino=fold.treino[:-nv], validacao=fold.treino[-nv:], teste=fold.validacao)


def p_unilateral(r: dict) -> float:
    """p do DM para H1: perda do candidato menor. Sem estatística definida → 1 (não aceita)."""
    if not np.isfinite(r.get("p", np.nan)) or not np.isfinite(r.get("DM", np.nan)):
        return 1.0
    return r["p"] / 2 if r["DM"] < 0 else 1 - r["p"] / 2


def selecionar(fold: Fold, spec: dict, sementes, prever, y_escolha: np.ndarray, h: int) -> dict:
    fi = fold_interno(fold)
    y_escolha = np.asarray(y_escolha, dtype=float)
    if len(y_escolha) != len(fi.teste):
        raise ValueError(f"fold {fold.id}: y da janela de escolha com {len(y_escolha)} datas, esperado {len(fi.teste)}")
    sementes = list(sementes)

    def avaliar(blocos):
        P = np.vstack([np.asarray(prever(list(blocos), fi, s), dtype=float) for s in sementes])
        if P.shape[1] != len(y_escolha) or np.isnan(P).any():
            raise RuntimeError(f"fold {fold.id} {blocos}: previsão interna inválida (forma {P.shape} ou NaN)")
        E = np.abs(P - y_escolha)
        return E.mean(axis=0), E.mean(axis=1)

    atual = list(spec["base"])
    perda, mae_s = avaliar(atual)
    passos, restantes = [], list(spec["candidatos"])
    while restantes:
        avals = []
        for c in restantes:
            perda_c, mae_s_c = avaliar(atual + [c])
            d = perda_c - perda
            r = dm(d, h)
            ganho = mae_s - mae_s_c
            ruido = float(np.std(ganho, ddof=1)) if len(ganho) > 1 else 0.0
            avals.append({"bloco": c, "MAE_escolha": float(perda_c.mean()), "d_medio": float(d.mean()),
                          "DM": r["DM"], "p_unilateral": float(p_unilateral(r)),
                          "ganho_medio_semente": float(ganho.mean()), "ruido_semente": ruido,
                          "_perda": perda_c, "_mae_s": mae_s_c})
        melhor = min(avals, key=lambda a: a["MAE_escolha"])
        motivo = []
        if not melhor["d_medio"] < 0:
            motivo.append("sem ganho")
        if not melhor["p_unilateral"] < spec["alfa"]:
            motivo.append(f"DM p={melhor['p_unilateral']:.3f} ≥ {spec['alfa']}")
        if len(sementes) > 1 and not melhor["ganho_medio_semente"] > melhor["ruido_semente"]:
            motivo.append("ganho ≤ ruído de semente")
        passos.append({"passo": len(passos) + 1, "conjunto_atual": list(atual), "MAE_escolha_atual": float(perda.mean()),
                       "candidatos": [{k: v for k, v in a.items() if not k.startswith("_")} for a in avals],
                       "melhor": melhor["bloco"], "aceito": not motivo, "motivo_parada": "; ".join(motivo) or None})
        if motivo:
            break
        atual.append(melhor["bloco"])
        restantes.remove(melhor["bloco"])
        perda, mae_s = melhor["_perda"], melhor["_mae_s"]
    return {"fold": fold.id, "blocos": atual, "acrescentados": atual[len(spec["base"]):], "sementes": sementes,
            "fold_interno": fi.resumo(), "passos": passos}
