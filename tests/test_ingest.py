import numpy as np
import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.data.ingest import split


def _fake(n: int = 10_000) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame({cfg.ID_COL: np.arange(n), cfg.TARGET: rng.binomial(1, 0.08, n)})


def test_split_sem_vazamento_de_ids():
    parts = split(_fake())
    ids = [set(p[cfg.ID_COL]) for p in parts]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
    assert sum(len(s) for s in ids) == 10_000


def test_split_preserva_taxa_de_default():
    taxas = [p[cfg.TARGET].mean() for p in split(_fake())]
    assert max(taxas) - min(taxas) < 0.005
