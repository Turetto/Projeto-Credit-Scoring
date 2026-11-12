"""
Ablação contrafactual pareada: os mesmos clientes e scores de cada mês são avaliados
com (a) os rótulos simulados (com desemprego) e (b) os rótulos originais do pool
(sem desemprego). As features são idênticas; a diferença isola o concept drift.
"""

import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from credit_scoring import config as cfg
from credit_scoring.drift.score_batches import SCORED_DIR
from credit_scoring.drift.simulate import LABELS_DIR
from credit_scoring.model.train import METRICS_FILE

OUT_FILE = cfg.ROOT / "reports" / "degradation_attribution.csv"
N_BOOT = 500


def avaliar(y: pd.Series, p: pd.Series, rng: np.random.Generator) -> dict:
    """AUC e gap de calibração com IC 95% por bootstrap."""
    y, p = np.asarray(y), np.asarray(p)
    n = len(y)
    aucs, gaps = np.empty(N_BOOT), np.empty(N_BOOT)
    for b in range(N_BOOT):
        i = rng.integers(0, n, n)
        aucs[b] = roc_auc_score(y[i], p[i])
        gaps[b] = y[i].mean() - p[i].mean()
    return {
        "auc": roc_auc_score(y, p),
        "auc_ic_inf": np.percentile(aucs, 2.5),
        "auc_ic_sup": np.percentile(aucs, 97.5),
        "gap": y.mean() - p.mean(),
        "gap_ic_inf": np.percentile(gaps, 2.5),
        "gap_ic_sup": np.percentile(gaps, 97.5),
        "default_obs": y.mean(),
    }


def main() -> None:
    auc_ref = json.loads(METRICS_FILE.read_text(encoding="utf-8"))["teste"]["auc"]
    originais = pd.read_parquet(cfg.PRODUCTION_DIR / "pool.parquet", columns=[cfg.ID_COL, cfg.TARGET]).rename(
        columns={cfg.TARGET: "TARGET_ORIGINAL"}
    )
    rng = np.random.default_rng(cfg.SEED)

    linhas = []
    for path in sorted(SCORED_DIR.glob("mes_*.parquet")):
        df = (
            pd.read_parquet(path, columns=[cfg.ID_COL, "SCORE"])
            .merge(pd.read_parquet(LABELS_DIR / path.name), on=cfg.ID_COL, validate="one_to_one")
            .merge(originais, on=cfg.ID_COL, validate="one_to_one")
        )
        for cenario, col in [("com_desemprego", cfg.TARGET), ("sem_desemprego", "TARGET_ORIGINAL")]:
            linhas.append({"mes": path.stem, "cenario": cenario, **avaliar(df[col], df["SCORE"], rng)})

    tab = pd.DataFrame(linhas).round(4)
    tab.to_csv(OUT_FILE, index=False)

    real = tab[tab["cenario"] == "com_desemprego"].set_index("mes")
    cf = tab[tab["cenario"] == "sem_desemprego"].set_index("mes")
    decomp = pd.DataFrame(
        {
            "queda_auc_total": auc_ref - real["auc"],
            "queda_data_drift": auc_ref - cf["auc"],
            "queda_desemprego": cf["auc"] - real["auc"],
            "gap_total": real["gap"],
            "gap_data_drift": cf["gap"],
            "gap_desemprego": real["gap"] - cf["gap"],
            "ic95_auc_real": real["auc_ic_inf"].map("{:.3f}".format)
            + "–"
            + real["auc_ic_sup"].map("{:.3f}".format),
            "ic95_gap_sem_desemp": cf["gap_ic_inf"].map("{:+.3f}".format)
            + " a "
            + cf["gap_ic_sup"].map("{:+.3f}".format),
            "queda_significativa": real["auc_ic_sup"] < auc_ref,
        }
    ).round(4)

    print(f"AUC de referência: {auc_ref}\n")
    with pd.option_context("display.width", 250):
        print(decomp.to_string())


if __name__ == "__main__":
    main()
