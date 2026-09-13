<p align="center">
  <img src="https://raw.githubusercontent.com/ksraj20009/vajra-os/main/branding/icons/vajra-logo-256x256.png" width="130" alt="Vajra OS Logo">
</p>

<h1 align="center">वज्र OS — Vajra OS</h1>

<h3 align="center">India's Privacy-First, AI-Powered Operating System</h3>

<p align="center"><strong>धर्मो रक्षति रक्षितः · Dharmo Rakshati Rakshitah</strong></p>

<p align="center">
  <a href="https://github.com/ksraj20009/vajra-os/releases"><img src="https://img.shields.io/badge/release-v1.0.0-FF9933" alt="Release"></a>
  <a href="https://github.com/ksraj20009/vajra-os/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-138808" alt="License"></a>
  <a href="https://ksraj20009.github.io/vajra-os/"><img src="https://img.shields.io/badge/website-ksraj20009.github.io-blue" alt="Website"></a>
  <img src="https://img.shields.io/badge/made%20in-India-red" alt="Made in India">
</p>

---

**Vajra OS is a complete, standalone operating system** — not a plugin, not an app, not an Ubuntu extension. It boots from USB, runs on bare metal, and comes with its own kernel, desktop environment, AI assistant, full branding suite, and 320+ built-in tools across 510+ source files.

## Download

**Latest Release:** [v1.0.0](https://github.com/ksraj20009/vajra-os/releases/tag/v1.0.0)

**Website:** [ksraj20009.github.io/vajra-os](https://ksraj20009.github.io/vajra-os/)

| Method | Description |
|--------|-------------|
| **ISO (Recommended)** | Bootable USB — complete OS, no installation needed |
| **Docker** | Try without rebooting |
| **APT (Optional)** | Install Vajra tools on existing Linux |

## Features

- **Complete OS** — Custom kernel, desktop, file system, package manager
- **Buddhi AI (बुद्धि)** — Built-in AI assistant, runs 100% locally
- **Privacy First** — No tracking, no telemetry, Tor integration
- **Indian at Core** — GST, Panchang, Vedic math, Ayurveda, IRCTC
- **Beginner & Pro Modes** — Safety guardrails for new users
- **10 Indian Languages** — Hindi, Tamil, Bengali, Gujarati, Punjabi, Kannada, Telugu, Malayalam, Marathi, Sanskrit
- **Cybersecurity Tools** — Pentesting suite with ethical usage guides
- **Full Branding Suite** — Plymouth boot splash, GRUB theme, icon set (16–512 px), wallpapers
- **6 Native Apps** — Terminal, Files, Monitor, Screenshot, App Store, Settings

## Quick Start

```bash
# Download and burn ISO to USB
dd if=vajra-os-1.0-amd64.iso of=/dev/sdX bs=4M status=progress

# Boot from USB — that's it!
```

## Repository Structure

```
vajra-os/
├── core/           → 16 core OS tools (process, memory, filesystem managers)
├── ai/             → Buddhi AI assistant
├── packaging/      → Debian package builds + GPG signing key
├── iso/            → Bootable ISO builder scripts
├── installer/      → Calamares installer configuration
├── live-build/     → Full desktop ISO build config
├── docker/         → Docker rootfs
├── branding/       → Plymouth splash, GRUB theme, icons, wallpapers
├── desktop/        → Desktop environment configs
├── system/         → Login banners, system configs
├── systemd/        → Boot services, timers
├── polkit/         → Beginner/Pro mode policies
├── web/            → Landing page (deployed to GitHub Pages)
├── apt-repo/       → APT repository metadata
├── kernel/         → Kernel module configs
├── security/       → Cybersecurity tools
├── privacy/        → Tor, VPN configs
├── network/        → Network management
├── locale/         → Indian language support
├── unique/         → GST, Panchang, Ayurveda, Vedic math, IRCTC
├── finance/        → Financial tools
├── education/      → Educational tools
├── accessibility/  → Accessibility tools
├── apps/           → Built-in applications
├── audio/          → Audio system configs
├── files/          → File management tools
├── graphics/       → Graphics tools
├── settings/       → System settings
├── developer/      → Development tools
├── devops/         → DevOps tools
├── infrastructure/ → Infrastructure management
├── creative/       → Creative tools
├── social/         → Communication tools
├── gaming/         → Gaming tools
├── scripts/        → Utility scripts
├── docs/           → Documentation
└── .github/        → CI/CD workflows (ISO build, Pages deploy, Release)
```

## Packages

| Package | Description |
|---------|-------------|
| vajra-core | Core OS utilities |
| vajra-buddhi-ai | AI assistant |
| vajra-security-center | Security tools |
| vajra-control-center | System settings |
| vajra-package-manager | Package manager |
| vajra-update-manager | Update manager |
| vajra-keyring | GPG signing key |
| vajra-desktop | Desktop meta-package |
| vajra-wallpapers | Official wallpapers |

## Documentation

- [INSTALL.md](INSTALL.md) — Installation guide
- [BUILD.md](BUILD.md) — Build from source
- [RELEASE_NOTES.md](RELEASE_NOTES.md) — Release history

## License

MIT License — Free and Open Source

## Made in India 🇮🇳

---

*Dharma protects those who protect it.*
