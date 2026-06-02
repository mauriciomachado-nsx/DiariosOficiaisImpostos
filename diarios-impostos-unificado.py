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


def export_dados_extraidos_txt(
    csv_path: Path,
    output_path: Path | None = None,
) -> Path:
    """
    Gera dados_extraidos.txt para integração com workflow externo.

    Formato: cabeçalho com total/arquivo, bloco ---DADOS--- com uma linha
    por registro (pipe-separated), encerrado em ---FIM---.
    """
    dest = output_path or _ROOT / "dados_extraidos.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    with dest.open("w", encoding="utf-8") as out:
        out.write(f"TOTAL: {len(rows)} registros\n")
        out.write(f"ARQUIVO: {csv_path.name}\n")
        out.write("---DADOS---\n")
        for i, row in enumerate(rows):
            resumo = (row.get("resumo") or "")[:200].replace("\n", " ")
            titulo = (row.get("titulo") or "")[:120]
            linha = (
                f"[{i + 1}] {row.get('diario_fonte', '')} | "
                f"{row.get('data_publicacao', '')} | "
                f"{row.get('tipo_ato', '')} | "
                f"{row.get('orgao', '')} | "
                f"{titulo} | "
                f"{row.get('termo_busca', '')} | "
                f"{resumo} | "
                f"{row.get('url', '')}"
            )
            out.write(linha + "\n")
        out.write("---FIM---\n")

    print(f"[WORKFLOW] dados_extraidos.txt gerado com {len(rows)} registros → {dest}")
    return dest


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
    parser.add_argument(
        "--workflow-txt",
        nargs="?",
        const=str(_ROOT / "dados_extraidos.txt"),
        default=str(_ROOT / "dados_extraidos.txt"),
        help="Gera dados_extraidos.txt para workflow (padrão: ./dados_extraidos.txt).",
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

    if result.get("status") == "success" and result.get("output_path"):
        export_dados_extraidos_txt(
            Path(result["output_path"]),
            Path(args.workflow_txt),
        )
    else:
        print("[WORKFLOW] Nenhum CSV gerado — dados_extraidos.txt não criado.")


if __name__ == "__main__":
    main()
