# Contributing to Vajra OS

वज्र OS is built in India, for everyone — and contributions are welcome.
This document tells you how to build, test and submit changes.

## Ways to contribute

- **Indian-language support** — improve any of the 10 languages
  (Hindi, Tamil, Bengali, Gujarati, Punjabi, Kannada, Telugu, Malayalam,
  Marathi, Sanskrit) or add a new one (`locale/`)
- **India-first tools** — GST, Panchang, Vedic math, Ayurveda, IRCTC
  and the other 280+ utilities (`unique/`, `finance/`, `education/`)
- **Core OS tools** — the 14 system managers in `core/`
- **Buddhi AI** — the local AI assistant (`ai/`)
- **Kernel** — config and patches (`kernel/`)
- **Branding** — Plymouth splash, GRUB theme, icons, wallpapers (`branding/`)
- **Documentation** — `README.md`, `BUILD.md`, `INSTALL.md`, `docs/`

## Development setup

Any Linux machine works. You need Python 3, git, and for full builds the
packages listed in `BUILD.md`.

```bash
git clone https://github.com/ksraj20009/vajra-os.git
cd vajra-os
```

### Build and test locally

```bash
# Lint / syntax-check what you changed
python3 -m py_compile core/<tool>.py
bash -n scripts/<script>.sh

# Build the custom kernel (~15 min on a fast machine)
scripts/build-kernel.sh kernel-output

# Build the ISO with it
python3 iso/build-iso.py --output test.iso \
  --kernel kernel-output/vajra-kernel-x86_64

# Boot-test it in QEMU (4 tests: kernel smoke, BIOS CD, UEFI CD, UEFI USB)
python3 iso/boot-test.py --iso test.iso --expect-custom-kernel

# Build the .deb packages (10 packages)
cd packaging && dpkg-buildpackage -us -uc -b
```

`BUILD.md` has the full reference, including Docker and APT-repo workflows.

## What CI does with your PR

Pushing to any of `core/`, `ai/`, `apps/`, `branding/`, `packaging/`,
`iso/`, `kernel/` or the shared build scripts triggers the full release
build on GitHub Actions: 10 packages, the custom kernel, the ISO, and
**four actual QEMU boot tests**. A red run blocks merging — please make
it green before requesting review.

`kernel/` and `scripts/build-kernel.sh` changes also run the standalone
kernel build + QEMU boot test.

## Code style

- **Python** (`.py`): Python 3 stdlib only — no pip dependencies in the
  OS tools. Keep scripts runnable on a bare live system.
- **Shell** (`.sh`): bash with `set -euo pipefail` where it makes sense.
- **Indic text**: UTF-8 everywhere; test rendering with `vajra-help`.
- **Commits**: short imperative subject line, body explaining *why*.

## Pull requests

1. Fork, branch, commit.
2. Run the relevant local checks above.
3. Open the PR with a clear description of what changed and why.
4. Confirm CI is green.

Small docs fixes (typos, clarifications) are always welcome and don't
need a test run.

धन्यवाद · Thank you 🙏
