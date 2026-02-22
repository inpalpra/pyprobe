#!/usr/bin/env bash
# release.sh — Tag and push a new PyProbe release to GitHub.
#
# Usage:
#   ./release.sh              # auto-bumps patch (v0.1.0 → v0.1.1)
#   ./release.sh v0.2.0       # explicit version
#   ./release.sh --dry-run    # show what would happen without doing it

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

DRY_RUN=false

# ── Parse args ──
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
  esac
done

# ── Ensure we're on a clean working tree ──
if [[ -n "$(git status --porcelain)" ]]; then
  echo -e "${RED}✗ Working tree is dirty. Commit or stash changes first.${RESET}"
  git status --short
  exit 1
fi

# ── Get latest version from pyproject.toml ──
CURRENT_VERSION=$(grep -E '^version = ' pyproject.toml | cut -d'"' -f2 | tr -d ' ')
echo -e "${CYAN}Current version in pyproject.toml:${RESET} ${BOLD}${CURRENT_VERSION}${RESET}"

# ── Determine new version ──
auto_bump() {
  local version="${1#v}"  # strip leading v
  local major minor patch
  IFS='.' read -r major minor patch <<< "$version"
  # Strip any pre-release suffix (e.g. -rc1)
  patch="${patch%%-*}"
  patch=$((patch + 1))
  echo "v${major}.${minor}.${patch}"
}

# Filter out --dry-run to find the version arg
NEW_TAG=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) ;;
    *) NEW_TAG="$arg" ;;
  esac
done

if [[ -z "$NEW_TAG" ]]; then
  NEW_TAG=$(auto_bump "$CURRENT_VERSION")
fi

# Validate format
if [[ ! "$NEW_TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-.*)?$ ]]; then
  echo -e "${RED}✗ Invalid version format: ${NEW_TAG}${RESET}"
  echo "  Expected: vMAJOR.MINOR.PATCH (e.g. v0.2.0, v1.0.0-rc1)"
  exit 1
fi

PURE_VERSION="${NEW_TAG#v}"

echo -e "${GREEN}New tag:${RESET}    ${BOLD}${NEW_TAG}${RESET}"
echo ""

# ── Show commits since last release ──
echo -e "${CYAN}Commits since v${CURRENT_VERSION}:${RESET}"
git log --oneline "v${CURRENT_VERSION}..HEAD" 2>/dev/null || git log --oneline -10
echo ""

# ── Dry run exit ──
if $DRY_RUN; then
  echo -e "${YELLOW}(dry run) Would create tag ${NEW_TAG} and push to origin.${RESET}"
  exit 0
fi

# ── Confirm ──
echo -e "${BOLD}This will:${RESET}"
echo "  1. Bump version to ${PURE_VERSION} in pyproject.toml"
echo "  2. Create git commit for the bump"
echo "  3. Create git tag ${NEW_TAG}"
echo "  4. Push to origin (triggers GitHub Actions release build)"
echo ""
read -rp "$(echo -e "${YELLOW}Proceed? [y/N]:${RESET} ")" confirm
if [[ "$confirm" != [yY] ]]; then
  echo "Aborted."
  exit 0
fi

# ── Bump Version in pyproject.toml ──
# Works on both BSD (macOS) and GNU sed
sed -i.bak -e "s/^version = \".*\"/version = \"${PURE_VERSION}\"/" pyproject.toml
rm pyproject.toml.bak

git add pyproject.toml
git commit -m "Bump version to ${PURE_VERSION}"
echo -e "${GREEN}✓ Bumped version in pyproject.toml${RESET}"

# ── Tag and push ──
git tag -a "$NEW_TAG" -m "Release $NEW_TAG"
echo -e "${GREEN}✓ Created tag ${NEW_TAG}${RESET}"

git push origin "$NEW_TAG"
echo -e "${GREEN}✓ Pushed tag to origin${RESET}"

echo ""
echo -e "${GREEN}${BOLD}Release triggered!${RESET}"
echo -e "  Watch progress: ${CYAN}https://github.com/inpalpra/pyprobe/actions${RESET}"
echo -e "  Release page:   ${CYAN}https://github.com/inpalpra/pyprobe/releases/tag/${NEW_TAG}${RESET}"
