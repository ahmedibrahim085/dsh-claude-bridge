"""Unit tests for bin/dsh-claude-bridge (no dsh, network or real config needed)."""
import importlib.machinery, importlib.util, os, tempfile, unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin" / "dsh-claude-bridge"
loader = importlib.machinery.SourceFileLoader("bridge", str(BIN))
spec = importlib.util.spec_from_loader("bridge", loader)
bridge = importlib.util.module_from_spec(spec)
loader.exec_module(bridge)


def cfg(**over):
    tmp = Path(tempfile.mkdtemp())
    keyfile = tmp / "provider.env"
    keyfile.write_text('export ANTHROPIC_AUTH_TOKEN="sk-test-123"\nexport OTHER=x\n')
    conf = tmp / "config"
    values = {"PROVIDER_ID": "acme", "PROVIDER_BASE_URL": "https://llm.example/anthropic",
              "PROVIDER_KEY_FILE": str(keyfile), "MODELS": "m-large m-small", "BIN_DIR": str(tmp / "bin")}
    values.update(over)
    conf.write_text("".join(f"{k}={v}\n" for k, v in values.items()))
    bridge.CONFIG = conf
    return bridge.load_config()


class ConfigTests(unittest.TestCase):
    def test_reads_export_quoted_and_skips_comments(self):
        p = Path(tempfile.mkdtemp()) / "f"
        p.write_text('# KEY=ignored\nexport A="1 2"\nB=\'x\'\nC=plain\n  # D=no\n')
        self.assertEqual(bridge.read_kv(p), {"A": "1 2", "B": "x", "C": "plain"})

    def test_defaults_fill_empty_values(self):
        c = cfg(HELPERS="", PROFILES="")
        self.assertEqual(c["HELPERS"], "both")
        self.assertEqual(c["PROFILES_LIST"], ["web", "acp", "headless"])
        self.assertEqual(c["MODELS_LIST"], ["m-large", "m-small"])

    def test_problems_name_missing_fields_and_absent_key(self):
        c = cfg(PROVIDER_ID="", PROVIDER_KEY_VAR="NOPE")
        probs = bridge.config_problems(c)
        self.assertIn("PROVIDER_ID is empty", probs)
        self.assertTrue(any("NOPE not set" in p for p in probs))
        self.assertEqual(bridge.config_problems(cfg()), [])


class BlockTests(unittest.TestCase):
    def test_acp_block_sets_its_own_route(self):
        b = bridge.managed_block(cfg(), "acp")
        self.assertIn("- id: acp\n  config:\n    provider: acme\n    model: m-large", b)
        self.assertNotIn("subagent-claude-code", b)

    def test_web_block_helpers_follow_config(self):
        both = bridge.managed_block(cfg(HELPERS="both"), "web")
        self.assertIn("- id: subagent-claude-code\n", both)
        self.assertIn("toolName: subagent_claude_code_claude", both)
        self.assertIn("CLAUDE_CONFIG_DIR: !!js process.env.HOME + '/.dsh/claude-code-provider'", both)
        claude_part = both.split("- id: subagent-claude-code-claude", 1)[1]
        self.assertNotIn("CLAUDE_CONFIG_DIR", claude_part)  # setting it breaks the keychain lookup
        self.assertNotIn("subagent-claude-code", bridge.managed_block(cfg(HELPERS="none"), "web"))
        self.assertNotIn("- id: subagent-claude-code\n", bridge.managed_block(cfg(HELPERS="claude"), "web"))

    def test_every_profile_gets_the_channel_tool_unless_disabled(self):
        for p in ("web", "acp", "headless"):
            b = bridge.managed_block(cfg(), p)
            self.assertIn("    - id: dsh-claude-channel\n      name: '@deepseek-ai/dsh-mcp-client'", b)
            self.assertIn("serverName: claude", b)
            self.assertIn("/dsh-claude-channel", b.split("command:", 1)[1].split("\n", 1)[0])
            self.assertIn("args: ['--role', 'dsh']", b)
        self.assertNotIn("dsh-claude-channel", bridge.managed_block(cfg(CHANNEL="0"), "web"))

    def test_block_never_contains_the_key(self):
        for p in ("web", "acp", "headless"):
            self.assertNotIn("sk-test-123", bridge.managed_block(cfg(), p))

    def test_write_block_is_idempotent_and_keeps_user_entries(self):
        f = Path(tempfile.mkdtemp()) / "cordis.patch.yml"
        f.write_text("# mine\n- id: something-else\n  config:\n    x: 1\n")
        c = cfg()
        self.assertTrue(bridge.write_block(f, bridge.managed_block(c, "web")))
        first = f.read_text()
        self.assertFalse(bridge.write_block(f, bridge.managed_block(c, "web")))
        self.assertEqual(f.read_text(), first)
        self.assertIn("- id: something-else", first)
        self.assertEqual(first.count(bridge.BEGIN), 1)
        bridge.write_block(f, bridge.managed_block(cfg(MODELS="m-new"), "web"))
        self.assertIn("model: m-new", f.read_text())
        self.assertEqual(f.read_text().count(bridge.BEGIN), 1)

    def test_empty_list_file_is_replaced(self):
        f = Path(tempfile.mkdtemp()) / "cordis.patch.yml"
        f.write_text("# header\n[]\n")
        bridge.write_block(f, bridge.managed_block(cfg(), "headless"))
        self.assertNotIn("[]", f.read_text())

    def test_conflicts_only_outside_the_block(self):
        text = "- id: llm-pi-ai\n  config: {}\n\n" + bridge.managed_block(cfg(), "acp")
        self.assertEqual(bridge.conflicts(text), ["llm-pi-ai"])
        self.assertEqual(bridge.conflicts(bridge.managed_block(cfg(), "web")), [])
        nested = "- id: preset-x\n  config:\n    plugins:\n              - id: tool-subagent-claude-code-claude\n"
        self.assertEqual(bridge.conflicts(nested), [])  # rows inside presets are not conflicts
        self.assertEqual(bridge.conflicts("- insert:\n    - id: subagent-claude-code-claude\n"), ["subagent-claude-code-claude"])


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.target = self.d / "new-target"; self.target.write_text("new")
        self.backups = self.d / "backups"

    def test_old_symlink_is_replaced_without_a_backup(self):
        old = self.d / "old-target"; old.write_text("old")
        link = self.d / "bin" / "tool"; link.parent.mkdir(); link.symlink_to(old)
        self.assertEqual(bridge.place_link(link, self.target, self.backups), "relinked")
        self.assertEqual(os.path.realpath(link), os.path.realpath(self.target))
        self.assertEqual(sorted(p.name for p in link.parent.iterdir()), ["tool"])
        self.assertFalse(self.backups.exists())

    def test_dangling_symlink_is_replaced(self):
        link = self.d / "tool"; link.symlink_to(self.d / "gone")
        self.assertEqual(bridge.place_link(link, self.target, self.backups), "relinked")
        self.assertTrue(link.exists())

    def test_real_file_is_backed_up_outside_the_link_dir(self):
        link = self.d / "bin" / "tool"; link.parent.mkdir(); link.write_text("mine")
        result = bridge.place_link(link, self.target, self.backups)
        self.assertTrue(result.startswith("backed up to"))
        self.assertEqual([p.read_text() for p in self.backups.iterdir()], ["mine"])
        self.assertEqual(sorted(p.name for p in link.parent.iterdir()), ["tool"])

    def test_correct_link_is_left_alone(self):
        link = self.d / "tool"; link.symlink_to(self.target)
        self.assertIsNone(bridge.place_link(link, self.target, self.backups))


class LiveCleanupTests(unittest.TestCase):
    def test_removes_only_the_live_sessions_and_empty_workspace_dirs(self):
        root = Path(tempfile.mkdtemp())
        (root / "--tmp-dsh-bridge-live-x--" / "sid-live").mkdir(parents=True)
        (root / "--tmp-dsh-bridge-live-x--" / "sid-live" / "session.v4.jsonl.zstd").write_text("x")
        (root / "--work--" / "sid-mine").mkdir(parents=True)
        (root / "--work--" / "sid-other").mkdir(parents=True)
        removed = bridge.remove_sessions(["sid-live", "sid-mine"], root)
        self.assertEqual(sorted(removed), ["sid-live", "sid-mine"])
        self.assertFalse((root / "--tmp-dsh-bridge-live-x--").exists())
        self.assertTrue((root / "--work--" / "sid-other").exists())

    def test_ignores_unsafe_ids(self):
        root = Path(tempfile.mkdtemp())
        (root / "ws" / "keep").mkdir(parents=True)
        self.assertEqual(bridge.remove_sessions(["", "..", "../ws", "*"], root), [])
        self.assertTrue((root / "ws" / "keep").exists())


class UninstallTests(unittest.TestCase):
    """uninstall removes only what setup made; `sh` is stubbed so no real dsh/claude/acpx is touched."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.saved = {k: getattr(bridge, k) for k in ("HOME", "DSH_HOME", "CONFIG", "EVENTS", "sh", "find_node", "find_dsh_bin")}
        bridge.HOME, bridge.DSH_HOME = self.home, self.home / ".dsh"
        bridge.EVENTS = self.home / ".local/state/dsh-events/turns.jsonl"
        self.calls = []
        bridge.sh = lambda args, **kw: (self.calls.append(list(map(str, args))) or (0, ""))
        bridge.find_node, bridge.find_dsh_bin = (lambda: "/usr/bin/node"), (lambda: Path("/x/dsh/lib/bin.js"))
        self.c = cfg(BIN_DIR=str(self.home / "bin"), PROFILES="web acp")
        bridge.CONFIG = self.home / "config"; (self.home / "config").write_text("PROVIDER_ID=x\n")
        pkg = self.home / "pkg/dsh-claude-bridge"
        for b in ("dsh-claude-bridge", "dsh-wait-turn", "dsh-turns"):
            (pkg / "bin").mkdir(parents=True, exist_ok=True); (pkg / "bin" / b).write_text("x")
        (pkg / "skills/dsh-harness").mkdir(parents=True)
        (self.home / "bin").mkdir()
        for b in ("dsh-claude-bridge", "dsh-wait-turn"):
            (self.home / "bin" / b).symlink_to(pkg / "bin" / b)
        (self.home / "bin/dsh-turns").write_text("someone else's script")
        (self.home / ".claude/skills").mkdir(parents=True)
        (self.home / ".claude/skills/dsh-harness").symlink_to(pkg / "skills/dsh-harness")
        for p in ("web", "acp"):
            pd = self.home / ".dsh/profiles" / p; pd.mkdir(parents=True)
            (pd / "cordis.patch.yml").write_text("# mine\n- id: keep-me\n\n" + bridge.managed_block(self.c, p))
            (pd / "package.json").write_text('{"dependencies": {"dsh-claude-bridge": "github:x#v1", "other": "1"}}')
        (self.home / ".acpx").mkdir()
        (self.home / ".acpx/config.json").write_text('{"agents": {"dsh": {"command": "/b/dsh-claude-bridge run --profile acp"}, "codex": {"command": "codex"}}}')
        (self.home / ".config/mcacp").mkdir(parents=True)
        (self.home / ".config/mcacp/mcacp.json").write_text('{"agent_servers": {"dsh": {"command": "/b/dsh-claude-bridge", "args": []}}}')
        (self.home / ".local/share/mcacp").mkdir(parents=True)
        (self.home / ".local/share/mcacp/package.json").write_text('{"name": "mcacp-local"}')
        bridge.EVENTS.parent.mkdir(parents=True); bridge.EVENTS.write_text("{}\n")

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(bridge, k, v)

    def test_dry_run_changes_nothing(self):
        before = sorted(str(p) for p in self.home.rglob("*"))
        self.assertEqual(bridge.uninstall(self.c, dry_run=True, purge=True), 0)
        self.assertEqual(sorted(str(p) for p in self.home.rglob("*")), before)
        self.assertEqual(self.calls, [])

    def test_removes_only_what_setup_made(self):
        self.assertEqual(bridge.uninstall(self.c, dry_run=False, purge=False), 0)
        for p in ("web", "acp"):
            text = (self.home / ".dsh/profiles" / p / "cordis.patch.yml").read_text()
            self.assertNotIn(bridge.BEGIN, text)
            self.assertIn("- id: keep-me", text)
        self.assertFalse(os.path.lexists(self.home / "bin/dsh-claude-bridge"))
        self.assertEqual((self.home / "bin/dsh-turns").read_text(), "someone else's script")
        self.assertFalse(os.path.lexists(self.home / ".claude/skills/dsh-harness"))
        acpx = __import__("json").loads((self.home / ".acpx/config.json").read_text())
        self.assertEqual(list(acpx["agents"]), ["codex"])
        removes = [c for c in self.calls if "remove" in c and "dsh-claude-bridge" in c]
        self.assertEqual([c[c.index("--profile") + 1] for c in removes], ["acp", "web"])  # web last: this CLI lives there
        self.assertIn(["claude", "mcp", "remove", "mcacp", "-s", "user"], self.calls)
        self.assertFalse((self.home / ".local/share/mcacp").exists())
        self.assertTrue(bridge.CONFIG.exists())
        self.assertTrue(bridge.EVENTS.exists())

    def test_deletes_the_channel_config_only_when_it_is_ours(self):
        cm = bridge.channel_mcp_file()
        cm.write_text(__import__("json").dumps(bridge.channel_mcp(self.c)))
        self.assertEqual(bridge.uninstall(self.c, dry_run=False, purge=False), 0)
        self.assertFalse(cm.exists())
        cm.write_text('{"mcpServers": {"mine": {"command": "/somebody/else"}}}')
        bridge.uninstall(self.c, dry_run=False, purge=False)
        self.assertTrue(cm.exists())

    def test_channel_config_points_claude_at_the_linked_server(self):
        server = bridge.channel_mcp(self.c)["mcpServers"]["dsh-channel"]
        self.assertEqual(server, {"command": str(self.home / "bin/dsh-claude-channel"), "args": ["--role", "claude"]})

    def test_removes_our_stop_hook_and_keeps_the_rest(self):
        import json
        sp = self.home / ".claude/settings.json"
        other = {"hooks": [{"type": "command", "command": "bash other.sh"}]}
        sp.write_text(json.dumps({"model": "m", "hooks": {"Stop": [other, bridge.stop_hook_entry(self.c)]}}, indent=2) + "\n")
        self.assertEqual(bridge.uninstall(self.c, dry_run=False, purge=False), 0)
        self.assertEqual(json.loads(sp.read_text()), {"model": "m", "hooks": {"Stop": [other]}})
        self.assertTrue(list((self.home / ".local/state/dsh-claude-bridge/backups").glob("settings.json.*")))

    def test_purge_also_removes_config_and_events(self):
        bridge.uninstall(self.c, dry_run=False, purge=True)
        self.assertFalse(bridge.CONFIG.exists())
        self.assertFalse(bridge.EVENTS.exists())

    def test_keeps_mcacp_when_it_serves_other_agents(self):
        (self.home / ".config/mcacp/mcacp.json").write_text(
            '{"agent_servers": {"dsh": {"command": "/b/dsh-claude-bridge"}, "gemini": {"command": "gemini"}}}')
        bridge.uninstall(self.c, dry_run=False, purge=False)
        self.assertNotIn(["claude", "mcp", "remove", "mcacp", "-s", "user"], self.calls)
        self.assertTrue((self.home / ".local/share/mcacp").exists())
        servers = __import__("json").loads((self.home / ".config/mcacp/mcacp.json").read_text())["agent_servers"]
        self.assertEqual(list(servers), ["gemini"])

    def test_second_run_finds_nothing(self):
        bridge.uninstall(self.c, dry_run=False, purge=False)
        self.calls.clear()
        for p in ("web", "acp"):
            (self.home / ".dsh/profiles" / p / "package.json").write_text('{"dependencies": {"other": "1"}}')
        self.assertEqual(bridge.uninstall(self.c, dry_run=False, purge=False), 0)
        self.assertEqual(self.calls, [])


class ClaudeDoneHookTests(unittest.TestCase):
    """The Stop hook that writes Claude's "done" events, and how setup/uninstall edit settings.json."""

    def test_merge_adds_once_and_keeps_other_stop_hooks(self):
        entry = bridge.stop_hook_entry(cfg(BIN_DIR="/b"))
        self.assertEqual(entry, {"hooks": [{"type": "command", "command": "/b/claude-turn-event", "timeout": 5}]})
        mine = {"matcher": "*", "hooks": [{"type": "command", "command": "bash other.sh"}]}
        s = {"model": "x", "hooks": {"Stop": [mine], "PreToolUse": [mine]}}
        s2, changed = bridge.merge_stop_hook(s, entry)
        self.assertTrue(changed)
        self.assertEqual(s2["hooks"]["Stop"], [mine, entry])
        self.assertEqual(s2["hooks"]["PreToolUse"], [mine])
        self.assertEqual(s2["model"], "x")
        s3, changed = bridge.merge_stop_hook(s2, entry)
        self.assertFalse(changed)
        self.assertEqual(s3, s2)

    def test_merge_replaces_an_entry_with_an_old_path(self):
        old = {"hooks": [{"type": "command", "command": "/old/bin/claude-turn-event", "timeout": 5}]}
        new = bridge.stop_hook_entry(cfg(BIN_DIR="/b"))
        s, changed = bridge.merge_stop_hook({"hooks": {"Stop": [old]}}, new)
        self.assertTrue(changed)
        self.assertEqual(s["hooks"]["Stop"], [new])

    def test_merge_into_settings_without_hooks(self):
        s, changed = bridge.merge_stop_hook({}, bridge.stop_hook_entry(cfg(BIN_DIR="/b")))
        self.assertTrue(changed)
        self.assertEqual(len(s["hooks"]["Stop"]), 1)

    def test_drop_removes_only_ours(self):
        mine = {"matcher": "*", "hooks": [{"type": "command", "command": "bash other.sh"}]}
        ours = bridge.stop_hook_entry(cfg(BIN_DIR="/b"))
        s, changed = bridge.drop_stop_hook({"hooks": {"Stop": [mine, ours]}})
        self.assertTrue(changed)
        self.assertEqual(s["hooks"]["Stop"], [mine])
        s, changed = bridge.drop_stop_hook({"hooks": {"Stop": [ours]}, "x": 1})
        self.assertEqual(s, {"hooks": {}, "x": 1})
        self.assertFalse(bridge.drop_stop_hook({"hooks": {"Stop": [mine]}})[1])

    def run_hook(self, stdin, env_file):
        import subprocess, sys
        env = {**os.environ, "CLAUDE_TURN_EVENTS_FILE": str(env_file)}
        return subprocess.run([sys.executable, str(BIN.parent / "claude-turn-event")], input=stdin,
                              capture_output=True, text=True, env=env, timeout=30)

    def test_hook_appends_one_private_line_per_stop(self):
        import json, stat
        ev = Path(tempfile.mkdtemp()) / "state" / "turns.jsonl"
        payload = {"session_id": "s-1", "cwd": "/w", "transcript_path": "/t.jsonl", "hook_event_name": "Stop",
                   "last_assistant_message": "done: " + "x" * 9000}
        r = self.run_hook(json.dumps(payload), ev)
        self.assertEqual((r.returncode, r.stdout), (0, ""))  # a Stop hook's stdout could be read as a decision
        r = self.run_hook(json.dumps({**payload, "last_assistant_message": "second"}), ev)
        lines = [json.loads(l) for l in ev.read_text().splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual({k: lines[0][k] for k in ("event", "session_id", "cwd")}, {"event": "stop", "session_id": "s-1", "cwd": "/w"})
        self.assertEqual(len(lines[0]["last_assistant_message"]), 8000)
        self.assertTrue(lines[0]["truncated"])
        self.assertEqual(lines[1]["last_assistant_message"], "second")
        self.assertEqual(stat.S_IMODE(ev.stat().st_mode), 0o600)

    def test_hook_never_fails_a_turn(self):
        ev = Path(tempfile.mkdtemp()) / "turns.jsonl"
        r = self.run_hook("not json", ev)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertFalse(ev.exists())
        blocked = Path(tempfile.mkdtemp()) / "file"
        blocked.write_text("x")
        r = self.run_hook('{"session_id": "s"}', blocked / "sub" / "turns.jsonl")  # parent is a file: write fails
        self.assertEqual((r.returncode, r.stdout), (0, ""))


class CliTests(unittest.TestCase):
    def test_every_subcommand_parses(self):
        import subprocess, sys
        for cmd in ([], ["doctor"], ["setup"], ["run"], ["uninstall"]):
            r = subprocess.run([sys.executable, str(BIN), *cmd, "--help"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{cmd}: {r.stderr[-300:]}")
        self.assertIn("--dry-run", subprocess.run([sys.executable, str(BIN), "uninstall", "--help"], capture_output=True, text=True).stdout)


class EnvTests(unittest.TestCase):
    def test_clean_env_has_key_under_bridge_name_only(self):
        os.environ["ANTHROPIC_BASE_URL"] = "https://leak.example"
        os.environ["SOME_CALLER_VAR"] = "x"
        os.environ["PASSME"] = "y"
        try:
            env = bridge.clean_env(cfg(PASS_ENV="PASSME"), "/usr/bin/node")
        finally:
            for k in ("ANTHROPIC_BASE_URL", "SOME_CALLER_VAR", "PASSME"):
                os.environ.pop(k, None)
        self.assertEqual(env["BRIDGE_PROVIDER_KEY"], "sk-test-123")
        self.assertEqual(env["PASSME"], "y")
        self.assertFalse([k for k in env if k.startswith("ANTHROPIC_")])
        self.assertNotIn("SOME_CALLER_VAR", env)
        self.assertTrue(env["PATH"].startswith("/usr/bin"))


if __name__ == "__main__":
    unittest.main()
