# Claude in Feishu

把 Claude Code 装进飞书。手机发任务，操作本地 Mac，管理飞书文档和日历，每次会话自动记录踩坑日志。

## What it does

```
📱 Phone (Feishu/Discord)
    ↓ send message
🖥️ Local daemon (Node.js)
    ↓ spawn session
🤖 Claude Code CLI
    ↓ execute tools
💻 Your Mac + Feishu API
    ↓ on exit
📝 Auto-journal (Haiku summary)
```

### Capabilities

| Feature | Description |
|---|---|
| **Mobile → Claude Code** | Send tasks from phone, get results back in chat |
| **Feishu Docs** | Create, read, search, append, move documents |
| **Feishu Calendar** | Create events, list schedules |
| **Send files to phone** | Upload images/files to Feishu chat for review |
| **Screenshot review** | Claude takes screenshots of local apps/web pages and sends to Feishu for product review from phone |
| **Cross-session visibility** | Sessions run in tmux, can read each other |
| **Auto-journaling** | Every session auto-summarized with tags and reflections |

## Quick Start

### 1. Install

```bash
# Clone
git clone https://github.com/imvanessali/claude-in-feishu.git
cd claude-in-feishu

# Install dependencies
npm install
npm run build
```

### 2. Configure

Create `~/.claude-in-feishu/config.env`:

```env
# Channels (comma-separated: feishu, discord, telegram)
CTI_ENABLED_CHANNELS=feishu

# Feishu (create app at https://open.feishu.cn/app)
CTI_FEISHU_APP_ID=your_app_id
CTI_FEISHU_APP_SECRET=your_app_secret
CTI_FEISHU_DOMAIN=https://open.feishu.cn

# Discord (optional)
CTI_DISCORD_BOT_TOKEN=your_bot_token
CTI_DISCORD_ALLOWED_USERS=your_user_id

# Claude settings
CTI_DEFAULT_WORKDIR=/Users/yourname
CTI_DEFAULT_MODEL=claude-sonnet-4-20250514
CTI_DEFAULT_MODE=bypassPermissions
CTI_ENV_ISOLATION=inherit
```

### 3. Setup Feishu App

1. Go to [Feishu Open Platform](https://open.feishu.cn/app)
2. Create a Custom App
3. Enable **Bot** capability
4. Add permissions: `im:message`, `im:resource`, `drive:drive`, `calendar:calendar`
5. Configure Events → **Long Connection** mode
6. Subscribe to `im.message.receive_v1`
7. Publish and approve the app version
8. (Optional) Run OAuth for user-space docs: `FEISHU_APP_ID=xxx FEISHU_APP_SECRET=xxx python3 scripts/feishu_oauth.py`

> **Note:** Without OAuth, documents created by the bot live in the bot's space and are invisible to you. OAuth lets Claude create docs in your own Drive. See `references/setup-guides.md` for details.

### 4. Setup Journals

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash /path/to/claude-in-feishu/journals/journal.sh"
          }
        ]
      }
    ]
  }
}
```

### 5. Setup tmux wrapper

Add to `~/.zshrc`:

```bash
claude() {
  if [ -n "$TMUX" ]; then
    command claude "$@"
    return
  fi
  local i=0
  while tmux has-session -t "claude-$i" 2>/dev/null; do
    i=$((i + 1))
  done
  local sess="claude-$i"
  tmux new-session -s "$sess" -e "CLAUDE_TMUX_SESSION=$sess" "command claude $*; zsh"
}
```

### 6. Start

```bash
bash scripts/daemon.sh start
```

## Usage

### From phone
Just message the bot in Feishu/Discord. It will:
- Spawn a Claude Code session on your Mac
- Execute whatever you ask
- Send results (text, images, files) back to chat

### Feishu toolkit
```bash
# Docs
python3 scripts/feishu_docs.py create "Meeting Notes"
python3 scripts/feishu_docs.py search "周报"
python3 scripts/feishu_docs.py append <doc_id> "New content"

# Calendar
python3 scripts/feishu_docs.py event_create "Standup" "2026-03-20T10:00:00+08:00" "2026-03-20T10:30:00+08:00"

# Send files to phone
python3 scripts/feishu_docs.py send_image <chat_id> /path/to/screenshot.png
python3 scripts/feishu_docs.py send_file <chat_id> /path/to/report.pdf
```

### Session journals

Journals are auto-generated on session exit:
- **Index**: `~/.claude/journals/INDEX.md` — scan tags to find relevant past sessions
- **Full logs**: `~/.claude/journals/<date>_<slug>.md` — background, process, decisions, reflections

## Architecture

### Components

```
claude-in-feishu/
├── src/                    # Bridge daemon (TypeScript)
│   ├── main.ts             # Entry point
│   ├── llm-provider.ts     # Claude SDK integration + auto-retry
│   ├── store.ts            # File-based persistence
│   ├── permission-gateway.ts # Async tool permissions via IM
│   ├── config.ts           # Config loader
│   └── logger.ts           # Secret-redacting log rotation
├── scripts/
│   ├── daemon.sh           # Start/stop/status
│   ├── doctor.sh           # Diagnostics
│   ├── build.js            # ESBuild bundler
│   └── feishu_docs.py      # Feishu API toolkit
├── journals/
│   ├── journal.sh          # Stop hook (extracts JSONL transcript)
│   ├── journal-worker.sh   # Async Haiku summarizer
│   └── extract-transcript.py # JSONL → readable text
└── references/
    └── setup-guides.md     # Platform setup instructions
```

### Key design decisions

- **JSONL-first journaling**: Reads Claude Code's native `.jsonl` session files instead of relying on tmux capture (tmux is fallback)
- **Async journal generation**: Stop hook returns immediately, spawns background worker so exit isn't blocked
- **Auto-retry on stale sessions**: If `resume` fails with expired session ID, automatically starts fresh
- **Secret redaction**: All logs auto-mask tokens, API keys, passwords
- **Dedup**: Same session never journaled twice (marker files)

## Prerequisites

- macOS with [Claude Code](https://claude.com/claude-code) installed
- Node.js 20+
- Python 3
- tmux

## Credits

Built on top of [claude-to-im](https://github.com/op7418/claude-to-im) by op7418.

## License

MIT
