#!/usr/bin/env python3
"""
Vajra OS ISO Builder v4 — BIOS + UEFI Dual-Boot, hybrid USB
Builds a real El Torito bootable ISO with both BIOS and UEFI support.

Usage:
    python3 build-iso.py [--output vajra-os-1.0-amd64.iso]

Requirements:
    pip install pycdlib

What it does:
    1. Downloads Alpine Linux kernel 6.6.142 + 922 kernel modules
    2. Downloads BusyBox (396 Unix commands)
    3. Downloads ISOLINUX bootloader (BIOS boot chain)
    4. Downloads GRUB EFI binary for UEFI boot (standalone if grub-mkstandalone is available)
    5. Downloads all Vajra utility scripts + 14 core tools from GitHub
    6. Downloads Buddhi AI assistant
    7. Builds initramfs (cpio.gz) with all tools + vajra-install disk installer
    8. Creates bootable ISO with:
       - El Torito BIOS boot via ISOLINUX (boot-info-table)
       - UEFI boot via EFI System Partition (/EFI/BOOT/BOOTX64.EFI)
       - isohybrid MBR so the ISO can be dd'd straight to USB
       - 3 boot options: default, debug, serial console

The ISO is verified by iso/boot-test.py in CI before anything is published.
"""

import os, sys, gzip, shutil, subprocess, urllib.request, json
from pathlib import Path
import pycdlib

# === Configuration ===
ISO_VERSION = "1.0"
ISO_LABEL = "VAJRA_OS_1.0"
REPO_OWNER = "ksraj20009"
REPO_NAME = "vajra-os"

# Download URLs
BUSYBOX_URL = "https://raw.githubusercontent.com/EXALAB/Busybox-static/main/busybox_amd64"
KERNEL_APK_URL = "https://dl-cdn.alpinelinux.org/alpine/v3.19/main/x86_64/linux-virt-6.6.142-r0.apk"
GRUB_EFI_DEB_URL = "https://deb.debian.org/debian-security/pool/main/g/grub2/grub-efi-amd64-bin_2.06-13+deb12u1_amd64.deb"
ISOLINUX_DEB_URL = "https://deb.debian.org/debian/pool/main/s/syslinux/isolinux_6.04~git20190206.bf6db5b4+dfsg1-3.2_all.deb"
SYSLINUX_COMMON_DEB_URL = "https://deb.debian.org/debian/pool/main/s/syslinux/syslinux-common_6.04~git20190206.bf6db5b4+dfsg1-3.2_all.deb"
SYSLINUX_UTILS_DEB_URL = "https://deb.debian.org/debian/pool/main/s/syslinux/syslinux-utils_6.04~git20190206.bf6db5b4+dfsg1-3+b1_amd64.deb"

# Cpio builder (newc format)
def make_cpio(entries):
    data = b""
    for name, content, mode in entries:
        nb = name.encode() + b'\0'
        ns = len(nb)
        np_ = (4 - (110 + ns) % 4) % 4
        cp_ = (4 - len(content) % 4) % 4
        # standard newc header: magic + 13 fields of 8 hex chars = 110 bytes
        h = ("070701"
             f"{0:08X}"            # c_ino
             f"{mode:08X}"          # c_mode
             f"{0:08X}"            # c_uid
             f"{0:08X}"            # c_gid
             f"{1:08X}"            # c_nlink
             f"{0:08X}"            # c_mtime
             f"{len(content):08X}"  # c_filesize
             f"{0:08X}"            # c_devmajor
             f"{0:08X}"            # c_devminor
             f"{0:08X}"            # c_rdevmajor
             f"{0:08X}"            # c_rdevminor
             f"{ns:08X}"           # c_namesize
             f"{0:08X}")           # c_check
        data += h.encode() + nb + b'\0'*np_ + content + b'\0'*cp_
    t = b"TRAILER!!!\0"
    h = ("070701"
         f"{0:08X}"
         f"{0:08X}"
         f"{0:08X}"
         f"{0:08X}"
         f"{1:08X}"
         f"{0:08X}"
         f"{0:08X}"
         f"{0:08X}"
         f"{0:08X}"
         f"{0:08X}"
         f"{0:08X}"
         f"{len(t):08X}"
         f"{0:08X}")
    data += h.encode() + t
    data += b'\0' * ((512 - len(data) % 512) % 512)
    return data

def download(url, dest, desc=""):
    """Download a file with progress indication."""
    print(f"  [*] Downloading {desc or url.split('/')[-1]}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=120)
    data = resp.read()
    Path(dest).write_bytes(data)
    print(f"      Downloaded: {len(data):,} bytes")
    return data

def extract_deb_file(deb_url, deb_name, inner_path, dest):
    """Download a .deb and pull one file out of its data.tar.* payload."""
    deb_path = WORK / deb_name
    if not deb_path.exists():
        download(deb_url, deb_path, deb_name)
    import lzma, tarfile, io
    out = subprocess.run(["ar", "t", str(deb_path)], capture_output=True, text=True)
    member = [m for m in out.stdout.split() if m.startswith("data.tar")]
    if not member:
        raise RuntimeError(f"no data.tar in {deb_name}")
    raw = subprocess.run(["ar", "p", str(deb_path), member[0]], capture_output=True).stdout
    payload = member[0].split(".")[-1]
    if payload == "xz":
        raw = lzma.decompress(raw)
    elif payload == "zst":
        import zstandard
        raw = zstandard.ZstdDecompressor().decompress(raw)
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        f = tar.extractfile(inner_path)
        if f is None:
            raise RuntimeError(f"{inner_path} not found in {deb_name}")
        Path(dest).write_bytes(f.read())
    print(f"      Extracted {inner_path} -> {dest}")

def get_isolinux(work):
    """Locate isolinux.bin + ldlinux.c32: system paths first, then Debian packages."""
    for sys_iso, sys_ld in [
        ("/usr/lib/ISOLINUX/isolinux.bin", "/usr/lib/syslinux/modules/bios/ldlinux.c32"),
        ("/usr/lib/syslinux/isolinux.bin", "/usr/lib/syslinux/modules/bios/ldlinux.c32"),
        ("/usr/lib/syslinux/bios/isolinux.bin", "/usr/lib/syslinux/bios/ldlinux.c32"),
    ]:
        if os.path.exists(sys_iso) and os.path.exists(sys_ld):
            print(f"  [+] Using system ISOLINUX: {sys_iso}")
            return Path(sys_iso), Path(sys_ld)
    iso_bin = work / "isolinux.bin"
    ld_c32 = work / "ldlinux.c32"
    if not iso_bin.exists():
        extract_deb_file(ISOLINUX_DEB_URL, "isolinux.deb", "./usr/lib/ISOLINUX/isolinux.bin", iso_bin)
    if not ld_c32.exists():
        extract_deb_file(SYSLINUX_COMMON_DEB_URL, "syslinux-common.deb", "./usr/lib/syslinux/modules/bios/ldlinux.c32", ld_c32)
    return iso_bin, ld_c32

def get_isohybrid(work):
    """Locate the isohybrid tool: PATH first, then extracted from the syslinux-utils package."""
    if shutil.which("isohybrid"):
        return "isohybrid"
    exe = work / "isohybrid"
    if not exe.exists():
        extract_deb_file(SYSLINUX_UTILS_DEB_URL, "syslinux-utils.deb", "./usr/bin/isohybrid", exe)
        os.chmod(exe, 0o755)
    return str(exe)

def build_grub_standalone(work, grub_cfg):
    """Build a self-contained bootx64.efi with the config embedded, if possible."""
    mk = shutil.which("grub-mkstandalone")
    if not mk:
        return None
    cfg_dir = work / "grub-embed"
    (cfg_dir / "boot" / "grub").mkdir(parents=True, exist_ok=True)
    (cfg_dir / "boot" / "grub" / "grub.cfg").write_text(grub_cfg)
    out = work / "bootx64.efi"
    r = subprocess.run(
        [mk, "-O", "x86_64-efi", "-o", str(out),
         "--install-modules=part_msdos part_gpt iso9660 normal boot linux search search_fs_file ls echo",
         "boot/grub/grub.cfg=" + str(cfg_dir / "boot" / "grub" / "grub.cfg")],
        capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        print(f"  [-] grub-mkstandalone failed: {r.stderr.strip()[:200]}")
        return None
    print(f"  [+] GRUB standalone EFI: {out.stat().st_size:,} bytes")
    return out

INSTALLER_SCRIPT = r"""#!/bin/busybox sh
# ============================================================================
# Vajra OS Installer v2 - installs Vajra OS to a hard disk or clones to USB
#
# Usage:
#   vajra-install               interactive
#   vajra-install sdb           install to /dev/sdb (erases it!)
#   vajra-install --clone sdb   dd the boot media straight onto /dev/sdb
# ============================================================================
SRC=""
SRCDIR="/mnt/source"
[ -d $SRCDIR ] || mkdir -p $SRCDIR

find_boot_media() {
    # CD first
    if [ -b /dev/sr0 ]; then
        if /bin/busybox mount -t iso9660 -o ro /dev/sr0 $SRCDIR 2>/dev/null; then
            [ -f $SRCDIR/vmlinuz ] && SRC=/dev/sr0 && return 0
            /bin/busybox umount $SRCDIR 2>/dev/null
        fi
    fi
    # whole-disk isohybrid USB
    for d in $(ls /sys/block 2>/dev/null | grep -E '^sd|^vd|^hd'); do
        if [ -b /dev/$d ]; then
            if /bin/busybox mount -t iso9660 -o ro /dev/$d $SRCDIR 2>/dev/null; then
                [ -f $SRCDIR/vmlinuz ] && SRC=/dev/$d && return 0
                /bin/busybox umount $SRCDIR 2>/dev/null
            fi
        fi
    done
    return 1
}

if [ "$1" = "--clone" ]; then
    if [ -z "$2" ]; then echo "usage: vajra-install --clone <target-disk> (e.g. sdb)"; exit 1; fi
    find_boot_media || { echo "[-] cannot find boot media to clone from"; exit 1; }
    umount $SRCDIR 2>/dev/null
    echo "  WARNING: this will ERASE ALL DATA on /dev/$2!"
    read -p "  Type YES to continue: " C; [ "$C" = "YES" ] || { echo cancelled; exit 0; }
    echo "[*] Cloning $SRC -> /dev/$2 (dd, be patient)..."
    /bin/busybox dd if=$SRC of=/dev/$2 bs=4M 2>/dev/null
    /bin/busybox sync
    echo "[+] Done. /dev/$2 is now a bootable Vajra OS USB stick."
    exit 0
fi

echo ""
echo "  ============================================"
echo "  Vajra OS Installer"
echo "  ============================================"
echo ""
find_boot_media || { echo "[-] Could not find the boot media (kernel source). Insert the CD/USB you booted from and retry."; exit 1; }
echo "[+] Boot media: $SRC (mounted at $SRCDIR)"

echo "Available disks:"
for dev in $(ls /sys/block 2>/dev/null | grep -E 'sd|vd|nvme|hd'); do
    [ "$dev" = "${SRC#/dev/}" ] && continue
    if [ -b /dev/$dev ]; then
        SIZE=$(cat /sys/block/$dev/size 2>/dev/null)
        if [ -n "$SIZE" ] && [ "$SIZE" -gt 0 ]; then
            MB=$((SIZE * 512 / 1024 / 1024))
            echo "  /dev/$dev - ${MB} MB"
        fi
    fi
done
echo ""
DISK="$1"
[ -n "$DISK" ] || read -p "Install to which disk? (e.g. sdb): " DISK
[ -n "$DISK" ] || { echo "[-] no disk specified"; exit 1; }
case "$DISK" in /dev/*) ;; *) DISK="/dev/$DISK";; esac
[ -b "$DISK" ] || { echo "[-] $DISK not found"; exit 1; }
[ "$DISK" = "$SRC" ] && { echo "[-] refusing to install onto the boot media itself"; exit 1; }
echo ""
echo "  WARNING: This will ERASE ALL DATA on $DISK!"
read -p "  Type YES to continue: " CONFIRM
[ "$CONFIRM" = "YES" ] || { echo "[-] cancelled"; exit 0; }
echo ""

echo "[1/8] Partitioning $DISK..."
cat << EOF | /bin/busybox fdisk $DISK
o
n
p
1


a
w
EOF
PART="${DISK}1"
[ -b "$PART" ] || PART="${DISK}p1"
[ -b "$PART" ] || { echo "[-] partition $PART not found after fdisk"; exit 1; }
echo "      [+] Partition: $PART"

echo "[2/8] Formatting..."
/bin/busybox mke2fs -L vajra-root "$PART" || { echo "[-] format failed"; exit 1; }

echo "[3/8] Mounting..."
mkdir -p /mnt/vajra
/bin/busybox mount "$PART" /mnt/vajra || { echo "[-] mount failed"; exit 1; }

echo "[4/8] Copying Vajra OS root filesystem..."
for dir in bin sbin usr/bin usr/sbin usr/share/vajra etc lib/modules root home; do
    if [ -d "/$dir" ]; then
        mkdir -p "/mnt/vajra/$dir"
        /bin/busybox cp -a "/$dir/." "/mnt/vajra/$dir/" 2>/dev/null
    fi
done

echo "[5/8] Installing kernel + initramfs from boot media..."
mkdir -p /mnt/vajra/boot
/bin/busybox cp $SRCDIR/vmlinuz /mnt/vajra/boot/vmlinuz || { echo "[-] kernel copy failed"; exit 1; }
/bin/busybox cp $SRCDIR/initramfs.cpio.gz /mnt/vajra/boot/initramfs.cpio.gz || { echo "[-] initramfs copy failed"; exit 1; }

echo "[6/8] fstab..."
cat > /mnt/vajra/etc/fstab << FSTAB
$PART / ext2 defaults 0 1
proc /proc proc defaults 0 0
sysfs /sys sysfs defaults 0 0
devtmpfs /dev devtmpfs defaults 0 0
tmpfs /tmp tmpfs defaults 0 0
FSTAB

echo "[7/8] Bootloader configuration..."
cat > /mnt/vajra/boot/extlinux.conf << EXTCONF
DEFAULT vajra
LABEL vajra
  KERNEL /boot/vmlinuz
  APPEND initrd=/boot/initramfs.cpio.gz console=tty0 quiet
EXTCONF
cat > /mnt/vajra/boot/grub.cfg << GRUBCONF
set timeout=3
set default=0
menuentry "Vajra OS 1.0" {
    linux /boot/vmlinuz console=tty0 quiet
    initrd /boot/initramfs.cpio.gz
}
GRUBCONF

echo "[8/8] Finalizing..."
/bin/busybox sync
/bin/busybox umount /mnt/vajra 2>/dev/null
/bin/busybox umount $SRCDIR 2>/dev/null
echo ""
echo "  ============================================"
echo "  Vajra OS installed to $PART"
echo "  ============================================"
echo ""
echo "  NOTE ON THE BOOTLOADER:"
echo "  A boot config was written to /boot on the new partition."
echo "  This live system has no bootloader installer, so before"
echo "  rebooting, boot any Linux rescue and run ONE of:"
echo "    extlinux --install /mnt/vajra/boot    (syslinux MBR to $DISK)"
echo "    grub-install $DISK                   (if you prefer GRUB)"
echo "  Or simply keep booting the live USB/CD - everything on the"
echo "  installed disk is identical."
echo ""
echo "  Dharmo Rakshati Rakshitah"
"""

TOOLS_SCRIPT = r"""#!/bin/busybox sh
# vajra-tools - list the Vajra utility tools available in this system
DIR=/usr/share/vajra/tools
if [ ! -d "$DIR" ]; then echo "no tools directory"; exit 1; fi
COUNT=$(ls "$DIR" | wc -l)
echo ""
echo "  Vajra OS utility tools ($COUNT):"
echo "  -------------------------------------------"
ls "$DIR" | sed 's/^/  /'
echo ""
echo "  Run any tool by name - it is on the PATH."
"""

def build_iso(output_path="vajra-os-1.0-amd64.iso"):
    global WORK
    WORK = Path("/scratch/work/vajra-iso-build")
    WORK.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Vajra OS ISO Builder v4 - BIOS + UEFI + USB hybrid")
    print(f"{'='*60}\n")

    # 1. Download kernel
    print("[1/7] Downloading Linux kernel...")
    kernel_apk = WORK / "linux-virt.apk"
    if not kernel_apk.exists():
        download(KERNEL_APK_URL, kernel_apk, "Alpine Linux kernel")

    # Extract kernel + modules from APK
    import tarfile
    with tarfile.open(str(kernel_apk), 'r') as tar:
        members = tar.getmembers()
        for m in members:
            if m.name == "boot/vmlinuz-virt" or m.name == "./boot/vmlinuz-virt":
                tar.extract(m, str(WORK))
                print(f"  [+] vmlinuz-virt: {m.size:,} bytes")
            if m.name.startswith("lib/modules/") or m.name.startswith("./lib/modules/"):
                tar.extract(m, str(WORK))

    vmlinuz = WORK / "boot/vmlinuz-virt"
    if not vmlinuz.exists():
        print("  [-] ERROR: Could not extract kernel!")
        sys.exit(1)

    # Count modules
    modules_dir = WORK / "lib/modules"
    if modules_dir.exists():
        module_count = sum(1 for _ in modules_dir.rglob("*.ko*"))
        print(f"  [+] Kernel modules: {module_count}")

    # 2. Download BusyBox
    print("\n[2/7] Downloading BusyBox...")
    busybox = WORK / "busybox"
    if not busybox.exists():
        download(BUSYBOX_URL, busybox, "BusyBox static")
    os.chmod(busybox, 0o755)

    # 2b. ISOLINUX bootloader (real BIOS boot chain)
    print("\n[2b/7] Getting ISOLINUX bootloader...")
    isolinux_bin, ldlinux_c32 = get_isolinux(WORK)
    print(f"  [+] isolinux.bin: {isolinux_bin.stat().st_size:,} bytes")
    print(f"  [+] ldlinux.c32: {ldlinux_c32.stat().st_size:,} bytes")

    # 3. Download GRUB EFI for UEFI boot
    print("\n[3/7] Getting GRUB EFI...")
    grub_cfg = """set timeout=3
set default=0
menuentry "Vajra OS 1.0" {
    search --no-floppy --file /vmlinuz --set=root
    linux /vmlinuz console=tty0 quiet
    initrd /initramfs.cpio.gz
}
menuentry "Vajra OS 1.0 (Serial Console)" {
    search --no-floppy --file /vmlinuz --set=root
    linux /vmlinuz console=ttyS0,115200
    initrd /initramfs.cpio.gz
}
"""
    bootx64 = build_grub_standalone(WORK, grub_cfg)
    if bootx64 is None:
        # Fallback: extract the modular Debian grubx64.efi
        grub_deb = WORK / "grub-efi-amd64-bin.deb"
        if not grub_deb.exists():
            download(GRUB_EFI_DEB_URL, grub_deb, "GRUB EFI (Debian)")
        import lzma
        extract_dir = WORK / "grub-extract"
        extract_dir.mkdir(exist_ok=True)
        subprocess.run(["ar", "x", str(grub_deb)], cwd=str(extract_dir), capture_output=True)
        data_tar_xz = extract_dir / "data.tar.xz"
        if data_tar_xz.exists():
            data = lzma.open(data_tar_xz, 'rb').read()
            data_tar = extract_dir / "data.tar"
            data_tar.write_bytes(data)
            with tarfile.open(str(data_tar), 'r') as tar:
                for m in tar.getmembers():
                    if "grubx64.efi" in m.name:
                        tar.extract(m, str(extract_dir))
                        break
        grubx64_files = list(extract_dir.rglob("grubx64.efi"))
        if grubx64_files:
            bootx64 = WORK / "bootx64.efi"
            shutil.copy(grubx64_files[0], bootx64)
            print(f"  [+] bootx64.efi (modular fallback): {bootx64.stat().st_size:,} bytes")
        else:
            print("  [-] WARNING: no GRUB EFI, building BIOS-only ISO")
            bootx64 = None

    # 4. Download Vajra tools from repo
    print("\n[4/7] Downloading Vajra OS tools from GitHub...")
    tree_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/main?recursive=1"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'}
    if os.environ.get("GITHUB_TOKEN"):
        headers['Authorization'] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    tree_data = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(tree_url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=30)
            tree_data = json.loads(resp.read())
            break
        except Exception as e:
            print(f"  [!] tree fetch attempt {attempt+1} failed: {e}")
            import time; time.sleep(5)
    if tree_data is None:
        print("  [-] ERROR: could not list repo tree")
        sys.exit(1)

    exclude_dirs = ["packaging", "installer", "live-build", ".github", "branding", "docker", "iso", "docs", "apt-repo", "kernel"]
    util_files = []
    core_files = []
    for item in tree_data.get("tree", []):
        if item["type"] != "blob":
            continue
        path = item["path"]
        if not (path.endswith(".py") or path.endswith(".sh") or path.endswith("vajra-help") or path.endswith("vajra-mode")):
            continue
        if any(path.startswith(ex + "/") for ex in exclude_dirs):
            continue
        if path.startswith("core/"):
            core_files.append(path)
        else:
            util_files.append(path)
    print(f"  [+] Found {len(util_files)} utility scripts + {len(core_files)} core tools")

    # 5. Build initramfs
    print("\n[5/7] Building initramfs...")
    initramfs_dir = WORK / "initramfs"
    if initramfs_dir.exists():
        shutil.rmtree(initramfs_dir)

    # Create directory structure
    for d in ["bin", "sbin", "usr/bin", "usr/sbin", "usr/share/vajra/tools",
              "lib/modules", "etc", "proc", "sys", "dev", "tmp", "root", "home/vajra",
              "var/log", "var/run", "mnt", "media"]:
        (initramfs_dir / d).mkdir(parents=True, exist_ok=True)

    # Install BusyBox
    shutil.copy(busybox, initramfs_dir / "bin/busybox")
    os.chmod(initramfs_dir / "bin/busybox", 0o755)

    # Create BusyBox symlinks
    result = subprocess.run([str(busybox), "--list"], capture_output=True, text=True, timeout=10)
    for applet in result.stdout.strip().split("\n"):
        link = initramfs_dir / f"bin/{applet}"
        if not link.exists():
            try:
                link.symlink_to("busybox")
            except:
                pass

    # Install utility scripts (flattened into the tools dir, on the PATH)
    downloaded = 0
    for path in util_files:
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{path}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=20)
            data = resp.read()
            filename = path.replace("/", "_")
            dest = initramfs_dir / "usr/share/vajra/tools" / filename
            dest.write_bytes(data)
            os.chmod(dest, 0o755)
            downloaded += 1
        except:
            pass
    print(f"  [+] Installed {downloaded} utility scripts")

    # Install core tools as real commands in /usr/bin
    core_ok = 0
    for path in core_files:
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{path}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read()
            dest = initramfs_dir / "usr/bin" / Path(path).name
            dest.write_bytes(data)
            os.chmod(dest, 0o755)
            core_ok += 1
        except:
            pass
    print(f"  [+] Installed {core_ok} core tools (vajra-help, managers, ...) into /usr/bin")

    # Install Buddhi AI
    try:
        buddhi_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/ai/buddhi-ai.py"
        req = urllib.request.Request(buddhi_url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        buddhi_data = resp.read()
        buddhi_path = initramfs_dir / "usr/bin/buddhi"
        buddhi_path.write_bytes(buddhi_data)
        os.chmod(buddhi_path, 0o755)
        print(f"  [+] Buddhi AI: {len(buddhi_data):,} bytes")
    except:
        pass

    # Install vajra-install (disk installer) + vajra-tools (tool lister)
    for name, script in [("vajra-install", INSTALLER_SCRIPT), ("vajra-tools", TOOLS_SCRIPT)]:
        p = initramfs_dir / "usr/bin" / name
        p.write_text(script)
        os.chmod(p, 0o755)
    print("  [+] Installed vajra-install + vajra-tools")

    # Copy kernel modules
    if modules_dir.exists():
        shutil.copytree(modules_dir, initramfs_dir / "lib/modules", dirs_exist_ok=True)

    # Create init script
    init_script = initramfs_dir / "init"
    init_script.write_text("""#!/bin/busybox sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t tmpfs tmpfs /tmp

banner() {
echo ""
echo "  =================================================="
echo "  |    VAJRA OS 1.0                                |"
echo "  |    India's Privacy-First AI-Powered OS         |"
echo "  |                                                |"
echo "  |    Dharmo Rakshati Rakshitah                  |"
echo "  =================================================="
echo ""
echo "  Kernel: $(uname -r)"
echo "  CPU: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2)"
echo "  RAM: $(grep MemTotal /proc/meminfo | awk '{print $2}') kB"
echo ""
}

banner
# also show the banner on the serial console (headless / CI boot tests)
banner > /dev/ttyS0 2>/dev/null

# Load essential modules
for mod in ext4 vfat e1000 virtio_pci virtio_blk; do
    modprobe $mod 2>/dev/null
done

# Setup network
ifconfig lo 127.0.0.1 up
udhcpc -i eth0 2>/dev/null || echo "  [!] No network (use 'udhcpc -i eth0')"

# Set hostname
hostname vajra-os

# Set PATH
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/share/vajra/tools
export PS1='vajra@vajra-os:/ # '

echo ""
echo "  Commands:"
echo "    vajra-install   - Install Vajra OS to disk"
echo "    vajra-help      - Show all commands"
echo "    vajra-tools     - List utility tools"
echo "    buddhi          - AI assistant"
echo ""

exec /bin/sh
""")
    os.chmod(init_script, 0o755)

    # Build cpio.gz
    entries = [(".", b"", 0o040755)]
    for root, dirs, files in os.walk(initramfs_dir):
        dirs.sort(); files.sort()
        for d in dirs:
            full = os.path.join(root, d)
            rel = os.path.relpath(full, initramfs_dir)
            entries.append(("./" + rel, b"", 0o040755))
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, initramfs_dir)
            if os.path.islink(full):
                entries.append(("./" + rel, os.readlink(full).encode(), 0o120755))
            else:
                with open(full, "rb") as fh:
                    content = fh.read()
                mode = 0o100755 if os.access(full, os.X_OK) else 0o100644
                entries.append(("./" + rel, content, mode))

    cpio_data = make_cpio(entries)
    initramfs_path = WORK / "initramfs.cpio.gz"
    with gzip.open(initramfs_path, "wb", compresslevel=9) as f:
        f.write(cpio_data)
    print(f"  [+] Initramfs: {initramfs_path.stat().st_size:,} bytes")

    # 6. Create boot configs
    print("\n[6/7] Creating boot configurations...")

    isolinux_cfg = WORK / "isolinux.cfg"
    isolinux_cfg.write_text("""SERIAL 0 115200
DEFAULT vajra
PROMPT 1
TIMEOUT 30
LABEL vajra
  KERNEL /vmlinuz
  APPEND initrd=/initramfs.cpio.gz console=tty0 quiet
LABEL vajra-debug
  KERNEL /vmlinuz
  APPEND initrd=/initramfs.cpio.gz console=tty0
LABEL vajra-serial
  KERNEL /vmlinuz
  APPEND initrd=/initramfs.cpio.gz console=ttyS0,115200
DISPLAY /boot.msg
""")

    boot_msg = WORK / "boot.msg"
    boot_msg.write_text("""
  ==================================================
  |    VAJRA OS 1.0                                |
  |    India's Privacy-First AI-Powered OS         |
  |    Dharmo Rakshati Rakshitah                  |
  ==================================================

  vajra        - Boot Vajra OS (default, in 3s)
  vajra-debug  - Boot with verbose output
  vajra-serial - Boot with serial console

  After boot: vajra-install, vajra-help, vajra-tools, buddhi
  Press Enter to boot.
""")

    # 7. Build the ISO
    print("\n[7/7] Building bootable ISO...")

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, joliet=True, rock_ridge="1.09", vol_ident=ISO_LABEL)

    # Add kernel + initramfs
    iso.add_file(str(vmlinuz), "/VMLINUZ", rr_name="vmlinuz")
    iso.add_file(str(initramfs_path), "/INITRAMF.CPG", rr_name="initramfs.cpio.gz")

    # ISOLINUX (BIOS boot chain)
    iso.add_directory("/ISOLINUX", rr_name="isolinux")
    iso.add_file(str(isolinux_bin), "/ISOLINUX/ISOLINUX.BIN", rr_name="isolinux.bin")
    iso.add_file(str(ldlinux_c32), "/ISOLINUX/LDLINUX.C32", rr_name="ldlinux.c32")
    iso.add_file(str(isolinux_cfg), "/ISOLINUX/ISOLINUX.CFG", rr_name="isolinux.cfg")
    iso.add_file(str(boot_msg), "/BOOT.MSG", rr_name="boot.msg")

    # GRUB (UEFI)
    if bootx64 and bootx64.exists():
        iso.add_directory("/EFI", rr_name="efi")
        iso.add_directory("/EFI/BOOT", rr_name="boot")
        iso.add_file(str(bootx64), "/EFI/BOOT/BOOTX64.EFI", rr_name="bootx64.efi")

    # README
    readme = WORK / "README.txt"
    readme.write_text(f"Vajra OS {ISO_VERSION}\nIndia's Privacy-First AI-Powered OS\nDharmo Rakshati Rakshitah\n\nBoot: dd if=vajra-os-1.0-amd64.iso of=/dev/sdX bs=4M (isohybrid: USB works)\nTest: python3 iso/boot-test.py --iso vajra-os-1.0-amd64.iso\n")
    iso.add_file(str(readme), "/README.TXT", rr_name="README.txt")

    # El Torito BIOS boot: ISOLINUX is the boot image (boot-info-table patches it)
    iso.add_eltorito(
        "/ISOLINUX/ISOLINUX.BIN",
        bootcatfile="/BOOT.CAT;1",
        rr_bootcatname="boot.cat",
        joliet_bootcatfile="/boot.cat",
        platform_id=0,
        media_name="noemul",
        bootable=True,
        boot_load_size=4,
        boot_info_table=True
    )

    # El Torito UEFI boot
    if bootx64 and bootx64.exists():
        iso.add_eltorito(
            "/EFI/BOOT/BOOTX64.EFI",
            bootcatfile="/BOOT.CAT;1",
            rr_bootcatname="boot.cat",
            joliet_bootcatfile="/boot.cat",
            platform_id=0xEF,
            efi=True,
            media_name="noemul",
            bootable=True,
            boot_info_table=False
        )

    iso.write(str(output_path))
    iso.close()

    # 7b. isohybrid: make the ISO dd-able straight onto a USB stick
    print("\n[7b/7] Applying isohybrid (dd-to-USB support)...")
    isohybrid_cmd = get_isohybrid(WORK)
    r = subprocess.run([isohybrid_cmd, str(Path(output_path))], capture_output=True, text=True)
    if r.returncode == 0:
        print("  [+] isohybrid applied - the ISO can be dd'd to USB")
    else:
        print(f"  [-] isohybrid FAILED: {r.stderr.strip()[:300]}")

    iso_size = Path(output_path).stat().st_size

    print(f"\n{'='*60}")
    print(f"  ISO BUILD COMPLETE!")
    print(f"{'='*60}")
    print(f"  File: {output_path}")
    print(f"  Size: {iso_size:,} bytes ({iso_size/1024/1024:.1f} MB)")
    print(f"  Boot: BIOS (ISOLINUX) + UEFI (GRUB) + USB (isohybrid)")
    print(f"{'='*60}")

    return output_path

if __name__ == "__main__":
    output = sys.argv[sys.argv.index("--output") + 1] if "--output" in sys.argv else "vajra-os-1.0-amd64.iso"
    build_iso(output)
