#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旁路审计：「拦了」不等于「拦住」。
==================================

前面三轮分别量化了：

    能力覆盖率   Loon 的功能用了多少        （分母 = 功能）
    广告面覆盖率 广告类型还剩多少           （分母 = 广告类型）
    规则有效率   写下的规则有多少真会命中   （分母 = 已写规则）

前两个数的分子都是**声明**，第三个开始检查**前提**。但它们合起来仍然有一个
共同的盲区：它们都假设「广告请求会走到我们的规则面前」。

真实情况是——广告请求有很多条路可以**绕开整个插件**到达广告服务器：

    · 域名是可见的，但 `[Host]` 只映射了 IPv4，App 走 IPv6 直连
    · 域名根本不存在：SDK 直连 HTTPDNS / DoH 的 IP，连接层只有 IP 没有域名
    · 用户主配置里一条 `DOMAIN-SUFFIX,xxx,DIRECT` 就把插件规则盖掉
    · Loon 自己跑在直连模式，规则/MITM/脚本全部不执行
    · 广告素材是上次联网预拉取的，本次根本没有请求

这些**不是规则写错，也不是前提没满足**，而是「路径没封死」。所以这是第四个
分母：**分母 = 广告请求可能走的旁路**。

四种状态
--------
    sealed   已封死：Loon 有手段，且已经落地，证据能在仓库里探到
    partial  部分封死：手段落地了，但只覆盖一部分场景
    open     有手段但没落地：必须写 blocked 说明为什么不落地
    na       无手段 / 不适用：必须写 blocked 说明为什么封不了

与 ad-surface-audit 的 `blocked` 断言同源：**允许封不死，但禁止沉默。**

用法
----
    python3 tools/bypass-audit.py          看报表
    python3 tools/bypass-audit.py --write  重写 docs/bypass-audit.md
    python3 tools/bypass-audit.py --check  门禁（已接入 npm run check）

退出码：0 通过；1 出现声明与证据/理由冲突，或文档过期。
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(ROOT, "docs")
OUT_MD = os.path.join(DOC_DIR, "bypass-audit.md")

DOC = "https://nsloon.app/docs"

STATUS_LABEL = {
    "sealed": "已封死",
    "partial": "部分封死",
    "open": "有手段未落地",
    "na": "无解",
}

# partial 记 0.5：手段到位但只覆盖一半场景，不能算「封死」也不能算「没做」
# na 不进分母：判得越认真分数越低，激励就反了
SEAL_WEIGHT = {"sealed": 1.0, "partial": 0.5, "open": 0.0, "na": 0.0}


def read(path):
    try:
        return io.open(path, encoding="utf-8").read()
    except (IOError, OSError):
        return ""


CORPUS = {}
for _rel in (
    "plugins/ads/ads.plugin",
    "plugins/soda/soda.plugin",
    "plugins/douyin/douyin.plugin",
    "src/ads/domains.json",
    "src/common/status.js",
    "src/common/block-domains.js",
    "docs/loon-native-first.md",
    "docs/device-checklist.md",
):
    CORPUS[_rel] = read(os.path.join(ROOT, _rel))


# ---------------------------------------------------------------------------
# 旁路清单
# ---------------------------------------------------------------------------
# 每条旁路必须回答四件事：怎么绕、Loon 有没有手段、现在做到哪、做不到时为什么。
#
#   expect   预期状态，工具会拿证据去核对
#   evidence 探测证据：(相对路径, 正则, 最少命中次数)；命中不到 = 声明与事实不符
#   blocked  封不死的理由（sealed 时**不许**写）
#   verify   真机怎么证伪/证实（写清楚动作，不要写「观察一下」）

BYPASSES = [
    dict(
        id="httpdns-domain",
        name="HTTPDNS 走域名",
        how="SDK 请求 `xxxhttpdns.xxx.com` 换回广告域的真实 IP，再用 IP 直连，"
            "绕开系统 DNS 与 `[Host]` 黑洞。",
        loon="`[Host]` 黑洞已知域名 + `DOMAIN-KEYWORD,httpdns,REJECT-DROP` 吃未知域名"
             " + `USER-AGENT` UA 特征兜底。",
        expect="sealed",
        evidence=[
            ("plugins/ads/ads.plugin", r"(?m)^DOMAIN-KEYWORD,httpdns,REJECT-DROP$", 1),
            ("plugins/ads/ads.plugin", r"(?m)^DOMAIN-KEYWORD,httpsdns,REJECT-DROP$", 1),
        ],
        verify="日志里搜 `httpdns` 关键词规则的命中；若命中为 0 且广告仍在，"
               "说明该 SDK 走的是 IP 直连（见 `httpdns-ip`）。",
    ),
    dict(
        id="httpdns-ip",
        name="HTTPDNS 走 IP 直连",
        how="SDK 硬编码接入点 IP（如 `203.107.1.x`）直连换成 IP，"
            "连接层**没有域名**，`[Host]` / `DOMAIN-KEYWORD` / `URL-REGEX` 全部失效。",
        loon="`IP-CIDR`（规则层）与 `[IP Rewrite]`（TUN 阶段，最快）——两者都是可选、默认关闭。",
        expect="partial",
        evidence=[
            ("plugins/ads/ads.plugin", r"(?m)^# IP-CIDR,203\.107\.1\.0/24,REJECT,no-resolve$", 1),
            ("plugins/ads/ads.plugin", r"(?m)^# 203\.119\.238\.240 = drop$", 1),
        ],
        blocked="默认关闭：这些 IP 段与云厂商其它业务共用（`IP-CIDR` 一拦就是整段），"
                "且火山/阿里官方文档写明接入点是 SDK **动态拉取**的，静态化会随版本失效。"
                "要开就得逐版本人工核对，不能常开。",
        verify="开一组后跑一天：广告是否消失 + App 是否有登录/支付异常；"
               "两者都正常才算这组 IP 可留。",
    ),
    dict(
        id="doh-domain",
        name="公网 DoH 走域名",
        how="App 自带 DoH（`https://dns.google/dns-query`），在 443 上把域名解析做掉，"
            "系统 DNS 与 `[Host]` 都碰不到。",
        loon="`[Host]` 把已知 DoH 入口域名映射到 127.0.0.1（DNS 阶段生效，"
             "不需要解密，QUIC 也一样拦）。",
        expect="sealed",
        evidence=[
            ("plugins/ads/ads.plugin", r"(?m)^dns\.google = 127\.0\.0\.1$", 1),
            ("plugins/ads/ads.plugin", r"(?m)^dns\.quad9\.net = 127\.0\.0\.1$", 1),
            ("plugins/ads/ads.plugin", r"(?m)^dns\.nextdns\.io = 127\.0\.0\.1$", 1),
        ],
        verify="在 Loon 里看这几个域名的解析结果是否为 127.0.0.1；"
               "未知 DoH 服务商不在清单内，走 `resolver-ip-direct` 那条路。",
    ),
    dict(
        id="resolver-ip-direct",
        name="公共解析器 IP 直连（53/443/853 全端口）",
        how="App 不请求 DoH 域名，直接连 `8.8.8.8:443` 或 `1.1.1.1:853`。"
            "此时**域名根本不存在**：`[Host]` 黑洞、`DOMAIN-KEYWORD`、`URL-REGEX` 全废，"
            "`DEST-PORT,853` 也只挡端口、挡不住 443 上的 DoH。",
        loon="`IP-CIDR` / `IP-CIDR6`——连接层只看 IP，是这条旁路**唯一**能在插件里生效的手段。",
        expect="partial",
        evidence=[
            ("plugins/ads/ads.plugin", r"(?m)^# IP-CIDR,8\.8\.8\.8/32,REJECT,no-resolve$", 1),
            ("plugins/ads/ads.plugin", r"(?m)^# IP-CIDR6,2606:4700:4700::1111/128,REJECT,no-resolve$", 1),
        ],
        blocked="默认关闭：用户主配置可能把 8.8.8.8 / 1.1.1.1 当作 `dns-server` / `doh-server`，"
                "插件规则一旦命中就会掐断 Loon 自己的解析链（表现是**全网上不了**，"
                "比广告回来严重得多）。且 anycast IP 会变。开启前必须逐条核对主配置。",
        verify="① 主配置 `dns-server` / `doh-server` 里没有清单内任何 IP；"
               "② 开启后网络与广告域解析（应为 127.0.0.1）都正常；"
               "③ 用 `dns.leak` 类工具确认 App 侧解析确实回到 Loon。",
    ),
    dict(
        id="dot-doq-port",
        name="DoT / DoQ 853 端口",
        how="App 自带 DoT（TCP 853）或 DoQ（UDP 853），绕过 Loon 的 DNS。",
        loon="`DEST-PORT,853,REJECT`——端口在连接层可见，不需要域名也不需要解密。",
        expect="sealed",
        evidence=[
            ("plugins/ads/ads.plugin", r"(?m)^DEST-PORT,853,REJECT$", 1),
        ],
        verify="官方 `Rule/port_rule` 页没有限定 TCP/UDP；而 `PROTOCOL` 支持 `UDP` 值"
               "（`Rule/protocol_rule`），说明 UDP 连接同样进规则引擎。"
               "若真机发现 DoQ 仍能穿透，确定解法是主配置的 `disable-udp-ports = 853`"
               "（插件 `[General]` 白名单里没有该键）。",
    ),
    dict(
        id="quic",
        name="QUIC / HTTP3 绕过解密",
        how="广告请求走 UDP 443，`[MITM]` 只处理 TCP，脚本根本不执行。",
        loon="按域 `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC)),REJECT` 逼回 TCP+TLS；"
             "**不做**全局 `PROTOCOL,QUIC,REJECT`。",
        expect="sealed",
        evidence=[
            ("plugins/soda/soda.plugin", r"(?m)^AND,\(\(DOMAIN-SUFFIX,[^)]*\),\(PROTOCOL,QUIC\)\),REJECT$", 1),
            ("plugins/douyin/douyin.plugin", r"(?m)^AND,\(\(DOMAIN-SUFFIX,[^)]*\),\(PROTOCOL,QUIC\)\),REJECT$", 1),
        ],
        verify="ads 是零证书 DNS 层，`[Host]` 在 DNS 阶段生效，不受 QUIC 影响；"
               "只有带 `[MITM]` 的 soda/douyin 需要回退。真机看请求日志里"
               "广告域是否出现 HTTP/3。",
    ),
    dict(
        id="ipv6-aaaa",
        name="IPv6 / AAAA 旁路",
        how="`[Host]` 里 1301 条黑洞**全部只映射 IPv4**（127.0.0.1）。"
            "若 Loon 对命中域名仍放行真实 AAAA 记录，App 走 IPv6 直连就绕过了整个黑洞。",
        loon="`[Host]` 的 `ip-mode:ipv4-only` 右值（官方 `DNS/hostmap` 支持 "
             "`ipv4-only`/`dual`/`ipv4-preferred`/`ipv6-preferred`）；"
             "或主配置 `ipv6-vif = off`（插件能声明，但关的是整个 TUN 的 IPv6）。",
        expect="open",
        evidence=[],
        blocked="**有手段但刻意不落地**。官方 `DNS/hostmap` 只给了 `ip-mode:` "
                "**单独使用**的示例，没有给同一域名同时写 `= 127.0.0.1` 与 "
                "`= ip-mode:ipv4-only` 的示例。若 Loon 一个域名只认最后一条，"
                "补 ip-mode 会**把黑洞覆盖掉**——比不补更糟（广告全回来且排查方向完全错）。"
                "在确认「多行共存」之前，不拿 1301 条主力规则去赌。",
        verify="① 先用一条无关域名验证共存：`probe.example = 127.0.0.1` 与 "
               "`probe.example = ip-mode:ipv4-only` 各写一行，看 A 记录是否仍是 127.0.0.1；"
               "② 再单独确认 `probe.example` 的 AAAA 查询返回空还是真实地址——"
               "**返回真实地址才说明旁路真的存在**，才值得补。"
               "两步都为正，再批量生成 ip-mode 行并接进 lint。",
    ),
    dict(
        id="hardcoded-ip-sni",
        name="硬编码 IP + SNI 直连",
        how="SDK 内置广告服务 IP，直接 `https://1.2.3.4/...` 带 SNI 请求，域名不出现在连接层。",
        loon="无。`IP-CIDR` 只能逐条枚举，`IP-ASN` 会打死整个云厂商。",
        expect="na",
        evidence=[],
        blocked="广告服务的 IP 是 anycast 且随时变更，逐条枚举必然漏；"
                "而广告与正常业务常常同 ASN（`IP-ASN` 一拦就是全站）。"
                "这条只能靠广告域的 DNS 层拦，拦不到 IP 直连形态。",
        verify="抓包看到 `https://<IP>/` 形态且 Host/SNI 是广告域时，才有具体目标可写；"
               "没有抓包证据不写 IP 规则（见第七轮「从品牌名推域名」的教训）。",
    ),
    dict(
        id="main-config-precedence",
        name="主配置规则盖掉插件规则",
        how="官方 `Rule/` 写明来源优先级 **本地 > 插件 > 订阅**。用户主配置里一条 "
            "`DOMAIN-SUFFIX,xxx,DIRECT` 就能让插件的 `REJECT` 永远轮不到。",
        loon="无。插件侧没有任何 API 能读取或改写主配置规则。",
        expect="na",
        evidence=[],
        blocked="插件读不到主配置，也无法声明优先级。只能写进 README 的排障段："
                "「广告突然全回来」时第一步就是查主配置有没有指向广告域的 DIRECT/代理规则。",
        verify="把插件规则原样复制到主配置最前面，若拦截恢复，即为该旁路命中。",
    ),
    dict(
        id="bypass-tun",
        name="App 被主配置 bypass-tun 排除",
        how="App 被排除在 TUN 之外，流量完全不进 Loon，规则/MITM/脚本一律不执行。",
        loon="无（`bypass-tun` 只在主配置声明；插件声明它就是全局生效，与「只拦广告」无关）。",
        expect="na",
        evidence=[],
        blocked="插件不能也不会去接管 TUN 范围——那是在替用户改全局网络边界，"
                "出问题时无法归因。",
        verify="Loon 的请求日志里完全没有该 App 的任何记录，即为该旁路命中。",
    ),
    dict(
        id="running-model-direct",
        name="Loon 跑在直连模式",
        how="`running_model = 0` 时 Loon 不走规则、不进 MITM、不跑脚本，插件完全不生效，"
            "而界面上只显示「直连」两个字。",
        loon="`$config.getConfig()` 读 `running_model`，状态页点名告警并给处置建议。",
        expect="sealed",
        evidence=[
            ("src/common/status.js", r"running_model", 2),
            ("src/common/status.js", r"插件不生效", 1),
        ],
        verify="状态自检按钮里应显示「运行模式 直连（⚠️ 插件不生效）」；"
               "看不到就说明脚本没跑（先看上一条 bypass-tun）。",
    ),
    dict(
        id="cert-pinning",
        name="证书固定导致解密失败",
        how="App 校验证书链，`[MITM]` 握手失败 → response 脚本不执行，"
            "响应体净化整条链路失效。",
        loon="无。官方 MitM 页只列 `hostname` / `ca-p12` / `ca-passphrase`，"
             "没有 `skip-server-cert-verify` 之类的键。",
        expect="na",
        evidence=[],
        blocked="证书固定是 App 侧的信任链校验，代理侧没有官方开关。"
                "仓库的做法是把它列为**已知风险并给退路**：受影响时把对应广告域从 "
                "`[MITM]` 注释掉，退回域名层拦截（见两个插件头部注释第 2 条）。",
        verify="开启 `blockAdDomains` 后某个 App 完全打不开/白屏，即为该旁路命中；"
               "删掉 `[MITM]` 里对应域可确认。",
    ),
    dict(
        id="local-cache-preload",
        name="本地缓存与素材预拉取",
        how="广告素材与配置在上次联网时已下载到本地，本次渲染不发起任何请求。",
        loon="无。网络层拦不到本地渲染。",
        expect="na",
        evidence=[],
        blocked="这是客户端行为，不是网络路径。任何代理工具都对它无效——"
                "这也是为什么「拦了域名但广告还出现一次」经常是正常现象，"
                "而不是规则失效。",
        verify="冷启动（清 App 数据）后首次打开是否无广告：是 → 规则有效；"
               "否 → 才是真的漏拦。",
    ),
    dict(
        id="same-domain-path",
        name="广告接口与业务同域（靠路径区分）",
        how="广告配置走业务域名下的某个路径，只靠域名拦会连业务一起打死。",
        loon="`[MITM]` + response 脚本按 URL 正则与字段裁剪（soda/douyin 已落地）。",
        expect="partial",
        evidence=[
            ("plugins/soda/soda.plugin", r"(?m)^\[MITM\]", 1),
            ("plugins/douyin/douyin.plugin", r"(?m)^\[Script\]", 1),
        ],
        blocked="ads 是零证书 DNS 层，看不到路径，只能整域拦——而整域拦会打死业务。"
                "soda/douyin 这类带 `[MITM]` 的插件能按路径处理，"
                "但**每多适配一个 App 就要重新抓包确认哪些键安全**（见 "
                "`docs/ad-type-strategy.md` 的 blocked 说明）。",
        verify="新增 App 时先抓包确认广告配置端点与业务端点是否同域；"
               "同域才值得加到 `[MITM]`。",
    ),
    dict(
        id="dns-cache",
        name="接管前的 DNS 缓存残留",
        how="App 在 Loon 接管之前已解析并缓存了广告域的真实 IP。",
        loon="无。插件清不掉 App 进程内的缓存。",
        expect="na",
        evidence=[],
        blocked="缓存属于 App 进程状态，网络层不可见也不可写。",
        verify="重开 App（不是重开 Loon）后广告是否消失：是 → 只是缓存；否 → 真的漏拦。",
    ),
    dict(
        id="plaintext-http",
        name="明文 HTTP 广告与上报",
        how="少量广告/上报端点仍是明文 `http://`。",
        loon="`URL-REGEX,^http://…`，不需要解密就能匹配完整 URL。",
        expect="partial",
        evidence=[
            ("plugins/ads/ads.plugin", r"(?m)^URL-REGEX,\^http:\\/\\/", 1),
        ],
        blocked="这几条正则锚定 `^http://`，**只吃明文**。同样路径的 HTTPS 端点要 "
                "`[MITM]` 才看得到，而 ads 没有 `[MITM]`。技术上有效、"
                "实际命中面很窄（见 `docs/rule-effectiveness.md` 第 4 节）。",
        verify="日志里搜这几条规则的命中数；长期为 0 就该考虑删掉，"
               "而不是继续把它当成一层防护。",
    ),
    dict(
        id="long-lived-push",
        name="长连接 / 私有协议下发广告配置",
        how="广告配置通过长连接或私有 TCP 协议下发，不走 HTTP，`[MITM]` 与脚本都看不到内容。",
        loon="`[Host]` 域名黑洞：连都连不上，长连接也建立不起来——**DNS 层对协议形态免疫**。",
        expect="sealed",
        evidence=[
            ("plugins/ads/ads.plugin", r"(?m)^\S+ = 127\.0\.0\.1$", 1000),
        ],
        verify="这条「已封死」依赖的是 DNS 层主力（1301 条黑洞）而不是解密层；"
               "若某天把主力改成规则层或脚本层，这条会立刻降级为 partial。",
    ),
]


# ---------------------------------------------------------------------------
# 探测
# ---------------------------------------------------------------------------

def probe(evidence):
    """返回未命中的证据列表。"""
    missing = []
    for item in evidence:
        path, rx, minimum = item
        text = CORPUS.get(path)
        if text is None:
            missing.append((path, rx, 0, minimum))
            continue
        n = len(re.findall(rx, text))
        if n < minimum:
            missing.append((path, rx, n, minimum))
    return missing


def audit():
    rows = []
    for b in BYPASSES:
        status = b.get("expect", "na")
        blocked = b.get("blocked", "").strip()
        missing = probe(b.get("evidence") or [])
        row = dict(b)
        row["status"] = status
        row["blocked"] = blocked
        row["missing"] = missing
        row["evidenced"] = bool(b.get("evidence")) and not missing
        rows.append(row)
    return rows


def drift(rows):
    """声明与事实/理由冲突的地方。"""
    out = []
    for r in rows:
        sid, name, status = r["id"], r["name"], r["status"]
        if status == "sealed" and r["blocked"]:
            out.append("%s（%s）：标为「已封死」却写了做不到的理由——二者只能有一个" % (name, sid))
        if status == "sealed" and not r["evidenced"]:
            out.append("%s（%s）：标为「已封死」但证据探不到（%d 项未命中）"
                       % (name, sid, len(r["missing"])))
        if status == "partial" and not r["evidenced"]:
            out.append("%s（%s）：标为「部分封死」但证据探不到（%d 项未命中）"
                       % (name, sid, len(r["missing"])))
        if status == "partial" and not r["blocked"]:
            out.append("%s（%s）：只做到「部分封死」，却没写剩下那部分为什么封不了" % (name, sid))
        if status == "open" and not r["blocked"]:
            out.append("%s（%s）：有手段却没落地，必须写 blocked 说明理由" % (name, sid))
        if status == "na" and not r["blocked"]:
            out.append("%s（%s）：判为无解，必须写 blocked 说明为什么" % (name, sid))
        if status == "open" and r["evidenced"]:
            out.append("%s（%s）：标为「未落地」却在仓库里探到了证据——状态写错了" % (name, sid))
    return out


# ---------------------------------------------------------------------------
# 报表
# ---------------------------------------------------------------------------

def pct(a, b):
    return 100.0 * a / b if b else 0.0


def stats(rows):
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    denom = sum(counts.get(s, 0) for s in ("sealed", "partial", "open"))
    score = sum(SEAL_WEIGHT[r["status"]] for r in rows)
    return counts, denom, score


def render_md(rows):
    L = []
    counts, denom, score = stats(rows)
    sealed = counts.get("sealed", 0)
    partial = counts.get("partial", 0)
    open_n = counts.get("open", 0)
    na_n = counts.get("na", 0)

    L.append("# 旁路审计：拦了 ≠ 拦住")
    L.append("")
    L.append("> 本文件由 `tools/bypass-audit.py` 生成，请勿手改。")
    L.append("> 改插件后跑 `python3 tools/bypass-audit.py --write`。")
    L.append("")
    L.append("## 0. 一页结论")
    L.append("")
    L.append("前三个分母分别数「功能」「广告类型」「规则前提」，")
    L.append("它们都默认了一件事：**广告请求会走到我们的规则面前**。")
    L.append("这一份数的是第四条假设——广告请求有多少条路可以**绕开整个插件**。")
    L.append("")
    L.append("- 共枚举 **%d** 条旁路。" % len(rows))
    L.append("- **已封死 %d 条**：Loon 有手段且已落地，证据在仓库里能探到。" % sealed)
    L.append("- **部分封死 %d 条**：手段落地了，但只覆盖一部分场景。" % partial)
    L.append("- **有手段未落地 %d 条**：能做但刻意没做，每条都写了为什么。" % open_n)
    L.append("- **无解 %d 条**：Loon 侧没有手段，每条都写了为什么封不了。" % na_n)
    L.append("")
    L.append("封死率 **%.1f%%**（分母 %d = 已封死 + 部分封死 + 未落地；"
             "无解不进分母——判得越认真分数越低，激励就反了）。"
             % (pct(sealed, denom), denom))
    L.append("加权封死率 **%.1f%%**（部分封死记 0.5 分）。" % pct(score, denom))
    L.append("")
    L.append("**这条审计最重要的一行是「有手段未落地」那一类**：")
    L.append("它不是「做不到」，是「还没做」。第 4 节写清了每条要怎么在真机上证伪，")
    L.append("证伪通过了才能挪进「已封死」——否则就是把愿望当成事实。")
    L.append("")

    # 1. 四态模型
    L.append("## 1. 四种状态")
    L.append("")
    L.append("| 状态 | 含义 | `--check` 要求 |")
    L.append("|---|---|---|")
    L.append("| 已封死 `sealed` | Loon 有手段，且已落地 | 证据必须探得到；**不许**写 blocked |")
    L.append("| 部分封死 `partial` | 手段落地，只覆盖部分场景 | 证据必须探得到；**必须**写 blocked |")
    L.append("| 有手段未落地 `open` | 能做但没做 | 证据必须**探不到**；**必须**写 blocked |")
    L.append("| 无解 `na` | Loon 侧没有手段 | **必须**写 blocked |")
    L.append("")
    L.append("「证据探不到」对 `sealed` 是错误，对 `open` 是**正确**。")
    L.append("这套互斥关系就是为了防止把「没做」伪装成「做了」——")
    L.append("与 `ad-surface-audit` 的 `blocked` 断言、`rule-effectiveness` 的 waiver 同源。")
    L.append("")

    # 2. 总表
    L.append("## 2. 总表")
    L.append("")
    L.append("| # | 旁路 | 怎么绕 | Loon 的手段 | 状态 |")
    L.append("|---:|---|---|---|---|")
    order = {"sealed": 0, "partial": 1, "open": 2, "na": 3}
    for i, r in enumerate(sorted(rows, key=lambda x: (order[x["status"]], x["id"])), 1):
        L.append("| %d | %s | %s | %s | %s |"
                 % (i, r["name"], r["how"].replace("\n", " "),
                    r["loon"], STATUS_LABEL[r["status"]]))
    L.append("")

    # 3. 逐条
    L.append("## 3. 逐条：为什么停在这")
    L.append("")
    for i, r in enumerate(sorted(rows, key=lambda x: (order[x["status"]], x["id"])), 1):
        L.append("### %d. %s · %s" % (i, r["name"], STATUS_LABEL[r["status"]]))
        L.append("")
        L.append("**怎么绕**　%s" % r["how"])
        L.append("")
        L.append("**Loon 的手段**　%s" % r["loon"])
        L.append("")
        if r["blocked"]:
            L.append("**为什么没封死**　%s" % r["blocked"])
            L.append("")
        L.append("**怎么证伪**　%s" % r["verify"])
        L.append("")
        if r["missing"]:
            L.append("> ⚠️ 以下证据未命中，`--check` 会失败：")
            L.append(">")
            for path, rx, n, minimum in r["missing"]:
                L.append("> - `%s` 需 ≥%d 处 `%s`，实际 %d 处" % (path, minimum, rx, n))
            L.append("")

    # 4. 未落地清单
    opens = [r for r in rows if r["status"] == "open"]
    L.append("## 4. 「有手段但未落地」清单（真机待办）")
    L.append("")
    if not opens:
        L.append("无。")
        L.append("")
    else:
        L.append("这一类必须被单独看见：它不是做不到，是**还没验证**。")
        L.append("每条都给了真机动作，做完才能挪进「已封死」。")
        L.append("")
        for r in opens:
            L.append("- **%s**：%s" % (r["name"], r["verify"]))
        L.append("")

    # 5. 四个分母
    L.append("## 5. 四个数，四个分母")
    L.append("")
    L.append("| 度量 | 分母 | 回答什么 | 当前 |")
    L.append("|---|---|---|---|")
    L.append("| 能力利用率 | Loon 的功能 | 功能用了多少 | 见 `docs/loon-coverage.md` |")
    L.append("| 广告面覆盖率 | 广告的类型 | 广告还剩多少 | 见 `docs/ad-type-strategy.md` |")
    L.append("| 规则有效率 | 已写的规则 | 写了的有多少真会命中 | 见 `docs/rule-effectiveness.md` |")
    L.append("| **路径封死率** | **绕过的路** | **拦了的是不是真拦住** | 本文件 |")
    L.append("")
    L.append("四者层层收紧：功能用了 → 广告覆盖了 → 规则生效了 → **但请求还有别的路**。")
    L.append("")

    # 6. 门禁
    L.append("## 6. 门禁")
    L.append("")
    L.append("`--check` 六条断言：")
    L.append("")
    L.append("1. 标「已封死」却写了 blocked —— 矛盾。")
    L.append("2. 标「已封死 / 部分封死」但证据探不到 —— 声明与事实不符。")
    L.append("3. 标「部分封死」但没写 blocked —— 剩那部分为什么封不了，必须说。")
    L.append("4. 标「有手段未落地」但没写 blocked —— 为什么不做，必须说。")
    L.append("5. 标「有手段未落地」却探到了证据 —— 状态写错了。")
    L.append("6. `docs/bypass-audit.md` 必须与工具输出一致。")
    L.append("")

    return "\n".join(L) + "\n"


def render_console(rows):
    counts, denom, score = stats(rows)
    out = ["bypass-audit: %d 条旁路" % len(rows)]
    for s in ("sealed", "partial", "open", "na"):
        if counts.get(s):
            out.append("  %-8s %2d  %s" % (s, counts[s], STATUS_LABEL[s]))
    out.append("  封死率 %.1f%%  加权 %.1f%%" % (pct(counts.get("sealed", 0), denom),
                                             pct(score, denom)))
    d = drift(rows)
    out.append("  漂移: %d" % len(d))
    for line in d:
        out.append("    - " + line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv):
    rows = audit()
    problems = drift(rows)

    if "--check" in argv:
        for line in problems:
            print(line, file=sys.stderr)
        if problems:
            return 1
        want = render_md(rows)
        have = read(OUT_MD)
        if have != want:
            print("bypass doc is stale: run `python3 tools/bypass-audit.py --write`",
                  file=sys.stderr)
            return 1
        counts, denom, score = stats(rows)
        print("bypass ok: %d paths  sealed=%d partial=%d open=%d na=%d  seal=%.1f%%"
              % (len(rows), counts.get("sealed", 0), counts.get("partial", 0),
                 counts.get("open", 0), counts.get("na", 0),
                 pct(counts.get("sealed", 0), denom)))
        return 0

    if "--write" in argv:
        io.open(OUT_MD, "w", encoding="utf-8").write(render_md(rows))
        print("wrote %s" % OUT_MD)
        return 0

    print(render_console(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
