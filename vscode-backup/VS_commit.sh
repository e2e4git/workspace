#!/bin/bash
# Сохраняет изменения в Git
cd /workspace
git add vscode-backup/
git commit -m "Бэкап VS Code: $(date +%Y-%m-%d_%H-%M)"
echo "✅ Коммит создан."
