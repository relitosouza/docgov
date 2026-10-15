#!/usr/bin/env python3
"""
Servidor Web integrado para o Sistema Formatador de Relatórios.
Fornece API REST e serve a interface Web moderna.
"""

import os
import sys
import json
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(BASE_DIR, "execution"))

from parse_content import parse_document_content
from parse_docx import parse_docx_file
from parse_pdf import parse_pdf_file
from document_model import DocumentModel
from generate_report import render_report_html
from generate_docx import generate_report_docx

WEB_DIR = os.path.join(BASE_DIR, "web")
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "report_template.html")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
INPUTS_DIR = os.path.join(BASE_DIR, "inputs")

def cleanup_old_outputs(directory: str, max_age_hours: int = 24):
    """Remove arquivos gerados mais antigos que max_age_hours para manter o disco enxuto."""
    if not os.path.exists(directory):
        return
    import time
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    try:
        for fname in os.listdir(directory):
            if fname.startswith("."):
                continue
            fpath = os.path.join(directory, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                os.remove(fpath)
    except Exception as err:
        print(f"⚠️ Erro ao limpar outputs antigos: {err}")

PORT = 5050

class ReportRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/format":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            
            try:
                payload = json.loads(post_data)
                raw_text = payload.get("text", "")
                title_override = payload.get("title", "").strip() or None
                subtitle_override = payload.get("subtitle", "").strip() or None
                author_override = payload.get("author", "").strip() or None
                orgao_override = payload.get("orgao", "").strip() or None
                logo_override = payload.get("logo", "").strip() or None

                # Parser do texto/markdown
                data = parse_document_content(raw_text)
                if title_override:
                    data["titulo"] = title_override
                if subtitle_override is not None:
                    data["subtitulo"] = subtitle_override
                if author_override:
                    data["autor"] = author_override
                    data["autor_val"] = author_override
                    data["autor_class"] = ""
                if orgao_override:
                    data["orgao"] = orgao_override
                    data["orgao_val"] = orgao_override
                    data["orgao_class"] = ""
                if logo_override:
                    data["logo"] = logo_override
                elif not data.get("logo"):
                    default_brasao_path = os.path.join(WEB_DIR, "brasao.png")
                    if os.path.exists(default_brasao_path):
                        data["logo"] = default_brasao_path
                
                # Flag de assinatura do responsável (Sim / Não)
                data["include_signature"] = payload.get("include_signature", True)
                
                # Orientação da página (portrait ou landscape)
                data["orientation"] = payload.get("orientation", "portrait")

                # Exibir quadro de identificação/metadados no cabeçalho
                data["include_meta_box"] = payload.get("include_meta_box", True)

                # Controle de visibilidade do subtítulo
                if not payload.get("include_subtitle", True):
                    data["subtitulo"] = ""

                # Controle de seções sem título: se falso, remove qualquer "Descrição Geral"
                show_desc = payload.get("show_descricao_geral", False)
                clean_secoes = []
                for sec_t, sec_h in data.get("secoes", []):
                    if not show_desc and sec_t in ("Descrição Geral", "Conteúdo Principal", ""):
                        clean_secoes.append(("", sec_h))
                    elif show_desc and not sec_t:
                        clean_secoes.append(("Descrição Geral", sec_h))
                    else:
                        clean_secoes.append((sec_t, sec_h))
                data["secoes"] = clean_secoes

                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_html = f"relatorio_web_{timestamp}.html"
                filename_docx = f"relatorio_web_{timestamp}.docx"
                out_path_html = os.path.join(OUTPUTS_DIR, filename_html)
                out_path_docx = os.path.join(OUTPUTS_DIR, filename_docx)

                # Gera tanto a versão HTML para visualização web / PDF quanto o DOCX para Word
                render_report_html(data, TEMPLATE_PATH, out_path_html)
                generate_report_docx(data, out_path_docx)

                with open(out_path_html, "r", encoding="utf-8") as f:
                    html_content = f.read()

                response = {
                    "success": True,
                    "filename": filename_html,
                    "filename_docx": filename_docx,
                    "html": html_content,
                    "data": {
                        "titulo": data.get("titulo"),
                        "subtitulo": data.get("subtitulo"),
                        "tipo_documento": data.get("tipo_documento"),
                        "orgao": data.get("orgao_val"),
                        "autor": data.get("autor_val"),
                        "data": data.get("data_val"),
                        "codigo": data.get("codigo_val"),
                        "total_secoes": len(data.get("secoes", []))
                    }
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        elif self.path == "/api/parse-docx":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                import base64
                payload = json.loads(post_data)
                b64_content = payload.get("file_base64", "")
                if "," in b64_content:
                    b64_content = b64_content.split(",", 1)[1]
                
                raw_bytes = base64.b64decode(b64_content)
                temp_docx_path = os.path.join(INPUTS_DIR, f"temp_upload_{os.getpid()}.docx")
                with open(temp_docx_path, "wb") as f:
                    f.write(raw_bytes)

                model = parse_docx_file(temp_docx_path)
                try:
                    os.remove(temp_docx_path)
                except Exception:
                    pass

                # Converte seções para texto em formato Markdown para preenchimento intuitivo no editor
                md_blocks = []
                for sec in model.secoes:
                    if sec.title:
                        md_blocks.append(f"\n## {sec.title}\n")
                    for blk in sec.blocks:
                        if blk.type == "paragraph":
                            md_blocks.append(blk.text)
                        elif blk.type == "list_item":
                            md_blocks.append(f"* {blk.text}")
                        elif blk.type == "image":
                            caption = blk.image_caption or "Imagem do Relatório"
                            md_blocks.append(f"\n![{caption}]({blk.image_src})\n")
                        elif blk.type == "table":
                            tbl_lines = []
                            if blk.table_headers:
                                tbl_lines.append("| " + " | ".join(blk.table_headers) + " |")
                                tbl_lines.append("| " + " | ".join(["---"] * len(blk.table_headers)) + " |")
                            for row in blk.table_rows:
                                tbl_lines.append("| " + " | ".join(row) + " |")
                            md_blocks.append("\n" + "\n".join(tbl_lines) + "\n")

                generated_md = "\n\n".join(md_blocks).strip()

                resp_data = {
                    "success": True,
                    "title": model.titulo if model.titulo != "Relatório Institucional" else "",
                    "subtitle": model.subtitulo,
                    "orgao": model.orgao_val if model.orgao_val != "[NÃO INFORMADO]" else "",
                    "autor": model.autor_val if model.autor_val != "[NÃO INFORMADO]" else "",
                    "data": model.data_val,
                    "codigo": model.codigo_val,
                    "logo": model.logo or None,
                    "markdown": generated_md
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
                return
        elif self.path == "/api/parse-pdf":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                import base64
                payload = json.loads(post_data)
                b64_content = payload.get("file_base64", "")
                if "," in b64_content:
                    b64_content = b64_content.split(",", 1)[1]
                
                raw_bytes = base64.b64decode(b64_content)
                temp_pdf_path = os.path.join(INPUTS_DIR, f"temp_upload_{os.getpid()}.pdf")
                with open(temp_pdf_path, "wb") as f:
                    f.write(raw_bytes)

                model = parse_pdf_file(temp_pdf_path)
                try:
                    os.remove(temp_pdf_path)
                except Exception:
                    pass

                md_blocks = []
                for sec in model.secoes:
                    if sec.title:
                        md_blocks.append(f"\n## {sec.title}\n")
                    for blk in sec.blocks:
                        if blk.type == "paragraph":
                            md_blocks.append(blk.text)
                        elif blk.type == "list_item":
                            md_blocks.append(f"* {blk.text}")
                        elif blk.type == "image":
                            caption = blk.image_caption or "Figura do Relatório"
                            md_blocks.append(f"\n![{caption}]({blk.image_src})\n")
                        elif blk.type == "table":
                            tbl_lines = []
                            if blk.table_headers:
                                tbl_lines.append("| " + " | ".join(blk.table_headers) + " |")
                                tbl_lines.append("| " + " | ".join(["---"] * len(blk.table_headers)) + " |")
                            for row in blk.table_rows:
                                tbl_lines.append("| " + " | ".join(row) + " |")
                            md_blocks.append("\n" + "\n".join(tbl_lines) + "\n")

                generated_md = "\n\n".join(md_blocks).strip()

                resp_data = {
                    "success": True,
                    "title": model.titulo if model.titulo != "Relatório Institucional" else "",
                    "subtitle": model.subtitulo,
                    "orgao": model.orgao_val if model.orgao_val != "[NÃO INFORMADO]" else "",
                    "autor": model.autor_val if model.autor_val != "[NÃO INFORMADO]" else "",
                    "data": model.data_val,
                    "codigo": model.codigo_val,
                    "logo": model.logo or None,
                    "markdown": generated_md
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self.send_error(404, "Endpoint não encontrado")

    def do_GET(self):
        # Permite acessar relatórios gerados via /outputs/<filename>
        if self.path.startswith("/outputs/"):
            filename = os.path.basename(urllib.parse.unquote(self.path))
            filepath = os.path.join(OUTPUTS_DIR, filename)
            if os.path.exists(filepath):
                self.send_response(200)
                if filename.endswith(".docx"):
                    self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                else:
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Relatório não encontrado")
                return

        super().do_GET()

def run_server():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(INPUTS_DIR, exist_ok=True)
    cleanup_old_outputs(OUTPUTS_DIR, max_age_hours=24)

    # Permite reutilizar a porta imediatamente sem esperar o TIME_WAIT do SO
    HTTPServer.allow_reuse_address = True
    server_address = ("", PORT)
    try:
        httpd = HTTPServer(server_address, ReportRequestHandler)
    except OSError as e:
        if e.errno == 98: # Address already in use
            print(f"⚠️ A porta {PORT} já estava ocupada por uma instância anterior. Liberando...")
            os.system(f"fuser -k {PORT}/tcp >/dev/null 2>&1 || true")
            import time
            time.sleep(1)
            httpd = HTTPServer(server_address, ReportRequestHandler)
        else:
            raise e

    import socket
    def get_lan_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    lan_ip = get_lan_ip()
    local_url = f"http://localhost:{PORT}"
    network_url = f"http://{lan_ip}:{PORT}"

    print(f"\n=======================================================")
    print(f"🚀 Interface Web do Sistema de Relatórios iniciada!")
    print(f"💻 Acesso Local:  {local_url}")
    print(f"🌐 Acesso na Rede: {network_url}")
    print(f"=======================================================\n")
    webbrowser.open(local_url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor encerrado.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
