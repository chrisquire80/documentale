#!/bin/bash
# Install git hooks

echo "📦 Installing git hooks..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

HOOKS_DIR=".git/hooks"
HOOKS_SRC="."

if [ ! -d "$HOOKS_DIR" ]; then
  echo -e "${RED}Error: .git/hooks directory not found${NC}"
  exit 1
fi

# Install pre-push hook
if [ -f "$HOOKS_SRC/.git/hooks/pre-push" ]; then
  cp "$HOOKS_SRC/.git/hooks/pre-push" "$HOOKS_DIR/pre-push"
  chmod +x "$HOOKS_DIR/pre-push"
  echo -e "${GREEN}✅ Pre-push hook installed${NC}"
else
  echo -e "${YELLOW}⚠️  Pre-push hook source not found${NC}"
fi

# Install pre-commit hook (from pre-commit framework)
if command -v pre-commit &> /dev/null; then
  pre-commit install
  echo -e "${GREEN}✅ Pre-commit hooks installed${NC}"
else
  echo -e "${YELLOW}⚠️  pre-commit not installed. Install with: pip install pre-commit${NC}"
fi

# Make hooks executable
find "$HOOKS_DIR" -maxdepth 1 -type f -exec chmod +x {} \;

echo ""
echo -e "${GREEN}✅ All hooks installed successfully!${NC}"
echo ""
echo "Installed hooks:"
echo "  - pre-commit: Code formatting and linting"
echo "  - pre-push: Tests and validation before push"
echo ""
echo "To bypass hooks (not recommended):"
echo "  git commit --no-verify"
echo "  git push --no-verify"
