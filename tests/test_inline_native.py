import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("inline_native", ROOT / "tools/inline-native.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InlineTests(unittest.TestCase):
    def test_idempotent_and_preserves_exceptions(self):
        profile = '[Host]\n[Rule]\nDOMAIN,allow.example,DIRECT\nFINAL,Proxy\n[Plugin]\n' + module.BASE + 'adfilter/adfilter.plugin,enabled=true\n'
        plugin = '[Rule]\nDOMAIN,ad.example,REJECT\n# DOMAIN,optional.example,REJECT\n'
        result = module.merge(profile, plugin, 'adfilter')
        self.assertEqual(result, module.merge(result, plugin, 'adfilter'))
        self.assertLess(result.index('allow.example'), result.index('ad.example'))
        self.assertLess(result.index('ad.example'), result.index('FINAL'))
        self.assertNotIn('optional.example', result)
        self.assertNotIn('https:', result)

    def test_refuses_other_capabilities(self):
        with self.assertRaises(ValueError):
            module.merge('[Host]\n[Rule]\nFINAL,DIRECT\n', '[Script]\nanything', 'taobao')

    def test_host_conflict(self):
        with self.assertRaises(ValueError):
            module.merge('[Host]\nAD.example=192.0.2.1\n', '[Host]\nad.example = 127.0.0.1', 'taobao')


if __name__ == '__main__':
    unittest.main()
