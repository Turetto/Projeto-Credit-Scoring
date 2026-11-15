import os
import time

import pytest

from credit_scoring.governance import retention
from credit_scoring.monitoring import events


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    q = tmp_path / "quarantine"
    q.mkdir()
    agora = time.time()
    for nome, idade_dias in [("velho.parquet", 31), ("novo.parquet", 5), (".gitkeep", 400)]:
        arq = q / nome
        arq.write_text("x")
        os.utime(arq, (agora - idade_dias * retention.DIA,) * 2)
    monkeypatch.setattr(retention, "RETENCAO_DIAS", {q: 30})
    monkeypatch.setattr(events, "LOG_FILE", tmp_path / "pipeline.jsonl")
    return q, agora


def test_simulacao_lista_vencidos_sem_apagar(pasta):
    q, agora = pasta
    assert retention.expurgar(agora=agora) == [q / "velho.parquet"]
    assert (q / "velho.parquet").exists()


def test_execucao_apaga_so_vencidos_e_preserva_gitkeep(pasta):
    q, agora = pasta
    retention.expurgar(executar=True, agora=agora)
    assert not (q / "velho.parquet").exists()
    assert (q / "novo.parquet").exists()
    assert (q / ".gitkeep").exists()


def test_expurgo_e_registrado_sem_conteudo(pasta, tmp_path):
    _, agora = pasta
    retention.expurgar(agora=agora)
    log = (tmp_path / "pipeline.jsonl").read_text(encoding="utf-8")
    assert '"etapa": "retencao"' in log
    assert "velho.parquet" not in log  # registra contagens, não nomes nem conteúdo
