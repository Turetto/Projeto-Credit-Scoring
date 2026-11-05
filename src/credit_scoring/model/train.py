import json
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from credit_scoring import config as cfg
from credit_scoring.data.features import CATEGORICAL_FEATURES, MODEL_FEATURES, NUMERIC_FEATURES

MODELS_DIR = cfg.ROOT / "models"
METRICS_FILE = cfg.ROOT / "reports" / "baseline_metrics.json"
TOLERANCIA_AUC = 0.01


def _preprocessor(linear: bool) -> ColumnTransformer:
    num = (
        make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler())
        if linear
        else "passthrough"
    )
    cat = OneHotEncoder(min_frequency=50, handle_unknown="infrequent_if_exist", sparse_output=False)
    return ColumnTransformer([("num", num, NUMERIC_FEATURES), ("cat", cat, CATEGORICAL_FEATURES)])


def build_models() -> dict[str, Pipeline]:
    return {
        "logreg": Pipeline(
            [
                ("prep", _preprocessor(linear=True)),
                ("clf", LogisticRegression(max_iter=1000)),
            ]
        ),
        "xgboost": Pipeline(
            [
                ("prep", _preprocessor(linear=False)),
                (
                    "clf",
                    XGBClassifier(
                        n_estimators=400,
                        learning_rate=0.05,
                        max_depth=4,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        random_state=cfg.SEED,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def ks(y: pd.Series, p: np.ndarray) -> tuple[float, float]:
    """
    Retorna (estatística KS, threshold no ponto de KS máximo).
    """
    fpr, tpr, thr = roc_curve(y, p)
    i = int(np.argmax(tpr - fpr))
    return float(tpr[i] - fpr[i]), float(thr[i])


def metricas(y: pd.Series, p: np.ndarray) -> dict:
    auc = roc_auc_score(y, p)
    return {
        "auc": round(auc, 4),
        "gini": round(2 * auc - 1, 4),
        "ks": round(ks(y, p)[0], 4),
        "pr_auc": round(average_precision_score(y, p), 4),
        "brier": round(brier_score_loss(y, p), 4),
        "pd_media_prevista": round(float(np.mean(p)), 4),
        "taxa_default_observada": round(float(np.mean(y)), 4),
    }


def main() -> None:
    train = pd.read_parquet(cfg.REFERENCE_DIR / "train_clean.parquet")
    test = pd.read_parquet(cfg.REFERENCE_DIR / "test_clean.parquet")
    X_tr, y_tr = train[MODEL_FEATURES], train[cfg.TARGET]

    # 1. Seleção do campeão por validação cruzada (o teste não participa)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=cfg.SEED)
    oof = {
        nome: cross_val_predict(m, X_tr, y_tr, cv=cv, method="predict_proba")[:, 1]
        for nome, m in build_models().items()
    }
    cv_metrics = {nome: metricas(y_tr, p) for nome, p in oof.items()}
    ganho = cv_metrics["xgboost"]["auc"] - cv_metrics["logreg"]["auc"]
    campeao = "xgboost" if ganho >= TOLERANCIA_AUC else "logreg"
    _, threshold = ks(y_tr, oof[campeao])

    # 2. Treino final e avaliação única no teste
    modelo = build_models()[campeao].fit(X_tr, y_tr)
    p_test = modelo.predict_proba(test[MODEL_FEATURES])[:, 1]
    test_metrics = metricas(test[cfg.TARGET], p_test)
    aprovacao = float(np.mean(p_test < threshold))

    # 3. Persistência
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(modelo, MODELS_DIR / "baseline.joblib")
    test.assign(SCORE=p_test, APROVADO=(p_test < threshold).astype(int)).to_parquet(
        cfg.REFERENCE_DIR / "test_scored.parquet", index=False
    )
    meta = {
        "campeao": campeao,
        "ganho_auc_xgb_sobre_logreg": round(ganho, 4),
        "threshold_ks": round(threshold, 4),
        "taxa_aprovacao_teste": round(aprovacao, 4),
        "features": MODEL_FEATURES,
        "cv_oof": cv_metrics,
        "teste": test_metrics,
        "linhas_treino": len(train),
        "treinado_em": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    METRICS_FILE.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(pd.DataFrame(cv_metrics).T.to_string())
    print(f"\nCampeão: {campeao} (ganho AUC do XGB = {ganho:+.4f}; tolerância = {TOLERANCIA_AUC})")
    print(f"Threshold KS: {threshold:.4f} | aprovação no teste: {aprovacao:.1%}")
    print(f"Teste: {test_metrics}")


if __name__ == "__main__":
    main()
