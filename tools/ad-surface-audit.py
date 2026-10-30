#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad-surface-audit.py —— 按「广告类型」而不是「Loon 功能」统计覆盖率

为什么要换轴
------------
`loon-coverage.py` 回答的是「Loon 的功能用了多少」，它的分母是**功能**。
但用户真正关心的是「广告还剩多少」，分母是**广告类型**。两者不是一回事：
Loon 的功能利用率到了 70%，仍可能有整类广告（贴片、直播挂件、Push）一条没碰。

这个脚本把分母换成广告面，做三件事：
  1. 定义 19 类主流 App 广告，按「可切断点」而不是「长相」分族；
  2. 对每类声明**理论可达档**与**当前档**，并用正则从插件/脚本里探测证据；
  3. 算出覆盖率，并把「下一步能到哪」一起算出来——方案因此是可验收的。

档位
----
  full     广告请求被切断或响应被清空，UI 无广告、无空位、无重试风暴
  strong   广告内容不出现，可能留空位/骨架屏/降级文案
  partial  只在部分 App 或部分场景生效
  weak     只能降低填充率或减少曝光，广告仍会出现
  none     无效：Loon 结构上碰不到

覆盖率 = Σ权重(当前) / Σ权重(理论可达)，理论可达为 none 的类**不进分母**
（Push、DAI 音频这类本来就不该由 Loon 背锅）。

用法
----
  python3 tools/ad-surface-audit.py            # 打印矩阵
  python3 tools/ad-surface-audit.py --write    # 生成 docs/ad-type-strategy.md
  python3 tools/ad-surface-audit.py --check    # CI：证据缺失或文档过期即失败
"""

import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MD = os.path.join(ROOT, "docs", "ad-type-strategy.md")

DOC = "https://nsloon.app/docs"

WEIGHT = {"full": 4, "strong": 3, "partial": 2, "weak": 1, "none": 0}
LABEL = {
    "full": "完全",
    "strong": "强效",
    "partial": "部分",
    "weak": "弱效",
    "none": "无效",
}
MARK = {"full": "●●●●", "strong": "●●●○", "partial": "●●○○", "weak": "●○○○", "none": "○○○○"}


# ---------------------------------------------------------------------------
# 语料
# ---------------------------------------------------------------------------

def read(path):
    try:
        return io.open(path, encoding="utf-8").read()
    except (IOError, OSError):
        return ""


class Corpus(object):
    """按 glob 缓存文件内容；区分「原始文本」与「剥离注释后的有效文本」。"""

    def __init__(self):
        self._raw = {}

    def raw(self, pattern):
        key = ("raw", pattern)
        if key not in self._raw:
            files = sorted(glob.glob(os.path.join(ROOT, pattern), recursive=True))
            self._raw[key] = {os.path.relpath(p, ROOT): read(p) for p in files}
        return self._raw[key]

    def live(self, pattern):
        """配置文件去 # 整行注释，脚本去 /* */ 与 // 注释。"""
        key = ("live", pattern)
        if key not in self._raw:
            out = {}
            for name, text in self.raw(pattern).items():
                if name.endswith(".plugin"):
                    text = "\n".join(
                        l for l in text.split("\n") if not l.lstrip().startswith("#")
                    )
                elif name.endswith(".js"):
                    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
                    text = re.sub(r"(?m)^\s*//.*$", "", text)
                out[name] = text
            self._raw[key] = out
        return self._raw[key]


CORPUS = Corpus()


def probe(glob_pattern, rx, raw=False):
    """在 glob 命中的文件里找 rx。返回命中的文件名列表。"""
    files = CORPUS.raw(glob_pattern) if raw else CORPUS.live(glob_pattern)
    hits = []
    cre = re.compile(rx)
    for name, text in files.items():
        if cre.search(text):
            hits.append(name)
    return hits


# ---------------------------------------------------------------------------
# 19 类广告面
# ---------------------------------------------------------------------------
# attack 里每条是 (层, 写法示例, 这一步买到了什么)
# probes 里每条是 (glob, 正则, 是否必须在原始文本上匹配)
#   —— 注释行也要算证据的（比如「可选组默认注释」），raw=True

SURFACES = [
    # ======================= 展示位 =======================
    dict(
        id="splash", brief="冷启动整屏，SDK 域或自家中台", family="展示位", name="开屏广告",
        apps="抖音 / 小红书 / 知乎 / 微博 / 工具类",
        signal="冷启动 0~5 秒的整屏位。两条来源：联盟 SDK 开屏（穿山甲 "
               "`ad.zijieapi.com`、优量汇 `gdt.qq.com`）与自家广告中台（业务域，"
               "如 `api.qishui.com/luna/advert/splash/brand/retrieve`）。响应里带素材 "
               "URL、曝光上报地址、倒计时与摇一摇参数。",
        protocol="半标准",
        attack=[
            ("[Host]", "ad.zijieapi.com = 127.0.0.1", "SDK 拿不到填充，直接走「无广告」分支，最彻底"),
            ("[Rule]", "DOMAIN-WILDCARD,ads[0-9]-normal*.zijieapi.com,REJECT（TF 3.5.3+，默认注释）", "兜住 SDK 的数字分片族，一条顶十几条"),
            ("[Script]", "response if ${url} ~= /\\/splash\\/brand\\/retrieve/ then script(sanitize)", "业务域开屏只能剥响应，删掉 brand 对象"),
            ("[Rewrite]", "request ... then reject_dict(200)", "上报接口回 `{}`，避免 SDK 因上报失败重试"),
        ],
        ceiling="strong", achieved="strong", next_to="strong",
        probes=[
            ("plugins/ads/ads.plugin", r"ad\.zijieapi\.com\s*=\s*127\.0\.0\.1", False),
            ("plugins/soda/soda.plugin", r"advert\\?/splash", False),
        ],
        limits="上次启动预拉的素材会缓存展示一次；摇一摇/扭一扭是传感器事件，"
               "Loon 碰不到；无广告时部分 App 仍占 3 秒「跳过」按钮。",
        next="",
    ),
    dict(
        id="feed", brief="列表第 N 项，与内容同构", family="展示位", name="信息流广告",
        apps="抖音 / 小红书 / 微博 / 知乎 / 新闻类",
        signal="列表接口把广告当第 N 个 item 返回，与内容**同构**（同 schema）。"
               "判据字段：`is_ad`、`ad_info`、`type=ad`、`cell_type`、`creative_id`、"
               "`log_extra`。素材走共享 CDN，域名拦不住。",
        protocol="私有",
        attack=[
            ("[Script]", "response if ${url} ~= /\\/feed\\// then script(sanitize)", "遍历数组按字段删除，唯一有效层"),
            ("[Host]", "只拦素材/上报域", "减少下载量，但列表里的空位还在"),
        ],
        ceiling="full", achieved="partial", next_to="partial",
        probes=[
            ("plugins/soda/soda.plugin", r"feed\\?/", False),
            ("plugins/douyin/douyin.plugin", r"\[Script\]", False),
        ],
        limits="字段名每个 App 不同；删多了会破分页游标（`cursor`/`has_more` 与广告数耦合）；"
               "广告与推荐混在同一 `cards` 数组时，删除会导致索引错位。",
        next="文档不再承诺「抽公共模块就能提档」：soda/douyin 的规则表都已到各自端点上限，再提档只能加第三个 App（要抓包读它的 JSON）。没有代码可写。",
        blocked="结构性：私有 JSON 字段名逐 App 不同，提档 = 多适配一个 App，不是多写一段代码。",
    ),
    dict(
        id="rewarded", brief="看广告换权益，独立 SDK 域", family="展示位", name="激励视频",
        apps="游戏 / 工具 / 小说 / 音乐（看广告换权益）",
        signal="独立 SDK 域，先 `config` 再 `retrieve` 素材，播放完回调 `/reward/verify` 发奖。"
               "素材是 m3u8/mp4，走联盟 CDN。",
        protocol="半标准",
        attack=[
            ("[Host]", "pangolin.snssdk.com = 127.0.0.1", "连素材都不下载，最省流量"),
            ("[Rule]", "DOMAIN-WILDCARD,ads-*,REJECT（TF 3.5.3+，默认注释）", "兜住聚合平台的中转域"),
            ("[Script]", "response if ${url} ~= /incentive\\/config/ then script(sanitize)", "自营激励位才需要"),
        ],
        ceiling="full", achieved="strong", next_to="strong",
        probes=[
            ("plugins/ads/ads.plugin", r"pangolin\.snssdk\.com\s*=\s*127\.0\.0\.1", False),
            ("plugins/soda/soda.plugin", r"incentive/config", False),
        ],
        limits="拦了就拿不到奖励——与「保奖励」目标互斥，必须做模式切换；"
               "部分 App 检测到「无广告」会把任务置为不可用。",
        next="Mintegral 的真实请求域（rayjump / mtgglobals / mintegral.net）已补，这是本轮最大的一个缺口；剩下的聚合长尾没有可核实的请求域，不再凭品牌名猜。",
        blocked="聚合长尾只剩「没有公开请求域证据」的厂商：AdTiming 的 SDK 端点未公开，Smaato 走 smaato.net（已在清单）、Ogury 走 ogury.io（已在清单）。**按品牌名补 .com 会拦到官网却不命中广告请求**——要补只能抓包，抓不到就不补。",
    ),
    dict(
        id="interstitial", brief="择机弹出，与激励共用 SDK", family="展示位", name="插屏 / 半插屏",
        apps="游戏 / 工具 / 小说",
        signal="SDK 域，`/interstitial`、`/fullscreen`；预加载后择机弹出，常带 5 秒跳过。"
               "与激励视频共用 SDK 连接池，域名往往相同。",
        protocol="半标准",
        attack=[
            ("[Host]", "与激励视频同一批 SDK 域", "一次拦截同时干掉插屏与激励"),
            ("[Rule]", "DOMAIN-WILDCARD,adserver.*,REJECT（TF 3.5.3+，默认注释）", "补充长尾 SDK"),
        ],
        ceiling="full", achieved="strong", next_to="strong",
        probes=[
            ("plugins/ads/ads.plugin", r"gdt\.qq\.com\s*=\s*127\.0\.0\.1", False),
            ("plugins/ads/ads.plugin", r"mintegral", False),
        ],
        limits="端上预加载的插屏（上次会话缓存）会展示一次；关闭按钮误触是端上逻辑，"
               "拦网络改不了。",
        next="与激励视频同一批 SDK 域，随 Mintegral 补域一起覆盖。",
        blocked="聚合长尾只剩「没有公开请求域证据」的厂商：AdTiming 的 SDK 端点未公开，Smaato 走 smaato.net（已在清单）、Ogury 走 ogury.io（已在清单）。**按品牌名补 .com 会拦到官网却不命中广告请求**——要补只能抓包，抓不到就不补。",
    ),
    dict(
        id="banner", brief="常驻条，30~60 秒刷新", family="展示位", name="Banner / 原生 Banner",
        apps="工具 / 小说 / 资讯 / 免费游戏",
        signal="常驻位，`banner`、`ad_size`、`pos_id` 参数，30~60 秒自动刷新。"
               "部分 App 用 WebView 渲染（联盟 JS），部分用原生 View。",
        protocol="半标准",
        attack=[
            ("[Host]", "联盟素材与投放域", "刷新请求拿不到填充，位空着"),
            ("[Rule]", "DOMAIN-WILDCARD,bannerads.*,REJECT（TF 3.5.3+，默认注释层）", "长尾联盟（正式版靠 [Host] 逐条兜底）"),
        ],
        ceiling="full", achieved="strong", next_to="strong",
        probes=[
            # bannerads.* 通配已降为默认注释层（需 3.5.3），不计入正式版生效证据；
            # banner 的 strong 由常开 [Host]（googlesyndication 等联盟素材/投放域）承担。
            ("plugins/ads/ads.plugin", r"googlesyndication", False),
        ],
        limits="广告容器仍占高度，会出现空白条；WebView 渲染的 banner 需要额外拦联盟 JS 域。",
        next="与激励/插屏共用联盟域；WebView 渲染的 banner 另算（见 H5，那一类到 partial 就是顶）。",
        blocked="聚合长尾只剩「没有公开请求域证据」的厂商：AdTiming 的 SDK 端点未公开，Smaato 走 smaato.net（已在清单）、Ogury 走 ogury.io（已在清单）。**按品牌名补 .com 会拦到官网却不命中广告请求**——要补只能抓包，抓不到就不补。",
    ),
    dict(
        id="preroll", brief="VAST/VMAP 清单 + 素材 CDN", family="展示位", name="视频贴片（前贴 / 中贴 / 后贴）",
        apps="爱奇艺 / 腾讯视频 / 优酷 / B 站 / YouTube",
        signal="标准协议：VAST / VMAP 广告清单（XML）+ 素材 CDN。清单域与正片域常常分离"
               "（FreeWheel `fwmrm.net`、SpringServe、Tremor），但国内长视频多与业务同域。"
               "中贴按时间轴插入，走播放器时间线而不是新请求。",
        protocol="标准协议",
        attack=[
            ("[Host]", "fwmrm.net / springserve.com 等广告服务器", "清单拉不到，播放器走无广告分支"),
            ("[Rewrite]", "response.body.mock_file 返回空 VAST", "格式固定，比脚本安全；但 mock 不支持 `application/xml`"),
            ("[Rule]", "URL-REGEX 拦 /\\.vmap|\\.vast/", "HTTPS 下需要 MITM 才看得到路径"),
        ],
        ceiling="partial", achieved="weak", next_to="weak",
        probes=[
            ("plugins/ads/ads.plugin", r"fwmrm\.net\s*=\s*127\.0\.0\.1", False),
        ],
        limits="**DAI/SSAI**（服务端拼接）把广告混进正片流，客户端拿到的是一条连续流，无法切分；"
               "国内长视频的广告接口与业务同域，必须 MITM + 逐 App 定制；"
               "`response.body.mock_file` 的 content-type 白名单里没有 `application/xml`，"
               "严格校验的播放器会拒绝空清单。",
        next="清单域已补 FreeWheel / Sizmek（独立域，零风险）；剩下要提档只能对"
             "国内长视频做 MITM 定制——投入产出比低，暂不做。",
        blocked="国内长视频的广告接口与业务同域，必须 MITM + 逐 App 定制；DAI/SSAI 把广告混进正片流，客户端拿到的是一条连续流，无法切分。",
    ),
    dict(
        id="search", brief="结果位混排，带「广告」角标", family="展示位", name="搜索广告",
        apps="淘宝 / 京东 / 美团 / 抖音 / 百度",
        signal="搜索接口响应里混排 `ads`、`promotion`、`commercial` 字段；"
               "结果第 1/3/5 位带「广告」角标；联想词带 `ad_type`。与自然结果同构。",
        protocol="私有",
        attack=[
            ("[Script]", "response if ${url} ~= /\\/search/ then script(sanitize)", "同域，只有脚本能剥"),
            ("[Rule]", "USER-AGENT 拦竞价上报（⚠️ 前提未满足：无 [MITM]）", "只减少回传，不影响展示"),
        ],
        ceiling="strong", achieved="partial", next_to="partial",
        probes=[
            ("plugins/soda/soda.plugin", r"search/track|search-block", False),
        ],
        limits="与自然结果同构，字段随版本变；剥错会丢搜索结果；"
               "「品牌专区」是整块 UI，删数据会留空白。",
        next="soda 的 search/track、search-block、search-categories 已在 sanitize 的 URL 表里，字段剥离与 feed 共用同一套；再提档同样只能加 App。",
        blocked="结构性：搜索结果是同构混排，删哪一条要靠 App 自己的角标字段，无法通用。",
    ),
    dict(
        id="livecommerce", brief="小黄车 / 挂件 / 红包雨", family="展示位", name="直播 / 电商挂件",
        apps="抖音 / 快手 / 淘宝直播 / 小红书",
        signal="直播间 `room/enter`、`room/init` 返回 `goods`、`promotion`、`popup`、"
               "`task`、`floating`；小黄车、讲解卡、红包雨、悬浮挂件。",
        protocol="私有",
        attack=[
            ("[Script]", "response if ${url} ~= /room\\/(enter|init)/ then script(sanitize)", "删挂件字段，需逐 App 定制"),
        ],
        ceiling="strong", achieved="none", next_to="none",
        probes=[],
        limits="电商是核心变现，剥离可能触发风控；`goods` 与直播间初始化强耦合，"
               "删了可能直接进不去直播间；红包雨是端上动画。",
        next="不做。",
        blocked="风控风险：goods 与直播间初始化强耦合，删挂件字段可能直接进不去直播间；红包雨是端上动画，删网络无效。投入产出比不成立。",
    ),

    dict(
        id="upsell", brief="会员/升级弹窗，限时优惠", family="展示位", name="推广弹窗 / 会员引导",
        apps="免费 App / 会员制服务 / 工具类",
        signal="`/commerce/upsells`、`/v2/upsell`、`/promotion/popup`；返回弹窗配置、价格档、"
               "挽留文案与倒计时。触发点多在看广告、退出、点升级入口时。与会员/支付同域。",
        protocol="私有",
        attack=[
            ("[Script]", "response if ${url} ~= /commerce\\/upsell/ then script(sanitize)", "删掉弹窗配置，UI 不再弹"),
            ("[Host]", "不适用", "与会员/支付同域，DNS 一拦就断会员页与支付"),
        ],
        ceiling="strong", achieved="partial", next_to="partial",
        probes=[
            ("plugins/soda/soda.plugin", r"commerce\\?/upsell", False),
        ],
        limits="与会员状态、支付流程同域同接口，剥错会让会员页空白；部分 App 用 WebView 渲染，"
               "弹窗内容在页面里；「限时优惠」倒计时是端上逻辑，删网络改不了。",
        next="soda 的 /commerce/upsells 与 /commerce/v2/upsell 已覆盖，douyin 的 cleanUpsell 覆盖 upsell_map。两边都到各自端点上限，再提档只能加 App。",
        blocked="结构性：弹窗配置与会员状态、支付流程同域同接口，每加一个 App 都要重新确认哪些键安全。",
    ),

    # ======================= 触达面 =======================
    dict(
        id="push", brief="APNs 系统通道，Loon 看不到", family="触达面", name="Push 推送广告",
        apps="几乎所有免费 App",
        signal="APNs（443/TCP 或 QUIC，5223 作回退）或厂商通道；payload 内含 `ad`、`promo`、"
               "`deeplink`。Loon 看不到 payload——APNs 是系统级双向 TLS 长连接。",
        protocol="系统通道",
        attack=[
            ("—", "无", "Loon 无法解密 APNs，也无法只拦「广告类」推送"),
        ],
        ceiling="none", achieved="none", next_to="none",
        probes=[],
        limits="**结构不可达**。唯一办法是系统设置关通知，或在 App 内关「营销推送」。"
               "拦 push 注册域等于全断推送，不做。",
        next="",
    ),
    dict(
        id="webview", brief="页面内联盟 JS 与内联位", family="触达面", name="H5 / WebView 广告",
        apps="所有内嵌网页的 App",
        signal="页面里的 GPT/Prebid/联盟 JS：`googlesyndication`、`doubleclick`、"
               "`criteo`、`taboola`、`outbrain`；内联 `<ins class=\"adsbygoogle\">`、"
               "弹窗、插页、浮层、贴片。",
        protocol="标准协议",
        attack=[
            ("[Host]", "googlesyndication.com = 127.0.0.1", "联盟 JS 拉不到，广告位不渲染（覆盖大部分）"),
            ("[Script]", "response 注入 `display:none` CSS", "需要 MITM 所有站点，证书风险远大于收益"),
        ],
        ceiling="partial", achieved="partial", next_to="partial",
        probes=[
            ("plugins/ads/ads.plugin", r"googlesyndication", False),
        ],
        limits="**内联广告位是 HTML 的一部分**，DNS 层拦不到；注入 CSS 要 MITM 任意站点，"
               "代价不可接受；WebView 里还可能有 App 自营广告（同域）。",
        next="",
    ),
    dict(
        id="audio", brief="DAI 混流，不可切分", family="触达面", name="音频广告",
        apps="Spotify / 喜马拉雅 / 小宇宙 / 播客",
        signal="音频贴片、口播；DAI（动态广告插入）在服务端把广告混进音频流，"
               "客户端拿到的是连续音频；或独立广告域返回 mp3/aac。",
        protocol="标准协议",
        attack=[
            ("[Host]", "独立音频广告域（少）", "能拦到的只有独立域那一小部分"),
        ],
        ceiling="weak", achieved="none", next_to="none",
        probes=[],
        limits="**DAI 不可切分**；口播是主播内容的一部分；音频 App 的广告素材常与内容同 CDN。",
        next="不做。写进「结构不可达」清单，避免以后重复讨论。",
        blocked="DAI 把广告混进音频流，客户端拿到的是连续音频；口播是主播内容的一部分。结构不可切分。",
    ),
    dict(
        id="ott", brief="大屏 SDK，证书固定多", family="触达面", name="OTT / CTV 大屏广告",
        apps="Apple TV / Android TV / 智能电视",
        signal="大屏 App 的开屏 + 贴片 + 屏保；独立 SDK 域较多（`ads.roku.com`、"
               "`samsungads.com`、`lgads.tv`）。同一份 ads 插件在 tvOS 生效。",
        protocol="标准协议",
        attack=[
            ("[Host]", "ads.roku.com = 127.0.0.1", "同一份清单直接复用"),
            ("[Rule]", "DOMAIN-WILDCARD（TF 3.5.3+，默认注释层）", "补长尾大屏 SDK"),
        ],
        ceiling="partial", achieved="weak", next_to="weak",
        probes=[
            ("plugins/ads/ads.plugin", r"ads\.roku\.com\s*=\s*127\.0\.0\.1", False),
        ],
        limits="大屏 App 多用证书固定（MITM 直接失败）；部分走系统播放器，"
               "广告由播放器而不是 App 拉取；`#!system` 已含 tvOS，但覆盖面小于移动端。",
        next="CTV 广告服务器（FreeWheel / Smart / Tremor / Roku）已在清单里；国内大屏（芒果 / CIBN / 银河 / NewTV）的广告与播控同域，整域拦会断播放，不做。",
        blocked="国内大屏广告域与播控同域，零证书无法只拦广告；证书固定又让 MITM 大面积失败。",
    ),

    # ======================= 数据面 =======================
    dict(
        id="adconfig", brief="广告位总闸，决定后面所有展示", family="数据面", name="投放配置 / 素材预拉取",
        apps="所有带广告 SDK 的 App",
        signal="`/ads/config`、`/advert/retrieve`、`/sdk/config`；返回广告位开关、"
               "频次上限、素材 URL 列表。是「后面所有展示」的总闸。",
        protocol="半标准",
        attack=[
            ("[Script]", "response 清空 ads 数组", "总闸关掉，后续展示自然没有"),
            ("[Rewrite]", "then reject_dict(200)", "更轻，但 SDK 可能按间隔重拉"),
        ],
        ceiling="full", achieved="strong", next_to="strong",
        probes=[
            ("plugins/soda/soda.plugin", r"luna\\?/ads\\?/", False),
        ],
        limits="返回空后 SDK 可能按固定间隔重拉（要有节奏地返回空，而不是断开）；"
               "部分 App 把 config 与会员状态耦合，清空会误判。",
        next="聚合 SDK 的 config 域已随本轮补域进清单；再往上要「把 REJECT-DICT 换成带最小合法包络的空配置」，那需要 MITM + 逐 App 包络，零证书插件做不到。",
        blocked="最小合法包络必须改响应体，只有 MITM 能做；零证书插件只能拦域，不能改包。",
    ),
    dict(
        id="beacon", brief="曝光/点击回传，影响结算", family="数据面", name="曝光 / 点击上报",
        apps="所有带广告的 App",
        signal="`/report`、`/track`、`/impression`、`/click`、`/log`；GET 带 base64 参数"
               "或 POST protobuf；fire-and-forget，失败会进本地队列重试。",
        protocol="私有",
        attack=[
            ("[Rule]", "URL-REGEX,...,REJECT-DICT", "回 200 + `{}`，SDK 认为已落库，清空重试队列"),
            ("[Rewrite]", "then reject_dict(200)", "同 URL 更精确的请求层版本"),
            ("[Rule]", "REJECT-DROP", "防重试风暴；代价是首次超时略慢"),
        ],
        ceiling="full", achieved="strong", next_to="strong",
        probes=[
            ("plugins/ads/ads.plugin", r"REJECT-DICT", False),
            ("plugins/soda/soda.plugin", r"reject_dict\(200\)", False),
        ],
        limits="拦上报不改变已展示的广告；价值在省电/省流量/降重试，不在「少看广告」；"
               "误拦业务埋点会让 App 统计异常。",
        next="上报路径特征已覆盖明文那两条与 /vN/event|log|track/...；HTTPS 上报要看到路径必须 MITM，零证书插件看不到。",
        blocked="[Rule] 的 URL-REGEX 在 HTTPS 下需要 MITM 才取得到路径；零证书只能靠域名，看不到 /impression。",
    ),
    dict(
        id="attribution", brief="MMP / 竞价，影响 eCPM", family="数据面", name="归因 / 画像 / 竞价",
        apps="所有投放过广告的 App",
        signal="MMP（AppsFlyer / Adjust / Kochava / Singular）、设备指纹、"
               "bidding（`/bid`、`/auction`、`/openrtb`）。",
        protocol="标准协议",
        attack=[
            ("[Host]", "可选组，默认注释", "会断安装归因与渠道 ROI，只能按需开"),
        ],
        ceiling="partial", achieved="weak", next_to="weak",
        probes=[
            ("plugins/ads/ads.plugin", r"appsflyer\.com\s*=\s*127\.0\.0\.1", True),
        ],
        limits="拦归因会断安装归因/渠道 ROI；bidding 被拦只是让瀑布流跳到下一个源，"
               "广告仍会出现——它影响的是 eCPM，不是「有没有广告」。",
        next="不做开关化。",
        blocked="机制不可达：Loon 的 [Argument] 只作用于 [Script]/[Rewrite] 的 enable，管不到 [Host] 与静态 [Rule]（仓库在 soda.plugin 第 57 行已记录该结论）。要让用户能开关，只能拆成独立插件，与单插件 All-in-One 冲突。",
    ),

    # ======================= 绕路面 =======================
    dict(
        id="httpdns", brief="绕过系统 DNS，让 Host 失效", family="绕路面", name="HTTPDNS / 私有 DoH 绕过",
        apps="抖音 / 快手 / B 站 / 美团 / 各大厂",
        signal="`/d`、`/resolve`、`/squery`、`httpdns` 域名；绕过系统 DNS 直接拿 IP，"
               "让 `[Host]` 完全失效。",
        protocol="半标准",
        attack=[
            ("[Rule]", "DOMAIN-KEYWORD,httpdns,REJECT-DROP", "未知域兜底，丢包避免重试风暴"),
            ("[Rule]", "USER-AGENT,httpdns*,REJECT（⚠️ 前提未满足）", "UA 特征兜底：UA 是请求头，无 [MITM] 时看不到"),
            ("[Host]", "已知 HTTPDNS 端点 = 127.0.0.1", "最精确"),
        ],
        ceiling="full", achieved="full", next_to="full",
        probes=[
            ("plugins/ads/ads.plugin", r"DOMAIN-KEYWORD\s*,\s*httpdns", False),
            ("plugins/ads/ads.plugin", r"USER-AGENT\s*,\s*https?dns", False),
        ],
        limits="IP 直连的 HTTPDNS 需要 IP-CIDR（默认注释，因为接入点 IP 会变）；"
               "拦太狠会让没有回退逻辑的 App 直接断网。",
        next="",
    ),
    dict(
        id="quic", brief="UDP 443，MITM 失效", family="绕路面", name="QUIC / HTTP3 绕过",
        apps="Google 系 / 字节系 / 部分大厂",
        signal="UDP 443，加密传输，规则层看不到 SNI 之后的路径；"
               "`[MITM]` 对 QUIC 无效，脚本根本不执行。",
        protocol="标准协议",
        attack=[
            ("[Rule]", "PROTOCOL,QUIC,REJECT", "强制回退 TCP，MITM 才有机会介入"),
        ],
        ceiling="full", achieved="full", next_to="full",
        probes=[
            ("plugins/douyin/douyin.plugin", r"PROTOCOL\s*,\s*QUIC", False),
        ],
        limits="回退增加首屏 RTT；部分 App 在 QUIC 失败后会短暂重试，产生额外请求。",
        next="",
    ),
    dict(
        id="hijack", brief="中间设备插入，已进正文", family="绕路面", name="链路劫持 / 运营商插入广告",
        apps="所有走明文的场景",
        signal="HTTP 明文响应被中间设备插入 `<script>`；DNS 被劫持到广告落地页；"
               "常见于公共 Wi-Fi 与部分运营商。",
        protocol="私有",
        attack=[
            ("[General]", "doh-server = https://223.5.5.5/dns-query", "从源头防 DNS 劫持"),
            ("[Rule]", "DEST-PORT,853,REJECT", "阻断自带 DoT 绕过"),
        ],
        ceiling="partial", achieved="partial", next_to="partial",
        probes=[
            ("plugins/ads/ads.plugin", r"doh-server\s*=", False),
        ],
        limits="**已插入的 HTML 正文无法剥离**——除非 MITM 全站 + 正则替换，风险极高；"
               "只能靠 HTTPS + DoH 让插入点变少。",
        next="",
    ),
]

FAMILIES = ["展示位", "触达面", "数据面", "绕路面"]
FAMILY_NOTE = {
    "展示位": "用户看得见的那块。拦截目标：让广告位没有东西可渲染。",
    "触达面": "不占页面也能到你（推送、H5、音频、大屏）。",
    "数据面": "不直接展示，但决定「展示什么、算不算钱」。",
    "绕路面": "让上面三层失效的东西：加密 DNS、QUIC、链路劫持。",
}


# ---------------------------------------------------------------------------
# 评估
# ---------------------------------------------------------------------------

def evaluate():
    rows = []
    drift = []
    for s in SURFACES:
        hits = []
        missing = []
        for glob_pattern, rx, raw in s["probes"]:
            h = probe(glob_pattern, rx, raw=raw)
            if h:
                hits.extend(h)
            else:
                missing.append("%s ~ /%s/" % (glob_pattern, rx))
        # 声明「有实现」（achieved 非 none）就必须能探到证据
        if s["achieved"] != "none" and missing:
            drift.append("%s（%s）：声明 %s 但探不到证据 — %s"
                         % (s["name"], s["id"], s["achieved"], missing[0]))
        # 声明「完全没做」却探到了，说明结论过期
        if s["achieved"] == "none" and hits:
            drift.append("%s（%s）：声明 none 但检测到实现 @ %s"
                         % (s["name"], s["id"], ",".join(sorted(set(hits))[:3])))
        # 档位必须自洽：当前不能超过上限，下一步不能超过上限、不能低于当前
        if WEIGHT[s["achieved"]] > WEIGHT[s["ceiling"]]:
            drift.append("%s（%s）：当前 %s 高于上限 %s"
                         % (s["name"], s["id"], s["achieved"], s["ceiling"]))
        if WEIGHT[s["next_to"]] > WEIGHT[s["ceiling"]]:
            drift.append("%s（%s）：下一步 %s 高于上限 %s"
                         % (s["name"], s["id"], s["next_to"], s["ceiling"]))
        if WEIGHT[s["next_to"]] < WEIGHT[s["achieved"]]:
            drift.append("%s（%s）：下一步 %s 低于当前 %s"
                         % (s["name"], s["id"], s["next_to"], s["achieved"]))
        # blocked 与 next_to 必须互为表里：
        #   承诺还能提档（next_to > achieved）→ 不许写「做不了」的理由；
        #   没到上限却停在原地（achieved < ceiling 且 next_to == achieved）→ 必须写清为什么。
        blocked = s.get("blocked", "")
        if WEIGHT[s["next_to"]] > WEIGHT[s["achieved"]] and blocked:
            drift.append("%s（%s）：承诺提到 %s 却同时声明做不到（%s）"
                         % (s["name"], s["id"], s["next_to"], blocked[:24]))
        if (WEIGHT[s["next_to"]] == WEIGHT[s["achieved"]]
                and WEIGHT[s["achieved"]] < WEIGHT[s["ceiling"]]
                and not blocked):
            drift.append("%s（%s）：距上限还有 %s，却没有 blocked 说明为什么不做"
                         % (s["name"], s["id"], s["ceiling"]))
        rows.append(dict(s, hits=sorted(set(hits)), blocked=blocked))
    return rows, drift


def stats(rows, key):
    num = sum(WEIGHT[r[key]] for r in rows if WEIGHT[r["ceiling"]] > 0)
    den = sum(WEIGHT[r["ceiling"]] for r in rows if WEIGHT[r["ceiling"]] > 0)
    return num, den, (100.0 * num / den if den else 0.0)


def stats_by_family(rows, key, family):
    items = [r for r in rows if r["family"] == family and WEIGHT[r["ceiling"]] > 0]
    num = sum(WEIGHT[r[key]] for r in items)
    den = sum(WEIGHT[r["ceiling"]] for r in items)
    return num, den, (100.0 * num / den if den else 0.0)


def stats_by_protocol(rows, key):
    out = {}
    for r in rows:
        if WEIGHT[r["ceiling"]] == 0:
            continue
        slot = out.setdefault(r["protocol"], [0, 0])
        slot[0] += WEIGHT[r[key]]
        slot[1] += WEIGHT[r["ceiling"]]
    return out


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def render_matrix(rows):
    lines = []
    lines.append("| # | 广告类型 | 族 | 一句话特征 | 协议 | 上限 | 现状 | 下一步 |")
    lines.append("|---:|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        sig = r["brief"].replace("|", "\\|")
        nxt = r["next_to"]
        delta = ""
        if WEIGHT[nxt] > WEIGHT[r["achieved"]]:
            delta = " → **%s**" % LABEL[nxt]
        lines.append("| %d | %s | %s | %s | %s | %s | %s%s |"
                     % (i, r["name"], r["family"], sig, r["protocol"],
                        MARK[r["ceiling"]], MARK[r["achieved"]], delta))
    return lines


def render_surface(r, idx):
    lines = []
    lines.append("#### %d. %s" % (idx, r["name"]))
    lines.append("")
    lines.append("**特征**　%s" % r["signal"])
    lines.append("")
    lines.append("**典型**　%s　·　**协议形态**　%s" % (r["apps"], r["protocol"]))
    lines.append("")
    lines.append("| 层 | 规则思路 | 买到了什么 |")
    lines.append("|---|---|---|")
    for layer, how, gain in r["attack"]:
        esc = lambda t: t.replace("|", "\\|")
        lines.append("| `%s` | %s | %s |" % (esc(layer), esc(how), esc(gain)))
    lines.append("")
    lines.append("**覆盖**　上限 `%s`（%s）· 现状 `%s`（%s）%s"
                 % (r["ceiling"], LABEL[r["ceiling"]], r["achieved"], LABEL[r["achieved"]],
                    ("· 下一步可到 `%s`（%s）" % (r["next_to"], LABEL[r["next_to"]])
                     if WEIGHT[r["next_to"]] > WEIGHT[r["achieved"]] else "")))
    lines.append("")
    lines.append("**局限**　%s" % r["limits"])
    if r["blocked"]:
        lines.append("")
        lines.append("**为什么停在这**　%s" % r["blocked"])
    elif r["next"]:
        lines.append("")
        lines.append("**下一步**　%s" % r["next"])
    lines.append("")
    return lines


def render_md(rows):
    cur_num, cur_den, cur_pct = stats(rows, "achieved")
    nxt_num, _, nxt_pct = stats(rows, "next_to")
    reachable = [r for r in rows if WEIGHT[r["ceiling"]] > 0]
    dead = [r for r in rows if WEIGHT[r["ceiling"]] == 0]

    L = []
    L.append("# 按广告类型分类的去除策略")
    L.append("")
    L.append("> 本文由 `tools/ad-surface-audit.py --write` 生成，**不要手改**。")
    L.append("> 改分类或结论请改脚本里的 `SURFACES`，再跑一次；`--check` 会拦住过期文档。")
    L.append("")
    L.append("## 0. 一页结论")
    L.append("")
    L.append("分母不是「Loon 有多少功能」，而是「广告有多少种」。%d 类里 **%d 类**有明确手段，"
             "%d 类（Push）结构上不可达——后者不计入分母，否则任何方案都到不了 100%%。"
             % (len(rows), len(reachable), len(dead)))
    L.append("")
    L.append("- 当前覆盖 **%.0f%%**（%d/%d）。**这已经是当前手段的真值**——"
             "剩下的 %d 分全部卡在结构性原因上，不是「还没做」。"
             % (cur_pct, cur_num, cur_den, cur_den - cur_num))
    # 已到顶的类从数据里取，不写死——写死过一次，改档位后就自相矛盾了
    topped = [r["name"] for r in rows
              if WEIGHT[r["ceiling"]] > 0 and r["achieved"] == r["ceiling"]]
    L.append("- 已经到顶的 **%d 类**：%s。这些类的上限就是现状，再投入没有档位收益。"
             % (len(topped), "、".join(topped)))
    L.append("- 最大的缺口集中在**同域私有 JSON**：信息流、搜索、直播挂件。"
             "它们与内容同构、同域，DNS 与规则层全部失效，只能 MITM + 逐 App 适配。"
             "**每多覆盖一个 App 才多一分，不是多写一段代码。**")
    L.append("- 结构上做不到的有 7 件事（**不是 7 类**，是跨类的限制）：Push、DAI 音频、"
             "端上缓存素材、传感器交互、正文劫持、证书固定、素材同 CDN。"
             "它们散落在多个类里，写进第 5 节，避免以后重复讨论。")
    # 零证书天花板：只用 Host/Rule/General 的类，其 ceiling 权重之和 / 总权重
    l1_only = [r for r in rows if r["attack"]
               and all(a[0] in ("[Host]", "[Rule]", "[General]") for a in r["attack"])
               and WEIGHT[r["ceiling"]] > 0]
    l1_cap = sum(WEIGHT[r["ceiling"]] for r in l1_only)
    L.append("- **零证书方案的天花板是 %.0f%%**（%d/%d），与上面的 %.0f%% 是两个口径："
             "前者只用 ads 插件（不装 CA、不开 MITM），后者要靠 soda/douyin 的证书层做逐 App 适配。"
             "**同一个仓库，两套成本，两个数**——别拿 %.0f%% 去要求零证书方案。"
             % (100.0 * l1_cap / cur_den if cur_den else 0, l1_cap, cur_den,
                cur_pct, cur_pct))
    L.append("")
    L.append("> **口径**：所有档位按**纯去广告模式**评价。保奖励模式（`rewardSafe=true`）下，"
             "激励视频与激励浏览会被主动放行，那是有意为之，不算覆盖缺口。")
    L.append(">")
    L.append("> 档位：`●●●●` 完全 · `●●●○` 强效 · `●●○○` 部分 · `●○○○` 弱效 · `○○○○` 无效。")
    L.append("> 覆盖率 = Σ权重(现状) / Σ权重(理论上限)；理论上限为「无效」的类不进分母。")
    L.append("")
    L.append("## 1. 为什么按「可切断点」分类")
    L.append("")
    L.append("按长相分（开屏/信息流/激励）只对用户有意义，对拦截没有指导性——"
             "同一个「开屏」，来自 SDK 的可以 DNS 一次拦死，来自自家中台的必须 MITM 剥 JSON，"
             "两者的手段和上限完全不同。")
    L.append("")
    L.append("所以这里用两层：**族**按「广告在链路的哪一段」分，**类**按用户感知的形态分。"
             "每类再标注**协议形态**——这一列决定能不能用 mock：")
    L.append("")
    L.append("| 协议形态 | 含义 | 首选手段 |")
    L.append("|---|---|---|")
    L.append("| 标准协议 | VAST / VMAP / OpenRTB / MRAID，格式公开且稳定 | `response.body.mock_file` 返回空清单，比脚本安全 |")
    L.append("| 半标准 | 联盟 SDK 的 JSON，有公开文档但会随版本变 | `[Host]` 黑洞优先；必须改内容时才用脚本 |")
    L.append("| 私有 | 自家业务 JSON，与内容同构同域 | 只能 MITM + 脚本，逐 App 适配 |")
    L.append("| 系统通道 | APNs、厂商推送 | 无手段 |")
    L.append("")
    for fam in FAMILIES:
        items = [r for r in rows if r["family"] == fam]
        L.append("**%s**（%d 类）—— %s" % (fam, len(items), FAMILY_NOTE[fam]))
        L.append("")
    L.append("## 2. 总览矩阵")
    L.append("")
    L.extend(render_matrix(rows))
    L.append("")
    L.append("## 3. 逐类研判")
    L.append("")
    for fam in FAMILIES:
        items = [r for r in rows if r["family"] == fam]
        L.append("### %s（%d 类）" % (fam, len(items)))
        L.append("")
        for i, r in enumerate(items, 1):
            L.extend(render_surface(r, i))
    L.append("## 4. 按层归因：谁在承担覆盖率")
    L.append("")
    layer_count = {}
    for r in rows:
        if WEIGHT[r["ceiling"]] == 0:
            continue
        for layer, _how, _gain in r["attack"]:
            if layer == "—":
                continue
            layer_count[layer] = layer_count.get(layer, 0) + 1
    L.append("| 层 | 涉及类数（含补充） | 说明 |")
    L.append("|---|---:|---|")
    note = {
        "[Host]": "独立广告域的主力。零证书、HTTPS/QUIC 通吃，是性价比最高的一层。",
        "[Rule]": "补 `[Host]` 表达不了的通配与特征（`DOMAIN-WILDCARD`、`URL-REGEX`、`PROTOCOL`）。",
        "[Script]": "同域私有 JSON 的唯一解。必须 MITM，且要处理压缩与包络。",
        "[Rewrite]": "轻量替代：能 `reject_dict` 就不写脚本，能 mock 就不写正则。",
        "[General]": "只管 DNS 防泄漏，不直接拦广告。",
    }
    for layer, n in sorted(layer_count.items(), key=lambda kv: -kv[1]):
        L.append("| `%s` | %d | %s |" % (layer, n, note.get(layer, "")))
    L.append("")
    top = max(layer_count.items(), key=lambda kv: kv[1])
    L.append("结论：**`%s` 参与的类最多（%d 类），但它只能覆盖「域名可分离」的那一半**。"
             "剩下的一半压在 `[Script]` 上，而脚本必须逐 App 写——这就是覆盖率的边际成本"
             "为什么在上升。一个反直觉的推论：**域名清单的价值在下降，App 适配的价值在上升**，"
             "但前者的边际成本几乎为零，后者每加一个 App 都要重新读一遍它的 JSON。"
             % (top[0], top[1]))
    L.append("")
    L.append("按协议形态看：")
    L.append("")
    L.append("| 协议形态 | 当前覆盖 | 为什么是这个数 |")
    L.append("|---|---:|---|")
    proto_cur = stats_by_protocol(rows, "achieved")
    proto_why = {
        "标准协议": "上限被「素材与内容同 CDN」「服务端拼接」压住，多数只能到 `partial`；"
                    "能拿的分基本拿到了。",
        "半标准": "DNS 黑洞对联盟 SDK 最有效，已接近该形态的天花板；"
                  "剩下的差距是聚合平台长尾。",
        "私有": "只能 MITM + 逐 App 适配。分子取决于「做了几个 App」，"
                "分母是「所有带信息流的 App」——这是当前最贵的一段。",
        "系统通道": "Loon 碰不到，理论上限为「无效」，不进分母。",
    }
    for proto in ["标准协议", "半标准", "私有", "系统通道"]:
        if proto not in proto_cur:
            L.append("| %s | — | %s |" % (proto, proto_why[proto]))
            continue
        n, d = proto_cur[proto]
        L.append("| %s | %.0f%% | %s |" % (proto, 100.0 * n / d if d else 0, proto_why[proto]))
    L.append("")
    L.append("标准协议类的上限普遍只有 `partial`/`weak`——因为标准协议解决的是"
             "「广告怎么描述」，不解决「素材和内容同 CDN」；"
             "私有类的上限反而更高（`full`/`strong`），因为一旦 MITM 进去，字段是可以删干净的。"
             "**这说明「协议越标准越好拦」是个错觉：好拦的不是协议，是域名。**")
    L.append("")
    L.append("## 5. 结构不可达清单")
    L.append("")
    L.append("下面这些不是「还没做」，是「用 Loon 做不了」。写清楚是为了不再重复投入：")
    L.append("")
    L.append("| 做不到的事 | 为什么 | 替代方案 |")
    L.append("|---|---|---|")
    L.append("| 拦 Push 里的广告 | APNs 是系统级双向 TLS 长连接，Loon 看不到 payload | 系统设置关通知 / App 内关营销推送 |")
    L.append("| 切分 DAI 音频广告 | 广告在服务端混进音频流，客户端拿到的是连续流 | 无 |")
    L.append("| 去掉端上已缓存的素材 | 上次会话预拉，本次展示不产生网络请求 | 清 App 缓存 / 重装 |")
    L.append("| 关掉摇一摇 / 扭一扭 | 传感器事件，不经网络 | 无 |")
    L.append("| 剥已插入的 HTML 正文 | 中间设备插入的 `<script>` 已在明文正文里 | 强制 HTTPS + DoH，从源头减少 |")
    L.append("| 绕过证书固定的 App | MITM 握手直接失败，脚本不执行 | 只用 DNS 层（`[Host]`/`[Rule]`） |")
    L.append("| 按域名区分贴片素材 | 广告与正片同 CDN 同签名 | 只能拦广告清单（VAST/VMAP）域 |")
    L.append("")
    L.append("## 6. 三层递进方案")
    L.append("")
    L.append("覆盖率不是一次性买断的，它按「证书成本」分三层。每层的边际收益递减：")
    L.append("")
    L.append("| 层 | 证书 | 能覆盖的类 | 当前覆盖 | 代价 |")
    L.append("|---|---|---|---|---|")
    l2 = [r for r in rows if any(a[0] in ("[Script]", "[Rewrite]") for a in r["attack"])]
    l1_only = [r for r in rows if r["attack"]
               and all(a[0] in ("[Host]", "[Rule]", "[General]") for a in r["attack"])
               and WEIGHT[r["ceiling"]] > 0]
    n1 = sum(WEIGHT[r["achieved"]] for r in l1_only)
    d1 = sum(WEIGHT[r["ceiling"]] for r in l1_only)
    L.append("| L1 域名层 | 不需要 | %d 类（纯独立域：联盟展示位 + 绕路面） | %.0f%%（%d/%d） | 零；HTTPS/QUIC 通吃 |"
             % (len(l1_only), 100.0 * n1 / d1 if d1 else 0, n1, d1))
    L.append("| L2 内容层 | 需要 MITM | %d 类（含同域 JSON 或需改内容） | 只有 2 个 App 做了定制 | 证书 + 逐 App 适配 + 压缩/包络处理 |"
             % len(l2))
    L.append("| L3 端上 | 不需要 | Push、传感器、端上缓存、悬浮窗 | 不可达 | 只能靠系统设置或 App 内开关 |")
    L.append("")
    L.append("两层可叠加（一类广告常常同时用 `[Host]` 拦素材、用 `[Script]` 剥列表），"
             "所以上面的类数相加大于 18。")
    L.append("")
    L.append("**提升覆盖率的正确顺序**：先把 L1 的域名清单补全（成本最低、收益线性），"
             "再对「高频且同域」的少数 App 做 L2 定制（成本高、但每做一个就多一类），"
             "最后承认 L3 不可达。反过来做——先堆脚本再补域名——会得到一堆"
             "「只在某个版本生效」的规则。")
    L.append("")
    L.append("## 7. 差额去哪了：按「谁挡住了」分四组")
    L.append("")
    L.append("上一轮这一节叫「下一步清单」，把 %d 分的差额全部当成待办列出来，"
             "算出一个「做完可到 90%%」的数字。**那个数字是假的**：差额里大部分不是"
             "「还没做」，而是「做不了」——两类混在一起算，等于把许愿当计划。"
             % (cur_den - cur_num))
    L.append("")
    L.append("这一版把挡路的东西分开：")
    L.append("")
    L.append("| 挡路的是 | 判据 | 能不能解 |")
    L.append("|---|---|---|")
    L.append("| 这类广告自己的上限 | `现状 == 上限` | 不能，已经用尽 Loon 能力 |")
    L.append("| 成本（要再加一个 App） | `现状 < 上限` 且有 `blocked` | 能，但要抓包读新 App 的 JSON |")
    L.append("| Loon 的机制 | `现状 < 上限` 且有 `blocked`，且理由是机制 | 不能，除非改插件形态 |")
    L.append("| 物理不可达 | `上限 == 无效` | 不能，不计入分母 |")
    L.append("")
    todo = [r for r in rows if WEIGHT[r["next_to"]] > WEIGHT[r["achieved"]]]
    L.append("**A. 还有活干（%d 类）**" % len(todo))
    L.append("")
    if not todo:
        L.append("无。当前 %d/%d 已是这些手段能达到的全部；再涨只能靠 C 组里"
                 "「多适配一个 App」那几条——那不是代码问题。" % (cur_num, cur_den))
    for r in todo:
        L.append("- **%s**：%s" % (r["name"], r["next"]))
    L.append("")
    L.append("**B. 已到顶（这类广告用尽 Loon 能力，再投入没有档位收益）**")
    L.append("")
    for r in rows:
        if WEIGHT[r["ceiling"]] == 0 or r["achieved"] != r["ceiling"]:
            continue
        L.append("- **%s**：上限就是 `%s`。" % (r["name"], r["ceiling"]))
    L.append("")
    L.append("**C. 停在原地的 %d 类：为什么不再涨**" % len(
        [r for r in rows if r["blocked"]]))
    L.append("")
    L.append("这一组是这一版的重点。它们的上限还没到，但**每一步都要额外付成本**，"
             "所以停在当前位置——理由必须写出来，否则下一个人会重新讨论一遍。")
    L.append("")
    for r in rows:
        if not r["blocked"]:
            continue
        L.append("- **%s**（`%s` → 上限 `%s`）：%s"
                 % (r["name"], r["achieved"], r["ceiling"], r["blocked"]))
    L.append("")
    L.append("**D. 结构不可达（不计入分母）**")
    L.append("")
    for r in rows:
        if WEIGHT[r["ceiling"]] != 0:
            continue
        head = r["limits"].split("。")[0] + "。"
        L.append("- **%s**：%s" % (r["name"], head))
    L.append("")
    L.append("**需真机取证（改代码前先确认）**")
    L.append("")
    L.append("- `response.body.mock_file` 返回空 VAST 时，播放器是否接受 `text` 而不是 `application/xml`。")
    L.append("- 信息流删除 item 后，分页 `cursor` 是否仍然连续（不同 App 行为不同）。")
    L.append("- 证书固定的 App 清单：哪些 App 在 MITM 开启后直接拒绝连接。")
    L.append("")
    L.append("## 8. 怎么读这份表")
    L.append("")
    L.append("1. **别只看总覆盖率**。它把「DNS 一次拦死」和「脚本逐 App 适配」算成同一个权重，"
             "但两者的维护成本差一个数量级。看第 4 节的按层归因。")
    L.append("2. **看「上限」而不是「现状」**。上限是这类广告用尽 Loon 全部能力的天花板；"
             "现状低于上限时，先去第 7 节 C 组看有没有 `blocked`——有就说明不是「还没做」，"
             "是「做不了」或「成本不划算」。")
    L.append("3. **看「协议形态」**。标准协议类优先想 mock，私有类才想脚本，"
             "系统通道类直接跳过。")
    L.append("4. **`--check` 会拦住吹牛**：声明做了但探不到证据、声明没做却探到了、"
             "当前档高于上限，三种情况都会失败。")
    L.append("5. **`--check` 还会拦住「承诺了却说不做」**：`next_to > 现状` 时不许写 `blocked`，"
             "`现状 < 上限` 且停在原地时必须写 `blocked`。这一条是第七节能成立的原因——"
             "**没有它，删掉一行 `next_to` 就能把「做不到」伪装成「没在做」。**")
    L.append("")
    L.append("## 附录：六种可复制的写法")
    L.append("")
    L.append("下面是「一类广告 × 一层」的最小片段。域名与路径要换成你实际抓到的；"
             "标 ⚠️ 的写法**未在真机验证**，先用一个 App 试。")
    L.append("")
    L.append("**① 独立广告域 → DNS 黑洞**（零证书，HTTPS/QUIC 通吃）")
    L.append("")
    L.append("```ini")
    L.append("ad.zijieapi.com = 127.0.0.1")
    L.append("*.pangolin-sdk-toutiao.com = 127.0.0.1")
    L.append("```")
    L.append("")
    L.append("**② 动态子域 → DOMAIN-WILDCARD**（`*` 跨点、`[0-9]` 字符类；语法仅 3.5.3(1008)+，当前只在 TestFlight——ads 插件里默认注释，App Store 3.5.2 用户保持注释、由 ① 的 `[Host]` 逐条兜底，3.5.3+ 取消注释才启用整族）")
    L.append("")
    L.append("```ini")
    L.append("# DOMAIN-WILDCARD,ads[0-9]-normal*.zijieapi.com,REJECT")
    L.append("# DOMAIN-WILDCARD,adserver.*,REJECT")
    L.append("```")
    L.append("")
    L.append("**③ 上报类 → 回 200 + `{}`**（不要回 404，SDK 会重试）")
    L.append("")
    L.append("```ini")
    L.append("URL-REGEX,^https?://[^/]+/(?:report|track|impression|click)(?:/|\\?|$),REJECT-DICT")
    L.append("```")
    L.append("")
    L.append("**④ 清单类 → 空 VAST**（标准协议，格式确定；⚠️ 播放器是否接受 `text` 待真机）")
    L.append("")
    L.append("```ini")
    L.append('response if ${url} ~= /[?&](?:vast|vmap)=/ then response.body.mock_file("text", "empty.vast", 200)')
    L.append("```")
    L.append("")
    L.append("把 `empty.vast`（内容 `<VAST version=\"4.0\"></VAST>`）放进 Loon 的 Mock 目录。"
             "本仓库插件不用 `mock_file`（外部文件违背自包含），这条是给你在主配置里自己试的。")
    L.append("")
    L.append("**⑤ 同域 JSON → 只删广告项**（⚠️ jq 语法与 App 字段名需逐个核对；"
             "命中后同 URL 的脚本不再执行）")
    L.append("")
    L.append("```ini")
    L.append('response if ${url} ~= /\\/feed\\// then response.json.jq("del(.data.items[] | select(.is_ad == true))")')
    L.append("```")
    L.append("")
    L.append("**⑥ 防绕过 → QUIC 回退 + HTTPDNS 拦截**")
    L.append("")
    L.append("```ini")
    L.append("AND,((DOMAIN-SUFFIX,ad.zijieapi.com),(PROTOCOL,QUIC)),REJECT")
    L.append("DOMAIN-KEYWORD,httpdns,REJECT-DROP")
    L.append("DEST-PORT,853,REJECT")
    L.append("```")
    L.append("")
    L.append("选哪一条，看第 1 节那张「协议形态」表：标准协议优先 ④，"
             "半标准优先 ① + ②，私有才用 ⑤。⑥ 是前置条件——不做这层，"
             "上面的规则在 QUIC 与 HTTPDNS 面前会整段失效。")
    L.append("")
    return "\n".join(L) + "\n"


def render_console(rows):
    cur_num, cur_den, cur_pct = stats(rows, "achieved")
    nxt_num, _, nxt_pct = stats(rows, "next_to")
    print("广告面覆盖审计（%d 类）" % len(rows))
    print("=" * 88)
    print("%-22s %-8s %-10s %-10s %s" % ("类型", "族", "上限", "现状", "下一步"))
    print("-" * 88)
    for r in rows:
        arrow = ""
        if WEIGHT[r["next_to"]] > WEIGHT[r["achieved"]]:
            arrow = "→ " + LABEL[r["next_to"]]
        print("%-22s %-8s %-10s %-10s %s"
              % (r["name"], r["family"], LABEL[r["ceiling"]], LABEL[r["achieved"]], arrow))
    print("-" * 88)
    blocked_n = len([r for r in rows if r["blocked"]])
    print("当前 %.1f%% (%d/%d)   待做增分 %d 分   结构性停住 %d 类"
          % (cur_pct, cur_num, cur_den, nxt_num - cur_num, blocked_n))
    print()
    print("按族：")
    for fam in FAMILIES:
        n, d, p = stats_by_family(rows, "achieved", fam)
        print("  %-8s %5.1f%%  (%d/%d)" % (fam, p, n, d))


def main(argv):
    rows, drift = evaluate()

    if "--check" in argv:
        if drift:
            print("surface audit drift: %d" % len(drift), file=sys.stderr)
            for d in drift:
                print("  - " + d, file=sys.stderr)
            return 1
        want = render_md(rows)
        have = read(OUT_MD)
        if have != want:
            print("strategy doc is stale: run `python3 tools/ad-surface-audit.py --write`",
                  file=sys.stderr)
            return 1
        cur_num, cur_den, cur_pct = stats(rows, "achieved")
        nxt_num, _, nxt_pct = stats(rows, "next_to")
        blocked_n = len([r for r in rows if r["blocked"]])
        print("surfaces ok: %d classes  now=%.1f%% (%d/%d)  pending=%d  blocked=%d"
              % (len(rows), cur_pct, cur_num, cur_den, nxt_num - cur_num, blocked_n))
        return 0

    if "--write" in argv:
        md = render_md(rows)
        d = os.path.dirname(OUT_MD)
        if not os.path.isdir(d):
            os.makedirs(d)
        io.open(OUT_MD, "w", encoding="utf-8").write(md)
        print("wrote %s (%d lines)" % (os.path.relpath(OUT_MD, ROOT), md.count("\n")))

    render_console(rows)
    if drift:
        print()
        print("⚠️ 证据漂移 %d 条：" % len(drift))
        for d in drift:
            print("  - " + d)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
