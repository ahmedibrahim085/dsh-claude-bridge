# Supported ways a `claude -p` worker can receive a push

Ticket: #13 (map #8). Date: 2026-11-12. Tested on Claude Code 2.1.322 (macOS), model haiku, hooks disabled in the throwaway workers (`--settings '{"disableAllHooks":true}'`). 9 test runs, all in a temp folder, all processes started by this research and removed afterwards.

Vocabulary: "channel" in this repo means dsh pushing into a running session (GLOSSARY.md). Claude Code's own session-to-session messaging is called "cross-session messaging" here, as the glossary asks.

Label rule: a statement with a command and output is measured. `INFERRED` means not executed.

## Answer in one table

| Mechanism | Works in `-p`? | Supported sender for a non-Claude program (dsh)? | Wakes an idle worker? |
|---|---|---|---|
| Cross-session messaging | Yes, with `crossSessionInbound: accept` | No documented send API. A short `claude -p` relay that calls `SendMessage` works (tested) | Yes (tested) |
| `--input-format stream-json` | Yes (documented, tested) | Yes: write JSON lines to the worker's stdin; a named pipe works (tested) | Yes (tested) |
| Monitor on a mailbox file | Yes, but every watch has a deadline | Yes: any program appends a line to the file | Yes while a watch is armed (tested); no after it expires (tested) |
| Stop hook that polls a mailbox | Yes (tested) | Yes: append a line to the file | Only while the hook is polling; the turn stays open meanwhile (tested) |
| Development-channels flag | No: ignored with `-p` | n/a | n/a |

## 1. Cross-session messaging into a `-p` worker

Documented: https://code.claude.com/docs/en/cross-session-messaging.md, section "Non-interactive sessions": Claude Code binds an inbox socket for a `claude -p` session like an interactive one, so a long-running `-p` worker can receive messages. `--bare` mode does not bind the socket. To take messages unattended, set `crossSessionInbound` to `accept` in the worker's `--settings` value. A `-p` session cannot show the approval dialog: a message held by the default rule is kept five minutes (`dialogExpiry`) and then dropped; a message held by an explicit `hold` never expires. Requires Claude Code 2.1.224 or later. Setting reference: https://code.claude.com/docs/en/settings-reference.md (`crossSessionInbound`: `accept`, `hold`, `refuse`).

Test of the receiving side. Worker A: `claude -p --model haiku --name tw-a-9137 --settings '{"disableAllHooks":true,"crossSessionInbound":"accept"}' --input-format stream-json --output-format stream-json --verbose`, idle after its first turn. Sender B, a separate one-shot run: `claude -p --model haiku --settings '{"disableAllHooks":true,"crossSessionInbound":"accept"}' --allowedTools SendMessage "Use SendMessage once: send to the session named tw-a-9137 ..."`.

    B tool result: {"success":true,"message":"... tw-a-9137 (another Claude session on this machine; in that session's inbox ...)","msg_id":"53abf095-..."}
    A log:  [16.3s] user ... Another Claude session sent a message:
            <cross-session-message from="uds:/tmp/cc-socks/14356.sock" from-name="w2-fd" from-mode="prompting">
            PUSH-FROM-B: reply with exactly the word DELTA
    A log:  [16.3s] assistant TEXT:DELTA   [18.6s] result/success RESULT:DELTA

Result: an idle `-p` worker started a new turn on the message (turn start 16.3s, result 18.6s in worker A's clock; the send time itself was not recorded). A single-prompt `-p` run exits after its turn, so it can only receive while something keeps it alive: an open stdin (stream-json input) or background work (see section 3). Receiving in a single-prompt run kept alive by background work is `INFERRED`, not tested.

A `-p` worker also exports its own socket: in worker A's Bash tool, `echo $CLAUDE_CODE_MESSAGING_SOCKET; ls -l` printed `SOCK=/tmp/cc-socks/79751.sock` and `srw-------@ 1 <user> wheel 0 ... /tmp/cc-socks/79751.sock` (owner-only mode).

### Is there a supported way for a non-Claude program to send?

Looked for, none found:
- CLI. `claude --help` lists these subcommands: `agents`, `attach`, `auth`, `auto-mode`, `doctor`, `gateway`, `import`, `install`, `logs`, `mcp`, `plugin`, `purge`, `respawn`, `rm`, `setup-token`, `stop`. No send or message command. `attach`, `logs`, `stop` and `rm` act on background sessions started with `--bg`, and `--bg` cannot be combined with `-p` (https://code.claude.com/docs/en/headless.md, "Basic usage").
- Documented API. The page says the socket is for "a script or hook to post into a session", but documents only the connection auth line `{"type":"auth","token":"<token>"}` and the 30-second line timeout. The message line shape is not documented anywhere in the docs index. The docs frame posting as a script posting to its own session's socket, and verify such own-child messages specially. A writer that is not the worker's child is not covered; with an explicit `accept` it would be delivered like a peer message (`INFERRED`, not tested).
- So a dsh process writing a hand-built message to a worker's socket would depend on an undocumented protocol. Not done and not tested, as instructed. Whether dsh's own sandbox allows connecting to `/tmp/cc-socks/*.sock` is `INFERRED` unknown (the docs cover only Claude Code's sandbox settings `sandbox.network.allowUnixSockets`).

Supported route that does exist: dsh runs a one-shot `claude -p` relay (as sender B above) that calls the documented `SendMessage` tool with the worker's name. Costs: one model call per push, a Claude login on the sender side, and the worker needs a unique `--name` (docs: one live session answering to the name is addressed by name alone). The mods API also documents `$.session.send({ to: { sessionId }, text })` (https://code.claude.com/docs/en/plugins/mods/api.md), but it also needs a running Claude session as sender; not tested. Messages arrive as plain text only, are capped near one million characters, are rate-limited per sender and queued at most 50 deep (cross-session messaging page, "Limitations").

## 2. `--input-format stream-json`

Documented: CLI reference https://code.claude.com/docs/en/cli-reference.md (`--input-format`: options `text`, `stream-json`, print mode only; `--replay-user-messages` re-emits stdin user messages on stdout, needs both stream-json formats). Message shape: Agent SDK "Streaming Input", https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode.md: `{"type":"user","message":{"role":"user","content":"<text>"}}` (the TypeScript type also lists `parent_tool_use_id: null`). The same page lists "queued messages" as a streaming input benefit. Headless page https://code.claude.com/docs/en/headless.md covers `--output-format stream-json --verbose`.

Tests, each line is one JSON object on stdin:
- Two messages 25 seconds apart, worker idle in between: `ALPHA` at 3.4s, then `BRAVO` at 27.0s (a new `system/init` event per turn).
- A message sent at 8s while a 25-second Bash command ran: it was replayed at 27.5s after the tool result and answered (`CHARLIE`). Messages sent mid-turn queue.
- A named pipe works as the transport, so a shell-only sender (dsh) needs no library: `mkfifo in.fifo; tail -f /dev/null > in.fifo & claude -p --input-format stream-json --output-format stream-json --verbose < in.fifo > out.log &`, then `echo '{"type":"user","message":{"role":"user","content":"..."}}' > in.fifo`. Output: `RESULT ONE`, `RESULT TWO` for two echoes 12 seconds apart. The held-open writer (`tail -f /dev/null`) is needed so the worker does not see end of input after the first echo.

Limits:
- One process owns the worker's stdin. Whoever starts the worker (the launcher) must create and keep the pipe; a worker already running without it cannot be pushed to this way.
- Closing stdin lets the run end once its turn and any background work finish (headless page, "Background tasks at exit"). After the held writer was killed in the last test the worker was still running at the check three seconds later; the exit timing on end of input is not measured.
- The sender must drain the worker's stdout, or the worker stalls (headless page: Claude Code waits for queued output to drain, capped at 30 seconds, only at exit; stall under a full pipe is `INFERRED`).
- The done signal and results come back on stdout as `result` events, one per turn.

## 3. Monitor on a mailbox file

Documented: Monitor tool, https://code.claude.com/docs/en/tools-reference.md (section "Monitor tool"): every watch has a deadline, 5 minutes by default, at most 30, and at most 10 minutes in a non-interactive run given a single prompt with `-p`. At the deadline Claude gets one notice and must start the watch again. Headless page, "Background tasks at exit": a `-p` run waits for Monitor watches until the watch times out or a 10-minute idle cap ends the wait. Plugin-declared monitors (https://code.claude.com/docs/en/plugins/components.md, "Monitors") do not start under `-p`, so the always-on form is unavailable. Monitor is a deferred tool; haiku loaded it itself with ToolSearch (`{"query":"select:Monitor"}`).

Tests (watch command `tail -n0 -F mailbox.txt`):
- Stream-json worker, watch armed, idle at 6.9s, a line appended at 25s: `[25.2s] system/init`, `[26.0s] TEXT:GOT hello-from-mailbox-1`. The file append woke the idle worker.
- Single-prompt `-p` run, `timeout_ms` 30000, line appended at 12s: `GOT single-prompt-line` at 14.7s; the run ended at about 43s wall, after the watch expired (the model's reply said it expired and was not re-armed). Several `result` events per run.
- Stream-json worker, `timeout_ms` 15000, line appended at 40s: the expiry notice started a turn at 19s (`TEXT:EXPIRED`); the line at 40s produced no turn. A push after the deadline is lost unless the worker re-armed the watch; re-arming depends on the model following instructions.

Limits: deadline of at most 10 minutes (single prompt) or 30 minutes; re-arm is model-driven; each line costs a model turn; reads only what is appended after the watch starts (a mailbox needs an offset file or a consume-and-truncate step, `INFERRED`).

## 4. Other official routes

- Development-channels flag: ignored with `-p`, the channel does not register (https://code.claude.com/docs/en/channels-reference.md: "If you pass it in non-interactive mode with `-p` or through the Agent SDK, Claude Code ignores the flag and the channel doesn't register"). Not tested, per the ticket's rule against using the flag.
- Stop hook that holds the turn open (https://code.claude.com/docs/en/hooks.md, Stop decision control: returning `decision: "block"` with a `reason` keeps the conversation going with the reason as feedback). Test: a hook script polled a mailbox for 45 seconds and blocked with the line as reason. Stream-json worker: `FIRST` at 5.4s; line appended at 15s; `[15.3s] Stop hook feedback: Mailbox message: hook-mailbox-msg ...`, `[16.7s] TEXT:HOOKGOT hook-mailbox-msg`. Limits: the worker's `result` for the turn arrived only at 64s, after the hook polled a second time, so while the hook polls the parent sees no turn end; the hook has its own timeout; needs hooks enabled on the machine (the `SessionStart` hook on the test machine forced `disableAllHooks` in the other tests, here `--setting-sources project` kept user hooks out). `asyncRewake` (hooks.md: wakes Claude on exit code 2) was not tested.
- Agent SDK streaming input (TypeScript `query({ prompt: asyncIterable })`, Python `ClaudeSDKClient.query(generator)`): same mechanism as stream-json input with a library in front. Needs a Node or Python program as the parent; not tested. dsh itself can only reach it through shell commands, so the named pipe is the smaller route.
- `claude --bg` and `claude attach`: background sessions, interactive terminals; `--bg` cannot combine with `-p`.

## Recommendation

For a worker that dsh itself launches, use stream-json input over a named pipe. It is documented, tested, takes messages mid-turn and while idle, needs no model call to deliver, and needs only shell commands on the dsh side. The launcher must create the pipe and hold its write end open.

Use cross-session messaging (a short `claude -p` relay calling `SendMessage`) only for a worker dsh did not launch, or one without an open stdin. It is supported and tested, but costs a model call per push and the worker must carry `crossSessionInbound: accept` and a unique `--name`.

Use a Monitor on a mailbox file as a last resort: it works, but the deadline (10 or 30 minutes) and re-arm make it unreliable for long runs. Do not write to a worker's socket directly: the message shape is undocumented.

Open items for the follow-up decision ticket (#14): whether the launcher owns the pipe for every worker or only the fallback; whether dsh's sandbox lets it create and write a named pipe (`INFERRED`, not tested); behavior of the worker when end of input arrives (measured only partly).

## Cleanup note

Every worker, pipe and folder used for the tests was created in a temp folder and removed; the held-open writer and worker processes of the last test were killed by their own pids.
