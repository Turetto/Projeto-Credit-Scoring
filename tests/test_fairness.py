import pandas as pd
import pytest

from credit_scoring.governance.fairness import grupos, metricas_grupo


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
