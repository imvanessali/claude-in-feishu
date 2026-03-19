---
name: claude-in-feishu
description: Turn Claude Code into a mobile-controlled autopilot — operate your Mac, Feishu docs/calendar, and local dev environment from your phone. Includes session journaling with auto-summarization.
argument-hint: "setup | start | stop | status | logs | doctor | journal"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

# Claude in Feishu

**把 Claude Code 装进飞书。** 手机发任务，操作本地 Mac，管理飞书文档和日历，截图验收产品，自动记录踩坑日志。

## Architecture

```
Phone (Feishu/Discord) → Local daemon → Claude Code CLI → Your Mac + Feishu API
                                                         ↓
                                              Auto-journal on exit (Haiku)
```

## Capabilities

| Capability | How |
|---|---|
| **Mobile → Claude Code** | IM bot daemon bridges messages to local Claude Code sessions |
| **Feishu Docs** | Create, read, search, append, move documents |
| **Feishu Calendar** | Create events, list calendars |
| **Send files to phone** | Upload images/files directly to Feishu chat |
| **Screenshot review** | Take screenshots of local apps, send to Feishu for mobile product review |
| **Cross-session visibility** | All sessions run in tmux, can read each other |
| **Session journals** | Stop hook auto-summarizes every session via Haiku |

## Subcommand: `setup`

When the user runs `/claude-in-feishu setup`, execute this interactive wizard step by step.
Use AskUserQuestion for each step. Do NOT skip steps or ask multiple questions at once.

### Step 0: Prerequisites Check

Run these checks automatically (no user input needed):
```bash
node --version    # Must be >= 20
python3 --version # Must be >= 3.8
which tmux        # Must exist
which claude      # Must exist
```
If any fails, tell the user what to install and stop.

### Step 1: Choose IM Platform

Ask: "你要连接哪个 IM 平台？(feishu / discord / telegram，可以逗号分隔选多个)"

Default: feishu

### Step 2: Feishu Setup (if feishu selected)

**Step 2a**: Show the user these instructions, then ask for App ID:

> 请按以下步骤创建飞书应用：
> 1. 打开 https://open.feishu.cn/app → 创建自建应用
> 2. 在「凭证与基础信息」页找到 **App ID** 和 **App Secret**
>
> 请输入你的 Feishu App ID（格式：cli_xxxxxxxxxx）：

**Step 2b**: Ask for App Secret:
> 请输入 App Secret：

**Step 2c**: Tell the user to configure permissions, then ask to confirm:

> 现在请配置权限。在应用的「权限管理」页面，点击「批量开通」，粘贴以下 JSON：
>
> ```json
> {
>   "scopes": {
>     "tenant": [
>       "im:message", "im:message:send_as_bot", "im:message.p2p_msg:readonly",
>       "im:message.group_at_msg:readonly", "im:message:readonly", "im:resource",
>       "im:chat.access_event.bot_p2p_chat:read", "im:chat.members:bot_access",
>       "drive:drive", "drive:drive:readonly", "sheets:spreadsheet",
>       "bitable:app", "calendar:calendar", "calendar:calendar:readonly"
>     ],
>     "user": [
>       "drive:drive", "sheets:spreadsheet", "bitable:app",
>       "calendar:calendar", "calendar:calendar:readonly"
>     ]
>   }
> }
> ```
>
> ⚠️ **注意**：`user` 权限是用于 OAuth 授权后以用户身份操作文档/日历，后续步骤会引导你完成授权。
>
> 完成后回复 "ok"

**Step 2d**: Tell user to enable bot and events:

> 接下来：
> 1. 进入「添加应用能力」→ 开启**机器人**
> 2. 进入「事件与回调」→ 请求方式选择**长连接**
> 3. 添加事件 `im.message.receive_v1`
> 4. 创建版本并发布（需管理员审批）
>
> 全部完成后回复 "ok"

**Step 2e** (optional): Ask for Feishu domain:
> Feishu 域名（直接回车使用默认 https://open.feishu.cn，国际版用 https://open.larksuite.com）：

**Step 2f**: OAuth authorization for user-space documents and calendar:

> ⚠️ **重要：Bot 空间 vs 用户空间**
>
> 飞书应用有两种 token：
> - **tenant_access_token**（Bot token）：用它创建的文档和日历事件存在 Bot 的空间里，**用户看不到**
> - **user_access_token**（用户 token）：用它创建的文档在**你自己的云盘**里，直接可见
>
> 如果你需要用 Claude 创建飞书文档并在手机上查看，需要完成 OAuth 授权。
>
> 是否现在进行 OAuth 授权？(y/n，默认 y)

If yes, run:
```bash
cd <skill_directory>
FEISHU_APP_ID=$APP_ID FEISHU_APP_SECRET=$APP_SECRET python3 scripts/feishu_oauth.py
```
This will open a browser window for OAuth authorization. The user_access_token will be saved to `~/.claude-in-feishu/feishu_user_token.json`.

**Step 2g**: Shared calendar setup for event visibility:

> **日历可见性**：即使用了 user_access_token，Bot 创建的日历事件默认在 Bot 的日历上。
> 推荐做法是创建一个**共享日历**：
>
> 1. 在飞书日历中新建一个日历（如「Claude 任务」）
> 2. 记下这个日历的 calendar_id（可通过 `python3 scripts/feishu_docs.py cal_list` 查看）
> 3. Bot 创建事件时指定这个 calendar_id，事件就会出现在你的日历中
>
> 是否跳过日历配置？(y/n，默认跳过)

If the user provides a calendar_id, save it to config.env as `CTI_FEISHU_CALENDAR_ID`.

### Step 3: Discord Setup (if discord selected)

**Step 3a**: Show instructions, ask for bot token:
> 请创建 Discord Bot：
> 1. 打开 https://discord.com/developers/applications → New Application
> 2. 进入 Bot 页面 → Reset Token → 复制
> 3. 开启 Message Content Intent
> 4. 用 OAuth2 URL Generator 邀请到你的服务器（权限：Send Messages, Read Message History）
>
> 请输入 Bot Token：

**Step 3b**: Ask for allowed user IDs:
> 你的 Discord User ID（开启开发者模式后右键自己 → Copy User ID）。留空允许所有人：

### Step 4: Claude Settings

**Step 4a**: Ask for default model:
> 默认使用哪个模型？(sonnet / opus，默认 sonnet)：

**Step 4b**: Ask for working directory:
> Claude Code 默认工作目录（直接回车使用 $HOME）：

**Step 4c**: Ask for permission mode:
> 权限模式？(bypassPermissions = 不弹确认 / default = 每次确认，默认 bypassPermissions)：

### Step 5: Write Config

Based on collected answers, write `~/.claude-in-feishu/config.env`:
```bash
mkdir -p ~/.claude-in-feishu
chmod 700 ~/.claude-in-feishu
# Write config.env with collected values
chmod 600 ~/.claude-in-feishu/config.env
```

### Step 6: Install Dependencies & Build

```bash
cd <skill_directory>
npm install
npm run build
```

### Step 7: Setup Journals

Automatically:
1. Create `~/.claude/journals/` directory
2. Copy journal.sh, journal-worker.sh, extract-transcript.py
3. Add Stop hook to `~/.claude/settings.json` (merge with existing hooks)
4. Create INDEX.md

### Step 8: Setup tmux Wrapper

Check if the claude() function already exists in ~/.zshrc or ~/.bashrc.
If not, ask:
> 是否添加 tmux 自动包装到你的 shell 配置？这样所有 claude 会话都在 tmux 里运行，可以互相查看。(y/n，默认 y)

If yes, append the claude() function to the appropriate rc file.

### Step 9: Setup launchd (auto-start)

Ask:
> 是否设置开机自启动？daemon 会在系统启动时自动运行。(y/n，默认 y)

If yes, create and load the launchd plist.

### Step 10: Validate & Start

1. Run `scripts/doctor.sh` to validate everything
2. Start the daemon with `scripts/daemon.sh start`
3. Show status and tell user to send a test message from their phone

Tell user:
> ✅ 配置完成！现在打开飞书，给机器人发一条消息试试。
> 如果遇到问题，运行 `/claude-in-feishu doctor` 诊断。

## Subcommand: `start`

```bash
cd <skill_directory> && bash scripts/daemon.sh start
```

## Subcommand: `stop`

```bash
cd <skill_directory> && bash scripts/daemon.sh stop
```

## Subcommand: `status`

```bash
cd <skill_directory> && bash scripts/daemon.sh status
```
Also show: active bindings from `~/.claude-in-feishu/data/bindings.json`

## Subcommand: `logs`

```bash
cd <skill_directory> && bash scripts/daemon.sh logs ${ARGS:-50}
```

## Subcommand: `doctor`

```bash
cd <skill_directory> && bash scripts/doctor.sh
```

## Subcommand: `journal`

Manually trigger journal generation for the current session:
1. Get current session ID from environment or Claude internals
2. Run `extract-transcript.py` on the session JSONL
3. Run `journal-worker.sh` to generate summary
4. Show the generated INDEX entry

## Components

### 1. IM Bridge (`src/`)
Node.js daemon using `claude-to-im` + `@anthropic-ai/claude-agent-sdk`:
- **llm-provider.ts** — Spawns Claude Code via SDK, auto-retries on stale sessions
- **store.ts** — File-based persistence (sessions, bindings, messages, audit)
- **permission-gateway.ts** — Async tool permission via IM buttons (5-min timeout)
- **config.ts** — Reads `~/.claude-in-feishu/config.env`
- **logger.ts** — Secret-redacting log rotation

### 2. Feishu Toolkit (`scripts/feishu_docs.py`)
Python CLI for Feishu Open API:
- `read/create/append/search/move/list` — Document ops
- `cal_list/event_create/event_list` — Calendar ops
- `send_image/send_file` — Send files to Feishu chat
- `mkdir/folders/organize` — Drive management

### 3. Session Journals (`journals/`)
Auto-journaling on session exit:
- **journal.sh** — Stop hook entry, extracts JSONL transcript, spawns worker
- **journal-worker.sh** — Calls Haiku to generate structured summary
- **extract-transcript.py** — Converts Claude Code `.jsonl` to readable text
- **INDEX.md** — Cover index with tags for retrieval

### 4. Tmux Wrapper
Shell function that auto-wraps `claude` in tmux sessions for cross-session visibility.

## Prerequisites

- macOS with Claude Code CLI installed
- Node.js 20+
- Python 3
- tmux
- A Feishu custom app (for Feishu integration)
- Discord bot token (for Discord integration)
