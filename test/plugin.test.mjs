import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { apply, defaultFile, eventLine, name } from '../index.mjs'

/** A minimal stand-in for the dsh Cordis context: records `on` handlers and logger warnings. */
function fakeCtx() {
  const handlers = {}
  const warnings = []
  return {
    handlers,
    warnings,
    on(event, fn) { handlers[event] = fn },
    logger: () => ({ warn: (...args) => warnings.push(args) }),
  }
}

const payload = {
  agent: { session: { header: { id: 'session-abc', cwd: '/work/repo', agentPreset: 'standard' } } },
  turn: 3,
}

test('exports the plugin name the bundle patch mounts', () => {
  assert.equal(name, 'dsh-claude-bridge')
})

test('subscribes to agent/turn-stopping and appends one JSON line per turn', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'dsh-claude-bridge-'))
  const file = join(dir, 'nested', 'turns.jsonl')
  const ctx = fakeCtx()
  apply(ctx, { file })
  assert.equal(typeof ctx.handlers['agent/turn-stopping'], 'function')

  await ctx.handlers['agent/turn-stopping'](payload)
  await ctx.handlers['agent/turn-stopping']({ ...payload, turn: 4 })

  const lines = (await readFile(file, 'utf8')).trim().split('\n').map((l) => JSON.parse(l))
  assert.equal(lines.length, 2)
  assert.deepEqual(
    { ...lines[0], ts: undefined },
    { ts: undefined, event: 'turn-stopping', session_id: 'session-abc', cwd: '/work/repo', turn: 3, agent_preset: 'standard' },
  )
  assert.equal(lines[1].turn, 4)
  assert.match(lines[0].ts, /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/)
})

test('a write failure is logged, never thrown into the dsh turn', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'dsh-claude-bridge-'))
  const blocker = join(dir, 'not-a-dir')
  await writeFile(blocker, 'x')
  const ctx = fakeCtx()
  apply(ctx, { file: join(blocker, 'turns.jsonl') }) // parent is a file: mkdir must fail
  await assert.doesNotReject(ctx.handlers['agent/turn-stopping'](payload))
  assert.equal(ctx.warnings.length, 1)
})

test('missing agent fields become null instead of crashing', () => {
  const line = JSON.parse(eventLine({}, new Date(0)))
  assert.deepEqual(line, { ts: '1970-01-01T00:00:00.000Z', event: 'turn-stopping', session_id: null, cwd: null, turn: null, agent_preset: null })
})

test('default file honours DSH_TURN_EVENTS_FILE, else ~/.local/state/dsh-events/turns.jsonl', () => {
  assert.equal(defaultFile({ DSH_TURN_EVENTS_FILE: '/x/y.jsonl' }), '/x/y.jsonl')
  assert.match(defaultFile({}), /\.local\/state\/dsh-events\/turns\.jsonl$/)
})
