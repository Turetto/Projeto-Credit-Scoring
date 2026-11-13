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
