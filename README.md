# dsh-turn-events

**Know when DeepSeek Harness is done — from another agent, a script or CI.**

`dsh-turn-events` is a [DeepSeek Harness](https://www.npmjs.com/package/@deepseek-ai/dsh) (dsh) plugin that writes one JSON line every time a dsh agent finishes a turn. Other programs react to that line event-driven: a Claude Code Monitor wakes on it, a `claude -p` run or shell script blocks on it with the bundled `dsh-wait-turn`, and `dsh-turns` reads back what dsh answered.

```json
{"ts":"2026-11-06T13:16:30.877Z","event":"turn-stopping","session_id":"session-d06e3c3a-…","cwd":"/work/repo","turn":6,"agent_preset":"standard"}
```

## Why

dsh can run long, multi-step work in the web UI, over ACP (`dsh --profile acp`, used by acpx and editors) or headless. When another agent hands dsh a task, it needs to know when dsh is finished without polling and without a human watching a browser tab.

The obvious route — dsh's Claude Code hook bridge with a `Stop` hook — does not work for this: dsh runs hook commands inside its file sandbox, which denies every write (we measured `Operation not permitted` for `~/.dsh`, `~/.local/state` and `/tmp`, even in full-access sessions). This plugin instead runs in the dsh host process, so it needs no shell, no hook bridge and no change to the sandbox.

## How it differs from dsh notification plugins

Existing plugins notify **people**: desktop toasts and sounds (`dsh-notify-tray`, `dsh-notification`, `dsh-notify-plugin`), browser badges (`@zhanghanxuan/dsh-notify`), or chat and push services (`dsh-notify-me`, `dsh-notify-plugin`'s Telegram/WeCom). Others go the other way, sending work **into** dsh (`dsh-inbox-mcp`, `dsh-a2a-server`) or waking a session on GitHub activity (`dsh-session-superagent`).

`dsh-turn-events` is for **programs**:

| | dsh-turn-events | typical notify plugin |
|---|---|---|
| Output | local JSONL event stream, one line per turn | toast, sound, chat message |
| Consumer | other agents, scripts, CI | a person |
| Waiting on it | `dsh-wait-turn` (kernel-event wait), `tail -F` | — |
| Shell commands | none | usually `osascript` / `notify-send` |
| Network | none | often webhooks / chat APIs |
| Sandbox / hooks | not involved | — |

It pairs with them rather than replacing them.

## Install

Requires dsh 0.2.x and Node ≥ 24.9.

```bash
dsh plugin --profile web add github:ahmedibrahim085/dsh-turn-events
```

Repeat for every profile whose turns you want to see (for example `--profile acp`). The package's bundle layer mounts the plugin; restart the dsh host afterwards. Check it:

```bash
tail -1 ~/.local/state/dsh-events/turns.jsonl    # after any turn: a fresh line
```

The CLIs live in the package's `bin/`. Put them on your PATH, for example:

```bash
ln -s ~/.dsh/profiles/web/node_modules/dsh-turn-events/bin/dsh-wait-turn ~/.local/bin/
ln -s ~/.dsh/profiles/web/node_modules/dsh-turn-events/bin/dsh-turns ~/.local/bin/
```

They need Python 3; `dsh-turns` also needs the `zstd` CLI (dsh compresses its session logs).

## Use

**Be told when any dsh turn finishes** (Claude Code Monitor, a terminal, a log shipper):

```bash
tail -n 0 -F ~/.local/state/dsh-events/turns.jsonl
```

**Block until a specific turn finishes** (`claude -p`, scripts, CI):

```bash
dsh-wait-turn --cwd "$PWD" --timeout 1800      # or --session <dsh session id>
```

Exits 0 with the event line when a matching turn finishes, 2 on timeout. On macOS/BSD it sleeps on a kernel kqueue watch, so waiting costs no CPU; on other systems it checks the file size once a second.

**Read what dsh answered:**

```bash
dsh-turns --session <session_id>               # or --since 10m
```

Example with [acpx](https://www.npmjs.com/package/acpx): queue a long dsh task, wait for it, read the result.

```bash
acpx dsh sessions new --name build
acpx --approve-all dsh prompt -s build --no-wait "run the test suite and fix failures"
dsh-wait-turn --cwd "$PWD" --timeout 3600 && dsh-turns --since 1h
```

acpx's session id differs from dsh's, so match on `--cwd` when you started the session through acpx.

## Configuration

| Setting | Default | How to change |
|---|---|---|
| Event file | `~/.local/state/dsh-events/turns.jsonl` | `config.file` on the `dsh-turn-events` entry in your profile's `cordis.patch.yml`, or `DSH_TURN_EVENTS_FILE` (read by the plugin and by `dsh-wait-turn`) |

```yaml
# ~/.dsh/profiles/web/cordis.patch.yml
- id: dsh-turn-events
  config:
    file: /path/to/turns.jsonl
```

## Event fields

| Field | Meaning |
|---|---|
| `ts` | ISO time the turn stopped |
| `event` | always `turn-stopping` |
| `session_id` | dsh session id (directory name under `~/.dsh/sessions/<workspace>/`) |
| `cwd` | the session's working directory |
| `turn` | turn number within the session |
| `agent_preset` | the session's agent preset, when dsh records one |

## Safety

- Observes only: it never steers, blocks or edits a turn, and runs no shell commands.
- Writes one local file with mode `0600`; no network.
- A failed write (full disk, bad path) is logged as a warning and never breaks the session.

## Limits

- It listens to dsh's internal `agent/turn-stopping` event, which is not a documented public API. A dsh release may rename it; after updating dsh, run one turn and check the file gets a line.
- Only profiles that list the bundle emit events.
- Tested on macOS with dsh 0.2.2-rc.1 and Node 26, in web (including full-access) and ACP (read-only) sessions.

## Development

```bash
npm test     # node --test (plugin) + sh test/wait-turn.test.sh (CLI)
```

## License

MIT
