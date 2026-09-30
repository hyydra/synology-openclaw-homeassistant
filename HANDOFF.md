# Handoff: Synology + OpenClaw + Home Assistant

## Current State

### OpenClaw (Windows)
- **Version**: 2026.9.6
- **Gateway**: Stuck in crash loop — starts then exits code 1. Fix: `schtasks /Change /TN "OpenClaw Gateway" /RI 0` then restart.
- **Config**: `C:\Users\ptral\.openclaw\openclaw.json`

### Models (free only)
- **Primary**: `openrouter/meituan/longcat-2.0`
- **Fallbacks**: `openrouter/meta-llama/llama-3.3-70b:free`, `openrouter/deepseek/deepseek-r1:free`, `openrouter/google/gemini-flash-exp:free`
- **Alerts**: Built-in fallback/recovery notifications (automatic)

### MCP Servers
- **synology**: `rafalr100/synology-mcp` v0.4.0 — 71 tools (Docker, packages, users, storage, system). Requires `mcp<2` pin. Connects to `http://synpet.synology.me:5000` (user: peti)
- **home-assistant**: `ha-mcp` v3.5.1 — connects to `http://synpet.synology.me:8123`

### Telegram Bot
- **Bot**: @peti_nas_bot
- **Status**: Token received, channel config pending (gateway must be running)

### Synology NAS
- **Host**: `synpet.synology.me` (SSH port 32, user: peti)
- **DSM**: 7.4.1
- **Docker**: NOT installed — Container Manager needed from Package Center
- **Home Assistant**: Running in Docker on port 8123

## Pending Tasks

1. **Fix gateway crash loop** — remove scheduled task restart interval limit
2. **Install Container Manager** on Synology (Package Center, web UI only)
3. **Deploy OpenClaw in Docker** on Synology once Container Manager is installed
4. **Configure Telegram channel** in OpenClaw once gateway is stable
5. **Set up Synology Git** — already has remote `origin` pointing to `192-168-1-2.synpet.direct.quickconnect.to:8418`

## Key Files
- `~/.openclaw/openclaw.json` — main config
- `~/.openclaw/agents/coordinator/agent/models.json` — Ollama provider config
- `~/synology-mcp/` — full-featured Synology MCP source

## Credentials
- Synology: `synpet.synology.me:5000` (HTTP) / `:5001` (HTTPS), user `peti`
- Home Assistant: `synpet.synology.me:8123`, token in config
- Telegram: bot token in config
- OpenRouter: API key in env `OPENROUTER_API_KEY`
