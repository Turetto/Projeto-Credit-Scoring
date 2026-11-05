import numpy as np
import pytest

from credit_scoring.contracts.run_contract import resumo, run_contract


def _regras_rigidas(df) -> set[str]:
    rigidas, _ = run_contract(df)
    return set(resumo(rigidas).index)


def _alertas(df) -> set[str]:
    _, alertas = run_contract(df)
    return set(resumo(alertas).index)


def test_lote_valido_passa_sem_alertas(make_batch):
    rigidas, alertas = run_contract(make_batch(5))
    assert rigidas.empty
    assert alertas.empty


@pytest.mark.parametrize(
    ("coluna", "valor", "regra_esperada"),
    [
        ("DAYS_BIRTH", -5000, "DAYS_BIRTH:idade_entre_18_e_100"),
        ("DAYS_EMPLOYED", 100, "DAYS_EMPLOYED:emprego_negativo_ou_sentinela"),
        ("DAYS_EMPLOYED", -20000, "emprego_menor_que_idade"),
        ("AMT_INCOME_TOTAL", 60_000_000.0, "AMT_INCOME_TOTAL:less_than_or_equal_to"),
        ("AMT_INCOME_TOTAL", np.nan, "AMT_INCOME_TOTAL:not_nullable"),
        ("AMT_ANNUITY", np.nan, "AMT_ANNUITY:not_nullable"),
        ("AMT_ANNUITY", 200_000.0, "parcela_menor_que_credito"),
        ("AMT_CREDIT", -1.0, "AMT_CREDIT:greater_than"),
        ("AMT_GOODS_PRICE", np.nan, "bem_obrigatorio_em_cash_loans"),
        ("EXT_SOURCE_1", 1.5, "EXT_SOURCE_1:in_range"),
        ("CNT_CHILDREN", -1, "CNT_CHILDREN:in_range"),
        ("REGION_RATING_CLIENT", 4, "REGION_RATING_CLIENT:isin"),
        ("NAME_INCOME_TYPE", "Self-employed", "NAME_INCOME_TYPE:isin"),
    ],
)
def test_cada_violacao_dispara_exatamente_uma_regra(make_batch, coluna, valor, regra_esperada):
    df = make_batch(3)
    df.loc[0, coluna] = valor
    regras = _regras_rigidas(df)
    assert len(regras) == 1, f"esperada 1 regra, disparadas: {regras}"
    assert next(iter(regras)).startswith(regra_esperada)


def test_id_duplicado_bloqueia(make_batch):
    df = make_batch(3)
    df.loc[1, "SK_ID_CURR"] = df.loc[0, "SK_ID_CURR"]
    assert _regras_rigidas(df) == {"SK_ID_CURR:field_uniqueness"}


def test_coluna_faltando_e_falha_estrutural(make_batch):
    assert "column_in_dataframe" in _regras_rigidas(make_batch(3).drop(columns=["EXT_SOURCE_2"]))


def test_coluna_extra_e_falha_estrutural(make_batch):
    assert "column_in_schema" in _regras_rigidas(make_batch(3).assign(NOVA=1))


def test_target_e_opcional_mas_validado_se_presente(make_batch):
    df = make_batch(2)
    assert not _regras_rigidas(df)  # sem TARGET: ok
    df["TARGET"] = [0, 2]
    assert any(r.startswith("TARGET:isin") for r in _regras_rigidas(df))


def test_alerta_nao_bloqueia(make_batch):
    df = make_batch(3)
    df.loc[0, "CNT_CHILDREN"] = 12
    assert not _regras_rigidas(df)
    assert "alerta_filhos_acima_10" in _alertas(df)


def test_renda_nula_nao_dispara_alerta_de_renda_alta(make_batch):
    df = make_batch(3)
    df.loc[0, "AMT_INCOME_TOTAL"] = np.nan
    assert "alerta_renda_acima_1M" not in _alertas(df)
