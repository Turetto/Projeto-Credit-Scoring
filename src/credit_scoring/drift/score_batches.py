"""Pontua os lotes aceitos pelo gate e mede a performance quando os rótulos chegam."""

import json

import joblib
import pandas as pd
from sklearn.metrics import roc_auc_score

from credit_scoring import config as cfg
from credit_scoring.contracts.gate import ACCEPTED_DIR
from credit_scoring.data.features import MODEL_FEATURES, build_features
from credit_scoring.drift.simulate import LABELS_DIR
from credit_scoring.model.train import METRICS_FILE, MODELS_DIR, ks
from credit_scoring.monitoring.policy import GAP_CALIBRACAO, QUEDA_AUC

SCORED_DIR = cfg.PRODUCTION_DIR / "scored"
PERF_FILE = cfg.ROOT / "reports" / "performance_by_month.csv"

# (atenção, alerta) — política definida na 2.1
LIMITES = {"queda_auc": (0.02, 0.03), "gap_calibracao": (0.01, 0.02)}


def classificar(valor: float, atencao: float, alerta: float) -> str:
    if valor >= alerta:
        return "ALERTA"
    return "ATENÇÃO" if valor >= atencao else "ESTÁVEL"


def pontuar(df: pd.DataFrame, modelo, threshold: float) -> pd.DataFrame:
    feats = build_features(df)
    p = modelo.predict_proba(feats[MODEL_FEATURES])[:, 1]
    return feats.assign(SCORE=p, APROVADO=(p < threshold).astype(int))


def performance(scored: pd.DataFrame, labels: pd.DataFrame, auc_ref: float) -> dict:
    df = scored.merge(labels, on=cfg.ID_COL, how="inner", validate="one_to_one")
    y, p = df[cfg.TARGET], df["SCORE"]
    auc = roc_auc_score(y, p) if y.nunique() > 1 else 0.5
    gap = y.mean() - p.mean()  # > 0: modelo subestima o risco
    return {
        "linhas": len(df),
        "auc": auc,
        "ks": ks(y, p)[0],
        "queda_auc": auc_ref - auc,
        "pd_prevista": p.mean(),
        "default_observado": y.mean(),
        "gap_calibracao": gap,
        "taxa_aprovacao": df["APROVADO"].mean(),
        "default_aprovados": df.loc[df["APROVADO"] == 1, cfg.TARGET].mean(),
        "status_auc": classificar(auc_ref - auc, *QUEDA_AUC),
        "status_calibracao": classificar(abs(gap), *GAP_CALIBRACAO),
    }


def main() -> None:
    meta = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    modelo = joblib.load(MODELS_DIR / "baseline.joblib")
    threshold, auc_ref = meta["threshold_ks"], meta["teste"]["auc"]
    SCORED_DIR.mkdir(parents=True, exist_ok=True)

    ref = pd.read_parquet(cfg.REFERENCE_DIR / "test_scored.parquet")
    linhas = [
        {
            "mes": "referencia",
            **performance(ref.drop(columns=[cfg.TARGET]), ref[[cfg.ID_COL, cfg.TARGET]], auc_ref),
        }
    ]

    for path in sorted(ACCEPTED_DIR.glob("mes_*.parquet")):
        scored = pontuar(pd.read_parquet(path), modelo, threshold)
        scored.to_parquet(SCORED_DIR / path.name, index=False)
        labels = pd.read_parquet(LABELS_DIR / path.name)
        linhas.append({"mes": path.stem, **performance(scored, labels, auc_ref)})

    tabela = pd.DataFrame(linhas).round(4)
    tabela.to_csv(PERF_FILE, index=False)
    with pd.option_context("display.width", 200):
        print(tabela.to_string(index=False))


if __name__ == "__main__":
    main()
