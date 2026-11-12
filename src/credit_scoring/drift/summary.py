"""Consolida os JSON do Evidently em uma tabela PSI × mês."""

import json
from pathlib import Path

import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.drift.reports import REPORTS_DIR

SUMMARY_FILE = cfg.ROOT / "reports" / "drift_summary.csv"


def extrair(path: Path) -> dict:
    metricas = json.loads(path.read_text(encoding="utf-8"))["metrics"]
    linha = {"mes": path.stem}
    for m in metricas:
        tipo = m["config"]["type"].rsplit(":", 1)[-1]
        if tipo == "DriftedColumnsCount":
            linha["features_em_drift"] = int(m["value"]["count"])
            linha["share_drift"] = round(m["value"]["share"], 4)
        elif tipo == "ValueDrift":
            linha[m["config"]["column"]] = round(m["value"], 4)
    return linha


def main() -> None:
    tabela = pd.DataFrame([extrair(p) for p in sorted(REPORTS_DIR.glob("mes_*.json"))])
    tabela = tabela.set_index("mes")
    tabela.to_csv(SUMMARY_FILE)

    psi = tabela.drop(columns=["features_em_drift", "share_drift"]).T
    with pd.option_context("display.width", 200, "display.max_rows", 50):
        print(tabela[["features_em_drift", "share_drift", "SCORE"]].to_string())
        print("\nPSI por feature (≥ 0,10 atenção | ≥ 0,25 alerta), ordenado por mes_06:")
        print(psi.sort_values("mes_06", ascending=False).to_string())


if __name__ == "__main__":
    main()
