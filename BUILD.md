# Vajra OS Build Guide

Complete instructions for building Vajra OS from source.

## Quick Start (Pre-built ISO)

Download the pre-built ISO from the releases page. The ISO is isohybrid —
dd it straight to a USB stick and boot it (works on BIOS **and** UEFI
machines):

```bash
dd if=vajra-os-1.0-amd64.iso of=/dev/sdX bs=4M status=progress
sync
```

Or install it to disk from the running live system with `vajra-install`.

Test in QEMU:
```bash
sudo apt install qemu-system-x86 ovmf
# Automated headless boot test (4 tests: kernel smoke, BIOS CD, UEFI CD, UEFI USB)
python3 iso/boot-test.py --iso vajra-os-1.0-amd64.iso
```

## The Custom Kernel

The release ISO boots Vajra OS's **own kernel** — Linux 6.10 built from
torvalds/linux with the Vajra branding patch and the hardened
`kernel/configs/vajra.config` (all live-system drivers compiled in, so the
ISO needs no module set). `uname -r` reports `6.10.0-vajra+` (the trailing
`+` is Kbuild's marker for a locally-built tree).

```bash
# Build it yourself (~15 min on a fast machine)
scripts/build-kernel.sh kernel-output
#    kernel-output/vajra-kernel-x86_64   - the bzImage
#    kernel-output/modules/               - full module set
```

CI runs the same script twice: once standalone (`.github/workflows/build.yml`
publishes `vajra-kernel.tar.gz` to the release after QEMU boot-testing the
kernel), and once inside the release build so the ISO itself is built with
the custom kernel.

## Building the ISO Yourself

### Prerequisites (any Linux machine)

```bash
sudo apt install python3 python3-pip qemu-system-x86 ovmf
pip3 install pycdlib
```

### Build the ISO

```bash
git clone https://github.com/ksraj20009/vajra-os.git
cd vajra-os

# With the custom kernel (what CI ships):
scripts/build-kernel.sh kernel-output
python3 iso/build-iso.py --output vajra-os-1.0-amd64.iso \
  --kernel kernel-output/vajra-kernel-x86_64

# Or the quick local variant (downloads the Alpine 6.6 kernel instead,
# everything else identical):
python3 iso/build-iso.py

# Verify it boots (QEMU: kernel smoke + full BIOS chain + UEFI + UEFI USB, ~15 min)
python3 iso/boot-test.py
```

### What the build does

1. Kernel: custom 6.10.0-vajra (built by `scripts/build-kernel.sh`) or the
   Alpine 6.6.142 fallback
2. Downloads BusyBox (396 Unix commands)
3. Downloads all 280 Vajra utility scripts + 14 core tools from the repo
4. Downloads Buddhi AI assistant
5. Builds initramfs (cpio.gz) with all tools + vajra-install embedded
6. Gets ISOLINUX (BIOS boot chain) + builds GRUB EFI (UEFI, standalone)
7. Applies isohybrid **with UEFI support** — dd to USB and it boots on
   BIOS and UEFI machines alike
8. Creates ISO with El Torito BIOS entry, UEFI entry (FAT efiboot.img),
   and 3 boot options: default, debug, serial console

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

The APT repository is published to the `gh-pages` branch (`apt-repo/`), and
signed with a **persistent key** stored as the `VAJRA_APT_GPG_KEY` repo
secret — the fingerprint never changes between releases:

```
5607 5607 3ECC 64AD 45C1 99C0 3212 D97D DE0C CA4A
```

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
| Vajra kernel 6.10.0-vajra | 1 | ~15 MB |
| Kernel modules | builtin | — |
| BusyBox applets | 396 | 1.4 MB |
| Vajra core tools | 14 | 200 KB |
| Utility scripts | 280 | 2 MB |
| Buddhi AI | 1 | 49 KB |
| vajra-install + vajra-tools | 2 | 9 KB |
| ISOLINUX bootloader | 2 files | 155 KB |
| GRUB EFI (standalone) | 1 | ~5 MB |
| GPG public key | 1 | 1 KB |

## Boot Modes

1. **BIOS CD (El Torito)** — SeaBIOS → ISOLINUX → kernel
2. **UEFI CD** — OVMF → El Torito 0xEF → FAT efiboot.img → GRUB → kernel
3. **BIOS USB** — dd the ISO to a stick; isohybrid MBR → kernel
4. **UEFI USB** — same dd'd stick; GPT/MBR ESP → GRUB → kernel
5. **Serial console** — for headless servers and VMs

All four boot paths are verified in CI by actually booting them in QEMU
(`iso/boot-test.py`), before anything is published.

## Architecture

```
vajra-os-1.0-amd64.iso
├── /vmlinuz              — Vajra custom kernel 6.10.0-vajra
├── /initramfs.cpio.gz    — Root filesystem
│   ├── /bin/             — BusyBox (396 applets)
│   ├── /usr/bin/         — 14 core tools + vajra-install + vajra-tools + Buddhi AI
│   ├── /usr/share/vajra/ — 280 utility scripts
│   └── /etc/             — System config
├── /ISOLINUX/ISOLINUX.BIN — BIOS bootloader (El Torito boot image)
├── /ISOLINUX/LDLINUX.C32 — ISOLINUX module
├── /EFI/BOOT/BOOTX64.EFI — GRUB for UEFI boot
├── /EFIBOOT.IMG          — FAT image wrapping GRUB (UEFI El Torito + USB ESP)
├── /boot.cat             — El Torito boot catalog
├── /README.txt           — Documentation
└── [MBR/GPT]             — isohybrid --uefi boot sector (BIOS + UEFI USB)
```

## CI Workflows

| Workflow | What it does |
|----------|--------------|
| `build-release.yml` | Full release: 10 .deb packages, custom kernel, ISO (all 4 boot tests), rootfs, APT repo publish |
| `build.yml` | Standalone custom-kernel build + QEMU boot test → `vajra-kernel.tar.gz` |

(c) 2026 Vajra OS Project
