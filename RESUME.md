# Resume here

Handoff written 2026-11-13. Read this first, then the map issue. It points to the issues and files that hold the detail and does not repeat them.

## Where things stand

- **Released:** v0.5.0 is the latest release, and `main` is at the commit that adds this file. The tree is clean, with no open branches except the three `research/*` branches below.
- **Installed on the owner's Mac:** v0.5.0, dsh 0.2.2-rc.1, Claude Code 2.1.322.
- **Current effort: planning only.** No code is being written. The wayfinder map makes the backlog decision-complete, and building starts after it is done.
  - Map: [Wayfinder map: decision-complete backlog for dsh-claude-bridge (#8)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/8).
  - Its body holds the destination, the notes, a "Decisions so far" index, the fog ("Not yet specified") and "Out of scope". Load it first.

### Decisions closed (detail in each issue's resolution comment)

| Decision | Gist |
|---|---|
| [What the dsh web host API offers an outside program (#9)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/9) | The HTTP API works with a 30-day owner cookie, but it is not promised stable. |
| [Where the dsh MCP server gets its dsh from (#10)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/10) | One **broker** per user owns one dsh ACP process for all Claude sessions. It shuts down when idle and resumes sessions after a crash. |
| [Which tools and permission posture the dsh MCP server exposes (#11)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/11) | 19 of mcacp's 24 tools in 4 switchable groups. `DSH_PERMISSION` defaults to `workspace-write`; `permissionPolicy` defaults to `elicit`. |
| [Supported ways a claude -p worker can receive a push (#13)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/13) | A stream-json named pipe for workers dsh starts itself; a SendMessage relay for other workers. |
| [dsh marketplace listing rules (#15)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/15) | One PR to awesome-dsh-plugin, category `dev`. |

### Decisions still open (the frontier; each has a "Context for this decision" comment with the facts gathered)

1. [mcacp's future once the dsh MCP server exists (#12)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/12): grilling. Its blocker #11 is closed. This was the agreed next ticket.
2. [Which mechanism the claude -p fallback uses (#14)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/14): grilling, unblocked.
3. [Marketplace listing text and category (#16)](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/16): grilling, unblocked. The owner must approve the exact text before any PR (public post).

### Build tickets (native blockers wired; each already reflects the closed decisions)

| Ticket | Blocked by | Note |
|---|---|---|
| [#5 dsh MCP server, first slice: one dsh turn through the shared broker](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/5) | #2 (closed) | Ready to build once the map is done. |
| [#6 dsh MCP server: remaining tools and switchable tool groups](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/6) | #5 | |
| [#7 Make the dsh MCP server the default; mcacp optional](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/7) | #6, #12 | Update it after #12 closes. |
| [#3 claude -p fallback: dsh can message a headless Claude worker](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/3) | #14 | Its body predates #13; rewrite it after #14 closes. |
| [#4 List dsh-claude-bridge in the dsh plugin marketplace](https://github.com/ahmedibrahim085/dsh-claude-bridge/issues/4) | #16 | Public post, so the owner approves it. |

### Fog left on the map

How the `dsh` MCP server is tested end to end. Tools and broker are decided; what is still open is which checks run without a model call and which need a live dsh turn. Turn it into a ticket when it can be stated sharply.

## How to work the map (rules the owner set)

- Use the `mp-wayfinder` "Work through the map" mode, **one decision ticket per session**; research tickets are the exception.
  - Claim a ticket by assigning it to @me first.
  - Run the `grilling` and `domain-modeling` skills.
  - Ask the whole frontier in one round, giving a recommendation for each question.
  - Wait for the owner's answers.
- **Resolving a ticket:**
  1. Post a resolution comment with the evidence (command and output, or file:line).
  2. Close the issue by hand.
  3. Add one line to the map's "Decisions so far".
  4. Update the build tickets it affects, plus the fog.
- **Commit messages:** never write "Closes #N". It closed #2 early once.
- **Unproven claims:** mark anything not executed as INFERRED. dsh facts come from dsh's own code under `~/.npm-global/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/` (packages `dsh-acp`, `dsh-permission-presets`, `dsh-user-approval`, `dsh-sandbox-policy`).
- **Owner approval:** the owner approves each GitHub release and each public post (PR to another repo, listing).
- **Glossary:** use the terms in [GLOSSARY.md](GLOSSARY.md) (dsh side, Claude side, provider helper, Claude-login helper, done signal, channel, broker) and add new terms there as they are settled.

## Gotchas learned the hard way

- **One mcacp per Claude session.** Measured: 15 mcacp processes for 15 Claude sessions. "Shared dsh" in v0.2.3 means shared within one Claude session only; the broker (#10) fixes that.
- **dsh's ACP cannot set permissions per session.** `setConfigOption` accepts only model and reasoning, and dsh-acp never runs dsh's `/permission` command. The permission level is per dsh process.
- **The owner's dsh web host on port 3080 is not always up.** It was down on 2026-11-12. Restarting the host invalidates the token and cookie.
- **Killing processes:** kill only by an exact pid captured with `$!`, never `pkill` or `killall`. Background test commands must end with the test's own exit code, not a trailing `echo`.
- **The `research/*` branches** (`research/dsh-web-host-api`, `research/claude-p-push`, `research/dsh-marketplace-listing`) hold the long research files that the resolution comments link to. Keep them.

## Suggested skills

- `mp-wayfinder`: work the map (frontier ticket #12 first).
- `mattpocock-skills:grilling` and `mattpocock-skills:domain-modeling`: for each decision ticket.
- `mattpocock-skills:research`: only if a decision needs facts from outside this repo.
- `dsh-harness`: for any live dsh check.
- Once the map is done: `mp-implement`, `superpowers:test-driven-development` and `superpowers:verification-before-completion` to build #5.

## Not done in this session

- The retro (`mp-retro`) required after the second compaction has not been run.
