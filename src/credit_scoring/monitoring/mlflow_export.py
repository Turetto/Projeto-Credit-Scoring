"""Exporta para o MLflow: (1) o modelo baseline; (2) cada execução do pipeline.

O log de eventos é a fonte da verdade; o MLflow é um destino.
O pipeline não depende do MLflow para rodar.
"""

import argparse
import json
import tempfile
from pathlib import Path

import joblib
import mlflow

from credit_scoring import config as cfg
from credit_scoring.model.train import METRICS_FILE, MODELS_DIR
from credit_scoring.monitoring.events import ler_eventos
from credit_scoring.monitoring.policy import NIVEL

TRACKING_URI = f"sqlite:///{(cfg.ROOT / 'mlflow.db').as_posix()}"
EXP_MODELO = "credit-scoring-modelo"
EXP_MONITORAMENTO = "credit-scoring-monitoramento"
MODELO_REGISTRADO = "credit-scoring-baseline"


ARTEFATOS_FIXOS = [
    cfg.ROOT / "reports" / "simulation_config.json",
    cfg.ROOT / "reports" / "drift" / "mes_00.html",
    cfg.ROOT / "reports" / "drift" / "mes_06.html",
]


def configurar() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)


def _step(batch_id: str) -> int | None:
    try:
        return int(batch_id.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return None


def registrar_modelo() -> None:
    meta = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    mlflow.set_experiment(EXP_MODELO)
    with mlflow.start_run(run_name=f"baseline-{meta['campeao']}"):
        mlflow.log_params(
            {
                "campeao": meta["campeao"],
                "threshold_ks": meta["threshold_ks"],
                "n_features": len(meta["features"]),
                "linhas_treino": meta["linhas_treino"],
            }
        )
        for modelo, m in meta["cv_oof"].items():
            mlflow.log_metrics({f"oof_{modelo}_{k}": v for k, v in m.items()})
        mlflow.log_metrics({f"teste_{k}": v for k, v in meta["teste"].items()})
        mlflow.log_artifact(str(METRICS_FILE))
        mlflow.sklearn.log_model(
            joblib.load(MODELS_DIR / "baseline.joblib"),
            name="modelo",
            registered_model_name=MODELO_REGISTRADO,
        )


def exportar_run(run_id: str) -> None:
    eventos = ler_eventos(run_id)
    if not eventos:
        raise SystemExit(f"Nenhum evento para run_id={run_id}")

    mlflow.set_experiment(EXP_MONITORAMENTO)
    with mlflow.start_run(run_name=run_id):
        mlflow.set_tag("pipeline_run_id", run_id)
        execucoes: dict[str, int] = {}

        for e in eventos:
            chave = f"execucoes_{e['etapa']}_{e['status']}"
            execucoes[chave] = execucoes.get(chave, 0) + 1
            step = _step(e["batch_id"])
            if step is None:
                continue

            if e["etapa"] == "contract_gate":
                mlflow.log_metrics(
                    {
                        "gate_taxa_rejeicao": e["taxa_rejeicao"],
                        "gate_linhas_entrada": e["linhas_entrada"],
                        "gate_bloqueado": int(e["status"] == "BLOQUEADO"),
                        "gate_duracao_ms": e["duracao_ms"],
                    },
                    step=step,
                )
            elif e["etapa"] == "scoring":
                mlflow.log_metrics(
                    {
                        "scoring_pd_media": e["pd_media"],
                        "scoring_taxa_aprovacao": e["taxa_aprovacao"],
                        "scoring_duracao_ms": e["duracao_ms"],
                    },
                    step=step,
                )
            elif e["etapa"] == "drift":
                mlflow.log_metrics({f"psi_{c}": v for c, v in e["psi"].items()}, step=step)
                if e["ks_d"]:
                    mlflow.log_metrics({f"ks_d_{c}": v for c, v in e["ks_d"].items()}, step=step)
                mlflow.log_metrics(
                    {
                        "drift_nivel": NIVEL[e["status_drift"]],
                        "drift_nivel_score": NIVEL[e["status_score"]],
                        "drift_n_features_alerta": len(e["features_alerta"]),
                        "drift_n_features_atencao": len(e["features_atencao"]),
                    },
                    step=step,
                )
            elif e["etapa"] == "performance":
                metricas = {
                    "perf_auc": e["auc"],
                    "perf_gap_calibracao": e["gap_calibracao"],
                    "perf_default_observado": e["default_observado"],
                    "perf_default_aprovados": e["default_aprovados"],
                    "perf_nivel_auc": NIVEL[e["status_auc"]],
                    "perf_nivel_calibracao": NIVEL[e["status_calibracao"]],
                }
                conhecido = _step(e["avaliado_em"])
                if conhecido is not None:
                    metricas["perf_mes_conhecimento"] = conhecido
                mlflow.log_metrics(metricas, step=step)  # série no mês em que a degradação ocorreu

                if conhecido is not None:  # série no mês em que a operação ficou sabendo
                    mlflow.log_metrics(
                        {
                            "operacao_nivel_auc": NIVEL[e["status_auc"]],
                            "operacao_nivel_calibracao": NIVEL[e["status_calibracao"]],
                        },
                        step=conhecido,
                    )

        mlflow.log_metrics(execucoes)
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / f"eventos_{run_id}.jsonl"
            arquivo.write_text(
                "\n".join(json.dumps(e, ensure_ascii=False) for e in eventos), encoding="utf-8"
            )
            mlflow.log_artifact(str(arquivo), artifact_path="eventos")
        for artefato in ARTEFATOS_FIXOS:
            if artefato.exists():
                mlflow.log_artifact(str(artefato), artifact_path="relatorios")


def _ultimo_run_id() -> str:
    pipelines = [e for e in ler_eventos() if e["etapa"] == "pipeline"]
    if not pipelines:
        raise SystemExit("Nenhuma execução do pipeline encontrada no log.")
    return pipelines[-1]["run_id"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta modelo e execuções para o MLflow")
    parser.add_argument("--modelo", action="store_true", help="registra o modelo baseline")
    parser.add_argument("--run-id", help="execução do pipeline a exportar (padrão: a última)")
    args = parser.parse_args()

    configurar()
    if args.modelo:
        registrar_modelo()
    if args.run_id or not args.modelo:
        exportar_run(args.run_id or _ultimo_run_id())


if __name__ == "__main__":
    main()
