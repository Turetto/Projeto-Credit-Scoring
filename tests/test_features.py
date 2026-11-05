import numpy as np
import pandas as pd
import pytest

from credit_scoring.contracts.schema import SENTINELA_EMPREGO
from credit_scoring.data.features import EXCLUDED_FROM_MODEL, MODEL_FEATURES, build_features


def _linha(**kw) -> pd.DataFrame:
    base = dict(
        SK_ID_CURR=1,
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
    base.update(kw)
    return pd.DataFrame([base])


def test_sentinela_vira_flag_e_nan():
    out = build_features(_linha(DAYS_EMPLOYED=SENTINELA_EMPREGO))
    assert out.loc[0, "FLAG_EMPLOYED_ANOMALY"] == 1
    assert np.isnan(out.loc[0, "YEARS_EMPLOYED"])


def test_conversao_idade_e_razoes():
    out = build_features(_linha())
    assert out.loc[0, "AGE_YEARS"] == pytest.approx(40.0)
    assert out.loc[0, "ANNUITY_INCOME_RATIO"] == pytest.approx(0.2)
    assert out.loc[0, "FLAG_EMPLOYED_ANOMALY"] == 0


def test_governanca_modelo_nao_usa_id_rotulo_ou_genero():
    assert not set(EXCLUDED_FROM_MODEL) & set(MODEL_FEATURES)


def test_todas_features_do_modelo_existem():
    assert set(MODEL_FEATURES) <= set(build_features(_linha()).columns)
