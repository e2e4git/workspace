#!/bin/bash
# Сохраняет настройки VS Code
mkdir -p /workspace/vscode-backup/User
cp ~/.config/Code/User/settings.json /workspace/vscode-backup/User/ 2>/dev/null
cp ~/.config/Code/User/keybindings.json /workspace/vscode-backup/User/ 2>/dev/null
cp -r ~/.config/Code/User/snippets /workspace/vscode-backup/User/ 2>/dev/null
code --list-extensions > /workspace/vscode-backup/extensions.txt
echo "✅ Настройки сохранены. Теперь запустите VS_commit.sh"
