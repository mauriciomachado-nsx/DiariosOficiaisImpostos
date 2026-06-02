# Diários Oficiais — Impostos (Unificado)

Raspagem de publicações sobre **impostos e tributação** em 5 diários oficiais, consolidadas em um único **CSV**.

## Fontes

| Diário | Cliente |
|--------|---------|
| DOU (União) | `DouClient.py` |
| Recife (município) | `DiarioOficialClient.py` + `DomeRecifeClient.py` |
| Pernambuco (estado) | `CepePernambucoClient.py` |
| São Paulo (município) | `DiarioOficialClient.py` |
| São Paulo (estado) | `DoeSpEstadoClient.py` |

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

```bash
python3 diarios-impostos-unificado.py --days 7
python3 diarios-impostos-unificado.py --from 2026-05-29 --to 2026-06-02
```

Saída: `saida/diarios/impostos_unificado_*.csv` e `dados_extraidos.txt` (workflow).

## DO Pernambuco (CEPE)

Opcional — requer credenciais:

```bash
export CEPE_AUTH_TOKEN="..."
# ou CEPE_BASIC_USER / CEPE_BASIC_PASSWORD
```

## Variáveis de ambiente

- `DIARIOS_DAYS_BACK`, `DIARIOS_DATE_FROM`, `DIARIOS_DATE_TO`
- `DIARIOS_SEARCH_TERMS=imposto|ICMS|ISS`
- `DIARIOS_INCLUDE_DOU`, `DIARIOS_INCLUDE_RECIFE`, `DIARIOS_INCLUDE_PE`, etc.

Termos padrão em `DouConfigImpostos.py`.
