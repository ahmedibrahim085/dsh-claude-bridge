# Changelog

## 0.2.1 — 2026-11-06

- `setup` moves an existing `~/.claude/skills/dsh-harness` to `~/.claude/skills-backup/` instead of renaming it inside `skills/`, where Claude Code would load both copies.

## 0.2.0 — 2026-11-06

Renamed from `dsh-turn-events` to **`dsh-claude-bridge`**: one package for everything that connects Claude Code and dsh. The plugin id is now `dsh-claude-bridge`; `setup` removes the old `dsh-turn-events` entry from your profiles.

- **`dsh-claude-bridge doctor [--live]`**: checks Node, dsh, pnpm, zstd, the config, each profile (managed block, plugin loaded, one dsh copy), acpx and its `dsh` agent, the CLIs, the skill and mcacp; `--live` runs one real dsh turn and checks its event.
- **`dsh-claude-bridge setup`**: installs or repairs everything doctor checks, from one config file (`~/.config/dsh-claude-bridge/config`). Writes a marked block per profile and refuses to override hand-written entries with the same ids. Safe to re-run; exits non-zero when a step fails.
- **`dsh-claude-bridge run --profile P`**: starts dsh with a clean environment; the provider key reaches dsh only as `BRIDGE_PROVIDER_KEY`. Fixes provider `ANTHROPIC_*` variables leaking into every Claude Code helper.
- **Claude Code helpers on two brains**: `subagent_claude_code` (your provider; own config dir so a claude.ai login cannot outrank the provider key) and `subagent_claude_code_claude` (Claude, your Claude Code login; no `CLAUDE_CONFIG_DIR`, which breaks the keychain lookup). Default permission mode `auto`.
- **ACP default model**: the managed block sets the `acp` entry, which ACP sessions use instead of `agent-default-model`.
- **One dsh copy per profile**: setup links `@deepseek-ai/dsh` to the global install when a plugin pulls a second copy (which breaks settings saves).
- **mcacp**: installed with `zod >= 4.6.6` (upstream pins a version with 2 high advisories) and registered in Claude Code.
- **`dsh-harness` skill** shipped in the package (`skills/`), with 4 eval cases; it runs `doctor` first.
- **MAINTENANCE.md**: what a dsh, Claude Code, acpx or mcacp update can break, how it shows, and the fix.
- Tests: 5 plugin, 3 wait-CLI, 10 bridge unit tests; `test/clean-install.sh` installs into a throwaway HOME and passes `doctor --live`.

## 0.1.0 — 2026-11-06

First release.

- **Plugin** (`dsh-turn-events`): on every finished agent turn (`agent/turn-stopping`), appends one JSON line `{"ts","event","session_id","cwd","turn","agent_preset"}` to `~/.local/state/dsh-events/turns.jsonl` (override with `config.file` or `DSH_TURN_EVENTS_FILE`). Runs in the dsh host process: no shell, no hook bridge, no sandbox change; observes only and never steers or blocks a turn; write failures are logged, not thrown.
- **`dsh-wait-turn`**: blocks until the next matching turn finishes (`--session` matches any part of the id, `--cwd`, `--timeout`), prints its event and exits 0, or exits 2 on timeout. Event-driven on macOS/BSD (kqueue); 1-second size check elsewhere.
- **`dsh-turns`**: one-shot lookup of finished turns with each turn's reply text, read from dsh's own session logs (needs the `zstd` CLI).
- Installable as a dsh bundle (`dsh.bundle.patch`); tested on dsh 0.2.2-rc.1, Node 26, macOS, in web (including full-access) and ACP (read-only) sessions.

Known limits: the plugin listens to dsh's internal `agent/turn-stopping` event, which is not a documented public API, so a future dsh release may need an update. Headless one-shot runs are not covered by bundle profiles that do not list this plugin.
