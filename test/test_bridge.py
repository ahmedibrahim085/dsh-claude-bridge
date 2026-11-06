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
