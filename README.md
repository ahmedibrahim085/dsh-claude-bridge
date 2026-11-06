# dsh-claude-bridge

**Claude Code ↔ DeepSeek Harness (dsh), both directions, with one setup command.**

| Direction | What you get |
|---|---|
| Claude Code → dsh | Multi-turn, resumable dsh sessions from Claude Code through [acpx](https://www.npmjs.com/package/acpx) (shell) or [mcacp](https://www.npmjs.com/package/mcacp) (MCP tools), plus headless one-shots |
| dsh → Claude Code: "done" | A dsh plugin writes one JSON line per finished turn; `dsh-wait-turn` blocks on it without polling, a Claude Code Monitor wakes on it, `dsh-turns` reads the answer |
| dsh → Claude Code: "do this" | Two Claude Code helpers inside dsh: `subagent_claude_code` on your dsh provider, `subagent_claude_code_claude` on Claude with your Claude Code login |
| Claude Code knows how | The `dsh-harness` skill: checks the setup first, then picks the right surface |

`dsh-claude-bridge doctor` checks every piece; `dsh-claude-bridge setup` installs or repairs what is missing and is safe to re-run.

## Install

Requires macOS or Linux, Node ≥ 24.9, Python 3, `zstd`, and [dsh 0.2.x](https://www.npmjs.com/package/@deepseek-ai/dsh) (`npm install -g @deepseek-ai/dsh`). Claude Code is optional (needed for the skill to be useful and for mcacp).

```bash
dsh plugin --profile web add github:ahmedibrahim085/dsh-claude-bridge#v0.2.4
~/.dsh/profiles/web/node_modules/dsh-claude-bridge/bin/dsh-claude-bridge setup
```

The first `setup` writes `~/.config/dsh-claude-bridge/config` and stops. Fill in your provider, run `setup` again, restart any running dsh host, then:

```bash
dsh-claude-bridge doctor --live      # every line [ok]; --live runs one real dsh turn
```

### Configuration

```ini
PROVIDER_ID=zai-glm                                   # any id; dsh shows it in the model list
PROVIDER_API=anthropic-messages
PROVIDER_BASE_URL=https://open.bigmodel.cn/api/anthropic
PROVIDER_KEY_FILE=~/.glm-env                          # an env file holding the key ...
PROVIDER_KEY_VAR=ANTHROPIC_AUTH_TOKEN                 # ... under this name (read at run time, never copied)
MODELS=glm-5.3 glm-5.3-flash                          # first = default
PROFILES=web acp headless
HELPERS=both                                          # provider | claude | both | none
HELPER_PERMISSION_MODE=auto                           # auto | acceptEdits | dontAsk | plan
MCACP=1
PASS_ENV=                                             # extra variables to pass into dsh
BIN_DIR=~/.local/bin
```

### Upgrade

Run the two install commands with the new tag. The new `setup` moves your other profiles to the same release and keeps your config:

```bash
dsh plugin --profile web add github:ahmedibrahim085/dsh-claude-bridge#v0.2.4
~/.dsh/profiles/web/node_modules/dsh-claude-bridge/bin/dsh-claude-bridge setup
```

Restart any running dsh host, then run `dsh-claude-bridge doctor --live`. Read [CHANGELOG.md](CHANGELOG.md) first for changes marked **BREAKING**.

### Uninstall

```bash
dsh-claude-bridge uninstall --dry-run    # list what would be removed; changes nothing
dsh-claude-bridge uninstall              # remove it; add --purge to delete your config and turn events too
```

`uninstall` removes only what `setup` made: the plugin and the managed block in each profile, the links and the skill, the acpx `dsh` agent, and mcacp's `dsh` agent (plus mcacp itself when no other agent uses it). Your own profile entries, dsh, pnpm and acpx stay. Restart any running dsh host afterwards.

### What `setup` does

- Links `dsh-claude-bridge`, `dsh-wait-turn` and `dsh-turns` into `BIN_DIR`, and the skill into `~/.claude/skills/dsh-harness`.
- Writes one marked block per profile into `~/.dsh/profiles/<p>/cordis.patch.yml`: your provider and default model, the ACP route, and the helpers. Your own entries stay untouched; if they set the same ids, setup stops and names them instead of overriding.
- Adds this plugin to each profile, installs dsh's Claude Code helper package when helpers are on, and keeps one dsh copy per profile.
- Installs pnpm and acpx if missing and registers the `dsh` agent in acpx; installs mcacp (with a patched `zod`) and registers it in Claude Code.

## Use

Start dsh through the bridge, so it gets a clean environment and your provider key:

```bash
dsh-claude-bridge run --profile web -- --no-open          # web UI
dsh-claude-bridge run --profile headless -- "summarise README.md"
```

From Claude Code (or any shell):

```bash
acpx dsh sessions new --name build
acpx --approve-all dsh prompt -s build --no-wait "run the tests and fix failures"
dsh-wait-turn --cwd "$PWD" --timeout 3600       # returns when that turn ends; exit 2 = timeout
dsh-turns --since 1h                            # what dsh answered
```

For several dsh sessions at once, use the mcacp MCP tools from Claude Code: all sessions share one dsh process. The `dsh-harness` skill does this on its own for three or more sessions.

Inside dsh, ask for a helper by name, e.g. "use subagent_claude_code_claude to review this diff". The helper runs in the background; its result arrives as a later turn.

Event line (`~/.local/state/dsh-events/turns.jsonl`):

```json
{"ts":"2026-11-06T13:16:30.877Z","event":"turn-stopping","session_id":"session-d06e3c3a-…","cwd":"/work/repo","turn":6,"agent_preset":"standard"}
```

## How it differs

dsh notification plugins (`dsh-notify-tray`, `dsh-notify-plugin`, `dsh-notify-me`, …) notify **people** with toasts, sounds or chat messages. Inbound bridges (`dsh-inbox-mcp`, `dsh-a2a-server`) send work **into** dsh. This bridge connects dsh and Claude Code **as programs**: a local event stream, a wait command, both-way delegation, and the setup that makes them work together.

## Safety

- The turn-events plugin only observes: no shell commands, no network, one local file (mode `0600`), and a failed write never breaks a turn.
- Keys stay in your key file; dsh receives them only as `BRIDGE_PROVIDER_KEY` at run time.
- The Claude Code helpers run **outside dsh's sandbox**. The default `auto` permission mode lets them edit and run commands unattended while Claude Code's classifier blocks risky actions; `bypassPermissions` is deliberately not offered.

## Limits

- Turn events use dsh's internal `agent/turn-stopping` event, which is not a public API. [MAINTENANCE.md](MAINTENANCE.md) lists every piece an update can break and the check for it.
- The provider helper needs an Anthropic-compatible endpoint (`PROVIDER_API=anthropic-messages`).
- The helper tools are added at host level; agent presets that list their own tool rows need a row for each helper.
- `dsh-wait-turn` uses kernel file events on macOS/BSD and a 1-second size check elsewhere.
- Parallel sessions, measured on a 24 GB, 14-core Mac with a GLM provider (2026-11-06):
  - **Claude Code → dsh**: through **mcacp** every session runs in one dsh process; 16 at once answered in 9 s at 502 MB, 32 sessions in one dsh process peaked at 478 MB. Through **acpx** each session is its own dsh process, about 320 MB; 16 at once answered in 18 s at 5.2 GB. The skill sends parallel work to mcacp.
  - **dsh → Claude Code** (helpers): **8 active helpers per root dsh session** by default; the 9th call is refused with `subagent limit reached (active child limit: 8)`. The cap is `maxActiveSubagents` on the `subagent` entry and can be raised: at 16, one session ran 12 helpers. Each helper is a Claude Code process, about 200 MB and about 1 core while it starts.
  - **Both at once**: 16 dsh sessions (4 clients × 4) plus 16 helpers (2 root sessions × 8) all answered; free memory went from 55 % to 51 %.
- Tested on macOS with dsh 0.2.2-rc.1, Claude Code 2.1.319, Node 26.

## Development

```bash
npm test                                  # plugin (node --test), wait CLI (sh), bridge (python unittest)
PROVIDER_ID=… PROVIDER_BASE_URL=… PROVIDER_KEY_FILE=… MODELS=… sh test/clean-install.sh   # throwaway HOME, real dsh turn
```

The `skills/dsh-harness/evals/` cases follow the `claude plugin eval` layout.

## Versioning

[Semantic Versioning](https://semver.org/); every release is listed in [CHANGELOG.md](CHANGELOG.md) and on the [releases page](https://github.com/ahmedibrahim085/dsh-claude-bridge/releases).

## License

MIT
