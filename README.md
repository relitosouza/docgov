# DocGov — Sistema Institucional de Relatórios

Sistema moderno e completo para formatação, padronização e exportação de relatórios institucionais nos padrões executivos da administração pública.

---

## 🚀 Funcionalidades

- **Visualização A4 Paginada em Tempo Real:** Pré-visualização com divisão de páginas, cabeçalho e rodapé automáticos.
- **Importação Multiformato:**
  - **Word (`.docx`):** Análise e extração automática de metadados, títulos, tabelas e imagens embutidas.
  - **PDF (`.pdf`):** Extração de texto e figuras via utilitários do sistema.
  - **Markdown (`.md`) e Texto (`.txt`):** Entrada estruturada ou anotações livres.
- **Exportação:**
  - **DOCX (.docx):** Documentos Microsoft Word formatados.
  - **PDF / Impressão:** Geração em formato A4 (`Ctrl + P`) pronto para impressão ou assinatura.
  - **HTML:** Cópia rápida do código HTML renderizado.
- **Parâmetros e Identidade:**
  - Menu retrátil com controle de título, órgão/secretaria, autor, data e brasão/logo institucional.
  - Alternância de tema escuro e claro.
  - Modo paisagem ou retrato.

---

## 🛠️ Instalação e Execução

### Pré-requisitos
- Python 3.10+
- `poppler-utils` (para processamento de PDF via `pdftotext` e `pdfimages`)

```bash
# Clone o repositório
git clone https://github.com/relitosouza/docgov.git
cd docgov

# Instale as dependências
pip install -r requirements.txt

# Inicie o servidor
./iniciar.sh
```

Acesse no navegador:
- Local: `http://localhost:5050`
- Rede: `http://<seu-ip>:5050`

---

## 🧪 Testes

Execute a suíte de testes unitários:

```bash
python3 -m unittest tests/test_report_pipeline.py
```
