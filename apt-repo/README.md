# Vajra OS APT Repository

Add this repository to your Debian/Ubuntu system:

```bash
# Import GPG key (published fresh with each repo update)
curl -fsSL https://raw.githubusercontent.com/ksraj20009/vajra-os/gh-pages/apt-repo/vajra-archive-keyring.asc \
  | gpg --dearmor -o /usr/share/keyrings/vajra-archive-keyring.gpg

# Add repository (packages are served from the gh-pages branch)
echo "deb [signed-by=/usr/share/keyrings/vajra-archive-keyring.gpg] https://raw.githubusercontent.com/ksraj20009/vajra-os/gh-pages/apt-repo vajra main" \
  | sudo tee /etc/apt/sources.list.d/vajra.list

# Update and install
sudo apt update
sudo apt install vajra-core vajra-security-center vajra-control-center vajra-package-manager vajra-update-manager vajra-wallpapers

# Or install the complete desktop
sudo apt install vajra-desktop
```

## Available Packages

Built and published automatically by CI (`.github/workflows/build-release.yml` → `scripts/ci-build-release.sh`):

- vajra-core — 8 OS managers (process, memory, filesystem, device, service, user, boot, display)
- vajra-security-center — Security center (firewall, intrusion detection, privacy)
- vajra-control-center — 12-section settings panel
- vajra-package-manager — App store with permission review before install
- vajra-update-manager — System update manager with rollback
- vajra-wallpapers — Default diamond wallpaper pack
- vajra-desktop — Complete desktop meta-package (entries + icons)
- vajra-buddhi-ai — Buddhi AI assistant
- vajra-keyring — Archive signing keyring
- vajra-sources — APT sources list

## Alternative: direct download

All packages are also bundled in the [v1.0.0 release](https://github.com/ksraj20009/vajra-os/releases/tag/v1.0.0)
as `vajra-os-packages.tar.gz`:

```bash
tar xzf vajra-os-packages.tar.gz
sudo dpkg -i vajra-*.deb
sudo apt-get install -f   # fix dependencies
```

(c) 2026 Vajra OS Project — https://github.com/ksraj20009/vajra-os
