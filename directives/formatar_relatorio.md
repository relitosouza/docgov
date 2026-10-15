# Diretriz: Sistema Formatador de Relatórios

## Objetivo
Processar textos brutos e arquivos (.txt, .md) contendo anotações ou relatórios desestruturados/estruturados e convertê-los automaticamente para um relatório institucional elegante em formato HTML com estilização profissional para visualização em tela e impressão/salvamento em PDF (`Ctrl + P`).

## Arquitetura (DOE Framework)
1. **Directive**: `directives/formatar_relatorio.md` (este documento).
2. **Orchestration**: Agente Antigravity executando e validando fluxos.
3. **Execution**:
   - `execution/parse_content.py`: Parser híbrido determinístico (com fallback para LLM/regras) que extrai metadados (Título, Autor, Data, Órgão, Objetivos, Descrição, Tabelas, Conclusões).
   - `execution/generate_report.py`: Injeta os dados estruturados no template HTML e gera o arquivo em `outputs/`.
   - `execution/cli.py`: Ponto de entrada CLI amigável (suporta `--file`, `--text`, processamento em lote em `inputs/`, e `--open` para visualização automática).
4. **Templates & Estilos**:
   - `templates/report_template.html`: Layout institucional com cabeçalho, paginação CSS (`@page`), tipografia limpa, badges de metadados, suporte a tabelas e bloco de assinaturas.

## Entradas (Inputs)
- Arquivos em texto plano (`.txt`) ou Markdown (`.md`) colocados em `inputs/` ou informados via CLI `--file`.
- Texto digitado diretamente via linha de comando ou pipe/interativo `--text`.
- Variáveis de ambiente opcionais (ex: `GEMINI_API_KEY` para modo IA avançado).

## Saídas (Outputs)
- Arquivos `.html` em `outputs/` autossuficientes com CSS embutido.
- Abertura opcional e automática no navegador padrão (`--open` ativado por padrão).

## Casos Extremos Tratados
- **Campos Ausentes**: Preenchimento automático com `[NÃO INFORMADO]` discreto e estilizado.
- **Tabelas Markdown e Listas**: Conversão correta para tabelas HTML com cabeçalhos e bordas para impressão.
- **Impressão**: Regras de quebra de página (`page-break-inside: avoid;`) e ocultação de controles de impressão na impressão real.
