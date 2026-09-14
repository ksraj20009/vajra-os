#!/usr/bin/env python3
"""
Vajra OS — Buddhi Agentic AI Engine v3.0
=========================================
बुद्धि (Buddhi) — Supreme Intelligence

Fully agentic AI that can:
- Plan and execute multi-step tasks autonomously
- Control the entire OS via natural language
- Voice-activated with wake word "Buddhi"
- Monitor system health and auto-fix issues
- Install software automatically
- Act as a security guardian
- Natural language shell (translate English → commands)
- File operations, app management, process control
- Web search, research, summarization
- Local LLM integration (Ollama, fully offline)
- REST API on localhost:5210
- Continuous background monitoring

No cloud. No tracking. Everything runs locally.
"""

import os, sys, json, time, socket, subprocess, threading, urllib.request, urllib.parse, urllib.error, re, hashlib, shutil, tempfile, signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque, OrderedDict
import inspect

# ============================================================
#  Configuration
# ============================================================

VERSION = "3.0"
CODENAME = "Vajra"
RELEASE_NAME = "Vajra OS 1.0 — वज्र"

CONFIG = {
    "version": VERSION,
    "codename": CODENAME,
    "release": RELEASE_NAME,
    "api_port": 5210,
    "api_host": "127.0.0.1",
    "voice_enabled": True,
    "voice_wake_word": "buddhi",
    "voice_lang": "en-IN",
    "privacy_mode": True,
    "agentic_mode": True,
    "auto_fix": True,
    "log_file": "/var/log/buddhi-ai.log",
    "max_context": 100,
    "user_name": "vajra",
    "max_task_steps": 15,
    "monitor_interval": 60,
    "local_llm": {
        "enabled": True,
        "model": "llama3.2",
        "endpoint": "http://127.0.0.1:11434/api/generate",
    },
    "voice_model_path": "/opt/vajra/ai/models/vosk-model-small-en-in-0.4",
}

def log(msg, level="INFO"):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(CONFIG["log_file"], "a") as f:
            f.write(line + "\n")
    except:
        pass

# ============================================================
#  Memory & Context
# ============================================================

class Memory:
    def __init__(self, max_ctx=100):
        self.history = deque(maxlen=max_ctx)
        self.facts = {}
        self.tasks_completed = []

    def add(self, role, content, meta=None):
        entry = {
            "role": role,
            "content": content,
            "ts": datetime.now().isoformat(),
            "meta": meta or {}
        }
        self.history.append(entry)

    def recent(self, n=10):
        return list(self.history)[-n:]

    def clear(self):
        self.history.clear()

    def remember(self, key, value):
        self.facts[key] = value

    def recall(self, key, default=None):
        return self.facts.get(key, default)

    def task_done(self, task):
        self.tasks_completed.append({"task": task, "ts": datetime.now().isoformat()})

mem = Memory(CONFIG["max_context"])

# ============================================================
#  Web Search
# ============================================================

class WebSearch:
    def search(self, query, num=8):
        try:
            params = urllib.parse.urlencode({"q": query, "format": "json", "no_html": "1"})
            url = f"https://api.duckduckgo.com/?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "VajraOS/3.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = []
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", query),
                    "content": data["AbstractText"],
                    "url": data.get("AbstractURL", "")
                })
            for t in data.get("RelatedTopics", [])[:num]:
                if isinstance(t, dict) and t.get("Text"):
                    results.append({
                        "title": t["Text"][:80],
                        "content": t["Text"],
                        "url": t.get("FirstURL", "")
                    })
            if not results:
                r = self._wiki(query)
                if r:
                    results.append(r)
            return results or [{"title": "No results", "content": f"No instant answers for '{query}'."}]
        except Exception as e:
            return [{"title": "Error", "content": str(e)}]

    def _wiki(self, query):
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ', '_'))}"
            req = urllib.request.Request(url, headers={"User-Agent": "VajraOS/3.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("extract"):
                return {
                    "title": data.get("title", query),
                    "content": data["extract"],
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
                }
        except:
            pass
        return None

    def alternatives(self, name):
        r1 = self.search(f"{name} alternative software")
        r2 = self.search(f"{name} open source alternative")
        seen, out = set(), []
        for r in r1 + r2:
            if r["title"] not in seen:
                seen.add(r["title"])
                out.append(r)
        return out[:10]

    def summarize(self, query):
        results = self.search(query, num=5)
        combined = " ".join([r["content"][:300] for r in results])
        if not combined.strip():
            return f"Could not find information about '{query}'."
        summary = f"Summary for '{query}':\n\n"
        for i, r in enumerate(results[:5], 1):
            summary += f"{i}. {r['title']}\n   {r['content'][:250]}\n\n"
        return summary

web = WebSearch()

# ============================================================
#  Local LLM (Ollama)
# ============================================================

class LLM:
    def __init__(self):
        self.enabled = CONFIG["local_llm"]["enabled"]
        self.endpoint = CONFIG["local_llm"]["endpoint"]
        self.model = CONFIG["local_llm"]["model"]

    def available(self):
        if not self.enabled:
            return False
        try:
            urllib.request.urlopen(self.endpoint.replace("/api/generate", "/api/tags"), timeout=2)
            return True
        except:
            return False

    def generate(self, prompt, context=""):
        if not self.available():
            return None
        try:
            p = f"{context}\n\nUser: {prompt}\nAssistant:" if context else f"User: {prompt}\nAssistant:"
            data = json.dumps({
                "model": self.model,
                "prompt": p,
                "stream": False,
                "options": {"temperature": 0.7, "top_p": 0.9}
            }).encode("utf-8")
            req = urllib.request.Request(self.endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8")).get("response", "").strip()
        except Exception as e:
            log(f"LLM error: {e}", "ERROR")
            return None

    def translate_to_shell(self, natural_lang):
        prompt = f"""Convert this natural language request to a Linux shell command.
Return ONLY the command, nothing else.
Request: "{natural_lang}"
Command:"""
        r = self.generate(prompt)
        if r:
            r = r.strip()
            r = r.split("\n")[0]
            r = r.replace("```", "").replace("bash", "").strip()
            return r if r else None
        return None

llm = LLM()

# ============================================================
#  OS Controller
# ============================================================

class OSController:
    APPS = {
        "terminal": ["gnome-terminal", "xterm"],
        "browser": ["firefox-esr", "firefox", "chromium"],
        "tor": ["tor-browser"],
        "files": ["nautilus", "thunar"],
        "file manager": ["nautilus", "thunar"],
        "editor": ["gedit", "mousepad"],
        "text editor": ["gedit", "mousepad"],
        "calculator": ["gnome-calculator"],
        "settings": ["gnome-control-center"],
        "monitor": ["gnome-system-monitor", "htop"],
        "system monitor": ["gnome-system-monitor", "htop"],
        "music": ["rhythmbox", "mpv"],
        "video": ["mpv", "vlc"],
        "photos": ["eog", "gthumb"],
        "screenshot": ["gnome-screenshot", "scrot"],
        "notes": ["gedit", "mousepad"],
        "email": ["thunderbird", "evolution"],
        "office": ["libreoffice"],
        "calendar": ["gnome-calendar"],
        "weather": ["gnome-weather"],
        "maps": ["gnome-maps"],
        "software": ["gnome-software"],
        "app store": ["gnome-software"],
    }

    def open_app(self, name):
        name = name.lower().strip()
        if name in self.APPS:
            for cmd in self.APPS[name]:
                if self._exists(cmd):
                    try:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")})
                        return True, f"Opened {name}"
                    except:
                        continue
        return False, f"App '{name}' not found. Available: {', '.join(self.APPS.keys())}"

    def run(self, cmd):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return True, (r.stdout.strip() or r.stderr.strip() or "Done")
        except subprocess.TimeoutExpired:
            return False, "Command timed out (30s limit)"
        except Exception as e:
            return False, str(e)

    def run_safely(self, cmd):
        DANGEROUS = ["rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){ :|:& };:", "> /dev/sda", "shutdown", "halt", "reboot", "init 0", "init 6"]
        for d in DANGEROUS:
            if d in cmd:
                return False, f"BLOCKED dangerous command: {cmd}"
        return self.run(cmd)

    def install(self, package):
        ok, msg = self.run(f"which {package}")
        if ok and msg != "Done":
            return True, f"{package} is already installed"
        ok, msg = self.run(f"sudo apt-get install -y {package} 2>&1")
        if ok:
            return True, f"Installed {package} successfully"
        return False, f"Failed to install {package}: {msg}"

    def uninstall(self, package):
        ok, msg = self.run(f"sudo apt-get remove -y {package} 2>&1")
        if ok:
            return True, f"Removed {package} successfully"
        return False, f"Failed to remove {package}: {msg}"

    def update_system(self):
        ok, msg = self.run("sudo apt-get update && sudo apt-get upgrade -y 2>&1")
        return ok, "System updated" if ok else msg

    def info(self):
        info = {
            "os": "Vajra OS",
            "version": VERSION,
            "codename": CODENAME,
            "kernel": os.uname().release,
            "hostname": socket.gethostname(),
            "arch": os.uname().machine,
            "cpu_count": os.cpu_count(),
            "time": datetime.now().isoformat(),
        }
        try:
            with open("/proc/uptime") as f:
                up = float(f.read().split()[0])
                info["uptime"] = f"{int(up//3600)}h {int((up%3600)//60)}m"
        except: pass
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        info["mem_total"] = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        info["mem_available"] = int(line.split()[1]) // 1024
        except: pass
        try:
            with open("/proc/loadavg") as f:
                info["load"] = f.read().strip()
        except: pass
        try:
            df = os.statvfs("/")
            total = df.f_blocks * df.f_frsize // (1024**3)
            free = df.f_bavail * df.f_frsize // (1024**3)
            info["disk_total"] = total
            info["disk_free"] = free
        except: pass
        return info

    def battery(self):
        try:
            bat_dir = "/sys/class/power_supply/BAT0"
            if not os.path.exists(bat_dir):
                bat_dir = "/sys/class/power_supply/BAT1"
            if os.path.exists(bat_dir):
                with open(f"{bat_dir}/capacity") as f:
                    pct = f.read().strip()
                with open(f"{bat_dir}/status") as f:
                    status = f.read().strip()
                return f"Battery: {pct}% ({status})"
        except: pass
        return "No battery found"

    def network_info(self):
        ok, out = self.run("ip addr show 2>/dev/null | grep 'inet ' | awk '{print $2}'")
        if ok:
            return out
        return "Network info unavailable"

    def list_files(self, path="."):
        try:
            files = os.listdir(path)
            dirs = [f for f in files if os.path.isdir(os.path.join(path, f))]
            files = [f for f in files if not os.path.isdir(os.path.join(path, f))]
            result = f"Directory: {os.path.abspath(path)}\n\n"
            if dirs:
                result += "Folders:\n"
                for d in sorted(dirs):
                    result += f"  {d}/\n"
            if files:
                result += f"\nFiles ({len(files)}):\n"
                for f in sorted(files):
                    size = os.path.getsize(os.path.join(path, f))
                    result += f"  {f} ({size} bytes)\n"
            return result
        except Exception as e:
            return f"Error: {e}"

    def read_file(self, path, lines=50):
        try:
            with open(path, 'r', errors='replace') as f:
                content = f.read(lines * 100)
            return content[:5000]
        except Exception as e:
            return f"Error reading {path}: {e}"

    def write_file(self, path, content):
        try:
            with open(path, 'w') as f:
                f.write(content)
            return True, f"Written to {path}"
        except Exception as e:
            return False, str(e)

    def kill_process(self, name):
        ok, msg = self.run(f"pkill -f {name} 2>/dev/null || true")
        if ok:
            return True, f"Killed processes matching '{name}'"
        return False, msg

    def list_processes(self, top=15):
        ok, out = self.run(f"ps aux --sort=-%cpu | head -{top+1}")
        return out if ok else "Failed to list processes"

    def screenshot(self):
        ok, _ = self.run("gnome-screenshot -f /tmp/vajra-screenshot.png 2>/dev/null || scrot /tmp/vajra-screenshot.png 2>/dev/null || true")
        return "Screenshot saved to /tmp/vajra-screenshot.png" if ok else "Screenshot failed"

    def set_volume(self, level=None, mute=None):
        cmds = []
        if level is not None:
            cmds.append(f"amixer -q sset Master {level}% 2>/dev/null || pactl set-sink-volume @DEFAULT_SINK@ {level}% 2>/dev/null || true")
        if mute is not None:
            cmds.append(f"amixer -q sset Master {'mute' if mute else 'unmute'} 2>/dev/null || pactl set-sink-mute @DEFAULT_SINK@ {'1' if mute else '0'} 2>/dev/null || true")
        for c in cmds:
            self.run(c)
        return "Volume adjusted"

    def set_brightness(self, level):
        self.run(f"brightnessctl set {level}% 2>/dev/null || xbacklight -set {level} 2>/dev/null || true")
        return f"Brightness set to {level}%"

    def clipboard(self, text=None):
        if text:
            self.run(f"echo '{text}' | xclip -selection clipboard 2>/dev/null || echo '{text}' | wl-copy 2>/dev/null || true")
            return "Copied to clipboard"
        else:
            ok, out = self.run("xclip -selection clipboard -o 2>/dev/null || wl-paste 2>/dev/null || true")
            return out if ok else "Clipboard empty"

    def _exists(self, cmd):
        try:
            return subprocess.run(["which", cmd], capture_output=True, timeout=5).returncode == 0
        except:
            return False

os_ctl = OSController()

# ============================================================
#  Security Guardian
# ============================================================

class SecurityGuardian:
    def __init__(self):
        self.threats_blocked = 0
        self.last_scan = None
        self.monitoring = False
        self.suspicious_ips = set()

    def check_firewall(self):
        ok, out = os_ctl.run("ufw status 2>/dev/null || firewall-cmd --state 2>/dev/null || iptables -L -n 2>/dev/null | head -5")
        if "inactive" in out.lower() or "not running" in out.lower():
            os_ctl.run("sudo ufw enable 2>/dev/null || sudo systemctl start firewalld 2>/dev/null || true")
            return "Firewall was OFF - auto-enabled"
        return f"Firewall: {out.split(chr(10))[0]}"

    def check_failed_logins(self):
        ok, out = os_ctl.run("grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -20 || journalctl -u sshd --no-pager -n 20 2>/dev/null | grep Failed || echo 'No failed logins'")
        count = len([l for l in out.split("\n") if "Failed" in l])
        if count > 10:
            return f"WARNING: {count} failed login attempts detected!"
        return f"Failed logins: {count}"

    def check_open_ports(self):
        ok, out = os_ctl.run("ss -tlnp 2>/dev/null | grep LISTEN | awk '{print $4}' | sort -u")
        return f"Open ports:\n{out}" if ok else "Could not check ports"

    def check_updates(self):
        ok, out = os_ctl.run("apt list --upgradable 2>/dev/null | grep -c upgradable || echo 0")
        try:
            count = int(out.strip())
            if count > 0:
                return f"{count} security updates available"
            return "All packages up to date"
        except:
            return "Could not check updates"

    def full_scan(self):
        results = []
        results.append(("Firewall", self.check_firewall()))
        results.append(("Failed Logins", self.check_failed_logins()))
        results.append(("Open Ports", self.check_open_ports()))
        results.append(("Updates", self.check_updates()))
        self.last_scan = datetime.now().isoformat()
        return results

    def start_monitor(self):
        self.monitoring = True
        def _monitor():
            while self.monitoring:
                try:
                    self.check_firewall()
                    time.sleep(CONFIG["monitor_interval"])
                except:
                    time.sleep(30)
        threading.Thread(target=_monitor, daemon=True).start()
        return "Security monitoring started"

    def stop_monitor(self):
        self.monitoring = False
        return "Security monitoring stopped"

guardian = SecurityGuardian()

# ============================================================
#  Task Planner — Agentic multi-step execution
# ============================================================

class TaskPlanner:
    def __init__(self):
        self.max_steps = CONFIG["max_task_steps"]

    def plan_and_execute(self, task):
        task = task.strip()
        log(f"Agentic task: {task}", "AGENT")
        mem.add("user", task, {"type": "agentic_task"})
        steps = self._create_plan(task)
        if not steps:
            return {"response": "I couldn't figure out how to help with that. Try rephrasing.", "action": "failed"}
        results = []
        for i, step in enumerate(steps[:self.max_steps], 1):
            log(f"Step {i}/{len(steps)}: {step['desc']}", "AGENT")
            result = self._execute_step(step)
            results.append({"step": i, "desc": step["desc"], "result": result})
            if result.get("failed"):
                break
        summary = self._summarize_results(task, results)
        mem.add("assistant", summary, {"type": "agentic_result", "steps": len(results)})
        mem.task_done(task)
        return {"response": summary, "action": "agentic", "steps": results}

    def _create_plan(self, task):
        task_lower = task.lower()
        steps = []
        if "install" in task_lower and ("software" in task_lower or "app" in task_lower or "package" in task_lower):
            pkg = self._extract_package_name(task)
            if pkg:
                steps.append({"desc": f"Check if {pkg} is already installed", "type": "check_install", "pkg": pkg})
                steps.append({"desc": f"Install {pkg}", "type": "install", "pkg": pkg})
                steps.append({"desc": f"Verify {pkg} installation", "type": "verify_install", "pkg": pkg})
        elif "update" in task_lower and "system" in task_lower:
            steps.append({"desc": "Update package lists", "type": "run", "cmd": "sudo apt-get update"})
            steps.append({"desc": "Upgrade all packages", "type": "run", "cmd": "sudo apt-get upgrade -y"})
            steps.append({"desc": "Clean up old packages", "type": "run", "cmd": "sudo apt-get autoremove -y"})
        elif "scan" in task_lower or "security" in task_lower:
            steps.append({"desc": "Check firewall status", "type": "guardian_firewall"})
            steps.append({"desc": "Check failed logins", "type": "guardian_logins"})
            steps.append({"desc": "Check open ports", "type": "guardian_ports"})
            steps.append({"desc": "Check for updates", "type": "guardian_updates"})
        elif "clean" in task_lower or "free space" in task_lower:
            steps.append({"desc": "Clean apt cache", "type": "run", "cmd": "sudo apt-get clean"})
            steps.append({"desc": "Remove old packages", "type": "run", "cmd": "sudo apt-get autoremove -y"})
            steps.append({"desc": "Clean temp files", "type": "run", "cmd": "rm -rf /tmp/vajra-* 2>/dev/null || true"})
            steps.append({"desc": "Empty trash", "type": "run", "cmd": "rm -rf ~/.local/share/Trash/* 2>/dev/null || true"})
            steps.append({"desc": "Check disk space", "type": "run", "cmd": "df -h /"})
        elif "backup" in task_lower:
            steps.append({"desc": "Create backup directory", "type": "run", "cmd": "mkdir -p ~/vajra-backup"})
            steps.append({"desc": "Backup home directory", "type": "run", "cmd": "tar czf ~/vajra-backup/home-$(date +%Y%m%d).tar.gz -C ~ . 2>/dev/null"})
            steps.append({"desc": "List backup", "type": "run", "cmd": "ls -lh ~/vajra-backup/"})
        elif "tor" in task_lower and ("enable" in task_lower or "start" in task_lower or "activate" in task_lower):
            steps.append({"desc": "Start Tor service", "type": "run", "cmd": "sudo systemctl start tor"})
            steps.append({"desc": "Run Tor proxy setup", "type": "run", "cmd": "sudo /opt/vajra/privacy/setup-tor-proxy.sh"})
            steps.append({"desc": "Verify Tor is running", "type": "run", "cmd": "systemctl is-active tor"})
        elif "optimize" in task_lower or "speed up" in task_lower:
            steps.append({"desc": "Check running processes", "type": "run", "cmd": "ps aux --sort=-%cpu | head -10"})
            steps.append({"desc": "Clear swap cache safely", "type": "run", "cmd": "sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || true"})
            steps.append({"desc": "Disable unnecessary services", "type": "run", "cmd": "sudo systemctl disable avahi-daemon cups bluetooth 2>/dev/null || true"})
            steps.append({"desc": "Check disk usage", "type": "run", "cmd": "df -h"})
        elif "screenshot" in task_lower:
            steps.append({"desc": "Take screenshot", "type": "screenshot"})
        else:
            if llm.available():
                shell_cmd = llm.translate_to_shell(task)
                if shell_cmd and len(shell_cmd) < 200:
                    steps.append({"desc": f"Execute: {shell_cmd}", "type": "run_safely", "cmd": shell_cmd})
                else:
                    steps.append({"desc": "Search the web for information", "type": "search", "query": task})
            else:
                steps.append({"desc": "Search the web for information", "type": "search", "query": task})
        return steps

    def _execute_step(self, step):
        stype = step.get("type")
        try:
            if stype == "run":
                ok, out = os_ctl.run(step["cmd"])
                return {"output": out, "failed": not ok}
            elif stype == "run_safely":
                ok, out = os_ctl.run_safely(step["cmd"])
                return {"output": out, "failed": not ok}
            elif stype == "install":
                ok, out = os_ctl.install(step["pkg"])
                return {"output": out, "failed": not ok}
            elif stype == "check_install":
                ok, out = os_ctl.run(f"which {step['pkg']}")
                return {"output": out}
            elif stype == "verify_install":
                ok, out = os_ctl.run(f"which {step['pkg']} && echo INSTALLED || echo NOT_FOUND")
                return {"output": out, "failed": "NOT_FOUND" in out}
            elif stype == "search":
                results = web.search(step["query"])
                lines = [f"Search results for '{step['query']}':", ""]
                for i, r in enumerate(results[:5], 1):
                    lines.append(f"{i}. {r['title']}")
                    lines.append(f"   {r['content'][:200]}")
                return {"output": "\n".join(lines)}
            elif stype == "guardian_firewall":
                return {"output": guardian.check_firewall()}
            elif stype == "guardian_logins":
                return {"output": guardian.check_failed_logins()}
            elif stype == "guardian_ports":
                return {"output": guardian.check_open_ports()}
            elif stype == "guardian_updates":
                return {"output": guardian.check_updates()}
            elif stype == "screenshot":
                return {"output": os_ctl.screenshot()}
            else:
                return {"output": "Unknown step type", "failed": True}
        except Exception as e:
            return {"output": str(e), "failed": True}

    def _extract_package_name(self, text):
        text = text.lower()
        for prefix in ["install ", "set up ", "get ", "download "]:
            if prefix in text:
                idx = text.index(prefix) + len(prefix)
                rest = text[idx:].strip().rstrip("?.,").strip()
                words = rest.split()[:3]
                pkg = "-".join(words) if len(words) > 1 else words[0] if words else ""
                return pkg if pkg else None
        return None

    def _summarize_results(self, task, results):
        summary = f"Task: {task}\n\n"
        for r in results:
            icon = "OK" if not r["result"].get("failed") else "FAIL"
            summary += f"[{icon}] Step {r['step']}: {r['desc']}\n"
            output = r["result"].get("output", "")
            if output and len(output) < 500:
                summary += f"   -> {output}\n"
            elif output:
                summary += f"   -> {output[:200]}...\n"
        summary += f"\nCompleted {len(results)} step(s)."
        return summary

planner = TaskPlanner()

# ============================================================
#  Voice Control
# ============================================================

class Voice:
    def __init__(self):
        self.enabled = CONFIG["voice_enabled"]
        self.word = CONFIG["voice_wake_word"]
        self.listening = False
        self.tts_enabled = True
        self.continuous_mode = False
        self.last_command = ""

    def init(self):
        if not self.enabled:
            return False
        try:
            from vosk import Model, KaldiRecognizer
            path = CONFIG["voice_model_path"]
            if not os.path.exists(path):
                log("Voice model not found.", "WARN")
                return False
            self.model = Model(path)
            self.rec = KaldiRecognizer(self.model, 16000)
            return True
        except Exception as e:
            log(f"Voice init failed: {e}", "WARN")
            return False

    def speak(self, text):
        if not self.tts_enabled:
            return
        try:
            subprocess.Popen(["espeak-ng", text, "-v", "en-us", "-s", "150"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            try:
                subprocess.Popen(["espeak", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

    def loop(self):
        if not self.init():
            log("Voice engine not available", "WARN")
            return
        import sounddevice as sd
        import json as jm
        self.listening = True
        log(f"Voice listening started (wake word: '{self.word}')", "INFO")
        if self.tts_enabled:
            self.speak("Buddhi voice activated. Say my name to command.")
        def cb(indata, frames, ti, status):
            if self.rec.AcceptWaveform(bytes(indata)):
                r = jm.loads(self.rec.Result())
                t = r.get("text", "").strip().lower()
                if not t:
                    return
                log(f"Heard: '{t}'", "VOICE")
                if self.continuous_mode:
                    self.last_command = t
                    proc.process(t, voice=True)
                elif self.word in t:
                    cmd = t.split(self.word, 1)[-1].strip()
                    if cmd:
                        log(f"Voice command: '{cmd}'", "VOICE")
                        if self.tts_enabled:
                            self.speak(f"Executing: {cmd}")
                        self.last_command = cmd
                        proc.process(cmd, voice=True)
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=cb):
                while self.listening:
                    time.sleep(0.1)
        except Exception as e:
            log(f"Voice error: {e}", "ERROR")

    def start(self):
        if not self.listening:
            threading.Thread(target=self.loop, daemon=True).start()
        return "Voice started"

    def stop(self):
        self.listening = False
        return "Voice stopped"

    def enable_continuous(self):
        self.continuous_mode = True
        return "Continuous voice mode enabled"

    def disable_continuous(self):
        self.continuous_mode = False
        return "Continuous mode disabled"

voice = Voice()

# ============================================================
#  Command Processor
# ============================================================

class Processor:
    def __init__(self):
        self.start_time = time.time()
        self.command_count = 0

    def process(self, query, user="vajra", voice=False):
        query = query.strip()
        if not query:
            return {"response": "How can I help?", "action": "none"}
        q = query.lower()
        mem.add("user", query)
        self.command_count += 1
        resp, action = None, "none"

        if CONFIG["agentic_mode"] and any(trigger in q for trigger in [
            "install ", "update system", "scan ", "security check", "clean ", "free space",
            "backup ", "optimize", "speed up", "tor enable", "enable tor", "start tor",
            "full scan", "diagnose"
        ]):
            result = planner.plan_and_execute(query)
            return result

        elif q.startswith(("open ", "launch ", "start ")):
            app = q.replace("open ", "").replace("launch ", "").replace("start ", "").strip()
            _, resp = os_ctl.open_app(app)
            action = "open"
        elif q.startswith(("close ", "kill ", "quit ", "stop ")):
            proc_name = q.replace("close ", "").replace("kill ", "").replace("quit ", "").replace("stop ", "").strip()
            _, resp = os_ctl.kill_process(proc_name)
            action = "kill"
        elif q.startswith("run "):
            _, resp = os_ctl.run_safely(query[4:].strip())
            action = "run"
        elif q.startswith(("execute ", "do ")):
            nl_cmd = query.replace("execute ", "").replace("do ", "").strip()
            if llm.available():
                shell_cmd = llm.translate_to_shell(nl_cmd)
                if shell_cmd:
                    _, resp = os_ctl.run_safely(shell_cmd)
                    resp = f"Interpreted as: `{shell_cmd}`\n\n{resp}"
                    action = "nl_shell"
                else:
                    resp = "Couldn't translate that to a command."
            else:
                _, resp = os_ctl.run_safely(nl_cmd)
                action = "run"
        elif any(x in q for x in ["what time", "current time", "time now"]):
            resp = f"It's {datetime.now().strftime('%I:%M %p')} on {datetime.now().strftime('%A, %B %d, %Y')}."
            action = "info"
        elif any(x in q for x in ["what date", "what day", "today's date"]):
            resp = f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."
            action = "info"
        elif any(x in q for x in ["system status", "system info", "about system", "about vajra"]):
            i = os_ctl.info()
            resp = f"{RELEASE_NAME}\n\nKernel: {i['kernel']}\nHost: {i['hostname']}\nArch: {i['arch']}\nCPU: {i['cpu_count']} cores\nUptime: {i.get('uptime', '?')}\nMemory: {i.get('mem_available', '?')}MB / {i.get('mem_total', '?')}MB free\nDisk: {i.get('disk_free', '?')}GB / {i.get('disk_total', '?')}GB free\nLoad: {i.get('load', '?')}"
            action = "info"
        elif "battery" in q:
            resp = os_ctl.battery()
            action = "info"
        elif any(x in q for x in ["network", "ip address", "wifi", "internet"]):
            resp = f"Network Info:\n{os_ctl.network_info()}"
            action = "info"
        elif q.startswith(("search ", "look up ", "google ")):
            sq = query
            for p in ["search the web for ", "search web for ", "search ", "look up ", "google "]:
                if q.startswith(p):
                    sq = query[len(p):]
                    break
            results = web.search(sq)
            lines = [f"Search results for '{sq}':\n"]
            for i, r in enumerate(results[:5], 1):
                lines.append(f"{i}. {r['title']}")
                lines.append(f"   {r['content'][:250]}")
                if r.get("url"):
                    lines.append(f"   {r['url']}")
                lines.append("")
            resp = "\n".join(lines)
            action = "search"
        elif "alternative" in q:
            for p in ["alternatives for ", "alternatives to ", "alternative for ", "alternative to "]:
                if p in q:
                    sw = query[q.lower().index(p) + len(p):].strip().rstrip("?.,").strip()
                    break
            else:
                sw = query.replace("alternative", "").strip()
            results = web.alternatives(sw)
            lines = [f"Alternatives for {sw}:\n"]
            for i, r in enumerate(results[:8], 1):
                lines.append(f"{i}. {r['title']}")
                lines.append("")
            resp = "\n".join(lines)
            action = "alternatives"
        elif q.startswith(("summarize ", "summary of ", "explain ")):
            sq = query.replace("summarize ", "").replace("summary of ", "").replace("explain ", "").strip()
            resp = web.summarize(sq)
            action = "summarize"
        elif q.startswith(("list files", "ls", "show files", "list directory")):
            parts = query.split(maxsplit=2)
            path = parts[2] if len(parts) > 2 else "."
            resp = os_ctl.list_files(path)
            action = "files"
        elif q.startswith("read file "):
            path = query.replace("read file ", "").strip()
            resp = os_ctl.read_file(path)
            action = "files"
        elif q.startswith("write file "):
            parts = query.replace("write file ", "").split(" ", 1)
            if len(parts) == 2:
                ok, msg = os_ctl.write_file(parts[0], parts[1])
                resp = msg
            else:
                resp = "Usage: write file <path> <content>"
            action = "files"
        elif any(x in q for x in ["running", "processes", "top processes"]):
            resp = os_ctl.list_processes()
            action = "processes"
        elif "volume" in q:
            nums = re.findall(r'\d+', q)
            if nums:
                level = min(int(nums[0]), 100)
                os_ctl.set_volume(level=level)
                resp = f"Volume set to {level}%"
            elif "mute" in q:
                os_ctl.set_volume(mute=True)
                resp = "Muted"
            elif "unmute" in q:
                os_ctl.set_volume(mute=False)
                resp = "Unmuted"
            action = "volume"
        elif "brightness" in q:
            nums = re.findall(r'\d+', q)
            if nums:
                level = min(int(nums[0]), 100)
                os_ctl.set_brightness(level)
                resp = f"Brightness set to {level}%"
            action = "brightness"
        elif "screenshot" in q:
            resp = os_ctl.screenshot()
            action = "screenshot"
        elif "clipboard" in q:
            if "copy" in q:
                text = query.split("copy", 1)[-1].strip() if "copy" in q else ""
                resp = os_ctl.clipboard(text=text) if text else "What to copy?"
            else:
                resp = f"Clipboard: {os_ctl.clipboard()}"
            action = "clipboard"
        elif "lock" in q and "screen" in q:
            os_ctl.run("loginctl lock-session 2>/dev/null || true")
            resp = "Locking screen..."
            action = "lock"
        elif "voice" in q:
            if "start" in q or "enable" in q or "on" in q:
                resp = voice.start()
            elif "stop" in q or "disable" in q or "off" in q:
                resp = voice.stop()
            elif "continuous" in q:
                resp = voice.enable_continuous()
            elif "normal" in q or "wake" in q:
                resp = voice.disable_continuous()
            elif "speak" in q or "tts" in q:
                if "off" in q or "disable" in q:
                    voice.tts_enabled = False
                    resp = "TTS disabled"
                elif "on" in q or "enable" in q:
                    voice.tts_enabled = True
                    resp = "TTS enabled"
            else:
                resp = "Voice: 'start voice', 'stop voice', 'continuous voice mode'"
            action = "voice"
        elif "security" in q or "firewall" in q:
            results = guardian.full_scan()
            lines = ["Security Scan Results:\n"]
            for name, result in results:
                lines.append(f"- {name}: {result}")
            resp = "\n".join(lines)
            action = "security"
        elif q in ("update", "update system", "upgrade"):
            _, resp = os_ctl.update_system()
            action = "update"
        elif q in ("help", "what can you do", "commands"):
            resp = ("Buddhi AI - Agentic Assistant\n\n"
                "AGENTIC: 'install vlc', 'update system', 'security scan', 'clean up disk', 'backup files', 'optimize system', 'enable tor'\n\n"
                "APPS: 'open browser', 'close firefox'\n\n"
                "SHELL: 'run df -h', 'execute show disk usage'\n\n"
                "SEARCH: 'search AI news', 'alternatives for Notion', 'summarize quantum computing'\n\n"
                "FILES: 'list files /home', 'read file /etc/hostname'\n\n"
                "SYSTEM: 'system status', 'battery', 'network info', 'running processes'\n\n"
                "CONTROLS: 'set volume 50%', 'set brightness 80%', 'screenshot', 'lock screen'\n\n"
                "VOICE: 'start voice', 'continuous voice mode', Say 'Buddhi' then command\n\n"
                "API: http://127.0.0.1:5210")
            action = "help"
        elif q in ("hello", "hi", "hey", "namaste", "namaskar", "pranam"):
            resp = "Namaste! I'm Buddhi, your Vajra OS assistant. Type 'help' to see what I can do."
            action = "greeting"
        elif "who are you" in q or "what are you" in q:
            resp = "I am Buddhi, the agentic AI of Vajra OS. I run entirely locally - no cloud, no tracking."
            action = "info"
        else:
            if llm.available():
                r = mem.recent(5)
                ctx = " ".join([f"{m['role']}: {m['content']}" for m in r[:-1]])
                lr = llm.generate(query, ctx)
                if lr:
                    resp = lr
                    action = "llm"
            if not resp:
                results = web.search(query)
                lines = [f"Results for '{query}':\n"]
                for i, r in enumerate(results[:5], 1):
                    lines.append(f"{i}. {r['title']}")
                    lines.append(f"   {r['content'][:250]}")
                    lines.append("")
                resp = "\n".join(lines)
                action = "search"

        if voice and voice.tts_enabled and len(resp) < 200:
            voice.speak(resp)
        mem.add("assistant", resp)
        return {"response": resp, "action": action, "query": query, "timestamp": datetime.now().isoformat()}

proc = Processor()

# ============================================================
#  REST API Handler
# ============================================================

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._json({"status": "ok"})

    def do_GET(self):
        if self.path == "/status":
            i = os_ctl.info()
            i["ai_version"] = VERSION
            i["ai_name"] = "Buddhi"
            i["voice_listening"] = voice.listening
            i["voice_continuous"] = voice.continuous_mode
            i["llm_available"] = llm.available()
            i["commands_processed"] = proc.command_count
            i["tasks_completed"] = len(mem.tasks_completed)
            i["guardian_monitoring"] = guardian.monitoring
            self._json({"status": "ok", "data": i})
        elif self.path == "/history":
            self._json({"status": "ok", "data": mem.recent(50)})
        elif self.path == "/help":
            self._json({"status": "ok", "data": proc.process("help")["response"]})
        elif self.path == "/system":
            self._json({"status": "ok", "data": os_ctl.info()})
        elif self.path == "/security":
            results = guardian.full_scan()
            self._json({"status": "ok", "data": [{"check": n, "result": r} for n, r in results]})
        elif self.path == "/processes":
            self._json({"status": "ok", "data": os_ctl.list_processes()})
        else:
            self._json({"error": "Not found. Try /status, /history, /help, /system, /security, /processes"}, 404)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
        try:
            data = json.loads(body) if body else {}
        except:
            self._json({"error": "Invalid JSON"}, 400)
            return

        if self.path == "/query":
            q = data.get("query", "")
            if not q:
                self._json({"error": "Missing 'query'"}, 400)
                return
            result = proc.process(q, data.get("user", "vajra"))
            self._json({"status": "ok", "data": result})
        elif self.path == "/voice/start":
            self._json({"status": "ok", "msg": voice.start()})
        elif self.path == "/voice/stop":
            self._json({"status": "ok", "msg": voice.stop()})
        elif self.path == "/voice/continuous":
            self._json({"status": "ok", "msg": voice.enable_continuous()})
        elif self.path == "/voice/normal":
            self._json({"status": "ok", "msg": voice.disable_continuous()})
        elif self.path == "/voice/speak":
            text = data.get("text", "")
            voice.speak(text)
            self._json({"status": "ok", "msg": f"Spoke: {text}"})
        elif self.path == "/voice/tts/on":
            voice.tts_enabled = True
            self._json({"status": "ok", "msg": "TTS enabled"})
        elif self.path == "/voice/tts/off":
            voice.tts_enabled = False
            self._json({"status": "ok", "msg": "TTS disabled"})
        elif self.path == "/agentic":
            task = data.get("task", "")
            if not task:
                self._json({"error": "Missing 'task'"}, 400)
                return
            result = planner.plan_and_execute(task)
            self._json({"status": "ok", "data": result})
        elif self.path == "/security/scan":
            results = guardian.full_scan()
            self._json({"status": "ok", "data": [{"check": n, "result": r} for n, r in results]})
        elif self.path == "/security/monitor/start":
            self._json({"status": "ok", "msg": guardian.start_monitor()})
        elif self.path == "/security/monitor/stop":
            self._json({"status": "ok", "msg": guardian.stop_monitor()})
        elif self.path == "/install":
            pkg = data.get("package", "")
            if not pkg:
                self._json({"error": "Missing 'package'"}, 400)
                return
            ok, msg = os_ctl.install(pkg)
            self._json({"status": "ok" if ok else "error", "data": msg})
        elif self.path == "/run":
            cmd = data.get("command", "")
            if not cmd:
                self._json({"error": "Missing 'command'"}, 400)
                return
            ok, out = os_ctl.run_safely(cmd)
            self._json({"status": "ok" if ok else "error", "data": out})
        elif self.path == "/search":
            q = data.get("query", "")
            if not q:
                self._json({"error": "Missing 'query'"}, 400)
                return
            results = web.search(q)
            self._json({"status": "ok", "data": results})
        elif self.path == "/context/clear":
            mem.clear()
            self._json({"status": "ok", "msg": "Memory cleared"})
        else:
            self._json({"error": "Not found"}, 404)

# ============================================================
#  CLI Interface
# ============================================================

def cli():
    print(f"""
  ========================================
    Vajra OS - Buddhi AI v{VERSION}
    Supreme Intelligence
    Agentic - Voice - Privacy - Local
  ========================================

  Type 'help' for commands, 'exit' to quit.
  Say 'Buddhi' for voice commands.
""")
    while True:
        try:
            q = input("buddhi@vajra:~$ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNamaste!")
            break
        if not q:
            continue
        if q.lower() in ("exit", "quit", "bye"):
            print("Namaste!")
            break
        r = proc.process(q)
        print(f"\n{r['response']}")

# ============================================================
#  Main Entry
# ============================================================

def main():
    log(f"Buddhi AI v{VERSION} ('{CODENAME}') starting...", "INFO")
    if "--service" in sys.argv or "--daemon" in sys.argv:
        if CONFIG["voice_enabled"]:
            threading.Thread(target=voice.loop, daemon=True).start()
        if CONFIG["auto_fix"]:
            threading.Thread(target=guardian.start_monitor, daemon=True).start()
        try:
            server = HTTPServer((CONFIG["api_host"], CONFIG["api_port"]), Handler)
            log(f"API server on http://{CONFIG['api_host']}:{CONFIG['api_port']}", "INFO")
            server.serve_forever()
        except KeyboardInterrupt:
            log("Shutting down...", "INFO")
    else:
        cli()

if __name__ == "__main__":
    main()
