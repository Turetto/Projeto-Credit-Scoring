"""Política de monitoramento: fonte única dos limites.

Fixada na 2.1 (antes da simulação); validada na 2.5 (0% de falso alarme
sob H0 com n = 4.000 para PSI ≥ 0,10).
"""

PSI_ATENCAO, PSI_ALERTA = 0.10, 0.25
QUEDA_AUC = (0.02, 0.03)  # (atenção, alerta)
GAP_CALIBRACAO = (0.01, 0.02)  # (atenção, alerta), em valor absoluto
LAG_ROTULOS = 3  # meses até a inadimplência ser observável


def classificar(valor: float, atencao: float, alerta: float) -> str:
    if valor >= alerta:
        return "ALERTA"
    return "ATENÇÃO" if valor >= atencao else "ESTÁVEL"


VERSAO = "v2"  # v1 (2.1): PSI/AUC/gap · v2 (3.5): + materialidade nas variáveis nominais

# Variáveis monetárias nominais derivam com a inflação; só é alerta se a mudança for material.
VARIAVEIS_NOMINAIS = ["AMT_CREDIT", "AMT_ANNUITY", "AMT_GOODS_PRICE", "AMT_INCOME_TOTAL"]
MATERIALIDADE_NOMINAL = 0.05  # |Δ mediana| mínimo vs referência

NIVEL = {"ESTÁVEL": 0, "ATENÇÃO": 1, "ALERTA": 2}
