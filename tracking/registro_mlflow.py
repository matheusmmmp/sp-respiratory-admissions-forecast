"""Registro ao vivo de uma execução do runner no MLflow (opção ``--mlflow`` de ``run_preliminary``).

Este módulo **só registra**: nenhuma métrica é calculada aqui, nenhum modelo é treinado de novo e
nenhuma decisão do benchmark passa por ele. O runner chama três ganchos finos, e só quando a
opção ``--mlflow`` está ligada (sem ela, nem este módulo nem o pacote ``mlflow`` são importados):

* :func:`iniciar` — depois de o RUN_ID existir e antes do primeiro modelo: cria a run **mãe**;
* :meth:`RegistroMLflow.registrar_modelo` — logo depois de cada ``predict`` validado: salva **um
  modelo por (modelo, conjunto, fold, semente)** como LoggedModel do MLflow 3, ligado à run
  **filha** do par (modelo, conjunto), criada na primeira vez que o par aparece;
* :meth:`RegistroMLflow.finalizar` — depois de o runner gravar todos os artefatos: métricas das
  filhas, datasets e artefatos da mãe, status final.

Uso::

    uv run python -m src.experiments.run_preliminary --config configs/smoke_mlflow.yaml --smoke \\
        --mlflow --mlflow-uri sqlite:///mlruns/mlflow.db [--mlflow-experimento NOME]

Sem ``--mlflow-uri`` vale a variável ``MLFLOW_TRACKING_URI``; sem nenhuma das duas o runner falha.
O experimento padrão é ``run.nome`` do config. Com backend ``sqlite:///<arquivo>.db`` e experimento
novo, os artefatos vão para ``<pasta do .db>/mlartifacts/`` (e não para ``./mlruns`` do diretório
corrente, o padrão do MLflow).

Organização no MLflow
---------------------
* **Run mãe** (nome = RUN_ID do runner). Tags ``run_id``, ``commit``, ``git_sujo``, ``modo``,
  ``status``, ``horizonte``, ``alvo``, ``provisorio=true``, ``config_sha256`` (mais ``branch``);
  params = o config achatado (o mesmo de ``config.json``) e, sob ``efetivo.*``, o protocolo
  realmente aplicado (folds, sementes, conjuntos, modelos ativos — difere do config em ``--smoke``);
  datasets de entrada = os arquivos do manifesto (``dataset_sih``, ``dataset_cams``,
  ``dataset_cetesb``, ``dataset_meteo``). O MLflow limita o ``digest`` de um dataset a 36
  caracteres; o digest registrado é o **prefixo de 36 caracteres do sha256 do manifesto**, e o sha256
  completo vai no ``profile`` do dataset e na tag de entrada ``sha256``. Ao fim, a pasta inteira da
  run (``config.json``, ``manifest.json``, ``metrics.json``, ``summary.md``, CSVs, ``figures/``…) é
  anexada como artefato, mais ``modelos_registrados.json`` (índice dos LoggedModels).
* **Runs filhas** (``mlflow.parentRunId`` = mãe), uma por par (modelo, feature_set) do
  ``metrics.json`` — os baselines aparecem como ``feature_set = baseline``, como no runner. Params:
  ``experimento.*``, ``split.*`` e ``modelo.*`` efetivos, ``feature_set.blocos``. Métricas **lidas dos
  mesmos objetos que o runner grava em metrics.json** (a lista ``por_fold`` e
  ``agg.to_dict(orient="records")``), com os mesmos nomes: as agregadas (``MAE_medio``,
  ``MASE_medio``…) com ``step=0`` e as por fold como ``por_fold/seed<semente>/<métrica>`` com
  ``step=fold`` (a mesma convenção de ``tracking/importar_runs.py``; o prefixo da semente evita que
  duas sementes do mesmo fold colidam no mesmo passo). NaN do ``metrics.json`` entra como NaN e é
  listado na tag ``metricas_nan``.
* **LoggedModels**: um por (modelo, conjunto, fold, semente) efetivamente treinado/previsto, com
  ``source_run_id`` = filha, tags ``fold``, ``semente``, ``modelo``, ``feature_set``, ``run_id`` (mais
  ``entrada`` e ``formato_nativo``), assinatura e exemplo de entrada. **O exemplo de entrada de cada
  modelo é exatamente a entrada que reproduz as previsões daquele fold e semente gravadas em
  ``predictions.csv``** — o modelo e o exemplo bastam para conferir, sem o repositório de dados.

Como cada modelo é salvo, e qual é a entrada
--------------------------------------------
``h`` = horizonte; ``teste`` = datas-alvo do fold; ``janela de ajuste`` = ``fold.treino_completo``.
Datas sempre como texto ``AAAA-MM-DD`` (coluna ``data``); a coluna booleana ``prever`` marca as
linhas a prever (as demais são contexto). Colunas inteiras vão como int64, as demais como float64 —
os valores são os do dataset, sem transformação. A saída é um vetor float64 alinhado às linhas
``prever``, na ordem.

* **xgboost** — flavor nativo ``mlflow.xgboost`` (``XGBRegressor`` em formato ``ubj``, com a
  iteração de parada antecipada). Entrada: as colunas de features do conjunto nas datas de teste
  (``ds.X.loc[teste, colunas]``), uma linha por data, nomes das colunas = features.
* **lstm** — ``mlflow.pyfunc`` (``PrevisorDoFold``) com a rede Keras salva pelo flavor nativo
  ``mlflow.keras`` dentro de ``artifacts/rede_keras`` (carregável sozinha com
  ``mlflow.keras.load_model``). O flavor nativo sozinho não serve: a rede recebe janelas já
  padronizadas e devolve o alvo padronizado; a padronização ajustada no treino do fold fica no
  wrapper. Entrada: o frame diário bruto (``ds.frame_bruto``) com os canais do conjunto, de
  ``min(teste) − h − lookback + 1`` a ``max(teste)``; o wrapper monta as janelas com a mesma função
  do modelo (``construir_janelas``), aplica a escala do treino e desfaz a escala na saída.
* **sarimax** — ``mlflow.pyfunc`` com o resultado ajustado do statsmodels salvo pelo flavor nativo
  ``mlflow.statsmodels`` em ``artifacts/resultado_statsmodels``. O ``predict`` do flavor não serve:
  a previsão um passo à frente reaplica o modelo congelado à série inteira (``apply(refit=False)``)
  com as exógenas padronizadas pela janela de ajuste. Entrada: a janela de ajuste (contexto) + as
  datas de teste, com ``y`` observado e as exógenas do conjunto (sem o bloco excluído).
* **gam_nb** — como o SARIMAX (resultado ``GLMGam`` no flavor ``mlflow.statsmodels``; desenho,
  indicadoras e truncamento ao suporte dos splines ficam no wrapper). Mesma entrada.
* **ingarch_nb** — ``mlflow.pyfunc`` (implementação própria em numpy/scipy; não há flavor nativo).
  Mesma entrada do SARIMAX; a recursão de ν continua a partir do estado do fim do treino.
* **naive / seasonal_naive** — ``mlflow.pyfunc`` (sem flavor nativo; não há parâmetros). Entrada:
  ``y`` observado de ``min(teste) − defasagem`` a ``max(teste)`` (defasagem = h no Naïve,
  ``m·⌈h/m⌉`` no Seasonal).

Em todas as séries, ``y`` de uma data de teste só entra como informação até a origem ``u − h``; o
valor da própria data ``u`` nunca é usado para prevê-la (é o mesmo código de ``predict`` do modelo,
executado sobre um dataset montado a partir da entrada).

Carregar os modelos exige o repositório no ``sys.path`` (os wrappers pyfunc referenciam
``tracking.registro_mlflow`` e ``src.models``)::

    import mlflow
    m = mlflow.pyfunc.load_model("models:/<model_id>")
    local = mlflow.artifacts.download_artifacts("models:/<model_id>")
    entrada = mlflow.models.Model.load(local).load_input_example(local)
    m.predict(entrada)   # == y_pred do predictions.csv daquele (modelo, conjunto, fold, semente)

Desvio observado ao recarregar (``configs/smoke_mlflow.yaml`` e a config do teste, CPU, Windows,
2026-11-26): **zero em todos os modelos, LSTM inclusive** (comparação contra ``predictions.csv`` lido
com ``float_precision="round_trip"``; o leitor padrão do pandas erra o último dígito em ~1e-14). O
teste aceita até 1e-9 (LSTM: 1e-6). Os wrappers pyfunc são serializados com cloudpickle: carregue só
modelos de origem confiável. Custo: o exemplo de entrada de SARIMAX, GAM-NB e INGARCH-NB leva a
janela de ajuste inteira (numa run ``--full``, ~2.000 linhas × colunas do conjunto), porque é ela que
reproduz a previsão.

Garantias de não interferência
------------------------------
* Nada é escrito na pasta da run; o runner gera os mesmos bytes com e sem ``--mlflow``
  (``tests/test_runner_mlflow.py`` compara).
* Cada gancho salva e restaura o estado dos geradores ``random`` e ``numpy.random`` globais; o
  modelo salvo é uma cópia rasa do forecaster (o original não é tocado); nenhum modelo é recarregado
  durante a run (a validação do exemplo de entrada pelo MLflow, que recarrega o modelo, é desligada,
  e os requisitos pip são declarados em vez de inferidos num subprocesso).
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import math
import os
import random
import tempfile
import warnings
from contextlib import contextmanager
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import numpy as np
import pandas as pd

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
# Os requisitos de cada modelo são declarados (versões instaladas); sem isto o MLflow 3 copiaria o
# uv.lock e o pyproject.toml do repositório para dentro de CADA modelo salvo.
os.environ.setdefault("MLFLOW_LOG_UV_FILES", "false")

import mlflow  # noqa: E402
import mlflow.pyfunc  # noqa: E402
from mlflow import MlflowClient  # noqa: E402
from mlflow.entities import Dataset, DatasetInput, InputTag, Metric, Param, RunTag  # noqa: E402

from tracking.importar_runs import _achatar, chave_por_fold  # noqa: E402

__all__ = [
    "PrevisorDoFold",
    "RegistroMLflow",
    "abortar_ativo",
    "alvo_do_config",
    "entrada_do_modelo",
    "iniciar",
]

#: Colunas de controle da entrada dos wrappers pyfunc.
COL_DATA = "data"
COL_PREVER = "prever"
COL_Y = "y"
#: Identificadores (não métricas) nas linhas de ``por_fold`` e ``agregado`` do metrics.json.
_ID_FOLD = {"model", "feature_set", "seed", "fold", "teste_inicio", "teste_fim"}
_ID_AGREGADO = {"model", "feature_set"}
#: Modelos cuja entrada é a série (janela de ajuste + teste).
MODELOS_SERIE = ("sarimax", "gam_nb", "ingarch_nb")
MODELOS_BASELINE = ("naive", "seasonal_naive")

_ATIVO: RegistroMLflow | None = None


# ---------------------------------------------------------------------------------- utilidades
#: Loggers do MLflow silenciados (nível ERROR) só durante o salvamento de cada modelo: avisos
#: repetidos a cada um dos N modelos (cloudpickle do pyfunc, versão do pip ausente no venv do uv,
#: assinatura da rede Keras aninhada), já tratados ou documentados neste módulo.
_LOGGERS_RUIDOSOS = (
    "mlflow.pyfunc",
    "mlflow.utils.environment",
    "mlflow.utils.uv_utils",
    "mlflow.keras.save",
    "mlflow.models.model",
)


@contextmanager
def _silencio_mlflow():
    niveis = {n: logging.getLogger(n).level for n in _LOGGERS_RUIDOSOS}
    try:
        for n in niveis:
            logging.getLogger(n).setLevel(logging.ERROR)
        with warnings.catch_warnings():
            # "Hint: Inferred schema contains integer column(s)": as colunas inteiras (dow, mes,
            # feriado...) nunca têm faltantes — o construtor de features falha alto antes.
            warnings.filterwarnings("ignore", message=".*Inferred schema contains integer column.*")
            yield
    finally:
        for n, nivel in niveis.items():
            logging.getLogger(n).setLevel(nivel)


@contextmanager
def _rng_preservado():
    """Restaura ``random`` e ``numpy.random`` globais ao sair: registrar não consome sorteios."""
    estado_py = random.getstate()
    estado_np = np.random.get_state()
    try:
        yield
    finally:
        random.setstate(estado_py)
        np.random.set_state(estado_np)


def _versao(pacote: str) -> str | None:
    try:
        return metadata.version(pacote)
    except metadata.PackageNotFoundError:
        return None


def _requisitos(*pacotes: str) -> list[str]:
    """Requisitos pip fixados nas versões instaladas (evita a inferência por subprocesso do MLflow)."""
    base = ("mlflow", "numpy", "pandas", "cloudpickle")
    saida = []
    for p in (*base, *pacotes):
        v = _versao(p)
        if v and not any(s.startswith(f"{p}==") for s in saida):
            saida.append(f"{p}=={v}")
    return saida


def _bool(valor: Any) -> str:
    return "true" if bool(valor) else "false"


def alvo_do_config(cfg: dict) -> str:
    """``"urgencia"`` ou ``"total"`` — a mesma regra de ``tracking.importar_runs.alvo_da_run``."""
    dados = cfg.get("dados", {})
    sih = str(dados.get("sih", ""))
    alvo = dados.get("alvo")
    carater = alvo.get("carater_internacao") if isinstance(alvo, dict) else None
    por_carater = carater == "nao_eletivo"
    por_arquivo = sih.replace("\\", "/").endswith("_urgencia.parquet")
    if por_carater != por_arquivo:
        raise ValueError(f"alvo ambíguo — dados.alvo.carater_internacao={carater!r} mas dados.sih={sih!r}")
    return "urgencia" if por_carater else "total"


def _caminho_sqlite(uri: str) -> Path | None:
    """``sqlite:///C:/x/mlflow.db`` -> ``C:/x/mlflow.db``; ``sqlite:////tmp/x.db`` -> ``/tmp/x.db``."""
    if not uri.startswith("sqlite:///"):
        return None
    return Path(unquote(uri[len("sqlite:///") :].split("?", 1)[0]))


def _params_achatados(valor: Any, prefixo: str) -> dict[str, str]:
    saida: dict[str, str] = {}
    _achatar(json.loads(json.dumps(valor, default=str)), prefixo, saida)
    return saida


def _em_lotes(itens: list, tamanho: int):
    for i in range(0, len(itens), tamanho):
        yield itens[i : i + tamanho]


def _numero(valor: Any) -> bool:
    return isinstance(valor, (int, float, np.integer, np.floating)) and not isinstance(valor, (bool, np.bool_))


def _normalizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Inteiros -> int64, booleanos ficam, o resto -> float64 (tipos estáveis no JSON do exemplo)."""
    out = {}
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_bool_dtype(s):
            out[c] = s.astype(bool)
        elif pd.api.types.is_integer_dtype(s):
            out[c] = s.astype("int64")
        else:
            out[c] = s.astype("float64")
    res = pd.DataFrame(out, index=df.index)
    # Index de colunas `object`: o MLflow 3.18 compara `df.columns == range(n)` ao salvar o
    # exemplo, o que o Index de strings do pandas 3 não implementa.
    res.columns = pd.Index([str(c) for c in res.columns], dtype=object)
    return res


class _FlavorSemValidacao:
    """Um flavor visto por ``Model.log`` sem o kwarg ``validate_serving_input``.

    ``Model.log`` lê ``validate_serving_input`` dos kwargs (``False`` = não recarregar o modelo para
    validar o exemplo de entrada durante a run), mas os repassa ao ``save_model`` do flavor, e o do
    pyfunc (e o do xgboost, que os passa ao ``XGBModel.save_model``) rejeita kwargs desconhecidos.
    Este adaptador só remove o kwarg; o MLmodel gravado é o do flavor, sem diferença.
    """

    def __init__(self, modulo):
        self._modulo = modulo
        self.__name__ = modulo.__name__

    def save_model(self, *args, validate_serving_input=None, **kwargs):
        return self._modulo.save_model(*args, **kwargs)


def _assinatura_rede(forecaster, canais: list[str]):
    """Assinatura da rede Keras aninhada: janelas padronizadas -> alvo padronizado (float32)."""
    from mlflow.models.signature import ModelSignature
    from mlflow.types.schema import Schema, TensorSpec

    entrada = TensorSpec(np.dtype("float32"), (-1, int(forecaster.lookback), len(canais)), "janelas_padronizadas")
    saida = TensorSpec(np.dtype("float32"), (-1, 1), "alvo_padronizado")
    return ModelSignature(inputs=Schema([entrada]), outputs=Schema([saida]))


def _defasagem_baseline(nome_modelo: str, forecaster, horizonte: int) -> int:
    if nome_modelo == "naive":
        return int(horizonte)
    m = int(forecaster.periodo_sazonal)
    return m * int(np.ceil(horizonte / m))


# --------------------------------------------------------------------------- entrada dos modelos
def _frame_entrada(datas: pd.DatetimeIndex, prever: pd.DatetimeIndex, valores: pd.DataFrame) -> pd.DataFrame:
    for c in (COL_DATA, COL_PREVER):
        if c in valores.columns:
            raise ValueError(f"coluna de dados com nome reservado {c!r}")
    df = _normalizar_tipos(valores.loc[datas]).reset_index(drop=True)
    df.insert(0, COL_PREVER, np.asarray(datas.isin(prever), dtype=bool))
    df.insert(0, COL_DATA, [d.strftime("%Y-%m-%d") for d in datas])
    df.columns = pd.Index([str(c) for c in df.columns], dtype=object)
    return df


def entrada_do_modelo(nome_modelo: str, forecaster, ds, fold, colunas: list[str], lookback: int) -> pd.DataFrame:
    """A entrada que, dada ao modelo salvo, reproduz ``forecaster.predict(ds, fold, colunas)``.

    Ver a seção "Como cada modelo é salvo, e qual é a entrada" do docstring do módulo.
    """
    teste = pd.DatetimeIndex(fold.teste)
    h = int(ds.horizonte)
    if nome_modelo == "xgboost":
        return _normalizar_tipos(ds.X.loc[teste, list(colunas)]).reset_index(drop=True)
    if nome_modelo in MODELOS_BASELINE:
        defas = _defasagem_baseline(nome_modelo, forecaster, h)
        datas = (teste - pd.Timedelta(days=defas)).union(teste)
        serie = ds.serie_alvo_completa.rename(COL_Y).to_frame()
        return _frame_entrada(datas, teste, serie)
    if nome_modelo == "lstm":
        inicio = teste.min() - pd.Timedelta(days=h + int(lookback) - 1)
        idx = ds.frame_bruto.index
        datas = idx[(idx >= inicio) & (idx <= teste.max())]
        return _frame_entrada(pd.DatetimeIndex(datas), teste, ds.frame_bruto[list(colunas)])
    if nome_modelo in MODELOS_SERIE:
        datas = pd.DatetimeIndex(fold.treino_completo).append(teste)
        if COL_Y in colunas:
            raise ValueError(f"{nome_modelo}: feature com nome reservado {COL_Y!r}")
        valores = pd.concat([ds.y.rename(COL_Y), ds.X[list(colunas)]], axis=1)
        return _frame_entrada(datas, teste, valores)
    raise ValueError(f"modelo sem wrapper MLflow: {nome_modelo!r}")


@dataclass(frozen=True)
class _FoldDaEntrada:
    """O que os ``predict`` dos modelos leem de um fold: as datas de teste e a janela de ajuste."""

    teste: pd.DatetimeIndex
    treino_completo: pd.DatetimeIndex


class PrevisorDoFold(mlflow.pyfunc.PythonModel):
    """Wrapper pyfunc: o forecaster de UM fold e semente, já ajustado.

    ``predict`` monta, a partir da entrada, um ``DatasetExperimental`` e um fold mínimos e chama o
    próprio ``predict`` do forecaster — o mesmo código que gerou ``predictions.csv``. O objeto
    pesado com flavor nativo (rede Keras, resultado do statsmodels) fica em ``artifacts/`` e é
    reposto no forecaster em :meth:`load_context`.
    """

    def __init__(
        self,
        nome_modelo: str,
        forecaster,
        horizonte: int,
        colunas: list[str],
        canais_calendario: list[str] | None = None,
        artefato_nativo: str | None = None,
    ):
        self.nome_modelo = nome_modelo
        self.forecaster = forecaster
        self.horizonte = int(horizonte)
        self.colunas = list(colunas)
        self.canais_calendario = list(canais_calendario or [])
        self.artefato_nativo = artefato_nativo

    def load_context(self, context):
        if self.artefato_nativo == "rede_keras":
            import mlflow.keras as mlflow_keras

            self.forecaster._modelo = mlflow_keras.load_model(context.artifacts["rede_keras"])
        elif self.artefato_nativo == "resultado_statsmodels":
            import mlflow.statsmodels as mlflow_statsmodels

            self.forecaster._res = mlflow_statsmodels.load_model(context.artifacts["resultado_statsmodels"])

    def _dataset(self, df: pd.DataFrame):
        from src.features.forecasting_features import DatasetExperimental

        for c in (COL_DATA, COL_PREVER):
            if c not in df.columns:
                raise ValueError(f"{self.nome_modelo}: entrada sem a coluna {c!r}")
        datas = pd.DatetimeIndex(pd.to_datetime(df[COL_DATA].astype(str), format="%Y-%m-%d"), name="data")
        if datas.has_duplicates or not datas.is_monotonic_increasing:
            raise ValueError(f"{self.nome_modelo}: datas da entrada repetidas ou fora de ordem")
        prever = np.asarray(df[COL_PREVER], dtype=bool)
        if not prever.any():
            raise ValueError(f"{self.nome_modelo}: nenhuma linha com prever=True")
        valores = df.drop(columns=[COL_DATA, COL_PREVER]).set_axis(datas, axis=0)
        fold = _FoldDaEntrada(teste=datas[prever], treino_completo=datas[~prever])
        if self.nome_modelo == "lstm":
            faltando = [c for c in self.colunas if c not in valores.columns]
            if faltando:
                raise ValueError(f"lstm: entrada sem os canais {faltando}")
            ds = DatasetExperimental(
                X=pd.DataFrame(index=datas),
                y=pd.Series(np.nan, index=datas),
                horizonte=self.horizonte,
                colunas_por_bloco={},
                serie_alvo_completa=pd.Series(np.nan, index=datas),
                frame_bruto=valores[self.colunas],
                canais_por_bloco={"CAL": self.canais_calendario},
            )
            return ds, fold
        if COL_Y not in valores.columns:
            raise ValueError(f"{self.nome_modelo}: entrada sem a coluna {COL_Y!r}")
        faltando = [c for c in self.colunas if c not in valores.columns]
        if faltando:
            raise ValueError(f"{self.nome_modelo}: entrada sem as colunas {faltando}")
        y = valores[COL_Y].astype(float)
        ds = DatasetExperimental(
            X=valores[self.colunas],
            y=y,
            horizonte=self.horizonte,
            colunas_por_bloco={},
            serie_alvo_completa=y,
        )
        return ds, fold

    # `pd.DataFrame` como type hint: o MLflow não infere esquema dele (a assinatura de cada modelo é
    # declarada no salvamento) e não embrulha o predict com validação própria.
    def predict(self, context, model_input: pd.DataFrame, params: dict | None = None) -> np.ndarray:
        df = model_input if isinstance(model_input, pd.DataFrame) else pd.DataFrame(model_input)
        ds, fold = self._dataset(df.reset_index(drop=True))
        return np.asarray(self.forecaster.predict(ds, fold, self.colunas), dtype=float)


# --------------------------------------------------------------------------------- o registro
@dataclass
class RegistroMLflow:
    """Estado do registro de UMA execução do runner."""

    client: MlflowClient
    experimento_id: str
    mae_id: str
    run_id: str
    tags_comuns: dict[str, str]
    params_comuns: dict[str, str]
    modelos_cfg: dict[str, dict]
    feature_sets: dict[str, Any]
    filhas: dict[tuple[str, str], str] = field(default_factory=dict)
    modelos: list[dict] = field(default_factory=list)
    encerrado: bool = False

    # ------------------------------------------------------------------------- runs filhas
    def _filha(self, modelo: str, feature_set: str) -> str:
        chave = (modelo, feature_set)
        if chave in self.filhas:
            return self.filhas[chave]
        tags = {
            **self.tags_comuns,
            "mlflow.parentRunId": self.mae_id,
            "modelo": modelo,
            "feature_set": feature_set,
        }
        run = self.client.create_run(self.experimento_id, run_name=f"{modelo}__{feature_set}", tags=tags)
        rid = run.info.run_id
        params = dict(self.params_comuns)
        params.update(_params_achatados(self.modelos_cfg.get(modelo, {}), "modelo"))
        blocos = self.feature_sets.get(feature_set)
        if blocos is not None:
            params.update(_params_achatados(blocos, "feature_set.blocos"))
        for lote in _em_lotes([Param(k, v) for k, v in params.items()], 100):
            self.client.log_batch(rid, params=lote)
        self.filhas[chave] = rid
        return rid

    # ----------------------------------------------------------------------------- modelos
    def registrar_modelo(
        self, forecaster, nome_modelo: str, feature_set: str, fold, semente: int, ds, colunas: list[str], lookback: int
    ) -> str:
        """Salva o forecaster de (modelo, conjunto, fold, semente) como LoggedModel da filha."""
        with _rng_preservado(), _silencio_mlflow():
            return self._registrar_modelo(
                forecaster, nome_modelo, feature_set, fold, int(semente), ds, list(colunas), int(lookback)
            )

    def _registrar_modelo(self, forecaster, nome_modelo, feature_set, fold, semente, ds, colunas, lookback):
        from mlflow.models import Model
        from mlflow.models.signature import infer_signature

        filha = self._filha(nome_modelo, feature_set)
        entrada = entrada_do_modelo(nome_modelo, forecaster, ds, fold, colunas, lookback)
        # saída só para o esquema da assinatura (tipo/forma); o vetor real não é usado
        saida_exemplo = np.zeros(len(fold.teste), dtype=float)
        assinatura = infer_signature(entrada, saida_exemplo)
        nome = f"{nome_modelo}__{feature_set}__fold{fold.id}__seed{semente}"
        tags = {
            "run_id": self.run_id,
            "modelo": nome_modelo,
            "feature_set": feature_set,
            "fold": str(fold.id),
            "semente": str(semente),
            "provisorio": "true",
        }
        params = {
            f"ajuste.{k}": (str(v) if not isinstance(v, bool) else _bool(v))[:1000]
            for k, v in (forecaster.params() or {}).items()
            if v is None or isinstance(v, (str, int, float, bool, np.integer, np.floating))
        }
        comum = dict(
            artifact_path=None,
            name=nome,
            run_id=filha,
            signature=assinatura,
            input_example=entrada,
            validate_serving_input=False,
            tags=tags,
            params=params,
            step=int(fold.id),
        )

        with tempfile.TemporaryDirectory(prefix="mlflow_modelo_") as tmp:
            if nome_modelo == "xgboost":
                import mlflow.xgboost as mlflow_xgboost

                tags.update(entrada="features_do_teste", formato_nativo="mlflow.xgboost")
                info = Model.log(
                    flavor=_FlavorSemValidacao(mlflow_xgboost),
                    xgb_model=forecaster._modelo,
                    model_format="ubj",
                    pip_requirements=_requisitos("xgboost", "scikit-learn"),
                    **comum,
                )
            else:
                copia = copy.copy(forecaster)
                artefatos: dict[str, str] = {}
                nativo = None
                extras: tuple[str, ...] = ("scipy",)
                if nome_modelo == "lstm":
                    import mlflow.keras as mlflow_keras

                    nativo = "rede_keras"
                    destino = str(Path(tmp) / nativo)
                    mlflow_keras.save_model(
                        forecaster._modelo,
                        destino,
                        signature=_assinatura_rede(forecaster, colunas),
                        pip_requirements=_requisitos("tensorflow", "keras"),
                    )
                    artefatos[nativo] = destino
                    copia._modelo = None
                    extras = ("tensorflow", "keras")
                    tags.update(entrada="frame_diario_bruto", formato_nativo="mlflow.keras")
                elif nome_modelo in ("sarimax", "gam_nb"):
                    import mlflow.statsmodels as mlflow_statsmodels

                    nativo = "resultado_statsmodels"
                    destino = str(Path(tmp) / nativo)
                    mlflow_statsmodels.save_model(
                        forecaster._res, destino, pip_requirements=_requisitos("statsmodels", "scipy")
                    )
                    artefatos[nativo] = destino
                    copia._res = None
                    extras = ("statsmodels", "scipy", "patsy")
                    tags.update(entrada="serie_janela_de_ajuste_e_teste", formato_nativo="mlflow.statsmodels")
                elif nome_modelo == "ingarch_nb":
                    tags.update(entrada="serie_janela_de_ajuste_e_teste", formato_nativo="pyfunc (sem flavor)")
                elif nome_modelo in MODELOS_BASELINE:
                    tags.update(entrada="serie_do_alvo", formato_nativo="pyfunc (sem flavor)")
                else:
                    raise ValueError(f"modelo sem wrapper MLflow: {nome_modelo!r}")
                wrapper = PrevisorDoFold(
                    nome_modelo,
                    copia,
                    int(ds.horizonte),
                    colunas,
                    canais_calendario=list(ds.canais_por_bloco.get("CAL", [])) if nome_modelo == "lstm" else None,
                    artefato_nativo=nativo,
                )
                info = Model.log(
                    flavor=_FlavorSemValidacao(mlflow.pyfunc),
                    python_model=wrapper,
                    artifacts=artefatos or None,
                    pip_requirements=_requisitos(*extras),
                    **comum,
                )

        registro = {
            "model_id": info.model_id,
            "nome": nome,
            "modelo": nome_modelo,
            "feature_set": feature_set,
            "fold": int(fold.id),
            "semente": semente,
            "run_filha": filha,
            "formato_nativo": tags["formato_nativo"],
            "entrada": tags["entrada"],
        }
        self.modelos.append(registro)
        return info.model_id

    # ---------------------------------------------------------------------------- fim
    def finalizar(self, status: str, manifesto: dict, por_fold: list[dict], agregado: list[dict], saida: Path) -> None:
        """Métricas das filhas, datasets e artefatos da mãe, status final."""
        with _rng_preservado():
            self._finalizar(status, manifesto, por_fold, agregado, Path(saida))

    def _finalizar(self, status, manifesto, por_fold, agregado, saida):
        global _ATIVO
        c = self.client
        salvos = {(m["modelo"], m["feature_set"], m["fold"], m["semente"]) for m in self.modelos}
        esperados = {(str(r["model"]), str(r["feature_set"]), int(r["fold"]), int(r["seed"])) for r in por_fold}
        if salvos != esperados or len(self.modelos) != len(por_fold):
            raise RuntimeError(
                f"MLflow: {len(self.modelos)} modelos salvos para {len(por_fold)} linhas de por_fold; "
                f"diferença: {sorted(salvos ^ esperados)[:5]}"
            )
        linhas_fold: dict[tuple[str, str], list[dict]] = {}
        for linha in por_fold:
            linhas_fold.setdefault((str(linha["model"]), str(linha["feature_set"])), []).append(linha)

        for linha in agregado:
            par = (str(linha["model"]), str(linha["feature_set"]))
            rid = self._filha(*par)
            metricas = [
                Metric(key=str(k), value=float(v), timestamp=0, step=0)
                for k, v in linha.items()
                if k not in _ID_AGREGADO and _numero(v)
            ]
            for lf in linhas_fold.get(par, []):
                for k, v in lf.items():
                    if k in _ID_FOLD or not _numero(v):
                        continue
                    metricas.append(
                        Metric(
                            key=chave_por_fold(str(k), int(lf["seed"])),
                            value=float(v),
                            timestamp=0,
                            step=int(lf["fold"]),
                        )
                    )
            nan = sorted({m.key for m in metricas if math.isnan(m.value) and m.step == 0})
            tags = [RunTag("status", str(status))]
            if nan:
                tags.append(RunTag("metricas_nan", ",".join(nan)))
            for lote in _em_lotes(metricas, 900):
                c.log_batch(rid, metrics=lote)
            c.log_batch(rid, tags=tags)

        # datasets de entrada, com o sha256 já calculado pelo manifesto
        entradas = []
        for chave in ("dataset_sih", "dataset_cams", "dataset_cetesb", "dataset_meteo"):
            caminho, sha = manifesto.get(chave), manifesto.get(f"{chave}_sha256")
            if not caminho or not sha:
                continue
            ds = Dataset(
                name=chave.removeprefix("dataset_"),
                digest=str(sha)[:36],
                source_type="local",
                source=json.dumps({"uri": str(caminho)}),
                profile=json.dumps({"sha256": sha, "caminho": str(caminho)}),
            )
            entradas.append(
                DatasetInput(ds, tags=[InputTag("mlflow.data.context", "entrada"), InputTag("sha256", str(sha))])
            )
        if entradas:
            c.log_inputs(self.mae_id, datasets=entradas)

        c.log_artifacts(self.mae_id, str(saida))
        c.log_dict(
            self.mae_id,
            {"run_id": self.run_id, "n_modelos": len(self.modelos), "modelos": self.modelos},
            "modelos_registrados.json",
        )
        c.log_batch(
            self.mae_id, tags=[RunTag("status", str(status)), RunTag("n_modelos_salvos", str(len(self.modelos)))]
        )
        for rid in self.filhas.values():
            c.set_terminated(rid, "FINISHED")
        c.set_terminated(self.mae_id, "FINISHED")
        self.encerrado = True
        if _ATIVO is self:
            _ATIVO = None

    def abortar(self) -> None:
        """Marca mãe e filhas como FAILED (chamado pelo runner quando a execução levanta)."""
        global _ATIVO
        if self.encerrado:
            return
        with _rng_preservado():
            try:
                self.client.set_tag(self.mae_id, "status", "FALHOU")
                for rid in self.filhas.values():
                    self.client.set_terminated(rid, "FAILED")
                self.client.set_terminated(self.mae_id, "FAILED")
            finally:
                self.encerrado = True
                if _ATIVO is self:
                    _ATIVO = None


def abortar_ativo() -> None:
    """Encerra como FAILED o registro em andamento, se houver."""
    if _ATIVO is not None:
        _ATIVO.abortar()


def _experimento(client: MlflowClient, nome: str, uri: str) -> str:
    exp = client.get_experiment_by_name(nome)
    if exp is not None:
        if exp.lifecycle_stage != "active":
            raise RuntimeError(
                f"experimento MLflow '{nome}' está '{exp.lifecycle_stage}'; restaure-o ou use outro nome"
            )
        return exp.experiment_id
    local = None
    db = _caminho_sqlite(uri)
    if db is not None:
        local = (db.resolve().parent / "mlartifacts").as_uri()
    return client.create_experiment(
        nome, artifact_location=local, tags={"projeto": "sp-respiratory-admissions-forecast", "provisorio": "true"}
    )


def iniciar(
    opcoes: dict,
    *,
    run_id: str,
    modo: str,
    cfg: dict,
    caminho_config: Path,
    proveniencia: dict,
    split: dict,
    modelos: dict,
    feature_sets: dict,
    sementes: list[int],
    ativos: list[str],
) -> RegistroMLflow:
    """Cria a run mãe. ``opcoes`` = ``{"uri": ..., "experimento": ...}`` vindo da CLI do runner."""
    global _ATIVO
    with _rng_preservado():
        uri = opcoes.get("uri") or os.environ.get("MLFLOW_TRACKING_URI")
        if not uri:
            raise RuntimeError("--mlflow exige --mlflow-uri ou a variável MLFLOW_TRACKING_URI")
        nome_exp = opcoes.get("experimento") or str(cfg["run"]["nome"])
        mlflow.set_tracking_uri(uri)
        client = MlflowClient(uri)
        exp_id = _experimento(client, nome_exp, uri)
        mlflow.set_experiment(experiment_id=exp_id)

        exp = cfg["experimento"]
        tags_comuns = {
            "run_id": run_id,
            "commit": str(proveniencia.get("git_commit_no_inicio")),
            "git_sujo": _bool(proveniencia.get("git_sujo_no_inicio")),
            "modo": modo,
            "horizonte": str(int(exp["horizonte"])),
            "alvo": alvo_do_config(cfg),
            "provisorio": "true",
        }
        tags_mae = {
            **tags_comuns,
            "config_sha256": hashlib.sha256(Path(caminho_config).read_bytes()).hexdigest(),
            "branch": str(proveniencia.get("git_branch_no_inicio")),
            "status": "EM_EXECUCAO",
            "mlflow.note.content": (
                f"Registro ao vivo do runner (run {run_id}, modo {modo}). Provisório: números de "
                f"smoke/triagem nunca são resultado."
            ),
        }
        mae = client.create_run(exp_id, run_name=run_id, tags=tags_mae)
        mae_id = mae.info.run_id

        params_mae = _params_achatados(cfg, "")
        params_mae.update(_params_achatados(split, "efetivo.split"))
        params_mae.update(_params_achatados(sementes, "efetivo.sementes"))
        params_mae.update(_params_achatados(list(feature_sets), "efetivo.feature_sets"))
        params_mae.update(_params_achatados(ativos, "efetivo.modelos"))
        for lote in _em_lotes([Param(k, v[:6000]) for k, v in params_mae.items()], 100):
            client.log_batch(mae_id, params=lote)

        params_comuns = _params_achatados(exp, "experimento")
        params_comuns.update(_params_achatados(split, "split"))
        reg = RegistroMLflow(
            client=client,
            experimento_id=exp_id,
            mae_id=mae_id,
            run_id=run_id,
            tags_comuns=tags_comuns,
            params_comuns=params_comuns,
            modelos_cfg={k: dict(v) for k, v in modelos.items()},
            feature_sets=dict(feature_sets),
        )
        _ATIVO = reg
        print(f"MLflow: experimento '{nome_exp}' ({exp_id}), run mãe {mae_id} em {uri}", flush=True)
        return reg
