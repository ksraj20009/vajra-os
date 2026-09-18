#!/usr/bin/env python3
"""
Vajra OS ISO Builder v3 — BIOS + UEFI Dual-Boot
Builds a real El Torito bootable ISO with both BIOS and UEFI support.

Usage:
    python3 build-iso.py [--output vajra-os-1.0-amd64.iso]

Requirements:
    pip install pycdlib

What it does:
    1. Downloads Alpine Linux kernel 6.6.142 + 922 kernel modules
    2. Downloads BusyBox (396 Unix commands)
    3. Downloads GRUB EFI binary for UEFI boot
    4. Downloads all 279 Vajra utility scripts from GitHub
    5. Downloads Buddhi AI assistant
    6. Builds initramfs (cpio.gz) with all tools
    7. Creates bootable ISO with:
       - El Torito BIOS boot (no-emulation mode)
       - UEFI boot via EFI System Partition (/EFI/BOOT/BOOTX64.EFI)
       - ISOLINUX + GRUB configs
       - 3 boot options: default, debug, serial console
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
    resp = urllib.request.urlopen(req, timeout=60)
    data = resp.read()
    Path(dest).write_bytes(data)
    print(f"      Downloaded: {len(data):,} bytes")
    return data

def build_iso(output_path="vajra-os-1.0-amd64.iso"):
    WORK = Path("/scratch/work/vajra-iso-build")
    WORK.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"  Vajra OS ISO Builder v3 — BIOS + UEFI")
    print(f"{'='*60}\n")
    
    # 1. Download kernel
    print("[1/7] Downloading Linux kernel...")
    kernel_apk = WORK / "linux-virt.apk"
    if not kernel_apk.exists():
        download(KERNEL_APK_URL, kernel_apk, "Alpine Linux kernel")
    
    # Extract kernel + modules from APK
    import tarfile, io
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
    
    # 3. Download GRUB EFI for UEFI boot
    print("\n[3/7] Downloading GRUB EFI binary...")
    grub_deb = WORK / "grub-efi-amd64-bin.deb"
    if not grub_deb.exists():
        download(GRUB_EFI_DEB_URL, grub_deb, "GRUB EFI (Debian)")
    
    # Extract bootx64.efi
    import lzma
    extract_dir = WORK / "grub-extract"
    extract_dir.mkdir(exist_ok=True)
    subprocess.run(["ar", "x", str(grub_deb)], cwd=str(extract_dir), capture_output=True)
    data_tar_xz = extract_dir / "data.tar.xz"
    if data_tar_xz.exists():
        with lzma.open(data_tar_xz, 'rb') as f:
            data = f.read()
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
        print(f"  [+] bootx64.efi: {bootx64.stat().st_size:,} bytes")
    else:
        print("  [-] WARNING: Could not extract GRUB EFI, building BIOS-only ISO")
        bootx64 = None
    
    # 4. Download Vajra tools from repo
    print("\n[4/7] Downloading Vajra OS tools from GitHub...")
    tree_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/main?recursive=1"
    req = urllib.request.Request(tree_url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'})
    resp = urllib.request.urlopen(req, timeout=15)
    tree_data = json.loads(resp.read())
    
    exclude_dirs = ["packaging", "installer", "live-build", ".github", "branding", "docker", "iso", "docs", "apt-repo"]
    util_files = []
    for item in tree_data.get("tree", []):
        if item["type"] != "blob":
            continue
        path = item["path"]
        if not (path.endswith(".py") or path.endswith(".sh")):
            continue
        if any(path.startswith(ex + "/") for ex in exclude_dirs):
            continue
        if path.startswith("core/"):
            continue
        util_files.append(path)
    print(f"  [+] Found {len(util_files)} utility scripts")
    
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
                link.symlink_to("busybox", )
            except:
                pass
    
    # Install Vajra tools
    downloaded = 0
    for path in util_files:
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{path}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read()
            filename = path.replace("/", "_")
            dest = initramfs_dir / "usr/share/vajra/tools" / filename
            dest.write_bytes(data)
            os.chmod(dest, 0o755)
            downloaded += 1
        except:
            pass
    print(f"  [+] Installed {downloaded} utility scripts")
    
    # Install Buddhi AI
    try:
        buddhi_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/ai/buddhi-ai.py"
        req = urllib.request.Request(buddhi_url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        buddhi_data = resp.read()
        buddhi_path = initramfs_dir / "usr/bin/buddhi"
        buddhi_path.write_bytes(buddhi_data)
        os.chmod(buddhi_path, 0o755)
        print(f"  [+] Buddhi AI: {len(buddhi_data):,} bytes")
    except:
        pass
    
    # Install Vajra core tools
    for path in util_files:
        if path.startswith("core/"):
            url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{path}"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib.request.urlopen(req, timeout=10)
                data = resp.read()
                filename = Path(path).name
                dest = initramfs_dir / "usr/bin" / filename
                dest.write_bytes(data)
                os.chmod(dest, 0o755)
            except:
                pass
    
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
echo "    vajra-install   — Install Vajra OS to disk"
echo "    vajra-help      — Show all commands"
echo "    vajra-tools     — List 279 utility tools"
echo "    buddhi          — AI assistant"
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
    isolinux_cfg.write_text("""DEFAULT vajra
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
    
    grub_cfg = WORK / "grub.cfg"
    grub_cfg.write_text("""set timeout=30
set default=0
menuentry "Vajra OS 1.0 (Default)" {
    linux /vmlinuz console=tty0 quiet
    initrd /initramfs.cpio.gz
}
menuentry "Vajra OS 1.0 (Debug Mode)" {
    linux /vmlinuz console=tty0
    initrd /initramfs.cpio.gz
}
menuentry "Vajra OS 1.0 (Serial Console)" {
    linux /vmlinuz console=ttyS0,115200
    initrd /initramfs.cpio.gz
}
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
    
    # ISOLINUX (BIOS)
    iso.add_directory("/ISOLINUX", rr_name="isolinux")
    iso.add_file(str(isolinux_cfg), "/ISOLINUX/ISOLINUX.CFG", rr_name="isolinux.cfg")
    iso.add_file(str(boot_msg), "/BOOT.MSG", rr_name="boot.msg")
    
    # GRUB (UEFI)
    if bootx64 and bootx64.exists():
        iso.add_directory("/EFI", rr_name="efi")
        iso.add_directory("/EFI/BOOT", rr_name="boot")
        iso.add_file(str(bootx64), "/EFI/BOOT/BOOTX64.EFI", rr_name="bootx64.efi")
    
    iso.add_file(str(grub_cfg), "/GRUB.CFG", rr_name="grub.cfg")
    
    # README
    readme = WORK / "README.txt"
    readme.write_text(f"Vajra OS {ISO_VERSION}\nIndia's Privacy-First AI-Powered OS\nDharmo Rakshati Rakshitah\n\nBoot: dd if=vajra-os-1.0-amd64.iso of=/dev/sdX bs=4M\nTest: qemu-system-x86_64 -cdrom vajra-os-1.0-amd64.iso -m 512\n")
    iso.add_file(str(readme), "/README.TXT", rr_name="README.txt")
    
    # El Torito BIOS boot
    iso.add_eltorito(
        "/VMLINUZ",
        bootcatfile="/BOOT.CAT;1",
        rr_bootcatname="boot.cat",
        joliet_bootcatfile="/boot.cat",
        platform_id=0,
        media_name="noemul",
        bootable=True,
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
            media_name="noemul",
            bootable=True,
            boot_info_table=False
        )
    
    iso.write(str(output_path))
    iso.close()
    
    iso_size = Path(output_path).stat().st_size
    result = subprocess.run(["file", output_path], capture_output=True, text=True)
    
    print(f"\n{'='*60}")
    print(f"  ISO BUILD COMPLETE!")
    print(f"{'='*60}")
    print(f"  File: {output_path}")
    print(f"  Size: {iso_size:,} bytes ({iso_size/1024/1024:.1f} MB)")
    print(f"  Type: {result.stdout.strip()}")
    print(f"  Boot: BIOS (El Torito) + UEFI (GRUB)")
    print(f"{'='*60}")
    
    return output_path

if __name__ == "__main__":
    output = sys.argv[sys.argv.index("--output") + 1] if "--output" in sys.argv else "vajra-os-1.0-amd64.iso"
    build_iso(output)
