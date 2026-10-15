"""
Módulo para geração de relatório institucional no formato DOCX (Microsoft Word).
Converte a estrutura de dados (metadados, seções, listas, tabelas, negrito/itálico) em um documento DOCX elegante.
Usa a mesma tipografia (Aptos / Segoe UI / Arial / Calibri) e a paleta de cores idêntica ao HTML/PDF.
"""

import os
import re
import datetime
from typing import Dict, Any, List
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# Paleta de Cores IDÊNTICA ao CSS do Modelo de Relatório
# --primary-dark: #172554 (Azul Marinho Escuro do Título)
COLOR_PRIMARY_DARK = RGBColor(23, 37, 84)

# --primary: #1e3a8a (Azul Institucional dos Títulos de Seção / Bordas)
COLOR_PRIMARY = RGBColor(30, 58, 138)

# --primary-light: #3b82f6 (Azul Claro)
COLOR_PRIMARY_LIGHT = RGBColor(59, 130, 246)

# --text: #0f172a (Texto principal escuro)
COLOR_TEXT = RGBColor(15, 23, 42)

# --section-text: #334155 (Texto dos parágrafos do corpo)
COLOR_BODY_TEXT = RGBColor(51, 65, 85)

# --text-muted: #64748b (Rótulos e subtítulos acinzentados)
COLOR_MUTED = RGBColor(100, 116, 139)

# --border: #e2e8f0
COLOR_BORDER_HEX = "E2E8F0"

# --bg-meta / thead: #f1f5f9
COLOR_BG_META_HEX = "F1F5F9"

# Família de Fonte padrão universal para compatibilidade no Word
FONT_FAMILY = "Segoe UI"
FONT_FALLBACK = "Arial"

def configure_doc_styles(doc):
    """Configura o estilo 'Normal' do documento para herdar a tipografia e cores padrão do relatório."""
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = FONT_FAMILY
    font.size = Pt(10.5)
    font.color.rgb = COLOR_BODY_TEXT
    
    # Define rFonts para garantir a fonte em todo o documento Word
    rFonts = style_normal.element.rPr.get_or_add_rFonts()
    rFonts.set(qn('w:ascii'), FONT_FAMILY)
    rFonts.set(qn('w:hAnsi'), FONT_FAMILY)
    rFonts.set(qn('w:cs'), FONT_FALLBACK)

def set_cell_background(cell, fill_hex: str):
    """Define a cor de fundo de uma célula da tabela."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Define o espaçamento interno (padding) de uma célula."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_formatted_runs(paragraph, text: str):
    """Interpreta trechos com **negrito** e *itálico* e insere runs formatados no parágrafo."""
    pattern = re.compile(r'(\*\*\s*.*?\s*\*\*|\*(?!\*)\s*.*?\s*\*(?!\*))')
    tokens = pattern.split(text)

    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**') and len(token) >= 4:
            clean = token[2:-2].strip()
            run = paragraph.add_run(clean)
            run.bold = True
            run.font.name = FONT_FAMILY
            run.font.color.rgb = COLOR_TEXT
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
            clean = token[1:-1].strip()
            run = paragraph.add_run(clean)
            run.italic = True
            run.font.name = FONT_FAMILY
            run.font.color.rgb = COLOR_BODY_TEXT
        else:
            run = paragraph.add_run(token)
            run.font.name = FONT_FAMILY
            run.font.color.rgb = COLOR_BODY_TEXT

def generate_report_docx(data: Dict[str, Any], output_path: str) -> str:
    """Gera um arquivo .docx com a mesma paleta visual e tipográfica do relatório HTML/PDF."""
    doc = docx.Document()
    configure_doc_styles(doc)

    # 1. Configuração de Página e Margens (A4)
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    if data.get("orientation") == "landscape":
        section.page_width = Inches(11.69)
        section.page_height = Inches(8.27)

    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    # 2. Cabeçalho Institucional (com suporte a Brasão/Logo)
    logo_data = data.get("logo")
    logo_stream = None

    if logo_data:
        logo_str = str(logo_data).strip()
        import io, base64
        if logo_str.startswith("data:image"):
            try:
                header, encoded = logo_str.split(",", 1)
                image_bytes = base64.b64decode(encoded)
                logo_stream = io.BytesIO(image_bytes)
            except Exception as e:
                print(f"Erro ao decodificar imagem base64 para DOCX: {e}")
        elif os.path.exists(logo_str):
            logo_stream = logo_str

    if logo_stream:
        # Layout lado a lado: Tabela sem borda com 2 colunas (Logo na esquerda, Títulos na direita)
        header_table = doc.add_table(rows=1, cols=2)
        header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        header_table.autofit = True
        
        # Remove bordas da tabela de cabeçalho
        tblPr = header_table._tbl.tblPr
        tblBorders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="none"/><w:left w:val="none"/><w:bottom w:val="none"/><w:right w:val="none"/>'
            f'<w:insideH w:val="none"/><w:insideV w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr.append(tblBorders)

        cell_logo, cell_text = header_table.rows[0].cells
        cell_logo.width = Inches(1.3)
        cell_text.width = Inches(5.4)

        # Insere imagem
        p_logo = cell_logo.paragraphs[0]
        p_logo.paragraph_format.space_before = Pt(0)
        p_logo.paragraph_format.space_after = Pt(0)
        try:
            run_logo = p_logo.add_run()
            run_logo.add_picture(logo_stream, width=Inches(1.15))
        except Exception as e:
            print(f"Erro ao inserir imagem no DOCX: {e}")

        # Insere títulos ao lado da logo
        p_title = cell_text.paragraphs[0]
        p_title.paragraph_format.space_before = Pt(0)
        p_title.paragraph_format.space_after = Pt(2)
        run_title = p_title.add_run(str(data.get("titulo", "RELATÓRIO INSTITUCIONAL")).upper())
        run_title.font.name = FONT_FAMILY
        run_title.font.size = Pt(16)
        run_title.font.bold = True
        run_title.font.color.rgb = COLOR_PRIMARY_DARK

        subtitulo = data.get("subtitulo")
        if subtitulo and str(subtitulo).strip():
            p_sub = cell_text.add_paragraph()
            p_sub.paragraph_format.space_before = Pt(0)
            p_sub.paragraph_format.space_after = Pt(4)
            run_sub = p_sub.add_run(str(subtitulo))
            run_sub.font.name = FONT_FAMILY
            run_sub.font.size = Pt(10)
            run_sub.font.color.rgb = COLOR_MUTED

        tipo_doc = data.get("tipo_documento")
        if tipo_doc:
            p_badge = cell_text.add_paragraph()
            p_badge.paragraph_format.space_before = Pt(0)
            p_badge.paragraph_format.space_after = Pt(4)
            run_badge = p_badge.add_run(f"[{tipo_doc}]")
            run_badge.font.name = FONT_FAMILY
            run_badge.font.size = Pt(9)
            run_badge.font.bold = True
            run_badge.font.color.rgb = COLOR_PRIMARY_LIGHT

    else:
        # Sem logo: Layout padrão
        p_title = doc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(0)
        p_title.paragraph_format.space_after = Pt(2)
        run_title = p_title.add_run(str(data.get("titulo", "RELATÓRIO INSTITUCIONAL")).upper())
        run_title.font.name = FONT_FAMILY
        run_title.font.size = Pt(16)
        run_title.font.bold = True
        run_title.font.color.rgb = COLOR_PRIMARY_DARK

        subtitulo = data.get("subtitulo")
        if subtitulo and str(subtitulo).strip():
            p_sub = doc.add_paragraph()
            p_sub.paragraph_format.space_before = Pt(0)
            p_sub.paragraph_format.space_after = Pt(6)
            run_sub = p_sub.add_run(str(subtitulo))
            run_sub.font.name = FONT_FAMILY
            run_sub.font.size = Pt(10)
            run_sub.font.color.rgb = COLOR_MUTED

        tipo_doc = data.get("tipo_documento")
        if tipo_doc:
            p_badge = doc.add_paragraph()
            p_badge.paragraph_format.space_before = Pt(0)
            p_badge.paragraph_format.space_after = Pt(8)
            run_badge = p_badge.add_run(f"[{tipo_doc}]")
            run_badge.font.name = FONT_FAMILY
            run_badge.font.size = Pt(9)
            run_badge.font.bold = True
            run_badge.font.color.rgb = COLOR_PRIMARY_LIGHT

    # Linha divisória fina (border-bottom azul do cabeçalho)
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(4)
    p_div.paragraph_format.space_after = Pt(14)
    run_div = p_div.add_run("―" * 58)
    run_div.font.size = Pt(8)
    run_div.font.color.rgb = COLOR_PRIMARY

    # 3. Metadados (Quadro de Identificação) se habilitado
    if data.get("include_meta_box", True):
        table_meta = doc.add_table(rows=1, cols=3)
        table_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_meta.autofit = True

        hdr_cells = table_meta.rows[0].cells
        labels_values = [
            ("ÓRGÃO", data.get("orgao_val", "[NÃO INFORMADO]")),
            ("RESPONSÁVEL", data.get("autor_val", "[NÃO INFORMADO]")),
            ("IDENTIFICADOR", data.get("codigo_val", "S/N"))
        ]

        for i, (label, val) in enumerate(labels_values):
            cell = hdr_cells[i]
            set_cell_background(cell, COLOR_BG_META_HEX)
            set_cell_margins(cell, top=120, bottom=120, left=150, right=150)
            
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            run_lbl = p.add_run(label + "\n")
            run_lbl.font.name = FONT_FAMILY
            run_lbl.font.size = Pt(8.5)
            run_lbl.font.bold = True
            run_lbl.font.color.rgb = COLOR_MUTED

            run_v = p.add_run(str(val))
            run_v.font.name = FONT_FAMILY
            run_v.font.size = Pt(10)
            run_v.font.bold = True
            if val == "[NÃO INFORMADO]":
                run_v.font.color.rgb = RGBColor(148, 163, 184)
                run_v.font.italic = True
            else:
                run_v.font.color.rgb = COLOR_TEXT

        # Espaçamento após o quadro
        doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # 4. Seções de Conteúdo
    for title, content_html in data.get("secoes", []):
        # Título da Seção (apenas se existir título)
        if title and title.strip():
            p_sec = doc.add_paragraph()
            p_sec.paragraph_format.space_before = Pt(18)
            p_sec.paragraph_format.space_after = Pt(6)
            run_sec = p_sec.add_run(str(title).upper())
            run_sec.font.name = FONT_FAMILY
            run_sec.font.size = Pt(11.5)
            run_sec.font.bold = True
            run_sec.font.color.rgb = COLOR_PRIMARY

        # Processamento do conteúdo:
        if '<table class="data-table">' in content_html:
            parts = re.split(r'(<table class="data-table">.*?</table>)', content_html, flags=re.DOTALL)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if part.startswith('<table class="data-table">'):
                    # Converte tabela HTML para tabela DOCX
                    tr_matches = re.findall(r'<tr>(.*?)</tr>', part, flags=re.DOTALL)
                    rows_data = []
                    for tr in tr_matches:
                        tds = re.findall(r'<t[dh]>(.*?)</t[dh]>', tr)
                        if tds:
                            clean_tds = [re.sub(r'<[^>]+>', '', t).strip() for t in tds]
                            rows_data.append(clean_tds)

                    if rows_data:
                        docx_table = doc.add_table(rows=len(rows_data), cols=len(rows_data[0]))
                        docx_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                        docx_table.style = 'Table Grid'
                        
                        for r_idx, row in enumerate(rows_data):
                            for c_idx, cell_text in enumerate(row):
                                cell = docx_table.cell(r_idx, c_idx)
                                set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
                                if r_idx == 0:
                                    set_cell_background(cell, COLOR_BG_META_HEX)
                                p = cell.paragraphs[0]
                                p.paragraph_format.space_before = Pt(0)
                                p.paragraph_format.space_after = Pt(0)
                                run = p.add_run(cell_text)
                                run.font.name = FONT_FAMILY
                                run.font.size = Pt(9.5)
                                if r_idx == 0:
                                    run.font.bold = True
                                    run.font.color.rgb = COLOR_PRIMARY_DARK
                                else:
                                    run.font.color.rgb = COLOR_BODY_TEXT
                        
                        doc.add_paragraph().paragraph_format.space_after = Pt(8)
                else:
                    render_html_text_to_docx(doc, part)
        else:
            render_html_text_to_docx(doc, content_html)

    # 5. Assinatura (se habilitada)
    if data.get("include_signature", True):
        autor_nome = data.get("autor_val", "Responsável Técnico")
        orgao_nome = data.get("orgao_val", "")
        if orgao_nome == "[NÃO INFORMADO]":
            orgao_nome = "Órgão Responsável"

        p_sig_line = doc.add_paragraph()
        p_sig_line.paragraph_format.space_before = Pt(30)
        p_sig_line.paragraph_format.space_after = Pt(2)
        p_sig_line.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_sline = p_sig_line.add_run("____________________________________________________")
        run_sline.font.name = FONT_FAMILY
        run_sline.font.color.rgb = RGBColor(148, 163, 184)

        p_sig_name = doc.add_paragraph()
        p_sig_name.paragraph_format.space_before = Pt(2)
        p_sig_name.paragraph_format.space_after = Pt(1)
        p_sig_name.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_sname = p_sig_name.add_run(autor_nome)
        run_sname.font.name = FONT_FAMILY
        run_sname.font.size = Pt(10.5)
        run_sname.font.bold = True
        run_sname.font.color.rgb = COLOR_TEXT

        p_sig_role = doc.add_paragraph()
        p_sig_role.paragraph_format.space_before = Pt(0)
        p_sig_role.paragraph_format.space_after = Pt(12)
        p_sig_role.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_srole = p_sig_role.add_run(orgao_nome)
        run_srole.font.name = FONT_FAMILY
        run_srole.font.size = Pt(9.5)
        run_srole.font.color.rgb = COLOR_MUTED

    # Salva o arquivo DOCX
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path

def render_html_text_to_docx(doc, html_snippet: str):
    """Interpreta parágrafos (<p>), itens de lista (<li>), subtítulos (<h4>) e imagens (<figure>)."""
    raw_blocks = re.findall(r'(<(?:p|li|h4|figure)[^>]*>.*?</(?:p|li|h4|figure)>)', html_snippet, flags=re.DOTALL)
    if not raw_blocks:
        clean = re.sub(r'<[^>]+>', '', html_snippet).strip()
        if clean:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            add_formatted_runs(p, clean)
        return

    for block in raw_blocks:
        block = block.strip()
        if block.startswith('<figure') or 'class="report-image-box"' in block:
            img_src_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block)
            if img_src_m:
                src_val = img_src_m.group(1).strip()
                import io, base64
                img_stream = None
                if src_val.startswith("data:image"):
                    try:
                        _, encoded = src_val.split(",", 1)
                        img_stream = io.BytesIO(base64.b64decode(encoded))
                    except Exception as err:
                        print(f"Erro ao decodificar imagem para DOCX: {err}")
                elif os.path.exists(src_val):
                    img_stream = src_val

                if img_stream:
                    p = doc.add_paragraph()
                    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before = Pt(8)
                    p.paragraph_format.space_after = Pt(2)
                    run = p.add_run()
                    try:
                        # Adiciona imagem com limite de 5.5 polegadas (largura útil de A4 com margens)
                        run.add_picture(img_stream, width=Inches(5.5))
                    except Exception as err:
                        print(f"Erro ao inserir imagem no docx: {err}")
                    
                    # Adiciona legenda se houver
                    cap_m = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', block)
                    if cap_m and cap_m.group(1).strip():
                        p_cap = doc.add_paragraph()
                        p_cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_cap.paragraph_format.space_before = Pt(2)
                        p_cap.paragraph_format.space_after = Pt(8)
                        r_cap = p_cap.add_run(cap_m.group(1).strip())
                        r_cap.font.name = FONT_FAMILY
                        r_cap.font.size = Pt(8.5)
                        r_cap.font.italic = True
                        r_cap.font.color.rgb = COLOR_MUTED
        elif block.startswith('<h4'):
            text = re.sub(r'</?h4[^>]*>', '', block).strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(re.sub(r'<[^>]+>', '', text))
            run.font.name = FONT_FAMILY
            run.font.size = Pt(10.5)
            run.font.bold = True
            run.font.color.rgb = COLOR_PRIMARY_DARK
        elif block.startswith('<li'):
            text = re.sub(r'</?li[^>]*>', '', block).strip()
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(3)
            parse_html_inline_to_runs(p, text)
        else: # <p>
            text = re.sub(r'</?p[^>]*>', '', block).strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            parse_html_inline_to_runs(p, text)

def parse_html_inline_to_runs(paragraph, text: str):
    """Converte <strong>...</strong> e <em>...</em> em runs com estilo no docx."""
    tokens = re.split(r'(</?(?:strong|em|b|i)>)', text)
    is_bold = False
    is_italic = False

    for token in tokens:
        if not token:
            continue
        lower = token.lower()
        if lower in ('<strong>', '<b>'):
            is_bold = True
        elif lower in ('</strong>', '</b>'):
            is_bold = False
        elif lower in ('<em>', '<i>'):
            is_italic = True
        elif lower in ('</em>', '</i>'):
            is_italic = False
        else:
            clean_text = re.sub(r'<[^>]+>', '', token)
            pattern = re.compile(r'(\*\*\s*.*?\s*\*\*|\*(?!\*)\s*.*?\s*\*(?!\*))')
            sub_tokens = pattern.split(clean_text)
            for st in sub_tokens:
                if not st:
                    continue
                if st.startswith('**') and st.endswith('**') and len(st) >= 4:
                    run = paragraph.add_run(st[2:-2].strip())
                    run.font.name = FONT_FAMILY
                    run.bold = True
                    run.italic = is_italic
                    run.font.color.rgb = COLOR_TEXT
                elif st.startswith('*') and st.endswith('*') and len(st) >= 2:
                    run = paragraph.add_run(st[1:-1].strip())
                    run.font.name = FONT_FAMILY
                    run.bold = is_bold
                    run.italic = True
                    run.font.color.rgb = COLOR_BODY_TEXT
                else:
                    run = paragraph.add_run(st)
                    run.font.name = FONT_FAMILY
                    run.bold = is_bold
                    run.italic = is_italic
                    run.font.color.rgb = COLOR_BODY_TEXT if not is_bold else COLOR_TEXT
