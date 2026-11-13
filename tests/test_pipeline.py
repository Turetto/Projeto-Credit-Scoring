import numpy as np
import pandas as pd

from credit_scoring.data.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from credit_scoring.monitoring import policy
from credit_scoring.pipeline import medir_drift


def _lote(n: int, rng: np.random.Generator, deslocamento: float = 0.0) -> pd.DataFrame:
    df = pd.DataFrame({c: rng.normal(size=n) + deslocamento for c in [*NUMERIC_FEATURES, "SCORE"]})
    for c in policy.VARIAVEIS_NOMINAIS:
        df[c] = 100 + df[c]  # valores monetários positivos; +1,0 ≈ +1% na mediana
    for c in CATEGORICAL_FEATURES:
        df[c] = rng.choice(["A", "B", "C"], n)
    return df


def test_sem_deslocamento_fica_estavel():
    rng = np.random.default_rng(0)
    r = medir_drift(_lote(20_000, rng), _lote(4_000, rng))
    assert r["status_drift"] == "ESTÁVEL"
    assert r["features_alerta"] == []


def test_deslocamento_forte_gera_alerta_e_separa_score():
    rng = np.random.default_rng(0)
    r = medir_drift(_lote(20_000, rng), _lote(4_000, rng, deslocamento=1.0))
    assert r["status_drift"] == "ALERTA"
    assert "AGE_YEARS" in r["features_alerta"]
    assert "SCORE" not in r["features_alerta"]


def test_mudanca_nominal_imaterial_nao_alerta():
    rng = np.random.default_rng(0)
    r = medir_drift(_lote(20_000, rng), _lote(4_000, rng, deslocamento=1.0))
    # +1% na mediana das variáveis monetárias: PSI alto, mas abaixo da materialidade de 5%
    assert set(policy.VARIAVEIS_NOMINAIS) <= set(r["imateriais"])
    assert not set(policy.VARIAVEIS_NOMINAIS) & set(r["features_alerta"])
