# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| v1.0.0 (main) | ✅ |

## Reporting a vulnerability

**Please do not open public issues for security vulnerabilities.**

Use GitHub's **private vulnerability reporting** instead —
on GitHub go to this repository → **Security** tab →
**Report a vulnerability**. Reports go only to the maintainer.

If private reporting is unavailable to you, open a regular issue
asking for a security contact **without including vulnerability
details**, and a private channel will be arranged.

Please include:

- What you found, and the component (ISO, kernel config, a tool,
  the APT repository, the website)
- Step-by-step reproduction (boot method, exact commands)
- Impact, and any mitigations you see

This is a community project; fixes are on a best-effort basis, but
reports are triaged promptly.

## Scope

**In scope:**

- `kernel/` — the Vajra kernel config and patches
- `core/`, `ai/`, and all tool scripts shipped in the ISO or packages
- `iso/` — ISO/initramfs build
- `packaging/` and the published APT repository
- The website on GitHub Pages

**Out of scope:**

- Vulnerabilities in the upstream Linux kernel itself — report those
  to the kernel security team (https://www.kernel.org/doc/html/latest/process/security-bugs.html)
- Vulnerabilities in BusyBox, GRUB, ISOLINUX — report upstream
- Theoretical issues requiring already-root access to the live session
  (the live ISO is a single-user console by design)

## Security features already in place

- Hardened kernel config (`kernel/configs/vajra.config`): KASLR, strict
  RWX, module signature enforcement, stack initialization
- APT repository signed with a persistent GPG key; every release asset
  ships with a `.sha256` checksum
- No telemetry, no cloud calls — Buddhi AI runs fully locally
