"""Alertas derivados dos eventos do pipeline e relatório automatizado.

- Os alertas são uma visão sobre o log de eventos (fonte única); podem ser
  recalculados para qualquer execução passada.
- Cada alerta tem origem, severidade, regra, valor e ação recomendada.
- O relatório registra todos os alertas (auditoria); a notificação ocorre só
  em escaladas (alerta novo, nível maior ou regressão), para evitar fadiga.
"""

from datetime import UTC, datetime

import pandas as pd

from credit_scoring import config as cfg
from credit_scoring.monitoring import policy
from credit_scoring.monitoring.events import ler_eventos

REPORT_FILE = cfg.ROOT / "reports" / "alerts_latest.md"

ACOES = {
    "gate": "Lote retido. Acionar o responsável pelo sistema de origem; não reprocessar sem correção.",
    "quarentena": "Revisar as linhas em data/quarantine/; corrigir na origem ou descartar.",
    "drift_atencao": "Acompanhar no próximo lote e analisar os segmentos afetados.",
    "drift_alerta": "Abrir análise causal (playbook de governança) e avaliar recalibração do score.",
    "score": "Distribuição de PD mudou: revisar taxa de aprovação e corte com a área de Risco.",
    "fairness": (
        "Disparidade mudou em relação à linha de base documentada: acionar Compliance "
        "e aplicar o gate de fairness antes de qualquer recalibração."
    ),
    "performance": "Degradação confirmada por rótulos: recalibrar ou retreinar; revisar o corte com Risco.",
    "execucao": "Verificar o log da etapa e reexecutar o lote após a correção.",
}

ORIGENS = ["execucao", "contrato", "data_drift", "prediction_drift", "fairness", "performance"]


# ---------------------------------------------------------------- geração


def _alerta(e: dict, origem: str, severidade: str, regra: str, valor, acao: str) -> dict:
    return {
        "lote": e["batch_id"],
        "conhecido_em": e.get("avaliado_em", e["batch_id"]),
        "origem": origem,
        "severidade": severidade,
        "regra": regra,
        "valor": valor,
        "acao": acao,
    }


def gerar_alertas(eventos: list[dict]) -> list[dict]:
    alertas = []
    for e in eventos:
        etapa, status = e["etapa"], e["status"]

        if status == "FALHA":
            alertas.append(
                _alerta(e, "execucao", "ALERTA", f"falha em {etapa}: {e.get('erro')}", None, ACOES["execucao"])
            )

        elif etapa == "contract_gate" and status == "BLOQUEADO":
            alertas.append(_alerta(e, "contrato", "ALERTA", e["motivo"], e["taxa_rejeicao"], ACOES["gate"]))

        elif etapa == "contract_gate" and status == "ACEITO_COM_QUARENTENA":
            alertas.append(
                _alerta(
                    e,
                    "contrato",
                    "ATENÇÃO",
                    "linhas em quarentena",
                    e["linhas_rejeitadas"],
                    ACOES["quarentena"],
                )
            )

        elif etapa == "scoring" and e.get("status_fairness", "ESTÁVEL") != "ESTÁVEL":
            alertas.append(
                _alerta(
                    e,
                    "fairness",
                    e["status_fairness"],
                    "queda de AIR de aprovação",
                    e["queda_air_max"],
                    ACOES["fairness"],
                )
            )

        elif etapa == "drift":
            for f in e["features_alerta"]:
                alertas.append(_alerta(e, "data_drift", "ALERTA", f"PSI {f}", e["psi"][f], ACOES["drift_alerta"]))
            for f in e["features_atencao"]:
                alertas.append(_alerta(e, "data_drift", "ATENÇÃO", f"PSI {f}", e["psi"][f], ACOES["drift_atencao"]))
            if e["status_score"] != "ESTÁVEL":
                alertas.append(
                    _alerta(e, "prediction_drift", e["status_score"], "PSI SCORE", e["psi_score"], ACOES["score"])
                )

        elif etapa == "performance":
            for regra, nivel, valor in [
                ("queda de AUC", e["status_auc"], e["queda_auc"]),
                ("gap de calibração", e["status_calibracao"], e["gap_calibracao"]),
            ]:
                if nivel != "ESTÁVEL":
                    alertas.append(_alerta(e, "performance", nivel, regra, valor, ACOES["performance"]))
            if e.get("status_dispersao", "ESTÁVEL") != "ESTÁVEL":
                alertas.append(
                    _alerta(
                        e,
                        "fairness",
                        e["status_dispersao"],
                        "dispersão de calibração por faixa etária",
                        e["dispersao_calibracao"],
                        ACOES["fairness"],
                    )
                )
    return alertas


# ---------------------------------------------------------------- ordem e notificação


def lotes_da_execucao(eventos: list[dict]) -> list[str]:
    """Lotes na ordem em que foram processados."""
    return list(dict.fromkeys(e["batch_id"] for e in eventos if e["etapa"] == "contract_gate"))


def ordem_cronologica(alertas: list[dict], lotes: list[str] | None = None) -> list[str]:
    """Lotes processados, depois meses extras, e 'flush' por último."""
    conhecidos = {a["conhecido_em"] for a in alertas}
    ordem = list(dict.fromkeys([*(lotes or []), *sorted(conhecidos - {"flush"})]))
    if "flush" in conhecidos:
        ordem.append("flush")
    return ordem


def escaladas(alertas: list[dict], ordem: list[str]) -> list[dict]:
    """Alertas que viram notificação: (origem, regra) nova ou com nível maior que no mês anterior."""
    anterior: dict[tuple, int] = {}
    notificar = []
    for mes in ordem:
        atuais: dict[tuple, tuple[int, dict]] = {}
        for a in alertas:
            if a["conhecido_em"] != mes:
                continue
            chave, nivel = (a["origem"], a["regra"]), policy.NIVEL[a["severidade"]]
            if nivel > atuais.get(chave, (-1, None))[0]:
                atuais[chave] = (nivel, a)
        notificar += [a for chave, (nivel, a) in atuais.items() if nivel > anterior.get(chave, 0)]
        anterior = {chave: nivel for chave, (nivel, _) in atuais.items()}
    return notificar


# ---------------------------------------------------------------- relatório


def relatorio_md(run_id: str, alertas: list[dict], lotes: list[str] | None = None) -> str:
    cab = [
        "# Relatório de alertas",
        "",
        f"- Execução: `{run_id}`",
        f"- Política: `{policy.VERSAO}` (limites em `src/credit_scoring/monitoring/policy.py`; "
        "limites de fairness em `reports/fairness_baseline.json`)",
        f"- Gerado em: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"- Total: {len(alertas)} alertas "
        f"({sum(a['severidade'] == 'ALERTA' for a in alertas)} ALERTA, "
        f"{sum(a['severidade'] == 'ATENÇÃO' for a in alertas)} ATENÇÃO)",
        "",
    ]
    if not alertas:
        return "\n".join([*cab, "Nenhum alerta."])

    ordem = ordem_cronologica(alertas, lotes)
    notif = escaladas(alertas, ordem)

    df = pd.DataFrame(alertas)
    df["conhecido_em"] = pd.Categorical(df["conhecido_em"], categories=ordem, ordered=True)
    df["nivel"] = df["severidade"].map(policy.NIVEL)

    visao = (
        df.pivot_table(index="conhecido_em", columns="origem", values="nivel", aggfunc="max", observed=False)
        .reindex(index=ordem, columns=ORIGENS)
        .fillna(0)
        .astype(int)
        .replace({v: k for k, v in policy.NIVEL.items()})
    )
    notificacoes = pd.DataFrame(notif)[["conhecido_em", "origem", "severidade", "regra", "valor"]]
    detalhe = df.sort_values(["conhecido_em", "nivel"], ascending=[True, False]).drop(columns="nivel")

    return "\n".join(
        [
            *cab,
            "## Visão da operação (pior severidade por origem, no mês em que ficou conhecida)",
            "",
            visao.to_markdown(),
            "",
            "`flush` = rótulos que, em tempo real, ainda não teriam amadurecido.",
            "",
            "## Notificações (somente escaladas)",
            "",
            f"{len(notif)} notificações de {len(alertas)} alertas registrados.",
            "",
            notificacoes.to_markdown(index=False, floatfmt=".4f"),
            "",
            "## Detalhe",
            "",
            detalhe.to_markdown(index=False, floatfmt=".4f"),
        ]
    )


def escrever_relatorio(run_id: str) -> list[dict]:
    eventos = ler_eventos(run_id)
    alertas = gerar_alertas(eventos)
    REPORT_FILE.write_text(relatorio_md(run_id, alertas, lotes_da_execucao(eventos)), encoding="utf-8")
    return alertas
