"""LSTM sequencial de verdade — correção do Problema A.

O `src/main.py` faz `reshape((n, 1, features))` e `LSTM(32, input_shape=(1, F))`
(linhas 406-415). Com timesteps=1 a recorrência não tem sobre o que recorrer:
é um modelo tabular vestindo uma camada LSTM. Esta implementação NÃO reaproveita
aquilo.

JANELA — a regra que impede vazamento
--------------------------------------
Para a data-alvo `u` e horizonte `h`, a origem é `t = u - h`. A janela cobre

    [t - lookback + 1  ..  t]

ou seja, termina em `t` e nunca alcança `u`. Os canais observados (internações,
meteorologia, PM2.5) entram com seus valores reais nesses dias.

Calendário é exceção legítima: `dow`, `mês`, `feriado` e os termos de Fourier de
`u` são conhecidos de antemão. Entram como canais CONSTANTES ao longo da janela,
carregando a informação da data-alvo. É a forma usual de covariável estática.

ESCALONAMENTO
-------------
`StandardScaler` ajustado SOMENTE no treino do fold, aplicado a treino,
validação e teste. O alvo também é escalado com estatísticas de treino, e as
previsões voltam à escala original antes de qualquer métrica.
"""
from __future__ import annotations

import os
import random

import numpy as np
import pandas as pd

from .base import Forecaster

__all__ = ["LSTMForecaster"]


def _semear(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    import tensorflow as tf

    tf.random.set_seed(seed)


def construir_janelas(
    frame_bruto: pd.DataFrame,
    canais: list[str],
    canais_calendario: list[str],
    datas_alvo: pd.DatetimeIndex,
    horizonte: int,
    lookback: int,
) -> np.ndarray:
    """(n_amostras, lookback, n_canais) — janelas terminando na origem.

    Exposta no nível do módulo para poder ser testada isoladamente.
    """
    if lookback < 2:
        raise ValueError(f"lookback deve ser >= 2 para haver sequência; recebido {lookback}")

    observados = [c for c in canais if c not in canais_calendario]
    do_calendario = [c for c in canais if c in canais_calendario]

    idx = frame_bruto.index
    pos = pd.Series(np.arange(len(idx)), index=idx)

    janelas = np.empty((len(datas_alvo), lookback, len(canais)), dtype=np.float32)
    mat_obs = frame_bruto[observados].to_numpy(dtype=np.float32) if observados else None
    mat_cal = frame_bruto[do_calendario].to_numpy(dtype=np.float32) if do_calendario else None

    for i, u in enumerate(datas_alvo):
        t = u - pd.Timedelta(days=horizonte)
        if t not in pos.index:
            raise RuntimeError(f"origem {t.date()} (alvo {u.date()}, h={horizonte}) fora do frame")
        p = int(pos.loc[t])
        ini = p - lookback + 1
        if ini < 0:
            raise RuntimeError(
                f"janela incompleta para o alvo {u.date()}: precisa de {lookback} dias "
                f"até {t.date()}, existem {p + 1}"
            )
        bloco = []
        if mat_obs is not None:
            bloco.append(mat_obs[ini : p + 1, :])
        if mat_cal is not None:
            # calendário da DATA-ALVO, repetido ao longo da janela
            pu = int(pos.loc[u])
            bloco.append(np.repeat(mat_cal[pu : pu + 1, :], lookback, axis=0))
        janelas[i] = np.concatenate(bloco, axis=1)

    if np.isnan(janelas).any():
        raise RuntimeError("janelas contêm NaN")
    return janelas


class LSTMForecaster(Forecaster):
    nome = "lstm"

    def __init__(
        self,
        lookback: int = 28,
        unidades: int = 32,
        dropout: float = 0.2,
        learning_rate: float = 1e-3,
        epocas: int = 150,
        batch_size: int = 32,
        paciencia: int = 15,
        seed: int = 42,
    ):
        self.lookback = int(lookback)
        self.unidades = int(unidades)
        self.dropout = float(dropout)
        self.learning_rate = float(learning_rate)
        self.epocas = int(epocas)
        self.batch_size = int(batch_size)
        self.paciencia = int(paciencia)
        self.seed = int(seed)
        self._modelo = None
        self._mu_x = self._sd_x = None
        self._mu_y = self._sd_y = None
        self._epocas_treinadas: int | None = None

    # ------------------------------------------------------------------ helpers
    def _janelas(self, ds, datas, canais):
        return construir_janelas(
            frame_bruto=ds.frame_bruto,
            canais=canais,
            canais_calendario=ds.canais_por_bloco["CAL"],
            datas_alvo=pd.DatetimeIndex(datas),
            horizonte=ds.horizonte,
            lookback=self.lookback,
        )

    def _escalar_x(self, X: np.ndarray) -> np.ndarray:
        return (X - self._mu_x) / self._sd_x

    # ---------------------------------------------------------------------- API
    def fit(self, ds, fold, colunas) -> None:
        _semear(self.seed)
        import tensorflow as tf

        canais = colunas  # para a LSTM, `colunas` já vem de ds.canais(blocos)

        Xtr = self._janelas(ds, fold.treino, canais)
        Xv = self._janelas(ds, fold.validacao, canais)
        ytr = ds.y.loc[fold.treino].to_numpy(dtype=np.float32)
        yv = ds.y.loc[fold.validacao].to_numpy(dtype=np.float32)

        # escalonamento ajustado SOMENTE no treino
        self._mu_x = Xtr.mean(axis=(0, 1), keepdims=True)
        self._sd_x = Xtr.std(axis=(0, 1), keepdims=True)
        self._sd_x[self._sd_x == 0] = 1.0
        self._mu_y = float(ytr.mean())
        self._sd_y = float(ytr.std()) or 1.0

        Xtr_s, Xv_s = self._escalar_x(Xtr), self._escalar_x(Xv)
        ytr_s = (ytr - self._mu_y) / self._sd_y
        yv_s = (yv - self._mu_y) / self._sd_y

        modelo = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(self.lookback, Xtr.shape[2])),
                tf.keras.layers.LSTM(self.unidades),
                tf.keras.layers.Dropout(self.dropout),
                tf.keras.layers.Dense(16, activation="relu"),
                tf.keras.layers.Dense(1),
            ]
        )
        modelo.compile(optimizer=tf.keras.optimizers.Adam(self.learning_rate), loss="mse")

        parada = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=self.paciencia, restore_best_weights=True
        )
        hist = modelo.fit(
            Xtr_s,
            ytr_s,
            # validação EXPLÍCITA do fold — nunca o teste, nunca validation_split
            validation_data=(Xv_s, yv_s),
            epochs=self.epocas,
            batch_size=self.batch_size,
            callbacks=[parada],
            verbose=0,
            shuffle=False,
        )
        self._modelo = modelo
        self._epocas_treinadas = len(hist.history["loss"])

    def predict(self, ds, fold, colunas) -> np.ndarray:
        if self._modelo is None:
            raise RuntimeError("predict chamado antes de fit")
        Xte = self._escalar_x(self._janelas(ds, fold.teste, colunas))
        pred_s = self._modelo.predict(Xte, verbose=0).reshape(-1)
        return pred_s * self._sd_y + self._mu_y   # volta à escala de internações

    def params(self) -> dict:
        return {
            "lookback": self.lookback,
            "unidades": self.unidades,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "epocas_max": self.epocas,
            "epocas_treinadas": self._epocas_treinadas,
            "batch_size": self.batch_size,
            "paciencia": self.paciencia,
            "seed": self.seed,
        }
