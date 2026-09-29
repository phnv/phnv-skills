#!/usr/bin/env bash
# End-to-end npm publish helper for a skills-npm package.
# Handles the common failure points so each step can be run safely in sequence.
#
# Usage: ./publish.sh [patch|minor|major]
#   Default bump type is "patch".

set -euo pipefail

BUMP="${1:-patch}"
PKG_NAME=$(node -p "require('./package.json').name")

# ── 1. Node version ─────────────────────────────────────────────────────────
REQUIRED_MAJOR=22
CURRENT_MAJOR=$(node -p "parseInt(process.versions.node.split('.')[0])")
if [ "$CURRENT_MAJOR" -lt "$REQUIRED_MAJOR" ]; then
  echo "❌ Node ${REQUIRED_MAJOR}+ is required (current: $(node -v))."
  echo "   If using nvm: source ~/.nvm/nvm.sh && nvm use ${REQUIRED_MAJOR}"
  exit 1
fi
echo "✓ Node $(node -v)"

# ── 2. Clean git tree ────────────────────────────────────────────────────────
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "❌ Working directory is not clean."
  echo "   Commit or stash your changes, then retry."
  git status --short
  exit 1
fi
echo "✓ Git working directory is clean"

# ── 3. No version collision ──────────────────────────────────────────────────
LOCAL_VERSION=$(node -p "require('./package.json').version")
REMOTE_VERSION=$(npm view "${PKG_NAME}" version 2>/dev/null || echo "none")
if [ "$LOCAL_VERSION" = "$REMOTE_VERSION" ]; then
  echo "❌ Local version (${LOCAL_VERSION}) already exists on the registry."
  echo "   The previous 'npm version' bump may not have run. This script will"
  echo "   bump the version now — if you didn't intend a ${BUMP} bump, cancel (Ctrl-C)."
  read -r -p "   Proceed with 'npm version ${BUMP}'? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

# ── 4. Bump version ──────────────────────────────────────────────────────────
echo "Bumping version (${BUMP})..."
npm version "${BUMP}"

# ── 5. Publish ───────────────────────────────────────────────────────────────
echo "Publishing to npm..."
BROWSER=true npm publish

# ── 6. Push commit + tags ────────────────────────────────────────────────────
echo "Pushing commit and tags to remote..."
git push --follow-tags

echo ""
echo "✅ Done! $(node -p "require('./package.json').name")@$(node -p "require('./package.json').version") is live."
