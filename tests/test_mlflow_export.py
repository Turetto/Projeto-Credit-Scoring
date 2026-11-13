import mlflow
from mlflow import MlflowClient

from credit_scoring.monitoring import events
from credit_scoring.monitoring.mlflow_export import EXP_MONITORAMENTO, exportar_run


def test_drift_e_exportado_com_step_do_mes(tmp_path, monkeypatch):
    monkeypatch.setattr(events, "LOG_FILE", tmp_path / "pipeline.jsonl")
    mlflow.set_tracking_uri(f"sqlite:///{(tmp_path / 't.db').as_posix()}")

    for mes, valor in [(0, 0.01), (3, 0.30)]:
        events.registrar(
            "drift",
            f"mes_{mes:02d}",
            "r1",
            "SUCESSO",
            psi={"AMT_CREDIT": valor},
            ks_d={},
            features_alerta=[],
            features_atencao=[],
            psi_score=0.0,
            status_drift="ESTÁVEL",
            status_score="ESTÁVEL",
        )
    exportar_run("r1")

    run = mlflow.search_runs(experiment_names=[EXP_MONITORAMENTO], output_format="list")[0]
    historico = MlflowClient().get_metric_history(run.info.run_id, "psi_AMT_CREDIT")
    assert sorted((m.step, m.value) for m in historico) == [(0, 0.01), (3, 0.30)]
