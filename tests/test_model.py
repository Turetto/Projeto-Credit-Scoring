import numpy as np
import pandas as pd
import pytest

from credit_scoring.data.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from credit_scoring.model.train import build_models, ks


def _sintetico(n: int = 300, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({c: rng.normal(size=n) for c in NUMERIC_FEATURES})
    for c in CATEGORICAL_FEATURES:
        X[c] = rng.choice(["A", "B"], size=n)
    return X, pd.Series(rng.binomial(1, 0.3, n))


def test_ks_separacao_perfeita():
    estat, _ = ks(pd.Series([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.9]))
    assert estat == pytest.approx(1.0)


@pytest.mark.parametrize("nome", ["logreg", "xgboost"])
def test_pipeline_tolera_categoria_nova(nome):
    X, y = _sintetico()
    modelo = build_models()[nome].fit(X, y)
    X_novo = X.head(5).assign(**{CATEGORICAL_FEATURES[0]: "CATEGORIA_NUNCA_VISTA"})
    p = modelo.predict_proba(X_novo)[:, 1]
    assert np.all((p >= 0) & (p <= 1))
