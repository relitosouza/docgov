"""
Gerador de relatório HTML a partir de dados estruturados e template.
"""

import os
import datetime
from typing import Dict, Any

def render_report_html(data: Dict[str, Any], template_path: str, output_path: str) -> str:
    """Renderiza os dados no template HTML e salva no arquivo de destino."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template não encontrado em: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Monta o HTML das seções
    secoes_html_parts = []
    for title, content_html in data.get("secoes", []):
        title_tag = f'<h2 class="section-title">{title}</h2>' if title and title.strip() else ''
        secao_block = f"""
      <section class="report-section">
        {title_tag}
        <div class="section-content">
          {content_html}
        </div>
      </section>
        """
        secoes_html_parts.append(secao_block)
    secoes_html = "\n".join(secoes_html_parts)

    # Monta o bloco de encerramento e assinaturas
    now = datetime.datetime.now()
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    data_extenso = f"{now.day} de {meses[now.month - 1]} de {now.year}"
    
    autor_nome = data.get("autor_val", "Responsável Técnico")
    orgao_nome = data.get("orgao_val", "")
    if orgao_nome == "[NÃO INFORMADO]":
        orgao_nome = "Órgão Responsável"
    
    # Bloco formal de encerramento
    include_sig = data.get("include_signature", True)
    if include_sig:
        signature_block = f"""
      <div class="signature-grid">
        <div class="signature-box">
          <div class="sig-line"></div>
          <div class="sig-name">{autor_nome}</div>
          <div class="sig-role">{orgao_nome}</div>
        </div>
      </div>
        """
    else:
        signature_block = ""

    if include_sig:
        encerramento_html = f"""
    <div class="report-closure">
      {signature_block}
    </div>
    """
    else:
        encerramento_html = ""

    # Monta o bloco de logo
    logo_data = data.get("logo")
    logo_html = ""
    if logo_data:
        logo_str = str(logo_data).strip()
        # Se for caminho local de imagem existente, converte para base64 para o HTML ser 100% independente
        if os.path.exists(logo_str):
            import base64
            import mimetypes
            mime_type, _ = mimetypes.guess_type(logo_str)
            mime_type = mime_type or "image/png"
            with open(logo_str, "rb") as img_file:
                b64_content = base64.b64encode(img_file.read()).decode("utf-8")
                logo_str = f"data:{mime_type};base64,{b64_content}"
        
        logo_html = f'<img src="{logo_str}" alt="Brasão/Logo" class="report-logo-img">'
        
    # Monta o bloco de Metadados do Cabeçalho (Opcional)
    include_meta = data.get("include_meta_box", True)
    if include_meta:
        meta_grid_html = f"""
            <div class="meta-grid">
              <div class="meta-item">
                <span class="meta-label">Órgão</span>
                <span class="meta-value {data.get("orgao_class", "")}">{data.get("orgao_val", "[NÃO INFORMADO]")}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Responsável</span>
                <span class="meta-value {data.get("autor_class", "")}">{data.get("autor_val", "[NÃO INFORMADO]")}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Identificador / Cód.</span>
                <span class="meta-value {data.get("codigo_class", "")}">{data.get("codigo_val", "S/N")}</span>
              </div>
            </div>
        """
    else:
        meta_grid_html = ""

    # Substituição de placeholders
    replacements = {
        "{{LOGO_HTML}}": logo_html,
        "{{TITULO}}": data.get("titulo", "Relatório"),
        "{{SUBTITULO}}": data.get("subtitulo", ""),
        "{{TIPO_DOCUMENTO_HTML}}": f'<div class="header-badge">{data.get("tipo_documento")}</div>' if data.get("tipo_documento") else '',
        "{{META_GRID_HTML}}": meta_grid_html,
        "{{ORGAO}}": data.get("orgao_val", "[NÃO INFORMADO]"),
        "{{ORGAO_CLASS}}": data.get("orgao_class", ""),
        "{{AUTOR}}": data.get("autor_val", "[NÃO INFORMADO]"),
        "{{AUTOR_CLASS}}": data.get("autor_class", ""),
        "{{DATA}}": data.get("data_val", "[NÃO INFORMADO]"),
        "{{DATA_CLASS}}": data.get("data_class", ""),
        "{{CODIGO}}": data.get("codigo_val", "S/N"),
        "{{CODIGO_CLASS}}": data.get("codigo_class", ""),
        "{{SECOES_HTML}}": secoes_html,
        "{{ENCERRAMENTO_HTML}}": encerramento_html,
        "{{DATA_HORA_GERACAO}}": now.strftime("%d/%m/%Y às %H:%M"),
        "{{RESPONSAVEL_RODAPE}}": autor_nome,
        "{{PAGE_ORIENTATION}}": "landscape" if data.get("orientation") == "landscape" else "portrait",
        "{{BODY_ORIENTATION_CLASS}}": "orientation-landscape" if data.get("orientation") == "landscape" else "orientation-portrait",
    }

    html_final = template
    for placeholder, val in replacements.items():
        html_final = html_final.replace(placeholder, str(val))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_final)

    return output_path
