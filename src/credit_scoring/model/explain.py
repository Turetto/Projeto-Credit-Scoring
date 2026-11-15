"""Explicabilidade (art. 20 LGPD): contribuições TreeSHAP nativas do XGBoost.

- Global: participação média de cada fator na decisão (critérios do art. 20, §1º).
- Local: os k fatores que mais aumentaram a PD do cliente (motivos da decisão).
Não expõe pesos nem o modelo (segredo comercial, art. 20, §1º).
"""

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from credit_scoring import config as cfg
from credit_scoring.data.features import CATEGORICAL_FEATURES, MODEL_FEATURES
from credit_scoring.model.train import MODELS_DIR

GLOBAL_FILE = cfg.ROOT / "reports" / "explicabilidade_global.csv"

ROTULOS = {
    "AMT_CREDIT": "Valor do crédito solicitado",
    "AMT_ANNUITY": "Valor da parcela",
    "AMT_GOODS_PRICE": "Valor do bem financiado",
    "AMT_INCOME_TOTAL": "Renda declarada",
    "AGE_YEARS": "Idade",
    "YEARS_EMPLOYED": "Tempo no emprego atual",
    "FLAG_EMPLOYED_ANOMALY": "Sem vínculo empregatício (ex.: aposentadoria)",
    "CNT_CHILDREN": "Número de filhos",
    "REGION_RATING_CLIENT": "Classificação de risco da região",
    "EXT_SOURCE_1": "Score de crédito externo (bureau 1)",
    "EXT_SOURCE_2": "Score de crédito externo (bureau 2)",
    "EXT_SOURCE_3": "Score de crédito externo (bureau 3)",
    "CREDIT_INCOME_RATIO": "Crédito em relação à renda",
    "ANNUITY_INCOME_RATIO": "Comprometimento da renda com a parcela",
    "ANNUITY_CREDIT_RATIO": "Prazo e taxa do contrato (parcela em relação ao crédito)",
    "NAME_CONTRACT_TYPE": "Modalidade do crédito",
    "NAME_INCOME_TYPE": "Tipo de renda",
    "NAME_FAMILY_STATUS": "Estado civil",
    "NAME_EDUCATION_TYPE": "Escolaridade",
    "FLAG_OWN_CAR": "Posse de veículo",
    "FLAG_OWN_REALTY": "Posse de imóvel",
}


def _mapa_colunas(nomes: list[str]) -> dict[str, list[int]]:
    """Agrupa as colunas transformadas (one-hot, indicadores) pela feature original."""
    mapa: dict[str, list[int]] = {f: [] for f in MODEL_FEATURES}
    for i, nome in enumerate(nomes):
        bloco, _, resto = nome.partition("__")
        resto = resto.removeprefix("missingindicator_")
        if bloco == "num":
            mapa[resto].append(i)
        else:
            mapa[next(c for c in CATEGORICAL_FEATURES if resto.startswith(f"{c}_"))].append(i)
    return mapa


def contribuicoes(modelo, X: pd.DataFrame) -> pd.DataFrame:
    """Contribuições em log-odds por feature original + coluna '_base'."""
    prep, clf = modelo.named_steps["prep"], modelo.named_steps["clf"]
    Xt = prep.transform(X[MODEL_FEATURES])
    phi = clf.get_booster().predict(xgb.DMatrix(Xt), pred_contribs=True)
    mapa = _mapa_colunas(list(prep.get_feature_names_out()))
    out = pd.DataFrame({f: phi[:, idx].sum(axis=1) for f, idx in mapa.items()}, index=X.index)
    out["_base"] = phi[:, -1]
    return out


def motivos(linha: pd.Series, k: int = 3) -> list[str]:
    """Os k fatores que mais aumentaram o risco, em linguagem simples."""
    c = linha.drop("_base")
    return [ROTULOS[f] for f in c[c > 0].sort_values(ascending=False).head(k).index]


def importancia_global(contrib: pd.DataFrame) -> pd.Series:
    imp = contrib.drop(columns="_base").abs().mean()
    return (imp / imp.sum()).sort_values(ascending=False)


def main() -> None:
    modelo = joblib.load(MODELS_DIR / "baseline.joblib")
    ref = pd.read_parquet(cfg.REFERENCE_DIR / "test_scored.parquet")
    contrib = contribuicoes(modelo, ref)

    imp = importancia_global(contrib)
    tabela = pd.DataFrame(
        {"fator": [ROTULOS[f] for f in imp.index], "feature": imp.index, "participacao": imp.round(4).values}
    )
    tabela.to_csv(GLOBAL_FILE, index=False)
    print("=== Importância global ===")
    print(tabela.to_string(index=False))
    ext = imp[[c for c in imp.index if c.startswith("EXT_SOURCE")]].sum()
    print(f"\nParticipação dos scores externos: {ext:.1%}")

    print("\n=== Exemplos de motivos (clientes negados, sem identificação) ===")
    negados = ref.index[ref["APROVADO"] == 0][:3]
    for letra, i in zip("ABC", negados, strict=False):
        print(f"Cliente {letra} (PD = {ref.at[i, 'SCORE']:.1%}): " + "; ".join(motivos(contrib.loc[i])))

    p = 1 / (1 + np.exp(-contrib.sum(axis=1)))
    print(f"\nErro máximo de aditividade: {np.abs(p - ref['SCORE']).max():.2e}")


if __name__ == "__main__":
    main()
