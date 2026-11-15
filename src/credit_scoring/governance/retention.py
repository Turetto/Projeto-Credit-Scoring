"""Política de retenção e expurgo (arts. 15 e 16 LGPD).

Padrão seguro: simulação (lista e registra). A eliminação só ocorre com --executar.
Prazos contados a partir da última modificação do arquivo.
"""

import argparse
import time
from pathlib import Path

from credit_scoring.contracts.gate import ACCEPTED_DIR, INCOMING_DIR, QUARANTINE_DIR
from credit_scoring.monitoring.events import novo_run_id, registrar

DIA = 86_400
RETENCAO_DIAS: dict[Path, int] = {
    QUARANTINE_DIR: 30,  # corrigir a origem e reprocessar
    INCOMING_DIR: 90,  # janela de reprocessamento; depois, scored/ é o registro da decisão
    ACCEPTED_DIR: 90,
}


def vencidos(agora: float) -> list[Path]:
    alvos = []
    for pasta, dias in RETENCAO_DIAS.items():
        if not pasta.exists():
            continue
        for arq in sorted(pasta.iterdir()):
            if arq.is_file() and arq.name != ".gitkeep" and agora - arq.stat().st_mtime > dias * DIA:
                alvos.append(arq)
    return alvos


def expurgar(executar: bool = False, agora: float | None = None) -> list[Path]:
    alvos = vencidos(time.time() if agora is None else agora)
    if executar:
        for arq in alvos:
            arq.unlink()
    registrar(
        "retencao",
        "*",
        novo_run_id(),
        "EXECUTADO" if executar else "SIMULADO",
        arquivos=len(alvos),
        por_pasta={p.name: sum(a.parent == p for a in alvos) for p in RETENCAO_DIAS},
    )
    return alvos


def main() -> None:
    parser = argparse.ArgumentParser(description="Expurgo de dados vencidos (padrão: simulação)")
    parser.add_argument("--executar", action="store_true", help="apaga de fato os arquivos vencidos")
    args = parser.parse_args()

    alvos = expurgar(executar=args.executar)
    acao = "Apagados" if args.executar else "Seriam apagados (simulação)"
    print(f"{acao}: {len(alvos)} arquivo(s)")
    for arq in alvos:
        print(f"  {arq.parent.name}/{arq.name}")


if __name__ == "__main__":
    main()
