#!/bin/bash
set -e

REPO="jurrienk/one2track"
BETA_DIR="/config/custom_components/one2track_beta"

# Fetch available releases and branches
echo "Fetching available versions from GitHub..."
echo ""

echo "=== Releases ==="
RELEASES=$(curl -s "https://api.github.com/repos/${REPO}/releases" | grep -oP '"tag_name":\s*"\K[^"]+')
if [ -z "$RELEASES" ]; then
    echo "  (none found)"
else
    echo "$RELEASES" | nl -ba
fi

echo ""
echo "=== Branches ==="
BRANCHES=$(curl -s "https://api.github.com/repos/${REPO}/branches" | grep -oP '"name":\s*"\K[^"]+')
if [ -z "$BRANCHES" ]; then
    echo "  (none found)"
else
    echo "$BRANCHES" | nl -ba
fi

echo ""
read -p "Enter a release tag (e.g. v2.0.0) or branch name (e.g. main): " VERSION

if [ -z "$VERSION" ]; then
    echo "No version specified, aborting."
    exit 1
fi

# Determine download URL (tags use /refs/tags/, branches use /refs/heads/)
TAG_URL="https://github.com/${REPO}/archive/refs/tags/${VERSION}.zip"
BRANCH_URL="https://github.com/${REPO}/archive/refs/heads/${VERSION}.zip"

echo ""
echo "Trying to download ${VERSION}..."

cd /tmp
rm -f one2track-beta.zip
rm -rf one2track-beta-extract

if curl -fsSL -o one2track-beta.zip "$TAG_URL" 2>/dev/null; then
    echo "Downloaded release tag: ${VERSION}"
elif curl -fsSL -o one2track-beta.zip "$BRANCH_URL" 2>/dev/null; then
    echo "Downloaded branch: ${VERSION}"
else
    echo "ERROR: Could not download '${VERSION}' as a tag or branch."
    exit 1
fi

# Extract
mkdir -p one2track-beta-extract
unzip -qo one2track-beta.zip -d one2track-beta-extract

# Find the extracted folder (name varies by tag/branch)
EXTRACTED=$(find one2track-beta-extract -maxdepth 1 -mindepth 1 -type d | head -1)
if [ -z "$EXTRACTED" ] || [ ! -d "$EXTRACTED/custom_components/one2track" ]; then
    echo "ERROR: Unexpected archive structure."
    exit 1
fi

# Remove old beta if present
if [ -d "$BETA_DIR" ]; then
    echo "Removing previous beta installation..."
    rm -rf "$BETA_DIR"
fi

# Copy files
mkdir -p "$BETA_DIR"
cp -r "$EXTRACTED/custom_components/one2track/"* "$BETA_DIR/"

# Rename domain to one2track_beta
echo "Patching domain to one2track_beta..."
sed -i 's/"domain": "one2track"/"domain": "one2track_beta"/g' "$BETA_DIR/manifest.json"
sed -i 's/"name": "One2Track"/"name": "One2Track Beta"/g' "$BETA_DIR/manifest.json"
sed -i 's/DOMAIN = "one2track"/DOMAIN = "one2track_beta"/g' "$BETA_DIR/common.py"
sed -i 's/integration: one2track$/integration: one2track_beta/g' "$BETA_DIR/services.yaml"

# Clean up
rm -f /tmp/one2track-beta.zip
rm -rf /tmp/one2track-beta-extract

echo ""
echo "=== Installed One2Track Beta (${VERSION}) ==="
echo "Location: ${BETA_DIR}"
echo ""
read -p "Restart Home Assistant now? [y/N]: " RESTART
if [[ "$RESTART" =~ ^[Yy]$ ]]; then
    ha core restart
    echo "Restarting..."
else
    echo "Remember to restart HA manually before using the beta."
fi
