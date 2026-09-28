#!/bin/bash
# ============================================================================
# Vajra OS — Desktop ISO builder (live-build in a Debian trixie container)
#
#   scripts/build-desktop-iso.sh [output-dir]
#
# live-build must run on a Debian host with root privileges, so this script
# runs the entire build inside a privileged debian:trixie Docker container
# with the repo's live-build/ config mounted at /lb. Produces:
#
#   <output-dir>/vajra-os-1.0-desktop-amd64.iso
#
# The desktop ISO installs the Vajra tools from the project's published,
# GPG-signed APT repository (https://ksraj20009.github.io/vajra-os/apt-repo).
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/vajra-desktop-output}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

IMAGE="${VAJRA_BUILD_IMAGE:-debian:trixie}"

echo "[Vajra OS] Building the Desktop ISO in $IMAGE ..."
docker run --privileged --rm \
  -v "$ROOT/live-build:/lb" \
  -v "$OUT:/out" \
  "$IMAGE" bash -exc '
    export DEBIAN_FRONTEND=noninteractive
    export HOME=/root
    apt-get update -qq
    apt-get install -y -qq live-build debootstrap squashfs-tools xorriso file ca-certificates
    cd /lb
    lb config
    lb build --verbose
    test -s live-image-amd64.hybrid.iso || { echo "[-] FATAL: no ISO was produced"; exit 1; }
    cp live-image-amd64.hybrid.iso /out/vajra-os-1.0-desktop-amd64.iso
    cd /out
    sha256sum vajra-os-1.0-desktop-amd64.iso > vajra-os-1.0-desktop-amd64.iso.sha256
    ls -la /out/
  '

echo ""
echo "============================================"
echo "  Vajra OS Desktop ISO built:"
echo "    $OUT/vajra-os-1.0-desktop-amd64.iso"
echo "============================================"
