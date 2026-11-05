import pandas as pd
import pytest

LINHA_VALIDA = dict(
    CODE_GENDER="F",
    NAME_CONTRACT_TYPE="Cash loans",
    AMT_CREDIT=100_000.0,
    AMT_ANNUITY=10_000.0,
    AMT_GOODS_PRICE=90_000.0,
    AMT_INCOME_TOTAL=50_000.0,
    NAME_INCOME_TYPE="Working",
    DAYS_EMPLOYED=-3653,
    DAYS_BIRTH=-14610,
    CNT_CHILDREN=0,
    NAME_FAMILY_STATUS="Married",
    NAME_EDUCATION_TYPE="Higher education",
    FLAG_OWN_CAR="N",
    FLAG_OWN_REALTY="Y",
    REGION_RATING_CLIENT=2,
    EXT_SOURCE_1=0.5,
    EXT_SOURCE_2=0.5,
    EXT_SOURCE_3=0.5,
)


@pytest.fixture
def make_batch():
    """Lote de n linhas válidas, sem TARGET (como chega em produção)."""

    def _make(n: int = 1) -> pd.DataFrame:
        return pd.DataFrame([{"SK_ID_CURR": i + 1, **LINHA_VALIDA} for i in range(n)])

    return _make
