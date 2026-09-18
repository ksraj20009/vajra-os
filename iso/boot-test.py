#!/usr/bin/env python3
"""
Vajra OS ISO boot test.
Extracts the kernel and initramfs from the ISO and boots them under QEMU
(software emulation — no KVM needed), capturing the serial console. The test
passes when the Vajra OS init banner appears on the serial console.

Usage:
    python3 boot-test.py [--iso vajra-os-1.0-amd64.iso]

Requirements:
    pip install pycdlib
    qemu-system-x86_64 on PATH
"""
import os, sys, shutil, subprocess, tempfile
from pathlib import Path
import pycdlib

BOOT_TIMEOUT = 300  # seconds; TCG emulation of a 6.6 kernel boot is slow

def fail(msg, serial_log=None):
    print(f"  [-] BOOT TEST FAILED: {msg}")
    if serial_log and Path(serial_log).exists():
        print("  --- serial console (last 40 lines) ---")
        tail = Path(serial_log).read_text(errors="replace").splitlines()[-40:]
        for line in tail:
            print(f"  | {line}")
    sys.exit(1)

def boot_test(iso_path):
    print(f"\n{'='*60}")
    print("  Vajra OS ISO Boot Test")
    print(f"{'='*60}\n")

    iso_path = Path(iso_path)
    if not iso_path.exists():
        fail(f"ISO not found: {iso_path}")

    work = Path(tempfile.mkdtemp(prefix="vajra-boot-"))

    # 1. Extract kernel + initramfs from the ISO
    print("[1/3] Extracting kernel and initramfs from ISO...")
    try:
        iso = pycdlib.PyCdlib()
        iso.open(str(iso_path))
        iso.get_file_from_iso(local_path=str(work / "vmlinuz"), iso_path="/VMLINUZ")
        iso.get_file_from_iso(local_path=str(work / "initramfs.cpio.gz"), iso_path="/INITRAMF.CPG")
        iso.close()
    except Exception as e:
        fail(f"could not extract kernel/initramfs from ISO: {e}")
    print(f"  [+] vmlinuz: {(work / 'vmlinuz').stat().st_size:,} bytes")
    print(f"  [+] initramfs: {(work / 'initramfs.cpio.gz').stat().st_size:,} bytes")

    # 2. Boot under QEMU with the serial console logged to a file
    print("[2/3] Booting under QEMU (TCG, up to {}s)...".format(BOOT_TIMEOUT))
    serial_log = work / "serial.log"
    cmd = [
        "qemu-system-x86_64",
        "-m", "512",
        "-accel", "tcg",
        "-kernel", str(work / "vmlinuz"),
        "-initrd", str(work / "initramfs.cpio.gz"),
        "-append", "console=ttyS0",
        "-display", "none",
        "-monitor", "none",
        "-serial", f"file:{serial_log}",
        "-netdev", "user,id=n0",
        "-device", "e1000,netdev=n0",
        "-no-reboot",
    ]
    try:
        subprocess.run(cmd, timeout=BOOT_TIMEOUT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        pass  # expected — the OS drops to an interactive shell
    except FileNotFoundError:
        fail("qemu-system-x86_64 not found on PATH")

    if not serial_log.exists():
        fail("no serial output captured")

    # 3. Assert the boot banner
    print("[3/3] Checking serial console for the Vajra OS banner...")
    output = serial_log.read_text(errors="replace")
    checks = [
        "VAJRA OS 1.0",
        "Dharmo Rakshati Rakshitah",
        "vajra@vajra-os",
    ]
    ok = True
    for marker in checks:
        if marker in output:
            print(f"  [+] found: {marker!r}")
        else:
            print(f"  [-] MISSING: {marker!r}")
            ok = False

    if not ok:
        fail("boot banner markers missing from serial console", serial_log)

    print(f"\n{'='*60}")
    print("  BOOT TEST PASSED — the ISO boots to a Vajra OS shell")
    print(f"{'='*60}")
    shutil.rmtree(work, ignore_errors=True)
    return True

if __name__ == "__main__":
    iso = sys.argv[sys.argv.index("--iso") + 1] if "--iso" in sys.argv else "vajra-os-1.0-amd64.iso"
    boot_test(iso)
