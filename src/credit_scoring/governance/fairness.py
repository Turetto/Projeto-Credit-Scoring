"""Auditoria de viés (art. 6º, IX LGPD): disparidade por gênero e faixa etária.

AIR (adverse impact ratio) < 0,8 é gatilho de investigação (heurística dos 4/5),
não veredito de discriminação.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from credit_scoring import config as cfg
from credit_scoring.data.features import MODEL_FEATURES
from credit_scoring.drift.score_batches import SCORED_DIR
from credit_scoring.drift.simulate import LABELS_DIR
from credit_scoring.model.explain import ROTULOS, contribuicoes, motivos
from credit_scoring.model.train import MODELS_DIR, build_models

OUT_FILE = cfg.ROOT / "reports" / "fairness_audit.csv"
FAIXAS, ROT_FAIXAS = [18, 30, 45, 60, 101], ["18-29", "30-44", "45-59", "60+"]
AIR_MIN = 0.8
FATORES_PROTEGIDOS = [
    ROTULOS[f] for f in ["AGE_YEARS", "NAME_FAMILY_STATUS", "CNT_CHILDREN", "NAME_EDUCATION_TYPE"]
]


def grupos(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "genero": df["CODE_GENDER"].where(df["CODE_GENDER"].isin(["F", "M"])),
        "faixa_etaria": pd.cut(df["AGE_YEARS"], FAIXAS, right=False, labels=ROT_FAIXAS),
    }


def metricas_grupo(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    linhas = []
    for g, d in df.groupby(coluna, observed=True):
        y, p, a = d[cfg.TARGET], d["SCORE"], d["APROVADO"]
        linhas.append(
            {
                "grupo": g,
                "n": len(d),
                "taxa_aprovacao": a.mean(),
                "aprovacao_bons_pagadores": a[y == 0].mean(),
                "default_observado": y.mean(),
                "pd_prevista": p.mean(),
                "gap_calibracao": y.mean() - p.mean(),
                "auc": roc_auc_score(y, p) if y.nunique() > 1 else np.nan,
            }
        )
    t = pd.DataFrame(linhas)
    t["air"] = t["taxa_aprovacao"] / t["taxa_aprovacao"].max()
    t["air_bons_pagadores"] = t["aprovacao_bons_pagadores"] / t["aprovacao_bons_pagadores"].max()
    return t


def auditar(df: pd.DataFrame, base: str) -> pd.DataFrame:
    df = df.assign(**grupos(df))
    return pd.concat(
        [
            metricas_grupo(df.dropna(subset=[dim]), dim).assign(dimensao=dim, base=base)
            for dim in ["genero", "faixa_etaria"]
        ]
    )


def forca_proxy(df: pd.DataFrame) -> float:
    """AUC de prever o gênero a partir das features do modelo (validação cruzada)."""
    d = df[df["CODE_GENDER"].isin(["F", "M"])]
    y = (d["CODE_GENDER"] == "M").astype(int)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=cfg.SEED)
    p = cross_val_predict(build_models()["xgboost"], d[MODEL_FEATURES], y, cv=cv, method="predict_proba")[
        :, 1
    ]
    return float(roc_auc_score(y, p))


def motivos_protegidos(df: pd.DataFrame, modelo) -> pd.DataFrame:
    """% dos recusados em que cada fator protegido está entre os 3 motivos, no total e por faixa."""
    negados = df[df["APROVADO"] == 0].assign(**grupos(df[df["APROVADO"] == 0]))
    tops = contribuicoes(modelo, negados).apply(motivos, axis=1)
    linhas = []
    for fator in FATORES_PROTEGIDOS:
        presente = tops.apply(lambda m, f=fator: f in m)
        linha = {"fator": fator, "total": presente.mean()}
        for faixa in ROT_FAIXAS:
            mask = negados["faixa_etaria"] == faixa
            linha[faixa] = presente[mask].mean() if mask.any() else np.nan
        linhas.append(linha)
    return pd.DataFrame(linhas)


def main() -> None:
    modelo = joblib.load(MODELS_DIR / "baseline.joblib")
    ref = pd.read_parquet(cfg.REFERENCE_DIR / "test_scored.parquet")
    m06 = pd.read_parquet(SCORED_DIR / "mes_06.parquet").merge(
        pd.read_parquet(LABELS_DIR / "mes_06.parquet"), on=cfg.ID_COL, validate="one_to_one"
    )

    tabela = pd.concat([auditar(ref, "referencia"), auditar(m06, "mes_06")])
    tabela.to_csv(OUT_FILE, index=False)

    cols = [
        "grupo",
        "n",
        "taxa_aprovacao",
        "air",
        "aprovacao_bons_pagadores",
        "air_bons_pagadores",
        "default_observado",
        "pd_prevista",
        "gap_calibracao",
        "auc",
    ]
    with pd.option_context("display.width", 220, "display.float_format", "{:.4f}".format):
        for base in ["referencia", "mes_06"]:
            for dim in ["genero", "faixa_etaria"]:
                t = tabela[(tabela["base"] == base) & (tabela["dimensao"] == dim)]
                print(f"\n=== {base} · {dim} ===")
                print(t[cols].to_string(index=False))
                abaixo = t.loc[t["air"] < AIR_MIN, "grupo"].tolist()
                if abaixo:
                    print(f"AIR < {AIR_MIN}: {abaixo}")

        print(f"\n=== Força de proxy: AUC de prever gênero pelas features = {forca_proxy(ref):.3f} ===")
        print("\n=== Fatores protegidos entre os 3 motivos de recusa (referência) ===")
        print(motivos_protegidos(ref, modelo).to_string(index=False))


if __name__ == "__main__":
    main()
