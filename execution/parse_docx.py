"""
Leitor e parser de documentos .docx (Microsoft Word) para o Modelo Intermediário Canônico.
Usa a biblioteca python-docx para extrair metadados, títulos, listas e tabelas.
"""

import os
import re
import datetime
from typing import Dict, Any
import docx
try:
    from document_model import DocumentModel, Section, Block, InlineSpan
except ImportError:
    from execution.document_model import DocumentModel, Section, Block, InlineSpan

def parse_docx_file(file_path: str) -> DocumentModel:
    """Abre um arquivo DOCX e converte seu conteúdo e formatação no DocumentModel canônico."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo DOCX não encontrado: {file_path}")

    doc = docx.Document(file_path)
    model = DocumentModel()

    current_section = Section(title="")
    current_sec_html_parts = []

    # Regex para metadados comuns em parágrafos
    meta_patterns = {
        "orgao": re.compile(r"^(?:[óo]rg[ãa]o(?:\s*respons[áa]vel)?|entidade|institui[çc][ãa]o|secretaria)\s*:\s*(.+)$", re.IGNORECASE),
        "autor": re.compile(r"^(?:autor|respons[áa]vel|elaborado\s*por|relator)\s*:\s*(.+)$", re.IGNORECASE),
        "data": re.compile(r"^(?:data|emiss[ãa]o)\s*:\s*(.+)$", re.IGNORECASE),
        "codigo": re.compile(r"^(?:c[óo]digo|n[úu]mero|identificador|id|processo)\s*:\s*(.+)$", re.IGNORECASE),
        "tipo_documento": re.compile(r"^(?:tipo(?:\s*de\s*documento)?)\s*:\s*(.+)$", re.IGNORECASE),
    }

    def close_section():
        nonlocal current_section, current_sec_html_parts
        if current_sec_html_parts or current_section.title:
            current_section.html_cache = "\n".join(current_sec_html_parts)
            model.secoes.append(current_section)
        current_section = Section(title="")
        current_sec_html_parts = []

    # Itera sobre elementos do corpo do documento
    # Para manter ordem cronológica, iteramos sobre os filhos de doc._body._element
    for child in doc._body._element:
        tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        
        if tag_name == "p":
            p = docx.text.paragraph.Paragraph(child, doc)
            text = p.text.strip()

            # Extrai imagens incorporadas no parágrafo
            blip_ids = p._element.xpath('.//a:blip/@r:embed')
            extracted_images = []
            if blip_ids:
                import base64
                for r_id in blip_ids:
                    try:
                        if r_id in doc.part.related_parts:
                            img_part = doc.part.related_parts[r_id]
                            content_type = getattr(img_part, "content_type", "image/png")
                            blob = img_part.blob
                            b64 = base64.b64encode(blob).decode("utf-8")
                            data_uri = f"data:{content_type};base64,{b64}"
                            extracted_images.append(data_uri)
                    except Exception as err:
                        print(f"⚠️ Erro ao extrair imagem rId {r_id}: {err}")

            # Se for uma imagem solta no início do documento (sem texto ou metadados de seção), assume como logo/brasão
            if extracted_images and not model.logo and not current_section.title and not current_sec_html_parts and not text:
                model.logo = extracted_images[0]
                extracted_images = extracted_images[1:]

            if not text and not extracted_images:
                continue

            # Detecta metadados
            matched_meta = False
            for key, pat in meta_patterns.items():
                m = pat.match(text)
                if m:
                    val = m.group(1).strip()
                    if key == "orgao":
                        model.orgao = val
                        model.orgao_val = val
                        model.orgao_class = ""
                    elif key == "autor":
                        model.autor = val
                        model.autor_val = val
                        model.autor_class = ""
                    elif key == "data":
                        model.data = val
                        model.data_val = val
                        model.data_class = ""
                    elif key == "codigo":
                        model.codigo = val
                        model.codigo_val = val
                        model.codigo_class = ""
                    elif key == "tipo_documento":
                        model.tipo_documento = val
                    matched_meta = True
                    break
            if matched_meta:
                continue

            style_name = p.style.name.lower() if p.style else ""
            
            # Detecta se é Título do documento ou Seção
            if "title" in style_name or (style_name.startswith("heading 1") and model.titulo == "Relatório Institucional"):
                model.titulo = text
                continue
            elif "subtitle" in style_name and not model.subtitulo:
                model.subtitulo = text
                continue
            elif text.startswith("Subtítulo:") or text.startswith("Subtitulo:"):
                model.subtitulo = text.split(":", 1)[1].strip()
                continue
            elif text.startswith("――――") or text.startswith("----"):
                continue
            elif model.titulo == "Relatório Institucional" and not model.secoes and not current_section.title and not current_sec_html_parts and text and not re.match(r"^\d+[\.\)]", text):
                # Primeiro parágrafo em destaque antes de qualquer seção é o título do documento
                model.titulo = text
                continue
            elif model.titulo != "Relatório Institucional" and not model.subtitulo and not model.secoes and not current_section.title and not current_sec_html_parts and text and not re.match(r"^\d+[\.\)]", text) and len(text) < 140:
                # Segundo parágrafo em destaque logo após o título vira o subtítulo
                model.subtitulo = text
                continue
            elif "heading 1" in style_name or "heading 2" in style_name or re.match(r"^(?:\d+[\.\)]\s*)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ\s\(\)\/\-]{4,}:?$", text):
                close_section()
                current_section.title = text
                for img_uri in extracted_images:
                    current_section.blocks.append(Block(type="image", image_src=img_uri, image_caption="Imagem do Relatório"))
                    current_sec_html_parts.append(f'<div class="report-image-box"><img src="{img_uri}" alt="Imagem do Relatório" class="content-img"></div>')
                continue

            # Insere as imagens extraídas deste parágrafo
            for img_uri in extracted_images:
                current_section.blocks.append(Block(type="image", image_src=img_uri, image_caption="Imagem do Relatório"))
                current_sec_html_parts.append(f'<div class="report-image-box"><img src="{img_uri}" alt="Imagem do Relatório" class="content-img"></div>')

            if not text:
                continue

            # Parágrafo normal ou item de lista
            is_list = "list" in style_name or text.startswith("- ") or text.startswith("* ")
            if is_list:
                clean_item = re.sub(r"^[\*\-]\s*", "", text)
                current_section.blocks.append(Block(type="list_item", text=clean_item))
                current_sec_html_parts.append(f"<ul><li>{clean_item}</li></ul>")
            else:
                # Extrai spans com formatação
                spans = []
                html_spans = []
                for r in p.runs:
                    if not r.text:
                        continue
                    b = bool(r.bold)
                    it = bool(r.italic)
                    spans.append(InlineSpan(text=r.text, bold=b, italic=it))
                    t = r.text
                    if b:
                        t = f"<strong>{t}</strong>"
                    if it:
                        t = f"<em>{t}</em>"
                    html_spans.append(t)

                current_section.blocks.append(Block(type="paragraph", text=text, spans=spans))
                current_sec_html_parts.append(f"<p>{''.join(html_spans)}</p>")

        elif tag_name == "tbl":
            table = docx.table.Table(child, doc)
            if not table.rows:
                continue

            # Se for a tabela de metadados do cabeçalho (ex: 3 colunas com ÓRGÃO, RESPONSÁVEL, IDENTIFICADOR)
            if len(table.rows) == 1 and any("ÓRGÃO" in c.text or "RESPONSÁVEL" in c.text for c in table.rows[0].cells):
                for cell in table.rows[0].cells:
                    lines = [ln.strip() for ln in cell.text.split("\n") if ln.strip()]
                    if len(lines) >= 2:
                        label, val = lines[0].upper(), lines[1]
                        if "ÓRGÃO" in label:
                            model.orgao = val
                            model.orgao_val = val
                            model.orgao_class = ""
                        elif "RESPONSÁVEL" in label or "AUTOR" in label:
                            model.autor = val
                            model.autor_val = val
                            model.autor_class = ""
                        elif "IDENTIFICADOR" in label or "CÓD" in label:
                            model.codigo = val
                            model.codigo_val = val
                            model.codigo_class = ""
                    else:
                        cell_text = cell.text.strip()
                        for key, pat in meta_patterns.items():
                            m = pat.match(cell_text)
                            if m:
                                val = m.group(1).strip()
                                if key == "orgao":
                                    model.orgao = val
                                    model.orgao_val = val
                                    model.orgao_class = ""
                                elif key == "autor":
                                    model.autor = val
                                    model.autor_val = val
                                    model.autor_class = ""
                                elif key == "codigo":
                                    model.codigo = val
                                    model.codigo_val = val
                                    model.codigo_class = ""
                continue
            
            headers = [c.text.strip() for c in table.rows[0].cells]
            rows_data = []
            for r in table.rows[1:]:
                rows_data.append([c.text.strip() for c in r.cells])

            current_section.blocks.append(Block(
                type="table",
                table_headers=headers,
                table_rows=rows_data
            ))

            # Gera HTML correspondente para a tabela
            tbl_html = ['<table class="data-table">']
            tbl_html.append('  <thead><tr>')
            for h in headers:
                tbl_html.append(f'    <th>{h}</th>')
            tbl_html.append('  </tr></thead>')
            tbl_html.append('  <tbody>')
            for row in rows_data:
                tbl_html.append('    <tr>')
                for c in row:
                    tbl_html.append(f'      <td>{c}</td>')
                tbl_html.append('    </tr>')
            tbl_html.append('  </tbody></table>')
            current_sec_html_parts.append("\n".join(tbl_html))

    close_section()

    # Fallbacks inteligentes idênticos ao parse_content.py
    if not model.titulo:
        model.titulo = "Relatório Institucional"
    if not model.data_val:
        model.data_val = datetime.date.today().strftime("%d/%m/%Y")
    if not model.codigo_val:
        model.codigo_val = datetime.datetime.now().strftime("REL-%Y%m%d-%H%M")

    if not model.secoes:
        model.secoes.append(Section(title="Conteúdo Principal", html_cache="<p>[Conteúdo importado do DOCX]</p>"))

    if model.autor and model.autor != "[NÃO INFORMADO]":
        model.assinaturas.append({"nome": model.autor, "cargo": model.orgao or "Responsável Técnico"})

    return model
