#!/bin/sh
# dsh-wait-turn: matches by session, ignores other sessions, rebuilds a line split across writes,
# and exits 2 on timeout. Uses a temp event file; never touches a real dsh install.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export DSH_TURN_EVENTS_FILE="$tmp/turns.jsonl"
: > "$DSH_TURN_EVENTS_FILE"
fail() { echo "FAIL: $1"; exit 1; }

"$here/bin/dsh-wait-turn" --session abc --timeout 10 > "$tmp/out" &
pid=$!
sleep 1
printf '{"session_id":"zzz","cwd":"/x"}\n{"session_id":"abc-1","cw' >> "$DSH_TURN_EVENTS_FILE"
sleep 1
printf 'd":"/y","turn":2}\n' >> "$DSH_TURN_EVENTS_FILE"
wait "$pid" || fail "wait exited non-zero on a matching turn"
grep -q '"session_id": "abc-1"' "$tmp/out" || fail "wrong or missing event: $(cat "$tmp/out")"
grep -q '"turn": 2' "$tmp/out" || fail "split line not rebuilt"
echo "ok - matches session, skips others, rebuilds split line"

set +e
"$here/bin/dsh-wait-turn" --session nope --timeout 1 2>/dev/null
rc=$?
set -e
[ "$rc" -eq 2 ] || fail "timeout exit was $rc, want 2"
echo "ok - timeout exits 2"

# dsh web ids look like session-<uuid>; users pass the short id from the middle.
"$here/bin/dsh-wait-turn" --session d06e3c3a --timeout 10 > "$tmp/out2" &
pid=$!
sleep 1
printf '{"session_id":"session-d06e3c3a-5af2-417c-a283-bd7534bf1608","turn":7}\n' >> "$DSH_TURN_EVENTS_FILE"
wait "$pid" || fail "short id inside session-<uuid> did not match"
grep -q '"turn": 7' "$tmp/out2" || fail "wrong event for short id: $(cat "$tmp/out2")"
echo "ok - matches a short id inside session-<uuid>"

# --claude waits on Claude Code's done events (Stop hook file), not on dsh's.
export CLAUDE_TURN_EVENTS_FILE="$tmp/claude.jsonl"
"$here/bin/dsh-wait-turn" --claude --cwd /work --timeout 10 > "$tmp/out3" &
pid=$!
sleep 1
printf '{"event":"turn-stopping","session_id":"dsh-1","cwd":"/work"}\n' >> "$DSH_TURN_EVENTS_FILE"
printf '{"event":"stop","session_id":"c-1","cwd":"/work","last_assistant_message":"done"}\n' >> "$CLAUDE_TURN_EVENTS_FILE"
wait "$pid" || fail "--claude did not match a Claude stop event"
grep -q '"session_id": "c-1"' "$tmp/out3" || fail "--claude returned the wrong event: $(cat "$tmp/out3")"
echo "ok - --claude waits on Claude's events, not dsh's"
