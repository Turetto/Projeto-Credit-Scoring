import pandas as pd
from sklearn.model_selection import train_test_split

from credit_scoring import config as cfg

COLUMNS = [cfg.ID_COL, cfg.TARGET, *cfg.SENSITIVE_COLS, *cfg.FEATURES]


def load_raw() -> pd.DataFrame:
    return pd.read_csv(cfg.RAW_FILE, usecols=COLUMNS)


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Referência (treino/teste) vs pool de produção, estratificado pelo target."""
    ref, prod = train_test_split(df, test_size=0.25, stratify=df[cfg.TARGET], random_state=cfg.SEED)
    ref_train, ref_test = train_test_split(
        ref, test_size=0.20, stratify=ref[cfg.TARGET], random_state=cfg.SEED
    )
    return ref_train, ref_test, prod


def main() -> None:
    ref_train, ref_test, prod = split(load_raw())
    cfg.REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    cfg.PRODUCTION_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        cfg.REFERENCE_DIR / "train.parquet": ref_train,
        cfg.REFERENCE_DIR / "test.parquet": ref_test,
        cfg.PRODUCTION_DIR / "pool.parquet": prod,
    }
    for path, df in outputs.items():
        df.to_parquet(path, index=False)
        print(f"{path.name:<15} linhas={len(df):>7,}  default={df[cfg.TARGET].mean():.4f}")


if __name__ == "__main__":
    main()
