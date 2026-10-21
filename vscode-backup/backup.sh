#!/bin/bash
set -e
BACKUP_DIR="$(cd "$(dirname "$0")" && pwd)"
VSCODE_USER="$HOME/.config/Code/User"
DEST_USER="$BACKUP_DIR/User"

mkdir -p "$DEST_USER/snippets"

if [ -f "$VSCODE_USER/settings.json" ]; then
    cp "$VSCODE_USER/settings.json" "$DEST_USER/settings.json"
    echo "  settings.json сохранён."
fi

if [ -f "$VSCODE_USER/keybindings.json" ]; then
    cp "$VSCODE_USER/keybindings.json" "$DEST_USER/keybindings.json"
    echo "  keybindings.json сохранён."
fi

if [ -d "$VSCODE_USER/snippets" ] && [ -n "$(ls -A "$VSCODE_USER/snippets" 2>/dev/null)" ]; then
    cp -r "$VSCODE_USER/snippets/"* "$DEST_USER/snippets/" 2>/dev/null || true
    echo "  Сниппеты сохранены."
fi

code --list-extensions > "$BACKUP_DIR/extensions.txt"
echo "  extensions.txt сохранён ($(grep -c . "$BACKUP_DIR/extensions.txt") расширений)."
echo "ГОТОВО."
