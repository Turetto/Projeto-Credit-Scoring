import json

import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.contracts.run_contract import resumo, run_contract
from credit_scoring.data.features import build_features

SUMMARY_FILE = cfg.ROOT / "reports" / "cleaning_summary.json"


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rigidas, _ = run_contract(df)
    if rigidas.empty:
        return df, {"linhas_entrada": len(df), "linhas_removidas": 0, "por_regra": {}}

    if rigidas["index"].isna().any():  # falha de schema/lote: não se resolve removendo linhas
        raise RuntimeError("Falha estrutural na referência:\n" + resumo(rigidas).to_string())

    idx = pd.Index(rigidas["index"].unique()).astype(int)
    limpo = df.drop(index=idx)
    info = {
        "linhas_entrada": len(df),
        "linhas_removidas": len(idx),
        "por_regra": {k: int(v) for k, v in resumo(rigidas).items()},
    }
    return limpo, info


def main() -> None:
    summary = {}
    for nome in ["train", "test"]:
        df = pd.read_parquet(cfg.REFERENCE_DIR / f"{nome}.parquet")
        limpo, info = clean(df)

        revalidacao, _ = run_contract(limpo)
        assert revalidacao.empty, f"{nome}: referência limpa ainda viola o contrato"

        build_features(limpo).to_parquet(cfg.REFERENCE_DIR / f"{nome}_clean.parquet", index=False)
        summary[nome] = info
        print(
            f"{nome:<6} entrada={info['linhas_entrada']:>7,}  removidas={info['linhas_removidas']:>3}"
            f"por_regra={info['por_regra']}"
        )

    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResumo salvo em {SUMMARY_FILE.relative_to(cfg.ROOT)}")


if __name__ == "__main__":
    main()
