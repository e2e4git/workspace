#!/bin/bash
set -e
BACKUP_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_USER="$BACKUP_DIR/User"
VSCODE_USER="$HOME/.config/Code/User"

if ! command -v code &>/dev/null; then
    echo "ОШИБКА: команда 'code' не найдена."
    exit 1
fi

mkdir -p "$VSCODE_USER/snippets"

if [ -f "$SRC_USER/settings.json" ]; then
    cp "$SRC_USER/settings.json" "$VSCODE_USER/settings.json"
    echo "  settings.json восстановлен."
fi

if [ -f "$BACKUP_DIR/extensions.txt" ]; then
    echo "  Устанавливаю расширения..."
    while IFS= read -r ext; do
        [ -z "$ext" ] && continue
        code --install-extension "$ext" --force
    done < "$BACKUP_DIR/extensions.txt"
fi
echo "ГОТОВО."
