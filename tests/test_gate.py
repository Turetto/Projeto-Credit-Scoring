import json

import pandas as pd
import pytest

from credit_scoring.contracts import gate


@pytest.fixture(autouse=True)
def _diretorios_temporarios(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "ACCEPTED_DIR", tmp_path / "accepted")
    monkeypatch.setattr(gate, "QUARANTINE_DIR", tmp_path / "quarantine")
    monkeypatch.setattr(gate, "LOG_FILE", tmp_path / "logs" / "pipeline.jsonl")


def test_lote_limpo_e_aceito(make_batch):
    assert gate.run_gate(make_batch(200), "t").status == "ACEITO"


def test_erro_isolado_vai_para_quarentena(make_batch, tmp_path):
    df = make_batch(200)
    df.loc[0, "DAYS_BIRTH"] = -5000  # 0,5% ≤ 1%
    r = gate.run_gate(df, "t")
    assert r.status == "ACEITO_COM_QUARENTENA"
    assert r.linhas_rejeitadas == 1
    assert len(pd.read_parquet(tmp_path / "accepted" / "t.parquet")) == 199
    assert len(pd.read_parquet(tmp_path / "quarantine" / "t_linhas.parquet")) == 1


def test_erro_sistemico_bloqueia_lote(make_batch, tmp_path):
    df = make_batch(200)
    df.loc[:4, "DAYS_BIRTH"] = -5000  # 2,5% > 1%
    assert gate.run_gate(df, "t").status == "BLOQUEADO"
    assert not (tmp_path / "accepted" / "t.parquet").exists()


def test_schema_quebrado_bloqueia_lote(make_batch):
    r = gate.run_gate(make_batch(10).drop(columns=["EXT_SOURCE_2"]), "t")
    assert r.status == "BLOQUEADO"
    assert "estrutural" in r.motivo


def test_politica_tudo_ou_nada(make_batch, monkeypatch):
    monkeypatch.setattr(gate, "MAX_TAXA_REJEICAO", 0.0)
    df = make_batch(200)
    df.loc[0, "DAYS_BIRTH"] = -5000
    assert gate.run_gate(df, "t").status == "BLOQUEADO"


def test_gate_registra_evento_estruturado(make_batch, tmp_path):
    gate.run_gate(make_batch(10), "t")
    linha = (tmp_path / "logs" / "pipeline.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    evento = json.loads(linha)
    assert evento["etapa"] == "contract_gate"
    assert evento["batch_id"] == "t"
    assert evento["status"] == "ACEITO"
