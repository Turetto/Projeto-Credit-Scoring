import pandas as pd
import pytest

from credit_scoring import config as cfg
from credit_scoring.drift.simulate import desemprego, inflacao


def test_controle_nao_altera_nada(make_batch, rng=None):
    import numpy as np

    df = make_batch(3).assign(TARGET=0)
    pd.testing.assert_frame_equal(inflacao(df, 0, 0), df)
    pd.testing.assert_series_equal(desemprego(df, 0, 0.2, np.random.default_rng(0)), df[cfg.TARGET])


def test_inflacao_com_repasse_parcial_e_choque_de_juros(make_batch):
    out = inflacao(make_batch(1), pi=0.10, rho=0.05)
    assert out.loc[0, "AMT_INCOME_TOTAL"] == pytest.approx(50_000 * 1.06)  # repasse de 60%
    assert out.loc[0, "AMT_CREDIT"] == pytest.approx(100_000 * 1.10)
    assert out.loc[0, "AMT_ANNUITY"] == pytest.approx(10_000 * 1.10 * 1.05)


def test_desemprego_so_afeta_assalariados_adimplentes(make_batch):
    import numpy as np

    df = make_batch(3).assign(TARGET=[0, 0, 1])
    df.loc[0, "NAME_INCOME_TYPE"] = "Pensioner"
    y = desemprego(df, delta=10.0, mediana_ref=0.2, rng=np.random.default_rng(0))  # p ≥ 1
    assert y.tolist() == [0, 1, 1]  # pensionista intacto; assalariado vira default; default segue default
