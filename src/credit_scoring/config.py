from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_FILE = DATA_DIR / "raw" / "application_train.csv"
REFERENCE_DIR = DATA_DIR / "reference"
PRODUCTION_DIR = DATA_DIR / "production"

SEED = 42
ID_COL = "SK_ID_CURR"
TARGET = "TARGET"

SENSITIVE_COLS = ["CODE_GENDER"]

FEATURES = [
    # Contrato
    "NAME_CONTRACT_TYPE",
    "AMT_CREDIT",
    "AMT_ANNUITY",
    "AMT_GOODS_PRICE",
    # Renda e emprego
    "AMT_INCOME_TOTAL",
    "NAME_INCOME_TYPE",
    "DAYS_EMPLOYED",
    # Perfil
    "DAYS_BIRTH",
    "CNT_CHILDREN",
    "NAME_FAMILY_STATUS",
    "NAME_EDUCATION_TYPE",
    "FLAG_OWN_CAR",
    "FLAG_OWN_REALTY",
    "REGION_RATING_CLIENT",
    # Scores externos (bureau)
    "EXT_SOURCE_1",
    "EXT_SOURCE_2",
    "EXT_SOURCE_3",
]
