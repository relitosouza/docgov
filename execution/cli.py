#!/usr/bin/env python3
"""
Interface CLI para o Sistema Formatador de Relatórios.
Permite importar arquivos (.txt, .md), processar em lote na pasta inputs/
ou passar texto diretamente via terminal.
Abre automaticamente no navegador para visualização e impressão PDF (Ctrl + P).
"""

import os
import sys
import argparse
import webbrowser
from parse_content import parse_document_content
from parse_docx import parse_docx_file
from parse_pdf import parse_pdf_file
from generate_report import render_report_html
from generate_docx import generate_report_docx

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "report_template.html")
INPUTS_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

def process_file(file_path: str, open_browser: bool = True) -> str:
    """Lê um arquivo específico (.txt, .md, .docx ou .pdf), processa e gera o relatório em HTML e DOCX."""
    if not os.path.exists(file_path):
        print(f"❌ Erro: Arquivo não encontrado: {file_path}")
        return ""

    print(f"📖 Lendo arquivo: {file_path}")
    if file_path.lower().endswith(".docx"):
        model = parse_docx_file(file_path)
        data = model.to_legacy_dict()
    elif file_path.lower().endswith(".pdf"):
        model = parse_pdf_file(file_path)
        data = model.to_legacy_dict()
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        data = parse_document_content(content)

    if not data.get("logo"):
        default_brasao = os.path.join(BASE_DIR, "web", "brasao.png")
        if os.path.exists(default_brasao):
            data["logo"] = default_brasao
    
    # Nome do arquivo de saída baseado no arquivo original
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    out_file = os.path.join(OUTPUTS_DIR, f"{base_name}_relatorio.html")
    out_docx = os.path.join(OUTPUTS_DIR, f"{base_name}_relatorio.docx")

    render_report_html(data, TEMPLATE_PATH, out_file)
    generate_report_docx(data, out_docx)
    print(f"✅ Relatórios gerados com sucesso!")
    print(f"📍 HTML (PDF/Web): {out_file}")
    print(f"📍 DOCX (Word):    {out_docx}")

    if open_browser:
        print("🌐 Abrindo no navegador para visualização / impressão...")
        webbrowser.open(f"file://{out_file}")

    return out_file

def process_raw_text(text: str, title: str = None, open_browser: bool = True) -> str:
    """Processa texto digitado diretamente."""
    print("✍️ Processando texto inserido...")
    data = parse_document_content(text)
    if title:
        data["titulo"] = title

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = os.path.join(OUTPUTS_DIR, f"relatorio_digitado_{timestamp}.html")

    render_report_html(data, TEMPLATE_PATH, out_file)
    print(f"✅ Relatório gerado com sucesso!")
    print(f"📍 Local do arquivo: {out_file}")

    if open_browser:
        print("🌐 Abrindo no navegador para visualização / impressão...")
        webbrowser.open(f"file://{out_file}")

    return out_file

def process_batch_inputs(open_browser: bool = False) -> None:
    """Processa todos os arquivos .txt, .md, .docx e .pdf presentes na pasta inputs/."""
    os.makedirs(INPUTS_DIR, exist_ok=True)
    files = [f for f in os.listdir(INPUTS_DIR) if f.endswith((".txt", ".md", ".docx", ".pdf"))]

    if not files:
        print(f"⚠️ Nenhum arquivo .txt, .md, .docx ou .pdf encontrado na pasta '{INPUTS_DIR}'.")
        print("💡 Dica: Coloque arquivos na pasta 'inputs/' e rode `python execution/cli.py --batch`")
        return

    print(f"📦 Encontrados {len(files)} arquivo(s) para processamento em lote...")
    for idx, f in enumerate(files, 1):
        full_path = os.path.join(INPUTS_DIR, f)
        # Abre no navegador apenas o último se solicitado
        should_open = open_browser and (idx == len(files))
        process_file(full_path, open_browser=should_open)

def main():
    parser = argparse.ArgumentParser(description="Sistema Formatador de Relatórios Institucionais")
    parser.add_argument("--file", "-f", help="Caminho do arquivo (.txt, .md, .docx ou .pdf) para importar")
    parser.add_argument("--text", "-t", help="Texto direto a ser convertido em relatório")
    parser.add_argument("--title", help="Título manual (opcional ao usar --text)")
    parser.add_argument("--author", help="Nome do responsável que elaborou o relatório")
    parser.add_argument("--orgao", help="Nome da Secretaria ou Órgão responsável")
    parser.add_argument("--batch", "-b", action="store_true", help="Processa todos os arquivos da pasta inputs/")
    parser.add_argument("--no-open", action="store_true", help="Não abre automaticamente o navegador após a geração")

    args = parser.parse_args()
    open_browser = not args.no_open

    if args.file:
        process_file(args.file, open_browser=open_browser)
    elif args.text:
        process_raw_text(args.text, title=args.title, open_browser=open_browser)
    elif args.batch:
        process_batch_inputs(open_browser=open_browser)
    else:
        # Modo interativo simples se nenhum argumento for fornecido
        print("="*60)
        print("   SISTEMA FORMATADOR DE RELATÓRIOS INSTITUCIONAIS")
        print("="*60)
        print("1. Processar arquivo (.txt ou .md)")
        print("2. Digitar/colar texto agora")
        print("3. Processar todos os arquivos da pasta inputs/")
        print("0. Sair")
        escolha = input("\nEscolha uma opção (0-3): ").strip()

        if escolha == "1":
            caminho = input("Digite o caminho do arquivo: ").strip()
            process_file(caminho, open_browser=open_browser)
        elif escolha == "2":
            print("\nDigite ou cole seu texto (pressione Ctrl+D ou digite FIM em linha separada para terminar):")
            linhas = []
            try:
                while True:
                    linha = input()
                    if linha.strip() == "FIM":
                        break
                    linhas.append(linha)
            except EOFError:
                pass
            texto_completo = "\n".join(linhas)
            if texto_completo.strip():
                process_raw_text(texto_completo, open_browser=open_browser)
            else:
                print("Texto vazio. Operação cancelada.")
        elif escolha == "3":
            process_batch_inputs(open_browser=open_browser)
        else:
            print("Encerrando.")

if __name__ == "__main__":
    main()
