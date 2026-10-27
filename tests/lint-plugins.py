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
    ("plugins/soda/soda.plugin", 5, 0, 2, 40, "soda"),
    ("plugins/douyin/douyin.plugin", 5, 0, 1, 11, "douyin"),
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
            "hideDouyinTab": 1,
            "blockSplashAd": 1,
            "debugLog": 22,
        },
        "selects": [
            ("statusNotify", '"notification","silent"'),
        ],
        # Generic 自检按钮必须拿到全部开关，结果页才能给出准确的摘要与冲突提醒。
        "status": [
            "rewardSafe", "splashClean", "cleanAds", "killRewardAds",
            "blockAdDomains", "blockSplashAd", "settingsClean",
            "hideDouyinEntry", "hideDouyinTab", "debugLog", "logTaskTitles",
            "dailyReminder", "reminderCron",
        ],
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
            "splash-v2": "https://ad.zijieapi.com/api/ad/v2/ack/splash/report",
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
            ("blockSplashAd", "false"),
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
            "blockSplashAd": 1,
            "debugLog": 2,
        },
        "selects": [
            ("statusNotify", '"notification","silent"'),
        ],
        "status": [
            "treasureMinimal", "cleanFeedAds", "killRewardAds", "cleanUpsell",
            "cleanActivity", "blockAdDomains", "blockSplashAd", "debugLog",
            "dailyReminder", "reminderCron",
        ],
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

# DOMAIN-WILDCARD（Loon 3.5.3(1008)+）广告子域通配层。
# 永久锁死模式集合：只允许由广告专用左标签锚定的 glob，避免误写 `*`、
# `*.com` 或 `ads*` 这类会扫到共享主域/正常域名的宽泛匹配。
ADS_WILDCARDS = (
    "ads.*",
    "ads-*",
    "adserver.*",
    "adserver-*",
    "adserve.*",
    "adserv.*",
    "adserv-*",
    "adserving.*",
    "adserving-*",
    "adservice.*",
    "adservices.*",
    "adsystem.*",
    "advertising.*",
    "advertising-*",
    "advert.*",
    "adverts.*",
    "advertiser.*",
    "adtech.*",
    "adtech-*",
    "adclick.*",
    "adnetwork.*",
    "adnetwork-*",
    "adx.*",
    "adx-*",
    "adtrack.*",
    "adtrack-*",
    "adunit.*",
    "bannerads.*",
    "sponsorads.*",
    "ad-exchange.*",
)
ADS_WILDCARD_HITS = {
    "ads.*": ("ads.example.com", "ads.a.b.example.com"),
    "ads-*": ("ads-tracker.example.com", "ads-1.example.net"),
    "adserver.*": ("adserver.example.com", "adserver.foo.example.net"),
    "adserver-*": ("adserver-eu.example.com",),
    "adserve.*": ("adserve.example.com",),
    "adserv.*": ("adserv.example.com",),
    "adserv-*": ("adserv-fra1.example.com",),
    "adserving.*": ("adserving.example.com",),
    "adserving-*": ("adserving-com.example.com",),
    "adservice.*": ("adservice.example.com",),
    "adservices.*": ("adservices.example.com",),
    "adsystem.*": ("adsystem.example.com",),
    "advertising.*": ("advertising.example.com",),
    "advertising-*": ("advertising-api.example.com", "advertising-cdn.example.net"),
    "advert.*": ("advert.example.com", "advert.a.example.net"),
    "adverts.*": ("adverts.example.com",),
    "advertiser.*": ("advertiser.example.com",),
    "adtech.*": ("adtech.example.com",),
    "adtech-*": ("adtech-prod.example.com",),
    "adclick.*": ("adclick.example.com",),
    "adnetwork.*": ("adnetwork.example.com",),
    "adnetwork-*": ("adnetwork-core.example.com",),
    "adx.*": ("adx.example.com",),
    "adx-*": ("adx-ads.example.com", "adx-api.example.net"),
    "adtrack.*": ("adtrack.example.com",),
    "adtrack-*": ("adtrack-php.example.com",),
    "adunit.*": ("adunit.example.com",),
    "bannerads.*": ("bannerads.example.com",),
    "sponsorads.*": ("sponsorads.example.com",),
    "ad-exchange.*": ("ad-exchange.example.com",),
}
ADS_WILDCARD_MUST_MISS = (
    "example.com",
    "com",
    "ads",
    "ad.example.com",
    "adsl.example.com",
    "adsp.example.com",
    "xads.example.com",
    "myads-tracker.example.com",
    "tracker.example.com",
    "advertisement.example.com",
    "advertise.example.com",
    "banner.example.com",
    "adunit2.example.com",
)
ADS_WILDCARD_MIN_BUILD = 1008


def ads_glob_regex(pattern):
    """Loon DOMAIN-WILDCARD glob semantics: '*' crosses dots, '?' one char."""
    return re.compile(
        "".join(
            ".*" if char == "*" else "." if char == "?" else re.escape(char)
            for char in pattern
        )
        + r"\Z"
    )

# 开屏请求拦截绑定的边界：只拦开屏素材/登记家族，绝不能碰激励广告与发奖。
SPLASH_MUST_HIT = (
    "https://ads5-normal-hl.zijieapi.com/api/ad/splash/luna/v15/",
    "https://ad.zijieapi.com/api/ad/splash/stock/",
    "https://ad.zijieapi.com/api/ad/v2/ack/splash/collect",
)
SPLASH_MUST_MISS = (
    "https://ad.zijieapi.com/api/ad/v1/inspire/",
    "https://ad.zijieapi.com/api/ad/v1/inspire_preload/",
    "https://ad.zijieapi.com/api/incentive/marketing/done/",
)

# ---------------------------------------------------------------------------
# 绑定矩阵（Loon 对同一响应只执行配置顺序里第一条命中的 Response Script）：
# 用真实 URL 样本把每条 request/response 绑定映射出来。每条绑定都必须至少被
# 一个样本命中——新增端点不补样本就失败；同一 URL 命中多条绑定时，只允许
# “同脚本同参数”（谁跑都拿到完整上下文）或下面显式论证过的组合。
# ---------------------------------------------------------------------------
BINDING_SAMPLES = {
    "soda": {
        "request": (
            "https://ad.zijieapi.com/api/ad/splash/stock/",
            "https://ad.zijieapi.com/api/ad/v1/inspire/",
            "https://foo.zijieapi.com/api/ad/v2/ack/splash/collect",
        ),
        "response": (
            "https://api.qishui.com/luna/advert/splash/brand/retrieve",
            "https://api.qishui.com/luna/advert/incentive/config",
            "https://api.qishui.com/luna/advert/incentive/retrieve",
            "https://api.qishui.com/luna/advert/incentive/done",
            "https://api.qishui.com/luna/advert/fallback/done/info",
            "https://api.qishui.com/luna/ads/config",
            "https://api.qishui.com/luna/ads/retrieve",
            "https://api.qishui.com/luna/ads/dsp/retrieve",
            "https://api.qishui.com/luna/ads/reward/receive",
            "https://api.qishui.com/luna/ads/reward/settle",
            "https://api.qishui.com/luna/feed/song-tab",
            "https://api.qishui.com/luna/commerce/upsells",
            "https://api.qishui.com/luna/commerce/validate_reward",
            "https://api.qishui.com/luna/commerce/v2/upsell?x=1",
            "https://api.qishui.com/luna/treasure/entrance/config",
            "https://api.qishui.com/luna/treasure/task/view",
            "https://api.qishui.com/luna/treasure/task/page",
            "https://api.qishui.com/luna/treasure/task/reward_ads/do_action",
            "https://api.qishui.com/luna/treasure/task/fallback/do_action",
            "https://api.qishui.com/luna/treasure/task/flip_card/do_action",
            "https://api.qishui.com/luna/treasure/task/guide/do_action",
            "https://api.qishui.com/luna/treasure/task/browse_mall/do_action",
            "https://api.qishui.com/luna/growth/activity_entrance",
            "https://api.qishui.com/luna/growth/activity/finish",
            "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
            "https://conf.qishui.com/service/settings/v3/?device_id=x",
        ),
    },
    "douyin": {
        "request": (
            "https://ad.zijieapi.com/api/ad/splash/stock/",
            "https://ad.zijieapi.com/api/ad/v1/inspire/",
            "https://foo.zijieapi.com/api/ad/v2/ack/splash/collect",
        ),
        "response": (
            "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
            "https://beta-luna.douyin.com/luna/ads/config",
            "https://beta-luna.douyin.com/luna/ads/retrieve",
            "https://beta-luna.douyin.com/luna/ads/dsp/retrieve",
            "https://beta-luna.douyin.com/luna/advert/incentive/config",
            "https://beta-luna.douyin.com/luna/advert/incentive/retrieve",
            "https://beta-luna.douyin.com/luna/advert/incentive/done",
            "https://beta-luna.douyin.com/luna/advert/fallback/done/info",
            "https://beta-luna.douyin.com/luna/commerce/v2/upsell",
            "https://beta-luna.douyin.com/luna/growth/music_festival/performance_details",
            "https://polaris.zijieapi.com/luckycat/activity/settings/v1/x",
            "https://ad.zijieapi.com/api/ad/v1/inspire/",
            "https://ad.zijieapi.com/api/incentive/marketing/done/",
        ),
    },
}

# 允许的“清理/隐藏 + 只读观测 + 打卡兜底”组合：功能上有意让清理优先，
# 被抢走的观测是诊断信息；settings 与 hide 绑定同脚本同参数，单独放行。
SHADOW_ALLOWED_PAIRS = {
    "soda": {
        frozenset(("sanitize.min.js", "reward-observe.min.js")),
        frozenset(("sanitize.min.js", "welfare-stamp.min.js")),
        frozenset(("reward-observe.min.js", "welfare-stamp.min.js")),
        frozenset(("block-domains.min.js", "splash-ad.min.js")),
    },
    "douyin": {
        frozenset(("treasure.min.js", "observe.min.js")),
        frozenset(("treasure.min.js", "welfare-stamp.min.js")),
        frozenset(("observe.min.js", "welfare-stamp.min.js")),
        frozenset(("clean.min.js", "observe.min.js")),
        frozenset(("block-domains.min.js", "splash-ad.min.js")),
    },
}

# ---------------------------------------------------------------------------
# 脚本安全边界（静态）：插件脚本只做净化/观测，不得发起网络请求、不得执行
# 动态代码，$notification 只允许出现在 status / daily-reminder。所有脚本
# 必须在结束时调用 $done() 释放 Loon 的 JS 资源。
# ---------------------------------------------------------------------------
SAFE_SCRIPT_FORBIDDEN = (
    ("$httpClient", re.compile(r"\$httpClient")),
    ("XMLHttpRequest", re.compile(r"\bXMLHttpRequest\b")),
    ("WebSocket", re.compile(r"\bWebSocket\b")),
    ("sendBeacon", re.compile(r"\bsendBeacon\b")),
    ("Function(", re.compile(r"\bFunction\s*\(")),
    ("eval(", re.compile(r"\beval\s*\(")),
    ("require(", re.compile(r"\brequire\s*\(")),
    ("fetch(", re.compile(r"\bfetch\s*\(")),
)
SAFE_DONE_RX = re.compile(r"\$done\s*\(")
SAFE_NOTIFY_RX = re.compile(r"\$notification\s*(?:\.|\[)\s*[\"']?post")
SAFE_NOTIFY_ALLOWED = {"status.js", "daily-reminder.js"}

errors = []
COMMON_DIR = ROOT / "src/common"
FAMILIES_FILE = COMMON_DIR / "families.json"

# ---------------------------------------------------------------------------
# 静态传输层（常开，无 [Argument] 开关）：
#   [Rule] 里每个 [MITM] 域都必须有一条 AND+PROTOCOL,QUIC 回退规则；
#   绝不允许全局 PROTOCOL,QUIC,REJECT（会伤视频/通话）。
# ---------------------------------------------------------------------------
QUIC_HOSTS = {
    "soda": (
        "api.qishui.com",
        "conf.qishui.com",
        "ad.zijieapi.com",
        "lianmengapi.snssdk.com",
        "ads5-normal-hl.zijieapi.com",
        "zlink.ugsdk.cn",
        "praisewindow.ugsdk.cn",
        "beta-luna.douyin.com",
    ),
    "douyin": (
        "beta-luna.douyin.com",
        "polaris.zijieapi.com",
        "ad.zijieapi.com",
        "lianmengapi.snssdk.com",
        "ads5-normal-hl.zijieapi.com",
        "zlink.ugsdk.cn",
        "praisewindow.ugsdk.cn",
    ),
}

# 跨层短路的显式允许清单：(rewrite 片段, 脚本名)。为空 = 一条都不许。
CROSS_LAYER_ALLOWED = set()

# 只有“直接终止请求”的复写才会遮蔽后续脚本；改 header / 改 URL 不会。
REWRITE_TERMINAL_RX = re.compile(r"\breject(?:_\w+)?\s*\(|\bredirect\s*\(|\s302\s|\s307\s")
DOMAIN_BLOCK_KINDS = ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-WILDCARD")


def host_of(url):
    m = re.match(r"^https?://([^/:?#]+)", url)
    return m.group(1).lower() if m else ""


def active_domain_blocks(rule_lines):
    """只取“无条件整域拒绝”的静态规则；AND+PROTOCOL 这类协议限定不算。"""
    out = []
    for line in rule_lines:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3 or parts[0] not in DOMAIN_BLOCK_KINDS:
            continue
        if not parts[2].startswith("REJECT"):
            continue
        out.append((parts[0], parts[1]))
    return out


def domain_hit(kind, pattern, host):
    pattern = pattern.lower()
    if kind == "DOMAIN":
        return host == pattern
    if kind == "DOMAIN-SUFFIX":
        return host == pattern or host.endswith("." + pattern)
    if kind == "DOMAIN-WILDCARD":
        return ads_glob_regex(pattern).fullmatch(host) is not None
    return False


def rewrite_entries(rewrite_lines):
    """把 [Rewrite] 行拆成 {stage, regex, terminal}，兼容新旧两套语法。"""
    out = []
    for line in rewrite_lines:
        stage = "response" if line.startswith("response if") else "request"
        rx = regex_literal(line)
        if not rx:
            # 旧语法：`^https?://... reject_dict(200)` / `... header-del X`
            m = re.match(r"^(\S+)\s+\S", line)
            rx = m.group(1) if m and m.group(1).startswith("^") else None
        if not rx:
            continue
        try:
            compiled = re.compile(rx)
        except re.error:
            continue
        out.append(
            {
                "stage": stage,
                "rx": compiled,
                "terminal": bool(REWRITE_TERMINAL_RX.search(line)),
                "line": line,
            }
        )
    return out


def check_cross_layer(fp, family, data, scripts, samples):
    """[Rule] / [Rewrite] / [Script] 三层用同一批真实 URL 交叉验证。

    只锁“会静默吃掉脚本”的组合：静态整域拒绝、终止型复写。
    传输层优化（删 Accept-Encoding）是互补的，不算短路。
    """
    block = active_domain_blocks(data.get("Rule", []))
    rewrites = rewrite_entries(data.get("Rewrite", []))
    entries = [binding_entry(line) for line in scripts]
    for entry in entries:
        try:
            entry["compiled"] = re.compile(entry["rx"]) if entry["rx"] else None
        except re.error:
            entry["compiled"] = None

    problems = 0
    for url in samples:
        host = host_of(url)
        for kind, pattern in block:
            if domain_hit(kind, pattern, host):
                problems += 1
                errors.append(
                    f"{fp}: 跨层短路：静态 {kind},{pattern},REJECT 命中 {url}，"
                    f"该 URL 的脚本永远不会执行"
                )
        for rw in rewrites:
            if not rw["terminal"] or not rw["rx"].match(url):
                continue
            for entry in entries:
                if not entry["compiled"] or not entry["compiled"].match(url):
                    continue
                # request 阶段终止 = 请求不出网，response 脚本同样收不到；
                # response 阶段终止只遮蔽同阶段脚本。
                if rw["stage"] == "response" and entry["stage"] != "response":
                    continue
                if (rw["line"][:60], entry["script"]) in CROSS_LAYER_ALLOWED:
                    continue
                problems += 1
                errors.append(
                    f"{fp}: 跨层短路：{rw['stage']} 复写终止 {url}，"
                    f"遮蔽 {entry['script']}(enable={entry['enable']})"
                )
    print(
        f"  {family} cross-layer: {len(samples)} url / "
        f"{len(block)} static block / {len(rewrites)} rewrite / {problems} shadow(s)"
    )


def check_static_layer(fp, family, data, mitm_text):
    """静态传输层：QUIC 回退齐全、无全局 QUIC 拒绝、免压缩规则齐全。"""
    rules = data.get("Rule", [])
    quic = {
        line
        for line in rules
        if line.startswith("AND,") and "PROTOCOL,QUIC" in line
    }
    expected = {
        f"AND,((DOMAIN-SUFFIX,{host}),(PROTOCOL,QUIC)),REJECT"
        for host in QUIC_HOSTS[family]
    }
    if quic != expected:
        errors.append(
            f"{fp}: QUIC fallback set {sorted(quic)}, expected {sorted(expected)}"
        )
    for line in rules:
        if line.startswith("PROTOCOL,QUIC,"):
            errors.append(
                f"{fp}: global PROTOCOL,QUIC,REJECT is forbidden (breaks video/calls)"
            )
    for host in QUIC_HOSTS[family]:
        if host not in mitm_text:
            errors.append(f"{fp}: QUIC fallback host {host} is not in [MITM]")

    # 免压缩（request.header.del Accept-Encoding）经真机体积核算后放弃：
    # upsell 类响应 gzip 后 183~191 KB，去压缩会让单次传输膨胀 5~10 倍。
    # 这里反向锁死：不允许再悄悄加回来，除非先改 docs/loon-native-first.md 的结论。
    rewrite_text = "\n".join(data.get("Rewrite", []))
    if "Accept-Encoding" in rewrite_text:
        errors.append(
            f"{fp}: no-compress rewrite was rejected on measured payload size; "
            "see docs/loon-native-first.md (E2)"
        )

    if "h2 = true" not in mitm_text:
        errors.append(f"{fp}: [MITM] must enable h2 = true for HTTP/2 visibility")

    hostname_line = next(
        (line for line in mitm_text.splitlines() if line.startswith("hostname")), "")
    mitm_hosts = [
        host.strip()
        for host in hostname_line.split("=", 1)[-1].replace("%APPEND%", "").split(",")
        if host.strip()
    ]

    print(
        f"  {family} static layer: quic={len(quic)} mitm_hosts={len(mitm_hosts)} h2=on"
    )


def check_switch_labels():
    """[Argument] 开关名必须与 status.js 的 SWITCH_LABELS 双向一致。

    这类漂移不会报错，只会让状态看板少显示/多显示一行。
    """
    status_src = COMMON_DIR / "status.js"
    text = status_src.read_text(encoding="utf-8") if status_src.exists() else ""
    m = re.search(r"SWITCH_LABELS\s*=\s*\[(.*?)\];", text, re.S)
    if not m:
        errors.append("src/common/status.js: cannot find SWITCH_LABELS")
        return
    labels = set(re.findall(r'\[\s*"([A-Za-z_]\w*)"\s*,', m.group(1)))

    declared = set()
    for fp, _sections, _rules, _rewrites, _scripts, _family in PLUGINS:
        path = ROOT / fp
        if not path.exists():
            continue
        data, _ = parse_plugin(path)
        for line in data.get("Argument", []):
            arg = re.match(r"^([A-Za-z_]\w*)\s*=\s*(switch|select|input)", line)
            if not arg:
                continue
            if arg.group(2) != "switch":
                continue
            declared.add(arg.group(1))

    missing = sorted(declared - labels)
    stale = sorted(labels - declared)
    if missing:
        errors.append(f"status.js SWITCH_LABELS missing switches: {missing}")
    if stale:
        errors.append(f"status.js SWITCH_LABELS has unknown switches: {stale}")
    print(
        f"switch labels: {len(labels)} labels / {len(declared)} declared switches"
    )


def check_quic_count():
    """families.json 的 quicCount 必须等于插件里真实的 QUIC 回退条数。"""
    fam = load_families()
    if not fam:
        return
    for family, cfg in (fam.get("families") or {}).items():
        want = QUIC_HOSTS.get(family)
        if want is None:
            errors.append(f"src/common/families.json: family {family} has no QUIC_HOSTS spec")
            continue
        got = cfg.get("quicCount")
        if got != len(want):
            errors.append(
                f"src/common/families.json: {family}.quicCount={got}, expected {len(want)}"
            )
    print("static layer: families.json quicCount matches plugin rules")


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
        m = re.match(r"^\[([A-Za-z][A-Za-z ]*)\]$", s)
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


def binding_entry(line):
    stage = "request" if line.startswith("request if") else "response"
    rx_text = regex_literal(line)
    m_script = re.search(r'then script\("([^"]+)"', line)
    m_args = re.search(r'script\("[^"]+",\s*\{([^}]*)\}', line)
    m_enable = re.search(r"enable=\$\{([A-Za-z_]\w*)\}", line)
    script = m_script.group(1).rsplit("/", 1)[-1] if m_script else "?"
    return {
        "line": line,
        "stage": stage,
        "rx": rx_text,
        "script": script,
        "args": tuple(sorted(re.findall(r"\$\{([^}]+)\}", m_args.group(1)))) if m_args else (),
        "enable": m_enable.group(1) if m_enable else "?",
    }


def shadow_pair_allowed(family, a, b):
    """同脚本同参数 = 等价重复（谁先命中都拿到完整上下文）；其余只放行白名单。"""
    if a["script"] == b["script"] and a["args"] == b["args"]:
        return True
    return frozenset((a["script"], b["script"])) in SHADOW_ALLOWED_PAIRS.get(family, set())


def check_binding_matrix(fp, family, scripts_lines):
    samples = BINDING_SAMPLES.get(family)
    if not samples:
        errors.append(f"{fp}: missing BINDING_SAMPLES for {family}")
        return
    entries = [binding_entry(line) for line in scripts_lines]
    for entry in entries:
        try:
            entry["compiled"] = re.compile(entry["rx"]) if entry["rx"] else None
        except re.error as exc:
            errors.append(f"{fp}: binding matrix regex: {exc}")
            entry["compiled"] = None
    for stage in ("request", "response"):
        stage_entries = [e for e in entries if e["stage"] == stage and e["compiled"]]
        sample_list = samples.get(stage, ())
        if not sample_list:
            errors.append(f"{fp}: binding matrix needs {stage} URL samples")
            continue
        overlaps = 0
        for entry in stage_entries:
            if not any(entry["compiled"].match(url) for url in sample_list):
                errors.append(
                    f"{fp}: no {stage} sample covers binding "
                    f"{entry['script']} enable={entry['enable']}: {entry['line'][:90]}"
                )
        for url in sample_list:
            hits = [e for e in stage_entries if e["compiled"].match(url)]
            for i in range(len(hits)):
                for j in range(i + 1, len(hits)):
                    if shadow_pair_allowed(family, hits[i], hits[j]):
                        continue
                    overlaps += 1
                    errors.append(
                        f"{fp}: {stage} bindings shadow on {url}: "
                        f"{hits[i]['script']}(enable={hits[i]['enable']}) vs "
                        f"{hits[j]['script']}(enable={hits[j]['enable']})"
                    )
        print(
            f"  {family} binding matrix: {stage}={len(stage_entries)} bindings / "
            f"{len(sample_list)} samples / {overlaps} disallowed overlap(s)"
        )


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
        if re.search(r"reject(?:_(?:dict|array|img|video))?\(", l) or "reject-" in l
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
        if "report" in line and "reject_dict(200)" not in line:
            errors.append(
                f"{fp}: report endpoint must use reject_dict(200) "
                f"(JSON Content-Type, empty object): {line[:100]}"
            )

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

    # 部署目录只允许出现被 [Script] 绑定的脚本：删绑定/改脚本名后残留的
    # 孤儿 .min.js 仍可通过 raw 直链访问，属于无主代码面。
    deployed = {p.name for p in (path.parent / "scripts").glob("*.min.js")}
    referenced = set()
    for line in data.get("Script", []):
        m_ref = re.search(r'then script\("([^"]+)"', line)
        if m_ref:
            referenced.add(m_ref.group(1).rsplit("/", 1)[-1])
    for name in sorted(deployed - referenced):
        errors.append(f"{fp}: deployed script referenced by no binding: {name}")
    print(f"  scripts deployed={len(deployed)} referenced={len(referenced)}")

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
    for name, candidates in spec.get("selects", []):
        if f"{name} = select,{candidates}" not in arg_text:
            errors.append(
                f"{fp}: missing or wrong Argument select {name} "
                f"(expected candidates {candidates})"
            )

    generic_status = [
        line for line in data.get("Script", [])
        if line.startswith("generic") and "status.min.js" in line
    ]
    if not generic_status:
        errors.append(f"{fp}: missing generic status.min.js binding")
    else:
        status_line = generic_status[0]
        for name in ["statusNotify"] + spec.get("status", []):
            if "${" + name + "}" not in status_line:
                errors.append(
                    f"{fp}: generic status.min.js binding missing ${{{name}}}"
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

    # 静态层只允许 AND+PROTOCOL 这种协议限定规则；无条件整域 REJECT 会被
    # 上面的 counts 断言挡下（rules 列表只数 DOMAIN, 开头），
    # 真正的“是否短路脚本”交给 check_cross_layer 语义判断。

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

    # ---- 开屏请求拦截：绑定必须命中 splash 家族，且绝不命中激励/发奖 ----
    splash_lines = [line for line in scripts if "splash-ad.min.js" in line]
    if len(splash_lines) != 1:
        errors.append(
            f"{fp}: expected exactly one splash-ad.min.js binding, got {len(splash_lines)}"
        )
    for line in splash_lines:
        rx = regex_literal(line)
        try:
            splash_rx = re.compile(rx) if rx else None
        except re.error as exc:
            errors.append(f"{fp}: splash regex: {exc}")
            splash_rx = None
        if splash_rx is None:
            errors.append(f"{fp}: splash binding without a valid url regex: {line[:100]}")
            continue
        for url in SPLASH_MUST_HIT:
            if not splash_rx.match(url):
                errors.append(f"{fp}: splash binding misses {url}")
        for url in SPLASH_MUST_MISS:
            if splash_rx.match(url):
                errors.append(f"{fp}: splash binding must not block {url}")
    print(
        f"  {family} splash binding: {len(SPLASH_MUST_HIT)} hit / "
        f"{len(SPLASH_MUST_MISS)} miss checks, shared src/common/splash-ad.js"
    )

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

    check_binding_matrix(fp, family, scripts)
    check_static_layer(fp, family, data, mitm)
    cross_samples = list(spec["samples"].values())
    for stage_urls in BINDING_SAMPLES.get(family, {}).values():
        cross_samples.extend(stage_urls)
    check_cross_layer(
        fp, family, data, scripts, list(dict.fromkeys(cross_samples))
    )


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


def check_script_safety():
    """部署脚本与源码的静态安全门禁（网络/动态代码/通知/$done）。"""
    sources = sorted((ROOT / "src").glob("*/*.js"))
    dists = sorted((ROOT / "plugins").glob("*/scripts/*.min.js"))
    if not sources:
        errors.append("script safety: no source scripts found")
        return
    if not dists:
        errors.append("script safety: no dist scripts found")
        return
    problems = 0
    for path in sources + dists:
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not SAFE_DONE_RX.search(text):
            errors.append(f"{rel}: script never calls $done()")
            problems += 1
        for label, rx in SAFE_SCRIPT_FORBIDDEN:
            if rx.search(text):
                errors.append(f"{rel}: forbidden network/eval API: {label}")
                problems += 1
        source_name = path.name.replace(".min.js", ".js")
        if SAFE_NOTIFY_RX.search(text) and source_name not in SAFE_NOTIFY_ALLOWED:
            errors.append(
                f"{rel}: $notification.post is only allowed in "
                "status.js / daily-reminder.js"
            )
            problems += 1
    print(
        f"script safety: {len(sources)} sources / {len(dists)} dist scripts / "
        f"{problems} problem(s)"
    )


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

    # DOMAIN-WILDCARD 广告子域层：要求 Loon 3.5.3(1008)+，模式集合永久锁定，
    # 且每条 glob 都不能命中保护名单；同时用正/负样本锁定 glob 语义
    # （'*' 跨点、不匹配左标签不同段、不匹配共享主域本身）。
    wildcard_rules = [
        [part.strip() for part in line.split(",")]
        for line in rules
        if line.split(",", 1)[0].strip() == "DOMAIN-WILDCARD"
    ]
    wildcard_patterns = [parts[1] for parts in wildcard_rules if len(parts) > 2]
    if tuple(wildcard_patterns) != ADS_WILDCARDS:
        errors.append(
            f"{ADS_PLUGIN}: DOMAIN-WILDCARD set {wildcard_patterns}, "
            f"expected {list(ADS_WILDCARDS)}"
        )
    if len(set(wildcard_patterns)) != len(wildcard_patterns):
        errors.append(f"{ADS_PLUGIN}: duplicate DOMAIN-WILDCARD rule")
    if "# DOMAIN-WILDCARD," in raw:
        errors.append(f"{ADS_PLUGIN}: DOMAIN-WILDCARD rules must stay active")
    loon_version = meta.get("loon_version", "")
    loon_build = re.search(r"\((\d+)\)", loon_version)
    if not loon_build or int(loon_build.group(1)) < ADS_WILDCARD_MIN_BUILD:
        errors.append(
            f"{ADS_PLUGIN}: #!loon_version={loon_version!r} must be "
            f"{ADS_WILDCARD_MIN_BUILD}+ for DOMAIN-WILDCARD"
        )
    for parts in wildcard_rules:
        if len(parts) != 4 or parts[2] != "REJECT" or parts[3] != "pre-matching":
            errors.append(
                f"{ADS_PLUGIN}: DOMAIN-WILDCARD must be "
                f"DOMAIN-WILDCARD,<glob>,REJECT,pre-matching: {','.join(parts)}"
            )
    glob_regexes = {
        pattern: ads_glob_regex(pattern) for pattern in set(wildcard_patterns)
    }
    for pattern, regex in glob_regexes.items():
        for sample in ADS_WILDCARD_HITS.get(pattern, ()):
            if not regex.fullmatch(sample):
                errors.append(
                    f"{ADS_PLUGIN}: DOMAIN-WILDCARD {pattern} misses {sample}"
                )
        for root in protected:
            if regex.fullmatch(root):
                errors.append(
                    f"{ADS_PLUGIN}: DOMAIN-WILDCARD {pattern} matches protected root {root}"
                )
    for sample in ADS_WILDCARD_MUST_MISS:
        for pattern, regex in glob_regexes.items():
            if regex.fullmatch(sample):
                errors.append(
                    f"{ADS_PLUGIN}: DOMAIN-WILDCARD {pattern} overmatches {sample}"
                )

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
    if len(host_lines) < 1100:
        errors.append(
            f"{ADS_PLUGIN}: only {len(host_lines)} active Host rules, expected >= 1100"
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
    # 2026-10-27 审计补的高置信广告/测量域，防止后续整理时被误删。
    for domain in (
        "advertnative.com",
        "ntvk1.ru",
        "lentainform.com",
        "valueclickmedia.com",
        "medleyads.com",
        "bluecava.com",
        "voicefive.com",
        "events.brightline.tv",
    ):
        if domain not in exact and domain not in wildcard:
            errors.append(f"{ADS_PLUGIN}: audited ad domain missing: {domain}")
    # 公共加密 DNS 防绕过入口（含 DoT 域名兜底）。
    for domain in (
        "doh.applied-privacy.net",
        "doh.libredns.gr",
        "dns.controld.com",
        "doh.controld.com",
        "doh.ffmuc.net",
        "1dot1dot1dot1.cloudflare-dns.com",
        "dot.quad9.net",
        "dot.mullvad.net",
    ):
        if domain not in exact and domain not in wildcard:
            errors.append(f"{ADS_PLUGIN}: public encrypted-DNS entry missing: {domain}")
    # 默认注释的统计组也要有这几条真实补漏（保持 disabled，不能激活）。
    for marker in (
        "# cetrk.com = 127.0.0.1",
        "# wizaly.com = 127.0.0.1",
        "# stat.pl = 127.0.0.1",
        "# soicos.com = 127.0.0.1",
        "# stats.wp.com = 127.0.0.1",
        "# nr-data.net = 127.0.0.1",
    ):
        if marker not in raw:
            errors.append(f"{ADS_PLUGIN}: optional analytics marker missing: {marker}")
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
    # ad.abchina.com 经 EasyList China / AdRules 实证承载农行认证/核心脚本，绝不能拦截。
    for domain in ("is.snssdk.com", "graph.facebook.com", "branch.io", "ad.abchina.com"):
        if domain in exact or domain in wildcard:
            errors.append(f"{ADS_PLUGIN}: excluded shared host is active: {domain}")

    # 中国六大行精准广告专域守卫（工行、建行、中行、交行、邮储）
    for domain in (
        "adv.ccb.com",
        "ad.icbc.com.cn",
        "ad.boc.cn",
        "jf365.boc.cn",
        "ad.bankcomm.com",
        "ad.psbc.com",
    ):
        if domain not in exact:
            errors.append(f"{ADS_PLUGIN}: bank ad domain missing: {domain}")

    print(
        f"{ADS_PLUGIN}: host_rules={len(host_lines)} "
        f"exact={len(exact)} wildcard={len(wildcard)} "
        f"general={len(general)} rules={len(rules)} "
        f"domain_wildcards={len(wildcard_rules)}"
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
check_switch_labels()
check_quic_count()
check_script_safety()
check_ads_family()
print(f"lint errors: {len(errors)}")
for err in errors:
    print(" -", err)
sys.exit(1 if errors else 0)
