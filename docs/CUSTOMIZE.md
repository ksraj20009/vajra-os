# Customizing Vajra OS

Everything in Vajra OS is plain files and plain scripts — here is where to
change what.

## Branding (icons, wallpapers, boot splash)

All artwork lives in `branding/`:

| Directory | Contents |
|-----------|----------|
| `branding/icons/` | The Vajra icon set, 16–512 px (26 PNGs + SVG source) |
| `branding/wallpapers/` | Desktop wallpapers |
| `branding/plymouth/` | Plymouth boot splash (Vajra logo + tricolor bar) |
| `branding/grub/` | GRUB menu background |

Replace a file (keep the same name and size) and rebuild. The APT
packages `vajra-desktop` and `vajra-wallpapers` pick these up
automatically during `packaging/build-all-packages.sh`.

## Adding a utility tool

Drop a `.py` or `.sh` file into any top-level tool directory
(`security/`, `privacy/`, `unique/`, `finance/`, `education/`, ...). It
automatically:

- ships in the next ISO build (the builder sweeps every `.py`/`.sh`
  outside the build-only directories), and
- appears in `vajra-tools` output and on the live PATH.

## Adding a core tool

Core tools live in `core/` and get first-class treatment: real commands
in `/usr/bin` in the ISO and their own `.deb` packages
(`vajra-core`, `vajra-security-center`, ...). Add the file to `core/`
and, if it belongs to an existing package, list it in
`scripts/ci-build-release.sh` section 3 (source population).

## Kernel

`kernel/configs/vajra.config` is applied on top of defconfig by
`scripts/build-kernel.sh`. Toggle options there (hardening, drivers,
filesystems) and rebuild:

```bash
scripts/build-kernel.sh kernel-output
python3 iso/build-iso.py --kernel kernel-output/vajra-kernel-x86_64
```

Kernel patches (the branding patch, any future hardening patches) go in
`kernel/patches/*.patch`.

## Installer behavior

The disk installer script is embedded in `iso/build-iso.py`
(`INSTALLER_SCRIPT`) — partitioning, formatting, what gets copied, and
the boot configs it writes. The Calamares configuration for desktop
installs is `installer/calamares/`.

## First boot of an installed system

`system/vajra-first-boot.sh` (and the wizard `system/vajra-first-boot-wizard.py`)
decide what happens on the first boot: locales, default settings, AI
config seeding.

## Building your own variant

```bash
# Full ISO, your kernel config, your branding
scripts/build-kernel.sh out
python3 iso/build-iso.py --output my-vajra.iso --kernel out/vajra-kernel-x86_64

# Just the packages
cd packaging && ./build-all-packages.sh
```

See [BUILD.md](../BUILD.md) for the full build guide.
