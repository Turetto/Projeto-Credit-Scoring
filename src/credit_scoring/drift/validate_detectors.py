import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from credit_scoring import config as cfg
from credit_scoring.data.features import MODEL_FEATURES
from credit_scoring.drift.score_batches import SCORED_DIR
from credit_scoring.drift.simulate import N_POR_MES
from credit_scoring.drift.stats import eh_categorica, ks, psi
from credit_scoring.drift.summary import SUMMARY_FILE

OUT_FILE = cfg.ROOT / "reports" / "detector_validation.csv"
N_NULA = 200
COLUNAS = [*MODEL_FEATURES, "SCORE"]


def distribuicao_nula(ref: pd.DataFrame, fonte: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """PSI sob H0: amostras sem drift, do tamanho de um mês, contra a referência."""
    linhas = []
    for _ in range(N_NULA):
        amostra = fonte.sample(N_POR_MES, random_state=int(rng.integers(1_000_000)))
        linhas.append({c: psi(ref[c], amostra[c]) for c in MODEL_FEATURES})
    return pd.DataFrame(linhas)


def main() -> None:
    ref = pd.read_parquet(cfg.REFERENCE_DIR / "test_scored.parquet")
    treino = pd.read_parquet(cfg.REFERENCE_DIR / "train_clean.parquet")
    evidently = pd.read_csv(SUMMARY_FILE, index_col="mes")
    h0 = distribuicao_nula(ref, treino, np.random.default_rng(cfg.SEED))

    linhas = []
    for path in sorted(SCORED_DIR.glob("mes_*.parquet")):
        cur = pd.read_parquet(path)
        for c in COLUNAS:
            d, pval = (np.nan, np.nan) if eh_categorica(ref[c]) else ks(ref[c], cur[c])
            linhas.append(
                {
                    "mes": path.stem,
                    "coluna": c,
                    "psi_evidently": evidently.loc[path.stem, c],
                    "psi_proprio": round(psi(ref[c], cur[c]), 4),
                    "ks_d": round(d, 4),
                    "ks_p": pval,
                    "psi_h0_p99": round(h0[c].quantile(0.99), 4) if c in h0 else np.nan,
                }
            )
    tab = pd.DataFrame(linhas)
    tab.to_csv(OUT_FILE, index=False)

    print("=== 1. Distribuição nula (n = 4.000, sem drift) ===")
    print(f"Maior p99 de PSI entre as features: {h0.quantile(0.99).max():.4f}")
    for limite in (0.10, 0.25):
        taxa = (h0.max(axis=1) >= limite).mean()
        print(f"Falso alarme (alguma feature ≥ {limite:.2f}): {taxa:.1%}")

    print("\n=== 2. Concordância Evidently × próprio ===")
    rho = spearmanr(tab["psi_evidently"], tab["psi_proprio"]).statistic
    print(f"Spearman (todas as feature-mês): {rho:.3f}")
    for limite in (0.10, 0.25):
        acordo = ((tab["psi_evidently"] >= limite) == (tab["psi_proprio"] >= limite)).mean()
        print(f"Mesma decisão em {limite:.2f}: {acordo:.1%}")

    with pd.option_context("display.width", 200, "display.float_format", "{:.4g}".format):
        print("\n=== 3. mes_06: Evidently × próprio × KS ===")
        m6 = tab[tab["mes"] == "mes_06"].set_index("coluna")
        print(m6.drop(columns="mes").sort_values("psi_evidently", ascending=False).head(10).to_string())

        print("\n=== 4. ANNUITY_CREDIT_RATIO ao longo dos meses ===")
        acr = tab[tab["coluna"] == "ANNUITY_CREDIT_RATIO"].set_index("mes")
        print(acr[["psi_evidently", "psi_proprio", "ks_d", "ks_p"]].T.to_string())


if __name__ == "__main__":
    main()
