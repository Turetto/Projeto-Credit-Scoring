import pandas as pd
import pytest

from credit_scoring.governance.fairness import dispersao_calibracao, grupos, metricas_grupo, queda_air
from credit_scoring.monitoring.alerts import gerar_alertas


def test_air_e_relativo_ao_grupo_mais_aprovado():
    df = pd.DataFrame(
        {
            "g": ["A"] * 10 + ["B"] * 10,
            "APROVADO": [1] * 8 + [0] * 2 + [1] * 4 + [0] * 6,
            "TARGET": [0, 1] * 10,
            "SCORE": 0.1,
        }
    )
    t = metricas_grupo(df, "g").set_index("grupo")
    assert t.loc["A", "air"] == 1.0
    assert t.loc["B", "air"] == pytest.approx(0.5)


def test_faixas_etarias_e_genero_fora_do_dominio():
    df = pd.DataFrame({"CODE_GENDER": ["F", "M", "XNA"], "AGE_YEARS": [18.0, 29.99, 60.0]})
    g = grupos(df)
    assert g["faixa_etaria"].astype(str).tolist() == ["18-29", "18-29", "60+"]
    assert g["genero"].isna().tolist() == [False, False, True]


def test_queda_air_e_a_maior_queda_entre_grupos():
    base = {"genero": {"F": 1.0, "M": 0.88}, "faixa_etaria": {"18-29": 0.57}}
    atual = {"genero": {"F": 1.0, "M": 0.85}, "faixa_etaria": {"18-29": 0.47}}
    assert queda_air(atual, base) == pytest.approx(0.10)


def test_dispersao_e_a_amplitude_dos_gaps_entre_faixas():
    df = pd.DataFrame(
        {
            "CODE_GENDER": "F",
            "AGE_YEARS": [25.0] * 4 + [50.0] * 4,
            "TARGET": [1, 0, 0, 0] + [0, 0, 0, 0],  # default 25% e 0%
            "SCORE": [0.20] * 4 + [0.01] * 4,  # previsto 20% e 1%
        }
    )
    assert dispersao_calibracao(df) == pytest.approx(0.06)  # (+5 p.p.) − (−1 p.p.)


def test_queda_de_air_gera_alerta_de_fairness():
    eventos = [
        {
            "etapa": "scoring",
            "status": "SUCESSO",
            "batch_id": "mes_03",
            "run_id": "r",
            "status_fairness": "ALERTA",
            "queda_air_max": 0.12,
        }
    ]
    (a,) = gerar_alertas(eventos)
    assert (a["origem"], a["severidade"]) == ("fairness", "ALERTA")
