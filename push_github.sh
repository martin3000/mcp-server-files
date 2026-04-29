#!/bin/bash
set -e

git add -A
git status

echo ""
read -p "Commit-Nachricht: " msg
git commit -m "$msg"
git push origin main
echo "GitHub: fertig."
