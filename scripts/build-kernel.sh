#!/bin/bash
# ============================================================================
# Vajra OS custom kernel builder
#   scripts/build-kernel.sh [output-dir]        (default: kernel-output)
#
# Shared by .github/workflows/build.yml and scripts/ci-build-release.sh so
# the standalone kernel artifact and the kernel inside the ISO are always
# built from the same source, patch and config.
#
# Builds torvalds/linux v6.10 with:
#   - kernel/patches/*.patch    (Vajra branding, exports vajra_os_version)
#   - kernel/configs/vajra.config (hardening + all live-ISO drivers builtin)
#
# Output:
#   <output-dir>/vajra-kernel-x86_64       - the bzImage
#   <output-dir>/modules/lib/modules/...   - full module set (for the tarball)
#
# The kernel release is 6.10.0-vajra (the patch is committed inside the
# clone so setlocalversion does not append "-dirty").
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/kernel-output}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

# --- 1. Source ---------------------------------------------------------------
if [ ! -d "$ROOT/kernel/linux" ]; then
  echo "[1/4] Cloning torvalds/linux v6.10 (depth 1)..."
  git clone --depth=1 --branch v6.10 https://github.com/torvalds/linux.git \
    "$ROOT/kernel/linux"
fi
cd "$ROOT/kernel/linux"

# --- 2. Patches --------------------------------------------------------------
echo "[2/4] Applying Vajra OS patches..."
for patch in "$ROOT"/kernel/patches/*.patch; do
  if git apply "$patch"; then
    echo "  [+] applied: $(basename "$patch")"
  else
    echo "  [!] skipped: $(basename "$patch")"
  fi
done
# commit so the kernel release is a clean "6.10.0-vajra" (no -dirty suffix)
git add -A
git -c user.email=ci@vajra-os.org -c user.name="Vajra CI" \
  commit -qm "vajra: branding patch + config applied" || true

# --- 3. Config ---------------------------------------------------------------
echo "[3/4] Applying vajra.config on top of defconfig..."
make defconfig
while IFS= read -r line; do
  [[ "$line" =~ ^# ]] && continue
  [[ -z "$line" ]] && continue
  key="${line%%=*}"
  val="${line#*=}"
  val="${val%\"}"; val="${val#\"}"
  case "$val" in
    y) scripts/config --enable "$key" ;;
    n) scripts/config --disable "$key" ;;
    m) scripts/config --module "$key" ;;
    *) scripts/config --set-str "$key" "$val" ;;
  esac
done < "$ROOT/kernel/configs/vajra.config"
make olddefconfig
echo "--- key config values ---"
grep -E "CONFIG_LOCALVERSION=|CONFIG_DEFAULT_HOSTNAME=" .config || true

# --- 4. Build ----------------------------------------------------------------
echo "[4/4] Building kernel (make -j$(nproc))..."
set -o pipefail
make -j"$(nproc)" 2>&1 | tail -30
test -s arch/x86/boot/bzImage || { echo "[-] FATAL: bzImage was not built"; exit 1; }
echo "[+] bzImage: $(stat -c%s arch/x86/boot/bzImage) bytes"
echo "[+] kernel release: $(make kernelrelease)"

make modules_install INSTALL_MOD_PATH="$OUT/modules" > /dev/null 2>&1
cp arch/x86/boot/bzImage "$OUT/vajra-kernel-x86_64"

echo ""
echo "============================================"
echo "  Custom Vajra kernel built:"
echo "    $OUT/vajra-kernel-x86_64"
echo "    $OUT/modules/lib/modules/"
echo "============================================"
