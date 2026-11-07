import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit', ROOT / 'tools/ads-audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def test_only_unconditional_domain_rules(self):
        self.assertEqual(audit.parse_adblock_line('||ads.example.com^'), 'ads.example.com')
        for line in ('||example.com/ads.js$script,third-party',
                     '||example.com^$domain=news.example',
                     '||example.com^$important', '|https://example.com/ad',
                     '||example.com^$badfilter', '||example.com^extra'):
            self.assertIsNone(audit.parse_adblock_line(line), line)

    def test_exceptions_quarantine_parent_and_children(self):
        text = '\n'.join(['||example.com^', '||ads.example.com^',
                          '||other.test^', '@@||login.example.com/path$document'])
        self.assertEqual(audit.parse_adblock(text), {'ads.example.com', 'other.test'})
        self.assertEqual(audit.parse_adblock('||ads.example.com^\n@@||example.com^'), set())

    def test_order_independent_and_no_substring_confusion(self):
        lines = ['||example.com^', '@@||example.com^', '||notexample.com^']
        self.assertEqual(audit.parse_adblock('\n'.join(lines)), {'notexample.com'})
        self.assertEqual(audit.parse_adblock('\n'.join(reversed(lines))), {'notexample.com'})

    def test_admitted_delivery_host_has_no_root_expansion(self):
        import json

        entries = json.loads((ROOT / 'src/ads/admission.json').read_text())['entries']
        groups = audit.load_categories()
        for entry in entries:
            group = next(g for g in groups if g['id'] == entry['group'])
            self.assertEqual(entry['scope'], 'exact')
            self.assertIn(entry['domain'], group['rules'])
            self.assertIn('https://', entry['purpose_source'])
            self.assertIn('advertising', audit.classify_candidate(entry['domain'], groups, [])['categories'])
            for host in entry['protected_hosts']:
                self.assertEqual(audit.classify_candidate(host, groups, [])['categories'], ['unknown'])

    def test_category_inventory_and_dns_separation(self):
        groups = audit.load_categories()
        self.assertEqual(len(groups), 24)
        self.assertEqual(next(g['category'] for g in groups if g['id'] == 'doh_public'), 'dns_control')
        result = audit.classify_candidate('unknown-ad.example.com', groups, ['example.com'])
        self.assertEqual(result['categories'], ['unknown'])
        self.assertEqual(result['shared_infrastructure'], 'example.com')
        self.assertFalse(result['auto_admit'])

    def test_category_exact_and_wildcard_scope(self):
        groups = [{'id': 'test', 'category': 'analytics', 'rules': ['=metrics.example', 'exact.example']}]
        self.assertEqual(audit.classify_candidate('a.metrics.example', groups, [])['categories'], ['analytics'])
        self.assertEqual(audit.classify_candidate('a.exact.example', groups, [])['categories'], ['unknown'])
        self.assertEqual(audit.classify_candidate('notmetrics.example', groups, [])['categories'], ['unknown'])

    def test_allowlist_is_not_a_block_candidate(self):
        self.assertIsNone(audit.parse_adblock_line('@@||example.com^'))
        self.assertIsNone(audit.parse_adblock_line('||*.example.com^'))


if __name__ == '__main__':
    unittest.main()
