---
name: managing-daemon
description: "Monitors and manages the A.E.G.I.S. background processes. Use when the user asks about system health, wants to restart the AI, or check uptime."
---

# Managing Daemon

This skill provides control over the A.E.G.I.S. background environment (AEGIS-CORE) managed by PM2.

## Core Commands

- **Status Check**: `pm2 status AEGIS-CORE` (Check if the daemon is online)
- **Restart AI**: `pm2 restart AEGIS-CORE` (Use when the backend is unresponsive or settings change)
- **Stop AI**: `pm2 stop AEGIS-CORE` (Use to halt the background process)
- **View Logs**: `pm2 logs AEGIS-CORE --lines 50 --no-daemon` (Debug recent activity)

## Telemetry & Health

To get machine-readable telemetry data, use the JSON list format:
```powershell
pm2 jlist
```
This is useful for parsing memory usage, CPU load, and uptime for `AEGIS-CORE`.

## Usage Guidelines
- Always verify the process name is exactly `AEGIS-CORE`.
- If the daemon crashes repeatedly, check the combined logs at `~/.aegis/logs/combined.log`.
- Use `pm2 save` after any significant changes to persistent process settings.
