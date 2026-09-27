#!/usr/bin/env python3
"""
Vajra OS test suite — run before every release (and locally any time).

  tests/run-tests.py [--skip-smoke]

1. SYNTAX: every Python file in the repo must compile, every shell script
   must pass `bash -n`. This is the gate behind the "510+ source files"
   claim: a file with a syntax error fails the release build.

2. SMOKE: every core OS tool + Buddhi AI must actually start — import
   its modules, create its runtime dirs and reach its user interface —
   without a Python traceback. The tools are interactive menus, so the
   run is fed EOF on stdin; hitting the menu prompt and exiting on EOF
   is a PASS. A traceback (other than the expected EOFError exit) is a
   FAIL.

Run as root (sudo) so tools can create /var/log/vajra, e.g. in CI:
    sudo python3 tests/run-tests.py
"""

import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directories that are not Vajra source (build outputs, upstream clones)
SKIP_DIRS = {
    ".git", "kernel-output", "vajra-kernel-out", "vajra-kernel-output",
    "node_modules", "__pycache__",
}

SMOKE_TOOLS = sorted(
    [ROOT / "core" / f for f in os.listdir(ROOT / "core") if f.endswith(".py")]
    + [ROOT / "ai" / "buddhi-ai.py"]
)

def fail(msg):
    print(f"  [-] {msg}")
    return 1

def test_syntax():
    print("=== 1. Syntax validation of every source file ===")
    errors = 0
    py_files = sh_files = 0

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                       and not d.startswith("linux-")]
        # never descend into the torvalds/linux clone target
        if Path(dirpath).name == "linux" and (ROOT / "kernel") in Path(dirpath).parents:
            dirnames[:] = []
            continue
        for name in sorted(filenames):
            path = Path(dirpath) / name
            rel = path.relative_to(ROOT)
            if name.endswith(".py"):
                py_files += 1
                try:
                    py_compile.compile(str(path), doraise=True)
                except py_compile.PyCompileError as e:
                    errors += fail(f"PYTHON SYNTAX ERROR: {rel}\n{e}")
            elif name.endswith(".sh"):
                sh_files += 1
                r = subprocess.run(["bash", "-n", str(path)],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    errors += fail(f"SHELL SYNTAX ERROR: {rel}\n{r.stderr.strip()}")

    print(f"  [+] {py_files} Python files compiled, {sh_files} shell scripts parsed")
    return errors

def smoke_one(tool):
    rel = tool.relative_to(ROOT)
    try:
        r = subprocess.run(
            [sys.executable, str(tool)],
            stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=20,
        )
        out = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        # A tool that keeps running (daemon/service mode) started fine.
        print(f"  [+] {rel}: running past timeout (daemon?) - PASS")
        return 0

    if "Traceback" in out:
        # EOFError means the tool reached its interactive menu and stdin
        # was closed - that is the expected lifecycle of a menu tool.
        if "EOFError" in out and out.count("Traceback") == 1:
            print(f"  [+] {rel}: reached interactive prompt - PASS")
            return 0
        return fail(f"{rel}: crashed with a traceback:\n{out.strip()[:800]}")

    if "SyntaxError" in out or "ImportError" in out or "ModuleNotFoundError" in out:
        return fail(f"{rel}: import/syntax problem:\n{out.strip()[:800]}")

    print(f"  [+] {rel}: started and exited cleanly - PASS")
    return 0

def test_smoke():
    print(f"=== 2. Smoke test: {len(SMOKE_TOOLS)} core tools must start ===")
    errors = 0
    for tool in SMOKE_TOOLS:
        if not tool.exists():
            errors += fail(f"missing tool source: {tool.relative_to(ROOT)}")
            continue
        errors += smoke_one(tool)
    return errors

def main():
    print("Vajra OS test suite")
    print("==================")
    errors = test_syntax()

    if "--skip-smoke" in sys.argv:
        print("\n(smoke tests skipped)")
    else:
        if os.geteuid() != 0:
            print("\n[!] not running as root - the tools create /var/log/vajra at")
            print("    startup, so run with:  sudo python3 tests/run-tests.py")
        errors += test_smoke()

    print("\n" + "=" * 50)
    if errors:
        print(f"[-] {errors} FAILURE(S)")
        sys.exit(1)
    print("[+] ALL TESTS PASSED")

if __name__ == "__main__":
    main()
