import numpy as np
import pandas as pd

from credit_scoring.data.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from credit_scoring.model.explain import ROTULOS, contribuicoes, motivos
from credit_scoring.model.train import build_models


def _sintetico(n: int = 300, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({c: rng.normal(size=n) for c in NUMERIC_FEATURES})
    for c in CATEGORICAL_FEATURES:
        X[c] = rng.choice(["A", "B"], size=n)
    return X, pd.Series(rng.binomial(1, 0.3, n))


def test_contribuicoes_somam_exatamente_a_previsao():
    X, y = _sintetico()
    modelo = build_models()["xgboost"].fit(X, y)
    p = 1 / (1 + np.exp(-contribuicoes(modelo, X).sum(axis=1)))
    np.testing.assert_allclose(p, modelo.predict_proba(X)[:, 1], atol=1e-4)


def test_motivos_listam_so_fatores_que_aumentam_o_risco():
    linha = pd.Series({"_base": -2.0, "AGE_YEARS": 0.5, "EXT_SOURCE_2": -0.3, "AMT_CREDIT": 0.1})
    assert motivos(linha) == [ROTULOS["AGE_YEARS"], ROTULOS["AMT_CREDIT"]]


def test_todo_fator_do_modelo_tem_rotulo_em_linguagem_simples():
    from credit_scoring.data.features import MODEL_FEATURES

    assert set(MODEL_FEATURES) <= set(ROTULOS)
