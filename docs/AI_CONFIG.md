# Vajra OS AI Configuration

Buddhi AI (बुद्धि) runs **100% locally** — no cloud, no API keys, no
telemetry. This page explains where its settings live and how to change
them.

## The three files

| File | Role |
|------|------|
| `ai/config.yaml` (repo) | Human-readable **defaults**, shipped with the OS |
| `/etc/vajra/ai-config.json` | The **runtime** config (JSON) |
| `ai/ai-settings-panel.py` | The settings panel that reads/writes the runtime config |

On first boot of an installed system, `system/vajra-first-boot.sh` seeds
`/etc/vajra/ai-config.json` from the defaults. After that, the settings
panel is the way to change things.

## Keys

| Key | Default | Meaning |
|-----|---------|---------|
| `ai_enabled` | true | Master switch |
| `voice_enabled` | true | Voice control daemon |
| `voice_wake_word` | `buddhi` | Wake word for voice activation |
| `voice_language` | `en-IN` | Voice language (10 Indian languages supported) |
| `proactive_enabled` | true | Proactive/agentic features master switch |
| `proactive_file_organizer` | true | Auto-organize downloads |
| `proactive_log_analyzer` | true | Watch logs for anomalies |
| `proactive_monitor` | true | System health monitoring + auto-fix |
| `code_review_enabled` | true | AI code reviewer |
| `security_alerts` | true | Security guardian alerts |
| `learning_assistance` | true | Study help (Vedic math, languages) |
| `auto_suggest` | true | Command suggestions in the shell |
| `privacy_mode` | `local-only` | Nothing leaves the machine |
| `model` | `buddhi-local` | Local model identifier (Ollama backend) |

## Changing settings

From the installed desktop: open the **AI Settings** app
(`ai-settings-panel.py`). Programmatically, edit
`/etc/vajra/ai-config.json` and restart the Buddhi service:

```bash
sudo systemctl restart vajra-buddhi-ai
```

In the live ISO session, run `buddhi` and use its settings commands; the
runtime file persists for the session.

## Privacy guarantee

`privacy_mode: local-only` is not cosmetic: Buddhi has no network client
for inference — voice, chat, and agent features all execute on your
machine. Web search features, when used, are explicit user actions you
can route through Tor (see [PRIVACY.md](PRIVACY.md)).

## Related

- `ai/buddhi-ai.py` — the engine (REST API on localhost:5210)
- `ai/voice-control-daemon.py` — wake-word daemon
- `ai/proactive/`, `ai/scheduler/`, `ai/widgets/` — agentic extensions
- [CUSTOMIZE.md](CUSTOMIZE.md) — making Vajra OS yours
