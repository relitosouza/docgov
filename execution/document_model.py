"""
Módulo de Modelo Intermediário Canônico de Documentos Institucionais.
Define uma estrutura de dados normalizada e independente de formato.
Tanto Markdown quanto DOCX são transformados neste modelo, e os renderizadores
(HTML e DOCX) operam de forma padronizada a partir dele.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class InlineSpan:
    text: str
    bold: bool = False
    italic: bool = False

@dataclass
class Block:
    type: str  # 'paragraph', 'heading', 'list_item', 'table', 'image'
    text: str = ""
    level: int = 1  # Para headings
    spans: List[InlineSpan] = field(default_factory=list)
    items: List[str] = field(default_factory=list) # Para listas
    # Para tabelas: lista de linhas, onde cada linha é uma lista de strings/células
    table_headers: List[str] = field(default_factory=list)
    table_rows: List[List[str]] = field(default_factory=list)
    # Para imagens
    image_src: str = ""
    image_caption: str = ""

@dataclass
class Section:
    title: str = ""
    blocks: List[Block] = field(default_factory=list)
    html_cache: str = ""

@dataclass
class DocumentModel:
    titulo: str = "Relatório Institucional"
    subtitulo: str = ""
    tipo_documento: str = ""
    orgao: str = ""
    orgao_val: str = "[NÃO INFORMADO]"
    orgao_class: str = "nao-informado"
    autor: str = ""
    autor_val: str = "[NÃO INFORMADO]"
    autor_class: str = "nao-informado"
    data: str = ""
    data_val: str = ""
    data_class: str = ""
    codigo: str = ""
    codigo_val: str = ""
    codigo_class: str = ""
    logo: Optional[str] = None
    orientation: str = "portrait"
    include_signature: bool = True
    include_meta_box: bool = True
    secoes: List[Section] = field(default_factory=list)
    assinaturas: List[Dict[str, str]] = field(default_factory=list)

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Garante 100% de compatibilidade reversa com o dicionário esperado pelos renderizadores."""
        secoes_tuples = []
        for sec in self.secoes:
            secoes_tuples.append((sec.title, sec.html_cache))

        return {
            "titulo": self.titulo,
            "subtitulo": self.subtitulo,
            "tipo_documento": self.tipo_documento,
            "orgao": self.orgao,
            "orgao_val": self.orgao_val,
            "orgao_class": self.orgao_class,
            "autor": self.autor,
            "autor_val": self.autor_val,
            "autor_class": self.autor_class,
            "data": self.data,
            "data_val": self.data_val,
            "data_class": self.data_class,
            "codigo": self.codigo,
            "codigo_val": self.codigo_val,
            "codigo_class": self.codigo_class,
            "logo": self.logo,
            "orientation": self.orientation,
            "include_signature": self.include_signature,
            "include_meta_box": self.include_meta_box,
            "secoes": secoes_tuples,
            "assinaturas": [(a.get("nome", ""), a.get("cargo", "")) for a in self.assinaturas]
        }
