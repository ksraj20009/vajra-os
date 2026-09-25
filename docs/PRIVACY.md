# Vajra OS Privacy Stack

Vajra OS is privacy-first by design: no telemetry, no tracking, no
cloud accounts, and an AI assistant that runs entirely on your machine.

## What ships in `privacy/`

| Tool | What it does |
|------|--------------|
| `tor-decision-center.sh` | Interactive guide for routing traffic through Tor |
| `setup-tor-proxy.sh` | Sets up a local Tor SOCKS proxy |
| `torrc` | Hardened Tor configuration template |
| `vajra-tor.service` | systemd unit for the Tor daemon |
| `harden.sh` | Applies the full privacy hardening set (DNS, browser prefs, kernel sysctls) |
| `dns.conf` | Encrypted DNS (DNS-over-TLS via Quad9/Cloudflare) — see below |
| `browser-privacy-setup.sh` | Firefox hardening (pref overrides, no prefetch, no telemetry) |
| `gpg-email-encryption.sh` | Sets up GPG keys and email encryption |
| `encrypted-cloud-backup.sh` | Encrypted backups (LUKS/gocryptfs style) |
| `secure-file-shredder.sh` | Overwrite files before deletion |
| `password-manager-setup.sh` | Local password manager (pass-style) |
| `privacy-dashboard.sh` | One screen: what is listening, phoning, or resolving |

## DNS

`privacy/dns.conf` configures DNS-over-TLS on installed systems
(install to `/etc/systemd/resolved.conf.d/vajra-dns.conf`). In the live
session, point `/etc/resolv.conf` at Quad9 manually:

```sh
echo "nameserver 9.9.9.9" > /etc/resolv.conf
```

## Kernel-level protections

The custom kernel (`kernel/configs/vajra.config`) builds in:

- KASLR (address-space randomization) and randomize_kstack_offset
- Strict kernel/module RWX, page-table isolation, retpolines
- Module signature enforcement (SHA-256)
- AppArmor + YAMA + lockdown LSM support
- Network namespaces for container/Tor isolation

## The AI is local

`privacy_mode: local-only` in the AI config is structural: Buddhi has no
inference network client. See [AI_CONFIG.md](AI_CONFIG.md).

## Tor, quickly

```sh
sudo privacy/setup-tor-proxy.sh          # local SOCKS proxy on 9050
torify firefox                            # or route specific apps
```

## What we do NOT do

- No telemetry, no crash reporting, no update pings beyond APT
- No preinstalled accounts or cloud sync
- No search-engine deals; the browser's default engine is set locally

**धर्मो रक्षति रक्षितः** — Dharma protects those who protect it.
