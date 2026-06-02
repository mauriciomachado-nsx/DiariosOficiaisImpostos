"""
Cliente do DOME — Diário Oficial do Recife (busca por palavra-chave).
"""

from __future__ import annotations

import logging
import re
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from DiarioModels import DiarioPublication
from DiariosSourcesConfig import DOME_RECIFE_BUSCA, DIARIO_RECIFE
from DouConfig import USER_AGENT

logger = logging.getLogger(__name__)

BASE_URL = "https://dome.recife.pe.gov.br/dome/"


class DomeRecifeClient:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self._headers = {"User-Agent": USER_AGENT}

    def search(
        self,
        term: str,
        date_from: date,
        date_to: date,
    ) -> list[DiarioPublication]:
        params = {
            "opcaoBusca": "palavras",
            "palavras": term,
            "dataIni": date_from.strftime("%d/%m/%Y"),
            "dataFim": date_to.strftime("%d/%m/%Y"),
        }
        response = requests.get(
            DOME_RECIFE_BUSCA,
            params=params,
            timeout=self.timeout,
            headers=self._headers,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        publications: list[DiarioPublication] = []
        seen: set[str] = set()

        for h4 in soup.find_all("h4"):
            titulo = h4.get_text(" ", strip=True)
            if not titulo or titulo in seen:
                continue
            seen.add(titulo)

            link = ""
            parent = h4.parent
            if parent:
                anchor = parent.find("a", href=True)
                if anchor:
                    link = urljoin(BASE_URL, anchor["href"])

            pub_date = self._extract_date(titulo)
            publications.append(
                DiarioPublication(
                    diario_fonte=DIARIO_RECIFE,
                    termo_busca=term,
                    secao="DOME Recife",
                    titulo=titulo,
                    url=link,
                    resumo=f"Edição listada na busca DOME para o termo {term!r}.",
                    data_publicacao=pub_date,
                    orgao="Prefeitura do Recife",
                    tipo_ato="Edição do Diário",
                    publicacao_id=titulo,
                    coletado_em=DiarioPublication.now_stamp(),
                )
            )

        return publications

    @staticmethod
    def _extract_date(titulo: str) -> str:
        match = re.search(r"(\d{2}/\d{2}/\d{4})", titulo)
        return match.group(1) if match else ""
