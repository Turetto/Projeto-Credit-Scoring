"""Simula 7 meses de produção sob choque macroeconômico.

Mecanismos (cumulativos ao longo dos meses):
1. Inflação: crédito e bem sobem π; salários repassam só 60% (renda real cai).
2. Aperto monetário: juros maiores elevam a parcela (+ρ) para o mesmo crédito.
3. Expansão comercial: mix mais jovem e com score de bureau menor
   (covariate shift: muda P(X), preserva P(y|X)).
4. Desemprego pós-concessão: inadimplência sobe entre assalariados com maior
   comprometimento real de renda, invisível nas features (concept drift).
mes_00 é o controle negativo: amostra uniforme, sem alteração.
"""

import json

import numpy as np
import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.contracts.schema import DIAS_ANO

INCOMING_DIR = cfg.PRODUCTION_DIR / "incoming"
LABELS_DIR = cfg.PRODUCTION_DIR / "labels"
CONFIG_FILE = cfg.ROOT / "reports" / "simulation_config.json"

N_POR_MES = 4_000
REPASSE_SALARIAL = 0.6
ASSALARIADOS = ["Working", "Commercial associate", "State servant"]

# mês: (inflação acumulada π, choque de juros ρ, intensidade do novo perfil s, desemprego δ)
CENARIO = {
    0: (0.00, 0.00, 0.00, 0.00),
    1: (0.03, 0.02, 0.10, 0.00),
    2: (0.06, 0.04, 0.20, 0.01),
    3: (0.10, 0.07, 0.35, 0.02),
    4: (0.15, 0.10, 0.50, 0.03),
    5: (0.20, 0.12, 0.65, 0.04),
    6: (0.25, 0.15, 0.80, 0.05),
}


def _z(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std()


def novo_perfil(bloco: pd.DataFrame, s: float, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Reamostra favorecendo clientes mais jovens e com score menor (s=0 → uniforme)."""
    idade = -bloco["DAYS_BIRTH"] / DIAS_ANO
    score = bloco["EXT_SOURCE_2"].fillna(bloco["EXT_SOURCE_2"].median())
    risco = (-_z(idade) - _z(score)) / 2
    w = np.exp(s * risco).to_numpy()
    idx = rng.choice(len(bloco), size=n, replace=False, p=w / w.sum())
    return bloco.iloc[idx].reset_index(drop=True)


def desemprego(df: pd.DataFrame, delta: float, mediana_ref: float, rng: np.random.Generator) -> pd.Series:
    """Assalariados adimplentes viram default com prob. δ × comprometimento real relativo."""
    if delta == 0:
        return df[cfg.TARGET]
    comprometimento = (df["AMT_ANNUITY"] / df["AMT_INCOME_TOTAL"]) / mediana_ref
    p = delta * comprometimento.clip(0.5, 2.0)
    elegivel = df["NAME_INCOME_TYPE"].isin(ASSALARIADOS) & (df[cfg.TARGET] == 0)
    vira_default = elegivel & (rng.random(len(df)) < p)
    return df[cfg.TARGET].where(~vira_default, 1)


def inflacao(df: pd.DataFrame, pi: float, rho: float) -> pd.DataFrame:
    out = df.copy()
    out["AMT_INCOME_TOTAL"] = out["AMT_INCOME_TOTAL"] * (1 + REPASSE_SALARIAL * pi)
    out["AMT_CREDIT"] = out["AMT_CREDIT"] * (1 + pi)
    out["AMT_GOODS_PRICE"] = out["AMT_GOODS_PRICE"] * (1 + pi)
    out["AMT_ANNUITY"] = out["AMT_ANNUITY"] * (1 + pi) * (1 + rho)
    return out


def main() -> None:
    pool = pd.read_parquet(cfg.PRODUCTION_DIR / "pool.parquet")
    ref = pd.read_parquet(cfg.REFERENCE_DIR / "train.parquet")
    mediana_ref = (ref["AMT_ANNUITY"] / ref["AMT_INCOME_TOTAL"]).median()
    rng = np.random.default_rng(cfg.SEED)

    embaralhado = pool.sample(frac=1, random_state=cfg.SEED).reset_index(drop=True)
    blocos = np.array_split(np.arange(len(embaralhado)), len(CENARIO))

    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    meses = {}

    for (mes, (pi, rho, s, delta)), pos in zip(CENARIO.items(), blocos, strict=True):
        df = novo_perfil(embaralhado.iloc[pos], s, N_POR_MES, rng)
        df[cfg.TARGET] = desemprego(df, delta, mediana_ref, rng)  # antes da inflação: risco real
        df = inflacao(df, pi, rho)

        nome = f"mes_{mes:02d}"
        df.drop(columns=[cfg.TARGET]).to_parquet(INCOMING_DIR / f"{nome}.parquet", index=False)
        df[[cfg.ID_COL, cfg.TARGET]].to_parquet(LABELS_DIR / f"{nome}.parquet", index=False)

        meses[nome] = {
            "inflacao": pi,
            "choque_juros": rho,
            "novo_perfil": s,
            "desemprego": delta,
            "taxa_default": round(float(df[cfg.TARGET].mean()), 4),
            "idade_media": round(float((-df["DAYS_BIRTH"] / DIAS_ANO).mean()), 1),
            "ext_source_2_media": round(float(df["EXT_SOURCE_2"].mean()), 3),
            "renda_mediana": float(df["AMT_INCOME_TOTAL"].median()),
        }
        print(nome, meses[nome])

    CONFIG_FILE.write_text(
        json.dumps(
            {"n_por_mes": N_POR_MES, "repasse_salarial": REPASSE_SALARIAL, "meses": meses},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
