from credit_scoring.monitoring.alerts import gerar_alertas, relatorio_md


def _ev(etapa, status="SUCESSO", lote="mes_01", **kw):
    return {"etapa": etapa, "status": status, "batch_id": lote, "run_id": "r", **kw}


def test_gate_bloqueado_e_performance_degradada_geram_alerta():
    eventos = [
        _ev("contract_gate", "BLOQUEADO", motivo="falha estrutural de schema", taxa_rejeicao=0.0),
        _ev(
            "performance",
            lote="mes_02",
            avaliado_em="mes_05",
            status_auc="ALERTA",
            queda_auc=0.05,
            status_calibracao="ESTÁVEL",
            gap_calibracao=0.001,
        ),
    ]
    alertas = gerar_alertas(eventos)
    assert [(a["origem"], a["severidade"]) for a in alertas] == [
        ("contrato", "ALERTA"),
        ("performance", "ALERTA"),
    ]
    assert alertas[1]["conhecido_em"] == "mes_05"  # alerta de performance só existe quando o rótulo chega


def test_drift_estavel_nao_gera_alerta_e_relatorio_vazio():
    eventos = [
        _ev("drift", features_alerta=[], features_atencao=[], psi={}, psi_score=0.01, status_score="ESTÁVEL")
    ]
    assert gerar_alertas(eventos) == []
    assert "Nenhum alerta" in relatorio_md("r", [])


def test_visao_inclui_meses_sem_alerta_e_flush_por_ultimo():
    eventos = [
        _ev(
            "drift",
            lote="mes_02",
            features_alerta=[],
            features_atencao=["AGE_YEARS"],
            psi={"AGE_YEARS": 0.12},
            psi_score=0.01,
            status_score="ESTÁVEL",
        ),
        _ev(
            "performance",
            lote="mes_02",
            avaliado_em="flush",
            status_auc="ALERTA",
            queda_auc=0.05,
            status_calibracao="ESTÁVEL",
            gap_calibracao=0.001,
        ),
    ]
    visao = relatorio_md("r", gerar_alertas(eventos), ["mes_00", "mes_01", "mes_02"]).split("## Detalhe")[0]
    assert visao.index("mes_00") < visao.index("mes_02") < visao.index("flush")
    assert "prediction_drift" in visao
