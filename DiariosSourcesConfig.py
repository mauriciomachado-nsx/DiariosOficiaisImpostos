"""
Fontes de diários oficiais para o monitoramento tributário unificado.
"""

from __future__ import annotations

# Códigos IBGE (diários municipais via API pública)
IBGE_RECIFE = "2611606"
IBGE_SAO_PAULO_CAPITAL = "3550308"

DIARIO_DOU = "DOU - Diário Oficial da União"
DIARIO_RECIFE = "DO Recife - Diário Oficial do Município"
DIARIO_PE = "DO PE - Diário Oficial do Estado de Pernambuco"
DIARIO_SP_CAPITAL = "DO São Paulo - Diário Oficial do Município"
DIARIO_SP_ESTADO = "DO SP - Diário Oficial do Estado de São Paulo"

DIARIO_OFICIAL_API = "https://api.queridodiario.ok.org.br/gazettes"
DOE_SP_SEARCH_API = "https://api-web-search.doe.sp.gov.br/v2/advanced-search/publications"
CEPE_BUSCA_API = "https://diariooficial.cepe.com.br/diariooficial/buscaAvancada"
DOME_RECIFE_BUSCA = "https://dome.recife.pe.gov.br/dome/buscar.php"
