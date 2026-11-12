import numpy as np
import pandas as pd

from credit_scoring.drift.attribution import avaliar


def test_ic_contem_estimativa_pontual():
    rng = np.random.default_rng(0)
    y = pd.Series(rng.binomial(1, 0.1, 2_000))
    p = pd.Series(np.clip(y * 0.3 + rng.uniform(0, 0.2, 2_000), 0, 1))
    r = avaliar(y, p, rng)
    assert r["auc_ic_inf"] <= r["auc"] <= r["auc_ic_sup"]
    assert r["gap_ic_inf"] <= r["gap"] <= r["gap_ic_sup"]
