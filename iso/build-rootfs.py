#!/usr/bin/env python3
"""
Vajra OS Docker rootfs builder.
Builds vajra-os-rootfs.tar.gz — a Docker-importable root filesystem with
BusyBox, all Vajra tools, and Buddhi AI.

Usage:
    python3 build-rootfs.py [--output vajra-os-rootfs.tar.gz]

After building:
    docker import vajra-os-rootfs.tar.gz vajra-os:1.0
    docker run -it vajra-os:1.0
"""
import os, sys, gzip, shutil, subprocess, urllib.request, json, tarfile
from pathlib import Path

REPO_OWNER = "ksraj20009"
REPO_NAME = "vajra-os"
BUSYBOX_URL = "https://raw.githubusercontent.com/EXALAB/Busybox-static/main/busybox_amd64"

def download(url, dest, desc=""):
    print(f"  [*] Downloading {desc or url.split('/')[-1]}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = urllib.request.urlopen(req, timeout=60).read()
    Path(dest).write_bytes(data)
    print(f"      Downloaded: {len(data):,} bytes")
    return data

def build_rootfs(output_path="vajra-os-rootfs.tar.gz"):
    WORK = Path(os.environ.get("VAJRA_ROOTFS_WORK", "/scratch/work/vajra-rootfs-build"))
    WORK.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("  Vajra OS Docker Rootfs Builder")
    print(f"{'='*60}\n")

    # 1. BusyBox
    print("[1/5] Downloading BusyBox...")
    busybox = WORK / "busybox"
    if not busybox.exists():
        download(BUSYBOX_URL, busybox, "BusyBox static")
    os.chmod(busybox, 0o755)

    # 2. Rootfs skeleton
    print("[2/5] Creating rootfs structure...")
    rootfs = WORK / "rootfs"
    if rootfs.exists():
        shutil.rmtree(rootfs)
    for d in ["bin", "sbin", "usr/bin", "usr/sbin", "usr/local/bin",
              "usr/share/vajra/tools", "etc/vajra/settings", "proc", "sys", "dev", "tmp",
              "root", "home/vajra", "var/log", "var/run", "mnt", "media", "opt"]:
        (rootfs / d).mkdir(parents=True, exist_ok=True)

    shutil.copy(busybox, rootfs / "bin/busybox")
    os.chmod(rootfs / "bin/busybox", 0o755)
    result = subprocess.run([str(busybox), "--list"], capture_output=True, text=True, timeout=10)
    nlinks = 0
    for applet in result.stdout.strip().split("\n"):
        for bindir in ("bin", "sbin"):
            link = rootfs / f"{bindir}/{applet}"
            if not link.exists():
                try:
                    link.symlink_to("/bin/busybox")
                    nlinks += 1
                except OSError:
                    pass
    print(f"  [+] BusyBox + {nlinks} applet symlinks")

    # 3. Vajra tools from the repo
    print("[3/5] Downloading Vajra OS tools from GitHub...")
    tree_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/main?recursive=1"
    req = urllib.request.Request(tree_url, headers={'User-Agent': 'Mozilla/5.0',
                                                   'Accept': 'application/vnd.github.v3+json'})
    tree_data = json.loads(urllib.request.urlopen(req, timeout=15).read())

    exclude_dirs = ["packaging", "installer", "live-build", ".github", "branding",
                    "docker", "iso", "docs", "apt-repo", "web", "kernel"]
    util_files = []
    for item in tree_data.get("tree", []):
        if item["type"] != "blob":
            continue
        path = item["path"]
        if not (path.endswith(".py") or path.endswith(".sh")):
            continue
        if any(path.startswith(ex + "/") for ex in exclude_dirs):
            continue
        util_files.append(path)

    downloaded = 0
    for path in util_files:
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{path}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req, timeout=10).read()
            dest = rootfs / "usr/share/vajra/tools" / path.replace("/", "_")
            dest.write_bytes(data)
            os.chmod(dest, 0o755)
            downloaded += 1
        except Exception:
            pass
    print(f"  [+] Installed {downloaded} utility scripts")

    # core tools to /usr/bin
    for path in util_files:
        if path.startswith("core/"):
            url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{path}"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                data = urllib.request.urlopen(req, timeout=10).read()
                dest = rootfs / "usr/bin" / Path(path).name
                dest.write_bytes(data)
                os.chmod(dest, 0o755)
            except Exception:
                pass

    # Buddhi AI
    try:
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/ai/buddhi-ai.py"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=10).read()
        buddhi = rootfs / "usr/bin/buddhi"
        buddhi.write_bytes(data)
        os.chmod(buddhi, 0o755)
        print(f"  [+] Buddhi AI: {len(data):,} bytes")
    except Exception:
        pass

    # 4. System files
    print("[4/5] Writing system files...")
    (rootfs / "etc/os-release").write_text(
        'NAME="Vajra OS"\n'
        'VERSION="1.0"\n'
        'ID=vajra\n'
        'PRETTY_NAME="Vajra OS 1.0"\n'
        'HOME_URL="https://ksraj20009.github.io/vajra-os/"\n'
        'SUPPORT_URL="https://github.com/ksraj20009/vajra-os"\n')
    (rootfs / "etc/hostname").write_text("vajra-os\n")
    (rootfs / "etc/motd").write_text(
        "\n  Vajra OS 1.0 - India's Privacy-First AI-Powered OS\n"
        "  Dharmo Rakshati Rakshitah\n\n"
        "  Tools: vajra-help, vajra-tools, buddhi\n\n")
    (rootfs / "etc/vajra/settings/vajra.conf").write_text(
        '{"os_mode": "beginner", "language": "en_IN", "timezone": "Asia/Kolkata"}\n')
    # resolv + passwd basics
    (rootfs / "etc/passwd").write_text(
        "root:x:0:0:root:/root:/bin/sh\n"
        "vajra:x:1000:1000:vajra:/home/vajra:/bin/sh\n")
    (rootfs / "etc/group").write_text(
        "root:x:0:\nvajra:x:1000:\n")
    (rootfs / "etc/resolv.conf").write_text(
        "nameserver 9.9.9.9\nnameserver 1.1.1.1\n")

    # Docker entrypoint (POSIX sh — busybox compatible)
    entrypoint = rootfs / "usr/local/bin/vajra-docker-entrypoint"
    entrypoint.write_text(
        '#!/bin/sh\n'
        'echo ""\n'
        'echo "  =================================================="\n'
        'echo "  |    Vajra OS 1.0 - Docker Edition               |"\n'
        'echo "  |    India\'s Privacy-First AI-Powered OS         |"\n'
        'echo "  |    Dharmo Rakshati Rakshitah                  |"\n'
        'echo "  =================================================="\n'
        'echo ""\n'
        'echo "  Tools: vajra-help  vajra-tools  buddhi"\n'
        'echo ""\n'
        'export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/share/vajra/tools\n'
        'export HOME=/root\n'
        'exec /bin/sh\n')
    os.chmod(entrypoint, 0o755)

    # 5. Tar it up
    print("[5/5] Creating tarball...")
    with tarfile.open(output_path, "w:gz", compresslevel=9) as tar:
        tar.add(rootfs, arcname=".")
    size = Path(output_path).stat().st_size
    print(f"\n{'='*60}")
    print(f"  ROOTFS BUILD COMPLETE!")
    print(f"{'='*60}")
    print(f"  File: {output_path}")
    print(f"  Size: {size:,} bytes ({size/1024/1024:.1f} MB)")
    print(f"  Import: docker import {output_path} vajra-os:1.0")
    print(f"  Run:    docker run -it vajra-os:1.0")
    print(f"{'='*60}")
    return output_path

if __name__ == "__main__":
    output = sys.argv[sys.argv.index("--output") + 1] if "--output" in sys.argv else "vajra-os-rootfs.tar.gz"
    build_rootfs(output)
