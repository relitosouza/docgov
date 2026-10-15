"""
Parser híbrido para textos brutos e arquivos Markdown (.md) ou Texto (.txt).
Extrai metadados essenciais e seções estruturadas.
Suporta fallback automático para valores não informados.
"""

import re
import datetime
from typing import Dict, Any, List

def markdown_table_to_html(md_table: str) -> str:
    """Converte uma tabela Markdown em uma tabela HTML estilizada."""
    lines = [line.strip() for line in md_table.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return md_table

def apply_inline_formatting(text: str) -> str:
    """Aplica negrito e itálico mesmo com espaços internos entre os asteriscos (ex: ** texto ** ou **texto**)."""
    # Trata negrito com espaços internos: ** texto ** -> <strong>texto</strong>
    text = re.sub(r"\*\*\s*(.+?)\s*\*\*", r"<strong>\1</strong>", text)
    # Trata itálico com espaços ou padrão: * texto * -> <em>texto</em>
    text = re.sub(r"(?<!\*)\*\s*([^\*]+?)\s*\*(?!\*)", r"<em>\1</em>", text)
    return text

def markdown_table_to_html(md_table: str) -> str:
    """Converte uma tabela Markdown em uma tabela HTML estilizada."""
    lines = [line.strip() for line in md_table.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return md_table

    html = ['<table class="data-table">']
    
    # Cabeçalho
    header_cols = [apply_inline_formatting(c.strip()) for c in lines[0].strip("|").split("|")]
    html.append("  <thead>\n    <tr>")
    for col in header_cols:
        html.append(f"      <th>{col}</th>")
    html.append("    </tr>\n  </thead>")
    
    # Pula a linha separadora (ex: |---|---|)
    body_lines = lines[2:] if len(lines) > 2 and re.match(r"^\|?[\s\-:|]+\|?$", lines[1]) else lines[1:]
    
    html.append("  <tbody>")
    for row in body_lines:
        cols = [apply_inline_formatting(c.strip()) for c in row.strip("|").split("|")]
        html.append("    <tr>")
        for col in cols:
            html.append(f"      <td>{col}</td>")
        html.append("    </tr>")
    html.append("  </tbody>\n</table>")
    return "\n".join(html)

def format_text_block(text: str) -> str:
    """Formata texto comum com suporte a parágrafos, listas e tabelas markdown."""
    text = text.strip()
    if not text:
        return '<p class="meta-value nao-informado">[NÃO INFORMADO]</p>'

    # Detecta tabelas Markdown completas
    # Linha de cabeçalho | ..., linha separadora |---|..., e linhas de dados subsequentes
    table_pattern = re.compile(r"((?:^[ \t]*\|.+?\|[ \t]*\n){2,}(?:^[ \t]*\|.+?\|[ \t]*(?:\n|$))*)", re.MULTILINE)
    
    parts = []
    last_idx = 0
    for match in table_pattern.finditer(text):
        start, end = match.span()
        before = text[last_idx:start].strip()
        if before:
            parts.append(process_paragraphs_and_lists(before))
        table_html = markdown_table_to_html(match.group(1))
        parts.append(table_html)
        last_idx = end
        
    remaining = text[last_idx:].strip()
    if remaining:
        parts.append(process_paragraphs_and_lists(remaining))

    return "\n".join(parts) if parts else process_paragraphs_and_lists(text)

def process_paragraphs_and_lists(text: str) -> str:
    """Transforma linhas soltas e itens em listas e parágrafos."""
    lines = text.split("\n")
    output = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                output.append("</ul>")
                in_list = False
            continue

        # Item de lista (- ou * ou 1.)
        list_match = re.match(r"^(\*|-|\d+\.)\s+(.+)$", stripped)
        if list_match:
            if not in_list:
                output.append("<ul>")
                in_list = True
            item_text = apply_inline_formatting(list_match.group(2))
            output.append(f"  <li>{item_text}</li>")
        else:
            if in_list:
                output.append("</ul>")
                in_list = False

            # Imagem em Markdown: ![Legenda](URL_ou_Base64)
            img_match = re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped)
            if img_match:
                alt_text = img_match.group(1).strip()
                src_val = img_match.group(2).strip()
                caption_html = f'<figcaption class="image-caption">{alt_text}</figcaption>' if alt_text else ''
                output.append(f'<figure class="report-image-box"><img src="{src_val}" alt="{alt_text}" class="content-img">{caption_html}</figure>')
            # Subtítulos / Títulos internos Markdown (###, ####, etc)
            elif header_match := re.match(r"^(#{1,6})\s+(.+)$", stripped):
                level = len(header_match.group(1))
                h_text = apply_inline_formatting(header_match.group(2).strip())
                # Mapeia níveis de subtítulo com estilo consistente
                output.append(f'<h4 class="sub-section-title">{h_text}</h4>')
            else:
                line_html = apply_inline_formatting(stripped)
                output.append(f"<p>{line_html}</p>")

    if in_list:
        output.append("</ul>")

    return "\n".join(output)

def parse_document_content(raw_content: str) -> Dict[str, Any]:
    """
    Analisa o conteúdo bruto e extrai metadados e seções.
    Trata campos ausentes aplicando [NÃO INFORMADO] de forma elegante.
    """
    data = {
        "titulo": None,
        "subtitulo": None,
        "tipo_documento": "",
        "orgao": None,
        "autor": None,
        "data": None,
        "codigo": None,
        "logo": None,
        "secoes": [], # lista de tuplas (titulo_secao, conteudo_html)
        "assinaturas": []
    }

    # Garante que quebras de linha escapadas (\n) sejam tratadas como quebra real
    if "\\n" in raw_content and "\n" not in raw_content:
        raw_content = raw_content.replace("\\n", "\n")

    lines = raw_content.splitlines()
    remaining_lines = []

    # 1. Varredura por metadados no início ou em chaves explicitas (suporta **Campo:** e variações)
    meta_key_patterns = {
        "orgao": re.compile(r"^(?:\*\*)?(?:[óo]rg[ãa]o(?:\s*respons[áa]vel)?|entidade|institui[çc][ãa]o|secretaria)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "autor": re.compile(r"^(?:\*\*)?(?:autor|respons[áa]vel(?:\s*pela\s*elabora[çc][ãa]o(?:\s*da\s*ata)?)?|elaborado\s*por|relator)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "data": re.compile(r"^(?:\*\*)?(?:data|emiss[ãa]o)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "codigo": re.compile(r"^(?:\*\*)?(?:c[óo]digo|n[úu]mero|identificador|id|processo)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "tipo_documento": re.compile(r"^(?:\*\*)?(?:tipo(?:\s*de\s*documento)?)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "logo": re.compile(r"^(?:\*\*)?(?:logo|bras[ãa]o|logotipo|imagem_logo)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
    }

    # 1. Varredura por metadados e cabeçalho sequencial
    remaining_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if remaining_lines:
                remaining_lines.append(line)
            continue

        matched_meta = False

        # Verifica se é uma chave de metadado
        for key, pattern in meta_key_patterns.items():
            if not data[key]:
                m = pattern.match(stripped)
                if m:
                    val = m.group(1).strip()
                    val = re.sub(r"^\*+|\*+$", "", val).strip()
                    data[key] = val
                    matched_meta = True
                    break

        if matched_meta:
            continue

        # Detecta entidade / órgão ou título no topo antes do corpo principal
        if stripped.startswith("# ") and not stripped.startswith("## ") and not data["titulo"]:
            header_text = stripped[2:].strip()
            is_gov_entity = re.search(r"(?:prefeitura|c[âa]mara|secretaria|governo|tribunal|minist[ée]rio)", header_text, re.IGNORECASE)
            
            if re.search(r"^ata\s*(?:de\s*audi[êe]ncia\s*p[úu]blica)?$", header_text, re.IGNORECASE):
                data["tipo_documento"] = "Ata de Audiência Pública"
                continue

            if not data["orgao"] and is_gov_entity:
                data["orgao"] = header_text
                continue
            else:
                data["titulo"] = header_text
                continue

        # Detecta subtítulo caso seja um ## inicial antes das seções
        if stripped.startswith("## ") and not data["subtitulo"] and not data["secoes"] and not re.match(r"^##\s*\d+[\.\)]", stripped):
            data["subtitulo"] = stripped[3:].strip()
            continue

        remaining_lines.append(line)

    # 2. Processa o corpo do relatório (seções)
    current_section_title = None
    current_section_lines = []

    for line in remaining_lines:
        stripped = line.strip()
        if not stripped and not current_section_lines:
            continue

        # Detecta início de seção (## Título, ### Título ou Nome da Seção em CAPS com dois pontos)
        section_match = re.match(r"^(?:#{1,6}\s*)(.+)$", stripped)
        if not section_match:
            section_match = re.match(r"^(?:\d+[\.\)]\s*)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{4,}):?$", stripped)

        if section_match:
            content_str = "\n".join(current_section_lines).strip()
            if content_str:
                sec_title = current_section_title or ""
                sec_html = format_text_block(content_str)
                data["secoes"].append((sec_title, sec_html))
            current_section_lines = []
            clean_sec_title = section_match.group(1).strip()
            clean_sec_title = re.sub(r"^#+\s*", "", clean_sec_title)
            current_section_title = clean_sec_title
        else:
            current_section_lines.append(line)

    # Adiciona a última seção se houver conteúdo
    content_str = "\n".join(current_section_lines).strip()
    if content_str or current_section_title:
        sec_title = current_section_title or ""
        sec_html = format_text_block(content_str)
        data["secoes"].append((sec_title, sec_html))

    # Fallbacks inteligentes para campos ausentes (Regra de Edge Case 1: Opção A)
    if not data["titulo"]:
        data["titulo"] = "Relatório Institucional"
    if not data["subtitulo"]:
        data["subtitulo"] = ""
    
    if not data["orgao"]:
        data["orgao_val"] = "[NÃO INFORMADO]"
        data["orgao_class"] = "nao-informado"
    else:
        data["orgao_val"] = data["orgao"]
        data["orgao_class"] = ""

    if not data["autor"]:
        data["autor_val"] = "[NÃO INFORMADO]"
        data["autor_class"] = "nao-informado"
    else:
        data["autor_val"] = data["autor"]
        data["autor_class"] = ""

    if not data["data"]:
        data["data_val"] = datetime.date.today().strftime("%d/%m/%Y")
        data["data_class"] = ""
    else:
        data["data_val"] = data["data"]
        data["data_class"] = ""

    if not data["codigo"]:
        # Gera identificador automático baseado na data/hora
        data["codigo_val"] = datetime.datetime.now().strftime("REL-%Y%m%d-%H%M")
        data["codigo_class"] = ""
    else:
        data["codigo_val"] = data["codigo"]
        data["codigo_class"] = ""

    # Seções padrão se nenhuma foi identificada
    if not data["secoes"]:
        data["secoes"].append(("Conteúdo Principal", format_text_block(raw_content)))

    # Assinatura automática se houver autor
    if data["autor"] and data["autor"] != "[NÃO INFORMADO]":
        data["assinaturas"].append((data["autor"], data["orgao"] or "Responsável Técnico"))

    return data
