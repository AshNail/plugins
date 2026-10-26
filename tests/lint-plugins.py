#!/usr/bin/env python3
"""Structural lint for the Loon plugins (soda/douyin + the single ads plugin)."""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (path, sections, rules, rewrites, scripts, family)
PLUGINS = [
    ("plugins/soda/soda.plugin", 5, 0, 2, 39, "soda"),
    ("plugins/douyin/douyin.plugin", 5, 0, 1, 10, "douyin"),
]

# 只读观测脚本不需要 argument
OBSERVER_SCRIPTS = ("reward-observe.min.js", "observe.min.js")

FAMILY_CHECKS = {
    "soda": {
        "switches": [
            ("rewardSafe", "true"),
            ("cleanAds", "false"),
            ("killRewardAds", "false"),
            ("blockAdDomains", "false"),
            ("settingsClean", "false"),
            ("hideDouyinEntry", "false"),
            ("blockSplashAd", "false"),
            ("debugLog", "false"),
            ("logTaskTitles", "false"),
            ("splashClean", "true"),
            ("hideDouyinTab", "false"),
            ("dailyReminder", "false"),
        ],
        "enable": {
            "splashClean": 1,
            "cleanAds": 9,
            "killRewardAds": 2,
            "blockAdDomains": 1,
            "settingsClean": 1,
            "hideDouyinEntry": 1,
            "blockSplashAd": 1,
            "debugLog": 22,
        },
        "mitm": [
            "api.qishui.com",
            "conf.qishui.com",
            "ad.zijieapi.com",
            "lianmengapi.snssdk.com",
            "ads5-normal-hl.zijieapi.com",
            "zlink.ugsdk.cn",
            "praisewindow.ugsdk.cn",
            "beta-luna.douyin.com",
        ],
        "samples": {
            "search-block": "https://api.qishui.com/luna/search-block",
            "search-categories": "https://api.qishui.com/luna/search-categories",
            "card": "https://api.qishui.com/luna/card",
            "growth": "https://api.qishui.com/luna/growth/activity_entrance",
            "fallback": "https://api.qishui.com/luna/advert/fallback/done/info",
            "feed": "https://api.qishui.com/luna/feed/song-tab",
        },
    },
    "douyin": {
        "switches": [
            ("treasureMinimal", "true"),
            ("cleanFeedAds", "false"),
            ("killRewardAds", "false"),
            ("cleanUpsell", "false"),
            ("cleanActivity", "false"),
            ("blockAdDomains", "false"),
            ("debugLog", "false"),
            ("dailyReminder", "false"),
        ],
        "enable": {
            "treasureMinimal": 1,
            "cleanFeedAds": 1,
            "killRewardAds": 1,
            "cleanUpsell": 2,
            "cleanActivity": 1,
            "blockAdDomains": 1,
            "debugLog": 2,
        },
        "mitm": [
            "beta-luna.douyin.com",
            "polaris.zijieapi.com",
            "ad.zijieapi.com",
            "lianmengapi.snssdk.com",
            "ads5-normal-hl.zijieapi.com",
            "zlink.ugsdk.cn",
            "praisewindow.ugsdk.cn",
        ],
        "samples": {
            "treasure-page": "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
            "incentive-config": "https://beta-luna.douyin.com/luna/advert/incentive/config",
            "incentive-retrieve": "https://beta-luna.douyin.com/luna/advert/incentive/retrieve",
            "ads-dsp": "https://beta-luna.douyin.com/luna/ads/dsp/retrieve",
            "upsell": "https://beta-luna.douyin.com/luna/commerce/v2/upsell",
            "music-festival": "https://beta-luna.douyin.com/luna/growth/music_festival/performance_details",
        },
    },
}

# ads：单插件，[General] + [Rule] + [Host]。
# 生成物由 tools/build-ads.py --check 做逐字节比对，这里只做结构与安全边界检查，
# 避免每次加域名都要同步改 lint 的精确计数。
ADS_PLUGIN = "plugins/ads/ads.plugin"
ADS_RETIRED = (
    "plugins/ads/ads-httpdns.plugin",
    "plugins/ads/ads-measurement.plugin",
    "plugins/ads/ads-strict.plugin",
)
ADS_HOST_RE = re.compile(
    r"^(\*\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}"
    r" = 127\.0\.0\.1$"
)
ADS_META_KEYS = (
    "name",
    "desc",
    "author",
    "version",
    "homepage",
    "icon",
    "system",
    "loon_version",
    "date",
    "tag",
)
ADS_GENERAL_KEYS = {
    "bypass-tun",
    "include-tun",
    "skip-proxy",
    "real-ip",
    "dns-server",
    "doh-server",
    "doq-server",
    "doh3-server",
    "ipv6-vif",
}
ADS_RULE_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "DOMAIN-WILDCARD",
    "USER-AGENT",
    "URL-REGEX",
    "IP-CIDR",
    "IP-CIDR6",
    "DEST-PORT",
    "SRC-PORT",
    "PROTOCOL",
    "GEOIP",
    "IP-ASN",
}

# docs/cn/protocol_rule.md：Loon（3.1.7+）PROTOCOL 规则支持的全量取值。
PROTOCOL_VALUES = {"HTTP", "HTTPS", "TCP", "QUIC", "STUN", "UDP"}

errors = []

COMMON_DIR = ROOT / "src/common"
FAMILIES_FILE = COMMON_DIR / "families.json"


def to_config_str(value):
    """families.json 的布尔值要写进 JS 源码，统一为小写字面量。"""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def load_families():
    try:
        return json.loads(FAMILIES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"src/common/families.json: cannot read: {exc}")
        return None


def blocked_hosts_from_source(path, label):
    """从 src/common 或 src/<family> 的 block-domains.js 解析 BLOCKED_HOSTS。"""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    m = re.search(r"BLOCKED_HOSTS\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        errors.append(f"{label}: cannot find BLOCKED_HOSTS array")
        return set()
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def parse_plugin(path):
    data = {}
    sections = []
    cur = None
    for line in path.read_text().splitlines():
        s = line.strip()
        m = re.match(r"^\[([A-Za-z]+)\]$", s)
        if m:
            cur = m.group(1)
            sections.append(cur)
            data.setdefault(cur, [])
            continue
        if cur and s and not s.startswith(("#", ";")):
            data[cur].append(s)
    return data, sections


def regex_literal(line):
    """从新版语法里取出 /.../ 正则字面量（到 " then " 为止，避免被转义斜杠截断）。"""
    m = re.search(r"\$\{url\} ~\= (/.+?)(?: then |$)", line)
    if not m:
        return None
    body = m.group(1)
    if not body.startswith("/") or not body.endswith("/"):
        return None
    return body[1:-1]


def parse_meta(path):
    meta = {}
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s.startswith("#!"):
            continue
        if "=" not in s:
            continue
        key, value = s[2:].split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


for fp, want_sections, want_rules, want_rewrites, want_scripts, family in PLUGINS:
    path = ROOT / fp
    data, sections = parse_plugin(path)
    family_meta = parse_meta(path)
    # 插件元数据下限：#!date 让 Loon 卡片显示更新时间，与 ads 插件对齐。
    for key in ("name", "desc", "author", "version", "date"):
        if key not in family_meta:
            errors.append(f"{fp}: missing #!{key} metadata")

    rules = [l for l in data.get("Rule", []) if l.startswith("DOMAIN,")]
    rewrites = [
        l for l in data.get("Rewrite", [])
        if "reject(" in l or "reject-" in l
    ]
    scripts = [
        l for l in data.get("Script", [])
        if l.startswith(("response if", "request if"))
    ]

    for line in rewrites:
        rx = regex_literal(line)
        if not rx:
            errors.append(f"{fp}: rewrite without a url regex: {line[:100]}")
            continue
        try:
            re.compile(rx)
        except re.error as exc:
            errors.append(f"{fp}: rewrite regex: {exc}")

    compiled = []
    for line in scripts:
        m = re.match(r'^(response|request) if \$\{url\} ~\= (/.+?/) then script\("([^"]+)"', line)
        rx = regex_literal(line)
        if not m or not rx:
            errors.append(f"{fp}: malformed script line: {line[:100]}")
            continue
        try:
            compiled.append(re.compile(rx))
        except re.error as exc:
            errors.append(f"{fp}: script regex: {exc}")
        if not m.group(3).endswith(".min.js"):
            errors.append(f"{fp}: deployable script must be minified (.min.js): {m.group(3)}")

        script_path = path.parent / m.group(3)
        if not script_path.exists():
            errors.append(f"{fp}: missing script file {script_path}")
        else:
            source_name = pathlib.Path(m.group(3)).name.replace(".min.js", ".js")
            source_path = ROOT / "src" / family / source_name
            if not source_path.exists():
                errors.append(f"{fp}: missing source file {source_path}")
            else:
                if script_path.stat().st_size >= source_path.stat().st_size:
                    errors.append(
                        f"{fp}: script is not actually compressed: "
                        f"{source_path.name} {source_path.stat().st_size}B -> "
                        f"{script_path.name} {script_path.stat().st_size}B"
                    )
                try:
                    line_count = len(script_path.read_text().splitlines())
                    if line_count > 5:
                        errors.append(
                            f"{fp}: minified script still has {line_count} lines: "
                            f"{script_path.name}"
                        )
                except UnicodeDecodeError:
                    errors.append(f"{fp}: minified script is not UTF-8: {script_path}")
            try:
                check = subprocess.run(
                    ["node", "--check", str(script_path)],
                    capture_output=True,
                    text=True,
                )
                if check.returncode != 0:
                    errors.append(
                        f"{fp}: invalid minified script {script_path}: "
                        f"{check.stderr.strip()[:200]}"
                    )
            except FileNotFoundError:
                errors.append("node not found; cannot validate minified scripts")

    actual = (len(sections), len(rules), len(rewrites), len(scripts))
    expected = (want_sections, want_rules, want_rewrites, want_scripts)
    if actual != expected:
        errors.append(f"{fp}: counts {actual}, expected {expected}")

    print(
        f"{fp}: sections={len(sections)} rules={len(rules)} "
        f"rewrites={len(rewrites)} scripts={len(scripts)}"
    )

    spec = FAMILY_CHECKS[family]

    meta = parse_meta(path)
    for key in ("name", "desc", "author", "version", "homepage", "icon"):
        if key not in meta:
            errors.append(f"{fp}: missing #!{key} metadata")
    if "icon" in meta and not meta["icon"].startswith("https://"):
        errors.append(f"{fp}: #!icon must be an https URL, got {meta['icon'][:60]}")
    print(f"  meta: {meta.get('name', '?')} v{meta.get('version', '?')} icon={meta.get('icon', '-')[:60]}")

    arg_text = "\n".join(data.get("Argument", []))
    for name, default in spec["switches"]:
        if f"{name} = switch,{default}" not in arg_text:
            errors.append(
                f"{fp}: missing or wrong Argument switch {name} (expected default {default})"
            )

    # [Argument] 声明与 [Script]/[Rewrite] 引用对账。插件行是手工维护的，
    # ${名字} 出现 typo 时 build.js 不会拦截（它只 minify 脚本），Loon 会把
    # `${typo}` 原样带入插件，开关静默失灵。合法引用：已声明参数、引擎变
    # 量（${url}、${request.*}、${response.*}）、同一条 ` as xxx` 声明的捕获
    # 组（${xxx.1} 形态，Rewrite v2 官方示例 AutoRewrite_Example2.list 第六
    # 节同款语法）。
    declared_args = set()
    for arg_line in data.get("Argument", []):
        m_arg = re.match(r"^([A-Za-z_]\w*)\s*=", arg_line)
        if m_arg:
            declared_args.add(m_arg.group(1))
    ref_rx = re.compile(r"\$\{([^}]+)\}")
    for section in ("Script", "Rewrite"):
        for line in data.get(section, []):
            if line.lstrip().startswith("#"):
                continue
            as_names = set(re.findall(r"(?:^|[\s(])as\s+([A-Za-z_]\w*)", line))
            for ref in ref_rx.findall(line):
                m_cap = re.match(r"^([A-Za-z_]\w*)\.\d+$", ref)
                if (
                    ref not in declared_args
                    and ref != "url"
                    and not re.match(r"^(request|response)(\.|\[)", ref)
                    and not (m_cap and m_cap.group(1) in as_names)
                ):
                    errors.append(
                        f"{fp}: unresolved ${{{ref}}} in [{section}] "
                        f"(not a declared [Argument] or engine variable): {line[:80]}"
                    )

    if rules:
        errors.append(f"{fp}: plugin must not contain active static domain rules")

    for name, want in spec["enable"].items():
        got = sum(1 for line in scripts if f"enable=${{{name}}}" in line)
        if got != want:
            errors.append(f"{fp}: enable=${{{name}}} used {got} times, expected {want}")

    for line in scripts:
        if "enable=${" not in line:
            errors.append(f"{fp}: script missing enable switch: {line[:100]}")
        if "${" not in line.split("script(", 1)[-1] and not any(
                o in line for o in OBSERVER_SCRIPTS):
            errors.append(f"{fp}: script missing parameter binding: {line[:100]}")

    mitm = "\n".join(data.get("MITM", []))
    for host in spec["mitm"]:
        if host not in mitm:
            errors.append(f"{fp}: MITM missing {host}")

    for label, url in spec["samples"].items():
        hit = any(rx.match(url) for rx in compiled)
        print(f"  {family} sample {label:18} {'HIT' if hit else 'MISS'}")
        if not hit:
            errors.append(f"{fp}: sample {label} not matched")

    # ---- 「广告域名拦截」名单一致性：单一来源 src/common/block-domains.js ----
    # [Script] 正则、注释 [Rule] 严格模式、block-domains.js 的 BLOCKED_HOSTS
    # 必须是同一组域名；[MITM] 是超集（还包含业务域名），只要求包含该名单。
    block_common = blocked_hosts_from_source(
        COMMON_DIR / "block-domains.js", "src/common/block-domains.js")
    block_from_family = blocked_hosts_from_source(
        ROOT / "src" / family / "block-domains.js", f"src/{family}/block-domains.js")
    if block_from_family and block_from_family != block_common:
        errors.append(
            f"{fp}: src/{family}/block-domains.js diverges from src/common "
            f"(common={sorted(block_common)}, family={sorted(block_from_family)})"
        )

    raw_text = path.read_text(encoding="utf-8")
    strict_rules = set(re.findall(r"^#\s+DOMAIN,([a-z0-9.-]+),REJECT\s*$", raw_text, re.M))
    if strict_rules != block_common:
        errors.append(
            f"{fp}: commented [Rule] strict-mode set diverges from src/common "
            f"(rule={sorted(strict_rules)}, common={sorted(block_common)})"
        )

    script_regex_hosts = set()
    for line in scripts:
        if "block-domains.min.js" not in line:
            continue
        m = re.search(r"\$\{url\} ~\= (/.+?/) then", line)
        if not m:
            continue
        unescaped = re.sub(r"\\(.)", r"\1", m.group(1))
        script_regex_hosts = set(re.findall(r"([a-z0-9][a-z0-9.-]*\.[a-z]{2,})", unescaped))
    if not script_regex_hosts:
        errors.append(f"{fp}: cannot extract hosts from block-domains script regex")
    elif script_regex_hosts != block_common:
        errors.append(
            f"{fp}: block-domains [Script] regex host set diverges from src/common "
            f"(regex={sorted(script_regex_hosts)}, common={sorted(block_common)})"
        )
    for host in sorted(block_common):
        if host not in mitm:
            errors.append(f"{fp}: [MITM] missing block-domain host {host}")
    print(f"  block-domains set: {len(block_common)} hosts pinned to src/common")


def check_shared_scripts():
    """共享脚本（src/common -> src/<family>）必须与 families.json 展开一致。

    单一来源守卫：直接改 src/<family>/<shared>.js 属于漂移，
    必须改 src/common/*.js 或 families.json 后重跑 npm run build。
    """
    fam = load_families()
    if not fam:
        return
    scripts = fam.get("sharedScripts") or []
    tokens = fam.get("tokens") or []
    families = fam.get("families") or {}
    if not scripts or not tokens or not families:
        errors.append("src/common/families.json: needs sharedScripts/tokens/families")
        return

    for min_file in sorted((ROOT / "plugins").glob("*/scripts/*.min.js")):
        raw = min_file.read_text(encoding="utf-8", errors="ignore")
        if "@@" in raw:
            errors.append(
                f"{min_file.relative_to(ROOT)}: unresolved @@ token leaked into dist")

    for family in sorted(families):
        cfg = families[family]
        for name in scripts:
            common_file = COMMON_DIR / name
            if not common_file.exists():
                errors.append(f"src/common/{name}: missing shared source")
                continue
            text = common_file.read_text(encoding="utf-8")
            unresolved = False
            for token, key in tokens:
                if key not in cfg:
                    errors.append(
                        f"src/common/families.json: family {family} misses key {key}")
                    unresolved = True
                    continue
                text = text.replace(token, to_config_str(cfg[key]))
            if unresolved or "@@" in text:
                errors.append(
                    f"src/common/{name}: unresolved tokens for family {family}")
                continue
            target = ROOT / "src" / family / name
            if not target.exists():
                errors.append(f"{target}: missing generated shared script")
                continue
            if target.read_text(encoding="utf-8") != text:
                errors.append(
                    f"{target}: stale generated shared script; run `npm run build`")
        print(f"common: {family} shared scripts match families.json")


def check_ads_family():
    """Validate the single DNS-first ads plugin and its optional layers."""
    protected_path = ROOT / "src/ads/protected-roots.json"
    try:
        protected = set(json.loads(protected_path.read_text())["roots"])
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        errors.append(f"ads: cannot read {protected_path}: {exc}")
        protected = set()

    path = ROOT / ADS_PLUGIN
    if not path.exists():
        errors.append(f"{ADS_PLUGIN}: missing plugin")
        return
    data, sections = parse_plugin(path)
    meta = parse_meta(path)
    raw = path.read_text(encoding="utf-8")

    for key in ADS_META_KEYS:
        if key not in meta:
            errors.append(f"{ADS_PLUGIN}: missing #!{key} metadata")
    if meta.get("system") != "iOS,iPadOS,tvOS,macOS":
        errors.append(
            f"{ADS_PLUGIN}: #!system must be iOS,iPadOS,tvOS,macOS, "
            f"got {meta.get('system')!r}"
        )
    if "icon" in meta and not meta["icon"].startswith("https://"):
        errors.append(f"{ADS_PLUGIN}: #!icon must be an https URL")
    if sections not in (["General", "Rule", "Host"], ["General", "Rule", "IP Rewrite", "Host"]):
        errors.append(
            f"{ADS_PLUGIN}: sections {sections}, expected "
            "['General', 'Rule', 'Host'] or ['General', 'Rule', 'IP Rewrite', 'Host']"
        )

    if not (ROOT / "plugins/ads/README.md").exists():
        errors.append("ads: missing plugins/ads/README.md")

    for retired in ADS_RETIRED:
        if (ROOT / retired).exists():
            errors.append(f"{retired}: must not exist after the single-plugin merge")
    for retired in ADS_RETIRED:
        basename = retired.rsplit("/", 1)[-1]
        if basename in raw:
            errors.append(f"{ADS_PLUGIN}: must not reference retired {basename}")

    # [General] is limited to Loon's plugin whitelist. The ads plugin may only
    # append DNS/DoH servers; it must not look like it can set hijack/reject
    # modes that Loon ignores in plugins.
    general = data.get("General", [])
    general_map = {}
    for line in general:
        if "=" not in line:
            errors.append(f"{ADS_PLUGIN}: malformed [General] line: {line[:100]}")
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        general_map[key] = value
        if key not in ADS_GENERAL_KEYS:
            errors.append(f"{ADS_PLUGIN}: unsupported plugin [General] key: {key}")
    for key in ("hijack-dns", "domain-reject-mode", "dns-reject-mode", "disable-stun"):
        if key in general_map:
            errors.append(f"{ADS_PLUGIN}: plugin [General] cannot set {key}")
    if "dns-server" not in general_map:
        errors.append(f"{ADS_PLUGIN}: [General] missing dns-server")
    else:
        dns_values = [v.strip().lower() for v in general_map["dns-server"].split(",")]
        if "system" in dns_values:
            errors.append(f"{ADS_PLUGIN}: dns-server must not contain system")
    if "doh-server" not in general_map:
        errors.append(f"{ADS_PLUGIN}: [General] missing doh-server")
    else:
        for url in [v.strip() for v in general_map["doh-server"].split(",")]:
            if not re.match(r"^https://\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?/", url):
                errors.append(f"{ADS_PLUGIN}: doh-server must use an IP literal: {url}")
    if "doh3-server" in general_map:
        for url in [v.strip() for v in general_map["doh3-server"].split(",")]:
            if not re.match(r"^h3://\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?/", url):
                errors.append(f"{ADS_PLUGIN}: doh3-server must use an IP literal: {url}")

    # [Rule] is the HTTPDNS fallback. It must only block and must not smuggle
    # in an unsupported policy/parameter.
    rules = data.get("Rule", [])
    required_rules = (
        "DOMAIN-KEYWORD,httpdns,REJECT-DROP,extended-matching,pre-matching",
        "DOMAIN-KEYWORD,httpsdns,REJECT-DROP,extended-matching,pre-matching",
        "USER-AGENT,httpdns*,REJECT",
        "DEST-PORT,853,REJECT",
    )
    for required in required_rules:
        if required not in rules:
            errors.append(f"{ADS_PLUGIN}: [Rule] missing {required}")
    url_regexes = []
    for line in rules:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            errors.append(f"{ADS_PLUGIN}: malformed [Rule] line: {line[:100]}")
            continue
        if parts[0] == "FINAL":
            errors.append(f"{ADS_PLUGIN}: FINAL is not allowed in the ads plugin")
        elif parts[0] not in ADS_RULE_TYPES:
            errors.append(f"{ADS_PLUGIN}: unsupported [Rule] type: {parts[0]}")
        if not parts[2].startswith("REJECT"):
            errors.append(f"{ADS_PLUGIN}: [Rule] must reject: {line[:100]}")
        if parts[0] == "PROTOCOL" and parts[1] not in PROTOCOL_VALUES:
            errors.append(f"{ADS_PLUGIN}: unsupported PROTOCOL value: {parts[1]}")
        for param in parts[3:]:
            if param not in {"extended-matching", "pre-matching", "no-resolve"}:
                errors.append(f"{ADS_PLUGIN}: unsupported [Rule] parameter: {param}")
        if parts[0] == "URL-REGEX":
            try:
                url_regexes.append(re.compile(parts[1]))
            except re.error as exc:
                errors.append(f"{ADS_PLUGIN}: URL-REGEX compile failed: {exc}")

    # Exercise the IP-literal HTTPDNS fallback. This catches the common
    # Baidu/Tencent shapes (`/d?`, `/ss?`, `/vN/...`, `sign_...`) without
    # requiring network access or a Loon client.
    httpdns_url_samples = (
        "http://180.76.76.200/d?",
        "http://180.76.76.200/ss?",
        "http://180.76.76.200/v2/d?",
        "http://180.76.76.200/v2/resolve?",
        "http://[2400:3200::1]/resolve?",
        "http://api.weibo.cn/123/httpdns/config",
        "http://amdc.alipay.com/s?query",
    )
    for sample in httpdns_url_samples:
        if not any(rx.search(sample) for rx in url_regexes):
            errors.append(f"{ADS_PLUGIN}: HTTPDNS URL-REGEX misses {sample}")
    for sample in ("http://180.76.76.200/foo", "http://example.com/d?"):
        if any(rx.search(sample) for rx in url_regexes):
            errors.append(f"{ADS_PLUGIN}: HTTPDNS URL-REGEX overmatches {sample}")

    if "# IP-CIDR,203.107.1.0/24,REJECT,no-resolve,pre-matching" not in raw:
        errors.append(f"{ADS_PLUGIN}: optional HTTPDNS IP block must stay commented")
    # 2026 全网取证补的网关 IP 也必须保持默认注释（可选层纪律）。
    for marker in (
        "# IP-CIDR,203.119.238.240/32,REJECT,no-resolve,pre-matching",
        "# IP-CIDR,43.132.43.43/32,REJECT,no-resolve,pre-matching",
        "# IP-CIDR6,2401:b180:7001::31d/128,REJECT,no-resolve,pre-matching",
    ):
        if marker not in raw:
            errors.append(f"{ADS_PLUGIN}: optional HTTPDNS IP block missing: {marker}")
    # 186.76.76.200 不存在于任何官方文档（百度 VIP 只有 180.76.76.200），
    # 曾经是笔误，永久锁掉。只禁规则形态；注释里的说明文字允许。
    if re.search(r"#?\s*IP-CIDR,\s*186\.76\.76\.200", raw):
        errors.append(f"{ADS_PLUGIN}: typo IP 186.76.76.200 must stay removed")
    # 119.29.29.29 是公共普通 DNS，同时是本插件自己的 dns-server，绝不能拦。
    if "119.29.29.29/32" in raw or "119.29.29.29 = 127.0.0.1" in raw:
        errors.append(
            f"{ADS_PLUGIN}: must not block 119.29.29.29 (public resolver AND own dns-server)"
        )
    # PROTOCOL,STUN,REJECT 是可选层唯一非 IP 规则（Loon 3.1.7+ 协议规则），
    # README 与全功能清单按 28 条引用它；必须存在、恰好一行注释态、绝不能激活。
    stun_lines = [
        line
        for line in raw.splitlines()
        if line.strip() in ("PROTOCOL,STUN,REJECT", "# PROTOCOL,STUN,REJECT")
    ]
    if stun_lines != ["# PROTOCOL,STUN,REJECT"]:
        errors.append(
            f"{ADS_PLUGIN}: optional PROTOCOL STUN block must exist exactly once and stay commented"
        )

    # Build 1007+ [IP Rewrite] 可选块守卫：单 IPv4、drop 动作、不包含自身 119.29.29.29
    if "# 可选：[IP Rewrite]（Loon Build 1007+ 插件专属，TUN 阶段最快拦截）" not in raw:
        errors.append(f"{ADS_PLUGIN}: optional [IP Rewrite] block missing header")
    for ip_marker in (
        "# 203.119.238.240 = drop",
        "# 43.132.43.43 = drop",
        "# 180.76.76.200 = drop",
    ):
        if ip_marker not in raw:
            errors.append(f"{ADS_PLUGIN}: optional [IP Rewrite] marker missing: {ip_marker}")

    # [Host] is the core DNS layer.
    host_lines = data.get("Host", [])
    if len(host_lines) < 700:
        errors.append(
            f"{ADS_PLUGIN}: only {len(host_lines)} active Host rules, expected >= 700"
        )
    exact = set()
    wildcard = set()
    for line in host_lines:
        if not ADS_HOST_RE.match(line):
            errors.append(f"{ADS_PLUGIN}: malformed Host rule: {line[:100]}")
            continue
        left = line.split(" = ", 1)[0]
        if left.startswith("*."):
            base = left[2:]
            wildcard.add(base)
            if base in protected:
                errors.append(
                    f"{ADS_PLUGIN}: wildcard on protected shared root: {left} "
                    "(use an exact ad subdomain)"
                )
        else:
            exact.add(left)
            if left in protected:
                errors.append(
                    f"{ADS_PLUGIN}: blocked protected shared apex: {left} "
                    "(use an exact ad subdomain)"
                )

    for domain in ("ad.zijieapi.com", "ads.youtube.com", "gdt.qq.com"):
        if domain not in exact and domain not in wildcard:
            errors.append(f"{ADS_PLUGIN}: core sample missing: {domain}")
    for domain in ("doubleclick.net", "applovin.com", "pangle.io", "gdtimg.com"):
        if domain not in wildcard:
            errors.append(f"{ADS_PLUGIN}: core wildcard missing: *.{domain}")
    for domain in (
        "httpdns.aliyuncs.com",
        "httpdns.qq.com",
        "dns.weixin.qq.com",
        "resolver.msg.xiaomi.net",
    ):
        if domain not in exact:
            errors.append(f"{ADS_PLUGIN}: HTTPDNS sample missing: {domain}")
    # 公共 DoH 断言要感知通配覆盖——`=adguard-dns.com` 形态下
    # family/unfiltered 变体不在 exact 里，但被 *.'d 基域覆盖即算命中。
    def covered(domain: str) -> bool:
        if domain in exact:
            return True
        return any(domain.endswith("." + base) for base in wildcard)

    for domain in (
        "dns.google",
        "doh.pub",
        "cloudflare-dns.com",
        "dns.adguard-dns.com",
        "family.adguard-dns.com",
        "unfiltered.adguard-dns.com",
        "security.cloudflare-dns.com",
        "family.cloudflare-dns.com",
        "adblock.doh.mullvad.net",
        "sm2.doh.pub",
        "doh.dns.sb",
    ):
        if not covered(domain):
            errors.append(f"{ADS_PLUGIN}: public DoH sample missing: {domain}")

    # Attribution/analytics are intentionally opt-in comments. They must not
    # leak into the active Host set, or installing the core plugin would break
    # install attribution and app analytics by default.
    for domain in ("appsflyer.com", "google-analytics.com", "umeng.com"):
        if domain in exact or domain in wildcard:
            errors.append(f"{ADS_PLUGIN}: optional measurement domain is active: {domain}")
    for marker in (
        "# appsflyer.com = 127.0.0.1",
        "# google-analytics.com = 127.0.0.1",
        "# umeng.com = 127.0.0.1",
    ):
        if marker not in raw:
            errors.append(f"{ADS_PLUGIN}: optional measurement block missing: {marker}")

    # Explicitly excluded shared hosts must never become active by accident.
    for domain in ("is.snssdk.com", "graph.facebook.com", "branch.io"):
        if domain in exact or domain in wildcard:
            errors.append(f"{ADS_PLUGIN}: excluded shared host is active: {domain}")

    print(
        f"{ADS_PLUGIN}: host_rules={len(host_lines)} "
        f"exact={len(exact)} wildcard={len(wildcard)} "
        f"general={len(general)} rules={len(rules)}"
    )

    build = subprocess.run(
        [sys.executable, str(ROOT / "tools/build-ads.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        tail = (build.stderr or build.stdout).strip().splitlines()[-6:]
        errors.append(
            "ads: generated plugin is stale; run `python3 tools/build-ads.py`\n"
            + "\n".join("    " + line for line in tail)
        )
    else:
        print("ads: generated plugin matches src/ads/domains.json")


check_shared_scripts()
check_ads_family()
print(f"lint errors: {len(errors)}")
for err in errors:
    print(" -", err)
sys.exit(1 if errors else 0)
