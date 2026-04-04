#!/bin/bash
# update-pishrink.sh
#
# Checks whether the PiShrink commit pinned in build-image.sh is still the
# latest on master.  If a newer commit is found:
#   1. Downloads the new pishrink.sh
#   2. Computes its SHA256
#   3. Updates PISHRINK_COMMIT and PISHRINK_SHA256 in build-image.sh in-place
#
# Usage:
#   ./scripts/update-pishrink.sh              # check and auto-update
#   ./scripts/update-pishrink.sh --check-only # report without modifying files
#
# Requirements: curl, sha256sum (coreutils), awk, sed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_SCRIPT="${SCRIPT_DIR}/../build-image.sh"
CHECK_ONLY=false

for arg in "$@"; do
    [[ "$arg" == "--check-only" ]] && CHECK_ONLY=true
done

info()  { echo "[update-pishrink] $*"; }
die()   { echo "[update-pishrink] ERROR: $*" >&2; exit 1; }

# ── Verify dependencies ────────────────────────────────────────────────────────
for cmd in curl sha256sum awk sed; do
    command -v "$cmd" >/dev/null 2>&1 || die "Required command not found: $cmd"
done

[[ -f "$BUILD_SCRIPT" ]] || die "build-image.sh not found at $BUILD_SCRIPT"

# ── Read the currently pinned commit from build-image.sh ──────────────────────
CURRENT_COMMIT="$(awk -F'"' '/^PISHRINK_COMMIT=/{print $2}' "$BUILD_SCRIPT")"
[[ -n "$CURRENT_COMMIT" ]] || die "Could not read PISHRINK_COMMIT from $BUILD_SCRIPT"

info "Currently pinned commit: $CURRENT_COMMIT"

# ── Fetch the latest commit SHA from GitHub API ───────────────────────────────
info "Checking GitHub for latest PiShrink commit..."
LATEST_COMMIT="$(curl -fsSL \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/Drewsif/PiShrink/commits/master" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")"

[[ -n "$LATEST_COMMIT" ]] || die "Failed to fetch latest commit from GitHub API"

info "Latest upstream commit:  $LATEST_COMMIT"

if [[ "$CURRENT_COMMIT" == "$LATEST_COMMIT" ]]; then
    info "Already up to date. No changes needed."
    exit 0
fi

info "New commit available."

if $CHECK_ONLY; then
    info "(--check-only) Skipping update. Run without --check-only to apply."
    exit 0
fi

# ── Download new pishrink.sh and compute its SHA256 ───────────────────────────
PISHRINK_URL="https://raw.githubusercontent.com/Drewsif/PiShrink/${LATEST_COMMIT}/pishrink.sh"
info "Downloading PiShrink from commit $LATEST_COMMIT..."

NEW_SHA256="$(curl -fsSL "$PISHRINK_URL" | sha256sum | awk '{print $1}')"
[[ -n "$NEW_SHA256" ]] || die "Failed to compute SHA256 for new pishrink.sh"

info "New SHA256: $NEW_SHA256"

# ── Patch build-image.sh in-place ────────────────────────────────────────────
sed -i \
    -e "s|^PISHRINK_COMMIT=.*|PISHRINK_COMMIT=\"${LATEST_COMMIT}\"|" \
    -e "s|^PISHRINK_SHA256=.*|PISHRINK_SHA256=\"${NEW_SHA256}\"|" \
    "$BUILD_SCRIPT"

info "build-image.sh updated:"
info "  PISHRINK_COMMIT = $LATEST_COMMIT"
info "  PISHRINK_SHA256 = $NEW_SHA256"
info "Review the diff and commit the change to lock in the new pin."
