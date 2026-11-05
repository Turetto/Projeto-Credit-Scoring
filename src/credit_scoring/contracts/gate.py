"""Gate de ingestão: valida o lote contra o contrato e roteia.

Política híbrida:
- Falha estrutural (coluna/dtype/regra de lote)      → BLOQUEADO
- Taxa de linhas reprovadas > MAX_TAXA_REJEICAO      → BLOQUEADO (erro sistêmico)
- Rejeições isoladas                                 → ACEITO_COM_QUARENTENA
- Nenhuma violação rígida                            → ACEITO
MAX_TAXA_REJEICAO = 0 reproduz a política "tudo ou nada".
"""

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.contracts.run_contract import resumo, run_contract

MAX_TAXA_REJEICAO = 0.01
INCOMING_DIR = cfg.PRODUCTION_DIR / "incoming"
ACCEPTED_DIR = cfg.PRODUCTION_DIR / "accepted"
QUARANTINE_DIR = cfg.DATA_DIR / "quarantine"
LOG_FILE = cfg.ROOT / "logs" / "pipeline.jsonl"


@dataclass
class GateResult:
    batch_id: str
    status: str
    motivo: str
    linhas_entrada: int
    linhas_rejeitadas: int
    taxa_rejeicao: float
    regras_violadas: dict = field(default_factory=dict)
    alertas: dict = field(default_factory=dict)
    duracao_ms: int = 0
    timestamp: str = ""


def _contagens(fc: pd.DataFrame) -> dict:
    return {k: (v if v == "lote" else int(v)) for k, v in resumo(fc).items()}


def _log(result: GateResult) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"etapa": "contract_gate", **asdict(result)}, ensure_ascii=False) + "\n")


def run_gate(df: pd.DataFrame, batch_id: str) -> GateResult:
    t0 = time.perf_counter()
    df = df.reset_index(drop=True)
    rigidas, alertas = run_contract(df)

    estrutural = not rigidas.empty and rigidas["index"].isna().any()
    ruins = (
        pd.Index([], dtype=int) if rigidas.empty else pd.Index(rigidas["index"].dropna().unique()).astype(int)
    )
    taxa = len(ruins) / len(df) if len(df) else 0.0

    if estrutural:
        status, motivo = "BLOQUEADO", "falha estrutural de schema"
    elif taxa > MAX_TAXA_REJEICAO:
        status, motivo = "BLOQUEADO", f"taxa de rejeição {taxa:.1%} > {MAX_TAXA_REJEICAO:.0%}"
    elif len(ruins):
        status, motivo = "ACEITO_COM_QUARENTENA", "rejeições isoladas"
    else:
        status, motivo = "ACEITO", "sem violações rígidas"

    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    ACCEPTED_DIR.mkdir(parents=True, exist_ok=True)
    if status == "BLOQUEADO":
        df.to_parquet(QUARANTINE_DIR / f"{batch_id}.parquet", index=False)
    else:
        if len(ruins):
            df.loc[ruins].to_parquet(QUARANTINE_DIR / f"{batch_id}_linhas.parquet", index=False)
        df.drop(index=ruins).to_parquet(ACCEPTED_DIR / f"{batch_id}.parquet", index=False)
    if not rigidas.empty:
        rigidas.to_csv(QUARANTINE_DIR / f"{batch_id}_failures.csv", index=False)

    result = GateResult(
        batch_id=batch_id,
        status=status,
        motivo=motivo,
        linhas_entrada=len(df),
        linhas_rejeitadas=len(ruins),
        taxa_rejeicao=round(taxa, 4),
        regras_violadas=_contagens(rigidas),
        alertas=_contagens(alertas),
        duracao_ms=int((time.perf_counter() - t0) * 1000),
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    _log(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate de ingestão por contrato de dados")
    parser.add_argument("lotes", nargs="*", type=Path, help="Parquets; padrão: todos em incoming/")
    args = parser.parse_args()
    lotes = args.lotes or sorted(INCOMING_DIR.glob("*.parquet"))

    for path in lotes:
        r = run_gate(pd.read_parquet(path), path.stem)
        print(
            f"{r.batch_id:<22} {r.status:<22} rejeitadas={r.linhas_rejeitadas:>4} "
            f"({r.taxa_rejeicao:.1%})  {r.motivo}"
        )
        if r.regras_violadas:
            print(f"{'':<22} regras: {r.regras_violadas}")


if __name__ == "__main__":
    main()
