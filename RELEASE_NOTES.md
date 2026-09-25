Vajra OS 1.0.0 — Release Notes
===============================
Date: September 25, 2026 (updated from the initial 1.0.0 notes)

India's Privacy-First AI-Powered Operating System — a complete standalone
OS: custom kernel, own APT repository, Docker image, 320+ tools.

Bootable ISO (32.5 MB) — boots four ways, all CI-verified
=========================================================
`vajra-os-1.0-amd64.iso` boots on BIOS and UEFI machines, from CD and from
USB. Every path is verified in CI by actually booting it in QEMU before
anything is published (iso/boot-test.py, 4 tests):

  - BIOS CD    — El Torito → ISOLINUX → kernel
  - UEFI CD    — El Torito 0xEF → FAT efiboot.img → GRUB → kernel
  - BIOS USB   — isohybrid MBR (dd the ISO straight to a stick)
  - UEFI USB   — same dd'd stick; GPT + ESP partition → GRUB → kernel

Inside the ISO:

  - Custom Vajra kernel 6.10.0-vajra+ — Linux 6.10 from torvalds/linux
    with the Vajra branding patch (exports vajra_os_version) and the
    hardened kernel/configs/vajra.config; every live-system driver
    (virtio, e1000/e1000e, NVMe, AHCI, USB storage, ext4/vfat/iso9660,
    serial console) is compiled in, so no module set is needed.
  - BusyBox (396 Unix commands)
  - 14 Vajra core tools (process/memory/filesystem/device/service/
    security/control/package/update managers, display server, boot manager)
  - 280 utility scripts (GST, Panchang, Vedic math, Ayurveda, IRCTC, ...)
  - Buddhi AI assistant (बुद्धि) — fully local
  - vajra-install disk installer + vajra-tools

Custom Kernel
=============
`vajra-kernel.tar.gz` — the same kernel the ISO boots, standalone:
bzImage + the full module set. Built by scripts/build-kernel.sh and
QEMU boot-tested in CI (build.yml) before publishing.

Debian Packages (10, GPG-signed)
================================
  vajra-core              — 8 core OS managers
  vajra-security-center   — security center
  vajra-control-center    — 12-section settings
  vajra-package-manager   — app store
  vajra-update-manager    — update manager
  vajra-buddhi-ai         — AI assistant
  vajra-keyring           — GPG signing key
  vajra-desktop           — desktop meta-package
  vajra-wallpapers        — official wallpapers
  vajra-sources           — APT sources entry

APT Repository (persistent signing key)
=======================================
Published to gh-pages (`apt-repo/`), signed with a key stored as the
VAJRA_APT_GPG_KEY repo secret, so the fingerprint is stable across
releases:

  5607 5607 3ECC 64AD 45C1 99C0 3212 D97D DE0C CA4A

Docker
======
`vajra-os-rootfs.tar.gz` — `docker import` it and run Vajra OS as a
container.

Builds
======
Everything above is built and verified by GitHub Actions:
build-release.yml (full release, 4 boot tests) and build.yml
(custom kernel + QEMU boot test). A red run blocks publishing.

Dharmo Rakshati Rakshitah — धर्मो रक्षति रक्षितः
