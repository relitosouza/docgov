#!/usr/bin/env bash
# ==============================================================================
# Script de Inicialização - Sistema Formatador de Relatórios Institucionais
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR" || exit 1

# Verifica se o Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Erro: python3 não foi encontrado. Por favor, instale o Python 3 para continuar."
    exit 1
fi

mkdir -p inputs outputs templates execution web .tmp

# Se passar o parâmetro --cli ou algum argumento de arquivo/texto, roda o CLI
if [ "$1" == "--cli" ]; then
    shift
    python3 execution/cli.py "$@"
elif [ "$#" -gt 0 ]; then
    python3 execution/cli.py "$@"
else
    # Padrão: Inicia a Interface Web Moderna e abre no navegador
    python3 execution/server.py
fi
