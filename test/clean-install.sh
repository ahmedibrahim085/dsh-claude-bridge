#!/bin/sh
# Clean-install test: a throwaway HOME with no bridge, no acpx config, no dsh profiles.
# Installs this working copy, runs setup twice (must be idempotent), then doctor --live
# (one real dsh turn through acpx + its turn event). Needs network, a global @deepseek-ai/dsh
# and a provider: pass the provider fields as env vars, e.g.
#   PROVIDER_ID=zai-glm PROVIDER_BASE_URL=https://open.bigmodel.cn/api/anthropic \
#   PROVIDER_KEY_FILE=~/.glm-env MODELS="glm-5.3" sh test/clean-install.sh
set -eu
repo=$(cd "$(dirname "$0")/.." && pwd)
: "${PROVIDER_ID:?}" "${PROVIDER_BASE_URL:?}" "${PROVIDER_KEY_FILE:?}" "${MODELS:?}"
real_home=$HOME
npm_prefix=$(npm config get prefix)
tmp=$(mktemp -d)
[ -n "${KEEP:-}" ] || trap 'rm -rf "$tmp"' EXIT; echo "tmp=$tmp"
export HOME="$tmp/home" NPM_CONFIG_PREFIX="$npm_prefix"
claude_dir=$(dirname "$(command -v claude 2>/dev/null || echo /nonexistent/claude)")
export PATH="$HOME/.local/bin:$npm_prefix/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$claude_dir"
mkdir -p "$HOME/.config/dsh-claude-bridge"
key_file=$(eval echo "$PROVIDER_KEY_FILE" | sed "s#^$tmp/home#$real_home#")
cat > "$HOME/.config/dsh-claude-bridge/config" <<EOF
PROVIDER_ID=$PROVIDER_ID
PROVIDER_BASE_URL=$PROVIDER_BASE_URL
PROVIDER_KEY_FILE=$key_file
PROVIDER_KEY_VAR=${PROVIDER_KEY_VAR:-ANTHROPIC_AUTH_TOKEN}
MODELS=$MODELS
PROFILES=web acp headless
HELPERS=both
MCACP=${MCACP:-1}
BIN_DIR=~/.local/bin
EOF
fail() { echo "FAIL: $1"; exit 1; }

echo "== doctor before setup (must report missing pieces)"
if "$repo/bin/dsh-claude-bridge" doctor > "$tmp/d0" 2>&1; then fail "doctor passed on an empty HOME"; fi
grep -q "\[missing\]" "$tmp/d0" || fail "doctor printed no [missing] lines"
echo "ok - doctor reports $(grep -c '\[missing\]' "$tmp/d0") missing pieces"

echo "== setup (installs from this working copy)"
"$repo/bin/dsh-claude-bridge" setup --source "file:$repo" > "$tmp/s1" 2>&1 || { cat "$tmp/s1"; fail "setup failed"; }
grep -q "setup done" "$tmp/s1" || { cat "$tmp/s1"; fail "setup did not finish"; }
echo "ok - setup: $(grep -c '^- ' "$tmp/s1") steps"

echo "== setup again (idempotent: no profile rewrites)"
"$repo/bin/dsh-claude-bridge" setup --source "file:$repo" > "$tmp/s2" 2>&1 || { cat "$tmp/s2"; fail "second setup failed"; }
if grep -q "managed block written" "$tmp/s2"; then cat "$tmp/s2"; fail "second setup rewrote a profile"; fi
echo "ok - second setup changed no profile"

echo "== doctor --live"
"$HOME/.local/bin/dsh-claude-bridge" doctor --live > "$tmp/d1" 2>&1 || { cat "$tmp/d1"; fail "doctor --live reported missing pieces"; }
grep -q "live: dsh answered through acpx" "$tmp/d1" || fail "no live answer"
grep -q "live: turn event written" "$tmp/d1" || fail "no live turn event"
cat "$tmp/d1"
echo "ok - clean install passes doctor --live"

echo "== uninstall --dry-run (changes nothing)"
# ~/.npm/_logs is excluded: every npm call (here `npm prefix -g`, to locate dsh) writes a debug log there.
snap() { find "$HOME" -type f -not -path "$HOME/.npm/_logs/*" -exec shasum {} + | sort; }
snap > "$tmp/f0"
"$HOME/.local/bin/dsh-claude-bridge" uninstall --dry-run > "$tmp/u0" 2>&1 || { cat "$tmp/u0"; fail "dry run failed"; }
snap > "$tmp/f1"
diff "$tmp/f0" "$tmp/f1" > "$tmp/fdiff" || { cat "$tmp/fdiff"; fail "dry run changed files"; }
echo "ok - dry run lists $(grep -c '^- would' "$tmp/u0") actions, no file changed"

echo "== uninstall"
"$HOME/.local/bin/dsh-claude-bridge" uninstall > "$tmp/u1" 2>&1 || { cat "$tmp/u1"; fail "uninstall failed"; }
cat "$tmp/u1"
for b in dsh-claude-bridge dsh-wait-turn dsh-turns; do [ ! -e "$HOME/.local/bin/$b" ] && [ ! -L "$HOME/.local/bin/$b" ] || fail "$b link left"; done
[ ! -L "$HOME/.claude/skills/dsh-harness" ] || fail "skill link left"
for p in web acp headless; do
  ! grep -q "dsh-claude-bridge managed block" "$HOME/.dsh/profiles/$p/cordis.patch.yml" || fail "managed block left in $p"
  ! grep -q '"dsh-claude-bridge"' "$HOME/.dsh/profiles/$p/package.json" || fail "plugin left in $p"
done
! grep -q "dsh-claude-bridge" "$HOME/.acpx/config.json" || fail "acpx dsh agent left"
if [ "${MCACP:-1}" = 1 ] && command -v claude >/dev/null; then
  ! claude mcp get mcacp >/dev/null 2>&1 || fail "mcacp still registered"
  [ ! -e "$HOME/.local/share/mcacp" ] || fail "mcacp install left"
fi
[ -f "$HOME/.config/dsh-claude-bridge/config" ] || fail "config removed without --purge"
echo "ok - uninstall removed every piece and kept the config"

echo "== uninstall again (nothing left)"
"$repo/bin/dsh-claude-bridge" uninstall > "$tmp/u2" 2>&1 || { cat "$tmp/u2"; fail "second uninstall failed"; }
grep -q "nothing to remove" "$tmp/u2" || { cat "$tmp/u2"; fail "second uninstall found pieces"; }
echo "ok - second uninstall found nothing"

echo "== setup after uninstall (reinstall works)"
"$repo/bin/dsh-claude-bridge" setup --source "file:$repo" > "$tmp/s3" 2>&1 || { cat "$tmp/s3"; fail "reinstall failed"; }
"$HOME/.local/bin/dsh-claude-bridge" doctor > "$tmp/d2" 2>&1 || { cat "$tmp/d2"; fail "doctor after reinstall"; }
echo "ok - reinstall passes doctor"
