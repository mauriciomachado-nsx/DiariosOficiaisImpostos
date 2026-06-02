"""
Configurações de busca no DOU — alterações e atualizações tributárias (âmbito nacional).
"""

from __future__ import annotations

# Termos focados em mudanças normativas e atualizações de tributos federais.
SEARCH_TERMS: list[str] = [
    "reforma tributária",
    "alteração tributária",
    "atualização tributária",
    "norma tributária",
    "tributação",
    "imposto de renda",
    "IRPF",
    "IRPJ",
    "CSLL",
    "PIS",
    "COFINS",
    "IPI",
    "IOF",
    "contribuição social",
    "Simples Nacional",
    "instrução normativa",
    "Receita Federal",
    "alíquota",
    "base de cálculo",
    "retenção na fonte",
    "medida provisória tributária",
    "Lei Complementar 214",
]

# Órgãos federais mais relevantes para normas tributárias nacionais.
DEPARTMENTS: list[str] = [
    "Ministério da Fazenda",
    "Receita Federal do Brasil",
    "Procuradoria-Geral da Fazenda Nacional",
    "Senado Federal",
    "Câmara dos Deputados",
    "Presidência da República",
]

# Seção 1 concentra leis, decretos e instruções; incluímos doe para atos urgentes.
DOU_SECTIONS: list[str] = ["do1", "doe"]
