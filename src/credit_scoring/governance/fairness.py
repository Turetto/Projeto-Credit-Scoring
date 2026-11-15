"""Auditoria de viés (art. 6º, IX LGPD): disparidade por gênero e faixa etária.

- Auditoria: aprovação, igualdade de oportunidade, calibração e AUC por grupo.
- Proxy: o quanto as features do modelo reconstituem o gênero excluído.
- Linha de base: AIR de referência + limites calibrados por distribuição nula,
  usados pelo pipeline para monitorar drift de fairness.
- Mitigação (análises): trade-off de threshold por faixa e modelo sem idade.

AIR (adverse impact ratio) < 0,8 é gatilho de investigação (heurística dos 4/5),
não veredito de discriminação.
"""

import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from credit_scoring import config as cfg
from credit_scoring.data.features import MODEL_FEATURES
from credit_scoring.drift.score_batches import SCORED_DIR
from credit_scoring.drift.simulate import LABELS_DIR
from credit_scoring.model.explain import ROTULOS, contribuicoes, motivos
from credit_scoring.model.train import METRICS_FILE, build_models

OUT_FILE = cfg.ROOT / "reports" / "fairness_audit.csv"
BASELINE_FILE = cfg.ROOT / "reports" / "fairness_baseline.json"

FAIXAS, ROT_FAIXAS = [18, 30, 45, 60, 101], ["18-29", "30-44", "45-59", "60+"]
DIMENSOES = ["genero", "faixa_etaria"]
AIR_MIN = 0.8
N_NULA, N_LOTE = 200, 4_000
FATORES_PROTEGIDOS = [
    ROTULOS[f] for f in ["AGE_YEARS", "NAME_FAMILY_STATUS", "CNT_CHILDREN", "NAME_EDUCATION_TYPE"]
]


# ---------------------------------------------------------------- grupos e métricas


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
        [metricas_grupo(df.dropna(subset=[dim]), dim).assign(dimensao=dim, base=base) for dim in DIMENSOES]
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
    negados = df[df["APROVADO"] == 0]
    negados = negados.assign(**grupos(negados))
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


# ---------------------------------------------------------------- monitoramento de fairness


def air_aprovacao(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """AIR de aprovação por grupo (não precisa de rótulo: disponível no momento do scoring)."""
    g = pd.DataFrame(grupos(df)).assign(APROVADO=df["APROVADO"].to_numpy())
    out = {}
    for dim in DIMENSOES:
        taxa = g.groupby(dim, observed=True)["APROVADO"].mean()
        out[dim] = {str(k): round(float(v), 4) for k, v in (taxa / taxa.max()).items()}
    return out


def queda_air(atual: dict, base: dict) -> float:
    """Maior queda de AIR de qualquer grupo em relação à linha de base."""
    quedas = [base[d][k] - atual.get(d, {}).get(k, base[d][k]) for d in base for k in base[d]]
    return max(quedas, default=0.0)


def dispersao_calibracao(df: pd.DataFrame) -> float:
    """Maior gap de calibração entre faixas etárias menos o menor (precisa de rótulo)."""
    gaps = (df[cfg.TARGET] - df["SCORE"]).groupby(grupos(df)["faixa_etaria"], observed=True).mean()
    return float(gaps.max() - gaps.min())


def linha_de_base(ref: pd.DataFrame, rng: np.random.Generator) -> dict:
    """AIR de referência + limites calibrados por distribuição nula (p95 = atenção, p99 = alerta)."""
    air_ref = air_aprovacao(ref)
    quedas, dispersoes = [], []
    for _ in range(N_NULA):
        s = ref.sample(N_LOTE, random_state=int(rng.integers(1_000_000)))
        quedas.append(queda_air(air_aprovacao(s), air_ref))
        dispersoes.append(dispersao_calibracao(s))
    return {
        "air": air_ref,
        "limites": {
            "queda_air": [round(float(np.percentile(quedas, q)), 4) for q in (95, 99)],
            "dispersao_calibracao": [round(float(np.percentile(dispersoes, q)), 4) for q in (95, 99)],
        },
    }


# ---------------------------------------------------------------- análises de mitigação


def tradeoff_jovens(ref: pd.DataFrame, threshold_base: float, faixa: str = "18-29") -> pd.DataFrame:
    """Custo de equalizar oportunidade: threshold próprio para a faixa, demais grupos inalterados."""
    g = grupos(ref)["faixa_etaria"]
    alvo, bons = (g == faixa).to_numpy(), (ref[cfg.TARGET] == 0).to_numpy()
    score = ref["SCORE"].to_numpy()
    aprov_base = score < threshold_base
    referencia = (
        pd.Series(aprov_base[~alvo & bons]).groupby(g.to_numpy()[~alvo & bons], observed=True).mean().max()
    )

    linhas = []
    for t in np.arange(threshold_base, 0.2001, 0.01):
        aprov = score < np.where(alvo, t, threshold_base)
        linhas.append(
            {
                "threshold_faixa": round(float(t), 4),
                "air_bons_pagadores": aprov[alvo & bons].mean() / referencia,
                "aprovacao_faixa": aprov[alvo].mean(),
                "default_aprovados_faixa": ref.loc[alvo & aprov, cfg.TARGET].mean(),
                "default_aprovados_carteira": ref.loc[aprov, cfg.TARGET].mean(),
            }
        )
    return pd.DataFrame(linhas)


def experimento_sem_idade(treino: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """Retreina neutralizando a idade (coluna toda NaN: o XGBoost não consegue usá-la).

    Compara com a MESMA taxa de aprovação global do baseline, para isolar a distribuição.
    """
    modelo = build_models()["xgboost"].fit(
        treino[MODEL_FEATURES].assign(AGE_YEARS=np.nan), treino[cfg.TARGET]
    )
    p = modelo.predict_proba(ref[MODEL_FEATURES].assign(AGE_YEARS=np.nan))[:, 1]
    corte = np.quantile(p, ref["APROVADO"].mean())
    sem = ref.assign(SCORE=p, APROVADO=(p < corte).astype(int))

    linhas = []
    for nome, d in [("com idade (baseline)", ref), ("sem idade", sem)]:
        t = metricas_grupo(d.assign(faixa_etaria=grupos(d)["faixa_etaria"]), "faixa_etaria").set_index(
            "grupo"
        )
        linhas.append(
            {
                "modelo": nome,
                "auc": roc_auc_score(d[cfg.TARGET], d["SCORE"]),
                **{f"air_{k}": v for k, v in t["air"].items()},
                **{f"air_bons_{k}": v for k, v in t["air_bons_pagadores"].items()},
            }
        )
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------- execução


def main() -> None:
    meta = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    treino = pd.read_parquet(cfg.REFERENCE_DIR / "train_clean.parquet")
    ref = pd.read_parquet(cfg.REFERENCE_DIR / "test_scored.parquet")
    m06 = pd.read_parquet(SCORED_DIR / "mes_06.parquet").merge(
        pd.read_parquet(LABELS_DIR / "mes_06.parquet"), on=cfg.ID_COL, validate="one_to_one"
    )

    tabela = pd.concat([auditar(ref, "referencia"), auditar(m06, "mes_06")])
    tabela.to_csv(OUT_FILE, index=False)

    base = linha_de_base(ref, np.random.default_rng(cfg.SEED))
    BASELINE_FILE.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding="utf-8")

    with pd.option_context("display.width", 220, "display.float_format", "{:.4f}".format):
        print("=== Linha de base de fairness (limites calibrados por distribuição nula) ===")
        print(json.dumps(base["limites"], indent=2))

        print("\n=== Trade-off: threshold próprio para 18-29 ===")
        print(tradeoff_jovens(ref, meta["threshold_ks"]).to_string(index=False))

        print("\n=== Experimento: modelo sem idade (mesma aprovação global) ===")
        print(experimento_sem_idade(treino, ref).T.to_string())


if __name__ == "__main__":
    main()
