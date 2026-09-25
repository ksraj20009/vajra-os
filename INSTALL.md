# Vajra OS (वज्र OS) — Installation Guide

Four ways to run Vajra OS — pick one:

| Method | What you get |
|--------|--------------|
| **1. Live boot (recommended)** | The complete OS from a USB stick or CD — nothing installed |
| **2. Install to disk** | `vajra-install` from the running live system |
| **3. Docker** | Try it without rebooting |
| **4. APT packages** | Vajra tools on your existing Debian/Ubuntu |

## Requirements

- A 64-bit PC (x86_64) — BIOS (legacy) or UEFI, both work
- 512 MB RAM minimum (1 GB recommended)
- USB stick 512 MB or larger (or a CD/DVD)

## Download

All assets live on the [v1.0.0 release page](https://github.com/ksraj20009/vajra-os/releases/tag/v1.0.0):

| Asset | What it is |
|-------|-----------|
| `vajra-os-1.0-amd64.iso` | The bootable OS (32.5 MB) |
| `vajra-os-rootfs.tar.gz` | Root filesystem for Docker import |
| `vajra-os-packages.tar.gz` | All 10 `.deb` packages |
| `vajra-kernel.tar.gz` | The custom kernel (bzImage + full module set) |

## Option 1 — Live boot (no installation)

Write the ISO to a USB stick:

```bash
# Linux / macOS (replace sdX with your stick — double-check with lsblk!)
dd if=vajra-os-1.0-amd64.iso of=/dev/sdX bs=4M status=progress
sync
```

On Windows, use [Rufus](https://rufus.ie) (choose *DD mode* if asked) or [balenaEtcher](https://etcher.balena.io). Burning the ISO to a CD/DVD also works.

The ISO is a **hybrid image that boots four ways** — BIOS and UEFI, from CD and from USB — and all four paths are verified in CI by actually booting them in QEMU before anything is published.

Restart the computer and boot from the USB (usually F12 / F2 / Del for the boot menu). You land in the live Vajra OS environment running the custom **6.10.0-vajra** kernel. First commands:

```
vajra-help      — list everything available
vajra-tools     — list the 280 utility tools (GST, Panchang, IRCTC...)
buddhi          — the offline AI assistant
```

If DHCP did not answer during boot, bring the network up manually:

```sh
udhcpc -i eth0
```

## Option 2 — Install to disk

Boot the live system (Option 1), then run:

```sh
vajra-install              # interactive
vajra-install sdb          # install straight to /dev/sdb
vajra-install --clone sdb  # dd the boot media onto another USB stick
```

The installer partitions the target disk, formats it ext2, copies the whole
running system (kernel, initramfs, tools) and writes boot configurations.
The final screen explains the one manual step (installing the bootloader
boot block from any Linux rescue environment) — the installed disk is
otherwise identical to the live USB.

## Option 3 — Docker

```bash
docker import vajra-os-rootfs.tar.gz vajra-os:1.0
docker run -it vajra-os:1.0
```

## Option 4 — APT packages on existing Debian/Ubuntu

```bash
curl -fsSL https://raw.githubusercontent.com/ksraj20009/vajra-os/gh-pages/apt-repo/vajra-archive-keyring.asc \
  | gpg --dearmor -o /usr/share/keyrings/vajra-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/vajra-archive-keyring.gpg] https://raw.githubusercontent.com/ksraj20009/vajra-os/gh-pages/apt-repo vajra main" \
  | sudo tee /etc/apt/sources.list.d/vajra.list

sudo apt update
sudo apt install vajra-core vajra-buddhi-ai vajra-security-center
```

The repository is signed with a persistent key — the fingerprint never
changes between releases, so the keyring you import keeps working.

## Test in a virtual machine first (optional)

```bash
sudo apt install qemu-system-x86 ovmf
python3 iso/boot-test.py --iso vajra-os-1.0-amd64.iso   # automated, 4 tests
# or interactively:
qemu-system-x86_64 -m 1024 -cdrom vajra-os-1.0-amd64.iso -boot d
```

## More docs

- [BUILD.md](BUILD.md) — building everything from source
- [docs/PRIVACY.md](docs/PRIVACY.md) — the privacy stack
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — fixing problems
- [docs/CUSTOMIZE.md](docs/CUSTOMIZE.md) — making Vajra OS yours
