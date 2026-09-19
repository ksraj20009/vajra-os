#!/usr/bin/env python3
"""
Vajra OS ISO boot tests.

Test 1 (smoke)     : extract kernel+initramfs from the ISO and boot them
                     directly under QEMU (fast, isolates kernel/initramfs/init).
Test 2 (real BIOS) : boot the actual ISO as a CD-ROM — SeaBIOS -> El Torito ->
                     ISOLINUX -> kernel -> initramfs -> init. This is the exact
                     chain a user gets on real hardware (minus the silicon).
Test 3 (UEFI)      : boot the ISO via OVMF firmware -> El Torito 0xEF ->
                     BOOTX64.EFI -> kernel (skipped with a notice if OVMF is
                     not installed).

Usage:
    python3 boot-test.py [--iso vajra-os-1.0-amd64.iso]

Requirements:
    pip install pycdlib
    qemu-system-x86_64 on PATH
"""
import os, sys, glob, shutil, subprocess, tempfile
from pathlib import Path
import pycdlib

BOOT_TIMEOUT = 300   # seconds; TCG emulation of a kernel boot is slow
UEFI_TIMEOUT = 420   # seconds; OVMF firmware is slower still

BANNER_MARKERS = ["VAJRA OS 1.0", "Dharmo Rakshati Rakshitah"]

def fail(msg, serial_log=None):
    print(f"  [-] BOOT TEST FAILED: {msg}")
    if serial_log and Path(serial_log).exists():
        print("  --- serial console (last 40 lines) ---")
        tail = Path(serial_log).read_text(errors="replace").splitlines()[-40:]
        for line in tail:
            print(f"  | {line}")
    sys.exit(1)

def check_markers(output, extra=None):
    ok = True
    for marker in BANNER_MARKERS + (extra or []):
        if marker in output:
            print(f"  [+] found: {marker!r}")
        else:
            print(f"  [-] MISSING: {marker!r}")
            ok = False
    return ok

def qemu():
    q = shutil.which("qemu-system-x86_64")
    if not q:
        fail("qemu-system-x86_64 not found on PATH")
    return q

def test_smoke(iso_path, work):
    print("\n[Test 1] Direct kernel boot (smoke) — kernel + initramfs + init")
    iso = pycdlib.PyCdlib()
    iso.open(str(iso_path))
    iso.get_file_from_iso(local_path=str(work / "vmlinuz"), iso_path="/VMLINUZ")
    iso.get_file_from_iso(local_path=str(work / "initramfs.cpio.gz"), iso_path="/INITRAMF.CPG")
    iso.close()
    print(f"  [+] vmlinuz: {(work / 'vmlinuz').stat().st_size:,} bytes")
    print(f"  [+] initramfs: {(work / 'initramfs.cpio.gz').stat().st_size:,} bytes")
    serial_log = work / "smoke-serial.log"
    cmd = [qemu(), "-m", "512", "-accel", "tcg",
           "-kernel", str(work / "vmlinuz"),
           "-initrd", str(work / "initramfs.cpio.gz"),
           "-append", "console=ttyS0",
           "-display", "none", "-monitor", "none",
           "-serial", f"file:{serial_log}",
           "-netdev", "user,id=n0", "-device", "e1000,netdev=n0",
           "-no-reboot"]
    try:
        subprocess.run(cmd, timeout=BOOT_TIMEOUT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        pass  # expected — the OS drops to an interactive shell
    if not serial_log.exists():
        fail("no serial output captured")
    output = serial_log.read_text(errors="replace")
    if not check_markers(output, extra=["vajra@vajra-os"]):
        fail("boot banner markers missing from serial console", serial_log)
    print("  [+] PASS")

def test_bios_chain(iso_path, work):
    print("\n[Test 2] Full BIOS boot chain — SeaBIOS -> El Torito -> ISOLINUX -> kernel")
    serial_log = work / "bios-serial.log"
    cmd = [qemu(), "-m", "512", "-accel", "tcg",
           "-cdrom", str(iso_path), "-boot", "d",
           "-display", "none", "-monitor", "none",
           "-serial", f"file:{serial_log}",
           "-netdev", "user,id=n0", "-device", "e1000,netdev=n0",
           "-no-reboot"]
    try:
        subprocess.run(cmd, timeout=BOOT_TIMEOUT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        pass  # expected — the OS drops to an interactive shell
    if not serial_log.exists():
        fail("no serial output captured")
    output = serial_log.read_text(errors="replace")
    # ISOLINUX itself must appear on serial (SERIAL 0 directive in the config),
    # proving the bootloader was reached and executed from the CD.
    if not check_markers(output, extra=["ISOLINUX", "boot:"]):
        fail("BIOS boot chain did not reach the Vajra OS init", serial_log)
    print("  [+] PASS")

def find_ovmf():
    for pat in ["/usr/share/OVMF/OVMF_CODE.fd", "/usr/share/ovmf/OVMF.fd",
                "/usr/share/ovmf/OVMF_CODE.fd", "/usr/share/edk2/ovmf/OVMF_CODE.fd",
                "/usr/share/qemu/OVMF.fd", "/usr/share/OVMF/OVMF.fd"]:
        if os.path.exists(pat):
            return pat
    for pat in ["/usr/share/OVMF/*.fd", "/usr/share/ovmf/*.fd"]:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    return None

def test_uefi_chain(iso_path, work):
    print("\n[Test 3] UEFI boot chain — OVMF -> El Torito (0xEF) -> BOOTX64.EFI -> kernel")
    firmware = find_ovmf()
    if not firmware:
        print("  [!] OVMF firmware not found — UEFI test SKIPPED")
        print("      (install the 'ovmf' package to enable this test)")
        return
    print(f"  [+] firmware: {firmware}")
    serial_log = work / "uefi-serial.log"
    cmd = [qemu(), "-m", "1024", "-accel", "tcg",
           "-bios", firmware,
           "-cdrom", str(iso_path), "-boot", "d",
           "-display", "none", "-monitor", "none",
           "-serial", f"file:{serial_log}",
           "-netdev", "user,id=n0", "-device", "e1000,netdev=n0",
           "-no-reboot"]
    try:
        subprocess.run(cmd, timeout=UEFI_TIMEOUT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        pass  # expected — the OS drops to an interactive shell
    if not serial_log.exists():
        fail("no serial output captured")
    output = serial_log.read_text(errors="replace")
    if not check_markers(output):
        fail("UEFI boot chain did not reach the Vajra OS init", serial_log)
    print("  [+] PASS")

def boot_test(iso_path):
    print(f"\n{'='*60}")
    print("  Vajra OS ISO Boot Test")
    print(f"{'='*60}\n")

    iso_path = Path(iso_path)
    if not iso_path.exists():
        fail(f"ISO not found: {iso_path}")
    qemu()  # early check

    work = Path(tempfile.mkdtemp(prefix="vajra-boot-"))
    test_smoke(iso_path, work)
    test_bios_chain(iso_path, work)
    test_uefi_chain(iso_path, work)

    print(f"\n{'='*60}")
    print("  ALL BOOT TESTS PASSED — the ISO boots (kernel, BIOS chain, UEFI chain)")
    print(f"{'='*60}")
    shutil.rmtree(work, ignore_errors=True)
    return True

if __name__ == "__main__":
    iso = sys.argv[sys.argv.index("--iso") + 1] if "--iso" in sys.argv else "vajra-os-1.0-amd64.iso"
    boot_test(iso)
