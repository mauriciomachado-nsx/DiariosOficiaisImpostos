"""
Pipeline unificado — impostos em 5 diários oficiais.

Fontes:
  - DOU (Diário Oficial da União)
  - DO Recife (DiarioOficialClient + DOME)
  - DO PE (CEPE — requer credenciais opcionais)
  - DO São Paulo capital (DiarioOficialClient)
  - DO SP estado (API doe.sp.gov.br)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from CepePernambucoClient import CepePernambucoClient
from DiarioModels import DiarioPublication
from DiariosSourcesConfig import (
    DIARIO_DOU,
    DIARIO_PE,
    DIARIO_RECIFE,
    DIARIO_SP_CAPITAL,
    DIARIO_SP_ESTADO,
    IBGE_RECIFE,
    IBGE_SAO_PAULO_CAPITAL,
)
from DiarioOficialClient import DiarioOficialClient
from DoeSpEstadoClient import DoeSpEstadoClient
from DomeRecifeClient import DomeRecifeClient
from DouClient import DouClient
from DouConfig import DouSection
from DouConfigImpostos import DEPARTMENTS, DOU_SECTIONS, SEARCH_TERMS


@dataclass
class DiariosUnificadoConfig:
    output_file: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent
        / "saida"
        / "diarios"
        / "impostos_unificado.csv"
    )
    search_terms: list[str] = field(default_factory=lambda: list(SEARCH_TERMS))
    departments: list[str] = field(default_factory=lambda: list(DEPARTMENTS))
    dou_sections: list[str] = field(default_factory=lambda: list(DOU_SECTIONS))
    reference_date: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    days_back: int = 7
    filter_dou_departments: bool = True
    include_dou: bool = True
    include_recife: bool = True
    include_pernambuco: bool = True
    include_sao_paulo_capital: bool = True
    include_sao_paulo_estado: bool = True
    is_exact_search: bool = False

    @classmethod
    def from_env(cls, **overrides: Any) -> DiariosUnificadoConfig:
        terms = os.getenv("DIARIOS_SEARCH_TERMS")
        departments = os.getenv("DIARIOS_DEPARTMENTS")
        ref_date = os.getenv("DIARIOS_REFERENCE_DATE")
        date_from = os.getenv("DIARIOS_DATE_FROM")
        date_to = os.getenv("DIARIOS_DATE_TO")
        days_back = os.getenv("DIARIOS_DAYS_BACK")

        cfg = cls(
            filter_dou_departments=os.getenv("DIARIOS_FILTER_DOU_DEPARTMENTS", "true").lower()
            in ("1", "true", "yes"),
            is_exact_search=os.getenv("DIARIOS_EXACT_SEARCH", "").lower()
            in ("1", "true", "yes"),
            reference_date=datetime.strptime(ref_date, "%Y-%m-%d").date() if ref_date else None,
            date_from=datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None,
            date_to=datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None,
            days_back=int(days_back) if days_back else 7,
            include_dou=os.getenv("DIARIOS_INCLUDE_DOU", "true").lower() in ("1", "true", "yes"),
            include_recife=os.getenv("DIARIOS_INCLUDE_RECIFE", "true").lower()
            in ("1", "true", "yes"),
            include_pernambuco=os.getenv("DIARIOS_INCLUDE_PE", "true").lower()
            in ("1", "true", "yes"),
            include_sao_paulo_capital=os.getenv("DIARIOS_INCLUDE_SP_CAPITAL", "true").lower()
            in ("1", "true", "yes"),
            include_sao_paulo_estado=os.getenv("DIARIOS_INCLUDE_SP_ESTADO", "true").lower()
            in ("1", "true", "yes"),
        )

        if terms:
            cfg.search_terms = [t.strip() for t in terms.split("|") if t.strip()]
        if departments:
            cfg.departments = [d.strip() for d in departments.split("|") if d.strip()]

        for key, value in overrides.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg

    def resolve_date_range(self) -> tuple[date, date]:
        if self.date_from and self.date_to:
            start, end = self.date_from, self.date_to
        elif self.date_from:
            start = self.date_from
            end = self.date_to or date.today()
        elif self.reference_date:
            start = end = self.reference_date
        else:
            end = self.date_to or date.today()
            start = end - timedelta(days=self.days_back - 1)

        if start > end:
            raise ValueError(
                f"Data inicial ({start.isoformat()}) não pode ser posterior "
                f"à data final ({end.isoformat()})"
            )
        return start, end


def _parse_sections(section_codes: list[str]) -> list[DouSection]:
    mapping = {s.value: s for s in DouSection}
    sections: list[DouSection] = []
    for code in section_codes:
        key = code.lower()
        if key in mapping:
            sections.append(mapping[key])
        else:
            try:
                sections.append(DouSection[code.upper()])
            except KeyError:
                sections.append(DouSection.TODOS)
    return sections or [DouSection.TODOS]


def _deduplicate(publications: list[DiarioPublication]) -> list[DiarioPublication]:
    seen: set[str] = set()
    unique: list[DiarioPublication] = []
    for pub in publications:
        key = f"{pub.diario_fonte}|{pub.publicacao_id or pub.url}|{pub.titulo}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(pub)
    return unique


def _filter_dou_publications(
    publications: list[DiarioPublication],
    departments: list[str],
) -> list[DiarioPublication]:
    if not departments:
        return publications
    filtered: list[DiarioPublication] = []
    for pub in publications:
        orgao = pub.orgao.casefold()
        if any(dept.casefold() in orgao for dept in departments):
            filtered.append(pub)
    return filtered


def _collect_dou(
    config: DiariosUnificadoConfig,
    date_from: date,
    date_to: date,
) -> list[DiarioPublication]:
    client = DouClient()
    sections = _parse_sections(config.dou_sections)
    results: list[DiarioPublication] = []

    for term in config.search_terms:
        print(f"  [DOU] termo {term!r}...")
        try:
            pubs = client.search_term(
                term=term,
                reference_date=date_from,
                date_to=date_to if date_to != date_from else None,
                sections=sections,
                is_exact_search=config.is_exact_search,
            )
            for p in pubs:
                item = DiarioPublication.from_dou(p, DIARIO_DOU)
                results.append(item)
            print(f"       -> {len(pubs)} publicação(ões)")
        except Exception as exc:
            print(f"       -> ERRO: {exc}")
        time.sleep(1)

    if config.filter_dou_departments:
        before = len(results)
        results = _filter_dou_publications(results, config.departments)
        print(f"  [DOU] filtro órgãos: {before} -> {len(results)}")

    return results


def _collect_diario_oficial(
    client: DiarioOficialClient,
    territory_id: str,
    diario_fonte: str,
    orgao_label: str,
    search_terms: list[str],
    date_from: date,
    date_to: date,
) -> list[DiarioPublication]:
    results: list[DiarioPublication] = []
    for term in search_terms:
        print(f"  [{diario_fonte}] termo {term!r}...")
        try:
            pubs = client.search(
                territory_id=territory_id,
                diario_fonte=diario_fonte,
                term=term,
                date_from=date_from,
                date_to=date_to,
                orgao_default=orgao_label,
            )
            print(f"       -> {len(pubs)} publicação(ões)")
            results.extend(pubs)
        except Exception as exc:
            print(f"       -> ERRO: {exc}")
        time.sleep(1)
    return results


def _collect_recife_dome(
    config: DiariosUnificadoConfig,
    date_from: date,
    date_to: date,
) -> list[DiarioPublication]:
    client = DomeRecifeClient()
    results: list[DiarioPublication] = []
    for term in config.search_terms:
        print(f"  [DO Recife DOME] termo {term!r}...")
        try:
            pubs = client.search(term, date_from, date_to)
            print(f"       -> {len(pubs)} edição(ões)")
            results.extend(pubs)
        except Exception as exc:
            print(f"       -> ERRO: {exc}")
        time.sleep(1)
    return results


def _collect_pernambuco(
    config: DiariosUnificadoConfig,
    date_from: date,
    date_to: date,
) -> list[DiarioPublication]:
    client = CepePernambucoClient()
    results: list[DiarioPublication] = []
    for term in config.search_terms:
        print(f"  [DO PE] termo {term!r}...")
        try:
            pubs = client.search(term, date_from, date_to)
            print(f"       -> {len(pubs)} publicação(ões)")
            results.extend(pubs)
        except Exception as exc:
            print(f"       -> ERRO: {exc}")
        time.sleep(1)
    return results


def _collect_sp_estado(
    config: DiariosUnificadoConfig,
    date_from: date,
    date_to: date,
) -> list[DiarioPublication]:
    client = DoeSpEstadoClient()
    results: list[DiarioPublication] = []
    for term in config.search_terms:
        print(f"  [DO SP] termo {term!r}...")
        try:
            pubs = client.search(term, date_from, date_to)
            print(f"       -> {len(pubs)} publicação(ões)")
            results.extend(pubs)
        except Exception as exc:
            print(f"       -> ERRO: {exc}")
        time.sleep(1)
    return results


def _write_unified_csv(
    df: pd.DataFrame,
    output_path: Path,
    date_from: date,
    date_to: date,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() != ".csv":
        output_path = output_path.with_suffix(".csv")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_path.name == "impostos_unificado.csv":
        final_path = output_path.parent / f"impostos_unificado_{date_from}_{date_to}_{ts}.csv"
    else:
        final_path = output_path

    df.to_csv(final_path, index=False, encoding="utf-8-sig")
    return final_path


def run_unificado_pipeline(
    config: DiariosUnificadoConfig | None = None,
) -> dict[str, Any]:
    config = config or DiariosUnificadoConfig.from_env()
    date_from, date_to = config.resolve_date_range()
    all_publications: list[DiarioPublication] = []

    print("=== Diários Oficiais — Impostos (Unificado) ===\n")
    print(f"Período: {date_from.isoformat()} a {date_to.isoformat()}")
    total_buscas = len(config.search_terms)
    print(
        f"Termos: {total_buscas} (busca individual por termo em cada fonte) | Fontes: ",
        end="",
    )
    fontes = []
    if config.include_dou:
        fontes.append("DOU")
    if config.include_recife:
        fontes.append("Recife")
    if config.include_pernambuco:
        fontes.append("PE")
    if config.include_sao_paulo_capital:
        fontes.append("SP Capital")
    if config.include_sao_paulo_estado:
        fontes.append("SP Estado")
    print(", ".join(fontes) or "nenhuma")
    print()

    if config.include_dou:
        print("--- DOU ---")
        all_publications.extend(_collect_dou(config, date_from, date_to))
        print()

    diario_client = DiarioOficialClient()

    if config.include_recife:
        print("--- Diário Oficial de Recife ---")
        all_publications.extend(
            _collect_diario_oficial(
                diario_client,
                IBGE_RECIFE,
                DIARIO_RECIFE,
                "Prefeitura do Recife",
                config.search_terms,
                date_from,
                date_to,
            )
        )
        all_publications.extend(_collect_recife_dome(config, date_from, date_to))
        print()

    if config.include_pernambuco:
        print("--- Diário Oficial de Pernambuco (CEPE) ---")
        all_publications.extend(_collect_pernambuco(config, date_from, date_to))
        print()

    if config.include_sao_paulo_capital:
        print("--- Diário Oficial de São Paulo (capital) ---")
        all_publications.extend(
            _collect_diario_oficial(
                diario_client,
                IBGE_SAO_PAULO_CAPITAL,
                DIARIO_SP_CAPITAL,
                "Prefeitura de São Paulo",
                config.search_terms,
                date_from,
                date_to,
            )
        )
        print()

    if config.include_sao_paulo_estado:
        print("--- Diário Oficial do Estado de São Paulo ---")
        all_publications.extend(_collect_sp_estado(config, date_from, date_to))
        print()

    all_publications = _deduplicate(all_publications)

    if not all_publications:
        print("Nenhuma publicação encontrada.")
        return {
            "status": "empty",
            "publications_count": 0,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        }

    rows = [p.to_dict() for p in all_publications]
    df = pd.DataFrame(rows)
    df = df.sort_values(
        ["diario_fonte", "data_publicacao", "titulo"],
        ascending=[True, False, True],
        na_position="last",
    )

    output_path = _write_unified_csv(df, config.output_file, date_from, date_to)
    print(f"CSV unificado: {output_path}")
    print(f"Total de linhas: {len(df)}")
    print("\nResumo por fonte:")
    for fonte, count in df["diario_fonte"].value_counts().items():
        print(f"  {fonte}: {count}")

    return {
        "status": "success",
        "publications_count": len(df),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "output_path": str(output_path),
        "publications": rows,
    }
