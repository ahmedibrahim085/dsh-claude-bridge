import { test, afterEach } from 'node:test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, readdir, stat, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { createInterface } from 'node:readline'
import { fileURLToPath } from 'node:url'

const BIN = join(dirname(fileURLToPath(import.meta.url)), '..', 'bin', 'dsh-claude-channel')

// Every server a test starts is killed after that test, so a failing assertion cannot leave the run hanging.
const started = []
afterEach(() => { for (const c of started.splice(0)) if (c.exitCode === null) c.kill('SIGKILL') })

/** Start one server role as an MCP client would; collects notifications. */
function start(role, dir, cwd = dir) {
  const child = spawn(process.execPath, [BIN, '--role', role], { cwd, env: { ...process.env, DSH_CLAUDE_CHANNEL_DIR: dir }, stdio: ['pipe', 'pipe', 'pipe'] })
  started.push(child)
  let id = 0
  const pending = new Map()
  const notes = []
  const waiters = []
  createInterface({ input: child.stdout }).on('line', (line) => {
    const m = JSON.parse(line)
    if (m.id !== undefined && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return }
    if (m.method) { notes.push(m); waiters.splice(0).forEach((w) => w()) }
  })
  const rpc = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: i, method, params }) + '\n') })
  const ready = (async () => {
    const init = await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'test', version: '0' } })
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n')
    return init.result
  })()
  const nextNote = (ms = 3000) => new Promise((res, rej) => {
    if (notes.length) return res(notes.shift())
    const t = setTimeout(() => rej(new Error('no notification')), ms)
    waiters.push(() => { clearTimeout(t); res(notes.shift()) })
  })
  const stop = () => new Promise((res) => { child.once('exit', res); child.stdin.end() })
  return { child, rpc, ready, nextNote, notes, stop }
}

const listening = async (dir, n) => {
  for (let i = 0; i < 50; i++) { if ((await readdir(dir)).filter((f) => f.endsWith('.sock')).length >= n) return; await new Promise((r) => setTimeout(r, 50)) }
  throw new Error(`fewer than ${n} sockets in ${dir}`)
}

test('claude role declares the claude/channel capability and listens on a private socket', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'chan-'))
  const claude = start('claude', join(dir, 'socks'), dir)  // the server creates the socket dir itself
  const init = await claude.ready
  assert.deepEqual(init.capabilities.experimental, { 'claude/channel': {} })
  assert.match(init.instructions, /dsh/)
  await listening(join(dir, 'socks'), 1)
  assert.equal((await stat(join(dir, 'socks'))).mode & 0o777, 0o700)
  await claude.stop()
  assert.deepEqual((await readdir(join(dir, 'socks'))).filter((f) => f.endsWith('.sock')), [])
})

test('dsh role offers send_to_claude, which reaches the Claude session as a channel event', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'chan-'))
  const claude = start('claude', dir)
  await claude.ready
  await listening(dir, 1)
  const dsh = start('dsh', dir)
  await dsh.ready
  const tools = (await dsh.rpc('tools/list')).result.tools.map((t) => t.name)
  assert.deepEqual(tools, ['send_to_claude'])
  const r = (await dsh.rpc('tools/call', { name: 'send_to_claude', arguments: { message: 'tests pass, review the diff' } })).result
  assert.equal(r.isError, undefined)
  assert.match(r.content[0].text, /delivered to 1 Claude session/)
  const note = await claude.nextNote()
  assert.equal(note.method, 'notifications/claude/channel')
  assert.equal(note.params.content, 'tests pass, review the diff')
  assert.equal(note.params.meta.from, 'dsh')
  await Promise.all([dsh.stop(), claude.stop()])
})

test('cwd picks the Claude session working in that folder', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'chan-'))
  const a = await mkdtemp(join(tmpdir(), 'repo-a-'))
  const b = await mkdtemp(join(tmpdir(), 'repo-b-'))
  const ca = start('claude', dir, a), cb = start('claude', dir, b)
  await Promise.all([ca.ready, cb.ready])
  await listening(dir, 2)
  const dsh = start('dsh', dir)
  await dsh.ready
  const r = (await dsh.rpc('tools/call', { name: 'send_to_claude', arguments: { message: 'only b', cwd: b } })).result
  assert.match(r.content[0].text, /delivered to 1 Claude session/)
  assert.equal((await cb.nextNote()).params.content, 'only b')
  await new Promise((res) => setTimeout(res, 300))
  assert.equal(ca.notes.length, 0)
  await Promise.all([dsh.stop(), ca.stop(), cb.stop()])
})

test('no listening Claude session is an error the model can read; stale sockets are removed', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'chan-'))
  await writeFile(join(dir, '99999999.sock'), '')  // left by a crashed session: not a live socket
  const dsh = start('dsh', dir)
  await dsh.ready
  const r = (await dsh.rpc('tools/call', { name: 'send_to_claude', arguments: { message: 'anyone?' } })).result
  assert.equal(r.isError, true)
  assert.match(r.content[0].text, /no Claude session is listening/)
  assert.deepEqual((await readdir(dir)).filter((f) => f.endsWith('.sock')), [])
  await dsh.stop()
})

test('an empty message is refused', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'chan-'))
  const dsh = start('dsh', dir)
  await dsh.ready
  const r = (await dsh.rpc('tools/call', { name: 'send_to_claude', arguments: { message: '  ' } })).result
  assert.equal(r.isError, true)
  await dsh.stop()
})
