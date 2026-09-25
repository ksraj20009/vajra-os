# Vajra OS Troubleshooting

## Boot problems

**USB stick won't boot**
- BIOS machine: make sure USB-HDD boot is enabled in the firmware menu.
- UEFI machine: try the other USB port; some firmware only scans USB2
  ports for boot.
- The ISO boots four ways (BIOS/UEFI × CD/USB). If the stick fails, try
  a CD burn — that isolates stick vs firmware issues.
- Very old BIOS (<2010): use the `vajra-serial` boot option or a CD.

**Black screen, no output**
- Boot with the `vajra-serial` label (ISOLINUX menu) and connect a
  serial console, or in QEMU add `-serial file:log.txt`.

**UEFI shows "No bootable device" after dd**
- Re-run the dd — an incomplete copy is the usual cause (`sync` before
  unplugging!). Verify the stick size matches the ISO (32.5 MB is wrong —
  check your stick shows the full capacity).

## Live system

**No network**
```sh
udhcpc -i eth0                  # DHCP (also runs automatically at boot)
ip link                          # is your NIC present/UP?
```

**A tool is missing** — `vajra-tools` lists everything shipped; BusyBox
provides another 396 standard commands (`busybox --list`).

**Forgot what exists** — `vajra-help`.

## Install problems

**`vajra-install` refuses a disk** — it never installs onto the media you
booted from; pick another disk.

**Installed system doesn't boot** — the installer writes boot configs to
the new partition and its final screen explains the one manual step
(installing the bootloader boot block from any Linux rescue
environment). Boot the live USB again and re-run `vajra-install`.

## Docker

```bash
docker import vajra-os-rootfs.tar.gz vajra-os:1.0
docker run -it vajra-os:1.0
```
If `docker import` complains about the file, re-download — compare the
size against the release page.

## APT

**NO_PUBKEY / signature errors**
```bash
curl -fsSL https://raw.githubusercontent.com/ksraj20009/vajra-os/gh-pages/apt-repo/vajra-archive-keyring.asc \
  | gpg --dearmor -o /usr/share/keyrings/vajra-archive-keyring.gpg
sudo apt update
```
The key is persistent — the fingerprint
`5607 5607 3ECC 64AD 45C1 99C0 3212 D97D DE0C CA4A` never changes
between releases, so a one-time import keeps working.

**"Release file not valid yet"** — your clock is wrong; fix the system
time (`timedatectl set-ntp true`).

## Reporting a bug

Open an issue at the repo with: what you did, what happened, and the
serial log if it is a boot problem (`vajra-serial` boot option).
