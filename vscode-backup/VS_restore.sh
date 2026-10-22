#!/bin/bash
# Восстанавливает настройки VS Code
mkdir -p ~/.config/Code/User
cp /workspace/vscode-backup/User/settings.json ~/.config/Code/User/ 2>/dev/null
cp /workspace/vscode-backup/User/keybindings.json ~/.config/Code/User/ 2>/dev/null
cp -r /workspace/vscode-backup/User/snippets ~/.config/Code/User/ 2>/dev/null
if [ -f /workspace/vscode-backup/extensions.txt ]; then
    while IFS= read -r ext; do
        [ -z "$ext" ] && continue
        code --install-extension "$ext" --force
    done < /workspace/vscode-backup/extensions.txt
fi
echo "✅ Настройки восстановлены. Перезапустите VS Code."
