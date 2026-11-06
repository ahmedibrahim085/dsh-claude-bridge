# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) (while in 0.x, a minor release may break compatibility; such changes are marked **BREAKING**).

## [Unreleased]

## [0.4.1] - 2026-11-06

### Fixed

- `dsh-wait-turn` only reads an existing event file. It used to `touch` it, which dsh's sandboxed shell refuses (`PermissionError: Operation not permitted`), so dsh could not wait for Claude (or for another dsh session). Tested under a no-write `sandbox-exec` profile and live from a dsh turn.

## [0.4.0] - 2026-11-06

### Added

- Claude "done" signal: `claude-turn-event`, a Stop hook that writes one JSON line per finished Claude Code turn (with its final reply, first 8000 characters) to `~/.local/state/claude-events/turns.jsonl`. It prints nothing and always exits 0, so it never blocks a turn.
- `setup` adds the hook to `~/.claude/settings.json` (backup first; other hooks keep their order; `CLAUDE_DONE=0` skips it); `doctor` checks it; `uninstall` removes only this entry.
- `dsh-wait-turn --claude` waits on Claude's events (`CLAUDE_TURN_EVENTS_FILE` overrides the path).
- Tests: hook script, settings merge and removal, `--claude` wait; `clean-install.sh` checks the hook is added and removed.

## [0.3.0] - 2026-11-06

### Added

- dsh can message a **running** Claude Code session: tool `send_to_claude` (`message`, optional `cwd`) in every configured profile, through dsh's MCP client and the new `bin/dsh-claude-channel` server. The message arrives at once, even in an idle session, as a Claude Code channel event.
- `claude-dsh`: starts Claude Code with that channel loaded for this session only (`--mcp-config`), so other sessions start nothing (the server is about 37 MB per session). Uses Claude Code channels, a research preview.
- `CHANNEL=1|0` in the config; `setup` writes `~/.config/dsh-claude-bridge/channel-mcp.json`, `doctor` checks it, `uninstall` removes it.
- Tests: 5 channel-server tests with real processes and sockets; setup/uninstall tests; `clean-install.sh` checks the new pieces.

## [0.2.4] - 2026-11-06

### Added

- `dsh-claude-bridge uninstall [--dry-run] [--purge]`: removes only what `setup` made (plugin and managed block per profile, links, skill, acpx and mcacp `dsh` agents, and mcacp when nothing else uses it). `--purge` also deletes the config, turn events and helper state. `test/clean-install.sh` now uninstalls, checks nothing is left, and reinstalls.

### Fixed

- The CLI usage text listed a `setup --yes` flag that does not exist; it now shows `setup [--source SPEC]` and `uninstall`.

## [0.2.3] - 2026-11-06

### Changed

- The `dsh-harness` skill sends three or more parallel dsh sessions to mcacp, which runs them in one dsh process (16 sessions: 502 MB) instead of acpx's one process per session (16 sessions: 5.2 GB). It tells Claude to shut mcacp's agent down when the work is done.

### Added

- Eval case `parallel-fanout-uses-mcacp`.
- Docs: measured helper cost (about 200 MB each), how to raise the helper cap past 8, and both directions under load at once.

## [0.2.2] - 2026-11-06

### Added

- `setup` upgrades a profile whose plugin is pinned to an older release; `doctor` warns about an old pin.
- Docs: measured parallel limits for both directions (README Limits, skill gotchas, MAINTENANCE).

### Changed

- `setup` replaces old symlinks in place and moves only real files or folders to a backup dir outside the link dir (`~/.local/state/dsh-claude-bridge/backups`, `~/.claude/skills-backup`).

### Fixed

- `doctor --live` deletes the dsh session its test turn created; it used to leave one behind on every run.
- `npm test` runs on Node 26 (`node --test test/` stopped accepting a directory).

## [0.2.1] - 2026-11-06

### Fixed

- `setup` moves an existing `~/.claude/skills/dsh-harness` to `~/.claude/skills-backup/` instead of renaming it inside `skills/`, where Claude Code would load both copies.

## [0.2.0] - 2026-11-06

### Changed

- **BREAKING:** renamed from `dsh-turn-events` to `dsh-claude-bridge`, one package for everything that connects Claude Code and dsh. The plugin id is now `dsh-claude-bridge`; `setup` removes the old `dsh-turn-events` entry from your profiles.

### Added

- `dsh-claude-bridge doctor [--live]`: checks Node, dsh, pnpm, zstd, the config, each profile (managed block, plugin loaded, one dsh copy), acpx and its `dsh` agent, the CLIs, the skill and mcacp; `--live` runs one real dsh turn and checks its event.
- `dsh-claude-bridge setup`: installs or repairs everything doctor checks, from one config file (`~/.config/dsh-claude-bridge/config`). Writes a marked block per profile and refuses to override hand-written entries with the same ids. Safe to re-run; exits non-zero when a step fails.
- `dsh-claude-bridge run --profile P`: starts dsh with a clean environment; the provider key reaches dsh only as `BRIDGE_PROVIDER_KEY`.
- Claude Code helpers on two brains: `subagent_claude_code` (your provider; its own config dir, so a claude.ai login cannot outrank the provider key) and `subagent_claude_code_claude` (Claude, with your Claude Code login). Default permission mode `auto`.
- ACP default model: the managed block sets the `acp` entry, which ACP sessions use instead of `agent-default-model`.
- One dsh copy per profile: `setup` links `@deepseek-ai/dsh` to the global install when a plugin pulls a second copy, which breaks settings saves.
- The `dsh-harness` skill ships in the package (`skills/`), with 4 eval cases; it runs `doctor` first.
- `MAINTENANCE.md`: what a dsh, Claude Code, acpx or mcacp update can break, how it shows, and the fix.
- Tests: 5 plugin, 3 wait-CLI and 10 bridge unit tests; `test/clean-install.sh` installs into a throwaway HOME and passes `doctor --live`.

### Fixed

- Provider `ANTHROPIC_*` variables no longer leak into every Claude Code helper (`run` starts dsh with a clean environment).

### Security

- mcacp is installed with `zod >= 4.6.6`; upstream pins a `zod` version with 2 high-severity advisories.

## [0.1.0] - 2026-11-06

First release, as `dsh-turn-events`.

### Added

- Plugin `dsh-turn-events`: on every finished agent turn (`agent/turn-stopping`), appends one JSON line `{"ts","event","session_id","cwd","turn","agent_preset"}` to `~/.local/state/dsh-events/turns.jsonl` (override with `config.file` or `DSH_TURN_EVENTS_FILE`). Runs in the dsh host process: no shell, no hook bridge, no sandbox change; it only observes, and write failures are logged, not thrown.
- `dsh-wait-turn`: blocks until the next matching turn finishes (`--session` matches any part of the id, `--cwd`, `--timeout`), prints its event and exits 0, or exits 2 on timeout. Event-driven on macOS/BSD (kqueue); 1-second size check elsewhere.
- `dsh-turns`: one-shot lookup of finished turns with each turn's reply text, read from dsh's own session logs (needs the `zstd` CLI).
- Installable as a dsh bundle (`dsh.bundle.patch`); tested on dsh 0.2.2-rc.1, Node 26 and macOS.

Known limit: the plugin listens to dsh's internal `agent/turn-stopping` event, which is not a documented public API.

[Unreleased]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ahmedibrahim085/dsh-claude-bridge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ahmedibrahim085/dsh-claude-bridge/releases/tag/v0.1.0
