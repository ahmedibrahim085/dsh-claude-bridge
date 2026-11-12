# What the dsh web host API offers an outside program

Research for issue #9 (map #8). Checked against `@deepseek-ai/dsh` 0.2.2-rc.1 (installed) and the public repo
`deepseek-ai/deepseek-harness` (default branch `master`, commit `e8f7b93`, 2026-11-12). Live checks ran on a throwaway web
host on port 3099, 2026-11-12.

Labels: **VERIFIED-LIVE** = I ran it and saw the output. **DOCS** = a first-party document says it, source cited.
**INFERRED** = read from types or code, not executed.

Paths marked `[pkg]` are under `<global node_modules>/@deepseek-ai/dsh/node_modules/@deepseek-ai/`.

## Short answer

The web host exposes its whole typed Remote layer over `POST /api/<endpoint>`, and its design notes say outside "CLI and
MCP callers" are a supported kind of caller, with their own login step (`/connect`). Every operation the bridge needs
exists: create, list, prompt (queue and steer), wait, read results, cancel. The risk is not the shape of the API but its
stability: no version of dsh is a stable release, and the first-party docs promise nothing about these endpoints
staying fixed.

## 1. Endpoints and request shapes

All endpoints are in `[pkg]dsh-api-session-controller/lib/typert.remote-client.js` (`TYPERT_REMOTE.methods`, generated
from `packages/api/session-controller/src/index.ts`; line numbers below are that source file, taken from each method's
`sourceLocation`). Type docs: `[pkg]dsh-api-session-controller/lib/types/types.d.ts`.

Wire envelope (VERIFIED-LIVE, and given in the issue): `POST /api/<endpoint>`, header `content-type: application/json`,
body

```json
{"type":"client-request","rpcId":"<uuid>","method":"<endpoint>","payload":{"args":{"<param>":{...}}}}
```

The reply is `{"type":"server-response","rpcId":...,"result":{"ok":true,"value":...}}` or
`{"ok":false,"error":{"code":...,"message":...,"details":...}}`. A business or argument error still comes back as
HTTP 200 with `ok:false` (VERIFIED-LIVE: `gateway/arguments-invalid`); only authentication and trust failures are plain
HTTP 401 or 403.

The args key is the Host method's parameter name. It is `request` for every endpoint below except `session/list`,
which takes `_request` (VERIFIED-LIVE: sending `request` returned `missing "_request"; unexpected "request"`).

| Need | Endpoint | Args | Result | Source line |
|---|---|---|---|---|
| create | `session/create` | `request: {cwd?, workspaceId?, sessionId?, agentPreset?}`; `cwd` and `workspaceId` exclusive; a named blank `sessionId` is reused | `{sessionId, agentPreset?}` | index.ts:304 |
| list | `session/list` | `_request: {cursor?}` | `{items:[{sessionId, updatedAt, running, blank, cwd?, agentAvailable, formatStatus, projections...}]}` | index.ts:279 |
| search | `session/search` | `request: {query}` | `{items:[{sessionId, snippet}], hasMore}` (max 20) | index.ts:293 |
| prompt | `session/prompt` | `request: {requestId, sessionId, mode:"queue"\|"steer", content:[{type:"text",text}\|{type:"image",mediaType,data,name?}\|{type:"file",receiptId}], clientTimeZone?}` | `{accepted:true}` | index.ts:465 |
| wait | `session/wait` | `request: {sessionId, timeoutMs?, afterSeq?, maxMessages?}`; default timeout 30 s (types.d.ts:593) | `{reason:"idle"\|"input-required"\|"timeout", state, output:{records, truncated}}` | index.ts:595 |
| state | `session/state` | `request: {sessionId}` | `{cursor, active, running, queue\|null, pendingInput[]}` | index.ts:573 |
| read history | `session/events` (alias `session/page`, deprecated) | `request: {address:{kind:"session",sessionId}, throughSeq?, beforeSeq?, maxMessages?, turnWindow?}` | `{cursor, records:[{type:"event",event:{type,seq,time,data}}], hasMore}` | index.ts:540 |
| cancel | `session/cancel` | `request: {sessionId}` | `{accepted:true}`; "cancel one active Agent turn without dropping its pending inbox" | index.ts:517 |
| edit queue | `session/updateQueue` | `request: {sessionId, itemId, action:{kind:"edit"\|"remove"\|"steer"}}` | `{accepted:true}` | index.ts:507 |

Also present (INFERRED useful, not used live): `session/fork`, `session/rename`, `session/selectModel`,
`session/modelCatalog`, and the streams `session/follow`, `session/observeEvent`, `session/observeState`,
`session/control`. Streams run over the `/api/remote.mux` WebSocket (`[pkg]dsh-api-gateway/README.md:41`); the bridge does
not need them because `session/wait` plus `session/events` cover the same ground over plain HTTP.

### What the live checks showed (VERIFIED-LIVE, dsh 0.2.2-rc.1)

- `session/create {cwd}` returned a session id and `agentPreset:"standard"`. `session/state` on it:
  `{"cursor":3,"active":true,"running":false,"queue":[],"pendingInput":[]}`.
- `session/prompt` mode `queue`, then `session/wait {timeoutMs:25000}`: `reason:"idle"`, `truncated:false`, and the
  records held the assistant reply (`PONG`).
- Wait straight after a prompt does not return early. Prompt a `sleep 12` task, then `session/wait {timeoutMs:4000,
  afterSeq:20}` returned `reason:"timeout"`, `state.running:true`, after 4 s. (One sample, not a proof of no race.)
- `steer` reached the running turn. `session/state` showed the queue item with `placement:"steering"`; the final
  assistant text was `DONE\n\nSTEERED`.
- `wait.output.records` is newest first and holds every assistant message after `afterSeq`, tool-call messages
  included (`types.d.ts:600`, confirmed live: seq 36 listed before seq 26). A caller that wants the final answer
  reads the first record, and tracks `state.cursor` as the next `afterSeq`.
- A prompt that makes the agent call the ask-user tool ended `session/wait` with `reason:"input-required"` and
  `state.pendingInput:["question"]`, `running:true`. `session/cancel` then returned `accepted:true`, and the next wait
  returned `reason:"idle"` with `pendingInput:[]`. So cancel is the way out of a stuck question for a caller that
  cannot answer.
- `session/events {address, maxMessages:2}` returned a turn-aligned page of 12 events (`assistant/message`, `tool/call`,
  `tool/result`, `step/start`, `step/end`, `turn/end`, ...) with `cursor:55`, `hasMore:true`. A "page" is aligned to
  whole turns, not exactly `maxMessages`.
- `session/list` returns every visible session on the host, not only the caller's (41 rows on the test host, one of them
  mine). Filter by `sessionId` or `cwd`; there is no per-caller view.
- After a host restart, a session created earlier is still readable: `session/state` returned
  `{"active":false,"running":false,"queue":null,...}` (cold session, no live agent), so state survives restarts.

### Who answers an approval or question

`input-required` means the host is waiting for a human answer. Answers travel through the forwarded-event stream
(`$events/result`), not a `/api/session/*` call, and only a Peer connected with `interactions=answer` may reply
(`[pkg]dsh-client-connection/README.md:51`; design note `2026-10-09-operator-scoped-connect-handshake.md`, "Events and
Client scope"). I did not build an answering client. INFERRED: a plain-HTTP bridge with `interactions=none` can wait,
detect `input-required`, and cancel, but cannot answer. Whether the bridge needs to answer is a decision for #10.

## 2. Authentication for a non-browser caller

1. **Token source.** Each host process mints a random launch token and prints it in the URL line
   `dsh web: http://127.0.0.1:<port>/?token=<token>` (`[pkg]dsh-client-connection/README.md:41`;
   `[pkg]dsh-web-app/README.md:113`: "supervisors RPC as soon as they observe the line"). The token changes on every
   host start (VERIFIED-LIVE: token differed after restart).
2. **Exchange.** `GET /connect?token=<token>&interactions=none|answer` is "only for API callers"
   (`README.md:51`). VERIFIED-LIVE: it answers `302` with `Location: ./api/remote.mux` and a `Set-Cookie`
   `dsh-auth-<authority-hash>=...; Max-Age=2592000; Path=/; HttpOnly; SameSite=Strict`. `interactions` defaults to
   `none`. Repeating the parameter gives `400` (live); a wrong token gives `401` (live). The token is accepted only on
   `/` and `/connect`, never as an `Authorization` header (README:41; live: `Authorization: Bearer <token>` on
   `/api/...` gave `401`).
3. **Use.** Send the cookie on every `POST /api/...`. No WebSocket is needed: "HTTP need not wait for the socket to
   open" (upgrade guide `v0.2.1-alpha.2/operator-connect`, live: all calls above were plain HTTP).
4. **Trust fence.** Every request must carry a loopback `Host` (or a configured `trustedHosts` entry), and a cross-site
   `Origin` is refused (README:47). VERIFIED-LIVE: `Host: evil.example:3099` gave `403`; no cookie gave `401`.
5. **Lifetime.** The cookie is valid 30 days: `cookieMaxAgeDays` default 30 (`[pkg]dsh-client-connection/lib/index.js:1017`;
   live `Max-Age=2592000`). The signing secret lives in `$DSH_HOME/.credentials.yaml` (README:43).
6. **What invalidates it.** A host restart: VERIFIED-LIVE, a cookie from before the restart returned `401`, the old token
   returned `401` on `/connect`, and only a fresh token plus a new `/connect` worked. The design note says the same:
   "API Cookies cannot restore a Peer after its socket closes or the Host restarts". Closing the caller's lifecycle
   WebSocket (if it opened one) also removes the Peer and refuses later HTTP with that cookie (note, "Admission and
   ownership"; INFERRED here, I did not open a socket). There is no logout; deleting the credential record and
   restarting revokes every cookie (README:83).
7. **Several API callers.** Yes. Each `/connect` creates an independent Peer (README:51). VERIFIED-LIVE: two cookies,
   both returned `ok:true` from `session/state` in the same host run. Cost: an API caller that never opens the
   WebSocket leaves a small Peer record until host shutdown (README:82), accepted by the authors.
8. **Privilege.** The cookie belongs to the owner principal: "Any launch-token holder may request `answer`; this is
   interaction participation, not user isolation" (design note, "Consequences"). The same API also has
   `credentials/set`, `settings/*`, `pluginManager/*`, `commands/execute` (all endpoint names, listed from every
   `typert.remote-client.js`). Treat the token and cookie like a password to the whole host.
9. **Finding the token for a host the bridge did not start.** The printed URL is the only documented source. This
   machine's `~/.dsh/last-url` is a bridge-side convenience, not a dsh feature (given in the issue; not re-checked).

## 3. Public or internal, and how it changed

**Documented status: neither promised nor denied.** What the first-party docs say:

- Supported for outside callers, in the design note: "CLI and MCP callers need independent participation and cleanup"
  and "Raw streams already support CLI/MCP calls" (`.agents/notes/implemented/architecture/2026-10-09-operator-scoped-connect-handshake.md`,
  "Problem" and "Events and Client scope"; `/connect` was added in 0.2.1-alpha.2 for exactly this, upgrade guide
  `docs/upgrade-guide/v0.2.1-alpha.2/operator-connect/guide.md`). Agent notes are maintainer decision records, not user
  documentation.
- The group README calls it the application's "Remote layer: typed Client-to-Host capability calls" for "a Client
  environment" (repo `packages/api/README.md`, Summary). The session-controller README is titled "Host and Client session
  control". None of the READMEs reviewed says the endpoints are a public, versioned interface, none lists a
  compatibility promise, and no HTTP reference lists the `/api/<endpoint>` set for outsiders. The endpoint table is in
  generated `typert.remote-client.js` files.
- The out-of-process interfaces documented *as such* are different ones: the stdio JSON-RPC SDK server
  (`[pkg]dsh-sdk-jsonrpc-server/README.md`, "let out-of-process SDK clients open sessions and drive agents"; wire
  types in `[pkg]dsh-sdk-protocol`) with TypeScript and Python clients, and the ACP profile
  (`[pkg]dsh-acp-app/README.md`). They are separate processes from the web host. This ticket does not compare them;
  #10 may.

**Versioning.** All 43 npm versions of `@deepseek-ai/dsh` are prereleases (`-alpha.N` or `-rc.N`; none is a plain
`x.y.z`), from `0.0.1-rc.1` (2026-08-10) to `0.2.2-rc.2` (2026-11-12). The npm `latest` tag points at `0.2.2-rc.1`
and `next` at `0.2.2-rc.2`. Every GitHub release is marked "Pre-release" (0 non-prerelease in the list). Commands:
`npm view @deepseek-ai/dsh versions --json`, `gh release list --repo deepseek-ai/deepseek-harness`. The release notes
list "breaking" items by name, but they never mention the `/api` endpoints as a promised surface.

**Changes that touched this API** (release notes and `docs/upgrade-guide/`; cited by version):

| Version | Change | Effect on an outside caller |
|---|---|---|
| 0.1.2-alpha.1 | ApiProxy removed, replaced by the `@Remote` gateway; one-time launch-token auth for the Web UI | the legacy call interface (ApiProxy) was removed in favour of `@Remote`; token auth is new |
| 0.1.7-alpha.1 | Remote gains bidirectional streams and binary results (workspace file reads unified under `readBytes`) | additive for session calls |
| 0.2.1-alpha.2 | `/connect` and `interactions` added; "Custom SDK runtimes must support session/wait" | `session/wait` first appears as a required part of the session API |
| 0.2.1-alpha.4 | model selection fixed per step, `agent/request` deprecated | plugin-side |
| 0.2.1-rc.2 | New Session reuses a blank Session again (guide `new-session-blank-reuse`) | `session/create` reuse behaviour flipped twice in one release cycle (alpha.1 then rc.2) |
| 0.2.1-rc.3 | `session/follow` no longer activates a cold Agent unless `activate:true` (guide `session-follow-activation`); `session/attachment` now requires the full `attachment` reference | silent behaviour change for a follow-based caller; a request-shape break for attachments |
| 0.2.2-rc.2 | AgentTeam moves to "unified named subagents"; "migrate custom plugins and SDK integrations and upgrade all processes sharing session storage together"; "Tool failures provide clearer error types and codes... plugins and SDK integrations relying on older classifications need updating" | affects event content and error codes, not the call shapes |

`session/create`, `session/prompt`, `session/wait`, `session/state`, `session/cancel` and `session/events` have no
shape break in the upgrade guides I read (8 of the session, connect and projection guides under `docs/upgrade-guide/`,
plus the release notes). That is a reading, not a diff of every version's descriptors: INFERRED.

Two facts that bear on how fast the surface moves: 28 prerelease versions were published between 2026-09-04 and
2026-11-12 (`npm view @deepseek-ai/dsh time --json`, counted by date), and `0.2.2-rc.2` shipped 8 days after `rc.1`.

## 4. Safe to build on, and risky

**Safe (same shape on every build I read; verified live on 0.2.2-rc.1):**

- The `session/create`, `prompt`, `wait`, `state`, `cancel`, `events` calls and their request shapes. Their types
  are strict, generated from the Host source, and every one of them worked as documented.
- `/connect` with `interactions=none` plus cookie plus plain HTTP. It is the documented route for non-page callers and
  needs no WebSocket.
- The wait contract: `reason` is `idle`, `input-required` or `timeout`; `state.pendingInput` says what is pending;
  newest-first output with `afterSeq` as a cursor. A bridge can build "send, wait, read the reply" on only these.
- Several callers at once, and sessions surviving a host restart.

**Risky:**

- **No stability promise.** Prerelease-only versions; a request shape (`session/attachment`) and silent behaviours
  (`session/follow` activation, blank-session reuse) changed within one release cycle. Pin the dsh version the bridge
  was tested on, and run a live contract test (create, prompt, wait, events, cancel) in the bridge's own tests and in
  `doctor`, so a dsh upgrade fails loudly.
- **Re-login on every host restart.** The token changes and every cookie dies; the bridge must re-read the printed URL
  and call `/connect` again, and treat `401` on `/api` as "reconnect once, then fail".
- **The URL line is the only token source.** A bridge that did not launch the host must be told the URL (or read a file
  the launcher wrote). The token is a full-owner credential: never log it, and keep cookies out of shared storage.
- **Human interactions.** With `interactions=none` the bridge cannot answer approvals or questions; it sees them as
  `input-required` and can only cancel. Answering needs `interactions=answer` plus the event stream, which is
  unverified here.
- **The endpoint list is generated, not documented.** The only place that lists `/api/<endpoint>` for an outsider is
  generated JavaScript in the npm package; field names (`_request` for `list`) are discovered, not documented. A
  lookup of `TYPERT_REMOTE` at run time is more reliable than a copied table.
- **`session/list` shows every session on the host.** The bridge must filter to the sessions it created.
- **Unused Peers pile up until host shutdown** if the bridge calls `/connect` per task. Connect once per host run and
  reuse the cookie.
- **Cold sessions need a live agent for some calls.** `session/prompt` is documented as "Admit one prompt after
  explicitly resuming its Session"; `session/state` on a cold session reports `active:false`, `queue:null`
  (VERIFIED-LIVE after the restart). I did not prompt a cold session; the doc line is the only evidence.

## Reproduce

Throwaway host and the calls above (port 3099 only; never the owner's host):

```sh
dsh --profile web --no-open --port 3099 > host.log 2>&1 &
TOKEN=$(sed -n 's/.*?token=\([^ ]*\).*/\1/p' host.log | tail -1)
curl -s -c jar -D - -o /dev/null "http://127.0.0.1:3099/connect?token=$TOKEN&interactions=none"   # 302 + Set-Cookie
curl -s -b jar -H 'content-type: application/json' http://127.0.0.1:3099/api/session/create \
  -d '{"type":"client-request","rpcId":"'$(uuidgen)'","method":"session/create","payload":{"args":{"request":{"cwd":"/tmp/some-empty-dir"}}}}'
```

The session folder those checks created (`~/.dsh/sessions/--tmp-claude-502-r9-ws--`) was removed; the host was stopped by
its exact pid.
