import contextlib
import importlib.util
import io
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("private_config", ROOT / "tools/make-private-config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class PrivateConfigTests(unittest.TestCase):
    def test_duplicate_nodes_are_idempotent(self):
        line = 'node = Socks5,example.com,443,user,"secret"'
        self.assertEqual(config.unique_definitions(line + "\n" + line, "Proxy"), [line])

    def test_conflicting_nodes_fail_without_credentials(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
            config.unique_definitions(
                'node = Socks5,example.com,443,user,"secret-one"\n'
                'node = Socks5,example.com,443,user,"secret-two"', "Proxy"
            )
        self.assertNotIn("secret-one", output.getvalue())
        self.assertNotIn("secret-two", output.getvalue())

    def test_retired_plugins_cannot_return_via_backup(self):
        retired = "https://kelee.one/Tool/Loon/Lpx/BlockAdvertisers.lpx,enabled=true"
        for platform in ("all", "ios", "ipados", "macos", "tvos"):
            self.assertNotIn("kelee.one", config.filter_plugins(retired, platform))
        merged, _ = config.merge_plugins("", retired, True)
        self.assertNotIn("kelee.one", merged)

    def test_mobile_profiles_keep_mobile_plugins(self):
        mobile = "https://raw.githubusercontent.com/AshNail/plugins/main/plugins/soda/soda.plugin,enabled=true"
        for platform in ("ios", "ipados"):
            self.assertIn("soda.plugin", config.filter_plugins(mobile, platform))
        self.assertNotIn("soda.plugin", config.filter_plugins(mobile, "macos"))

    def test_device_rules_are_explicit_and_complete(self):
        baseline = {"Rule": "FINAL,Final", "General": "ip-mode=v4-only"}
        device = {"Rule": "DOMAIN,fnos,DIRECT\nDOMAIN,sub.example,Proxy\nFINAL,Proxy"}
        result = config.with_device_rules(baseline, device)
        self.assertEqual(result["Rule"], device["Rule"])
        self.assertEqual(baseline["Rule"], "FINAL,Final")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            config.with_device_rules(baseline, {})

    def test_native_inlining_updates_counts_and_is_idempotent(self):
        body = '[Host]\n[Rule]\nFINAL,DIRECT\n[Plugin]\n'
        summary = {'plugins': {'total': 0}, 'rule_total': 1, 'host_total': 0}
        result, stats = config.inline_native_modules(body, summary)
        self.assertEqual(stats['host_total'], 12)
        self.assertEqual(stats['rule_total'], 12)
        self.assertEqual(config.inline_native_modules(result, stats)[0], result)
        self.assertEqual(summary['host_total'], 0)
        self.assertNotIn('[MITM]', result)

    def test_device_plugins_preserve_order_and_disabled_state(self):
        baseline = {'Plugin': 'https://example.com/removed.plugin,enabled=true'}
        device = {'Plugin': 'https://example.com/b.plugin,enabled=false\nhttps://example.com/a.plugin,enabled=true'}
        result = config.with_device_plugins(baseline, device)
        self.assertEqual(result['Plugin'], device['Plugin'])
        self.assertIn('removed.plugin', baseline['Plugin'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            config.with_device_plugins(baseline, {})

    def test_deprecated_general_keys_are_dropped(self):
        text, stats = config.merge_general('', 'switch-node-after-failure-times = 2\nforce-http-engine-hosts = :8080\nskip-first-packet = true\n')
        self.assertEqual(text, '')
        self.assertEqual(set(stats['dropped']), {'switch-node-after-failure-times', 'force-http-engine-hosts', 'skip-first-packet'})

    def test_main_profile_never_emits_ip_rewrite(self):
        public = {'General': '', 'Host': '', 'Rule': 'FINAL,DIRECT', 'Plugin': 'https://example.com/a.plugin,enabled=true', 'MITM': 'hostname = example.com'}
        device = {'Proxy': 'N = HTTP,example.com,80', 'Remote Proxy': 'S = https://sub.example/x', 'Proxy Group': 'P = select,DIRECT', 'MITM': 'ca-p12 = x\nca-passphrase = y', 'IP Rewrite': '203.0.113.9 = drop'}
        with contextlib.redirect_stderr(io.StringIO()):
            body, summary = config.build(public, device)
        self.assertNotIn('[IP Rewrite]', body)
        self.assertEqual(summary['ip_rewrite'], 0)
        self.assertEqual(summary['ip_rewrite_dropped'], 1)

    def test_host_case_conflict_keeps_public_mapping(self):
        merged, stats = config.merge_hosts('example.com = 127.0.0.1', 'EXAMPLE.COM = server:203.0.113.53', False)
        self.assertIn('example.com = 127.0.0.1', merged)
        self.assertNotIn('EXAMPLE.COM', merged)
        self.assertEqual(stats['conflicts'], ['EXAMPLE.COM'])

    def test_host_name_case_is_preserved(self):
        merged, _ = config.merge_hosts("", "fnos = server:192.168.31.1\nFNOS = server:192.168.31.1", False)
        self.assertIn("fnos = server:192.168.31.1", merged)
        self.assertIn("FNOS = server:192.168.31.1", merged)


if __name__ == "__main__":
    unittest.main()
