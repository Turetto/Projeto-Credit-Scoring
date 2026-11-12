import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.drift.score_batches import classificar, performance


def test_classificar_faixas():
    assert classificar(0.005, 0.01, 0.02) == "ESTÁVEL"
    assert classificar(0.015, 0.01, 0.02) == "ATENÇÃO"
    assert classificar(0.020, 0.01, 0.02) == "ALERTA"


def test_gap_positivo_indica_subestimacao_de_risco():
    scored = pd.DataFrame({cfg.ID_COL: range(10), "SCORE": 0.1, "APROVADO": 1})
    labels = pd.DataFrame({cfg.ID_COL: range(10), cfg.TARGET: [1, 1] + [0] * 8})
    r = performance(scored, labels, auc_ref=0.76)
    assert r["gap_calibracao"] > 0  # observado 20% > previsto 10%
    assert r["status_calibracao"] == "ALERTA"
