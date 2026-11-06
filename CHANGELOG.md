# Changelog

## 0.1.0 — 2026-11-06

First release.

- **Plugin** (`dsh-turn-events`): on every finished agent turn (`agent/turn-stopping`), appends one JSON line `{"ts","event","session_id","cwd","turn","agent_preset"}` to `~/.local/state/dsh-events/turns.jsonl` (override with `config.file` or `DSH_TURN_EVENTS_FILE`). Runs in the dsh host process: no shell, no hook bridge, no sandbox change; observes only and never steers or blocks a turn; write failures are logged, not thrown.
- **`dsh-wait-turn`**: blocks until the next matching turn finishes (`--session` matches any part of the id, `--cwd`, `--timeout`), prints its event and exits 0, or exits 2 on timeout. Event-driven on macOS/BSD (kqueue); 1-second size check elsewhere.
- **`dsh-turns`**: one-shot lookup of finished turns with each turn's reply text, read from dsh's own session logs (needs the `zstd` CLI).
- Installable as a dsh bundle (`dsh.bundle.patch`); tested on dsh 0.2.2-rc.1, Node 26, macOS, in web (including full-access) and ACP (read-only) sessions.

Known limits: the plugin listens to dsh's internal `agent/turn-stopping` event, which is not a documented public API, so a future dsh release may need an update. Headless one-shot runs are not covered by bundle profiles that do not list this plugin.
