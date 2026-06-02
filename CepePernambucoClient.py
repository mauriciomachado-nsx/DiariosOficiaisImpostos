"""
Cliente do Diário Oficial do Estado de Pernambuco (CEPE).

A API de busca do CEPE exige autenticação. Defina CEPE_AUTH_TOKEN (Bearer) ou
CEPE_BASIC_USER + CEPE_BASIC_PASSWORD se houver credenciais institucionais.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

import requests

from DiarioModels import DiarioPublication
from DiariosSourcesConfig import CEPE_BUSCA_API, DIARIO_PE
from DouConfig import USER_AGENT

logger = logging.getLogger(__name__)


class CepePernambucoClient:
    def __init__(self, timeout: int = 90):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )
        token = os.getenv("CEPE_AUTH_TOKEN")
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"
        user = os.getenv("CEPE_BASIC_USER")
        password = os.getenv("CEPE_BASIC_PASSWORD")
        if user and password:
            self._session.auth = (user, password)

    def search(
        self,
        term: str,
        date_from: date,
        date_to: date,
    ) -> list[DiarioPublication]:
        if not self._has_auth():
            logger.warning(
                "CEPE: busca requer autenticação. "
                "Configure CEPE_AUTH_TOKEN ou CEPE_BASIC_USER/CEPE_BASIC_PASSWORD."
            )
            return []

        params = {
            "texto": term,
            "termo": term,
            "dataInicio": date_from.strftime("%d/%m/%Y"),
            "dataFim": date_to.strftime("%d/%m/%Y"),
            "pagina": 0,
            "tamanhoPagina": 50,
        }
        response = self._session.get(
            CEPE_BUSCA_API, params=params, timeout=self.timeout
        )
        if response.status_code == 401:
            logger.warning("CEPE: credenciais rejeitadas (401).")
            return []
        response.raise_for_status()
        return self._parse_response(response.json(), term)

    def _has_auth(self) -> bool:
        return bool(
            os.getenv("CEPE_AUTH_TOKEN")
            or (os.getenv("CEPE_BASIC_USER") and os.getenv("CEPE_BASIC_PASSWORD"))
        )

    def _parse_response(
        self, data: Any, term: str
    ) -> list[DiarioPublication]:
        items: list[Any]
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("content")
                or data.get("items")
                or data.get("publicacoes")
                or data.get("results")
                or []
            )
        else:
            items = []

        publications: list[DiarioPublication] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            title = raw.get("titulo") or raw.get("title") or "Publicação DO PE"
            excerpt = raw.get("resumo") or raw.get("ementa") or raw.get("texto") or ""
            pub_date = raw.get("dataPublicacao") or raw.get("date") or ""
            url = raw.get("url") or raw.get("link") or ""
            publications.append(
                DiarioPublication(
                    diario_fonte=DIARIO_PE,
                    termo_busca=term,
                    secao=str(raw.get("categoria") or raw.get("secao") or ""),
                    titulo=str(title),
                    url=str(url),
                    resumo=str(excerpt)[:2000],
                    data_publicacao=str(pub_date),
                    orgao=str(raw.get("orgao") or "Governo do Estado de Pernambuco"),
                    tipo_ato=str(raw.get("tipo") or raw.get("tipoAto") or "Publicação Oficial"),
                    publicacao_id=str(raw.get("id") or url or title),
                    coletado_em=DiarioPublication.now_stamp(),
                )
            )
        return publications
