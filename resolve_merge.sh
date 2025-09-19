#!/bin/bash
cd "$(dirname "$0")"

echo "Resolving merge conflict in document_sorter_app..."

# Add .claude/ to gitignore if not already there
if ! grep -q "\.claude/" .gitignore; then
    echo "# Claude AI settings (contains personal paths and permissions)" >> .gitignore
    echo ".claude/" >> .gitignore
fi

# Remove .claude from git tracking
git rm -r --cached .claude/ 2>/dev/null || true

# Add gitignore changes
git add .gitignore

# Complete the merge by committing
git commit -m "Resolve merge conflict: exclude .claude directory from version control

The .claude directory contains local Claude AI settings with personal
paths and permissions that should not be committed to version control.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

echo "Merge conflict resolved successfully!"