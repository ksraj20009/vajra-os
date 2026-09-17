# Vajra OS — Build Status

All artifacts are built by CI: `.github/workflows/build-release.yml` → `scripts/ci-build-release.sh`.
The pipeline rebuilds everything automatically on changes to `core/`, `ai/`, `apps/`,
`branding/`, `packaging/`, `iso/`, or the script itself.

## Packages (10/10 built and verified)

| Package | Version | Size | Contents |
|---------|---------|------|----------|
| vajra-core | 1.0.0 | 20,580 B | 8 OS managers (boot, process, memory, filesystem, device, display, service, user-session) |
| vajra-security-center | 1.0.0 | 4,468 B | Firewall, encryption, audit, antivirus |
| vajra-control-center | 1.0.0 | 6,434 B | 12-section system settings |
| vajra-package-manager | 1.0.0 | 5,254 B | App store with 28 curated apps |
| vajra-update-manager | 1.0.0 | 3,906 B | Update manager with rollback |
| vajra-buddhi-ai | 1.0.0 | 13,562 B | Buddhi AI assistant |
| vajra-desktop | 1.0.0 | 34,052 B | Desktop meta-package: entries + hicolor icons |
| vajra-wallpapers | 1.0.0 | 82,294 B | Default diamond wallpaper (1920x1080) |
| vajra-keyring | 1.0.0 | 2,222 B | APT archive signing keyring |
| vajra-sources | 1.0.0 | 1,392 B | APT sources list |

Every package passes `dpkg-deb --info` and `dpkg-deb --contents` verification in CI
(see the Verify packages step of the workflow logs).

## Release artifacts (v1.0.0)

| Artifact | Size | Description |
|----------|------|-------------|
| vajra-os-1.0-amd64.iso | ~43.5 MB | Bootable ISO, BIOS + UEFI, kernel 6.6.142, 280+ tools |
| vajra-os-packages.tar.gz | ~174 KB | All 10 .deb packages + SHA256SUMS |
| vajra-os-rootfs.tar.gz | ~1.7 MB | Docker rootfs: BusyBox + 290 tools + Buddhi AI |

## APT repository

Published to the `gh-pages` branch (`apt-repo/`) with real SHA256 checksums
and signed `Release` / `InRelease` metadata. Install instructions:
[apt-repo/README.md](../apt-repo/README.md).

## Building locally

```bash
# Packages (needs dpkg-buildpackage + debhelper)
bash packaging/build-all-packages.sh

# ISO (needs: pip install pycdlib)
python3 iso/build-iso.py

# Docker rootfs
python3 iso/build-rootfs.py

# Branding assets (needs Pillow)
python3 branding/generate-all-branding.py
```
