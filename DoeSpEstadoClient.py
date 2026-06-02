"""
Cliente do Diário Oficial do Estado de São Paulo (API de busca avançada).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import requests

from DiarioModels import DiarioPublication
from DiariosSourcesConfig import DIARIO_SP_ESTADO, DOE_SP_SEARCH_API
from DouConfig import USER_AGENT

logger = logging.getLogger(__name__)


class DoeSpEstadoClient:
    def __init__(self, timeout: int = 90, page_size: int = 50):
        self.timeout = timeout
        self.page_size = page_size
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )

    @staticmethod
    def _format_date(value: date) -> str:
        return f"{value.year}-{value.month}-{value.day}"

    def search(
        self,
        term: str,
        date_from: date,
        date_to: date,
    ) -> list[DiarioPublication]:
        publications: list[DiarioPublication] = []
        page = 1
        total_pages = 1

        while page <= total_pages:
            params = {
                "Terms": term,
                "FromDate": self._format_date(date_from),
                "ToDate": self._format_date(date_to),
                "PageNumber": page,
                "PageSize": self.page_size,
            }
            response = self._session.get(
                DOE_SP_SEARCH_API, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items") or data.get("publications") or []
            total_pages = int(
                data.get("totalPages")
                or data.get("total_pages")
                or (1 if not items else page)
            )

            for raw in items:
                publications.append(self._parse_item(raw, term))

            if not items:
                break
            page += 1
            time.sleep(0.5)

        return publications

    def _parse_item(self, raw: dict[str, Any], term: str) -> DiarioPublication:
        title = (
            raw.get("title")
            or raw.get("headline")
            or raw.get("publicationTitle")
            or "Publicação DO SP"
        )
        excerpt = raw.get("excerpt") or raw.get("summary") or raw.get("content") or ""
        if not excerpt and raw.get("termsFound"):
            terms_found = raw["termsFound"]
            if isinstance(terms_found, list) and terms_found:
                excerpt = str(terms_found[0])

        pub_date = raw.get("publicationDate") or raw.get("date") or raw.get("publishDate") or ""
        if isinstance(pub_date, str) and "T" in pub_date:
            pub_date = pub_date.split("T", 1)[0]
            y, m, d = pub_date.split("-")
            pub_date = f"{d}/{m}/{y}"

        url = raw.get("url") or raw.get("publicationUrl") or raw.get("link") or ""
        section = raw.get("sectionName") or raw.get("section") or raw.get("journalName") or ""
        orgao = raw.get("entityName") or raw.get("publisher") or "Governo do Estado de São Paulo"
        tipo = raw.get("actType") or raw.get("type") or "Publicação Oficial"
        pub_id = str(raw.get("id") or raw.get("publicationId") or url or title)

        return DiarioPublication(
            diario_fonte=DIARIO_SP_ESTADO,
            termo_busca=term,
            secao=str(section),
            titulo=str(title),
            url=str(url),
            resumo=str(excerpt)[:2000],
            data_publicacao=str(pub_date),
            orgao=str(orgao),
            tipo_ato=str(tipo),
            publicacao_id=pub_id,
            coletado_em=DiarioPublication.now_stamp(),
        )
