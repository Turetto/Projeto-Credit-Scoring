"""PSI e KS próprios, para validar o Evidently (2.5)."""

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from scipy.stats import ks_2samp

EPS = 1e-4  # evita log(0) em bins vazios
MAX_CATEGORIAS = 10  # numéricas com poucos valores distintos são tratadas como categóricas


def eh_categorica(s: pd.Series) -> bool:
    return not is_numeric_dtype(s) or s.nunique() <= MAX_CATEGORIAS


def psi(ref: pd.Series, cur: pd.Series, bins: int = 10) -> float:
    """PSI com bins por quantis da referência (numéricas) ou por categoria."""
    ref, cur = ref.dropna(), cur.dropna()
    if eh_categorica(ref):
        p = ref.astype(str).value_counts(normalize=True)
        q = cur.astype(str).value_counts(normalize=True)
        idx = p.index.union(q.index)
        p = p.reindex(idx, fill_value=0).to_numpy()
        q = q.reindex(idx, fill_value=0).to_numpy()
    else:
        cortes = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)[1:-1]))
        k = len(cortes) + 1
        p = np.bincount(np.searchsorted(cortes, ref, side="right"), minlength=k) / len(ref)
        q = np.bincount(np.searchsorted(cortes, cur, side="right"), minlength=k) / len(cur)
    p, q = np.clip(p, EPS, None), np.clip(q, EPS, None)
    return float(np.sum((q - p) * np.log(q / p)))


def ks(ref: pd.Series, cur: pd.Series) -> tuple[float, float]:
    """Retorna (estatística D, p-valor)."""
    r = ks_2samp(ref.dropna(), cur.dropna())
    return float(r.statistic), float(r.pvalue)
