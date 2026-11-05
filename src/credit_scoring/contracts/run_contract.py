import pandas as pd
from pandera.errors import SchemaErrors

from credit_scoring import config as cfg
from credit_scoring.contracts.schema import AlertSchema, ApplicationSchema


def _falhas(schema: type, df: pd.DataFrame) -> pd.DataFrame:
    try:
        schema.validate(df, lazy=True)
        return pd.DataFrame(columns=["check", "index"])
    except SchemaErrors as err:
        return err.failure_cases


def resumo(fc: pd.DataFrame) -> pd.Series:
    """Linhas únicas afetadas por regra; regras de lote/schema aparecem como 'lote'.

    Regras de coluna são prefixadas pela coluna (ex.: AMT_ANNUITY:not_nullable).
    """
    if fc.empty:
        return pd.Series(dtype=object)
    chave = (
        fc["check"]
        .astype(str)
        .where(
            fc["schema_context"] != "Column",
            fc["column"].astype(str) + ":" + fc["check"].astype(str),
        )
    )
    return (
        fc.assign(regra=chave)
        .groupby("regra")["index"]
        .agg(lambda s: s.nunique() if s.notna().any() else "lote")
    )


def run_contract(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (failure_cases rígidas, failure_cases alertas)."""
    return _falhas(ApplicationSchema, df), _falhas(AlertSchema, df)


def main() -> None:
    df = pd.read_parquet(cfg.REFERENCE_DIR / "train.parquet")
    rigidas, alertas = run_contract(df)
    print(f"Linhas: {len(df):,}")
    for titulo, fc in [("RÍGIDAS (bloqueariam o lote)", rigidas), ("ALERTAS", alertas)]:
        r = resumo(fc)
        print(f"\n=== {titulo} ===")
        print(r.to_string() if not r.empty else "nenhuma")


if __name__ == "__main__":
    main()
