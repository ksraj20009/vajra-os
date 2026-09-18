#!/bin/bash
# ============================================================================
# Vajra OS — full release build (run by .github/workflows/build-release.yml)
# Builds all vajra-* .deb packages, the ISO, the Docker rootfs, uploads them to
# the v1.0.0 release, and publishes a signed APT repository to gh-pages.
# ============================================================================
set -uo pipefail

REPO_SLUG="${GITHUB_REPOSITORY:-ksraj20009/vajra-os}"
RELEASE_TAG="v1.0.0"

fail() { echo "[-] FATAL: $*" >&2; exit 1; }

echo "============================================"
echo "  Vajra OS release build"
echo "============================================"

# --- 1. Build dependencies -------------------------------------------------
sudo apt-get update -qq
sudo apt-get install -y -qq dpkg-dev debhelper devscripts gnupg apt-utils binutils qemu-system-x86 \
  || fail "could not install build dependencies"

# --- 2. Generate the APT signing key ---------------------------------------
export GNUPGHOME="$(mktemp -d)"
echo "$GNUPGHOME" > /tmp/gnupghome
cat > /tmp/keyspec <<'EOF'
%no-protection
Key-Type: RSA
Key-Length: 3072
Name-Real: Vajra OS APT Repository
Name-Email: packages@vajra-os.org
Expire-Date: 0
%commit
EOF
gpg --batch --gen-key /tmp/keyspec || fail "key generation failed"
gpg --batch --yes --armor --export packages@vajra-os.org > packaging/keys/vajra-archive-keyring.asc
gpg --list-keys --fingerprint || true

# --- 3. Populate package sources from the repo tree ------------------------
mkdir -p packaging/vajra-core/src
for f in vajra-boot-manager.sh vajra-process-manager.py vajra-memory-manager.py \
         vajra-filesystem-manager.py vajra-device-manager.py vajra-display-server.sh \
         vajra-service-manager.py vajra-user-session-manager.py; do
  cp "core/$f" packaging/vajra-core/src/ || fail "missing core/$f"
done

mkdir -p packaging/vajra-security-center/src
cp core/vajra-security-center.py packaging/vajra-security-center/src/
mkdir -p packaging/vajra-control-center/src
cp core/vajra-control-center.py packaging/vajra-control-center/src/
mkdir -p packaging/vajra-package-manager/src
cp core/vajra-package-manager.py packaging/vajra-package-manager/src/
mkdir -p packaging/vajra-update-manager/src
cp core/vajra-update-manager.py packaging/vajra-update-manager/src/

mkdir -p packaging/vajra-buddhi-ai/src
cp ai/buddhi-ai.py packaging/vajra-buddhi-ai/src/ || fail "missing ai/buddhi-ai.py"

mkdir -p packaging/vajra-keyring/src
gpg --batch --yes --dearmor < packaging/keys/vajra-archive-keyring.asc \
  > packaging/vajra-keyring/src/vajra-archive-keyring.gpg

mkdir -p packaging/vajra-desktop/src
cp apps/desktop-entries/*.desktop packaging/vajra-desktop/src/
cp branding/icons/vajra-*-48x48.png packaging/vajra-desktop/src/ 2>/dev/null || true
cp branding/icons/vajra-logo-256x256.png packaging/vajra-desktop/src/ 2>/dev/null || true

mkdir -p packaging/vajra-wallpapers/src
cp branding/wallpapers/vajra-default.png packaging/vajra-wallpapers/src/vajra-default.png \
  || fail "missing wallpaper (run generate-branding first)"

chmod +x packaging/vajra-*/debian/rules
# debian/compat + debhelper-compat in control both declare the level — fatal in dh 13
rm -f packaging/vajra-*/debian/compat

# --- 4. Build every package -------------------------------------------------
cd packaging || fail "no packaging dir"
OK=0; FAIL=0; FAILED=""
for pkg in vajra-core vajra-security-center vajra-control-center vajra-package-manager \
           vajra-update-manager vajra-buddhi-ai vajra-keyring vajra-desktop \
           vajra-wallpapers vajra-sources; do
  echo "=== Building: $pkg ==="
  if (cd "$pkg" && dpkg-buildpackage -us -uc -b > "/tmp/build-$pkg.log" 2>&1); then
    echo "  [+] OK: $pkg"
    OK=$((OK+1))
  else
    echo "  [-] FAILED: $pkg"
    tail -30 "/tmp/build-$pkg.log" 2>/dev/null || true
    FAIL=$((FAIL+1)); FAILED="$FAILED $pkg"
  fi
done
echo "Packages built: $OK  failed: $FAIL ($FAILED)"
ls -la ./*.deb || true
[ "$OK" -ge 8 ] || fail "expected at least 8 of 10 packages to build, got $OK"

for deb in ./*.deb; do
  echo "--- $deb ---"
  dpkg-deb --info "$deb" | head -6
  dpkg-deb --contents "$deb" | head -5
done

sha256sum ./*.deb > SHA256SUMS
tar czf ../vajra-os-packages.tar.gz ./*.deb SHA256SUMS
echo "[+] Packages tarball:"
ls -la ../vajra-os-packages.tar.gz
cd "$GITHUB_WORKSPACE" || fail "lost workspace"

# --- 5. Build the ISO --------------------------------------------------------
python3 -m pip install --user pycdlib
sudo mkdir -p /scratch/work
sudo chown -R "$(id -u):$(id -g)" /scratch
python3 iso/build-iso.py --output vajra-os-1.0-amd64.iso || fail "ISO build failed"
ls -la vajra-os-1.0-amd64.iso

# --- 5a. Boot-test the ISO (nothing unbootable gets published) ---------------
python3 iso/boot-test.py --iso vajra-os-1.0-amd64.iso || fail "ISO boot test failed"

# --- 5b. Build the Docker rootfs ---------------------------------------------
python3 iso/build-rootfs.py --output vajra-os-rootfs.tar.gz || fail "rootfs build failed"
ls -la vajra-os-rootfs.tar.gz

# --- 6. Upload artifacts to the release -------------------------------------
if [ -n "${GH_TOKEN:-}" ]; then
  gh release upload "$RELEASE_TAG" \
    vajra-os-1.0-amd64.iso vajra-os-packages.tar.gz vajra-os-rootfs.tar.gz --clobber \
    || fail "release upload failed"
  echo "[+] Release assets updated"
else
  echo "[!] GH_TOKEN not set, skipping release upload"
fi

# --- 7. Publish the APT repository to gh-pages -------------------------------
git clone --quiet --branch gh-pages \
  "https://x-access-token:${GH_TOKEN}@github.com/${REPO_SLUG}.git" /tmp/pages \
  || fail "could not clone gh-pages"
# identity must be set in the CLONE, not the workspace checkout
git -C /tmp/pages config user.name "vajra-bot"
git -C /tmp/pages config user.email "actions@github.com"
cd /tmp/pages/apt-repo || fail "no apt-repo on gh-pages"

mkdir -p pool/main/v
for deb in "$GITHUB_WORKSPACE"/packaging/*.deb; do
  name="$(basename "$deb" | sed 's/_1\.0\.0_.*//')"
  mkdir -p "pool/main/v/$name/"
  cp "$deb" "pool/main/v/$name/"
done

apt-ftparchive packages pool > dists/vajra/main/binary-all/Packages
gzip -9kf dists/vajra/main/binary-all/Packages

export GNUPGHOME="$(cat /tmp/gnupghome)"
cd dists/vajra || fail "no dists/vajra"
apt-ftparchive \
  -o APT::FTPArchive::Release::Origin="Vajra OS" \
  -o APT::FTPArchive::Release::Suite="vajra" \
  -o APT::FTPArchive::Release::Codename="vajra" \
  -o APT::FTPArchive::Release::Architectures="all" \
  -o APT::FTPArchive::Release::Components="main" \
  -o APT::FTPArchive::Release::Description="Vajra OS APT Repository" \
  release . > Release
gpg --batch --yes --armor --detach-sign --local-user packages@vajra-os.org -o Release.gpg Release
gpg --batch --yes --clearsign --local-user packages@vajra-os.org -o InRelease Release
gpg --batch --yes --armor --export packages@vajra-os.org > ../../vajra-archive-keyring.asc

cd /tmp/pages || fail "lost pages clone"
git add apt-repo
if git diff --cached --quiet; then
  echo "[!] no changes to publish"
else
  git commit -m "apt: publish packages with signed metadata" || fail "git commit failed"
  git push origin gh-pages || fail "could not push gh-pages"
fi
echo "[+] APT repository published"
echo "Done."
