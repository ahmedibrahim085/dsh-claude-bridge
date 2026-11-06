// dsh-claude-bridge (turn events): a DeepSeek Harness plugin that appends one JSON line per finished agent turn.
//
// It runs in the dsh host process and only observes: no shell, no sandbox involvement, and it never
// steers or blocks a turn. Other agents (Claude Code, scripts, CI) read the file event-driven, for
// example with `tail -F` or the bundled `dsh-wait-turn`. A write failure is logged, never thrown,
// so a full disk or a bad path cannot break a dsh session.
//
// Line shape: {"ts","event":"turn-stopping","session_id","cwd","turn","agent_preset"}
import { appendFile, mkdir } from 'node:fs/promises'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'

export const name = 'dsh-claude-bridge'

/** Default event file; override with config `file` or the DSH_TURN_EVENTS_FILE environment variable. */
export function defaultFile(env = process.env) {
  return env.DSH_TURN_EVENTS_FILE || join(homedir(), '.local', 'state', 'dsh-events', 'turns.jsonl')
}

/** Build one event line from the `agent/turn-stopping` payload. Exported for tests. */
export function eventLine({ agent, turn }, now = new Date()) {
  const header = agent?.session?.header ?? {}
  return JSON.stringify({
    ts: now.toISOString(),
    event: 'turn-stopping',
    session_id: header.id ?? null,
    cwd: header.cwd ?? null,
    turn: turn ?? null,
    agent_preset: header.agentPreset ?? null,
  }) + '\n'
}

export function apply(ctx, config = {}) {
  const file = typeof config.file === 'string' && config.file !== '' ? config.file : defaultFile()
  ctx.on('agent/turn-stopping', async (payload) => {
    try {
      await mkdir(dirname(file), { recursive: true })
      await appendFile(file, eventLine(payload), { mode: 0o600 })
    } catch (error) {
      ctx.logger?.('dsh-claude-bridge')?.warn?.('cannot append %s: %s', file, error?.message)
    }
  })
}
