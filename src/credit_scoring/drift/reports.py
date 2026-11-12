"""Relatórios de drift (Evidently) por mês: features do modelo + score."""

import pandas as pd
from evidently import DataDefinition, Dataset, Report
from evidently.metrics import ValueDrift
from evidently.presets import DataDriftPreset

from credit_scoring import config as cfg
from credit_scoring.data.features import CATEGORICAL_FEATURES, MODEL_FEATURES, NUMERIC_FEATURES
from credit_scoring.drift.score_batches import SCORED_DIR

REPORTS_DIR = cfg.ROOT / "reports" / "drift"
PSI_ALERTA = 0.25  # política da 2.1
SHARE_DATASET = 0.30  # drift de dataset: ≥ 30% das features em drift (fixado antes de rodar)

# Discretas de baixa cardinalidade tratadas como categóricas no PSI
CATEGORICAS = [*CATEGORICAL_FEATURES, "FLAG_EMPLOYED_ANOMALY", "REGION_RATING_CLIENT"]
NUMERICAS = [c for c in NUMERIC_FEATURES if c not in CATEGORICAS] + ["SCORE"]
DEFINICAO = DataDefinition(numerical_columns=NUMERICAS, categorical_columns=CATEGORICAS)


def _dataset(df: pd.DataFrame) -> Dataset:
    return Dataset.from_pandas(df[[*MODEL_FEATURES, "SCORE"]], data_definition=DEFINICAO)


def build_report() -> Report:
    return Report(
        [
            DataDriftPreset(
                columns=MODEL_FEATURES, method="psi", threshold=PSI_ALERTA, drift_share=SHARE_DATASET
            ),
            ValueDrift(column="SCORE", method="psi", threshold=PSI_ALERTA),
        ]
    )


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ref = _dataset(pd.read_parquet(cfg.REFERENCE_DIR / "test_scored.parquet"))

    for path in sorted(SCORED_DIR.glob("mes_*.parquet")):
        snapshot = build_report().run(_dataset(pd.read_parquet(path)), ref)
        snapshot.save_html(str(REPORTS_DIR / f"{path.stem}.html"))
        (REPORTS_DIR / f"{path.stem}.json").write_text(snapshot.json(), encoding="utf-8")
        print(f"{path.stem}: relatório gerado")


if __name__ == "__main__":
    main()
