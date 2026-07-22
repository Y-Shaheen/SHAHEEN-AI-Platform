# SHAHEEN-AI-Platform

A self-hosted, agentic AI platform built on [AstrBot](https://github.com/AstrBotDevs/AstrBot) by Y. Z. A. SHAHEEN.

## Overview

Multi-platform LLM chatbot framework with a Python FastAPI backend and Vue 3 + Vuetify dashboard. Supports OpenAI, Claude, Gemini, Groq, DeepSeek, and many more providers. Integrates with Telegram, Discord, Slack, WeChat, and QQ. Includes a full Knowledge Base, plugin marketplace, MCP servers, agent orchestration, and now a built-in Git integration and interactive Terminal.

## Running the Project

The app starts automatically via the **Start AstrBot** workflow:

```bash
uv run python main.py
```

The dashboard is served at **port 6185**. On first run the pre-built WebUI is auto-downloaded from the AstrBot registry.

Default credentials are printed in the workflow console on first start (look for "Initial username / Initial password").

## Project Structure

```
astrbot/
  dashboard/
    api/          # FastAPI route modules
      git.py      # Git integration REST API (19 endpoints)
      terminal.py # Interactive terminal WebSocket + exec endpoint
      router.py   # API v1 router — registers all route modules
    services/     # Business logic services
  core/           # Bot engine (pipeline, agents, platforms, KB)
dashboard/
  src/
    views/
      GitPage.vue      # Git UI (status, log, branches, diff, remotes)
      TerminalPage.vue # Interactive terminal UI (WebSocket)
    router/
      MainRoutes.ts    # Frontend routes (/git, /terminal added)
    layouts/full/vertical-sidebar/
      sidebarItem.ts   # Navigation sidebar (Git & Terminal added)
    i18n/locales/      # en-US, zh-CN, ru-RU translations
```

## Key Features Added

### Git Integration (`/git`)
- **Status** — working-tree changes with ahead/behind tracking
- **Log** — commit history with author, date, message
- **Diff** — staged and unstaged diffs, per-file or full
- **Branches** — create, checkout, delete local branches
- **Commit** — stage all or specific files, write commit message
- **Pull / Push / Fetch** — remote operations
- **Clone** — clone any repository from the UI
- **Remotes** — list configured remotes
- **Conflict detection** — shows UU/AA/DD conflict markers
- **Stash** — push/pop stash

### Terminal (`/terminal`)
- **Interactive WebSocket terminal** — real-time streaming output
- **Command history** — ↑/↓ arrow navigation
- **Built-in `cd`** — tracks working directory across commands
- **Ctrl+C** — kill the running process
- **Ctrl+L** — clear the screen
- **ANSI colour rendering** — proper terminal colour output
- **Safe limits** — 128 KB output cap, 60s timeout, max 5 sessions

## API Endpoints

All routes are under `/api/v1` and require a system-scoped JWT:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/git/status` | Working tree status + branch |
| GET | `/git/log` | Commit history |
| GET | `/git/diff` | Diff (staged or unstaged) |
| GET | `/git/show` | Show a specific commit |
| GET | `/git/branches` | List branches |
| POST | `/git/checkout` | Checkout / create branch |
| POST | `/git/commit` | Stage and commit |
| POST | `/git/pull` | Pull from remote |
| POST | `/git/push` | Push to remote |
| POST | `/git/fetch` | Fetch from remote |
| POST | `/git/clone` | Clone a repository |
| GET | `/git/remotes` | List remotes |
| GET | `/git/repos` | Discover repos on disk |
| GET | `/git/conflicts` | Detect merge conflicts |
| POST | `/terminal/exec` | Run command, return output |
| WS | `/terminal/ws` | Interactive terminal stream |

## Environment Variables / Secrets

See README.md for the full list of supported API keys (LLM providers, search tools, bot tokens, database, etc.).

`SESSION_SECRET` is pre-configured as a Replit secret.

## User Preferences

- Keep the existing project architecture, branding, and naming exactly as-is.
- Do not rename files, folders, packages, modules, or classes.
- Preserve all README formatting, badges, and documentation.
- Commit only after tests pass; push to `origin main`.
- Use clear, descriptive commit messages.
