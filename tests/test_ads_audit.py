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

    def test_dual_stack_rule_derivation_ads_and_apps(self):
        import json
        import subprocess
        import sys

        tools_dir = str(ROOT / 'tools')
        sys.path.insert(0, tools_dir)
        try:
            spec_ads = importlib.util.spec_from_file_location('build_ads', ROOT / 'tools/build-ads.py')
            build_ads = importlib.util.module_from_spec(spec_ads)
            spec_ads.loader.exec_module(build_ads)

            spec_apps = importlib.util.spec_from_file_location('build_apps', ROOT / 'tools/build-apps.py')
            build_apps = importlib.util.module_from_spec(spec_apps)
            spec_apps.loader.exec_module(build_apps)
        finally:
            if sys.path and sys.path[0] == tools_dir:
                sys.path.pop(0)

        plugin = {
            'file': 'test.plugin',
            'rules': ['DOMAIN,already.example,REJECT', 'DOMAIN-KEYWORD,httpdns,REJECT-DROP'],
            'groups': [
                {'id': 'a', 'title': 'Active', 'rules': ['=adnet.example', 'sub.adnet.example', 'exact.example']},
                {'id': 'b', 'title': 'Disabled', 'disabled': True, 'rules': ['=opt.example', 'opt2.example']},
            ],
        }
        records, dual = build_ads.collect_host_groups(plugin, set(), [], {})
        self.assertEqual(len(records), 2)
        self.assertEqual(dual, ['DOMAIN-SUFFIX,adnet.example,REJECT', 'DOMAIN,exact.example,REJECT'])

        app_dual = build_apps.derive_dual_stack_rules(
            {'a.example', '*.a.example', 'b.example', 'dup.example'},
            {'a.example'},
            ['DOMAIN, dup.example, REJECT'],
        )
        self.assertEqual(app_dual, ['DOMAIN-SUFFIX,a.example,REJECT', 'DOMAIN,b.example,REJECT'])

        bili = json.loads((ROOT / 'src/apps/bilibili.json').read_text(encoding='utf-8'))
        story = next(r for r in bili['enhance']['rewrite'] if r['id'] == 'clean-feed-story')
        expr = story['action'].split('response.json.jq("', 1)[1][:-2].replace('\\"', '"')
        sample = {
            'data': {
                'items': [
                    {'card_goto': 'av'},
                    {'card_goto': 'ad_web_s'},
                    {'card_goto': 'vertical_ad_av'},
                    {'card_goto': 'vertical_ad_live'},
                    {'card_goto': 'vertical_ad_picture'},
                    {'card_goto': 9},
                ]
            }
        }
        res = subprocess.run(['jq', '-c', expr], input=json.dumps(sample), capture_output=True, text=True, check=True)
        out = json.loads(res.stdout)
        self.assertEqual([it['card_goto'] for it in out['data']['items']], ['av', 9])

    def test_banks_zero_mitm_and_joint_stock_protection(self):
        """Ensure banks.plugin stays zero-MITM and protects all Big-6 + 12 joint-stock + key city bank roots."""
        import json

        banks_cfg = json.loads((ROOT / 'src/apps/banks.json').read_text(encoding='utf-8'))
        banks_plugin = (ROOT / 'plugins/banks/banks.plugin').read_text(encoding='utf-8')
        protected = set(json.loads((ROOT / 'src/ads/protected-roots.json').read_text(encoding='utf-8'))['roots'])

        self.assertIsNone(banks_cfg.get('enhance'))
        for forbidden_section in ('[MITM]', '[Rewrite]', '[Script]'):
            self.assertNotIn(f'\n{forbidden_section}\n', banks_plugin)
        self.assertIn('# lban.spdb.com.cn = 127.0.0.1', banks_plugin)

        required_bank_roots = {
            'icbc.com.cn', 'ccb.com', 'ccb.com.cn', 'abchina.com', 'abchina.com.cn', '95599.cn',
            'boc.cn', 'bankofchina.com', 'bankcomm.com', 'bankcomm.cn', 'psbc.com', 'psbc.com.cn',
            'cmbchina.com', 'cmbimg.com', 'cmbimg.cn', 'spdb.com.cn', 'spdbccc.com.cn', '95528.cn',
            'ecitic.com', 'citicbank.com', 'cebbank.com', 'cebbank.com.cn', 'cgbchina.com.cn',
            '95508.com', 'cib.com.cn', 'cibfintech.com', 'cmbc.com.cn', 'hxb.com.cn', 'pingan.com',
            'pingan.com.cn', 'czbank.com', 'cbhb.com.cn', 'hfbank.com.cn', 'bosc.cn',
            'bankofbeijing.com.cn', '95516.com', 'cup.com.cn', 'unionpay.com', 'unionpayintl.com',
        }
        self.assertTrue(required_bank_roots.issubset(protected))
        redline_families = {r['domain'] for r in banks_cfg['redlines'] if r['kind'] == 'family'}
        self.assertTrue(required_bank_roots.issubset(redline_families))

    def test_banks_mitm_ordering_quic_and_core_gateway_isolation(self):
        """Ensure banks-mitm checks splash video before image fallback and isolates pinned core gateways."""
        import json

        mitm_cfg = json.loads((ROOT / 'src/apps/banks-mitm.json').read_text(encoding='utf-8'))
        mitm_plugin = (ROOT / 'plugins/banks-mitm/banks-mitm.plugin').read_text(encoding='utf-8')
        rewrites = mitm_cfg['enhance']['rewrite']
        ids = [r['id'] for r in rewrites]
        self.assertIn('kill-cmb-adplatform-video', ids)
        self.assertIn('kill-cmb-adplatform', ids)
        self.assertLess(ids.index('kill-cmb-adplatform-video'), ids.index('kill-cmb-adplatform'))
        self.assertEqual(rewrites[ids.index('kill-cmb-adplatform-video')]['action'], 'reject_video(200)')
        self.assertEqual(rewrites[ids.index('kill-cmb-adplatform')]['action'], 'reject_img(200)')

        # Plugin-level rewrite order must preserve video-before-image matching and exact QUIC fallbacks.
        self.assertLess(mitm_plugin.index('reject_video(200)'), mitm_plugin.index('reject_img(200)'))
        self.assertNotIn('\n[Host]\n', mitm_plugin)
        hosts = mitm_cfg['enhance']['mitm_hosts']
        for host in hosts:
            self.assertIn(f'AND,((DOMAIN-SUFFIX,{host}),(PROTOCOL,QUIC)),REJECT', mitm_plugin)

        pinned_core = {
            'mlife.cmbchina.com', 'az1mbasecc.bas.cmbchina.com', 'intellicc.bas.cmbchina.com',
            'mbmodule-openapi.paas.cmbchina.com', 'creditcardapp.bankcomm.com',
            'creditcardapp.bankcomm.cn', 'creditcard.bankcomm.com', 'wallet.95516.com',
            'mobilepaas.abchina.com.cn', 'yunbusiness.ccb.com', 'mbs.boc.cn', 'd.psbc.com',
            'oisc.icbc.com.cn', 'per.spdb.com.cn', 'ebank.spdb.com.cn',
        }
        self.assertTrue(pinned_core.isdisjoint(set(hosts)))


if __name__ == '__main__':
    unittest.main()
