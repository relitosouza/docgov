"""
Módulo para extração e leitura de arquivos PDF para o Modelo Intermediário Canônico.
Utiliza as ferramentas de alto desempenho do sistema (pdftotext e pdfimages).
Extrai metadados institucionais (Título, Órgão, Responsável, Data), estrutura de seções,
parágrafos, listas e imagens embutidas convertidas em base64.
"""

import os
import re
import shutil
import tempfile
import subprocess
import base64
from typing import Dict, Any, List

try:
    from document_model import DocumentModel, Section, Block, InlineSpan
    from parse_content import parse_document_content
except ImportError:
    from execution.document_model import DocumentModel, Section, Block, InlineSpan
    from execution.parse_content import parse_document_content

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrai texto estruturado do PDF usando pdftotext preservando layout e quebras."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

    # -layout preserva o alinhamento visual de colunas e parágrafos
    cmd = ["pdftotext", "-layout", "-enc", "UTF-8", pdf_path, "-"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return res.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        # Fallback sem a flag -layout caso necessário
        cmd_simple = ["pdftotext", "-enc", "UTF-8", pdf_path, "-"]
        res = subprocess.run(cmd_simple, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return res.stdout.decode("utf-8", errors="replace")

def extract_images_from_pdf(pdf_path: str, max_images: int = 10) -> List[str]:
    """Extrai imagens embutidas do PDF via pdfimages e retorna lista de data URIs base64."""
    if not shutil.which("pdfimages"):
        return []

    images_b64 = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        prefix = os.path.join(tmp_dir, "img")
        cmd = ["pdfimages", "-png", pdf_path, prefix]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            files = sorted([f for f in os.listdir(tmp_dir) if f.startswith("img-") and f.endswith(".png")])
            for f in files[:max_images]:
                img_full_path = os.path.join(tmp_dir, f)
                # Ignora imagens extremamente pequenas (ex: linhas divisórias ou 1x1 pixels menores que 200 bytes)
                if os.path.getsize(img_full_path) < 300:
                    continue
                with open(img_full_path, "rb") as img_file:
                    b64 = base64.b64encode(img_file.read()).decode("utf-8")
                    images_b64.append(f"data:image/png;base64,{b64}")
        except Exception as e:
            print(f"⚠️ Erro ao extrair imagens do PDF: {e}")

    return images_b64

def parse_pdf_file(pdf_path: str) -> DocumentModel:
    """Lê um arquivo PDF e converte seu conteúdo e metadados no DocumentModel canônico."""
    raw_text = extract_text_from_pdf(pdf_path)
    extracted_images = extract_images_from_pdf(pdf_path)

    # Limpa cabeçalhos/rodapés repetidos de página gerados pelo navegador (ex: '15/10/2026, 09:58  TITULO')
    cleaned_lines = []
    for line in raw_text.splitlines():
        if re.match(r"^\s*\d{1,2}/\d{1,2}/\d{4},\s*\d{1,2}:\d{2}", line):
            continue
        cleaned_lines.append(line)
    processed_text = "\n".join(cleaned_lines)

    # 1. Extração prévia de blocos tabulares de metadados típicos de PDF institucional
    orgao_found = None
    autor_found = None
    codigo_found = None

    lines = processed_text.splitlines()
    for i, line in enumerate(lines):
        if "ÓRGÃO" in line and ("RESPONSÁVEL" in line or "IDENTIFICADOR" in line):
            # As linhas subsequentes contêm os valores das colunas
            if i + 1 < len(lines):
                val_line = lines[i + 1]
                # Se for separado por múltiplos espaços (layout de colunas)
                cols = re.split(r"\s{4,}", val_line.strip())
                if len(cols) >= 2:
                    orgao_found = cols[0].strip()
                    autor_found = cols[1].strip()
                    if len(cols) >= 3:
                        codigo_found = cols[2].strip()
                # Verifica se há continuação de órgão na linha seguinte
                if i + 2 < len(lines) and not codigo_found:
                    next_line = lines[i + 2].strip()
                    if "REL-" in next_line:
                        codigo_found = next_line
                    elif next_line and not next_line.startswith(("1.", "2.", "3.", "4.")):
                        orgao_found = (orgao_found + " " + next_line).strip()

    # Usa o parser híbrido para extrair o restante
    data_dict = parse_document_content(processed_text)

    # Aplica os metadados encontrados
    if orgao_found:
        data_dict["orgao"] = orgao_found
        data_dict["orgao_val"] = orgao_found
        data_dict["orgao_class"] = ""
    if autor_found:
        data_dict["autor"] = autor_found
        data_dict["autor_val"] = autor_found
        data_dict["autor_class"] = ""
    if codigo_found:
        data_dict["codigo"] = codigo_found
        data_dict["codigo_val"] = codigo_found
        data_dict["codigo_class"] = ""

    # Se o primeiro título de seção for o título geral em CAPS, promove a título
    titulo_doc = data_dict.get("titulo")
    if (not titulo_doc or titulo_doc == "Relatório Institucional") and data_dict.get("secoes"):
        first_sec = data_dict["secoes"][0][0]
        if first_sec and re.search(r"(?:relat[óo]rio|ata|parecer|laudo)", first_sec, re.IGNORECASE):
            data_dict["titulo"] = first_sec
            data_dict["secoes"] = data_dict["secoes"][1:]

    model = DocumentModel(
        titulo=data_dict.get("titulo") or "Relatório Institucional",
        subtitulo=data_dict.get("subtitulo") or "",
        tipo_documento=data_dict.get("tipo_documento") or "",
        orgao=data_dict.get("orgao") or "",
        orgao_val=data_dict.get("orgao_val") or "[NÃO INFORMADO]",
        orgao_class=data_dict.get("orgao_class") or "nao-informado",
        autor=data_dict.get("autor") or "",
        autor_val=data_dict.get("autor_val") or "[NÃO INFORMADO]",
        autor_class=data_dict.get("autor_class") or "nao-informado",
        data=data_dict.get("data") or "",
        data_val=data_dict.get("data_val") or "",
        data_class=data_dict.get("data_class") or "",
        codigo=data_dict.get("codigo") or "",
        codigo_val=data_dict.get("codigo_val") or "",
        codigo_class=data_dict.get("codigo_class") or "",
    )

    # Se a primeira imagem for pequena/compatível com logo e não tivermos logo no texto
    if extracted_images:
        model.logo = extracted_images[0]
        body_images = extracted_images[1:]
    else:
        body_images = []

    # Converte as seções para a estrutura canônica
    for sec_title, sec_html in data_dict.get("secoes", []):
        sec = Section(title=sec_title, html_cache=sec_html)
        sec.blocks.append(Block(type="paragraph", text=re.sub(r'<[^>]+>', '', sec_html)))
        model.secoes.append(sec)

    # Se houver imagens restantes do PDF, adiciona em uma seção ou na última seção
    if body_images and model.secoes:
        for img_b64 in body_images:
            model.secoes[-1].blocks.append(Block(type="image", image_src=img_b64, image_caption="Figura extraída do PDF"))
            model.secoes[-1].html_cache += f'\n<figure class="report-image-box"><img src="{img_b64}" alt="Figura extraída do PDF" class="content-img"><figcaption class="image-caption">Figura extraída do PDF</figcaption></figure>'

    if data_dict.get("assinaturas"):
        model.assinaturas = [{"nome": a[0], "cargo": a[1]} for a in data_dict["assinaturas"]]

    return model
