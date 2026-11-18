"""
Parser híbrido para textos brutos e arquivos Markdown (.md) ou Texto (.txt).
Extrai metadados essenciais e seções estruturadas.
Suporta fallback automático para valores não informados, tabelas, blocos de código e fluxogramas (Mermaid / setas).
"""

import html as html_lib
import re
import datetime
from typing import Dict, Any, List, Tuple, Optional


def apply_inline_formatting(text: str) -> str:
    """Aplica código inline, links, negrito e itálico mesmo com espaços internos entre os asteriscos."""
    # Código inline: `codigo` -> <code class="inline-code">codigo</code>
    text = re.sub(r"`([^`]+?)`", r'<code class="inline-code">\1</code>', text)
    # Links markdown: [texto](url) -> <a href="url" class="doc-link">texto</a> (ignora imagens ![...])
    text = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener" class="doc-link">\1</a>', text)
    # Trata negrito com espaços internos: ** texto ** -> <strong>texto</strong>
    text = re.sub(r"\*\*\s*(.+?)\s*\*\*", r"<strong>\1</strong>", text)
    # Trata itálico com espaços ou padrão: * texto * -> <em>texto</em>
    text = re.sub(r"(?<!\*)\*\s*([^\*]+?)\s*\*(?!\*)", r"<em>\1</em>", text)
    return text


def _parse_flow_node_token(token: str, node_labels: Dict[str, str]) -> str:
    """Extrai (node_id, label) de um token Mermaid ou texto (ex: A["Rascunho"], B(Texto), [Etapa], Etapa)."""
    t = token.strip()
    if not t:
        return ""

    # Padrões com ID explícito seguido de delimitador: A["Texto"], A(Texto), A([Texto]), A{Texto}, A[[Texto]]
    m = re.match(
        r'^([A-Za-z0-9_]+)\s*(?:'
        r'\[\[\s*["\']?(.*?)["\']?\s*\]\]|'
        r'\[\(\s*["\']?(.*?)["\']?\s*\)\]|'
        r'\(\(\s*["\']?(.*?)["\']?\s*\)\)|'
        r'\(\[\s*["\']?(.*?)["\']?\s*\]\)|'
        r'\[\s*["\']?(.*?)["\']?\s*\]|'
        r'\(\s*["\']?(.*?)["\']?\s*\)|'
        r'\{\s*["\']?(.*?)["\']?\s*\}'
        r')$',
        t,
    )
    if m:
        node_id = m.group(1).strip()
        label = next((g for g in m.groups()[1:] if g is not None), node_id).strip()
        if label:
            node_labels[node_id] = label
        elif node_id not in node_labels:
            node_labels[node_id] = node_id
        return node_id

    # Sem ID separado, mas entre colchetes/parênteses/aspas: ["Rascunho"] ou [Rascunho]
    m_anon = re.match(r'^(?:\[+|\(+|\{+|["\'])\s*["\']?(.*?)["\']?\s*(?:\]+|\)+|\}+|["\'])$', t)
    if m_anon:
        label = m_anon.group(1).strip()
        node_id = re.sub(r'\W+', '_', label).strip('_') or label
        node_labels[node_id] = label
        return node_id

    # Texto simples ou ID já conhecido
    node_id = t
    if node_id not in node_labels:
        node_labels[node_id] = t
    return node_id


_ARROW_SPLIT_RE = re.compile(
    r'\s*(?:==>|-\.->|<-->|-->|---|->|=>|⟶|→|➔|➜)\s*(?:\|\s*([^|]*?)\s*\|)?\s*'
)


def _is_flow_line(line: str) -> bool:
    """Verifica se uma linha pertence a uma definição de fluxograma (Mermaid ou setas)."""
    s = line.strip()
    if not s:
        return False
    if re.match(r'^(?:flowchart|graph|stateDiagram(?:-v2)?|sequenceDiagram|direction)\b', s, re.IGNORECASE):
        return True
    if s.startswith('%%') or re.match(r'^(?:subgraph|end|classDef|class|style|click)\b', s, re.IGNORECASE):
        return True
    # Linha com seta de fluxo (ex: A --> B, A["X"] → B["Y"], Etapa 1 -> Etapa 2 -> Etapa 3)
    if re.search(r'(?:==>|-\.->|-->|->|=>|⟶|→|➔|➜)', s):
        # Evita confundir um item de lista longo de texto corrido com um fluxo, a menos que tenha sintaxe de nó ou múltiplas setas
        if re.match(r'^(?:\*|-|\d+[\.\)])\s+', s):
            return False
        arrow_count = len(re.findall(r'(?:==>|-\.->|-->|->|=>|⟶|→|➔|➜)', s))
        has_node_syntax = bool(re.search(r'[A-Za-z0-9_]+\s*[\[\(\{].+?[\]\)\}]|\|[^|]+\|', s))
        if has_node_syntax or arrow_count >= 2 or len(s) < 120:
            return True
    return False


def flowchart_to_html(flow_text: str) -> str:
    """
    Converte um bloco de fluxograma (Mermaid ou setas de texto) em um componente visual
    institucional estruturado em etapas, compatível com HTML/PDF (A4) e exportação DOCX.
    """
    node_labels: Dict[str, str] = {}
    edges: List[Tuple[str, str, str]] = []
    ordered_nodes: List[str] = []

    def register_node(nid: str):
        if nid and nid not in ordered_nodes:
            ordered_nodes.append(nid)

    for raw_line in flow_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("```") or line.startswith("%%"):
            continue
        if re.match(r'^(?:flowchart|graph|stateDiagram(?:-v2)?|sequenceDiagram|direction|subgraph|end|classDef|class|style|click)\b', line, re.IGNORECASE):
            continue

        # Normaliza sintaxe "-- Texto -->" para "-->|Texto|"
        line = re.sub(r'--\s+([^->|]+?)\s+-->', r'-->|\1|', line)
        line = re.sub(r'==\s+([^=>|]+?)\s+==>', r'==>|\1|', line)

        if _ARROW_SPLIT_RE.search(line):
            parts = _ARROW_SPLIT_RE.split(line)
            # parts = [node0, label0, node1, label1, node2, ...]
            for idx in range(0, len(parts) - 2, 2):
                left_tok = parts[idx]
                edge_lbl = (parts[idx + 1] or "").strip()
                right_tok = parts[idx + 2]
                src_id = _parse_flow_node_token(left_tok, node_labels)
                dst_id = _parse_flow_node_token(right_tok, node_labels)
                if src_id and dst_id:
                    register_node(src_id)
                    register_node(dst_id)
                    edges.append((src_id, dst_id, edge_lbl))
        else:
            # Definição isolada de nó (ex: A["Rascunho"])
            nid = _parse_flow_node_token(line, node_labels)
            if nid:
                register_node(nid)

    if not ordered_nodes:
        return f'<pre class="code-block"><code>{html_lib.escape(flow_text.strip())}</code></pre>'

    if not edges:
        # Apenas nós listados sem arestas
        steps_html = []
        for idx, nid in enumerate(ordered_nodes, 1):
            lbl = apply_inline_formatting(html_lib.escape(node_labels.get(nid, nid)))
            steps_html.append(
                f'<div class="flow-step-card">'
                f'  <div class="flow-step-top"><span class="flow-step-num">{idx}</span><span class="flow-step-title">{lbl}</span></div>'
                f'</div>'
            )
        return (
            '<div class="flow-diagram">'
            '  <div class="flow-diagram-header">⇄ Fluxo Operacional</div>'
            f'  <div class="flow-track">{"".join(steps_html)}</div>'
            '</div>'
        )

    # Constrói adjacência para encontrar o caminho principal (espinha dorsal do fluxo)
    adj: Dict[str, List[Tuple[str, str]]] = {n: [] for n in ordered_nodes}
    in_degree: Dict[str, int] = {n: 0 for n in ordered_nodes}
    for u, v, lbl in edges:
        adj.setdefault(u, []).append((v, lbl))
        in_degree[v] = in_degree.get(v, 0) + 1

    # Nó inicial preferencial: in_degree == 0 ou o primeiro nó declarado
    start_candidates = [n for n in ordered_nodes if in_degree.get(n, 0) == 0]
    start_node = start_candidates[0] if start_candidates else ordered_nodes[0]

    # Busca o caminho simples mais longo a partir de start_node (representa a sequência principal do processo)
    best_path: List[str] = []

    def dfs(curr: str, visited: List[str]):
        nonlocal best_path
        if len(visited) > len(best_path):
            best_path = list(visited)
        for nxt, _ in adj.get(curr, []):
            if nxt not in visited:
                visited.append(nxt)
                dfs(nxt, visited)
                visited.pop()

    dfs(start_node, [start_node])

    # Se existirem outros nós desconectados que não entraram em best_path nem são desvios diretos
    spine_set = set(best_path)

    # Mapeia rótulos das arestas da espinha dorsal: (u, v) -> label
    spine_edge_labels: Dict[Tuple[str, str], str] = {}
    for i in range(len(best_path) - 1):
        u, v = best_path[i], best_path[i + 1]
        for dst, lbl in adj.get(u, []):
            if dst == v:
                spine_edge_labels[(u, v)] = lbl
                break

    # Identifica desvios / retornos / ramificações fora da espinha dorsal
    # Ex: B -->|Devolvido| A2 e A2 --> B
    branch_notes: Dict[str, List[str]] = {n: [] for n in best_path}
    used_edges = set()
    for i in range(len(best_path) - 1):
        used_edges.add((best_path[i], best_path[i + 1]))

    for u, v, lbl in edges:
        if (u, v) in used_edges:
            continue
        if u in spine_set and v not in spine_set:
            v_label = node_labels.get(v, v)
            # Verifica se v retorna para algum nó da espinha dorsal
            returns_to = [dst for dst, _ in adj.get(v, []) if dst in spine_set]
            prefix = f"{lbl}: " if lbl else ""
            if returns_to:
                ret_node = returns_to[0]
                used_edges.add((v, ret_node))
                if ret_node == u:
                    branch_notes[u].append(f"↩ {prefix}{v_label}")
                else:
                    ret_label = node_labels.get(ret_node, ret_node)
                    branch_notes[u].append(f"↩ {prefix}{v_label} → {ret_label}")
            else:
                branch_notes[u].append(f"↳ {prefix}{v_label}")
            used_edges.add((u, v))
        elif u in spine_set and v in spine_set:
            # Aresta direta entre dois nós da espinha (ex: retorno direto)
            v_label = node_labels.get(v, v)
            prefix = f"{lbl}: " if lbl else "Retorno: "
            branch_notes[u].append(f"↩ {prefix}{v_label}")
            used_edges.add((u, v))

    # Monta o HTML dos cards da espinha dorsal
    track_items: List[str] = []
    for idx, nid in enumerate(best_path):
        step_num = idx + 1
        title_html = apply_inline_formatting(html_lib.escape(node_labels.get(nid, nid)))

        notes_html = ""
        if branch_notes.get(nid):
            pills = "".join(
                f'<div class="flow-step-branch">{apply_inline_formatting(html_lib.escape(note))}</div>'
                for note in branch_notes[nid]
            )
            notes_html = f'<div class="flow-step-branches">{pills}</div>'

        card_html = (
            f'<div class="flow-step-card" data-step="{step_num}">'
            f'  <div class="flow-step-top">'
            f'    <span class="flow-step-num">{step_num}</span>'
            f'    <span class="flow-step-title">{title_html}</span>'
            f'  </div>'
            f'  {notes_html}'
            f'</div>'
        )
        track_items.append(card_html)

        # Conector para o próximo passo
        if idx < len(best_path) - 1:
            nxt_id = best_path[idx + 1]
            edge_lbl = spine_edge_labels.get((nid, nxt_id), "")
            lbl_badge = (
                f'<span class="flow-edge-label">{ html_lib.escape(edge_lbl) }</span>'
                if edge_lbl
                else ""
            )
            connector_html = (
                f'<div class="flow-connector">'
                f'  {lbl_badge}'
                f'  <span class="flow-arrow">→</span>'
                f'</div>'
            )
            track_items.append(connector_html)

    return (
        '<div class="flow-diagram">\n'
        '  <div class="flow-diagram-header">⇄ Fluxo Operacional</div>\n'
        f'  <div class="flow-track">\n    ' + "\n    ".join(track_items) + '\n  </div>\n'
        '</div>'
    )


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


def _format_non_fenced_segment(text: str) -> str:
    """Processa tabelas Markdown e delega o restante para process_paragraphs_and_lists."""
    text = text.strip()
    if not text:
        return ""

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


def format_text_block(text: str) -> str:
    """Formata texto com suporte a parágrafos, listas, tabelas, blocos de código e fluxogramas."""
    text = text.strip()
    if not text:
        return '<p class="meta-value nao-informado">[NÃO INFORMADO]</p>'

    # 1. Extrai blocos cercados por ``` (ex: ```mermaid ... ``` ou ``` ... ```)
    fence_pattern = re.compile(r"^[ \t]*```([a-zA-Z0-9_-]*)[ \t]*\n(.*?)^[ \t]*```[ \t]*$", re.MULTILINE | re.DOTALL)

    parts = []
    last_idx = 0
    for match in fence_pattern.finditer(text):
        start, end = match.span()
        before = text[last_idx:start].strip()
        if before:
            parts.append(_format_non_fenced_segment(before))

        lang = (match.group(1) or "").strip().lower()
        body = match.group(2)

        if lang in ("mermaid", "flowchart", "graph", "fluxo") or any(_is_flow_line(l) for l in body.splitlines()):
            parts.append(flowchart_to_html(body))
        else:
            escaped_code = html_lib.escape(body.strip())
            parts.append(f'<pre class="code-block"><code>{escaped_code}</code></pre>')

        last_idx = end

    remaining = text[last_idx:].strip()
    if remaining:
        parts.append(_format_non_fenced_segment(remaining))

    result = "\n".join(p for p in parts if p)
    return result if result else '<p class="meta-value nao-informado">[NÃO INFORMADO]</p>'


def process_paragraphs_and_lists(text: str) -> str:
    """Transforma linhas soltas e itens em listas (<ul> / <ol>), subtítulos, fluxos e parágrafos."""
    lines = text.split("\n")
    output = []
    list_tag: Optional[str] = None  # 'ul' ou 'ol'
    flow_buffer: List[str] = []

    def close_list():
        nonlocal list_tag
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = None

    def flush_flow():
        nonlocal flow_buffer
        if flow_buffer:
            # Só renderiza como fluxograma se tiver ao menos uma linha com seta
            if any(re.search(r'(?:==>|-\.->|-->|->|=>|⟶|→|➔|➜)', l) for l in flow_buffer):
                output.append(flowchart_to_html("\n".join(flow_buffer)))
            else:
                for fl in flow_buffer:
                    if not re.match(r'^(?:flowchart|graph|stateDiagram)\b', fl.strip(), re.IGNORECASE):
                        output.append(f"<p>{apply_inline_formatting(fl.strip())}</p>")
            flow_buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            close_list()
            flush_flow()
            continue

        # Ignora linhas divisórias horizontais isoladas (---, ***, ___) ou cercas ``` soltas
        if re.match(r"^(?:[-*_]{3,}|```.*)$", stripped):
            close_list()
            flush_flow()
            continue

        # Detecta linhas de fluxograma (mesmo sem cerca ```mermaid)
        if _is_flow_line(stripped):
            close_list()
            flow_buffer.append(stripped)
            continue
        else:
            flush_flow()

        # Item de lista não ordenada (- ou *)
        ul_match = re.match(r"^(\*|-)\s+(.+)$", stripped)
        # Item de lista ordenada (1. ou 1))
        ol_match = re.match(r"^(\d+[\.\)])\s+(.+)$", stripped)

        if ul_match:
            if list_tag != "ul":
                close_list()
                output.append("<ul>")
                list_tag = "ul"
            item_text = apply_inline_formatting(ul_match.group(2))
            output.append(f"  <li>{item_text}</li>")
        elif ol_match:
            if list_tag != "ol":
                close_list()
                output.append("<ol>")
                list_tag = "ol"
            item_text = apply_inline_formatting(ol_match.group(2))
            output.append(f"  <li>{item_text}</li>")
        else:
            close_list()

            # Imagem em Markdown: ![Legenda](URL_ou_Base64)
            img_match = re.match(r"^!\[(.*?)\]\((.*?)\)$", stripped)
            if img_match:
                alt_text = img_match.group(1).strip()
                src_val = img_match.group(2).strip()
                caption_html = f'<figcaption class="image-caption">{alt_text}</figcaption>' if alt_text else ''
                output.append(f'<figure class="report-image-box"><img src="{src_val}" alt="{alt_text}" class="content-img">{caption_html}</figure>')
            # Subtítulos / Títulos internos Markdown (###, ####, etc)
            elif header_match := re.match(r"^(#{1,6})\s+(.+)$", stripped):
                h_text = apply_inline_formatting(header_match.group(2).strip())
                output.append(f'<h4 class="sub-section-title">{h_text}</h4>')
            else:
                line_html = apply_inline_formatting(stripped)
                output.append(f"<p>{line_html}</p>")

    close_list()
    flush_flow()

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
        "secoes": [],  # lista de tuplas (titulo_secao, conteudo_html)
        "assinaturas": []
    }

    # Garante que quebras de linha escapadas (\n) sejam tratadas como quebra real
    if "\\n" in raw_content and "\n" not in raw_content:
        raw_content = raw_content.replace("\\n", "\n")

    lines = raw_content.splitlines()

    # 1. Varredura por metadados no início ou em chaves explícitas (suporta **Campo:** e variações)
    meta_key_patterns = {
        "orgao": re.compile(r"^(?:\*\*)?(?:[óo]rg[ãa]o(?:\s*respons[áa]vel)?|entidade|institui[çc][ãa]o|secretaria)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "autor": re.compile(r"^(?:\*\*)?(?:autor|respons[áa]vel(?:\s*pela\s*elabora[çc][ãa]o(?:\s*da\s*ata)?)?|elaborado\s*por|relator)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "data": re.compile(r"^(?:\*\*)?(?:data|emiss[ãa]o)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "codigo": re.compile(r"^(?:\*\*)?(?:c[óo]digo|n[úu]mero|identificador|id|processo)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "tipo_documento": re.compile(r"^(?:\*\*)?(?:tipo(?:\s*de\s*documento)?)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
        "logo": re.compile(r"^(?:\*\*)?(?:logo|bras[ãa]o|logotipo|imagem_logo)(?:\*\*)?\s*:\s*(.+)$", re.IGNORECASE),
    }

    remaining_lines = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            remaining_lines.append(line)
            continue

        if in_fence:
            remaining_lines.append(line)
            continue

        if not stripped:
            if remaining_lines:
                remaining_lines.append(line)
            continue

        # Ignora linhas divisórias horizontais (---)
        if re.match(r"^[-*_]{3,}$", stripped):
            continue

        matched_meta = False

        # Verifica se é uma chave de metadado (apenas fora de listas/tabelas)
        if not stripped.startswith(("-", "*", "|")):
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
        if stripped.startswith("# ") and not stripped.startswith("## "):
            header_text = stripped[2:].strip()
            is_gov_entity = re.search(r"(?:prefeitura|c[âa]mara|secretaria|governo|tribunal|minist[ée]rio)", header_text, re.IGNORECASE)

            if re.search(r"^ata\s*(?:de\s*audi[êe]ncia\s*p[úu]blica)?$", header_text, re.IGNORECASE):
                data["tipo_documento"] = "Ata de Audiência Pública"
                if not data["titulo"]:
                    data["titulo"] = "ATA DE AUDIÊNCIA PÚBLICA"
                continue

            if not data["orgao"] and is_gov_entity:
                data["orgao"] = header_text
                continue
            elif not data["titulo"]:
                data["titulo"] = header_text
                continue
            elif not data["subtitulo"]:
                data["subtitulo"] = header_text
                continue

        # Detecta subtítulo caso seja um ## inicial antes das seções ou linha com **Subtítulo:**
        if stripped.lower().startswith("subtítulo:") or stripped.lower().startswith("subtitulo:"):
            if not data["subtitulo"]:
                data["subtitulo"] = stripped.split(":", 1)[1].strip()
                continue
        elif not data["subtitulo"] and data["titulo"] and not data["secoes"] and not remaining_lines and (stripped.startswith("**") and stripped.endswith("**") and len(stripped) < 120 and ":" not in stripped):
            data["subtitulo"] = stripped.strip("*").strip()
            continue

        remaining_lines.append(line)

    # Verifica se o documento possui cabeçalhos de nível 1 ou 2 (##) para definir se ### deve ser subseção interna
    has_h2_sections = any(re.match(r"^#{1,2}(?!#)\s+.+$", l.strip()) for l in remaining_lines)
    section_heading_regex = re.compile(r"^#{1,2}(?!#)\s+(.+)$") if has_h2_sections else re.compile(r"^#{1,6}\s+(.+)$")

    # 2. Processa o corpo do relatório (seções)
    current_section_title = None
    current_section_lines = []
    in_fence = False

    for line in remaining_lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            current_section_lines.append(line)
            continue

        if in_fence:
            current_section_lines.append(line)
            continue

        if not stripped and not current_section_lines:
            continue

        # Detecta início de seção (## Título ou Nome da Seção em CAPS com dois pontos)
        section_match = section_heading_regex.match(stripped)
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

    # Fallbacks inteligentes para campos ausentes
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
