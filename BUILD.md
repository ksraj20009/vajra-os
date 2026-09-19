# Vajra OS Build Guide

Complete instructions for building Vajra OS from source.

## Quick Start (Pre-built ISO)

Download the pre-built ISO from the releases page. The ISO is isohybrid —
dd it straight to a USB stick and boot it:

```bash
dd if=vajra-os-1.0-amd64.iso of=/dev/sdX bs=4M status=progress
sync
```

Or install it to disk from the running live system with `vajra-install`.

Test in QEMU:
```bash
sudo apt install qemu-system-x86
# Automated headless boot test (serial console, no display needed)
python3 iso/boot-test.py --iso vajra-os-1.0-amd64.iso

# Or interactive test with a window
sudo apt install ovmf
./iso/test-vajra-iso.sh vajra-os-1.0-amd64.iso
```

## Building the ISO Yourself

### Prerequisites (any Linux machine)

```bash
sudo apt install python3 python3-pip qemu-system-x86 ovmf
pip3 install pycdlib
```

### Build the ISO

```bash
# Clone the repo
git clone https://github.com/ksraj20009/vajra-os.git
cd vajra-os

# Build the ISO (downloads kernel + BusyBox, builds initramfs, creates bootable ISO)
python3 iso/build-iso.py

# Verify it boots (QEMU: kernel smoke test + full BIOS chain + UEFI, ~10 minutes)
python3 iso/boot-test.py
```

### What the build does

1. Downloads Alpine Linux kernel 6.6.142 (with 922 kernel modules)
2. Downloads BusyBox (396 Unix commands)
3. Downloads all 280 Vajra utility scripts + 14 core tools from the repo
4. Downloads Buddhi AI assistant
5. Builds initramfs (cpio.gz, 28.8 MB) with all tools embedded
6. Downloads ISOLINUX (BIOS bootloader) + GRUB EFI binary (UEFI boot)
7. Applies an isohybrid MBR so the ISO can be dd'd straight to USB
8. Creates ISO with:
   - El Torito BIOS boot via ISOLINUX (boot-info-table patched)
   - UEFI boot via /EFI/BOOT/BOOTX64.EFI (standalone GRUB in CI)
   - isohybrid MBR — dd to USB and it boots
   - 3 boot options: default, debug, serial console

## Building Debian Packages

```bash
# Build all .deb packages
sudo apt install dpkg-dev debhelper devscripts
cd packaging/
./build-all-packages.sh

# Packages will be in: packaging/
```

Note: CI builds all 10 packages with sources populated automatically — see
`scripts/ci-build-release.sh` for the authoritative build recipe.

## Building Docker Image

```bash
# Download vajra-os-rootfs.tar.gz from the release, then:
docker import vajra-os-rootfs.tar.gz vajra-os:1.0

# Or rebuild the rootfs yourself
python3 iso/build-rootfs.py

# Or build from Dockerfile
docker build -t vajra-os:1.0 -f docker/Dockerfile.vajra .

# Run
docker run -it vajra-os:1.0
```

## APT Repository

The APT repository is published to the `gh-pages` branch (`apt-repo/`). To use it:

```bash
# Import GPG key (from gh-pages, where the packages live)
curl -fsSL https://raw.githubusercontent.com/ksraj20009/vajra-os/gh-pages/apt-repo/vajra-archive-keyring.asc | gpg --dearmor -o /usr/share/keyrings/vajra-archive-keyring.gpg

# Add repository
echo "deb [signed-by=/usr/share/keyrings/vajra-archive-keyring.gpg] https://raw.githubusercontent.com/ksraj20009/vajra-os/gh-pages/apt-repo vajra main" | sudo tee /etc/apt/sources.list.d/vajra.list

# Install
sudo apt update
sudo apt install vajra-core vajra-security-center vajra-control-center
```

## ISO Contents

| Component | Count | Size |
|-----------|-------|------|
| Linux Kernel | 6.6.142 | 10.4 MB |
| Kernel modules | 922 | 17 MB |
| BusyBox applets | 396 | 1.4 MB |
| Vajra core tools | 14 | 200 KB |
| Utility scripts | 280 | 2 MB |
| Buddhi AI | 1 | 49 KB |
| vajra-install | 1 | 7 KB |
| ISOLINUX bootloader | 2 files | 155 KB |
| GRUB EFI | 1 | 4.2 MB |
| GPG public key | 1 | 1 KB |
| **Total ISO** | | **44 MB** |

## Boot Modes

1. **BIOS (El Torito)** — Works on all x86 PCs, legacy boot
2. **UEFI (GRUB)** — Works on modern PCs with UEFI firmware
3. **Serial console** — For headless servers and VMs

## Architecture

```
vajra-os-1.0-amd64.iso (44 MB)
├── /vmlinuz              — Linux kernel 6.6.142
├── /initramfs.cpio.gz    — Root filesystem (28.8 MB)
│   ├── /bin/             — BusyBox (396 applets)
│   ├── /usr/bin/         — core tools + vajra-install + Buddhi AI
│   ├── /usr/share/vajra/ — 280 utility scripts
│   ├── /lib/modules/     — 922 kernel modules
│   └── /etc/             — System config
├── /ISOLINUX/ISOLINUX.BIN — BIOS bootloader (El Torito boot image)
├── /ISOLINUX/LDLINUX.C32 — ISOLINUX module
├── /EFI/BOOT/BOOTX64.EFI — GRUB for UEFI boot
├── /boot.cat             — El Torito boot catalog
├── /README.txt           — Documentation
└── [MBR]                 — isohybrid boot sector (USB bootable)
```

(c) 2026 Vajra OS Project
