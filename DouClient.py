"""
Cliente de busca no Diário Oficial da União (DOU).

Baseado na API pública usada pelo Ro-DOU (gestaogovbr/Ro-dou):
https://www.in.gov.br/consulta/-/buscar/dou
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from urllib.parse import urlencode
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from DouConfig import SECTION_LABELS, USER_AGENT, DouSection

logger = logging.getLogger(__name__)

SCRIPT_TAG_ID = "_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"
IN_API_BASE_URL = "https://www.in.gov.br/consulta/-/buscar/dou"
IN_WEB_BASE_URL = "https://www.in.gov.br/web/dou/-/"


@dataclass
class DouPublication:
    termo_busca: str
    secao: str
    titulo: str
    url: str
    resumo: str
    data_publicacao: str
    orgao: str
    tipo_ato: str
    dou_id: str
    coletado_em: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "termo_busca": self.termo_busca,
            "secao": self.secao,
            "titulo": self.titulo,
            "url": self.url,
            "resumo": self.resumo,
            "data_publicacao": self.data_publicacao,
            "orgao": self.orgao,
            "tipo_ato": self.tipo_ato,
            "dou_id": self.dou_id,
            "coletado_em": self.coletado_em,
        }


class DouClient:
    def __init__(
        self,
        timeout: int = 120,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session = requests.Session()
        self._headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.in.gov.br/consulta/-/buscar/dou",
        }

    def search_term(
        self,
        term: str,
        reference_date: date | None = None,
        date_to: date | None = None,
        sections: list[DouSection] | None = None,
        is_exact_search: bool = False,
    ) -> list[DouPublication]:
        ref_from = reference_date or date.today()
        ref_to = date_to or ref_from
        if ref_from > ref_to:
            raise ValueError(
                f"Data inicial ({ref_from.isoformat()}) não pode ser posterior "
                f"à data final ({ref_to.isoformat()})"
            )

        section_values = sections or [DouSection.TODOS]
        query = f'"{term}"' if is_exact_search else term

        payload = {
            "q": query,
            "exactDate": "personalizado",
            "publishFrom": ref_from.strftime("%d-%m-%Y"),
            "publishTo": ref_to.strftime("%d-%m-%Y"),
            "sortType": "0",
            "s": [s.value for s in section_values],
        }

        if ref_from == ref_to:
            logger.info("Buscando DOU: termo=%r data=%s", term, ref_from.isoformat())
        else:
            logger.info(
                "Buscando DOU: termo=%r período=%s a %s",
                term,
                ref_from.isoformat(),
                ref_to.isoformat(),
            )
        return self._search_pages(term, payload)

    def _search_pages(self, term: str, payload: dict[str, Any]) -> list[DouPublication]:
        page_content = self._fetch_page(payload)
        soup = BeautifulSoup(page_content, "html.parser")
        number_pages = self._count_pages(soup)
        logger.info("Total de páginas para %r: %s", term, number_pages)

        results: list[DouPublication] = []
        last_item: dict[str, Any] | None = None

        for page_num in range(number_pages):
            if page_num > 0 and last_item:
                payload.update(
                    {
                        "id": last_item["dou_id"],
                        "displayDate": last_item["display_date_sortable"],
                        "newPage": page_num + 1,
                        "currentPage": page_num,
                    }
                )
                page_content = self._fetch_page(payload)
                soup = BeautifulSoup(page_content, "html.parser")

            for raw in self._extract_json_array(soup):
                pub = self._parse_publication(term, raw)
                results.append(pub)
                last_item = pub.to_dict()
                last_item["display_date_sortable"] = raw.get("displayDateSortable", "")

        return results

    def _fetch_page(self, payload: dict[str, Any]) -> bytes:
        try:
            return self._request_page(payload).content
        except RuntimeError:
            logger.warning("Usando fallback curl para consulta DOU")
            return self._request_page_curl(payload)

    def _request_page(self, payload: dict[str, Any]) -> requests.Response:
        last_error: Exception | None = None
        urls = [IN_API_BASE_URL, IN_API_BASE_URL.replace("https://", "http://")]

        for attempt in range(1, self.max_retries + 1):
            for url in urls:
                try:
                    response = self._session.get(
                        url,
                        params=payload,
                        timeout=self.timeout,
                        headers=self._headers,
                    )
                    if response.status_code >= 400 and SCRIPT_TAG_ID not in response.text:
                        response.raise_for_status()
                    return response
                except requests.RequestException as exc:
                    last_error = exc
                    logger.warning(
                        "Erro ao acessar DOU via %s (tentativa %s/%s): %s",
                        url.split("://", 1)[0],
                        attempt,
                        self.max_retries,
                        exc,
                    )

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        raise RuntimeError(f"Falha ao consultar DOU após {self.max_retries} tentativas") from last_error

    def _request_page_curl(self, payload: dict[str, Any]) -> bytes:
        """Fallback via curl quando requests falha (comum em alguns ambientes macOS)."""
        query = urlencode(payload, doseq=True)
        url = f"{IN_API_BASE_URL}?{query}"
        cmd = [
            "curl",
            "-sL",
            "--http1.1",
            "--compressed",
            "--max-time",
            str(self.timeout),
            "-H",
            f"User-Agent: {USER_AGENT}",
            "-H",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H",
            "Accept-Language: pt-BR,pt;q=0.9",
            "-H",
            "Referer: https://www.in.gov.br/consulta/-/buscar/dou",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, check=False)
        content = result.stdout
        if content and SCRIPT_TAG_ID.encode() in content:
            return content
        if result.returncode != 0:
            raise RuntimeError(
                f"curl falhou (code={result.returncode}): {result.stderr.decode()[:200]}"
            )
        return content

    @staticmethod
    def _count_pages(soup: BeautifulSoup) -> int:
        pagination_tag = soup.find("button", id="lastPage")
        if pagination_tag is not None:
            return int(pagination_tag.text.strip())

        second_page_tag = soup.find("button", id="2btn")
        if second_page_tag:
            return 2
        return 1

    def _extract_json_array(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        script_tag = soup.find("script", id=SCRIPT_TAG_ID)
        if script_tag is None or not script_tag.string:
            raise ValueError(
                "Não foi possível localizar resultados no HTML do DOU. "
                "A estrutura da página pode ter mudado."
            )

        data = json.loads(script_tag.string)
        return data.get("jsonArray", []) or []

    def _parse_publication(self, term: str, content: dict[str, Any]) -> DouPublication:
        section_key = str(content.get("pubName", "")).lower()
        section_label = SECTION_LABELS.get(section_key, section_key)
        hierarchy = content.get("hierarchyStr") or ""
        if not hierarchy and content.get("hierarchyList"):
            hierarchy = " > ".join(content["hierarchyList"])

        abstract = self._clean_html(content.get("content", "") or "")

        return DouPublication(
            termo_busca=term,
            secao=f"DOU - {section_label}",
            titulo=content.get("title", ""),
            url=IN_WEB_BASE_URL + content.get("urlTitle", ""),
            resumo=abstract,
            data_publicacao=content.get("pubDate", ""),
            orgao=hierarchy,
            tipo_ato=content.get("artType", ""),
            dou_id=str(content.get("classPK", "")),
            coletado_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @staticmethod
    def _clean_html(raw_html: str) -> str:
        text = re.sub(r"<.*?>", "", raw_html)
        return text.replace("... ", "").strip()
