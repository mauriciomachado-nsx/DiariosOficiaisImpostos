"""
Modelo unificado de publicação em diários oficiais.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DiarioPublication:
    diario_fonte: str
    termo_busca: str
    secao: str
    titulo: str
    url: str
    resumo: str
    data_publicacao: str
    orgao: str
    tipo_ato: str
    publicacao_id: str
    coletado_em: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "diario_fonte": self.diario_fonte,
            "termo_busca": self.termo_busca,
            "secao": self.secao,
            "titulo": self.titulo,
            "url": self.url,
            "resumo": self.resumo,
            "data_publicacao": self.data_publicacao,
            "orgao": self.orgao,
            "tipo_ato": self.tipo_ato,
            "publicacao_id": self.publicacao_id,
            "coletado_em": self.coletado_em,
        }

    @classmethod
    def from_dou(cls, pub: Any, diario_fonte: str = "DOU - Diário Oficial da União") -> DiarioPublication:
        return cls(
            diario_fonte=diario_fonte,
            termo_busca=pub.termo_busca,
            secao=pub.secao,
            titulo=pub.titulo,
            url=pub.url,
            resumo=pub.resumo,
            data_publicacao=pub.data_publicacao,
            orgao=pub.orgao,
            tipo_ato=pub.tipo_ato,
            publicacao_id=pub.dou_id,
            coletado_em=pub.coletado_em,
        )

    @staticmethod
    def now_stamp() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
