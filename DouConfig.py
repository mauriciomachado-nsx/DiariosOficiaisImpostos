"""
Configurações de busca no DOU — mercado de apostas (Brasil).
"""

from __future__ import annotations

from enum import Enum

# Termos monitorados diariamente no Diário Oficial da União.
SEARCH_TERMS: list[str] = [
    "apostas esportivas",
    "apostas de quota fixa",
    "operador de apostas",
    "autorização para exploração de apostas",
    "Secretaria de Prêmios e Apostas",
    "SIGAP",
    "Lei 14.790",
    "jogos de azar",
    "apostas",
]

# Órgãos mais relevantes para regulação do setor (filtro opcional).
DEPARTMENTS: list[str] = [
    "Ministério da Fazenda",
    "Secretaria de Prêmios e Apostas",
    "Ministério do Esporte",
    "Ministério da Justiça",
]

# Seções do DOU: do1 (normas), do2 (pessoal), do3 (contratos).
DOU_SECTIONS: list[str] = ["do1", "do2", "do3", "doe"]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class DouSection(str, Enum):
    SECAO_1 = "do1"
    SECAO_2 = "do2"
    SECAO_3 = "do3"
    EDICAO_EXTRA = "doe"
    TODOS = "todos"


SECTION_LABELS = {
    DouSection.SECAO_1.value: "Seção 1",
    DouSection.SECAO_2.value: "Seção 2",
    DouSection.SECAO_3.value: "Seção 3",
    DouSection.EDICAO_EXTRA.value: "Edição Extra",
    DouSection.TODOS.value: "Todas",
}
