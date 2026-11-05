"""Contrato de dados das solicitações de crédito (Home Credit).

Cada limite referencia o achado correspondente em docs/eda_findings.md.
- Rígidas: violação bloqueia o lote.
- Alertas (raise_warning=True): violação é registrada e o lote segue.
"""

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

SENTINELA_EMPREGO = 365243
DIAS_ANO = 365.25

IDADE_MIN, IDADE_MAX = 18, 100  # Q4 rígida
IDADE_ALERTA = (21, 70)  # Q4 alerta
RENDA_MAX = 50_000_000  # Q5 rígida
RENDA_ALERTA = 1_000_000  # Q5 alerta
FILHOS_MAX, FILHOS_ALERTA = 25, 10  # Q6
NULOS_MAX = {  # Q2: taxa da referência + margem
    "EXT_SOURCE_1": 0.61,
    "EXT_SOURCE_2": 0.05,
    "EXT_SOURCE_3": 0.25,
}

INCOME_TYPES = [
    "Working",
    "Commercial associate",
    "Pensioner",
    "State servant",
    "Unemployed",
    "Businessman",
    "Student",
    "Maternity leave",
]
EDUCATION_TYPES = [
    "Secondary / secondary special",
    "Higher education",
    "Incomplete higher",
    "Lower secondary",
    "Academic degree",
]
FAMILY_STATUS = [
    "Married",
    "Single / not married",
    "Civil marriage",
    "Separated",
    "Widow",
    "Unknown",
]
UNIT_RANGE = {"min_value": 0, "max_value": 1}


def _anos(dias: pd.Series) -> pd.Series:
    return -dias / DIAS_ANO


class ApplicationSchema(pa.DataFrameModel):
    # Identificação e rótulo
    SK_ID_CURR: Series[int] = pa.Field(unique=True)  # Q7
    TARGET: Series[int] | None = pa.Field(isin=[0, 1])  # Q1
    CODE_GENDER: Series[str] = pa.Field(nullable=True)  # Q6: só alerta

    # Contrato
    NAME_CONTRACT_TYPE: Series[str] = pa.Field(isin=["Cash loans", "Revolving loans"])
    AMT_CREDIT: Series[float] = pa.Field(gt=0)
    AMT_ANNUITY: Series[float] = pa.Field(gt=0)  # Q2
    AMT_GOODS_PRICE: Series[float] = pa.Field(gt=0, nullable=True)  # Q2 (condicional abaixo)

    # Renda e emprego
    AMT_INCOME_TOTAL: Series[float] = pa.Field(gt=0, le=RENDA_MAX)  # Q5
    NAME_INCOME_TYPE: Series[str] = pa.Field(isin=INCOME_TYPES)  # Q6
    DAYS_EMPLOYED: Series[int]  # Q3 (checks abaixo)

    # Perfil
    DAYS_BIRTH: Series[int]  # Q4 (checks abaixo)
    CNT_CHILDREN: Series[int] = pa.Field(in_range={"min_value": 0, "max_value": FILHOS_MAX})
    NAME_FAMILY_STATUS: Series[str] = pa.Field(isin=FAMILY_STATUS)
    NAME_EDUCATION_TYPE: Series[str] = pa.Field(isin=EDUCATION_TYPES)
    FLAG_OWN_CAR: Series[str] = pa.Field(isin=["Y", "N"])
    FLAG_OWN_REALTY: Series[str] = pa.Field(isin=["Y", "N"])
    REGION_RATING_CLIENT: Series[int] = pa.Field(isin=[1, 2, 3])

    # Scores externos
    EXT_SOURCE_1: Series[float] = pa.Field(in_range=UNIT_RANGE, nullable=True)
    EXT_SOURCE_2: Series[float] = pa.Field(in_range=UNIT_RANGE, nullable=True)
    EXT_SOURCE_3: Series[float] = pa.Field(in_range=UNIT_RANGE, nullable=True)

    class Config:
        strict = True
        coerce = False

    # ---------------- Rígidas ----------------
    @pa.check("DAYS_EMPLOYED", name="emprego_negativo_ou_sentinela")
    def _emprego_valido(cls, s: Series[int]) -> Series[bool]:
        return (s <= 0) | (s == SENTINELA_EMPREGO)

    @pa.check("DAYS_BIRTH", name="idade_entre_18_e_100")
    def _idade_valida(cls, s: Series[int]) -> Series[bool]:
        return _anos(s).between(IDADE_MIN, IDADE_MAX)

    @pa.dataframe_check(name="parcela_menor_que_credito", ignore_na=False)
    def _parcela_credito(cls, df: pd.DataFrame) -> Series[bool]:
        # Nulidade é responsabilidade de AMT_ANNUITY (nullable=False); aqui só a relação
        return df["AMT_ANNUITY"].isna() | (df["AMT_ANNUITY"] < df["AMT_CREDIT"])

    @pa.dataframe_check(name="emprego_menor_que_idade", ignore_na=False)
    def _emprego_idade(cls, df: pd.DataFrame) -> Series[bool]:
        sentinela = df["DAYS_EMPLOYED"] == SENTINELA_EMPREGO
        return sentinela | (df["DAYS_EMPLOYED"] >= df["DAYS_BIRTH"])

    @pa.dataframe_check(name="bem_obrigatorio_em_cash_loans", ignore_na=False)
    def _bem_cash(cls, df: pd.DataFrame) -> Series[bool]:
        return (df["NAME_CONTRACT_TYPE"] != "Cash loans") | df["AMT_GOODS_PRICE"].notna()

    # ---------------- Alertas ----------------
    @pa.check("CODE_GENDER", name="alerta_genero_fora_de_FM", raise_warning=True)
    def _genero(cls, s: Series[str]) -> Series[bool]:
        return s.isin(["F", "M"])

    @pa.check("NAME_FAMILY_STATUS", name="alerta_familia_unknown", raise_warning=True)
    def _familia(cls, s: Series[str]) -> Series[bool]:
        return s != "Unknown"

    @pa.check("DAYS_BIRTH", name="alerta_idade_fora_21_70", raise_warning=True)
    def _idade_alerta(cls, s: Series[int]) -> Series[bool]:
        return _anos(s).between(*IDADE_ALERTA)

    @pa.check("AMT_INCOME_TOTAL", name="alerta_renda_acima_1M", raise_warning=True)
    def _renda_alerta(cls, s: Series[float]) -> Series[bool]:
        return s <= RENDA_ALERTA

    @pa.check("CNT_CHILDREN", name="alerta_filhos_acima_10", raise_warning=True)
    def _filhos_alerta(cls, s: Series[int]) -> Series[bool]:
        return s <= FILHOS_ALERTA

    @pa.dataframe_check(name="alerta_bem_maior_que_credito", raise_warning=True, ignore_na=False)
    def _bem_credito(cls, df: pd.DataFrame) -> Series[bool]:
        return df["AMT_GOODS_PRICE"].isna() | (df["AMT_GOODS_PRICE"] <= df["AMT_CREDIT"])

    @pa.dataframe_check(name="alerta_sentinela_sem_pensao", raise_warning=True, ignore_na=False)
    def _sentinela_pensao(cls, df: pd.DataFrame) -> Series[bool]:
        sentinela = df["DAYS_EMPLOYED"] == SENTINELA_EMPREGO
        return ~sentinela | df["NAME_INCOME_TYPE"].isin(["Pensioner", "Unemployed"])

    @pa.check(
        "EXT_SOURCE_1",
        "EXT_SOURCE_2",
        "EXT_SOURCE_3",
        name="alerta_taxa_de_nulos",
        raise_warning=True,
        ignore_na=False,
    )
    def _taxa_nulos(cls, s: Series[float]) -> bool:
        return s.isna().mean() <= NULOS_MAX[s.name]
