import warnings

import pandas as pd
from pandera.errors import SchemaErrors, SchemaWarning

from credit_scoring import config as cfg
from credit_scoring.contracts.schema import ApplicationSchema


def run_contract(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Valida o lote; retorna (falhas rígidas, alertas)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            ApplicationSchema.validate(df, lazy=True)
            failures = pd.DataFrame()
        except SchemaErrors as err:
            failures = err.failure_cases
    alerts = [
        str(w.message).splitlines()[0] for w in caught if issubclass(w.category, SchemaWarning)
    ]
    return failures, alerts


def main() -> None:
    df = pd.read_parquet(cfg.REFERENCE_DIR / "train.parquet")
    failures, alerts = run_contract(df)

    print(f"Linhas: {len(df):,}")
    print("\n=== RÍGIDAS (bloqueariam o lote) ===")
    if failures.empty:
        print("nenhuma")
    else:
        print(failures.groupby(["column", "check"], dropna=False).size().to_string())

    print("\n=== ALERTAS ===")
    print("\n".join(alerts) if alerts else "nenhum")


if __name__ == "__main__":
    main()
