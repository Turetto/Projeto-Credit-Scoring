import numpy as np
import pandas as pd
import pytest

from credit_scoring.drift.stats import ks, psi


@pytest.fixture
def normal() -> pd.Series:
    return pd.Series(np.random.default_rng(0).normal(size=20_000))


def test_psi_zero_para_distribuicoes_identicas(normal):
    assert psi(normal, normal) == pytest.approx(0.0, abs=1e-9)


def test_psi_cresce_com_o_deslocamento(normal):
    assert psi(normal, normal + 0.1) < psi(normal, normal + 0.5)


def test_psi_categorico_detecta_categoria_nova():
    ref = pd.Series(["A"] * 90 + ["B"] * 10)
    cur = pd.Series(["A"] * 50 + ["C"] * 50)
    assert psi(ref, cur) > 0.25


def test_ks_d_zero_para_identicas(normal):
    d, _ = ks(normal, normal)
    assert d == 0.0
