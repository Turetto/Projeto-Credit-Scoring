"""Gera lotes de demonstração com falhas injetadas para exercitar o gate."""

import numpy as np
import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.contracts.gate import INCOMING_DIR

N = 1_000


def main() -> None:
    # Produção chega sem rótulo
    pool = pd.read_parquet(cfg.PRODUCTION_DIR / "pool.parquet").drop(columns=[cfg.TARGET])
    rng = np.random.default_rng(cfg.SEED)

    def amostra() -> pd.DataFrame:
        return pool.sample(N, random_state=int(rng.integers(1_000_000))).reset_index(drop=True)

    lotes = {}

    # 1. Limpo → ACEITO
    lotes["lote_01_limpo"] = amostra()

    # 2. Erro isolado (3 menores de idade, 0,3%) → ACEITO_COM_QUARENTENA
    b = amostra()
    b.loc[:2, "DAYS_BIRTH"] = -5000  # ~13,7 anos
    lotes["lote_02_isolado"] = b

    # 3. Erro sistêmico (sistema de origem quebrado) → BLOQUEADO por taxa
    b = amostra()
    b.loc[:99, "AMT_INCOME_TOTAL"] = np.nan  # 10% renda nula
    b.loc[100, "SK_ID_CURR"] = b.loc[101, "SK_ID_CURR"]  # duplicata
    b.loc[200:204, "NAME_INCOME_TYPE"] = "Self-employed"  # categoria fora do domínio
    b.loc[300:302, "AMT_CREDIT"] = -1.0  # crédito negativo
    lotes["lote_03_sistemico"] = b

    # 4. Mudança de schema na origem → BLOQUEADO por estrutura
    lotes["lote_04_schema"] = amostra().drop(columns=["EXT_SOURCE_2"]).assign(NOVA_COLUNA=1)

    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    for nome, df in lotes.items():
        df.to_parquet(INCOMING_DIR / f"{nome}.parquet", index=False)
        print(f"{nome}: {len(df)} linhas")


if __name__ == "__main__":
    main()
