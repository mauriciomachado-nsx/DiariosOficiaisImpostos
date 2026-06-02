"""
Cliente de busca em diários oficiais municipais (API Querido Diário).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import requests

from DiarioModels import DiarioPublication
from DiariosSourcesConfig import DIARIO_OFICIAL_API
from DouConfig import USER_AGENT

logger = logging.getLogger(__name__)


class DiarioOficialClient:
    def __init__(self, timeout: int = 90, page_size: int = 100):
        self.timeout = timeout
        self.page_size = page_size
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )

    def search(
        self,
        territory_id: str,
        diario_fonte: str,
        term: str,
        date_from: date,
        date_to: date,
        orgao_default: str = "",
    ) -> list[DiarioPublication]:
        publications: list[DiarioPublication] = []
        offset = 0

        while True:
            params = {
                "territory_ids": territory_id,
                "querystring": term,
                "published_since": date_from.isoformat(),
                "published_until": date_to.isoformat(),
                "excerpt_size": 800,
                "number_of_excerpts": 2,
                "size": self.page_size,
                "offset": offset,
            }
            response = self._session.get(
                DIARIO_OFICIAL_API, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            gazettes = data.get("gazettes") or []
            total = int(data.get("total_gazettes") or 0)

            for raw in gazettes:
                publications.append(
                    self._parse_gazette(raw, diario_fonte, term, orgao_default)
                )

            offset += len(gazettes)
            if offset >= total or not gazettes:
                break
            time.sleep(0.5)

        return publications

    def _parse_gazette(
        self,
        raw: dict[str, Any],
        diario_fonte: str,
        term: str,
        orgao_default: str,
    ) -> DiarioPublication:
        excerpts = raw.get("excerpts") or []
        resumo = "\n...\n".join(excerpts[:2]) if excerpts else ""
        edition = raw.get("edition") or ""
        extra = "Extra" if raw.get("is_extra_edition") else "Ordinária"
        secao = f"Edição {edition} ({extra})" if edition else extra

        pub_date = raw.get("date") or ""
        if pub_date and "-" in pub_date:
            y, m, d = pub_date.split("-")
            pub_date = f"{d}/{m}/{y}"

        territory = raw.get("territory_name") or orgao_default
        state = raw.get("state_code") or ""
        orgao = f"{territory}/{state}" if state else territory

        return DiarioPublication(
            diario_fonte=diario_fonte,
            termo_busca=term,
            secao=secao,
            titulo=f"{diario_fonte} — {pub_date}",
            url=raw.get("url") or raw.get("txt_url") or "",
            resumo=resumo,
            data_publicacao=pub_date,
            orgao=orgao,
            tipo_ato="Edição do Diário",
            publicacao_id=f"{raw.get('territory_id')}-{raw.get('date')}-{edition}",
            coletado_em=DiarioPublication.now_stamp(),
        )
