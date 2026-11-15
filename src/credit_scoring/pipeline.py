"""Orquestrador batch.

Para cada lote: gate → scoring (+ fairness de aprovação) → drift (sem rótulos).
Performance é avaliada com atraso: ao processar o mês t, avalia-se t LAG_ROTULOS
(+ dispersão de calibração por faixa etária).
"""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.contracts.gate import ACCEPTED_DIR, INCOMING_DIR, run_gate
from credit_scoring.data.features import MODEL_FEATURES
from credit_scoring.drift.score_batches import SCORED_DIR, performance, pontuar
from credit_scoring.drift.simulate import LABELS_DIR
from credit_scoring.drift.stats import eh_categorica, ks, psi
from credit_scoring.governance.fairness import (
    BASELINE_FILE,
    air_aprovacao,
    dispersao_calibracao,
    queda_air,
)
from credit_scoring.model.train import METRICS_FILE, MODELS_DIR
from credit_scoring.monitoring import policy
from credit_scoring.monitoring.events import etapa, ler_eventos, novo_run_id

COLUNAS_DRIFT = [*MODEL_FEATURES, "SCORE"]


# ---------------------------------------------------------------- medições


def medir_drift(ref: pd.DataFrame, cur: pd.DataFrame) -> dict:
    psis = {c: round(psi(ref[c], cur[c]), 4) for c in COLUNAS_DRIFT}
    ks_d = {c: round(ks(ref[c], cur[c])[0], 4) for c in COLUNAS_DRIFT if not eh_categorica(ref[c])}
    delta = {c: round(float(cur[c].median() / ref[c].median() - 1), 4) for c in policy.VARIAVEIS_NOMINAIS}

    niveis, imateriais = {}, []
    for c, valor in psis.items():
        if c == "SCORE":
            continue
        nivel = policy.classificar(valor, policy.PSI_ATENCAO, policy.PSI_ALERTA)
        if c in delta and nivel != "ESTÁVEL" and abs(delta[c]) < policy.MATERIALIDADE_NOMINAL:
            imateriais.append(c)  # mudança estatística sem relevância econômica
            nivel = "ESTÁVEL"
        niveis[c] = nivel

    return {
        "politica": policy.VERSAO,
        "psi": psis,
        "ks_d": ks_d,
        "delta_mediana": delta,
        "imateriais": sorted(imateriais),
        "features_atencao": sorted(c for c, n in niveis.items() if n == "ATENÇÃO"),
        "features_alerta": sorted(c for c, n in niveis.items() if n == "ALERTA"),
        "psi_score": psis["SCORE"],
        "status_drift": max(niveis.values(), key=policy.NIVEL.get),
        "status_score": policy.classificar(psis["SCORE"], policy.PSI_ATENCAO, policy.PSI_ALERTA),
    }


def avaliar_performance(lote: str, avaliado_em: str, run_id: str, auc_ref: float, base_fair: dict | None) -> None:
    labels_path = LABELS_DIR / f"{lote}.parquet"
    if not labels_path.exists():
        return
    with etapa("performance", lote, run_id) as ev:
        scored = pd.read_parquet(SCORED_DIR / f"{lote}.parquet")
        labels = pd.read_parquet(labels_path)
        r = performance(scored, labels, auc_ref)
        ev.update({k: round(float(v), 4) if isinstance(v, float) else v for k, v in r.items()})
        ev["avaliado_em"] = avaliado_em
        if base_fair:
            disp = dispersao_calibracao(scored.merge(labels, on=cfg.ID_COL))
            ev.update(
                dispersao_calibracao=round(disp, 4),
                status_dispersao=policy.classificar(disp, *base_fair["limites"]["dispersao_calibracao"]),
            )


# ---------------------------------------------------------------- execução


def run(lotes: list[Path], run_id: str, flush: bool) -> None:
    meta = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    modelo = joblib.load(MODELS_DIR / "baseline.joblib")
    ref = pd.read_parquet(cfg.REFERENCE_DIR / "test_scored.parquet")
    base_fair = json.loads(BASELINE_FILE.read_text(encoding="utf-8")) if BASELINE_FILE.exists() else None
    auc_ref = meta["teste"]["auc"]
    SCORED_DIR.mkdir(parents=True, exist_ok=True)
    processados: list[str] = []

    for path in lotes:
        lote = path.stem
        if run_gate(pd.read_parquet(path), lote, run_id).status == "BLOQUEADO":
            continue

        with etapa("scoring", lote, run_id) as ev:
            scored = pontuar(pd.read_parquet(ACCEPTED_DIR / path.name), modelo, meta["threshold_ks"])
            scored.to_parquet(SCORED_DIR / path.name, index=False)
            ev.update(
                linhas=len(scored),
                pd_media=round(float(scored["SCORE"].mean()), 4),
                taxa_aprovacao=round(float(scored["APROVADO"].mean()), 4),
            )
            if base_fair:
                q = queda_air(air_aprovacao(scored), base_fair["air"])
                ev.update(
                    queda_air_max=round(q, 4), status_fairness=policy.classificar(q, *base_fair["limites"]["queda_air"])
                )

        with etapa("drift", lote, run_id) as ev:
            ev.update(medir_drift(ref, scored))

        processados.append(lote)
        if len(processados) > policy.LAG_ROTULOS:  # rótulos do mês t − LAG amadureceram
            avaliar_performance(processados[-(policy.LAG_ROTULOS + 1)], lote, run_id, auc_ref, base_fair)

    if flush:  # simula o amadurecimento dos rótulos restantes
        for lote in processados[-policy.LAG_ROTULOS :]:
            avaliar_performance(lote, "flush", run_id, auc_ref, base_fair)


def resumo(run_id: str) -> pd.DataFrame:
    linhas = []
    for e in ler_eventos(run_id):
        if e["status"] == "FALHA":
            linhas.append(
                {
                    "lote": e["batch_id"],
                    "etapa": e["etapa"],
                    "status": "FALHA",
                    "detalhe": f"{e.get('erro')}: {e.get('mensagem')}",
                }
            )
        elif e["etapa"] == "contract_gate":
            linhas.append(
                {
                    "lote": e["batch_id"],
                    "etapa": "contract_gate",
                    "status": e["status"],
                    "detalhe": f"{e.get('duracao_ms')} ms",
                }
            )
        elif e["etapa"] == "scoring":
            fair = f" queda_air={e['queda_air_max']} ({e['status_fairness']})" if "queda_air_max" in e else ""
            linhas.append(
                {
                    "lote": e["batch_id"],
                    "etapa": "scoring",
                    "status": e["status"],
                    "detalhe": f"{e.get('duracao_ms')} ms{fair}",
                }
            )
        elif e["etapa"] == "drift":
            linhas.append(
                {
                    "lote": e["batch_id"],
                    "etapa": "drift",
                    "status": e["status_drift"],
                    "detalhe": f"alerta={e['features_alerta']} psi_score={e['psi_score']}",
                }
            )
        elif e["etapa"] == "performance":
            disp = (
                f" disp={e['dispersao_calibracao']:+.4f} ({e['status_dispersao']})"
                if "dispersao_calibracao" in e
                else ""
            )
            linhas.append(
                {
                    "lote": e["batch_id"],
                    "etapa": f"perf (em {e['avaliado_em']})",
                    "status": f"auc={e['status_auc']} cal={e['status_calibracao']}",
                    "detalhe": f"auc={e['auc']} gap={e['gap_calibracao']:+.4f}{disp}",
                }
            )
    return pd.DataFrame(linhas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de monitoramento do modelo de crédito")
    parser.add_argument("--padrao", default="mes_*.parquet", help="glob dos lotes em incoming/")
    parser.add_argument("--flush", action="store_true", help="avalia os rótulos restantes ao final")
    parser.add_argument("--mlflow", action="store_true", help="exporta a execução para o MLflow")
    args = parser.parse_args()

    run_id = novo_run_id()
    lotes = sorted(INCOMING_DIR.glob(args.padrao))
    with etapa("pipeline", "*", run_id) as ev:
        ev["lotes"] = [p.stem for p in lotes]
        run(lotes, run_id, args.flush)

    from credit_scoring.monitoring.alerts import REPORT_FILE, escrever_relatorio

    alertas = escrever_relatorio(run_id)

    if args.mlflow:
        from credit_scoring.monitoring.mlflow_export import configurar, exportar_run

        configurar()
        exportar_run(run_id)

    with pd.option_context("display.width", 220, "display.max_colwidth", 110):
        print(resumo(run_id).to_string(index=False))
    print(f"\n{len(alertas)} alertas → {REPORT_FILE.relative_to(cfg.ROOT)}")
    print(f"run_id = {run_id}")


if __name__ == "__main__":
    main()
