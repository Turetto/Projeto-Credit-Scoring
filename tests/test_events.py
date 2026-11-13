import json

import pytest

from credit_scoring.monitoring import events


@pytest.fixture(autouse=True)
def _log_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(events, "LOG_FILE", tmp_path / "pipeline.jsonl")


def _eventos() -> list[dict]:
    return [json.loads(x) for x in events.LOG_FILE.read_text(encoding="utf-8").splitlines()]


def test_etapa_com_sucesso_registra_campos_e_duracao():
    with events.etapa("scoring", "mes_01", "r1") as ev:
        ev["linhas"] = 4000
    (e,) = _eventos()
    assert e["status"] == "SUCESSO"
    assert e["linhas"] == 4000
    assert e["duracao_ms"] >= 0


def test_etapa_permite_status_customizado():
    with events.etapa("contract_gate", "mes_01", "r1") as ev:
        ev["status"] = "BLOQUEADO"
    assert _eventos()[0]["status"] == "BLOQUEADO"


def test_falha_e_registrada_e_relancada():
    with pytest.raises(ValueError), events.etapa("scoring", "mes_01", "r1"):
        raise ValueError("modelo corrompido")
    (e,) = _eventos()
    assert (e["status"], e["erro"]) == ("FALHA", "ValueError")
    assert "modelo corrompido" in e["mensagem"]
