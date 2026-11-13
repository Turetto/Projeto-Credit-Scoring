"""Eventos estruturados do pipeline (JSON Lines).

Esquema mínimo de todo evento:
  timestamp, run_id, batch_id, etapa, status, duracao_ms + campos da etapa.

Regra de privacidade: eventos carregam apenas contagens e metadados,
nunca valores de linhas (esses ficam na quarentena, em data/).
"""

import json
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from credit_scoring import config as cfg

LOG_FILE = cfg.ROOT / "logs" / "pipeline.jsonl"


def novo_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]


def registrar(etapa: str, batch_id: str, run_id: str, status: str, **campos) -> dict:
    evento = {
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "run_id": run_id,
        "batch_id": batch_id,
        "etapa": etapa,
        "status": status,
        **campos,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False, default=str) + "\n")
    return evento


@contextmanager
def etapa(nome: str, batch_id: str, run_id: str) -> Iterator[dict]:
    """Cronometra a etapa e registra o resultado.

    Uso:
        with etapa("scoring", batch_id, run_id) as ev:
            ...
            ev["linhas"] = len(df)          # campos extras do evento
            ev["status"] = "BLOQUEADO"      # opcional; padrão = SUCESSO
    Em exceção: registra FALHA com o tipo do erro e relança.
    """
    campos: dict = {}
    t0 = time.perf_counter()
    try:
        yield campos
    except Exception as exc:
        registrar(
            nome,
            batch_id,
            run_id,
            "FALHA",
            duracao_ms=int((time.perf_counter() - t0) * 1000),
            erro=type(exc).__name__,
            mensagem=str(exc)[:300],
        )
        raise
    status = campos.pop("status", "SUCESSO")
    registrar(nome, batch_id, run_id, status, duracao_ms=int((time.perf_counter() - t0) * 1000), **campos)


def ler_eventos(run_id: str | None = None) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    linhas = LOG_FILE.read_text(encoding="utf-8").splitlines()
    eventos = [json.loads(x) for x in linhas if x.strip()]
    return [e for e in eventos if run_id is None or e["run_id"] == run_id]
