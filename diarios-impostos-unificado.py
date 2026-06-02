"""
Consolida publicações sobre impostos em 5 diários oficiais num único arquivo CSV.

Fontes:
  - DOU (União)
  - DO Recife
  - DO Pernambuco (estado — CEPE; credenciais opcionais)
  - DO São Paulo (município)
  - DO São Paulo (estado)

Execução:
  python3 diarios-impostos-unificado.py
  python3 diarios-impostos-unificado.py --days 7
  python3 diarios-impostos-unificado.py --from 2026-05-29 --to 2026-06-01

Variáveis de ambiente:
  DIARIOS_DAYS_BACK=7
  DIARIOS_DATE_FROM=2026-05-29
  DIARIOS_DATE_TO=2026-06-01
  DIARIOS_SEARCH_TERMS=imposto|ICMS|ISS
  DIARIOS_FILTER_DOU_DEPARTMENTS=true
  CEPE_AUTH_TOKEN=...          # opcional — DO PE
  CEPE_BASIC_USER / CEPE_BASIC_PASSWORD
"""

from __future__ import annotations

import argparse
import csv
import glob as _glob
import os as _os
import sys
from datetime import date, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from diarios_impostos_unificado_pipeline import (  # noqa: E402
    DiariosUnificadoConfig,
    run_unificado_pipeline,
)


def _parse_cli_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _localizar_csv_mais_recente(csv_hint: str | None = None) -> str | None:
    if csv_hint and _os.path.isfile(csv_hint):
        return csv_hint

    candidatos: list[str] = []
    candidatos.extend(_glob.glob(str(_ROOT / "*.csv")))
    candidatos.extend(_glob.glob(str(_ROOT / "saida" / "diarios" / "*.csv")))
    candidatos.extend(_glob.glob("*.csv"))

    if not candidatos:
        return None

    return sorted(set(candidatos), key=_os.path.getmtime, reverse=True)[0]


def gerar_dados_extraidos_workflow(csv_hint: str | None = None) -> None:
    # ============================================================
    # BLOCO ADICIONAL: Gera dados_extraidos.txt para integração com workflow
    # ============================================================
    csv_file = _localizar_csv_mais_recente(csv_hint)
    if not csv_file:
        print("[WORKFLOW] ERRO: Nenhum CSV encontrado")
        return

    with open(csv_file, "r", encoding="utf-8-sig", newline="") as _f:
        _reader = csv.DictReader(_f)
        _rows = list(_reader)

    destino = _ROOT / "dados_extraidos.txt"
    with open(destino, "w", encoding="utf-8") as _out:
        _out.write(f"TOTAL: {len(_rows)} registros\n")
        _out.write("---DADOS---\n")
        for _i, _r in enumerate(_rows):
            _linha = (
                f"[{_i + 1}] {_r.get('data_publicacao', '')}|"
                f"{_r.get('tipo_ato', '')}|"
                f"{(_r.get('orgao', '') or '')[:60]}|"
                f"{(_r.get('titulo', '') or '')[:80]}|"
                f"{_r.get('termo_busca', '')}|"
                f"{(_r.get('resumo', '') or '')[:100].replace(chr(10), ' ')}"
            )
            _out.write(_linha + "\n")
        _out.write("---FIM---\n")

    print(f"[WORKFLOW] dados_extraidos.txt gerado com {len(_rows)} registros")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Busca impostos em 5 diários oficiais e gera CSV único."
    )
    parser.add_argument("--days", type=int, help="Últimos N dias (inclui hoje).")
    parser.add_argument("--from", dest="date_from", help="Data inicial (YYYY-MM-DD).")
    parser.add_argument("--to", dest="date_to", help="Data final (YYYY-MM-DD).")
    parser.add_argument(
        "--output",
        help="Caminho do arquivo .csv (padrão: saida/diarios/impostos_unificado.csv).",
    )
    args = parser.parse_args()

    config = DiariosUnificadoConfig.from_env()
    if args.days is not None:
        config.days_back = args.days
    if args.date_from:
        config.date_from = _parse_cli_date(args.date_from)
    if args.date_to:
        config.date_to = _parse_cli_date(args.date_to)
    if args.output:
        config.output_file = Path(args.output)

    result = run_unificado_pipeline(config)
    csv_hint = result.get("output_path") if result.get("status") == "success" else None
    gerar_dados_extraidos_workflow(csv_hint)


if __name__ == "__main__":
    main()
