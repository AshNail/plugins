#!/usr/bin/env python3
"""Structural lint for the Loon plugins (soda/douyin + the single ads plugin)."""
import fnmatch
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parent.parent


def escape_regex_slashes(pattern):
    return re.sub(r"(?<!\\)/", r"\\/", pattern)

# (path, sections, rules, rewrites, scripts, family)
PLUGINS = [
    ("plugins/soda/soda.plugin", 5, 0, 2, 39, "soda"),
    ("plugins/douyin/douyin.plugin", 5, 0, 1, 11, "douyin"),
]

# 只读观测脚本不需要 argument
OBSERVER_SCRIPTS = ("reward-observe.min.js", "observe.min.js")

FAMILY_CHECKS = {
    "soda": {
        "enable": {
            "splashClean": 1,
            "cleanAds": 8,
            "killRewardAds": 2,
            "blockAdDomains": 1,
            "settingsClean": 1,
            "skipUpdateCheck": 1,
            "hideDouyinEntry": 1,
            "hideDouyinTab": 1,
            "blockSplashAd": 1,
            "debugLog": 21,
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
            "luna-card": "https://beta-luna.douyin.com/luna/card",
            "luna-upsell-sort": "https://beta-luna.douyin.com/luna/commerce/v2/upsell_sort_decision?x=1",
            "splash-v2": "https://ad.zijieapi.com/api/ad/v2/ack/splash/report",
            "luna-check-update": "https://beta-luna.douyin.com/luna/check-update",
            "luna-check-update-slash": "https://api.qishui.com/luna/check-update/",
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
            "https://beta-luna.douyin.com/luna/advert/splash/brand/retrieve",
            "https://beta-luna.douyin.com/luna/advert/incentive/config",
            "https://beta-luna.douyin.com/luna/advert/incentive/retrieve",
            "https://beta-luna.douyin.com/luna/ads/config",
            "https://beta-luna.douyin.com/luna/card",
            "https://beta-luna.douyin.com/luna/feed/song-tab",
            "https://beta-luna.douyin.com/luna/commerce/v2/upsell_sort_decision?x=1",
            "https://api.qishui.com/luna/check-update",
            "https://beta-luna.douyin.com/luna/check-update",
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
        # 与两个构建器同一个口径：手写表 ∪ 由 App 红线派生的根。
        protected = REDLINES_MODULE.protected_roots()
    except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
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
        "httpdns.baidu.com",
    ):
        if domain not in exact:
            errors.append(f"{ADS_PLUGIN}: HTTPDNS sample missing: {domain}")
    # 红线冲突候选永久锁定：这几条只能以注释形态存在于 ads，绝不允许激活。
    # resolver.msg.xiaomi.net 曾经默认生效——它不在 mijia 那句 comment 红线里，而在同一文件的
    # triage_exclude 台账（推送/云红线 resolver.msg.*）里，第 27 轮只读 comment 的门禁看不见它。
    for marker in (
        "# resolver.msg.xiaomi.net = 127.0.0.1",
        "# dns.jd.com = 127.0.0.1",
        "# union.jd.com = 127.0.0.1",
        "# *.union.jd.com = 127.0.0.1",
    ):
        if marker not in raw:
            errors.append(f"{ADS_PLUGIN}: app-redline overlap entry missing: {marker}")
    for domain in ("resolver.msg.xiaomi.net", "dns.jd.com", "union.jd.com"):
        if domain in exact:
            errors.append(f"{ADS_PLUGIN}: 按 App 插件的红线被 ads 激活: {domain}")
        if any(base != domain and domain.endswith("." + base) for base in wildcard):
            errors.append(f"{ADS_PLUGIN}: 某条通配把红线 {domain} 捞进生效组")
    # 公共 DoH 断言要感知通配覆盖——`=adguard-dns.com` 形态下
    # family/unfiltered 变体不在 exact 里，但被 *.'d 基域覆盖即算命中。
    def covered(domain: str) -> bool:
        if domain in exact:
            return True
        return any(domain.endswith("." + base) for base in wildcard)

    for domain in (
        "dns.google",
        "cloudflare-dns.com",
        "dns.adguard-dns.com",
        "family.adguard-dns.com",
        "unfiltered.adguard-dns.com",
        "security.cloudflare-dns.com",
        "family.cloudflare-dns.com",
        "adblock.doh.mullvad.net",
        "doh.dns.sb",
    ):
        if not covered(domain):
            errors.append(f"{ADS_PLUGIN}: public DoH sample missing: {domain}")

    # 国内公共 DoH 默认不得生效。Loon 主配置在国内常用域名形式 doh/doq，
    # [Host] 会把 Loon 自己的加密 DNS 一起打到 127.0.0.1：2026-10-29 的 23 小时
    # 真机日志里 dns.alidns.com 17,073 + doh.pub 11,239 = 28,312 次 Host Map，
    # 连带 5,236 次 DoQ 连接尝试与 10,389 次 DoH 连接失败。插件读不到主配置，
    # 无法只在 App 流量上生效，因此这 9 条只能留在 doh_public_cn 默认注释组。
    ads_doh_self_harm = (
        "dns.alidns.com",
        "doh.aliyun.com",
        "doh.pub",
        "dns.pub",
        "dot.pub",
        "sm2.doh.pub",
        "doh.360.cn",
        "dot.360.cn",
        "dot.alidns.com",
    )
    for domain in ads_doh_self_harm:
        if domain in exact or any(domain.endswith("." + base) for base in wildcard):
            errors.append(
                f"{ADS_PLUGIN}: 国内公共 DoH 默认生效会打死 Loon 自己的解析链: {domain}"
            )
        if f"# {domain} = 127.0.0.1" not in raw:
            errors.append(
                f"{ADS_PLUGIN}: 国内公共 DoH 必须以默认注释形态保留: {domain}"
            )
    try:
        ads_source = json.loads(
            pathlib.Path("src/ads/domains.json").read_text(encoding="utf-8")
        )["plugins"]["ads"]["groups"]
        cn_group = next((g for g in ads_source if g.get("id") == "doh_public_cn"), None)
        if not cn_group or not cn_group.get("disabled"):
            errors.append("ads: src/ads/domains.json 缺少默认注释组 doh_public_cn")
        elif set(cn_group.get("rules") or []) != set(ads_doh_self_harm):
            errors.append(
                "ads: doh_public_cn 必须恰好包含 9 条国内公共 DoH，"
                "新增/删除都要同步 lint 的自伤名单"
            )
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"ads: cannot read doh_public_cn from src/ads/domains.json: {exc}")

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


ADS_README = "plugins/ads/README.md"
# README 把 HTTPDNS 与公共 DoH 单独成行；其余未注释组在文档里合称「核心广告组」。
ADS_ROLED_GROUPS = ("httpdns", "doh_public")
ADS_COUNT_UNIT = re.compile(r"(\d+)\s*(?:组|条)")

# 表格行标签 -> 该行「N 组 / N 条」应当出现的数字（顺序敏感）。
def ads_row_expectations(counts):
    return {
        "`[Host]` 核心广告组": [counts["__core_groups"], counts["__core_rules"]],
        "`[Host]` HTTPDNS 组": [counts["__httpdns_rules"]],
        "`[Host]` 公共 DoH 组": [counts["__doh_public_rules"]],
        "`[Rule]`": [counts["rules"]],
        "`[Rule]` DOMAIN-WILDCARD 通配/家族层": [counts["__glob_total"]],
        "`[General]`": [counts["general"]],
        "`[Host]` 默认注释组": [counts["__off_groups"], counts["__off_rules"]],
        "`[Rule]` 可选组": [
            counts["rules_disabled"],
            counts["optional_httpdns_ip"],
            counts["optional_public_ip"],
        ],
        "`[IP Rewrite]` 可选组": [counts["ip_rewrite_disabled"]],
    }


# 括号里的拆分数字后面不跟「组/条」，只能按题注取：和合计行同一套标签锚定语法。
ADS_ROW_PATTERNS = {
    "`[Rule]` DOMAIN-WILDCARD 通配/家族层": [
        (r"（(\d+) 广告左标签 \+ (\d+) 数字分片家族", ("wildcards", "family_wildcards")),
    ],
}

# 合计行的每条数字都带一个唯一标签：按标签取值，不按位置数列，改一行不会牵动其他行。
ADS_SUMMARY_PATTERNS = (
    (r"(\d+) 组、", ("groups",)),
    (r"(\d+) 条生效 Host", ("active",)),
    (r"exact (\d+) / wildcard (\d+)", ("host_exact", "host_wildcard")),
    (r"(\d+) 条默认注释 Host", ("disabled",)),
    (r"(\d+) 条生效 Rule", ("rules",)),
    (r"(\d+) 条默认注释 DOMAIN-WILDCARD", ("__glob_total",)),
    (r"（(\d+) 通配 \+ (\d+) 家族", ("wildcards", "family_wildcards")),
    (r"(\d+) 条默认注释可选 Rule", ("rules_disabled",)),
    (r"(\d+) 条默认注释 IP Rewrite", ("ip_rewrite_disabled",)),
)


def ads_machine_counts():
    """向 build-ads 要一份机器算出的计数——文档数字唯一的对照源。"""
    proc = subprocess.run(
        [sys.executable, "tools/build-ads.py", "--stats-json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        errors.append("ads: tools/build-ads.py --stats-json failed:\n" + proc.stderr.strip())
        return None
    try:
        counts = json.loads(proc.stdout)["ads"]
    except (ValueError, KeyError) as exc:
        errors.append(f"ads: cannot parse --stats-json: {exc}")
        return None
    counts["__glob_total"] = counts["wildcards"] + counts["family_wildcards"]
    core = [g for g in counts["by_group"] if not g["disabled"] and g["id"] not in ADS_ROLED_GROUPS]
    roled = [g for g in counts["by_group"] if g["id"] in ADS_ROLED_GROUPS]
    off = [g for g in counts["by_group"] if g["disabled"]]
    counts["__core_groups"] = len(core)
    counts["__core_rules"] = sum(g["rules"] for g in core)
    counts["__roled_total"] = sum(g["rules"] for g in roled)
    counts["__off_groups"] = len(off)
    counts["__off_rules"] = sum(g["rules"] for g in off)
    by_id = {g["id"]: g["rules"] for g in counts["by_group"]}
    for gid in ADS_ROLED_GROUPS:
        if gid not in by_id:
            errors.append(f"ads: src/ads/domains.json 缺少组 {gid}（README 为它单列了一行）")
        counts[f"__{gid}_rules"] = by_id.get(gid, 0)
    return counts


def ads_section_patterns(counts):
    """正文（除 `## 版本` 台账外）里的小节标题与要点行中的数字声明。

    锚点写死到具体标题文本，因此可以全文扫；`## 版本` 之后每一行记录的是**当时**的数字，
    本来就该陈旧，不进门禁。
    """
    return (
        # (锚定正则, 期望数字序列)
        (r"^### 核心广告组（(\d+) 组 / (\d+) 条展开）$",
         [counts["__core_groups"], counts["__core_rules"]]),
        (r"^### HTTPDNS / 公共 DoH（(\d+) 条展开）$", [counts["__roled_total"]]),
        (r"^### 广告子域通配层（(\d+) 条 \+ (\d+) 条家族层）$",
         [counts["wildcards"], counts["family_wildcards"]]),
        (r"^#### 数字分片家族层（(\d+) 条", [counts["family_wildcards"]]),
        (r"^- HTTPDNS/私有 DoH：", [counts["__httpdns_rules"]]),
        (r"^- 公共 DoH：", [counts["__doh_public_rules"]]),
        # 版本台账里每行记录的是「当时」的数字，不往这里加。
    )


def check_readme_numbers():
    """把 plugins/ads/README.md 里每一个计数声明钉在 build-ads 算出的数字上。

    文档正文也是数据源：加一批域名后忘了改 README 的「1479 条」，读者就会照着错的
    规模做判断。这里不重新数插件行，只信 tools/build-ads.py --stats-json 一个出口。
    """
    counts = ads_machine_counts()
    if counts is None:
        return
    ADS_NUMBER_CACHE.update({k: v for k, v in counts.items() if isinstance(v, int)})
    path = ROOT / ADS_README
    if not path.exists():
        errors.append(f"{ADS_README}: missing")
        return
    text = path.read_text(encoding="utf-8")

    checked = 0
    expectations = ads_row_expectations(counts)
    seen_labels = set()
    for num, line in enumerate(text.splitlines(), 1):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 3 or cells[1] not in expectations:
            continue
        label = cells[1]
        seen_labels.add(label)
        got = [int(x) for x in ADS_COUNT_UNIT.findall(cells[2])]
        want = expectations[label]
        if got != want:
            errors.append(
                f"{ADS_README}:{num}: 表格行 {label} 的数量声明是 {got}，"
                f"build-ads 机器算出的是 {want} —— 改文档或改数据，别让它们各自漂"
            )
        else:
            checked += 1
        for pattern, keys in ADS_ROW_PATTERNS.get(label, ()):
            m = re.search(pattern, cells[2])
            if not m:
                errors.append(
                    f"{ADS_README}:{num}: 表格行 {label} 缺少数值声明 {pattern!r}（对应 {keys}）"
                )
                continue
            got = [int(x) for x in m.groups()]
            want = [counts[key] for key in keys]
            if got != want:
                errors.append(
                    f"{ADS_README}:{num}: 表格行 {label} 的 {pattern!r} 声明 {got}，"
                    f"机器算出 {want}"
                )
            else:
                checked += 1
    for label in expectations:
        if label not in seen_labels:
            errors.append(f"{ADS_README}: 缺少数量声明行 {label}（改名要同步门禁）")

    summary = None
    for num, line in enumerate(text.splitlines(), 1):
        if line.startswith("合计："):
            if summary is not None:
                errors.append(f"{ADS_README}:{num}: 只允许一行「合计：」数量声明")
                continue
            summary = (num, line)
    if summary is None:
        errors.append(f"{ADS_README}: 找不到「合计：」数量声明行")
    else:
        num, line = summary
        for pattern, keys in ADS_SUMMARY_PATTERNS:
            m = re.search(pattern, line)
            if not m:
                errors.append(
                    f"{ADS_README}:{num}: 合计行缺少数值声明 {pattern!r}（对应 {keys}）"
                )
                continue
            got = [int(x) for x in m.groups()]
            want = [counts[key] for key in keys]
            if got != want:
                errors.append(
                    f"{ADS_README}:{num}: 合计行 {pattern!r} 声明 {got}，"
                    f"机器算出 {want}"
                )
            else:
                checked += 1

    patterns = ads_section_patterns(counts)
    matched = {pattern: False for pattern, _ in patterns}
    for num, line in enumerate(text.splitlines(), 1):
        if line.startswith("## 版本"):
            break  # 从这里起是版本台账，每一行记的是当时的数字，本来就该陈旧
        for pattern, want in patterns:
            m = re.match(pattern, line)
            if m is None:
                continue
            matched[pattern] = True
            got = [int(x) for x in m.groups()] or [int(x) for x in ADS_COUNT_UNIT.findall(line)]
            if got != want:
                errors.append(
                    f"{ADS_README}:{num}: 「{line[:60]}」声明 {got}，机器算出 {want}"
                )
            else:
                checked += 1
    for pattern, hit in matched.items():
        if not hit:
            errors.append(f"{ADS_README}: 缺少数量声明 {pattern!r}（改名要同步门禁）")

    GATE_CLAIM_COUNTS["ads"] = checked
    print(
        f"readme numbers: {checked} count claim(s) in {ADS_README} bound to "
        f"tools/build-ads.py --stats-json "
        f"(groups={counts['groups']} active_host={counts['active']} "
        f"exact={counts['host_exact']} wildcard={counts['host_wildcard']} "
        f"rules={counts['rules']} glob={counts['__glob_total']} "
        f"optional_rules={counts['rules_disabled']} "
        f"optional_ip_rewrite={counts['ip_rewrite_disabled']})"
    )


GATE_CLAIM_COUNTS: dict[str, int] = {}
# ads 那一份 build-ads 计数也缓存下来给别的文档用（同一进程内，不再多跑一次子进程）。
ADS_NUMBER_CACHE: dict[str, int] = {}
NATIVE_FIRST_DOC = "docs/loon-native-first.md"
NATIVE_FIRST_PATTERNS = (
    (r"`(\d+) 条生效 Host`", ("active_host",)),
    (r"(\d+) 个 App 插件", ("app_plugins",)),
    (r"官方文档 (\d+) 页", ("doc_pages",)),
    (r"能力表 (\d+) 条", ("cov_rows",)),
    # 红线名单也是规模数字（tools/build-ads.py --stats-json 的 redline_entries / redline_apps）。
    (r"(\d+) 条 App 红线", ("redline_entries",)),
    (r"(\d+) 个 App 的红线", ("redline_apps",)),
)
# 真机清单也讲规模：J 段插件数、正文页数、「本仓库当前 ads=x.y.z」这类版本引用、
# 以及「共 N 个（…）」——声明的个数必须等于括号里真列出的项数（纯文内自证，不需要外部出口）。
DEVICE_DOC = "docs/device-checklist.md"
DEVICE_PATTERNS = (
    (r"## J\. (\d+) 个 App 专属插件", ("app_plugins",)),
    (r"官方 (\d+) 个正文页", ("doc_pages",)),
)
DEVICE_VERSION_RE = re.compile(r"`(ads|soda|douyin)=([\d.]+)`")
DEVICE_ENUM_RE = re.compile(r"共 (\d+) 个（([^（）]*)）")
# 门禁自己的「管了 N 条声明」也是数字：文档复述它，就同样钉在本次真实计数上。
# 数字类陈述一旦被写进文档，它就和 README 的「1476 条生效 Host」是同一类东西——会漂。
GATE_SELF_REPORTS = (
    (
        "tests/README.md",
        (
            (r"文档数字门禁：ads README (\d+) 条声明", ("ads",)),
            (r"真机清单 (\d+) 条声明", ("root",)),
        ),
    ),
    (
        "docs/loon-feature-checklist.md",
        (
            (r"readme numbers: (\d+) count claim\(s\) in plugins/ads/README\.md", ("ads",)),
            (r"readme numbers: (\d+) claim\(s\) in repo-metrics", ("root",)),
            (r"doc links: (\d+) relative link", ("doc_links",)),
            (r"J section covers all (\d+)/(\d+) app plugins", ("device_covered", "device_total")),
        ),
    ),
)


def check_gate_self_report():
    """文档里「门禁管了 N 条声明」这句话，由门禁当场算出的 N 核对。"""
    if not GATE_CLAIM_COUNTS:
        return
    for rel, patterns in GATE_SELF_REPORTS:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, keys in patterns:
            if any(key not in GATE_CLAIM_COUNTS for key in keys):
                continue
            hits = list(re.finditer(pattern, text))
            if not hits:
                errors.append(f"{rel}: 缺少门禁声明 {pattern!r}")
                continue
            for hit in hits:
                got = [int(x) for x in hit.groups()]
                want = [GATE_CLAIM_COUNTS[key] for key in keys]
                if got != want:
                    errors.append(
                        f"{rel}: 「{hit.group(0)}」声明 {got}，"
                        f"本次门禁实际核对 {want}（{keys}）"
                    )


METRICS_DOC = "docs/repo-metrics.md"
# 规模页的每一句「有多少条」都应当能被机器重述。这里的每条数字都不在门禁里手写：
# 段词表来自 tokens.json，能力表来自 loon-coverage，路径数来自 bypass-audit，
# 类型数来自 ad-surface-audit，上游家数来自 app-coverage-audit 的 SOURCE_NAMES，
# 插件/App/增强层数来自 src/apps/*.json。
COVERAGE_OK_RE = re.compile(
    r"coverage ok: used=(\d+) open=(\d+) reject=(\d+) na=(\d+) undocumented=(\d+)"
)


def run_audit(args):
    proc = subprocess.run(
        [sys.executable] + [str(ROOT / a) if a.endswith(".py") else a for a in args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = proc.stdout + proc.stderr
    if proc.returncode != 0:
        errors.append(f"readme numbers: `{' '.join(args)}` failed\n" + "\n".join(out.strip().splitlines()[-4:]))
        return None
    return out


def bank_app_count():
    """银行合集里有几款 App：出处是 banks.json 的 desc 首句「覆盖A/B/C…」，不在门禁里写死。"""
    desc = json.loads((ROOT / "src/apps/banks.json").read_text(encoding="utf-8"))["desc"]
    head = re.split(r"[:：]", desc, 1)[0]
    return len([part for part in head.split("/") if part.strip()])


def root_machine_numbers():
    numbers = {}
    tokens_path = ROOT / "src/loon-docs/tokens.json"
    if not tokens_path.exists():
        errors.append(f"readme numbers: missing {tokens_path} —— 先跑 npm run tokens")
        return None
    numbers["doc_pages"] = len(json.loads(tokens_path.read_text(encoding="utf-8"))["doc_pages"])
    numbers["scheme_import_keys"] = len(SCHEME_IMPORT_KEYS)

    out = run_audit(["tools/loon-coverage.py", "--check"])
    if out is None:
        return None
    m = COVERAGE_OK_RE.search(out)
    if not m:
        errors.append("readme numbers: loon-coverage 输出里没有可解析的 coverage ok 行")
        return None
    used, openc, reject, na, undoc = (int(x) for x in m.groups())
    numbers.update(
        cov_rows=used + openc + reject + na + undoc,
        cov_used=used,
        cov_open=openc,
        cov_reject=reject,
        cov_na=na,
        cov_undoc=undoc,
    )

    out = run_audit(["tools/bypass-audit.py", "--check"])
    if out is None:
        return None
    m = re.search(r"bypass ok: (\d+) paths", out)
    if not m:
        errors.append("readme numbers: bypass-audit 输出里没有可解析的路径数")
        return None
    numbers["bypass_paths"] = int(m.group(1))

    out = run_audit(["tools/ad-surface-audit.py", "--check"])
    if out is None:
        return None
    m = re.search(r"surfaces ok: (\d+) classes", out)
    if not m:
        errors.append("readme numbers: ad-surface-audit 输出里没有可解析的类型数")
        return None
    numbers["surface_classes"] = int(m.group(1))

    spec = importlib.util.spec_from_file_location(
        "app_coverage_audit", str(ROOT / "tools/app-coverage-audit.py")
    )
    if spec is None or spec.loader is None:
        errors.append("readme numbers: cannot load tools/app-coverage-audit.py")
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    numbers["upstream_sources"] = len(set(module.SOURCE_NAMES))

    app_jsons = sorted(p for p in (ROOT / "src/apps").glob("*.json") if p.name != "_sdk.json")
    if not app_jsons:
        errors.append("readme numbers: src/apps/*.json 一个都没有")
        return None
    numbers["app_plugins"] = len(app_jsons)
    numbers["enhance_plugins"] = sum(
        1 for p in app_jsons if json.loads(p.read_text(encoding="utf-8")).get("enhance")
    )
    banks = [p for p in app_jsons if p.stem == "banks"]
    numbers["apps"] = numbers["app_plugins"] - len(banks) + (bank_app_count() if banks else 0)
    return numbers


# 每条模式都带一个唯一题注；finditer 全量比对，同一个数字在 README 里出现三次就必须三次一致。
ROOT_README_PATTERNS = (
    (r"(\d+) 个 App 插件", ("app_plugins",)),
    (r"(\d+) 个 App 专属去广告插件", ("app_plugins",)),
    (r"覆盖 (\d+) 个 App", ("apps",)),
    (r"(\d+) 个非固定 App", ("enhance_plugins",)),
    (r"官方文档 (\d+) 页", ("doc_pages",)),
    (r"(\d+) 类广告", ("surface_classes",)),
    (r"枚举 (\d+) 条「广告请求绕开整个插件」", ("bypass_paths",)),
    (r"拿 (\d+) 家上游黑名单", ("upstream_sources",)),
    (
        r"报表（(\d+) 条，探测真实用法；(\d+) 已用 / (\d+) 可用未用 / (\d+) 判死 / "
        r"(\d+) 不适用 / (\d+) 未文档化）",
        ("cov_rows", "cov_used", "cov_open", "cov_reject", "cov_na", "cov_undoc"),
    ),
)


CHECKLIST_PATTERNS = (
    (r"(\d+) 个正文页", ("doc_pages",)),
    (r"import\?plugin=encode\(url\)` 等 (\d+) 种", ("scheme_import_keys",)),
)


def bind_number_claims(rel, text, patterns, numbers):
    """按题注锚定把一份文档里的数字声明钉在机器值上；同一模式出现几次就查几次。"""
    checked = 0
    for pattern, keys in patterns:
        hits = list(re.finditer(pattern, text))
        if not hits:
            errors.append(f"{rel}: 找不到声明 {pattern!r}（对应 {[numbers[k] for k in keys]}）")
            continue
        for hit in hits:
            got = [int(x) for x in hit.groups()]
            want = [numbers[key] for key in keys]
            if got != want:
                errors.append(
                    f"{rel}: 「{hit.group(0)[:60]}」声明 {got}，机器算出 {want}（{keys}）"
                )
            else:
                checked += 1
    return checked


def check_root_readme_numbers():
    """把规模页与全功能清单的规模声明钉在各审计工具自己的输出上。"""
    numbers = root_machine_numbers()
    if numbers is None:
        return
    path = ROOT / METRICS_DOC
    if not path.exists():
        errors.append(f"{METRICS_DOC}: missing")
        return
    text = path.read_text(encoding="utf-8")
    checked = bind_number_claims(METRICS_DOC, text, ROOT_README_PATTERNS, numbers)

    checklist = ROOT / "docs/loon-feature-checklist.md"
    if not checklist.exists():
        errors.append("docs/loon-feature-checklist.md: missing")
    else:
        checked += bind_number_claims(
            "docs/loon-feature-checklist.md",
            checklist.read_text(encoding="utf-8"),
            CHECKLIST_PATTERNS,
            numbers,
        )

    # §9.7 讲的是「文档数字要钉给机器」，它自己的数字同样得钉——否则这一章本身就成了漏网的那类句子。
    native = ROOT / NATIVE_FIRST_DOC
    if not native.exists():
        errors.append(f"{NATIVE_FIRST_DOC}: missing")
    elif "active" in ADS_NUMBER_CACHE:
        merged = dict(numbers)
        merged["active_host"] = ADS_NUMBER_CACHE["active"]
        merged["redline_entries"] = ADS_NUMBER_CACHE["redline_entries"]
        merged["redline_apps"] = ADS_NUMBER_CACHE["redline_apps"]
        checked += bind_number_claims(
            NATIVE_FIRST_DOC,
            native.read_text(encoding="utf-8"),
            NATIVE_FIRST_PATTERNS,
            merged,
        )

    # 真机取证清单：同一个标准。
    device = ROOT / DEVICE_DOC
    if not device.exists():
        errors.append(f"{DEVICE_DOC}: missing")
    else:
        dtext = device.read_text(encoding="utf-8")
        checked += bind_number_claims(DEVICE_DOC, dtext, DEVICE_PATTERNS, numbers)
        for m in DEVICE_VERSION_RE.finditer(dtext):
            slug, claimed = m.group(1), m.group(2)
            path = ROOT / "plugins" / slug / f"{slug}.plugin"
            if not path.exists():
                errors.append(f"{DEVICE_DOC}: 引用了不存在的 {slug}.plugin")
                continue
            actual = parse_meta(path).get("version")
            if actual != claimed:
                errors.append(
                    f"{DEVICE_DOC}: 「{m.group(0)}」声明 {claimed}，#!version={actual}"
                )
            else:
                checked += 1
        for m in DEVICE_ENUM_RE.finditer(dtext):
            want = int(m.group(1))
            got = len(re.findall(r"`[^`]+`", m.group(2)))
            if got != want:
                errors.append(
                    f"{DEVICE_DOC}: 「{m.group(0)[:40]}…」声明 {want} 个，括号里实际列了 {got} 项"
                )
            else:
                checked += 1

    GATE_CLAIM_COUNTS["root"] = checked
    print(
        f"readme numbers: {checked} claim(s) in repo-metrics, checklist, native-first, device-checklist "
        f"bound to the auditors "
        f"(apps={numbers['apps']} app_plugins={numbers['app_plugins']} "
        f"enhance={numbers['enhance_plugins']} doc_pages={numbers['doc_pages']} "
        f"classes={numbers['surface_classes']} paths={numbers['bypass_paths']} "
        f"upstream={numbers['upstream_sources']} "
        f"coverage={numbers['cov_rows']}={numbers['cov_used']}/"
        f"{numbers['cov_open']}/{numbers['cov_reject']}/{numbers['cov_na']}/"
        f"{numbers['cov_undoc']})"
    )


DOC_LINK_GLOBS = ("README.md", "tests/README.md", "docs/*.md", "plugins/*/README.md")
MD_LINK_RE = re.compile(r"\]\((?!https?://|mailto:|loon://|#)([^)\s]*)\)")
MD_FENCE_RE = re.compile(r"```.*?```", re.S)
MD_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")


def check_doc_links():
    """`[文字](相对路径)` 本身就是「这个文件在这儿」的声明——渲染出来就是链接，藏不住。

    反引号与围栏里的路径**故意不查**：`docs/cn/` 指上游手册目录、变异实验的历史文件名也长在
    散文里，和「本仓库有这个文件」的声明在文本上无法区分（第 47/49 条同一局限）。
    链接语法自带凭证，所以只查它。
    """
    total = 0
    for pattern in DOC_LINK_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            text = MD_FENCE_RE.sub(" ", path.read_text(encoding="utf-8"))
            text = MD_CODE_SPAN_RE.sub(" ", text)
            for m in MD_LINK_RE.finditer(text):
                target = m.group(1).split("#")[0].split("?")[0]
                if not target:
                    continue
                total += 1
                if (path.parent / target).exists() or (ROOT / target).exists():
                    continue
                errors.append(
                    f"{path.relative_to(ROOT)}: 链接 ]({m.group(1)}) 指向不存在的文件"
                )
    GATE_CLAIM_COUNTS["doc_links"] = total
    print(f"doc links: {total} relative link(s) resolve (code spans/fences excluded by design)")


DEVICE_BOLD_ITEM_RE = re.compile(r"^- \[.\] \*\*([^*]+)\*\*")
APP_SLUG_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def check_device_app_coverage():
    """真机清单 J 段要逐款覆盖每个 App 插件——加了 App 忘了加判读项，等于那款从没测过。"""
    path = ROOT / DEVICE_DOC
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("## J.")), None)
    if start is None:
        errors.append(f"{DEVICE_DOC}: 找不到「## J.」App 插件段")
        return
    body = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    slugs = {p.stem for p in (ROOT / "src/apps").glob("*.json") if p.stem != "_sdk"}
    mentioned = set()
    for line in body:
        m = DEVICE_BOLD_ITEM_RE.match(line)
        if not m:
            continue
        for token in m.group(1).split("/"):
            token = token.strip().strip("`").strip()
            if APP_SLUG_TOKEN_RE.fullmatch(token):
                mentioned.add(token)
    missing = sorted(slugs - mentioned)
    if missing:
        errors.append(f"{DEVICE_DOC}: J 段缺少这些 App 的真机判读项：{' '.join(missing)}")
    unknown = sorted(mentioned - slugs)
    if unknown:
        errors.append(f"{DEVICE_DOC}: J 段引用了不存在的 App：{' '.join(unknown)}")
    GATE_CLAIM_COUNTS["device_covered"] = len(mentioned)
    GATE_CLAIM_COUNTS["device_total"] = len(slugs)
    if not missing and not unknown:
        print(f"device checklist: J section covers all {len(mentioned)}/{len(slugs)} app plugins")


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
    protected = (
        REDLINES_MODULE.protected_roots() if roots_path.exists() else set()
    )
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
                if s.startswith(("[MITM]", "hostname =", "URL-REGEX,", "response if", "response.json.jq")):
                    errors.append(
                        f"apps/{slug}: enhance line must stay commented: {s!r}"
                    )
            if not rd_has_section(plugin.parent / "README.md", "可选 MITM 增强层"):
                errors.append(f"apps/{slug}: README missing 可选 MITM 增强层 section")
            elif "QUIC 回退" not in (plugin.parent / "README.md").read_text():
                errors.append(
                    f"apps/{slug}: README must explain the QUIC fallback (MITM sees TCP only)"
                )
            for key in ("mitm_hosts", "url_regex", "sources"):
                if not enh.get(key):
                    errors.append(f"apps/{slug}: enhance.{key} empty")
            for r in enh.get("url_regex", []):
                parts = r.split(",")
                if parts[0] != "URL-REGEX" or len(parts) != 3:
                    errors.append(f"apps/{slug}: enhance url_regex malformed: {r!r}")
            rewrite_json = enh.get("rewrite_json", [])
            if rewrite_json and enh.get("scripts"):
                errors.append(
                    f"apps/{slug}: enhance response.json.jq 与 Response Script 互斥"
                    "（官方：Response Body Rewrite 命中时脚本不执行）"
                )
            for item in rewrite_json:
                if not isinstance(item, dict):
                    errors.append(f"apps/{slug}: enhance rewrite_json item must be an object")
                    continue
                url, jq = item.get("url", ""), item.get("jq", "")
                sample, note, source = item.get("sample", ""), item.get("note", ""), item.get("source", "")
                if not url.startswith("^https?://"):
                    errors.append(f"apps/{slug}: rewrite_json.url must start with ^https?://: {url!r}")
                if not jq or any(c in jq for c in "`\n\r"):
                    errors.append(f"apps/{slug}: rewrite_json.jq invalid: {jq!r}")
                if not note or not source:
                    errors.append(f"apps/{slug}: rewrite_json needs note + source: {url!r}")
                try:
                    rx = re.compile(url)
                except re.error as e:
                    errors.append(f"apps/{slug}: rewrite_json.url bad regex: {e}: {url!r}")
                    continue
                if not sample.startswith(("http://", "https://")):
                    errors.append(f"apps/{slug}: rewrite_json.sample not a full URL: {sample!r}")
                    continue
                host = (urlsplit(sample).hostname or "").lower()
                if not any(fnmatch.fnmatch(host, h.lower()) for h in enh.get("mitm_hosts", [])):
                    errors.append(
                        f"apps/{slug}: rewrite_json.sample host {host!r} not in enhance.mitm_hosts"
                    )
                if not rx.match(sample):
                    errors.append(
                        f"apps/{slug}: rewrite_json.url does not match its sample: {url!r} vs {sample!r}"
                    )
            if rewrite_json and "response.json.jq" not in (plugin.parent / "README.md").read_text():
                errors.append(f"apps/{slug}: README must document response.json.jq")
            quic_hosts = [
                h for h in enh.get("mitm_hosts", [])
                if not any(c in h for c in "*?[]:")
            ]
            raw_lines = raw.splitlines()

            def line_index(text, lines=raw_lines):
                try:
                    return lines.index(text)
                except ValueError:
                    return -1

            if enh.get("mitm_hosts") and line_index("# [MITM]") < 0:
                errors.append(f"apps/{slug}: enhance missing uncommentable '# [MITM]' header")
            rewrite_i = line_index("# [Rewrite]")
            if rewrite_json and rewrite_i < 0:
                errors.append(
                    f"apps/{slug}: enhance response.json.jq missing uncommentable '# [Rewrite]' header"
                )
            for item in rewrite_json:
                if not isinstance(item, dict):
                    continue
                want = (
                    f"# response if ${{url}} ~= /{escape_regex_slashes(item.get('url', ''))}/"
                    f" then response.json.jq(`{item.get('jq', '')}`)"
                )
                if want not in raw_lines:
                    errors.append(
                        f"apps/{slug}: generated response.json.jq line missing/!= source: {item.get('url')!r}"
                    )
                elif rewrite_i >= 0 and line_index(want) < rewrite_i:
                    errors.append(
                        f"apps/{slug}: response.json.jq must sit under the '# [Rewrite]' header"
                    )
            rule_i = line_index("# [Rule]")
            if enh.get("url_regex") and rule_i < 0:
                errors.append(
                    f"apps/{slug}: enhance URL-REGEX missing uncommentable '# [Rule]' header"
                )
            for h in quic_hosts:
                want = f"# AND,((DOMAIN-SUFFIX,{h}),(PROTOCOL,QUIC)),REJECT"
                if want not in raw_lines:
                    errors.append(
                        f"apps/{slug}: enhance host {h} missing commented QUIC fallback "
                        "(MITM only sees TCP; HTTP/3 would silently skip URL-REGEX)"
                    )
                elif rule_i >= 0 and line_index(want) < rule_i:
                    errors.append(
                        f"apps/{slug}: QUIC fallback must sit under the '# [Rule]' header"
                    )
            for r in enh.get("url_regex", []):
                want = f"# {r}"
                if rule_i >= 0 and line_index(want) < rule_i:
                    errors.append(
                        f"apps/{slug}: URL-REGEX must sit under the '# [Rule]' header"
                    )
            if enh.get("scripts"):
                script_i = line_index("# [Script]")
                if script_i < 0:
                    errors.append(
                        f"apps/{slug}: enhance scripts missing uncommentable '# [Script]' header"
                    )
                else:
                    for s in enh.get("scripts", []):
                        if line_index(f"# {s}") < script_i:
                            errors.append(
                                f"apps/{slug}: enhance script must sit under the '# [Script]' header"
                            )
            for line in raw_lines:
                s = line.strip()
                if s.startswith("AND,") and "PROTOCOL,QUIC" in s:
                    errors.append(
                        f"apps/{slug}: QUIC fallback must stay commented: {s!r}"
                    )
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


# 旧版 Rewrite / Script 语法 token：官方定位「仅维护旧配置，不再扩展」，本仓库全部走
# 3.5.1(978/983)+ 新语法。这里只查小写旧 token——[Rule] 里的 REJECT-DICT 等大写动作不受影响。
LEGACY_TOKENS = (
    r"script-path\s*=",
    r"\bhttp-(?:request|response)\s+\S",
    r"\bheader-(?:add|del|replace)\b",
    r"\bresponse-header-(?:add|del|replace)\b",
    r"\breject-(?:200|img|dict|array)\b",
    r"\b(?:mock-(?:request|response)-body|request-body-json-\w+|response-body-json-\w+)\b",
    r"\\x20",
)


def check_no_legacy_syntax():
    """插件的有效配置行不得出现旧版 Rewrite/Script 语法 token（注释行允许，用于说明来源）。"""
    hits = 0
    for path in sorted((ROOT / "plugins").glob("*/*.plugin")):
        rel = path.relative_to(ROOT)
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith(("#", ";")):
                continue
            for rx in LEGACY_TOKENS:
                if re.search(rx, line):
                    errors.append(f"{rel}:{num}: legacy syntax token {rx!r} in active line")
                    hits += 1
                    break
    if not hits:
        print("legacy syntax: 0 legacy tokens in active plugin lines")


IP_MODE_VALUES = ("v4-only", "dual", "prefer-v4", "prefer-v6", "v6-only")
IP_MODE_RX = re.compile(r"ip-mode[:=]\s*([A-Za-z0-9_-]+)")
IP_MODE_SCAN = ("docs/*.md", "tools/*.py", "tests/*.py", "plugins/*/*.plugin",
                "plugins/*/README.md", "src/apps/*.json", "README.md")


def check_ip_mode_values():
    """每个 `ip-mode:` 右值必须是官方取值表里的一个（第十八轮曾把 ipv4-only 等非法值写进探针说明，
    非法行被 Loon 忽略会让真机验证得到假阳性）。"""
    bad = 0
    for pattern in IP_MODE_SCAN:
        for path in sorted(ROOT.glob(pattern)):
            rel = path.relative_to(ROOT)
            text = path.read_text(encoding="utf-8", errors="ignore")
            for num, line in enumerate(text.splitlines(), 1):
                for value in IP_MODE_RX.findall(line):
                    if value not in IP_MODE_VALUES:
                        errors.append(f"{rel}:{num}: illegal ip-mode value {value!r} "
                                      f"(official: {'/'.join(IP_MODE_VALUES)})")
                        bad += 1
    if not bad:
        print("ip-mode values: every ip-mode right-hand value is an official one")


# 官方 MitM 页的参数表只有 hostname / ca-p12 / ca-passphrase 三行；把整站 26 个正文页
# 全扫一遍，`%APPEND%` 与 `h2` 都查不到（`h2` 只在节点 `alpn=` 与 $httpClient 选项里出现）。
# 所以插件 [MITM] 段的有效行只允许：官方键 + 下面显式登记的两个未文档化 token。
# ca-p12 / ca-passphrase 虽然是官方键，但等于把 CA 私钥塞进公开插件，永久禁止。
MITM_OFFICIAL_KEYS = ("hostname", "ca-p12", "ca-passphrase")
MITM_FORBIDDEN_KEYS = ("ca-p12", "ca-passphrase")
MITM_TOLERATED_LINES = ("h2 = true",)          # 未文档化，作「未知键被忽略」的零成本保险
MITM_TOLERATED_PREFIXES = ("%APPEND%",)        # 未文档化，Surge 的「追加而非覆盖」行首前缀


def check_mitm_surface():
    """每个插件的 [MITM] 段只允许官方三键，且私钥键绝不可出现。

    未文档化 token 必须以「整行相等 / hostname 首项」的形式出现，多一个写法就多改一次
    这里的常量——想扩散就得先过一遍评审。
    """
    sections = 0
    for path in sorted((ROOT / "plugins").glob("*/*.plugin")):
        rel = path.relative_to(ROOT)
        in_mitm = False
        for num, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if line.startswith("[") and line.endswith("]"):
                in_mitm = line.upper() == "[MITM]"
                continue
            if not in_mitm or not line or line.startswith(("#", ";")):
                continue
            sections += 1
            if line in MITM_TOLERATED_LINES:
                continue
            key = line.split("=", 1)[0].strip()
            if key not in MITM_OFFICIAL_KEYS:
                errors.append(f"{rel}:{num}: [MITM] 非官方键 {key!r}"
                              f"（官方参数表只有 {'/'.join(MITM_OFFICIAL_KEYS)}）")
                continue
            if key in MITM_FORBIDDEN_KEYS:
                errors.append(f"{rel}:{num}: [MITM] {key} 会把 CA 私钥/密码公开")
                continue
            value = line.split("=", 1)[1].lstrip()
            if "%APPEND%" in value:
                if not value.startswith(MITM_TOLERATED_PREFIXES):
                    errors.append(f"{rel}:{num}: %APPEND% 只能作为 hostname 的行首前缀")
                    continue
                value = value[len("%APPEND%"):].lstrip()
            for item in [it.strip() for it in value.split(",") if it.strip()]:
                if not re.fullmatch(r"-?[A-Za-z0-9][A-Za-z0-9.*?_-]*", item):
                    errors.append(f"{rel}:{num}: [MITM] hostname 项 {item!r} 不是主机名或 glob")
    if sections:
        print(f"mitm surface: {sections} active [MITM] line(s), keys ⊆ "
              f"{'/'.join(MITM_OFFICIAL_KEYS)} + {len(MITM_TOLERATED_LINES)} tolerated token(s)")


# 官方 Scheme 页（https://nsloon.app/docs/Scheme/）把 URL Scheme 列成两张表：
# 「常用操作」6 项 + 「导入资源」7 种资源键，通用链接就是把 `loon://` 整段换成
# `https://www.nsloon.com/openloon/`。导入地址**必须先 URL 编码**再替换 encode(url)。
# 分发层此前从没被任何门禁扫过：徽章与安装链接是用户接触插件的第一道门，写错一个
# slug 就是「点了导入，装进的是别人的插件」。这里的常量就是官方词表——想加一个新
# 操作或新资源键，必须先改这里，改这里就必须对得上官方那一页。
UNIVERSAL_PREFIX = "https://www.nsloon.com/openloon/"
SCHEME_OPS = ("on", "off", "editconfig")
SCHEME_KV_OPS = {"flowmodel": ("direct", "filter", "proxy"),
                 "proxymode": ("tun", "mix")}
SCHEME_IMPORT_KEYS = ("sub", "nodelist", "rules", "plugin", "iconset", "geoip", "parser")
SCHEME_UPDATE = "update?sub=all"
PLUGIN_URL_BASE = "https://raw.githubusercontent.com/AshNail/plugins/main/"

SCHEME_RX = re.compile(r"(?:loon://|https://www\.nsloon\.com/openloon/)[A-Za-z0-9:/?=&%_.~+-]*")

# 第二十九轮：红线约束的是「域名类拦截面」，而这种面有四种载体——`[Host]` 条目、
# `[Rule]` 顶层的 DOMAIN/DOMAIN-SUFFIX、AND 复合里**嵌套**的 DOMAIN-SUFFIX、以及覆盖面
# 比后缀更宽的 DOMAIN-KEYWORD（关键词命中的是主机名里任意一段，写成 `dns` 就连 `dns.jd.com`
# 一起捞走）。前两轮的门禁只读第一种和第二种，且用 `split(",")[0]` 取类型，于是 33 条嵌套
# 规则与 4 条关键词规则从来没有和 109 条红线比过。douyin/soda 由 node 构建器生成，
# Python 构建器看不见它们的规则行——所以这一层必须在 lint 用**产物**收口。
_RULELINES_RE = re.compile(r"^\[[A-Za-z]+\]$")


def load_redlines():
    """红线模块是唯一数据出口（构建器与 lint 都读它，不在这里复制第二份判定）。"""
    spec = importlib.util.spec_from_file_location("redlines", str(ROOT / "tools/redlines.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load tools/redlines.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REDLINES_MODULE = load_redlines()


def rule_vector_section(text):
    on = False
    for line in text.splitlines():
        s = line.strip()
        if s == "[Rule]":
            on = True
            continue
        if on and _RULELINES_RE.match(s):
            break
        if on and s and not s.startswith(("#", ";", "//")):
            yield s


def host_section_values(path):
    """产物 [Host] 段的有效左值（注释行不算——保护与红线都只管默认生效的东西）。"""
    on = False
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s == "[Host]":
            on = True
            continue
        if on and _RULELINES_RE.match(s):
            break
        if on and s and not s.startswith(("#", ";", "//")) and "=" in s:
            yield s.split("=", 1)[0].strip().lower()


def covers_protected(host, merged):
    """这条 [Host] 是否整族/黑洞了某个共享主域保护根（与 build-ads 同一个判据）。"""
    if host.startswith("*."):
        base = host[2:]
        for root in merged:
            if root == base or root.endswith("." + base):
                return root
        return None
    return host if host in merged else None


# 第三十一轮：`[MITM]` 的 hostname 名单是红线的**第四个载体**。它不黑洞主机，所以不受
# 第 27 轮那条判定管；但「银行/支付/门锁等红线域绝不允许进 [MITM] hostname」这句话一直只
# 写在真机清单的散文里。解密比拦截更值得警惕（证书固定/风控的 App 一旦进了 hostname，
# 用户取消注释就是断 App），所以这一层要在产物上算出来，而不是等人记得。
_SECTION_HEAD = re.compile(r"^#?\s*\[([A-Za-z]+)\]")


def mitm_hostname_entries(path):
    """产出 (是否注释, hostname 项)；`[MITM]` 段头本身可能是注释态（整层默认关）。"""
    on = False
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = raw.strip()
        m = _SECTION_HEAD.match(s)
        if m:
            on = m.group(1) == "MITM"
            continue
        if not on or not s:
            continue
        body = s.lstrip("#").strip()
        if not body.startswith("hostname") or "=" not in body:
            continue
        for item in body.split("=", 1)[1].replace("%APPEND%", "").split(","):
            item = item.strip().lower()
            if item:
                yield s.startswith("#"), item


def check_mitm_reach():
    """每个插件的 [MITM] hostname 都要和红线比过（注释行也查——它就是给用户取消注释的）。"""
    module = REDLINES_MODULE
    entries = module.load_app_redlines()
    apps = {}
    for path in sorted((ROOT / "src/apps").glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("slug"):
            apps[data["slug"]] = data
    reachable = 0
    bad = 0

    def fail(message):
        nonlocal bad
        bad += 1
        errors.append(message)

    for path in sorted(ROOT.glob("plugins/*/*.plugin")):
        rel = path.relative_to(ROOT)
        slug = path.parent.name
        enhance = ((apps.get(slug) or {}).get("enhance") or {}).get("mitm_hosts") or []
        declared = {h.lower() for h in enhance}
        rendered = set()
        for commented, item in mitm_hostname_entries(path):
            rendered.add(item)
            if slug in apps and not commented:
                fail(
                    f"{rel}: [MITM] hostname {item!r} 是默认生效的——按 App 插件的增强层"
                    "整段默认注释是仓库纪律（不装证书 = 永不生效）"
                )
            for entry in entries:
                if not module.mitm_reaches(item, entry):
                    continue
                reachable += 1
                if entry["slug"] != slug:
                    fail(
                        f"{rel}: [MITM] hostname {item!r} 罩住 {module.describe(entry)}——"
                        "别的 App 声明绝不碰的主机，不许出现在本插件的解密名单里"
                    )
                elif not declared:
                    fail(
                        f"{rel}: [MITM] hostname {item!r} 罩住本 App 自己的红线 {entry['domain']}，"
                        "而该 App 没有声明 enhance.mitm_hosts——没有增强层就是「这个 App 做了"
                        "证书固定/风控」的判决，取消注释即断 App（见真机清单的固定 App 红线）"
                    )
        if slug in apps and declared != rendered:
            fail(
                f"{rel}: enhance.mitm_hosts 与产物 [MITM] hostname 不等——"
                f"只在源里有 {sorted(declared - rendered)}，只在产物里有 {sorted(rendered - declared)}"
            )
    if not bad:
        print(
            f"mitm reach: {len(list(ROOT.glob('plugins/*/*.plugin')))} plugin(s) 的 hostname 名单"
            f"与 {len(entries)} 条红线交叉，罩住红线 {reachable} 处，全部落在「本 App 自己声明的"
            "默认注释增强层」里"
        )


_SECTION_HEAD = re.compile(r"^#?\s*\[([A-Za-z]+)\]")


def section_lines(path, want):
    """产出 (是否注释, 去掉缩进的原文)；段头本身可以是注释态（`# [MITM]` 整层默认关）。"""
    on = False
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = raw.strip()
        m = _SECTION_HEAD.match(s)
        if m:
            on = m.group(1) == want
            continue
        if on and s:
            yield s.startswith("#"), s


FILTER_RX = re.compile(r"~=\s*(/.*?/)\s*then")


def regex_host_tail(rx):
    r"""把 `^https?://<主机正则>/<路径正则>` 拆成（主机段原文, 路径段原文）。

    括号按深度处理，所以 `(?:a|b)/path` 的主机段是整串交替、路径段是 `/path`；
    括号**内**的 `/`（如 `dsp\/retrieve`）不会提前切断主机段。
    """
    rx = rx.replace("\\/", "/")
    i = rx.find("://")
    if i < 0:
        return None, None
    rest = rx[i + 3 :]
    seg = ""
    k = 0
    depth = 0
    while k < len(rest):
        ch = rest[k]
        if ch == "\\":
            seg += rest[k : k + 2]
            k += 2
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                break
            depth -= 1
        elif ch == "/" and depth == 0:
            break
        seg += ch
        k += 1
    return seg, rest[k:]


def expand_alt(seg):
    """把 `(?:a|b|c)`（含可选组 `(?:x|)`）展开成字面候选，逐层直到没有括号。"""
    out = [seg]
    for _ in range(12):
        nxt = []
        done = True
        for item in out:
            # 捕获组 / 非捕获组 + 组后的可选量词：`(g-)?` 与 `(?:a|b)` 都要展开。
            # 早先只认 `(?:`，普通捕获组整条面会被悄悄跳过（真机日志轮发现的漏判）。
            m = re.search(r"\(((?:[^()\\]|\\.)*)\)([?*+]|\{\d+(?:,\d*)?\})?", item)
            if m:
                done = False
                inner = m.group(1)
                if inner.startswith("?:"):
                    inner = inner[2:]
                parts = inner.split("|")
                quant = m.group(2)
                if quant in ("?", "*", "{0,1}"):
                    parts = parts + [""]
                for part in parts:
                    nxt.append(item[: m.start()] + part + item[m.end() :])
                continue
            # 单原子可选：`v?` / `\.?` / `[..]?` → {原子, 空}
            m = re.search(r"(\\?[A-Za-z0-9_.-]|\[[^\]]*\])\?", item)
            if m:
                done = False
                atom = m.group(1)
                for part in (atom, ""):
                    nxt.append(item[: m.start()] + part + item[m.end() :])
                continue
            nxt.append(item)
        out = nxt
        if done:
            break
    return [item for item in out if "(" not in item]


def regex_host_glob(seg):
    r"""主机段正则 → 可与 `[MITM]` hostname 通配比较的形态。

    `*`/`+` 一律折成 `*`（否则 `[0-9-]*` 变成「一个字符 + 任意」会把分片族读窄），
    `\.` 还原成 `.`，字符类按 Loon hostname 的 `?` 语义保留单字符位。
    """
    s = re.sub(r"\[[^\]]*\][*+]", "*", seg)
    s = re.sub(r"\[[^\]]*\]", "?", s)
    s = s.replace("\\.", ".").replace("\\", "")
    s = s.replace(".?", ".").replace("*?", "*")
    s = re.sub(r"[*+]{2,}", "*", s)
    s = s.replace("+", "*")
    return s.lower()


# 「生效的正则面罩到了本插件 [MITM] 名单之外的主机」的显式认罪层。
# 键钉到**具体那一条正则**（插件 / 段 / 原文），不是钉到一个主机形态：认罪的是这条面，
# 而不是这个域——收窄或删掉它，这条认罪项立刻变成「今天没被任何生效面命中」而报错。
PANGLE_SHARD_NOTE = (
    "穿山甲（Pangle）分片主机族：正则写作 `(?:[a-z0-9.-]+\\.)?zijieapi\\.com`，而 Loon 的 "
    "hostname 是枚举式的（`ads?-normal*.zijieapi.com` 罩不到任意分片）。路径段就是边界——"
    "不在 `[MITM]` 名单里的主机不解密、这条面不命中，所以最坏是**静默不生效**而不是误伤别家；"
    "真机若取证到某个分片主机在发开屏请求，正解是把那条主机补进 hostname 名单，不是放宽本项"
)
REGEX_SCOPE_EXCEPTIONS = {
    ("douyin", "Script",
     r"^https?:\/\/(?:[a-z0-9.-]+\.)?zijieapi\.com\/api\/ad\/(?:splash\/|v[0-9]+\/(?:ack\/)?splash\/)"):
        PANGLE_SHARD_NOTE + "（`blockSplashAd` 的开屏族）",
    ("douyin", "Script",
     r"^https?:\/\/(?:[a-z0-9.-]+\.)?zijieapi\.com\/(?:api\/ad\/|api\/incentive\/marketing\/done)"):
        PANGLE_SHARD_NOTE + "（`debugLog` 观测族，只读日志不改响应，越界面本身无副作用）",
    ("soda", "Script",
     r"^https?:\/\/(?:[a-z0-9.-]+\.)?zijieapi\.com\/api\/ad\/(?:splash\/|v[0-9]+\/(?:ack\/)?splash\/)"):
        PANGLE_SHARD_NOTE + "（与抖音共用 `src/common/splash-ad.js`，家族差异只有日志前缀）",
}


def regex_host_covered(glob, items):
    """正则推出的主机形态，能否被 hostname 名单里某一项**当作模式**描出来。

    方向是保守的：只有名单项罩得住这个主机形态才算覆盖。反过来比（拿正则主机当模式去描名单项）
    会把「正则写 `*.zijieapi.com`、名单里只有一条 `ad.zijieapi.com`」判成已覆盖——那正是这条
    门禁最不该犯的错，因为它放过的恰好是「没解密却宣称拦得住」。
    """
    return any(glob == item or fnmatch.fnmatch(glob, item) for item in items)


def check_regex_scopes():
    """生效的正则匹配面按「罩到主机还是罩到路径」分类——两种各有约束，不许沉默放过。"""
    module = REDLINES_MODULE
    entries = module.load_app_redlines()
    surfaces = https_surfaces = host_wide = exempted = 0
    used = set()
    bad = 0

    def fail(message):
        nonlocal bad
        bad += 1
        errors.append(message)

    for path in sorted(ROOT.glob("plugins/*/*.plugin")):
        rel = path.relative_to(ROOT)
        slug = path.parent.name
        mitm = {}
        for commented, s in section_lines(path, "MITM"):
            body = s.lstrip("#").strip()
            if not body.startswith("hostname") or "=" not in body:
                continue
            for item in body.split("=", 1)[1].replace("%APPEND%", "").split(","):
                item = item.strip().lower()
                if item:
                    mitm.setdefault(item, commented)
        active_mitm = [item for item, commented in mitm.items() if not commented]
        for sect in ("Rule", "Script", "Rewrite"):
            for commented, s in section_lines(path, sect):
                if commented:
                    continue
                body = s.lstrip("#").strip()
                if sect == "Rule":
                    if not body.startswith("URL-REGEX,"):
                        continue
                    regexes = [body.split(",", 1)[1].rsplit(",", 1)[0]]
                else:
                    regexes = [m.group(1)[1:-1] for m in FILTER_RX.finditer(body)]
                for rx in regexes:
                    seg, tail = regex_host_tail(rx)
                    if seg is None:
                        continue
                    if re.match(r"^\[0-9\]\+?\(|^\\\[\[0-9a-fA-F:]", seg):
                        continue  # IP 字面量（IPv4 的 [0-9] 类、IPv6 的 \[….\.\]）不受 hostname 约束
                    globs = [regex_host_glob(c) for c in expand_alt(seg)]
                    if not globs and "." in seg:
                        fail(
                            f"{rel}: {sect} 段的正则主机段 {seg[:60]!r} 展开不出任何候选——"
                            "门禁宁可报错也不许静默跳过一条面（跳过=这条面永远不受检查）"
                        )
                        continue
                    if not any("." in g or "*" in g for g in globs):
                        continue  # 其余没有主机形态的面，不受 hostname 约束
                    surfaces += 1
                    if not rx.lower().startswith("^https"):
                        continue  # 纯 http:// 不需要解密，本条约束与它无关
                    https_surfaces += 1
                    if not (tail or "").strip("/"):
                        host_wide += 1
                        for g in globs:
                            for entry in entries:
                                if fnmatch.fnmatch(entry["domain"], g):
                                    fail(
                                        f"{rel}: {sect} 段的 {rx[:60]!r} 没有路径段=整主机面，"
                                        f"却罩住 {module.describe(entry)}——域名类拦截面必须过红线判定"
                                    )
                    outside = sorted(g for g in globs if not regex_host_covered(g, active_mitm))
                    if not outside:
                        continue
                    key = (slug, sect, rx)
                    if key in REGEX_SCOPE_EXCEPTIONS:
                        used.add(key)
                        exempted += 1
                        continue
                    fail(
                        f"{rel}: {sect} 段按 HTTPS 匹配的正则 {rx[:70]!r} 罩在本插件生效 [MITM] "
                        f"名单之外（{'、'.join(outside)}）——不装证书这条面永不命中，「已拦截」是假宣告；"
                        "要么把主机补进 hostname 名单，要么在 REGEX_SCOPE_EXCEPTIONS 里逐条写明理由"
                    )
    if not bad:
        print(
            f"regex scopes: {surfaces} 条生效正则面（HTTPS 面 {https_surfaces} 条 / 整主机面 {host_wide} 条"
            f"须过红线判定 / 罩在 [MITM] 之外并已认罪 {exempted} 条）"
        )
    for key in sorted(set(REGEX_SCOPE_EXCEPTIONS) - used):
        fail(
            f"REGEX_SCOPE_EXCEPTIONS: {key[0]}/{key[1]} 的 {key[2][:50]!r} 今天没有被任何生效面命中——"
            "越界已经消失，认罪项就该删掉（写旧的例外等于给未来的越界预留后门）"
        )


# 第三十三轮：luna 接口有两个主机，且都还在被真实 App 使用。
# 2026-10-29 真机日志（Luna 21.4.0，build 100214010，23 小时）里
# `beta-luna.douyin.com/luna/*` 881 条请求、`api.qishui.com/luna/*` 5 条；
# 旧版 34 条单主机绑定当天只匹配到 1 条（task/page）。绑定面不是「写了一条
# 正则」就算数——它必须绑在流量真的会去的那个主机上。抖音插件合法的只绑
# beta-luna，所以这条奇偶性只对 soda 成立，主机对必须显式登记。
LUNA_HOST_PARITY = {
    "soda": ("api.qishui.com", "beta-luna.douyin.com"),
}


def check_luna_host_parity():
    """每个 luna 绑定必须同时显式写全该 App 的真实主机对，少一个就是静默失效。"""
    checked = 0
    bad = 0
    for slug, hosts in LUNA_HOST_PARITY.items():
        path = ROOT / "plugins" / slug / f"{slug}.plugin"
        if not path.exists():
            errors.append(f"plugins/{slug}/{slug}.plugin: missing (luna host parity)")
            bad += 1
            continue
        tokens = tuple(host.replace(".", r"\.") for host in hosts)
        for sect in ("Rewrite", "Script"):
            for commented, s in section_lines(path, sect):
                if commented:
                    continue
                for m in FILTER_RX.finditer(s):
                    rx = m.group(1)[1:-1]
                    if "/luna" not in rx.replace("\\/", "/"):
                        continue
                    checked += 1
                    missing = [h for h, t in zip(hosts, tokens) if t not in rx]
                    if missing:
                        bad += 1
                        errors.append(
                            f"plugins/{slug}/{slug}.plugin: {sect} 段的 luna 绑定只绑了 "
                            f"{'、'.join(h for h in hosts if h not in missing)}，缺 "
                            f"{'、'.join(missing)}——真机日志里两个主机都在承接 luna 流量，"
                            "少绑一个就是「插件在跑、清理不到」的静默失效"
                        )
        active = {
            item for commented, item in mitm_hostname_entries(path) if not commented
        }
        missing_mitm = [h for h in hosts if h not in active]
        if missing_mitm:
            bad += 1
            errors.append(
                f"plugins/{slug}/{slug}.plugin: [MITM] 生效 hostname 缺少 "
                f"{'、'.join(missing_mitm)}——luna 绑定写全了也解不了密"
            )
    if not bad:
        total_hosts = sum(len(hosts) for hosts in LUNA_HOST_PARITY.values())
        print(
            f"luna host parity: {checked} active luna binding(s) all bind "
            f"{total_hosts} attested host(s) "
            f"({' + '.join(sorted({h for hosts in LUNA_HOST_PARITY.values() for h in hosts}))})"
        )


def check_rule_vectors():
    """每个插件的每条生效 [Rule] 都要和红线比过；没登记过的新匹配面不许沉默通过。"""
    module = REDLINES_MODULE
    entries = module.load_app_redlines()
    plugins = sorted(ROOT.glob("plugins/*/*.plugin"))
    lines = items = nested = hits = 0
    seen_types = set()
    for path in plugins:
        rel = path.relative_to(ROOT)
        for line in rule_vector_section(path.read_text(encoding="utf-8", errors="ignore")):
            lines += 1
            seen_types |= module.rule_type_tokens(line)
            own = module.rule_match_items(line)
            items += len(own)
            if line.upper().startswith(("AND,", "OR,")):
                nested += len(own)
            for kind, target, item in module.rule_redline_hits(line, entries):
                hits += 1
                errors.append(
                    f"{rel}: 生效规则 {line[:80]!r} 的 {kind} 匹配项 {target!r} 命中 "
                    f"{module.describe(item)}——红线只管默认生效的东西，要留就注释掉并写明理由"
                )
    unknown = sorted(seen_types - module.RULE_TYPES)
    for token in unknown:
        errors.append(
            f"[Rule] 出现未归类的匹配面 {token!r}：它碰不碰得到红线，"
            "必须先在 tools/redlines.py 的分类表里写明（域名类=受红线约束，非域名类=记账但仍可比对）"
        )
    hand = module.hand_protected_roots()
    derived = module.redline_roots(entries)
    merged = module.protected_roots(entries)
    blocked = 0
    for path in plugins:
        rel = path.relative_to(ROOT)
        for host in host_section_values(path):
            root = covers_protected(host, merged)
            if root:
                blocked += 1
                errors.append(
                    f"{rel}: 生效 [Host] {host!r} 整族/黑洞了共享主域 {root!r}"
                    "（保护名单 = 手写表 ∪ App 红线派生根）"
                )
    if not unknown and not hits and not blocked:
        print(
            f"rule vectors: {len(plugins)} plugin(s) / {lines} active [Rule] line(s) / "
            f"{items} domain-scoped match item(s) ({nested} of them nested in composites) / "
            f"{len(seen_types)} rule type(s) all classified against {len(entries)} red line(s)"
        )
        print(
            f"protected roots: {len(hand)} 手写 + {len(derived - hand)} 由 App 红线派生 "
            f"= {len(merged)}，0 条生效 [Host] 命中它"
        )


def check_scheme_links():
    """README/docs 里每条 loon:// 与通用链接都必须落在官方 Scheme 页的语法内，
    且每个 App 插件自己的 README 必须链接到 **自己** 的 .plugin。"""
    seen = 0
    own_links = {}
    for path in sorted(list(ROOT.glob("README.md")) + list(ROOT.glob("plugins/*/README.md"))
                       + list(ROOT.glob("docs/*.md"))):
        rel = path.relative_to(ROOT)
        for num, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for url in SCHEME_RX.findall(line):
                if url.endswith(("?", "=", "/")) or "encode" in url:
                    continue                          # 引用官方模板，不是可用链接
                seen += 1
                tail = url[len("loon://"):] if url.startswith("loon://") \
                    else url[len(UNIVERSAL_PREFIX):]
                head, _, query = tail.partition("?")
                if head in SCHEME_OPS and not query:
                    continue
                if tail == SCHEME_UPDATE:
                    continue
                # `flowmodel=` / `proxymode=` 是「操作名自带 = 取值」，没有 `?`
                op, eq, val = head.partition("=")
                if eq and op in SCHEME_KV_OPS:
                    if query:
                        errors.append(f"{rel}:{num}: `{op}` 的取值直接跟在 `=` 后，不该再带 `?`")
                    elif val in SCHEME_KV_OPS[op]:
                        continue
                    else:
                        errors.append(f"{rel}:{num}: `{op}` 取值 {val!r} 不在官方表 "
                                      f"{'/'.join(SCHEME_KV_OPS[op])}")
                    continue
                if head != "import":
                    errors.append(f"{rel}:{num}: Scheme 操作 {head!r} 官方查不到")
                    continue
                key, eq, val = query.partition("=")
                if not eq or key not in SCHEME_IMPORT_KEYS:
                    errors.append(f"{rel}:{num}: `import?` 资源键 {key!r} 不在官方 7 种里")
                    continue
                if not re.fullmatch(r"[A-Za-z0-9._~%-]+", val):
                    errors.append(f"{rel}:{num}: import?{key} 的地址没有 URL 编码（官方要求先编码）")
                    continue
                target = unquote(val)
                if not target.startswith(("https://", "http://")):
                    errors.append(f"{rel}:{num}: import?{key} 解码后不是 http(s) 地址 {target!r}")
                    continue
                if key == "plugin":
                    if not target.startswith(PLUGIN_URL_BASE):
                        errors.append(f"{rel}:{num}: 导入地址不在本仓 raw 前缀下 {target!r}")
                        continue
                    m = re.fullmatch(r"plugins/([^/]+)/([^/]+)\.plugin",
                                     target[len(PLUGIN_URL_BASE):])
                    if not m or m.group(1) != m.group(2):
                        errors.append(f"{rel}:{num}: 导入地址不是 <slug>/<slug>.plugin 形态 {target!r}")
                        continue
                    slug = m.group(1)
                    if not (ROOT / "plugins" / slug / f"{slug}.plugin").exists():
                        errors.append(f"{rel}:{num}: 导入地址指向不存在的插件 {slug!r}")
                        continue
                    own_links.setdefault(slug, set()).add(str(rel))
                    # 表格里「某一行」的徽章必须指向该行自己的 slug
                    if "|" in line:
                        row_slugs = set(re.findall(r"`([a-z0-9][a-z0-9-]*)\.plugin`", line))
                        if row_slugs and row_slugs != {slug}:
                            errors.append(f"{rel}:{num}: 行内标注 {sorted(row_slugs)} 但链接指向 {slug!r}")
    for path in sorted((ROOT / "plugins").glob("*/*.plugin")):
        slug = path.stem
        own = f"plugins/{slug}/README.md"
        if own not in own_links.get(slug, set()):
            errors.append(f"{own}: 没有一条 `import?plugin=` 链接指向自己的 {slug}.plugin")
    if seen:
        print(f"scheme links: {seen} loon:// / openloon link(s) checked against the official "
              f"Scheme page grammar ({len(own_links)} plugin(s) self-linked)")


check_shared_scripts()
check_switch_labels()
check_argument_schema()
check_args_generated()
check_quic_count()
check_encoding_guard()
check_script_safety()
check_bypass_dns_guard()
check_no_legacy_syntax()
check_ip_mode_values()
check_mitm_surface()
check_mitm_reach()
check_regex_scopes()
check_luna_host_parity()
check_rule_vectors()
check_ads_family()
check_readme_numbers()
check_root_readme_numbers()
check_doc_links()
check_device_app_coverage()
check_gate_self_report()
check_app_plugins()
check_scheme_links()
print(f"lint errors: {len(errors)}")
for err in errors:
    print(" -", err)
sys.exit(1 if errors else 0)
