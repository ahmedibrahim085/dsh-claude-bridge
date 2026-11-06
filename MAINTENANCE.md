# What a dsh or Claude Code update can break, and how to check

Tested with dsh 0.2.2-rc.1, Claude Code 2.1.319, acpx 0.21.1, mcacp 0.1.3, Node 26, macOS.

After updating dsh, Claude Code, acpx or mcacp:

```bash
dsh-claude-bridge doctor --live
```

Then, in the dsh web UI, send one message in any session and toggle one setting (Settings saves are the first thing a duplicate dsh copy breaks).

| Piece | Why an update can break it | How it shows | Fix |
|---|---|---|---|
| **Turn events** (the dsh plugin) | It listens to dsh's internal `agent/turn-stopping` event and reads `agent.session.header`; neither is a documented public API | No new lines in `~/.local/state/dsh-events/turns.jsonl`; `dsh-wait-turn` times out | Find the event dsh's own `@deepseek-ai/dsh-hooks-claude-code` uses for `Stop` and update `index.mjs` |
| **dsh version range** | `engines.dsh` is `>=0.2.2-rc.1 <0.3.0`; dsh refuses plugins outside their range | Install or startup refuses the plugin as incompatible | Test on the new dsh, widen the range, release |
| **ACP default model** | ACP sessions take their model from the `acp` entry, not `agent-default-model`; the managed block sets both | ACP turns fail: `no API key for provider route "deepseek-official"` | Re-check the entry id in `dsh --profile acp --dump-config` |
| **Provider block** | The `llm-pi-ai` provider schema (`apiKeyEnv`, `api`, `baseURL`, `models`) belongs to dsh | The provider's models are missing from the model list | Update `managed_block()` in `bin/dsh-claude-bridge` |
| **One dsh copy per profile** | A plugin that depends on `@deepseek-ai/dsh` (e.g. `dsh-sdk-client`) installs a second copy; two `dsh-app-boot` copies make every settings save fail with `profile reload requires the root Include entry` | Settings don't save; the preview notice can't be dismissed | `setup` adds a pnpm override linking the global dsh; `doctor` flags the second copy |
| **Clean environment** | Provider settings must not be in dsh's environment as `ANTHROPIC_*`, or every Claude Code helper inherits them | The Claude helper answers as the provider model | Start dsh only through `dsh-claude-bridge run`; `ps eww` on the host must show no `ANTHROPIC_*` |
| **Provider helper** (`subagent_claude_code`) | Claude Code lets a claude.ai login in `~/.claude` outrank `ANTHROPIC_AUTH_TOKEN`; the helper gets its own config dir `~/.dsh/claude-code-provider` | `401` from the provider; dsh shows `stage: query-run; category: invalid-result` | Never log in to Claude inside that dir |
| **Claude helper** (`subagent_claude_code_claude`) | Setting `CLAUDE_CONFIG_DIR` at all, even to `~/.claude`, changes Claude Code's keychain lookup | `OAuth session expired and could not be refreshed` | The managed block sets no env for it; keep it that way |
| **Helper permission mode** | `auto` relies on Claude Code's classifier; the children run outside dsh's sandbox | Helpers stop running shell commands, or run more than expected | `HELPER_PERMISSION_MODE` in the bridge config |
| **acpx** | Argument order and flags can change between versions | `acpx … dsh …` prints help instead of running | `acpx --help`; update the skill |
| **mcacp** | Pinned on purpose: upstream ships an old `zod` with 2 high advisories; setup installs it with `zod >= 4.6.6` | `claude mcp get mcacp` not Connected; `npm audit` findings in `~/.local/share/mcacp` | Update there keeping the `overrides` block |
| **Helper concurrency** | dsh caps active helpers per root session at `maxActiveSubagents` (8 in 0.2.2-rc.1) | `subagent limit reached (active child limit: 8)` | Raise it in the `dsh-subagent` config if RAM allows (each helper is a Claude Code process) |
| **Plugin pin** | Each profile pins the plugin to a release tag; a newer bridge CLI does not update the pinned plugin on its own | `doctor` warns `plugin pinned to … this bridge is …` | `dsh-claude-bridge setup` re-adds the plugin at this release |
| **Hook bridge (not used)** | dsh runs Claude Code-style hook commands inside its sandbox, which denies every file write | — | That is why turn events are a native plugin |
