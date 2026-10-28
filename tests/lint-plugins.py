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
        "mitm": [
            "api.qishui.com",
            "conf.qishui.com",
            "ad.zijieapi.com",
            "lianmengapi.snssdk.com",
            "ads?-normal*.zijieapi.com",
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
        "mitm": [
            "beta-luna.douyin.com",
            "polaris.zijieapi.com",
            "ad.zijieapi.com",
            "lianmengapi.snssdk.com",
            "ads?-normal*.zijieapi.com",
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
    "openUrl",
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

# Loon 规则行只有 `no-resolve` 一个有文档依据的参数（且只用于 IP 类规则）。
# `pre-matching` / `extended-matching` 是 **Surge** 参数：Loon 里对应的行为
# （DNS 阶段拒绝、SNI 辅助匹配）默认开启，没有规则级开关；`domain-reject-mode`
# 属于主配置 `[General]`，插件无法声明。任何规则行出现这两个词都按错误处理，
# 因为它们要么被静默忽略（写了白写），要么让整条规则解析失败（写了更糟）。
ADS_RULE_PARAMS = {"no-resolve"}
SURGE_ONLY_RULE_PARAMS = {"pre-matching", "extended-matching", "no-resolve-sni"}

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
# 当前 App Store 正式版 = Loon 3.5.2(996)；TestFlight 才是 3.5.3(1008-1011)。
# 任何插件的 #!loon_version 都不得高于正式版 build，否则真实用户无法导入。
ADS_APPSTORE_STABLE_BUILD = 996

# 数字分片家族层（第二层 DOMAIN-WILDCARD）：Loon 3.5.3(1008) 起支持 `[...]`
# 字符类，官方示例含 node[0-9].example.com。这一层只允许 `[0-9]`——数字类
# 不会把匹配扩散到别的品牌主机，`[a-z]` / `[!0-9]` 会，所以不放开。
# 每条 glob 必须覆盖 2 个以上 [Host] 已枚举的同族主机，杜绝「凭想象造家族」。
ADS_FAMILY_WILDCARDS = (
    "ads[0-9]-normal*.zijieapi.com",
    "p[0-9]-ad-sign.byteimg.com",
    "v[0-9]-ad.video.yximgs.com",
    "pangolin-sdk-toutiao[0-9].com",
    "ads[0-9].msn.com",
    "ads[0-9]-adnow.com",
    "ads-splash-i[0-9].xhscdn.com",
    "ads-splash-v[0-9].xhscdn.com",
    "pg-ad-b[0-9].ws.126.net",
    "dns[0-9]*.quad9.net",
    "dns[0-9]*.nextdns.io",
)
# 每条家族 glob 至少要覆盖下面这些「已经在 [Host] 里」的主机。
ADS_FAMILY_COVERS = {
    "ads[0-9]-normal*.zijieapi.com": (
        "ads3-normal.zijieapi.com",
        "ads5-normal.zijieapi.com",
        "ads3-normal-hl.zijieapi.com",
        "ads5-normal-hl.zijieapi.com",
        "ads3-normal-lf.zijieapi.com",
        "ads3-normal-lq.zijieapi.com",
        "ads3-normal-xh.zijieapi.com",
        "ads5-normal-xh.zijieapi.com",
    ),
    "p[0-9]-ad-sign.byteimg.com": (
        "p3-ad-sign.byteimg.com",
        "p6-ad-sign.byteimg.com",
        "p9-ad-sign.byteimg.com",
    ),
    "v[0-9]-ad.video.yximgs.com": (
        "v1-ad.video.yximgs.com",
        "v2-ad.video.yximgs.com",
        "v3-ad.video.yximgs.com",
    ),
    "pangolin-sdk-toutiao[0-9].com": (
        "pangolin-sdk-toutiao1.com",
        "pangolin-sdk-toutiao2.com",
        "pangolin-sdk-toutiao5.com",
    ),
    "ads[0-9].msn.com": ("ads1.msn.com", "ads2.msn.com"),
    "ads[0-9]-adnow.com": (
        "ads1-adnow.com",
        "ads3-adnow.com",
        "ads5-adnow.com",
    ),
    "ads-splash-i[0-9].xhscdn.com": (
        "ads-splash-i1.xhscdn.com",
        "ads-splash-i2.xhscdn.com",
    ),
    "ads-splash-v[0-9].xhscdn.com": (
        "ads-splash-v1.xhscdn.com",
        "ads-splash-v2.xhscdn.com",
    ),
    "pg-ad-b[0-9].ws.126.net": (
        "pg-ad-b1.ws.126.net",
        "pg-ad-b2.ws.126.net",
    ),
    "dns[0-9]*.quad9.net": (
        "dns9.quad9.net",
        "dns10.quad9.net",
        "dns11.quad9.net",
        "dns12.quad9.net",
    ),
    "dns[0-9]*.nextdns.io": (
        "dns1.nextdns.io",
        "dns2.nextdns.io",
        "dns3.nextdns.io",
    ),
}
# 字符类必须「恰好一位数字」时才不多吃：这些样本全部不能命中。
ADS_FAMILY_MUST_MISS = (
    "ads-normal-hl.zijieapi.com",
    "adsxx-normal-hl.zijieapi.com",
    "ads10-normal-hl.zijieapi.com",
    "ads3-normal-hl.zijieapi.com.evil.example",
    "p-ad-sign.byteimg.com",
    "dns.quad9.net",
    "ads1.msn.com.evil.example",
)


def ads_glob_regex(pattern):
    """Loon DOMAIN-WILDCARD glob semantics: '*' crosses dots, '?' one char,
    and `[0-9]` is a single-digit character class."""
    parts = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "[":
            end = pattern.find("]", index + 1)
            if end == -1:
                raise ValueError(f"unterminated class in {pattern!r}")
            body = pattern[index + 1 : end]
            if body != "0-9":
                raise ValueError(f"unsupported class [{body}] in {pattern!r}")
            parts.append("[0-9]")
            index = end + 1
            continue
        parts.append(".*" if char == "*" else "." if char == "?" else re.escape(char))
        index += 1
    return re.compile("".join(parts) + r"\Z")

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

# 官方 Script API 5.3：`$persistentStore.remove()` **不接受参数**，语义是
# 「清空通过脚本存储 API 保存的全部数据」。传 key 进去不会只删那一项——
# 曾经用它清「广告开始时间」，结果每量一次时长就把打卡状态、统计、每日提醒
# 一起抹掉，而且没有任何报错。删单个键只能写 `write(undefined, key)`（5.1）。
SAFE_STORE_WIPE_RX = re.compile(r"\$persistentStore\s*\.\s*remove\s*\(")

# 上面这条要在「去掉注释」的文本上匹配：解释这条规则的注释本身就会写出
# `$persistentStore.remove()`，否则守卫会把自己判违规。
SAFE_COMMENT_RX = re.compile(r"/\*.*?\*/|^\s*//.*$", re.S | re.M)

# 会解析响应体的脚本：只有 gzip 可解（$utils.ungzip），其余编码必须在诊断里点名
ENCODING_GUARD_SCRIPTS = (
    "src/soda/sanitize.js",
    "src/soda/settings.js",
    "src/soda/reward-observe.js",
    "src/douyin/clean.js",
    "src/douyin/treasure.js",
    "src/douyin/observe.js",
)
ENCODING_BRANCH_MARKERS = (
    "skip=not-json",
    "skip=json-parse",
    "non-JSON len=",
    "JSON parse failed len=",
)

errors = []
COMMON_DIR = ROOT / "src/common"
FAMILIES_FILE = COMMON_DIR / "families.json"

# ---------------------------------------------------------------------------
# 静态传输层（常开，无 [Argument] 开关）：
#   [Rule] 里每个 [MITM] 域都必须有一条 AND+PROTOCOL,QUIC 回退规则；
#   绝不允许全局 PROTOCOL,QUIC,REJECT（会伤视频/通话）。
# ---------------------------------------------------------------------------
# Pangle 分片族：服务端按地区/线路下发 ads3|ads5 × normal|normal-hl|normal-lf|
# normal-lq|normal-xh，逐个列出（DOMAIN-SUFFIX 不吃通配），由 [MITM] 的
# ads?-normal*.zijieapi.com 一条覆盖全族。
PANGLE_SHARDS = (
    "ads3-normal.zijieapi.com",
    "ads5-normal.zijieapi.com",
    "ads3-normal-hl.zijieapi.com",
    "ads5-normal-hl.zijieapi.com",
    "ads3-normal-lf.zijieapi.com",
    "ads5-normal-lf.zijieapi.com",
    "ads3-normal-lq.zijieapi.com",
    "ads5-normal-lq.zijieapi.com",
    "ads3-normal-xh.zijieapi.com",
    "ads5-normal-xh.zijieapi.com",
)
# [MITM] 里覆盖分片族的通配（与 block-domains.js 的 BLOCKED_HOSTS 同字符串）。
PANGLE_MITM_GLOB = "ads?-normal*.zijieapi.com"

# 拦截名单的正/反样本：名单里出现 glob 后不再做字面集合比对，改验行为。
BLOCK_HOST_SAMPLES = (
    "https://ad.zijieapi.com/api/ad/v1/inspire/",
    "https://lianmengapi.snssdk.com/api/x",
    "https://ads3-normal-hl.zijieapi.com/api/ad/splash/luna/v15/",
    "https://ads5-normal.zijieapi.com/api/x",
    "https://ads3-normal-xh.zijieapi.com/api/x",
    "https://zlink.ugsdk.cn/a",
    "https://praisewindow.ugsdk.cn/a",
)
BLOCK_HOST_MUST_MISS = (
    "https://ads-normal-hl.zijieapi.com/api/x",
    "https://ads3-normal-hl.zijieapi.com.evil.example/api/x",
    "https://notad.zijieapi.com/api/x",
    "https://zzlink.ugsdk.cn/a",
)

QUIC_HOSTS = {
    "soda": (
        "api.qishui.com",
        "conf.qishui.com",
        "ad.zijieapi.com",
        "lianmengapi.snssdk.com",
        "zlink.ugsdk.cn",
        "praisewindow.ugsdk.cn",
        "beta-luna.douyin.com",
    )
    + PANGLE_SHARDS,
    "douyin": (
        "beta-luna.douyin.com",
        "polaris.zijieapi.com",
        "ad.zijieapi.com",
        "lianmengapi.snssdk.com",
        "zlink.ugsdk.cn",
        "praisewindow.ugsdk.cn",
    )
    + PANGLE_SHARDS,
}

# 跨层短路的显式允许清单：(rewrite 片段, 脚本名)。为空 = 一条都不许。
CROSS_LAYER_ALLOWED = set()

# 只有“直接终止请求”的复写才会遮蔽后续脚本；改 header / 改 URL 不会。
REWRITE_TERMINAL_RX = re.compile(r"\breject(?:_\w+)?\s*\(|\bredirect\s*\(|\s302\s|\s307\s")
# 原生 Body 改写（body.mock / body.replace / json.*）：文档明确「Response Body
# Rewrite 命中时，Response Script 不执行」「Request Body Rewrite 或 Mock 命中时，
# Request Script 不执行」。也就是说它和脚本是二选一，不是叠加。
REWRITE_BODY_RX = re.compile(
    r"\b(?:request|response)\.(?:body\.(?:mock|replace)|json\.(?:add|delete|replace|jq))(?:_file)?\s*\("
)
DOMAIN_BLOCK_KINDS = ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-WILDCARD")
# 唯一允许出现在 [Rewrite] 里的 Accept-Encoding 写法：把协商降到 gzip。
# 脚本层只有 $utils.ungzip（Build ≥ 988），br/zstd 没有解码器。
AE_SET_GZIP = re.compile(
    r'request\.header\.set\(\s*"Accept-Encoding"\s*,\s*"gzip"\s*\)')


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
                "body": bool(REWRITE_BODY_RX.search(line)),
                "line": line,
            }
        )
    return out


def check_cross_layer(fp, family, data, scripts, samples):
    """[Rule] / [Rewrite] / [Script] 三层用同一批真实 URL 交叉验证。

    只锁“会静默吃掉脚本”的组合：静态整域拒绝、终止型复写、原生 Body 改写。
    传输层优化（删 Accept-Encoding）是互补的，不算短路。

    层序依据（官方文档）：「Rewrite 仅对 HTTP 和经过 MitM 解密的 HTTPS 请求
    生效，并在规则匹配前执行」。所以在 MITM 内部是 Rewrite → Script；
    静态 [Rule] 整域拒绝是否先于脚本生效取决于连接有没有进入 HTTP 引擎，
    文档没有给出可依赖的顺序——这里按“可能先命中”的保守假设处理。
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
            if not rw["rx"].match(url):
                continue
            if rw["body"]:
                # response.body.mock 在请求出网前就生成响应，两个阶段的脚本都吃不到。
                stages = {rw["stage"]}
                if "response.body.mock" in rw["line"]:
                    stages = {"request", "response"}
                for entry in entries:
                    if not entry["compiled"] or not entry["compiled"].match(url):
                        continue
                    if entry["stage"] not in stages:
                        continue
                    problems += 1
                    errors.append(
                        f"{fp}: 跨层短路：原生 Body 改写命中 {url}，"
                        f"{entry['stage']} 脚本 {entry['script']} 不再执行"
                        "（文档：Body Rewrite 命中后同阶段 Script 不执行）"
                    )
                continue
            if not rw["terminal"]:
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


def mitm_host_list(mitm_text):
    line = next(
        (line for line in mitm_text.splitlines() if line.startswith("hostname")), "")
    return [
        host.strip()
        for host in line.split("=", 1)[-1].replace("%APPEND%", "").split(",")
        if host.strip()
    ]


def glob_host_regex(pattern):
    return re.compile(
        "".join(
            ".*" if char == "*" else "." if char == "?" else re.escape(char)
            for char in pattern
        )
        + r"\Z"
    )


def mitm_covers(host, mitm_text):
    """[MITM] 支持 `*`/`?` 通配：精确域名或覆盖它的 glob 都算在内。"""
    for pattern in mitm_host_list(mitm_text):
        if pattern == host:
            return True
        if "*" in pattern or "?" in pattern:
            if glob_host_regex(pattern).match(host):
                return True
    return False


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
        if not mitm_covers(host, mitm_text):
            errors.append(f"{fp}: QUIC fallback host {host} is not in [MITM]")
    # 分片族必须一条 glob 覆盖，而不是悄悄退回逐个枚举的 MITM 名单。
    if PANGLE_MITM_GLOB not in mitm_host_list(mitm_text):
        errors.append(
            f"{fp}: [MITM] must use the single glob {PANGLE_MITM_GLOB} "
            "for the Pangle shard family"
        )

    # 压缩协商：允许「br → gzip 降级」，禁止「免压缩」。
    #   · 免压缩（request.header.del / replace 掉 Accept-Encoding）经真机体积
    #     核算后放弃：upsell 类响应 gzip 后 183~191 KB，去压缩膨胀 5~10 倍。
    #   · br → gzip 是另一回事：脚本层只有 $utils.ungzip，br/zstd 没有解码器，
    #     收到就是乱码 → 落进「不是 JSON」分支 → 静默不清理。降级保住了压缩，
    #     只多 10~20% 体积，换来「不会再因为编码而整条失效」。
    rewrite_lines = data.get("Rewrite", [])
    for line in rewrite_lines:
        if "Accept-Encoding" in line and not AE_SET_GZIP.search(line):
            errors.append(
                f"{fp}: Accept-Encoding 只允许 "
                '`request.header.set("Accept-Encoding", "gzip")` 这种降级写法；'
                "删压缩 / 改 identity 已按体积核算否决"
                "（docs/loon-native-first.md E2）"
            )

    # 降级规则必须覆盖 [MITM] 的每一个域名：漏一个，那个域名的 br 响应
    # 仍然解不开，而且是**静默**的——这类漏配比不写还难查。
    ae_rules = [
        line
        for line in rewrite_lines
        if line.startswith("request if") and AE_SET_GZIP.search(line)
    ]
    if not ae_rules:
        errors.append(
            f"{fp}: 缺少 Accept-Encoding 降级规则"
            '（request.header.set("Accept-Encoding","gzip")）；'
            "br 响应在脚本层没有解码器，会静默跳过清理"
        )
    else:
        compiled = []
        for line in ae_rules:
            rx = regex_literal(line)
            if not rx:
                errors.append(f"{fp}: Accept-Encoding 降级规则的 URL 正则解析失败")
                continue
            try:
                compiled.append(re.compile(rx))
            except re.error as exc:
                errors.append(f"{fp}: Accept-Encoding 降级正则非法: {exc}")
        for host in QUIC_HOSTS[family]:
            probe = f"https://{host}/"
            if not any(rx.match(probe) for rx in compiled):
                errors.append(
                    f"{fp}: [MITM] 域名 {host} 不在 Accept-Encoding 降级规则里；"
                    "该域名一旦回 br，脚本会静默跳过"
                )

    # 官方 MitM 文档只列 hostname / ca-p12 / ca-passphrase，没有 h2；
    # 官方产品页把「解密 HTTPS 和 HTTP/2」写成默认能力、无开关。社区插件通行写
    # h2 = true，保留它是「未知键被忽略」的零成本保险——但不能对外当成能力点宣称
    # （统计口径已剔除，见 docs/loon-native-first.md §9.3）。写成 false 才是真错。
    if "h2 = true" not in mitm_text:
        if re.search(r"^\s*h2\s*=\s*false\s*$", mitm_text, re.M):
            errors.append(f"{fp}: [MITM] h2 = false 会主动关掉 HTTP/2 解密")
        else:
            errors.append(
                f"{fp}: [MITM] 缺少 h2 = true（未文档化键，作零成本保险保留；"
                "见 docs/loon-native-first.md §9.3）"
            )

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


ARG_CONTROLS = {"input", "select", "switch"}
ARG_TYPES = {"string", "number", "boolean"}


def split_arg_tokens(rest):
    """按英文逗号切分，但引号内的逗号不切（`select,"a","b"` / `desc="x,y"`）。"""
    out, buf, quoted = [], [], False
    for ch in rest:
        if ch == '"':
            quoted = not quoted
            buf.append(ch)
        elif ch == "," and not quoted:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf).strip())
    return out


def parse_argument_line(line):
    """拆 `name = control,v1,v2,type=..,tag=..,desc=..`。

    每个候选值单独成为一项；`type=` / `tag=` / `desc=` 是元数据。
    """
    if "=" not in line:
        return None
    name, rest = line.split("=", 1)
    name = name.strip()
    if not re.match(r"^[A-Za-z_]\w*$", name):
        return None
    tokens = split_arg_tokens(rest)
    control = tokens[0]
    values, meta = [], {}
    for tok in tokens[1:]:
        m = re.match(r"^(type|tag|desc)\s*=\s*(.*)$", tok)
        if m:
            meta[m.group(1)] = m.group(2).strip()
        elif tok:
            values.append(tok.strip('"'))
    return name, control, values, meta


def check_argument_schema():
    """[Argument] 只能出现官方文档定义的控件与类型。

    官方只定义 3 种控件（input / select / switch）和 3 种类型
    （string / number / boolean），并且明确 `integer` / `float` / `bool`
    这类别名**不能解析**——写错不会报错，只会让整个参数失效。
    """
    total = 0
    for fp, _s, _r, _w, _sc, _f in PLUGINS:
        path = ROOT / fp
        if not path.exists():
            continue
        data, _ = parse_plugin(path)
        seen = set()
        for line in data.get("Argument", []):
            parsed = parse_argument_line(line)
            if not parsed:
                errors.append(f"{fp}: malformed [Argument] line: {line[:80]}")
                continue
            name, control, values, meta = parsed
            total += 1
            if name in seen:
                errors.append(f"{fp}: duplicate [Argument] name: {name}")
            seen.add(name)
            if control not in ARG_CONTROLS:
                errors.append(
                    f"{fp}: [Argument] {name} uses unknown control {control!r} "
                    f"(only {sorted(ARG_CONTROLS)})"
                )
                continue
            declared = meta.get("type")
            if declared is not None and declared not in ARG_TYPES:
                errors.append(
                    f"{fp}: [Argument] {name} uses unsupported type {declared!r} "
                    f"(only {sorted(ARG_TYPES)}; aliases are rejected by Loon)"
                )
            kind = declared or "string"
            if control == "switch":
                if len(values) != 1 or values[0].lower() not in {"true", "false"}:
                    errors.append(
                        f"{fp}: [Argument] {name} switch default must be true/false, "
                        f"got {values}"
                    )
            elif control == "select":
                if len(values) < 2:
                    errors.append(
                        f"{fp}: [Argument] {name} select needs at least 2 options, "
                        f"got {values}"
                    )
            elif len(values) > 1:
                errors.append(
                    f"{fp}: [Argument] {name} input takes at most 1 default, got {values}"
                )
            if kind == "number":
                for v in values:
                    try:
                        float(v)
                    except ValueError:
                        errors.append(
                            f"{fp}: [Argument] {name} type=number but value {v!r} is not numeric"
                        )
            if kind == "boolean":
                for v in values:
                    if v.lower() not in {"true", "false"}:
                        errors.append(
                            f"{fp}: [Argument] {name} type=boolean but value {v!r} is not a boolean"
                        )
    print(f"argument schema: {total} declarations use documented controls/types")


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


def load_args_schema(family):
    """参数开关的唯一事实源；生成器负责插件行/状态标签/README 表。"""
    path = ROOT / "src" / "args" / f"{family}.json"
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: cannot read args schema: {exc}")
        return None
    if schema.get("family") != family:
        errors.append(
            f"{path.relative_to(ROOT)}: family {schema.get('family')!r} != {family!r}"
        )
        return None
    return schema


def check_args_generated():
    """插件 [Argument] / SWITCH_LABELS / README 表必须与 src/args 逐字节一致。"""
    proc = subprocess.run(
        ["node", "tools/gen-args.js", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        for line in (proc.stdout + proc.stderr).strip().splitlines():
            errors.append(f"args schema: {line}")
        return
    print("  " + proc.stdout.strip())


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
    for key in ("name", "desc", "author", "version", "homepage", "openUrl", "icon"):
        if key not in meta:
            errors.append(f"{fp}: missing #!{key} metadata")
    if "icon" in meta and not meta["icon"].startswith("https://"):
        errors.append(f"{fp}: #!icon must be an https URL, got {meta['icon'][:60]}")
    if "openUrl" in meta and not meta["openUrl"].startswith("https://"):
        errors.append(f"{fp}: #!openUrl must be an https URL, got {meta['openUrl'][:60]}")
    print(f"  meta: {meta.get('name', '?')} v{meta.get('version', '?')} icon={meta.get('icon', '-')[:60]}")

    schema = load_args_schema(family)
    arg_names = [item["name"] for item in schema["switches"]] if schema else []

    generic_status = [
        line for line in data.get("Script", [])
        if line.startswith("generic") and "status.min.js" in line
    ]
    if not generic_status:
        errors.append(f"{fp}: missing generic status.min.js binding")
    else:
        status_line = generic_status[0]
        for name in arg_names:
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

    # 名单里允许 glob（Pangle 分片族），所以不再做「字面集合相等」：
    # 改成用真实 URL 样本验证「名单」「[Script] 正则」两侧同时命中；
    # 反样本两侧都不许命中。任一侧漏了或放宽了，样本立刻失败。
    block_rx = None
    for line in scripts:
        if "block-domains.min.js" not in line:
            continue
        m = re.search(r"\$\{url\} ~\= /(.+?)/ then", line)
        if m:
            block_rx = re.compile(re.sub(r"\\(.)", r"\1", m.group(1)))
    if block_rx is None:
        errors.append(f"{fp}: cannot extract block-domains script regex")
    else:
        for url in BLOCK_HOST_SAMPLES:
            host = re.match(r"https?://([^/:?#]+)", url).group(1)
            if not any(glob_host_regex(p).match(host) for p in block_common):
                errors.append(f"{fp}: block-domains list misses {host}")
            if not block_rx.search(url):
                errors.append(f"{fp}: block-domains [Script] regex misses {url}")
        for url in BLOCK_HOST_MUST_MISS:
            host = re.match(r"https?://([^/:?#]+)", url).group(1)
            if any(glob_host_regex(p).match(host) for p in block_common):
                errors.append(f"{fp}: block-domains list overmatches {host}")
            if block_rx.search(url):
                errors.append(f"{fp}: block-domains [Script] regex overmatches {url}")
    mitm_entries = mitm_host_list(mitm)
    for host in sorted(block_common):
        if host in mitm_entries:
            continue
        if any(char in host for char in "*?"):
            errors.append(f"{fp}: [MITM] must declare the same glob {host}")
        else:
            errors.append(f"{fp}: [MITM] missing block-domain host {host}")
    print(f"  block-domains set: {len(block_common)} entries pinned to src/common")

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


def check_encoding_guard():
    """能解 body 的脚本：诊断必须能区分「非 JSON」和「编码不支持」。

    脚本层只有 $utils.ungzip（gzip），br / zstd / deflate 没有解码器；
    而 br 没有魔数（RFC 7932 是纯 stream format），连「这是不是 br」都只能
    看 content-encoding。所以每个「解析失败」分支都必须把 ce= 带出来，
    否则「接口换成 br 了」会被误判成「接口换了形状」，排查方向完全错。
    """
    for rel in ENCODING_GUARD_SCRIPTS:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: missing body-parsing script")
            continue
        text = path.read_text(encoding="utf-8")
        if "function readBody(" not in text:
            errors.append(f"{rel}: no readBody() found")
            continue
        if "function ceTag(" not in text:
            errors.append(
                f"{rel}: missing ceTag(); a br/zstd body would look like 'not JSON'")
            continue
        if 'ce === "gzip"' not in text:
            errors.append(f"{rel}: ceTag() must treat gzip as normal (no ce= noise)")
        for marker in ENCODING_BRANCH_MARKERS:
            for line in text.splitlines():
                if marker in line and "ceTag(" not in line:
                    errors.append(f"{rel}: {marker!r} branch misses ceTag()")
    print(f"encoding guard: {len(ENCODING_GUARD_SCRIPTS)} body-parsing scripts tagged")


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
        if SAFE_STORE_WIPE_RX.search(SAFE_COMMENT_RX.sub("", text)):
            errors.append(
                f"{rel}: $persistentStore.remove() 会清空全部脚本的键，"
                "删单个键请用 write(undefined, key)（Script API 5.3）"
            )
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


# 本插件自己声明的 DNS（[General] 的 dns-server / doh-server）。
# 把任何一个写进「公共解析器 IP 直连阻断」清单，等于让 Loon 掐断自己的解析链：
# 表现不是「广告回来」，而是整网不可用。build 管语法，这里管语义。
OWN_DNS_IPS = {
    "223.5.5.5", "223.6.6.6",          # dns-server + doh-server
    "119.29.29.29",                     # dns-server（DNSPod 公共 DNS）
    "180.184.1.1",                      # dns-server
    "1.12.12.12",                       # doh-server
}

# 四家公共解析器的官方 IPv4/IPv6，逐条锁死：少一条就是「以为封了其实漏了一路」，
# 多一条就要先核对是不是本插件自用的 DNS。
PUBLIC_RESOLVER_IPS = {
    "Google": ("8.8.8.8", "8.8.4.4", "2001:4860:4860::8888", "2001:4860:4860::8844"),
    "Cloudflare": ("1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"),
    "Quad9": ("9.9.9.9", "149.112.112.112", "2620:fe::fe", "2620:fe::9"),
    "AdGuard": ("94.140.14.14", "94.140.15.15", "2a10:50c0::ad1:ff", "2a10:50c0::ad2:ff"),
}


def check_bypass_dns_guard():
    """第九轮：公共 DNS 解析器 IP 直连阻断组的语义守卫。

    这条旁路（App 直连 8.8.8.8:443 做 DoH）里连接层没有域名，
    唯一生效的是 IP 类规则；但它的风险也最大——误伤本插件自用的 DNS
    会让整网不可用。build 只校验语法，语义由这里承担。
    """
    src_path = ROOT / "src/ads/domains.json"
    try:
        source = json.loads(src_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"ads: cannot read {src_path}: {exc}")
        return
    optional = source.get("plugins", {}).get("ads", {}).get("rules_disabled") or []

    blocked_ips = set()
    for raw in optional:
        if not isinstance(raw, str):
            continue
        line = raw.strip()
        if line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        if parts[0] in ("IP-CIDR", "IP-CIDR6"):
            blocked_ips.add(parts[1].split("/", 1)[0])

    problems = 0

    for ip in sorted(blocked_ips & OWN_DNS_IPS):
        errors.append(
            f"ads: {ip} 是本插件 [General] 自己声明的 DNS，写进 IP 阻断清单会"
            "掐断 Loon 自身的解析链（表现为整网不可用）。删掉这一条"
        )
        problems += 1

    for vendor, ips in sorted(PUBLIC_RESOLVER_IPS.items()):
        for ip in ips:
            if ip not in blocked_ips:
                errors.append(
                    f"ads: 公共解析器 {vendor} 的 {ip} 不在可选阻断清单里——"
                    "这条旁路按「每家两条 v4 + 两条 v6」封，漏一条就漏一路"
                )
                problems += 1

    # 生成物必须带上这一段（build 保证，这里再确认一次可选段确实进了插件）
    plugin = ROOT / ADS_PLUGIN
    if plugin.exists():
        raw = plugin.read_text(encoding="utf-8")
        if "# IP-CIDR,8.8.8.8/32,REJECT,no-resolve" not in raw:
            errors.append(
                f"{ADS_PLUGIN}: 缺少公共解析器 IP 直连阻断段；"
                "改完 src/ads/domains.json 要跑 `python3 tools/build-ads.py`"
            )
            problems += 1

    print(
        "bypass dns guard: %d blocked ip(s) / %d vendor(s) / %d problem(s)"
        % (len(blocked_ips), len(PUBLIC_RESOLVER_IPS), problems)
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
    if "openUrl" in meta and not meta["openUrl"].startswith("https://"):
        errors.append(f"{ADS_PLUGIN}: #!openUrl must be an https URL")
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
        "DOMAIN-KEYWORD,httpdns,REJECT-DROP",
        "DOMAIN-KEYWORD,httpsdns,REJECT-DROP",
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
            if param in SURGE_ONLY_RULE_PARAMS:
                errors.append(
                    f"{ADS_PLUGIN}: [Rule] uses the Surge-only parameter {param!r}; "
                    "Loon has no such option (see docs/loon-native-first.md §10)"
                )
            elif param not in ADS_RULE_PARAMS:
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

    # DOMAIN-WILDCARD 两层（广告子域 + 数字分片家族）：语法仅 Loon 3.5.3(1008)+
    # 提供，而当前 App Store 正式版是 3.5.2(996)，低版本遇到未知规则类型的行为
    # 官方未文档化。因此两层必须以注释行存在：活动 [Rule] 里出现 DOMAIN-WILDCARD
    # 会把正式版用户置于「整段不可用」风险，永久禁止。
    # glob 语义校验（'*' 跨点、正/负样本、保护名单）照常跑在注释层上。
    active_wildcards = [
        [part.strip() for part in line.split(",")]
        for line in rules
        if line.split(",", 1)[0].strip() == "DOMAIN-WILDCARD"
    ]
    if active_wildcards:
        errors.append(
            f"{ADS_PLUGIN}: DOMAIN-WILDCARD rules must stay commented — "
            "App Store 3.5.2(996) 不能解析该规则类型"
        )
    commented_globs = [
        m.group(1)
        for m in re.finditer(r"(?m)^# DOMAIN-WILDCARD,([^,]+),REJECT[ \t]*$", raw)
    ]
    wildcard_patterns = list(commented_globs)
    ad_label_globs = wildcard_patterns[: len(ADS_WILDCARDS)]
    family_globs = wildcard_patterns[len(ADS_WILDCARDS) :]
    if tuple(ad_label_globs) != ADS_WILDCARDS:
        errors.append(
            f"{ADS_PLUGIN}: commented DOMAIN-WILDCARD set {ad_label_globs}, "
            f"expected {list(ADS_WILDCARDS)}"
        )
    if tuple(family_globs) != ADS_FAMILY_WILDCARDS:
        errors.append(
            f"{ADS_PLUGIN}: family DOMAIN-WILDCARD set {family_globs}, "
            f"expected {list(ADS_FAMILY_WILDCARDS)}"
        )
    if len(set(wildcard_patterns)) != len(wildcard_patterns):
        errors.append(f"{ADS_PLUGIN}: duplicate DOMAIN-WILDCARD rule")
    loon_version = meta.get("loon_version", "")
    loon_build = re.search(r"\((\d+)\)", loon_version)
    if not loon_build or int(loon_build.group(1)) > ADS_APPSTORE_STABLE_BUILD:
        errors.append(
            f"{ADS_PLUGIN}: #!loon_version={loon_version!r} must not exceed the "
            f"App Store stable build ({ADS_APPSTORE_STABLE_BUILD}) — TestFlight "
            "gating blocks real users from importing"
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

    # 数字分片家族层：每条 glob 必须真的覆盖它声明的主机，类只允许 [0-9]，
    # 且不能与上一层 glob 重复或越界命中。
    for pattern in family_globs:
        if "[0-9]" not in pattern:
            errors.append(
                f"{ADS_PLUGIN}: family glob {pattern} must contain a [0-9] class"
            )
        for body in re.findall(r"\[([^\]]*)\]", pattern):
            if body != "0-9":
                errors.append(
                    f"{ADS_PLUGIN}: family glob {pattern} uses [{body}]; only [0-9] is allowed"
                )
        if pattern in ADS_WILDCARDS:
            errors.append(f"{ADS_PLUGIN}: family glob {pattern} duplicates ad-label layer")
        regex = ads_glob_regex(pattern)
        for host in ADS_FAMILY_COVERS.get(pattern, ()):
            if not regex.fullmatch(host):
                errors.append(
                    f"{ADS_PLUGIN}: family glob {pattern} misses enumerated host {host}"
                )
        for root in protected:
            if regex.fullmatch(root):
                errors.append(
                    f"{ADS_PLUGIN}: family glob {pattern} matches protected root {root}"
                )
        for sample in ADS_FAMILY_MUST_MISS:
            if regex.fullmatch(sample):
                errors.append(
                    f"{ADS_PLUGIN}: family glob {pattern} overmatches {sample}"
                )
    if len(set(family_globs)) != len(family_globs):
        errors.append(f"{ADS_PLUGIN}: duplicate family DOMAIN-WILDCARD rule")

    if "# IP-CIDR,203.107.1.0/24,REJECT,no-resolve" not in raw:
        errors.append(f"{ADS_PLUGIN}: optional HTTPDNS IP block must stay commented")
    # 2026 全网取证补的网关 IP 也必须保持默认注释（可选层纪律）。
    for marker in (
        "# IP-CIDR,203.119.238.240/32,REJECT,no-resolve",
        "# IP-CIDR,43.132.43.43/32,REJECT,no-resolve",
        "# IP-CIDR6,2401:b180:7001::31d/128,REJECT,no-resolve",
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
        f"domain_wildcards_commented={len(commented_globs)}"
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


APP_RULE_KINDS = {"DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}
APP_RULE_ACTIONS = {"REJECT", "REJECT-DROP"}
APP_HOST_RE = re.compile(r"^(?:\*\.)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)+\s*=\s*\d{1,3}(?:\.\d{1,3}){3}$")
APP_SECTIONS = {"Rule", "Host"}
# 做了证书固定/等效私有加密通道（mmtls）的 App：MITM 不可行甚至触发风控，
# 它们的 src/apps JSON 永远不许出现 enhance 层（用户裁决：仅非固定 App 加默认关增强层）。
APP_NO_ENHANCE_SLUGS = {"banks", "wechat", "mijia", "x", "instagram", "jd"}


def collect_source_urls(plugin):
    urls = []
    for line in plugin.read_text().splitlines():
        s = line.strip()
        if s.startswith("# 证据:"):
            urls.append(s.split("# 证据:", 1)[1].strip())
    return urls


def rd_has_section(readme, heading):
    return readme.exists() and heading in readme.read_text(encoding="utf-8")


def check_app_plugins():
    src_dir = ROOT / "src/apps"
    roots_path = ROOT / "src/ads/protected-roots.json"
    protected = set(json.loads(roots_path.read_text())["roots"]) if roots_path.exists() else set()
    apps = sorted(p for p in src_dir.glob("*.json") if not p.name.startswith("_"))
    if not apps:
        errors.append("apps: no src/apps/*.json found")
        return
    for path in apps:
        slug = path.stem
        try:
            data = json.loads(path.read_text())
        except Exception as e:
            errors.append(f"apps/{slug}: bad json: {e}")
            continue
        if data.get("slug") != slug:
            errors.append(f"apps/{slug}: slug field {data.get('slug')!r} != filename stem")
        plugin = ROOT / "plugins" / slug / f"{slug}.plugin"
        if not plugin.exists():
            errors.append(f"apps/{slug}: generated plugin missing: {plugin.relative_to(ROOT)} (run npm run build:apps)")
            continue
        meta = parse_meta(plugin)
        for key in ("name", "desc", "version", "date", "tag", "loon_version", "type"):
            if not meta.get(key):
                errors.append(f"apps/{slug}: header missing #{key} in {plugin.relative_to(ROOT)}")
        if meta.get("type") != "normal":
            errors.append(f"apps/{slug}: #!type must be normal, got {meta.get('type')!r}")
        m_build = re.search(r"\((\d+)\)", meta.get("loon_version", ""))
        if m_build and int(m_build.group(1)) > ADS_APPSTORE_STABLE_BUILD:
            errors.append(
                f"apps/{slug}: #!loon_version={meta.get('loon_version')!r} gates on a "
                f"TestFlight build (> {ADS_APPSTORE_STABLE_BUILD}); App Store users "
                "could not import"
            )
        for key in ("homepage", "openUrl", "icon"):
            val = meta.get(key, "")
            if val and not val.startswith("https://"):
                errors.append(f"apps/{slug}: #{key} must be https: {val}")
        parsed, sections = parse_plugin(plugin)
        bad = [s for s in sections if s not in APP_SECTIONS]
        if bad:
            errors.append(f"apps/{slug}: sections outside Rule/Host: {sorted(set(bad))}")
        for line in parsed.get("Rule", []):
            parts = [p.strip() for p in line.split(",")]
            if parts[0] not in APP_RULE_KINDS:
                errors.append(f"apps/{slug}: rule kind not whitelisted: {line}")
            if parts[-1] not in APP_RULE_ACTIONS:
                errors.append(f"apps/{slug}: rule action not whitelisted: {line}")
            if parts[0] == "DOMAIN-WILDCARD":
                errors.append(
                    f"apps/{slug}: DOMAIN-WILDCARD is TestFlight-only (3.5.3/1008); "
                    "app plugins must stay importable on App Store stable (3.5.2/996) — "
                    "use [Host] '*.domain' blackhole instead"
                )
        for line in parsed.get("Host", []):
            if not APP_HOST_RE.match(line):
                errors.append(f"apps/{slug}: bad [Host] line: {line}")
            host = line.split("=")[0].strip().removeprefix("*.")
            if host in protected:
                errors.append(f"apps/{slug}: [Host] blackholes a protected root: {host}")
        for url in collect_source_urls(plugin):
            if not url.startswith("https://"):
                errors.append(f"apps/{slug}: evidence url not https: {url}")
        enh = data.get("enhance")
        if enh is not None:
            if slug in APP_NO_ENHANCE_SLUGS:
                errors.append(
                    f"apps/{slug}: cert-pinned app must not ship an enhance/MITM layer "
                    "(红线：MITM 不可行也不做)"
                )
            raw = plugin.read_text()
            for line in raw.splitlines():
                s = line.strip()
                if s.startswith(("[MITM]", "hostname =", "URL-REGEX,")):
                    errors.append(
                        f"apps/{slug}: enhance line must stay commented: {s!r}"
                    )
            if not rd_has_section(plugin.parent / "README.md", "可选 MITM 增强层"):
                errors.append(f"apps/{slug}: README missing 可选 MITM 增强层 section")
            for key in ("mitm_hosts", "url_regex", "sources"):
                if not enh.get(key):
                    errors.append(f"apps/{slug}: enhance.{key} empty")
            for r in enh.get("url_regex", []):
                parts = r.split(",")
                if parts[0] != "URL-REGEX" or len(parts) != 3:
                    errors.append(f"apps/{slug}: enhance url_regex malformed: {r!r}")
        rd = plugin.parent / "README.md"
        if not rd.exists():
            errors.append(f"apps/{slug}: missing plugins/{slug}/README.md")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/build-apps.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-6:]
        errors.append("apps: generated plugins are stale; run `python3 tools/build-apps.py`\n"
                      + "\n".join("    " + line for line in tail))
    else:
        print(f"apps: {len(apps)} app plugins lint-clean and in sync with src/apps/")


check_shared_scripts()
check_switch_labels()
check_argument_schema()
check_args_generated()
check_quic_count()
check_encoding_guard()
check_script_safety()
check_bypass_dns_guard()
check_ads_family()
check_app_plugins()
print(f"lint errors: {len(errors)}")
for err in errors:
    print(" -", err)
sys.exit(1 if errors else 0)
