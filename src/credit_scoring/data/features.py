"""Transformações de domínio determinísticas (sem ajuste em dados).

Pré-condição: entrada já validada pelo ApplicationSchema (ex.: renda > 0).
Usadas identicamente no treino e na producao (evita training-serving skew).
Transformacgitões ajustadas (encoding, imputacao) ficam no pipeline do modelo.
"""

import pandas as pd

from credit_scoring.contracts.schema import DIAS_ANO, SENTINELA_EMPREGO

NUMERIC_FEATURES = [
    "AMT_CREDIT",
    "AMT_ANNUITY",
    "AMT_GOODS_PRICE",
    "AMT_INCOME_TOTAL",
    "AGE_YEARS",
    "YEARS_EMPLOYED",
    "FLAG_EMPLOYED_ANOMALY",
    "CNT_CHILDREN",
    "REGION_RATING_CLIENT",
    "EXT_SOURCE_1",
    "EXT_SOURCE_2",
    "EXT_SOURCE_3",
    "CREDIT_INCOME_RATIO",
    "ANNUITY_INCOME_RATIO",
    "ANNUITY_CREDIT_RATIO",
]
CATEGORICAL_FEATURES = [
    "NAME_CONTRACT_TYPE",
    "NAME_INCOME_TYPE",
    "NAME_FAMILY_STATUS",
    "NAME_EDUCATION_TYPE",
    "FLAG_OWN_CAR",
    "FLAG_OWN_REALTY",
]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Chave (rastreabilidade/rótulos atrasados), rótulo e atributo sensível (só auditoria)
EXCLUDED_FROM_MODEL = ["SK_ID_CURR", "TARGET", "CODE_GENDER"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    anomalia = out["DAYS_EMPLOYED"] == SENTINELA_EMPREGO
    out["FLAG_EMPLOYED_ANOMALY"] = anomalia.astype(int)
    out["YEARS_EMPLOYED"] = (-out["DAYS_EMPLOYED"] / DIAS_ANO).where(~anomalia)
    out["AGE_YEARS"] = -out["DAYS_BIRTH"] / DIAS_ANO

    out["CREDIT_INCOME_RATIO"] = out["AMT_CREDIT"] / out["AMT_INCOME_TOTAL"]
    out["ANNUITY_INCOME_RATIO"] = out["AMT_ANNUITY"] / out["AMT_INCOME_TOTAL"]
    out["ANNUITY_CREDIT_RATIO"] = out["AMT_ANNUITY"] / out["AMT_CREDIT"]

    return out.drop(columns=["DAYS_EMPLOYED", "DAYS_BIRTH"])
