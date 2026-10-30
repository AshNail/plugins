#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loon-coverage.py —— Loon 能力覆盖率 / 利用率统计（机器计算，不靠手写）

为什么需要它
------------
前几轮一直在按「能力条目」或「文档章节」人工扫，结论写在 md 里。问题有两个：
  1. 数字会漂：加了规则 / 换了写法，文档里的「已用 N 项」不会自动更新；
  2. 口径会混：把「不适用」和「判死」都算成「没用」，覆盖率被低估；
     把「写了但没生效」算成「已用」，覆盖率被高估。

这个脚本把能力表变成数据，从插件与脚本里**探测**真实用法，分五档：
  used         已用（有明确证据）
  open         可用未用（能落但没落，需要给理由）
  reject       判死（有理由，不是懒）
  na           不适用（不是插件能碰的东西）
  undocumented 未文档化（**官方 26 个正文页查不到的 token**，我们却在插件里带着它）

利用率 = used / (used + open)。reject / na / undocumented 都不进分母——否则
「判死得越认真，分数越低」，激励正好反了；而 undocumented 更不是能力，
它进分子就是虚报（第十九轮把 `%APPEND%` 与 `h2 = true` 从「已用」摘出，
正是为了守住这条：能力表只声明官方文档查得到的东西）。
undocumented 行仍然要求**探测得到**：token 一旦从插件里消失，说明连冗余都不剩了，
声明就该跟着删掉，`--check` 会失败提醒。

用法
----
  python3 tools/loon-coverage.py            # 打印报表
  python3 tools/loon-coverage.py --write    # 重新生成 docs/loon-coverage.md
  python3 tools/loon-coverage.py --check    # CI：探测结果与声明不符即失败
"""

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(ROOT, "plugins")
SRC_DIR = os.path.join(ROOT, "src")
OUT_MD = os.path.join(ROOT, "docs", "loon-coverage.md")

DOC = "https://loon0x00.github.io/docs"


# ---------------------------------------------------------------------------
# 语料装载
# ---------------------------------------------------------------------------

def read(path):
    try:
        return io.open(path, encoding="utf-8").read()
    except (IOError, OSError):
        return ""


def load_plugins():
    out = {}
    for name in sorted(os.listdir(PLUGIN_DIR)):
        path = os.path.join(PLUGIN_DIR, name, name + ".plugin")
        if os.path.isfile(path):
            out[name] = read(path)
    return out


def load_src():
    out = {}
    for base, _dirs, files in os.walk(SRC_DIR):
        for fn in files:
            if fn.endswith(".js"):
                path = os.path.join(base, fn)
                out[os.path.relpath(path, ROOT)] = read(path)
    return out


PLUGINS = load_plugins()
SRC = load_src()


def strip_hash_comments(text):
    """去掉以 # 开头的整行注释（插件配置行与注释行的区分）。"""
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))


def strip_js_comments(text):
    """去掉 /* */ 与 // 注释，避免「注释里提到过」被当成「用了」。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return text


PLUGIN_CFG = {k: strip_hash_comments(v) for k, v in PLUGINS.items()}
SRC_CODE = {k: strip_js_comments(v) for k, v in SRC.items()}
CFG_ALL = "\n".join(PLUGIN_CFG.values())
SRC_ALL = "\n".join(SRC_CODE.values())
RAW_ALL = "\n".join(PLUGINS.values()) + "\n" + "\n".join(SRC.values())


def section(text, name):
    """取插件里某个 [Section] 的有效配置行（到下一个 [ 开头的行为止）。"""
    m = re.search(r"(?m)^\s*\[%s\]\s*$" % re.escape(name), text)
    if not m:
        return []
    body = text[m.end():]
    stop = re.search(r"(?m)^\s*\[", body)
    if stop:
        body = body[: stop.start()]
    return [l.strip() for l in body.split("\n") if l.strip() and not l.strip().startswith("#")]


def in_any_section(name):
    out = []
    for text in PLUGIN_CFG.values():
        out.extend(section(text, name))
    return out


# ---------------------------------------------------------------------------
# 能力表
# ---------------------------------------------------------------------------
# 每条：layer / key / name / expect / probe / why
#   probe  正则，在「有效配置 + 有效脚本」上匹配；命中即 used
#   expect 声明期望（用于 --check 发现漂移）
#   why    open / reject / na / undocumented 的理由（used 可省）

CAPABILITIES = [
    # ---------------- 传输层 ----------------
    dict(layer="传输层", key="mitm", name="`[MITM]` 域名解密", expect="used",
         probe=r"(?m)^\s*hostname\s*=",
         href=DOC + "/MitM/"),
    dict(layer="传输层", key="mitm-wild", name="`[MITM]` 通配 `*` / `?`", expect="used",
         probe=r"(?m)^\s*hostname\s*=.*[*?]",
         href=DOC + "/MitM/",
         why="Pangle 分片族用一条 `ads?-normal*.zijieapi.com` 覆盖 10 台主机"),
    dict(layer="传输层", key="mitm-exclude", name="`[MITM]` 排除 `-域名`", expect="reject",
         probe=r"(?m)^\s*hostname\s*=.*(?:=\s*|,\s*)-[A-Za-z0-9]",
         href=DOC + "/MitM/",
         why="现有 MITM 名单是精确主机或窄通配（soda/douyin），没有需要排除的敏感兄弟域；"
             "排除语法本身可用，但当前没有场景"),
    dict(layer="传输层", key="mitm-append", name="`hostname = %APPEND% …`（官方查不到该 token）",
         expect="undocumented",
         token="lint:MITM.hostname-prefix",
         probe=r"(?m)^\s*hostname\s*=.*%APPEND%",
         href=DOC + "/MitM/",
         why="官方 MitM 页的参数表只有 `hostname` / `ca-p12` / `ca-passphrase` 三行，整站 26 个正文页"
             "都扫不到 `%APPEND%`（这条断言现在是机器数出来的：`tools/loon-token-audit.py` 的 "
             "`absent_claims[%append%] == 0`，命中数一变非 0 就报「断言已被推翻」）——它是 Surge 的"
             "「追加而非覆盖」写法。插件段与主配置同名键的合并语义"
             "官方同样没写（与订阅 Host Map 同一类未定义）。留着它的理由是对称的：Loon 若认识，删掉会"
             "让本插件整行覆盖用户主配置的解密名单；若不认识，它只是一个永不匹配的空主机项。"
             "**保留但不计入能力口径**；真机取证见 `docs/device-checklist.md`"),
    dict(layer="传输层", key="mitm-ca", name="`ca-p12` / `ca-passphrase`", expect="reject",
         probe=r"(?m)^\s*(?:ca-p12|ca-passphrase)\s*=",
         href=DOC + "/MitM/",
         why="自带 CA 私钥意味着把私钥塞进公开插件，安全与可移植性双输；统一用 Loon 内置 CA"),
    dict(layer="传输层", key="quic", name="QUIC→TCP 回退（`PROTOCOL,QUIC`）", expect="used",
         probe=r"PROTOCOL\s*,\s*QUIC",
         href=DOC + "/Rule/protocol_rule"),
    dict(layer="传输层", key="gzip-negotiate", name="压缩协商降到 gzip", expect="used",
         probe=r'request\.header\.set\(\s*"Accept-Encoding"\s*,\s*"gzip"\s*\)',
         href=DOC + "/Rewrite/rewrite_v2",
         why="脚本层只有 ungzip；br/zstd 解不开就是静默跳过"),
    dict(layer="传输层", key="h2", name="`h2 = true`（官方查不到该键）", expect="undocumented",
         token="MITM.h2",
         probe=r"(?m)^\s*h2\s*=\s*true\s*$",
         href=DOC + "/MitM/",
         why="同 `%APPEND%`：官方 MitM 参数表没有 `h2`，而官方产品页把「解密 HTTPS 与 HTTP/2」写成"
             "内置默认行为、没有开关。社区插件通行写 `h2 = true`，我们保留它当作「未知键被忽略」时的"
             "零成本保险——但保险不是能力，所以不进利用率；写成 `h2 = false` 才是真错（lint 锁死）。"
             "旧文档里那句「不计入能力点」在本轮才真正落地：此前它一直挂在「已用」上"),
    dict(layer="传输层", key="no-compress", name="免压缩（删 `Accept-Encoding`）", expect="reject",
         probe=r'request\.header\.(del|replace)\(\s*"Accept-Encoding"',
         href=DOC + "/Rewrite/rewrite_v2",
         why="upsell 响应 gzip 后已 183~191 KB，去压缩会膨胀 5~10 倍"),

    # ---------------- 规则层 ----------------
    dict(layer="规则层", key="r-domain", name="`DOMAIN`", expect="open",
         probe=r"(?m)^DOMAIN\s*,", href=DOC + "/Rule/domain_rule",
         why="被 `[Host]` 精确映射覆盖（同一批域名），规则层不需要重复一遍"),
    dict(layer="规则层", key="r-suffix", name="`DOMAIN-SUFFIX`", expect="used",
         probe=r"(?m)^DOMAIN-SUFFIX\s*,", href=DOC + "/Rule/domain_rule",
         why="ads 通配层与 app 插件（banks/qidian/x）整域 REJECT 使用；`[Host]` 的 `*.` 只映射 DNS，"
             "SUFFIX 还能表达 REJECT-DROP 等规则动作"),
    dict(layer="规则层", key="r-keyword", name="`DOMAIN-KEYWORD`", expect="used",
         probe=r"(?m)^DOMAIN-KEYWORD\s*,", href=DOC + "/Rule/domain_rule"),
    dict(layer="规则层", key="r-wildcard", name="`DOMAIN-WILDCARD`（含 `[0-9]` 字符类）", expect="open",
         probe=r"(?m)^DOMAIN-WILDCARD\s*,", href=DOC + "/Rule/domain_rule",
         why="语法仅 3.5.3(1008)+ 提供且当前只在 TestFlight；App Store 正式版 3.5.2(996) 对未知规则类型"
             "的行为未文档化，ads 插件把 41 条通配/家族 glob 默认注释收录，3.5.3+ 用户取消注释即生效"),
    dict(layer="规则层", key="r-url-regex", name="`URL-REGEX`", expect="used",
         probe=r"(?m)^URL-REGEX\s*,", href=DOC + "/Rule/http_rule",
         why="已写 6 条，**全部锚定 `^http://`**（HTTPDNS 配置与明文上报）。"
             "技术上有效、不依赖解密，但只吃明文 HTTP，而现代 App 接口几乎全 HTTPS，"
             "实际命中面很窄。见 `docs/rule-effectiveness.md` 第 4 节"),
    dict(layer="规则层", key="r-user-agent", name="`USER-AGENT`", expect="used",
         probe=r"(?m)^USER-AGENT\s*,", href=DOC + "/Rule/http_rule",
         why="已写 4 条（`httpdns*` / `httpsdns*`）。⚠️ **前提未满足**：ads 插件"
             "**没有 `[MITM]` 段**，而 UA 是 HTTP 请求头、未解密时看不到——"
             "能否命中**未经验证**，已登记 waiver（含真机证伪方法）。"
             "见 `docs/rule-effectiveness.md` 第 3 节"),
    dict(layer="规则层", key="r-ip-cidr", name="`IP-CIDR` / `IP-CIDR6`", expect="open",
         probe=r"(?m)^IP-CIDR6?\s*,", href=DOC + "/Rule/ip_rule",
         why="HTTPDNS 接入点拦截已写好但默认注释（换 IP 就失效，需要按版本人工核对）"),
    dict(layer="规则层", key="r-geoip", name="`GEOIP`", expect="reject",
         probe=r"(?mi)^(GEOIP)\s*,", href=DOC + "/Rule/ip_rule",
         why="按国家/地区分流与广告拦截无关"),
    dict(layer="规则层", key="r-ip-asn", name="`IP-ASN`", expect="reject",
         probe=r"(?mi)^IP-ASN\s*,", href=DOC + "/Rule/ip_rule",
         why="按 ASN 拦会把整个云厂商打死，广告与正常接口同 ASN"),
    dict(layer="规则层", key="r-src-ip", name="`SRC-IP`", expect="reject",
         probe=r"(?mi)^SRC-IP\s*,", href=DOC + "/Rule/ip_rule",
         why="按来源 IP 匹配，与「拦哪家广告」无关"),
    dict(layer="规则层", key="r-src-port", name="`SRC-PORT`", expect="reject",
         probe=r"(?mi)^SRC-PORT\s*,", href=DOC + "/Rule/port_rule",
         why="按来源端口匹配，插件场景没有可用的判断维度"),
    dict(layer="规则层", key="r-no-resolve", name="`no-resolve`（IP 类规则参数）", expect="open",
         probe=r"\bno-resolve\b", href=DOC + "/Rule/ip_rule",
         why="只对 IP 类规则有意义；当前 16 条 HTTPDNS 网关 IP 规则默认注释，生效项为 0"),
    dict(layer="规则层", key="r-proxy", name="`PROXY` 策略", expect="reject",
         probe=r"(?m)^(?:DOMAIN(?:-SUFFIX|-KEYWORD)?|AND|OR|NOT|URL-REGEX|USER-AGENT|DEST-PORT|PROTOCOL|IP-CIDR6?),[^\n]*,\s*PROXY\s*$",
         href=DOC + "/Plugin/",
         why="插件规则只允许 DIRECT / REJECT 族 / PROXY；去广告只做拒绝或直连，"
             "把广告流量交给代理组只会让广告正常加载"),
    dict(layer="规则层", key="r-protocol-stun", name="`PROTOCOL,STUN`", expect="open",
         probe=r"PROTOCOL\s*,\s*STUN", href=DOC + "/Rule/protocol_rule",
         why="ads 可选组以注释态收录（防 WebRTC/STUN 探测），默认关；"
             "主配置 `disable-stun` 更彻底，但插件不能声明"),
    dict(layer="规则层", key="r-dest-port", name="`DEST-PORT`", expect="used",
         probe=r"(?mi)^DEST-PORT\s*,", href=DOC + "/Rule/port_rule",
         why="153/853 等明文 DNS 端口直接拒绝；官方还支持 `80-443` 区间与 `>=443` 比较，"
             "当前按单端口精确匹配，避免误伤业务端口"),
    dict(layer="规则层", key="r-in-port", name="`IN-PORT`", expect="reject",
         probe=r"(?mi)^IN-PORT\s*,", href=DOC + "/Rule/port_rule",
         why="入站端口，插件场景用不到"),
    dict(layer="规则层", key="r-protocol", name="`PROTOCOL`", expect="used",
         probe=r"PROTOCOL\s*,", href=DOC + "/Rule/protocol_rule"),
    dict(layer="规则层", key="r-and", name="`AND`", expect="used",
         probe=r"(?m)^AND\s*,", href=DOC + "/Rule/logic_rule"),
    dict(layer="规则层", key="r-or", name="`OR`", expect="open",
         probe=r"(?m)^OR\s*,", href=DOC + "/Rule/logic_rule",
         why="`AND` 已覆盖；多个 `DOMAIN-SUFFIX` 的并集写成多条更易读，`OR` 无额外收益"),
    dict(layer="规则层", key="r-not", name="`NOT`", expect="open",
         probe=r"(?m)^NOT\s*,", href=DOC + "/Rule/logic_rule",
         why="白名单式「除这些以外都拦」风险太高，没有必须用它的场景"),
    dict(layer="规则层", key="r-ssid", name="`SSID`", expect="reject",
         probe=r"(?mi)^SSID\s*,", href=DOC + "/Rule/",
         why="「只在某个 Wi-Fi 下拦截」不是去广告的需求"),
    dict(layer="规则层", key="r-process", name="`PROCESS-NAME`", expect="reject",
         probe=r"(?mi)^PROCESS-NAME\s*,", href=DOC + "/Rule/process_rule",
         why="仅 macOS 生效，iOS 直接忽略"),
    dict(layer="规则层", key="r-domain-set", name="`DOMAIN-SET` / `RULE-SET`", expect="reject",
         probe=r"(?mi)^(DOMAIN-SET|RULE-SET)\s*,", href=DOC + "/Rule/sub_rule",
         why="远程列表拉取失败无本地兜底，表现是「广告突然全回来」且用户无感知"),
    dict(layer="规则层", key="r-final", name="`FINAL`", expect="na",
         probe=r"(?mi)^FINAL\s*,", href=DOC + "/Rule/final_rule",
         why="插件 `[Rule]` 不支持 `FINAL`，只能在主配置声明"),
    # REJECT 策略变体（rule 层动作，与复写层 reject_* 函数是两套东西）
    dict(layer="规则层", key="r-reject", name="`REJECT`（404 + 空 body）", expect="used",
         probe=r"(?m),(?:REJECT)\s*$", href=DOC + "/Policy/"),
    dict(layer="规则层", key="r-reject-drop", name="`REJECT-DROP`（丢包防重试风暴）", expect="used",
         probe=r"(?m),(?:REJECT-DROP)\s*$", href=DOC + "/Policy/",
         why="HTTPDNS 关键词域命中后 SDK 会对 200 空包秒级重试，丢包静默超时是从根上断重试"),
    dict(layer="规则层", key="r-reject-dict", name="`REJECT-DICT`（200 + `{}`）", expect="used",
         probe=r"(?m),(?:REJECT-DICT)\s*$", href=DOC + "/Policy/",
         why="上报/配置接口按 JSON 解析：返回空对象让 SDK 判定成功并清本地重试队列"),
    dict(layer="规则层", key="r-reject-img", name="`REJECT-IMG`（200 + 1px GIF）", expect="open",
         probe=r"(?m),(?:REJECT-IMG)\s*$", href=DOC + "/Policy/",
         why="meituan 可选 MITM 增强层里以注释态收录（p[0-9].meituan.net 广告图路径）——"
             "图片加载器拿到合法图像不会走「破损图→重试」，该层默认关，生效项仍为 0"),
    dict(layer="规则层", key="r-reject-array", name="`REJECT-ARRAY`（200 + `[]`）", expect="open",
         probe=r"(?m),(?:REJECT-ARR(?:AY|Y))\s*$", href=DOC + "/Policy/",
         why="当前可引用的广告端点都回对象包络（`{data:...}`），没有顶层数组端点，无法诚实启用"),

    # ---------------- Host / DNS 层 ----------------
    dict(layer="Host 层", key="h-exact", name="`域名 = 固定 IP`", expect="used",
         probe=r"(?m)^[a-z0-9][a-z0-9.-]*\s*=\s*\d+\.\d+\.\d+\.\d+\s*$",
         href=DOC + "/DNS/hostmap"),
    dict(layer="Host 层", key="h-wild", name="`*.域名 = 固定 IP`", expect="used",
         probe=r"(?m)^\*[a-z0-9.*?\[\]-]*\s*=\s*\d+\.\d+\.\d+\.\d+\s*$",
         href=DOC + "/DNS/hostmap"),
    dict(layer="Host 层", key="h-alias", name="`域名 = 域名别名`", expect="open",
         probe=r"(?m)^[a-z0-9][a-z0-9.*?\[\]-]*\s*=\s*[a-z0-9][a-z0-9.-]*\.[a-z]{2,}\s*$",
         href=DOC + "/DNS/hostmap",
         why="别名只能换解析目标，拦不住广告；拦截要的是黑洞 IP"),
    dict(layer="Host 层", key="h-server", name="`域名 = server:8.8.8.4`", expect="open",
         probe=r"(?m)=\s*server\s*:", href=DOC + "/DNS/hostmap",
         why="按域指定 DNS 服务器；本插件用全局 `dns-server` + `doh-server` 解决，按域再拆没有必要"),
    dict(layer="Host 层", key="h-ip-mode", name="`域名 = ip-mode:...`", expect="open",
         probe=r"(?m)=\s*ip-mode\s*:", href=DOC + "/DNS/hostmap",
         why="官方取值是 `v4-only`/`dual`/`prefer-v4`/`prefer-v6`/`v6-only`，其中 `v4-only` 明写"
             "「不查询 AAAA，并拒绝 IPv6 连接」——它唯一的广告相关收益是给黑洞域名补一条 v6 封口，"
             "正对 `docs/bypass-audit.md` 第 11 条 AAAA 旁路。但官方只给了 `ip-mode:` 单独使用的示例，"
             "同一域名多行（`= 127.0.0.1` + `= ip-mode:v4-only`）是否共存未文档化，"
             "因此与那条一起停在「未落地」，先做真机三步验证，不拿 1499 条生效黑洞去赌"),
    dict(layer="Host 层", key="h-ssid", name="`ssid:名称 = ...`", expect="reject",
         probe=r"(?m)^ssid\s*:", href=DOC + "/DNS/hostmap",
         why="「只在某个 Wi-Fi 下改解析」不是去广告需求"),
    dict(layer="Host 层", key="h-ip2ip", name="`IP = IP` 映射", expect="reject",
         probe=r"(?m)^\d+\.\d+\.\d+\.\d+\s*=\s*\d+\.\d+\.\d+\.\d+\s*$",
         href=DOC + "/DNS/hostmap",
         why="官方示例是 `198.51.100.10 = 192.0.2.20` 这类固定改址；广告侧 IP 由 CDN 随时轮换，"
             "按 IP 映射等于把我们已判死的「静态 IP 枚举」换个写法再来一遍"),
    dict(layer="Host 层", key="h-use-in-proxy", name="`域名 = IP, use-in-proxy=true`", expect="open",
         probe=r"use-in-proxy\s*=\s*true", href=DOC + "/DNS/hostmap",
         why="官方只写「代理内继续使用映射」，没展开映射后的 IP 是给客户端还是给节点连接用；"
             "我们的黑洞域名都落在 REJECT / DIRECT 上，不经过节点，因此既无收益也无从验证——不猜测语义"),

    # ---------------- 复写层（31 个 Action） ----------------
    dict(layer="复写层", key="w-cond-and", name="条件 `&&` / 多条件", expect="used",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*&&[^\n]*then\s+(?!script\()",
         href=DOC + "/Rewrite/rewrite_v2",
         why="开关参数 + URL 同时成立才拒绝（`${cleanFeedAds} == true && ${url} ~= ...`）"),
    dict(layer="复写层", key="w-cond-plugin-arg", name="条件引用 `[Argument]`", expect="used",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*\$\{\w+\}\s*==\s*(?:true|false)",
         href=DOC + "/Rewrite/rewrite_v2",
         why="布尔开关直接进条件；String/Number 参数按声明类型比较"),
    dict(layer="复写层", key="w-cond-method", name="条件 `${request.method}`", expect="open",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*\$\{request\.method\}",
         href=DOC + "/Rewrite/rewrite_v2",
         why="命中的广告端点全部由 URL 唯一确定，方法维度没有额外区分价值"),
    dict(layer="复写层", key="w-cond-header", name="条件 `${request/response.header[...]}`", expect="open",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*\$\{(?:request|response)\.header\[",
         href=DOC + "/Rewrite/rewrite_v2",
         why="Header 可能缺失或被网关改写，URL 条件更可靠；脚本内部已按 Content-Type 判断"),
    dict(layer="复写层", key="w-cond-status", name="条件 `${response.status}`", expect="open",
         probe=r"(?m)^\s*response\s+if\b[^\n]*\$\{response\.status\}",
         href=DOC + "/Rewrite/rewrite_v2",
         why="拒绝不依赖状态码；需要按响应内容判断时用脚本，而不是在 Rewrite 里再判一次"),
    dict(layer="复写层", key="w-capture", name="条件命名捕获 `as` / `${name.n}`", expect="reject",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*\bas\s+[A-Za-z_]\w*\s+then",
         href=DOC + "/Rewrite/rewrite_v2",
         why="广告端点按固定路径拒绝，不需要把 URL 片段回填到 Header/Body"),
    dict(layer="复写层", key="w-url-replace", name="`url.replace`", expect="open",
         probe=r"then\s+url\.replace\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="把请求改到另一个域名＝把广告请求变成正常请求，客户端仍会拿到可解析响应；拦就拦干净"),
    dict(layer="复写层", key="w-redirect", name="`redirect(302\\|307)`", expect="reject",
         probe=r"then\s+redirect\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="会把客户端送去继续请求，广告位可能被填上别的素材"),
    dict(layer="复写层", key="w-reject", name="`reject(status)`", expect="reject",
         probe=r"then\s+reject\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="官方注明返回 `text/plain`；按 JSON 解析的 SDK 会走「解析失败→重试」分支"),
    dict(layer="复写层", key="w-reject-dict", name="`reject_dict(status)`", expect="used",
         probe=r"then\s+reject_dict\s*\(", href=DOC + "/Rewrite/rewrite_v2"),
    dict(layer="复写层", key="w-reject-img", name="`reject_img(status)`", expect="reject",
         probe=r"then\s+reject_img\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="图片路径已由规则层 `REJECT-IMG` 覆盖（meituan 增强层）；同一请求再写一条 Rewrite 拒绝只会互相覆盖"),
    dict(layer="复写层", key="w-reject-array", name="`reject_array(status)`", expect="open",
         probe=r"then\s+reject_array\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="当前命中的广告端点都回对象包络（`{data:...}`），没有顶层数组的端点"),
    dict(layer="复写层", key="w-reject-video", name="`reject_video(status)`", expect="reject",
         probe=r"then\s+reject_video\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="同上，视频素材域名不进 MITM"),
    dict(layer="复写层", key="w-req-header", name="`request.header.add/set/del/replace`", expect="used",
         probe=r"then\s+request\.header\.(add|set|del|replace)\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="用 `set` 把 Accept-Encoding 降到 gzip"),
    dict(layer="复写层", key="w-res-header", name="`response.header.add/set/del/replace`", expect="open",
         probe=r"then\s+response\.header\.(add|set|del|replace)\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="响应头改写要让位给脚本（脚本自己回 `X-Soda-Plugin` 诊断头），两层同时改会互相覆盖"),
    dict(layer="复写层", key="w-req-body-replace", name="`request.body.replace`", expect="reject",
         probe=r"then\s+request\.body\.replace\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="正文级正则对 JSON 不安全（可能命中字符串内部的同名字段）"),
    dict(layer="复写层", key="w-res-body-replace", name="`response.body.replace`", expect="reject",
         probe=r"then\s+response\.body\.replace\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="同上；且命中后同阶段脚本不再执行，等于用正则换掉全部 JSON 逻辑"),
    dict(layer="复写层", key="w-req-json", name="`request.json.*`", expect="reject",
         probe=r"then\s+request\.json\.", href=DOC + "/Rewrite/rewrite_v2",
         why="本插件不改请求体；请求侧无广告载荷需要剥"),
    dict(layer="复写层", key="w-res-json-field", name="`response.json.add/delete/replace`", expect="reject",
         probe=r"then\s+response\.json\.(?:add|delete|replace)\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="soda/douyin 的响应层是字段级脚本 + 开关分支；原生 JSON 改写命中后同阶段脚本不执行，会整条废掉「保奖励」判断"),
    dict(layer="复写层", key="w-res-json-jq", name="`response.json.jq`", expect="open",
         probe=r"then\s+response\.json\.jq\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="xianyu 可选 MITM 层以注释态落地 15 条（ddgksf2013/fmz200 同域 http-response-jq 证据）；默认不生效，生效项为 0。soda/douyin 因与响应脚本互斥不用"),
    dict(layer="复写层", key="w-res-json-jq-file", name="`response.json.jq_file`", expect="reject",
         probe=r"then\s+response\.json\.jq_file\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="插件资源文件会引入包外依赖；本仓库要求自包含"),
    dict(layer="复写层", key="w-req-mock", name="`request.body.mock`", expect="reject",
         probe=r"then\s+request\.body\.mock", href=DOC + "/Rewrite/rewrite_v2",
         why="同上：改写请求体不属于本插件职责"),
    dict(layer="复写层", key="w-res-mock", name="`response.body.mock`", expect="reject",
         probe=r"then\s+response\.body\.mock", href=DOC + "/Rewrite/rewrite_v2",
         why="包络写错＝白屏，且会把同 URL 的脚本全废掉；收益只在「省一次解码」"),
    dict(layer="复写层", key="w-multi-action", name="多 Action 管道 `\\|`", expect="reject",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*then\b[^\n]*\s\|\s(?:request|response|url|reject|redirect)\.",
         href=DOC + "/Rewrite/rewrite_v2",
         why="每条命中 URL 只需要一个动作；多动作会增加同一请求的副作用面，没有收益"),
    dict(layer="复写层", key="w-reject-body", name="`reject(status, body)` 自定义 body", expect="reject",
         probe=r"then\s+reject\s*\(\s*\d+\s*,", href=DOC + "/Rewrite/rewrite_v2",
         why="自定义 body 不如 `reject_dict` 语义清楚；按 JSON 解析的 SDK 回 `{}` 最稳"),
    dict(layer="复写层", key="w-mock-file", name="`body.mock_file` / 远程文件", expect="reject",
         probe=r"\.body\.mock_file\s*\(", href=DOC + "/Rewrite/rewrite_v2",
         why="Mock 会整包替换响应，包络写错就是白屏；插件也不应依赖运行时远程拉取"),
    dict(layer="复写层", key="w-batch", name="批量数组参数", expect="open",
         probe=r"then\s+\w+\.[\w.]*\(\s*\[", href=DOC + "/Rewrite/rewrite_v2",
         why="单条规则只有一组参数，没有「同 URL 改多个头」的需求"),

    # ---------------- 脚本层 ----------------
    dict(layer="脚本层", key="s-trigger-request", name="Request Script（`request if ...`）", expect="used",
         probe=r"(?m)^\s*request\s+if\b[^\n]*then\s+script\(", href=DOC + "/Script/script_v2",
         why="广告域名阻断、开屏请求拦截在请求阶段执行，省掉一次出网"),
    dict(layer="脚本层", key="s-trigger-response", name="Response Script（`response if ...`）", expect="used",
         probe=r"(?m)^\s*response\s+if\b[^\n]*then\s+script\(", href=DOC + "/Script/script_v2"),
    dict(layer="脚本层", key="s-trigger-cron", name="Cron Script（`cron ...`）", expect="used",
         probe=r"(?m)^\s*cron\s+[^\n]*then\s+script\(", href=DOC + "/Script/script_v2",
         why="每日领取提醒；插件参数可提供动态 Cron"),
    dict(layer="脚本层", key="s-trigger-generic", name="Generic Script（`generic ...`）", expect="used",
         probe=r"(?m)^\s*generic\s+then\s+script\(", href=DOC + "/Script/script_v2",
         why="插件状态自检按钮；可配合 `img_url` 显示图标"),
    dict(layer="脚本层", key="s-trigger-network", name="Network Changed Script（`network-changed ...`）", expect="reject",
         probe=r"(?m)^\s*network-changed\s+then\s+script\(", href=DOC + "/Script/script_v2",
         why="广告拦截不依赖网络类型；网络切换时重跑脚本只会增加噪音，没有可执行动作"),
    dict(layer="脚本层", key="s-console", name="`console.log`", expect="used",
         probe=r"console\.log\s*\(", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-done", name="`$done`", expect="used",
         probe=r"\$done\s*\(", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-timeout", name="`setTimeout`", expect="reject",
         probe=r"\bsetTimeout\s*\(", href=DOC + "/Script/script_api",
         why="HTTP 脚本必须尽快 `$done`；延迟返回会挂住连接"),
    dict(layer="脚本层", key="s-interval", name="`setInterval`", expect="reject",
         probe=r"\bsetInterval\s*\(", href=DOC + "/Script/script_api",
         why="官方注明运行时里它只执行一次、且没有可靠的 clear，等于坏掉的 API"),
    dict(layer="脚本层", key="s-loon", name="`$loon`", expect="used",
         probe=r"\$loon\b", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-script-name", name="`$script.name` / `startTime`", expect="used",
         probe=r"\$script\.(name|startTime)", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-argument", name="`$argument`", expect="used",
         probe=r"\$argument\b", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-arg-subset", name="脚本参数白名单 `{${a},...}`", expect="used",
         probe=r"script\([^\n]*\{\s*\$\{", href=DOC + "/Script/script_v2",
         why="每条脚本只拿自己需要的参数，避免 20+ 个开关全量注入成 `$argument`"),
    dict(layer="脚本层", key="s-cond-multi", name="脚本条件 `&&`", expect="open",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*&&[^\n]*then\s+script\(",
         href=DOC + "/Script/script_v2",
         why="脚本条件目前只按 URL 命中；开关用 `with enable=${arg}` 控制，"
             "不再在条件里重复一次"),
    dict(layer="脚本层", key="s-cond-method", name="脚本条件 `${request.method}`", expect="open",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*\$\{request\.method\}[^\n]*then\s+script\(",
         href=DOC + "/Script/script_v2",
         why="命中的广告端点由 URL 唯一确定，方法维度没有额外区分价值"),
    dict(layer="脚本层", key="s-cond-header", name="脚本条件 `${request/response.header[...]}`", expect="open",
         probe=r"(?m)^\s*(?:request|response)\s+if\b[^\n]*\$\{(?:request|response)\.header\[[^\n]*then\s+script\(",
         href=DOC + "/Script/script_v2",
         why="Header 可能缺失或被网关改写，URL 条件更可靠；脚本内部已处理非 JSON"),
    dict(layer="脚本层", key="s-cond-status", name="脚本条件 `${response.status}`", expect="open",
         probe=r"(?m)^\s*response\s+if\b[^\n]*\$\{response\.status\}[^\n]*then\s+script\(",
         href=DOC + "/Script/script_v2",
         why="脚本内部按响应内容判断即可；把状态码写进条件会让同一端点的错误分支静默漏过"),
    dict(layer="脚本层", key="s-env-node", name="`$environment.params.nodeInfo`", expect="used",
         probe=r"params\.(nodeInfo|node)\b", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-env-policy", name="`$environment.params.policyGroup`", expect="open",
         probe=r"params\.policyGroup\b", href=DOC + "/Script/script_api",
         why="策略组只在「从策略入口手动运行」时才有值；插件状态按钮走 generic，拿不到"),
    dict(layer="脚本层", key="s-env-chain", name="`$environment.params.proxyChainInfo`", expect="open",
         probe=r"params\.proxyChainInfo\b", href=DOC + "/Script/script_api",
         why="代理链信息与去广告无关，写进状态页只是噪音"),
    dict(layer="脚本层", key="s-req-url", name="`$request.url` / `method` / `headers`", expect="used",
         probe=r"\$request\.(url|method|headers)", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-req-body", name="`$request.body`（需 `requires_body`）", expect="open",
         probe=r"\$request\.body\b", href=DOC + "/Script/script_api",
         why="本插件只改响应；请求体里没有需要剥的广告载荷"),
    dict(layer="脚本层", key="s-res-body", name="`$response.body`", expect="used",
         probe=r"readBody\s*\(\s*\$response|resp\.body|\$response\.body\b",
         href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-done-headers", name="`$done({headers})` 改响应头", expect="used",
         probe=r"(?s)\$done\(\s*\{[^{}]*?\bheaders\s*:",
         href=DOC + "/Script/script_api",
         why="回写 body 时同步补 `Content-Encoding`/诊断标记，避免过期压缩头"),
    dict(layer="脚本层", key="s-done-status", name="`$done({status})` 单独改状态码", expect="reject",
         probe=r"(?s)\$done\(\s*\{[^{}]*\bstatus\s*:",
         href=DOC + "/Script/script_api",
         why="只翻状态码、Body 仍是原广告响应，SDK 照样解析；要改回包就整包给（嵌套 `response`），"
             "单改 status 没有可用形态。此前标「已用」是探测式写漏了 `{` 边界，把嵌套回包误算成顶层用法"),
    dict(layer="脚本层", key="s-done-url", name="`$done({url})` 改请求 URL", expect="open",
         probe=r"(?s)\$done\(\s*\{[^{}]*?\burl\s*:",
         href=DOC + "/Script/script_api",
         why="改 URL 归复写层 `url.replace`：正则、捕获和替换范围都在配置里看得见。搬进脚本会变成"
             "「先 Rewrite 后 JS 再改一次」，排障时无法归因"),
    dict(layer="脚本层", key="s-done-node", name="`$done({node})` / `$done({policy})` 改本次路由", expect="reject",
         probe=r"(?s)\$done\(\s*\{[^{}]*?\b(?:node|policy)\s*:",
         href=DOC + "/Script/script_api",
         why="拦截插件替用户决定这条请求走哪个节点，等于把去广告和分流耦合；出问题时无法区分是谁改的路由"),
    dict(layer="脚本层", key="s-status", name="`$response.status`", expect="open",
         probe=r"\$response\.status\b", href=DOC + "/Script/script_api",
         why="脚本按 URL 与 content-type 就能判定广告响应；再叠状态码条件只会让错误分支静默漏过"),
    dict(layer="脚本层", key="s-h2-trailers", name="`$request/$response.h2_trailers`", expect="open",
         probe=r"\.h2_trailers\b", href=DOC + "/Script/script_api",
         why="gRPC 的 `grpc-status` 在 trailers 里；本插件命中的都是 JSON 端点，用 content-type 判断更直接"),
    dict(layer="脚本层", key="s-done-response", name="`$done({response:{status,headers,body}})` 直接回包",
         expect="used", probe=r"\$done\(\s*\{[^{}]*\bresponse\s*:",
         href=DOC + "/Script/script_api",
         why="Request Script 跳过上游、自己造响应。选它而不是复写层 `reject`：`reject` 只给 404、"
             "`reject(200,\"{}\")` 是 text/plain，广告 SDK 按 JSON 解析失败会进重试分支；"
             "脚本回包可以精确到 200 + `application/json` + `{}`，与 `reject_dict(200)` 对齐"),
    dict(layer="脚本层", key="s-store", name="`$persistentStore.read/write`", expect="used",
         probe=r"\$persistentStore\.(read|write)", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-store-remove", name="`$persistentStore.remove()`", expect="reject",
         probe=r"\$persistentStore\.remove\s*\(", href=DOC + "/Script/script_api",
         why="它会清空**全部**脚本的键，不只是当前脚本"),
    dict(layer="脚本层", key="s-store-delete", name="`$persistentStore.write(undefined, key)`", expect="used",
         probe=r"\$persistentStore\.write\(\s*(?:undefined|null)\s*,",
         href=DOC + "/Script/script_api",
         why="删单个键只能这么写：`remove()` 会清空所有键；奖励计时器用完即删，避免跨次误算"),
    dict(layer="脚本层", key="s-notify", name="`$notification.post`", expect="used",
         probe=r"\$notification\.post\s*\(", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-notify-attach", name="`attach` 对象（openUrl / clipboard / mediaUrl）",
         expect="used", probe=r'"(openUrl|clipboard)"\s*:', href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-notify-media", name="`attach.mediaUrl`（Data URI / Base64）",
         expect="open", probe=r'"mediaUrl"\s*:', href=DOC + "/Script/script_api",
         why="通知里放图要现生成 PNG，收益只是「好看」；剪贴板已经覆盖排障场景"),
    dict(layer="脚本层", key="s-http", name="`$httpClient`", expect="reject",
         probe=r"\$httpClient\.", href=DOC + "/Script/script_api",
         why="脚本外发数据是明确红线：拦截插件不该有任何出站请求"),
    dict(layer="脚本层", key="s-dns", name="`$dns.query`", expect="reject",
         probe=r"\$dns\.query\s*\(", href=DOC + "/Script/script_api",
         why="同上——它会绕过 TUN 直连 DoH，等于在插件里开一条不受控通道"),
    dict(layer="脚本层", key="s-ungzip", name="`$utils.ungzip`（Build 988+）", expect="used",
         probe=r"\$utils\.ungzip\s*\(", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-gzip", name="`$utils.gzip`", expect="open",
         probe=r"\$utils\.gzip\s*\(", href=DOC + "/Script/script_api",
         why="官方写明「改 Body 后 Loon 自己处理 Content-Encoding」，脚本再压一遍会多一次无谓运算"),
    dict(layer="脚本层", key="s-utils-ip-info", name="`$utils.geoip` / `ipasn` / `ipaso`", expect="reject",
         probe=r"\$utils\.(?:geoip|ipasn|ipaso)\s*\(", href=DOC + "/Script/script_api",
         why="IP 地理/ASN 查询与「拦哪家广告」无关，还会给脚本引入 IP 数据库依赖"),
    dict(layer="脚本层", key="s-aes", name="`$crypto.aes.encrypt/decrypt`", expect="reject",
         probe=r"\$crypto\.aes\b", href=DOC + "/Script/script_api",
         why="没有需要解密的载荷；拿到密钥也属于破解客户端协议"),
    dict(layer="脚本层", key="s-config-get", name="`$config.getConfig()`", expect="used",
         probe=r"\$config\.getConfig\s*\(", href=DOC + "/Script/script_api"),
    dict(layer="脚本层", key="s-config-selected", name="`$config.getSelectedPolicy`", expect="open",
         probe=r"\$config\.getSelectedPolicy\s*\(", href=DOC + "/Script/script_api",
         why="要读的是「当前节点」，`$environment.params.nodeInfo` 已给，且不依赖策略组名字"),
    dict(layer="脚本层", key="s-config-sub", name="`$config.getSubPolicies`", expect="reject",
         probe=r"\$config\.getSubPolicies\s*\(", href=DOC + "/Script/script_api",
         why="异步读策略组列表；插件不管理节点，读完也没有动作可做"),
    dict(layer="脚本层", key="s-config-set", name="`$config.setSelectPolicy`", expect="reject",
         probe=r"\$config\.setSelectPolicy\s*\(", href=DOC + "/Script/script_api",
         why="自动切节点＝替用户改全局状态，出问题时无法归因"),
    dict(layer="脚本层", key="s-config-mode", name="`$config.setRunningModel`", expect="reject",
         probe=r"\$config\.setRunningModel\s*\(", href=DOC + "/Script/script_api",
         why="同上；只读 `running_model` 做诊断，不改"),

    # ---------------- 脚本规则属性（with） ----------------
    dict(layer="脚本属性", key="o-enable", name="`enable`（可动态）", expect="used",
         probe=r"with[^\n]*\benable\s*=", href=DOC + "/Script/script_v2"),
    dict(layer="脚本属性", key="o-tag", name="`tag`", expect="used",
         probe=r"with[^\n]*\btag\s*=", href=DOC + "/Script/script_v2"),
    dict(layer="脚本属性", key="o-debug", name="`debug`（可动态）", expect="used",
         probe=r"with[^\n]*\bdebug\s*=", href=DOC + "/Script/script_v2"),
    dict(layer="脚本属性", key="o-timeout", name="`timeout`", expect="used",
         probe=r"with[^\n]*\btimeout\s*=", href=DOC + "/Script/script_v2"),
    dict(layer="脚本属性", key="o-body", name="`requires_body`", expect="used",
         probe=r"with[^\n]*\brequires_body\s*=", href=DOC + "/Script/script_v2"),
    dict(layer="脚本属性", key="o-binary", name="`binary_body_mode`", expect="open",
         probe=r"with[^\n]*\bbinary_body_mode\s*=", href=DOC + "/Script/script_v2",
         why="它只改变 Body 的表示形式（Uint8Array），本插件处理的都是 JSON 文本"),
    dict(layer="脚本属性", key="o-img", name="`img_url`", expect="used",
         probe=r"with[^\n]*\bimg_url\s*=", href=DOC + "/Script/script_v2"),

    # ---------------- 参数层 ----------------
    dict(layer="参数层", key="a-switch", name="`switch` 控件", expect="used",
         probe=r"(?m)^\w+\s*=\s*switch\s*,", href=DOC + "/Plugin/"),
    dict(layer="参数层", key="a-select", name="`select` 控件", expect="used",
         probe=r"(?m)^\w+\s*=\s*select\s*,", href=DOC + "/Plugin/"),
    dict(layer="参数层", key="a-input", name="`input` 控件", expect="used",
         probe=r"(?m)^\w+\s*=\s*input\s*,", href=DOC + "/Plugin/"),
    dict(layer="参数层", key="a-type-number", name="`type=number`", expect="open",
         probe=r"type\s*=\s*number\b", href=DOC + "/Plugin/",
         why="插件的可调项只有开关、二选一和 cron 表达式；cron 是字符串，不是数值"),
    dict(layer="参数层", key="a-type-string", name="`type=string`", expect="used",
         probe=r"type\s*=\s*string\b", href=DOC + "/Plugin/"),
    dict(layer="参数层", key="a-type-boolean", name="`type=boolean`", expect="open",
         probe=r"type\s*=\s*boolean\b", href=DOC + "/Plugin/",
         why="只有 `input` / `select` 需要声明类型，而两者都不接受 boolean；`switch` 本身就返回布尔"),

    # ---------------- 插件段落 ----------------
    dict(layer="插件段落", key="p-general", name="`[General]`", expect="used",
         probe=r"(?m)^\[General\]", href=DOC + "/Plugin/"),
    dict(layer="插件段落", key="p-rule", name="`[Rule]`", expect="used",
         probe=r"(?m)^\[Rule\]", href=DOC + "/Plugin/"),
    dict(layer="插件段落", key="p-rewrite", name="`[Rewrite]`", expect="used",
         probe=r"(?m)^\[Rewrite\]", href=DOC + "/Plugin/"),
    dict(layer="插件段落", key="p-script", name="`[Script]`", expect="used",
         probe=r"(?m)^\[Script\]", href=DOC + "/Plugin/"),
    dict(layer="插件段落", key="p-mitm", name="`[MITM]`", expect="used",
         probe=r"(?m)^\[MITM\]", href=DOC + "/Plugin/"),
    dict(layer="插件段落", key="p-host", name="`[Host]`", expect="used",
         probe=r"(?m)^\[Host\]", href=DOC + "/Plugin/"),
    dict(layer="插件段落", key="p-arg", name="`[Argument]`", expect="used",
         probe=r"(?m)^\[Argument\]", href=DOC + "/Plugin/"),
    dict(layer="插件段落", key="p-general-dns", name="`[General]` 的 `dns-server` / `doh-server` / `doh3-server`",
         expect="used",
         probe=r"(?m)^\s*(?:dns-server|doh-server|doh3-server)\s*=", href=DOC + "/Plugin/"),
    dict(layer="插件段落", key="p-general-doq", name="`[General]` 的 `doq-server`", expect="open",
         probe=r"(?m)^\s*doq-server\s*=", href=DOC + "/Plugin/",
         why="DoQ 要配 853 端口且很多网络直接封 UDP 853；现有 DoH/DoH3 已覆盖同三家 DNS，"
             "再加 DoQ 只增加失败面，不增加广告拦截效果"),
    dict(layer="插件段落", key="p-general-routing", name="`[General]` 的 `bypass-tun` / `skip-proxy` / `real-ip`",
         expect="reject",
         probe=r"(?m)^\s*(?:bypass-tun|skip-proxy|always-real-ip|real-ip)\s*=",
         href=DOC + "/Plugin/",
         why="这些是「让流量绕过代理 / 改写解析结果」的全局路由开关，属用户主配置主权；"
             "插件替用户改会让别家规则或局域网访问静默失效，且与去广告无关"),
    dict(layer="插件段落", key="p-general-include-tun", name="`[General]` 的 `include-tun`（Build 1007+）",
         expect="reject", probe=r"(?m)^\s*include-tun\s*=", href=DOC + "/Plugin/",
         why="仅 Build 1007+ 且同样是全局路由开关；3.5.2(996) 不识别，写进去等于给未来埋雷"),
    dict(layer="插件段落", key="p-general-ipv6-vif", name="`[General]` 的 `ipv6-vif`（Build 1007+）",
         expect="reject", probe=r"(?m)^\s*ipv6-vif\s*=", href=DOC + "/Plugin/",
         why="同上：3.5.2 不识别，且改 IPv6 出口接口会影响整个设备的连通性，插件无权替用户决定"),
    dict(layer="插件段落", key="p-iprewrite", name="`[IP Rewrite]`", expect="open",
         probe=r"(?m)^\[IP Rewrite\]", href=DOC + "/Plugin/",
         why="作为广告目标 IP 的拦截手段是死路（IP 随时变）；唯一落地形态是 16 条 HTTPDNS 网关"
             "单 IPv4 以注释态收录（Build 1007+，默认关），生效项为 0"),

    # ---------------- 主配置（[General] 非白名单键 / 节点与策略） ----------------
    dict(layer="主配置", key="m-hijack-dns", name="`[General]` 的 `hijack-dns`（3.2.5+）", expect="na",
         probe=r"(?m)^\s*hijack-dns\s*=", href=DOC + "/General/",
         why="把指定目标的 UDP DNS 查询劫持并返回 Fake IP。插件 [General] 白名单没有此项；"
             "劫持范围（`*:53` 还是个别 IP）是主配置主权，写在文档清单里供用户自己决定"),
    dict(layer="主配置", key="m-reject-mode", name="`domain-reject-mode` / `dns-reject-mode`", expect="na",
         probe=r"(?m)^\s*(?:domain-reject-mode|dns-reject-mode)\s*=", href=DOC + "/General/",
         why="决定域名拒绝发生在 DNS 阶段还是转发阶段、以 LoopbackIP / NoAnswer / NXDOMAIN 哪种应答拒绝；"
             "两项均不在插件 [General] 白名单内。官方还提醒 HTTP Proxy 与 TUN 下可拦到的系统 DNS 较少，"
             "所以部分请求仍会在转发阶段被拒绝——这正是插件层继续保留规则层 REJECT 的原因"),
    dict(layer="主配置", key="m-network-switch", name="`ssid-trigger` / `interface-mode`", expect="na",
         probe=r"(?m)^\s*(?:ssid-trigger|interface-mode)\s*=", href=DOC + "/General/",
         why="按 Wi-Fi/蜂窝切换 Loon 运行模式、指定出口网络接口，属设备级网络主权，与广告拦截无关"),
    dict(layer="主配置", key="m-udp-control", name="`disable-udp-ports` / `disable-stun` / `udp-fallback-mode`",
         expect="na", probe=r"(?m)^\s*(?:disable-udp-ports|disable-stun|udp-fallback-mode)\s*=",
         href=DOC + "/General/",
         why="插件不可声明。STUN 拦截我们已用注释态 `PROTOCOL,STUN` 规则落地；`disable-udp-ports,443` "
             "会连带掐掉 QUIC，`udp-fallback-mode=REJECT` 影响所有不支持 UDP 的节点业务"),
    dict(layer="主配置", key="m-lan-access", name="`allow-wifi-access` / `wifi-access-*-port`", expect="na",
         probe=r"(?m)^\s*(?:allow-wifi-access|wifi-access-(?:http|socks5)-port)\s*=", href=DOC + "/General/",
         why="把 Loon 变成局域网代理入口：扩大监听面、与去广告无关，且端口选择属用户环境"),
    dict(layer="主配置", key="m-speedtest", name="`proxy-test-url` / `internet-test-url` / `test-timeout`",
         expect="na", probe=r"(?m)^\s*(?:proxy-test-url|internet-test-url|test-timeout)\s*=",
         href=DOC + "/General/",
         why="节点测速与连通性探测参数；插件不管理节点，改测速地址还会影响用户其它策略组"),
    dict(layer="主配置", key="m-resource-parser", name="`resource-parser`（订阅解析脚本）", expect="na",
         probe=r"(?m)^\s*resource-parser\s*=", href=DOC + "/General/",
         why="主配置侧的订阅解析入口。插件侧的对应能力是 `#!type=parser`（已在元数据层单列），"
             "但本仓库不出解析器插件"),
    dict(layer="主配置", key="m-db-url", name="`geoip-url` / `ipasn-url`（自定义数据库）", expect="reject",
         probe=r"(?m)^\s*(?:geoip-url|ipasn-url)\s*=", href=DOC + "/General/",
         why="换 GeoIP/ASN 数据源会影响整机分流判定；插件既不能声明，也没有需要它的拦截逻辑"
             "（`GEOIP`/`IP-ASN` 大网段本身已判死）"),
    dict(layer="主配置", key="m-deprecated", name="已弃用参数（`ipv6` / `force-http-engine-hosts` 等）",
         expect="reject",
         probe=r"(?m)^\s*(?:ipv6|switch-node-after-failure-times|force-http-engine-hosts|skip-first-packet)\s*=",
         href=DOC + "/General/",
         why="官方明确「仅用于识别旧配置，新配置不应继续使用」：`ipv6` 自 3.2.3(754) 由 `ip-mode` 替代、"
             "`force-http-engine-hosts` 自 3.2.3(787) 弃用、`skip-first-packet` 自 3.5.0(968) 由 Loon 自动识别。"
             "写进插件等于给升级埋雷"),
    dict(layer="主配置", key="m-node-section", name="`[Node]` / `[Proxy Group]` / `[Remote Rule]` / `[Remote Script]`",
         expect="na", probe=r"(?m)^\s*\[(?:Node|Proxy Group|Remote Rule|Remote Script)\]", href=DOC + "/Policy/",
         why="节点、策略组与远程引用是主配置段落；插件规则只能落到 DIRECT / REJECT 族 / PROXY，"
             "由用户在策略组里选，插件不替用户建组"),

    dict(layer="主配置", key="m-sub-dns", name="订阅 Section 的 `[DNS]` / `[Proxy]` / Host Map 合并", expect="na",
         probe=r"(?m)^\s*\[DNS\]", href=DOC + "/Node/subscription",
         why="订阅文件可以整段下发 `[DNS]` / `[Host]` / `[Proxy]`，且「Host Map 加载后合并到当前 Host Map，"
             "并优先于主配置」。插件没有 `[DNS]` 段，节点与订阅也不属插件分发物——"
             "这条的真实意义是排障口径：用户订阅里的同名映射会盖掉主配置，我们的插件 [Host] 若某天不生效，"
             "先查订阅 Host Map，不要先怀疑正则"),

    # ---------------- 旧版语法（可用但刻意不用） ----------------
    dict(layer="旧版语法", key="l-legacy-rewrite", name="旧版 Rewrite（`正则 header-del …` / `reject-200` / `\\x20`）",
         expect="reject",
         probe=r"(?m)(?:^\s*\S+\s+(?:header-(?:add|del|replace(?:-regex)?)|response-header-(?:add|del|replace)|"
               r"reject-200|mock-(?:request|response)-body|request-body-json-jq|response-body-json-jq)[ =]|\\x20)",
         href=DOC + "/Rewrite/",
         why="官方定位「仅用于维护旧配置，不再扩展」。它按空格拆参数，正则含空格要写 `\\x20`，"
             "类型与批量数组也无从表达；本仓库全部落在 3.5.1(978)+ 新语法，lint 禁止旧 token 出现"),
    dict(layer="旧版语法", key="l-legacy-script", name="旧版 Script（`http-request ^regex script-path=…`）",
         expect="reject",
         probe=r"(?m)(?:^\s*(?:http-request|http-response)\s|script-path\s*=)", href=DOC + "/Script/",
         why="3.5.1(983) 起五类脚本统一为 `<type> if <条件> then script(...) with <属性>`。"
             "旧语法仍作输入兼容但不再输出，混用会让条件变量、`with` 属性名（`img-url` vs `img_url`）分两套口径"),

    # ---------------- 分发与外部控制 ----------------
    dict(layer="分发", key="d-import-scheme", name="`loon://import?…` 与 `nsloon.com/openloon/` 通用链接",
         expect="na", probe=r"(?m)^\s*(?:loon://|https://www\.nsloon\.com/openloon/)", href=DOC + "/Scheme/",
         why="导入入口（插件/规则/解析器/图标集），不是插件段落能力：URL 写在 README 徽章与安装链接里，"
             "自定义 Scheme 在网页里打不开时用 `https://www.nsloon.com/openloon/` 等价替换。"
             "本仓 16 个插件各自都用上了（38 条链接，其中 25 条安装链接），但探测语料只有插件文件与脚本源码，"
             "README 里的链接不属于「插件段落能力」，所以仍记 na；**生效与否由 lint 的 "
             "`check_scheme_links()` 按官方 Scheme 页语法逐条校验**（资源键 7 种、地址必须 URL 编码、"
             "`<slug>/<slug>.plugin` 自证、指向的插件文件必须存在）"),
    dict(layer="分发", key="d-control-scheme", name="`loon://on|off|flowmodel=|proxymode=|update?sub=all`",
         expect="na", probe=r"(?m)^\s*loon://(?:on|off|flowmodel|proxymode|update)", href=DOC + "/Scheme/",
         why="给快捷指令/其它 App 控制 Loon 的外部接口，插件内声明不了；脚本侧的同类能力"
             "（`$config.setRunningModel`、通知 `attach.openUrl`）已各自判死。"
             "文档里写到的 `on/off/editconfig/flowmodel=/proxymode=/update?sub=all` 六种操作同样受 "
             "`check_scheme_links()` 的官方取值表白名单约束——自造取值（如 `flowmodel=fast`）直接报错"),

    # ---------------- 元数据 ----------------
    dict(layer="元数据", key="m-name", name="`#!name`", expect="used", probe=r"(?m)^#!name\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-desc", name="`#!desc`", expect="used", probe=r"(?m)^#!desc\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-author", name="`#!author`", expect="used", probe=r"(?m)^#!author\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-version", name="`#!version`（官方查不到该键）", expect="undocumented",
         token="METADATA.version",
         probe=r"(?m)^#!version\s*=", href=DOC + "/Plugin/",
         why="官方 Plugin 页把插件信息字段列成一张表：`#!name`/`#!desc`/`#!author`/`#!homepage`/`#!icon`/"
             "`#!system`/`#!system_version`/`#!loon_version`/`#!date`/`#!tag`/`#!type` 共 11 个，**没有 `#!version`**；"
             "整站 grep 也只有 `system_version` / `loon_version`。它是社区插件的通行写法，Loon 大概率原样忽略"
             "（插件面板显示的版本来自 `#!date` 的「按原样显示」语义）。16 个插件都带着它：删掉最多丢一个"
             "可能根本不存在的显示项，留着也不影响解析——但它不是能力，不进利用率。取证见 `docs/device-checklist.md`"),
    dict(layer="元数据", key="m-homepage", name="`#!homepage`", expect="used", probe=r"(?m)^#!homepage\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-open-url", name="`#!openUrl`（官方查不到该键）", expect="undocumented",
         token="METADATA.openurl",
         probe=r"(?m)^#!openUrl\s*=", href=DOC + "/Plugin/",
         why="同上，官方 11 个 `#!` 字段里没有 `#!openUrl`；`openUrl` 只出现在 Script API 的 "
             "`$notification.post(..., attach)` 里，是另一个语法位。我们用它把插件 README 变成用户可点的入口，"
             "属于「社区约定 + 可能真的生效」——真机确认插件卡片是否会跳到该 URL，生效则升回 used，"
             "不生效则删除该行（`#!homepage` 已经在指仓库主页，功能不缺失）"),
    dict(layer="元数据", key="m-icon", name="`#!icon`", expect="used", probe=r"(?m)^#!icon\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-system", name="`#!system`", expect="used", probe=r"(?m)^#!system\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-system-version", name="`#!system_version`", expect="open",
         probe=r"(?m)^#!system_version\s*=", href=DOC + "/Plugin/",
         why="一个值同时约束 `#!system` 里列的**所有**平台：ads 写了 `iOS,iPadOS,tvOS,macOS`，"
             "填 15.0 等于要求 macOS 15 / tvOS 15。不填＝全部支持，比填错安全"),
    dict(layer="元数据", key="m-loon-version", name="`#!loon_version`", expect="used", probe=r"(?m)^#!loon_version\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-date", name="`#!date`", expect="used", probe=r"(?m)^#!date\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-tag", name="`#!tag`", expect="used", probe=r"(?m)^#!tag\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-type", name="`#!type`", expect="used", probe=r"(?m)^#!type\s*=", href=DOC + "/Plugin/"),
    dict(layer="元数据", key="m-type-parser", name="`#!type=parser`（规则/复写片段）", expect="reject",
         probe=r"(?m)^#!type\s*=\s*parser\b", href=DOC + "/Plugin/",
         why="parser 型插件只补规则/复写、不能带脚本与参数面板；本项目每个插件都要带 "
             "JS 与可关开关，必须是 normal 型"),
]

LAYER_ORDER = ["传输层", "规则层", "Host 层", "复写层", "脚本层", "脚本属性", "参数层",
               "插件段落", "主配置", "旧版语法", "分发", "元数据"]

STATUS_LABEL = {
    "used": "✅ 已用",
    "open": "🟡 可用未用",
    "reject": "❌ 判死",
    "na": "— 不适用",
    "undocumented": "⚪ 未文档化",
}


def evaluate():
    """逐条探测，返回 (rows, drift)。"""
    rows = []
    drift = []
    for cap in CAPABILITIES:
        rx = re.compile(cap["probe"])
        hits = []
        # `#!` 元数据行本身以 # 开头，会被 strip_hash_comments 当注释删掉，
        # 所以这一层必须在原始文本上匹配。
        corpus = ((PLUGINS if cap["layer"] == "元数据" else PLUGIN_CFG).items())
        for name, text in list(corpus) + list(SRC_CODE.items()):
            if rx.search(text):
                hits.append(name)
        actual = "used" if hits else "open"
        # 未文档化条目：声明的是「插件里带着一个官方查不到的 token」。探到才算数；
        # 探不到说明 token 已经没了，这行声明就该跟着删——留着会变成「凭空声称带过」。
        if cap["expect"] == "undocumented":
            actual = "undocumented" if hits else "absent"
            if not hits:
                drift.append(
                    "%s（%s）：标为未文档化但已探测不到该 token —— 要么恢复写法，要么删掉这行声明"
                    % (cap["layer"], cap["key"])
                )
            if not cap.get("why"):
                drift.append("%s（%s）：未文档化必须写清「为什么还留着」" % (cap["layer"], cap["key"]))
            # token 链接把这一行钉在 tools/loon-token-audit.py 的例外表上：
            # `SECTION.token` 形式由反向对差负责，`lint:` 前缀表示该 token 由 lint 的键面门禁登记。
            if not cap.get("token"):
                drift.append(
                    "%s（%s）：未文档化必须登记 token 链接（`段名.token` 或 `lint:说明`），"
                    "否则例外表和能力表会各说各话" % (cap["layer"], cap["key"])
                )
        # 判死 / 不适用的条目：探到用法说明「判死结论被推翻」，也是漂移
        elif cap["expect"] in ("reject", "na") and hits:
            drift.append(
                "%s（%s）：标为 %s 但检测到用法 @ %s"
                % (cap["layer"], cap["key"], cap["expect"], ",".join(hits[:3]))
            )
        elif cap["expect"] == "used" and not hits:
            drift.append("%s（%s）：标为已用但没检测到用法" % (cap["layer"], cap["key"]))
        elif cap["expect"] == "open" and hits:
            drift.append(
                "%s（%s）：标为可用未用但检测到用法 @ %s —— 要么改判已用，要么删掉"
                % (cap["layer"], cap["key"], ",".join(hits[:3]))
            )
        rows.append(dict(cap, actual=actual, hits=hits))
    return rows, drift


def summarize(rows):
    out = []
    for layer in LAYER_ORDER:
        items = [r for r in rows if r["layer"] == layer]
        used = sum(1 for r in items if r["actual"] == "used" or r["expect"] == "used")
        open_ = sum(1 for r in items if r["actual"] != "used" and r["expect"] == "open")
        reject = sum(1 for r in items if r["expect"] == "reject")
        na = sum(1 for r in items if r["expect"] == "na")
        undoc = sum(1 for r in items if r["expect"] == "undocumented")
        # 判死/不适用条目如果真被用上了，按已用计入（保守）
        total = used + open_
        pct = (100.0 * used / total) if total else 0.0
        out.append(dict(layer=layer, used=used, open=open_, reject=reject, na=na,
                        undoc=undoc, total=total, pct=pct))
    return out


def render_console(rows, summary):
    print("Loon 能力覆盖 / 利用率")
    print("=" * 82)
    print("%-10s %5s %5s %5s %5s %7s %8s"
          % ("层", "已用", "未用", "判死", "不适用", "未文档化", "利用率"))
    print("-" * 82)
    tu = to = tr = tn = td = 0
    for s in summary:
        print("%-10s %5d %5d %5d %5d %7d %7.1f%%"
              % (s["layer"], s["used"], s["open"], s["reject"], s["na"], s["undoc"], s["pct"]))
        tu += s["used"]; to += s["open"]; tr += s["reject"]; tn += s["na"]; td += s["undoc"]
    print("-" * 82)
    print("%-10s %5d %5d %5d %5d %7d %7.1f%%"
          % ("合计", tu, to, tr, tn, td, 100.0 * tu / (tu + to) if (tu + to) else 0))
    print()
    print("缺口（可用未用）：")
    for r in rows:
        if r["actual"] != "used" and r["expect"] == "open":
            print("  · %s / %s —— %s" % (r["layer"], r["name"], r.get("why", "")))
    if td:
        print()
        print("未文档化（官方查不到、我们却带着的 token，不进分子也不进分母）：")
        for r in rows:
            if r["expect"] == "undocumented":
                print("  · %s / %s —— %s" % (r["layer"], r["name"], r.get("why", "")))


def render_md(rows, summary):
    lines = []
    lines.append("# Loon 能力覆盖与利用率")
    lines.append("")
    lines.append("> 本文由 `tools/loon-coverage.py --write` 生成，**不要手改**。")
    lines.append("> 改能力表请改脚本里的 `CAPABILITIES`，再跑一次。")
    lines.append("")
    lines.append("口径：**利用率 = 已用 /（已用 + 可用未用）**。")
    lines.append("判死（❌）、不适用（—）与未文档化（⚪）都不进分母——判死得越认真分数越低，"
                 "激励就反了；而未文档化根本不是 Loon 的公开能力，进分子就是虚报。")
    lines.append("「已用」是**探测出来的**：脚本在插件有效行与脚本源码里找实际写法，"
                 "注释里提到不算。")
    lines.append("")
    lines.append("**⚪ 未文档化**是第十九轮新增的一档：官方 26 个正文页里查不到、我们却在插件里"
                 "带着的 token。它的存在本身就是一条待办——要么拿到真机证据证明 Loon 认它，"
                 "要么把这一行从插件里删掉。它既不进分子也不进分母。"
                 "「查不到」这句话第二十一轮起由 `npm run tokens` 机器复核：`--fetch` 当场记录官方"
                 "正文页清单，每页命中数写进 `absent_claims`，非 0 即报「断言已被推翻」；"
                 "本行也必须带 `token=` 链接指向 `tools/loon-token-audit.py` 的例外表，两边脱钩就红。")
    lines.append("")
    lines.append("**主配置层的 0% 是插件能力分母口径**：插件不能声明 `[Proxy]`/`[Proxy Group]`/"
                 "`FINAL` 等主配置段落，所以这些条目记为不适用，不代表主配置没有落地。"
                 "主配置的实际基线见 `examples/loon.conf`，插件外能力台账见 "
                 "`docs/loon-max-config.md`。")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append("| 层 | 已用 | 可用未用 | 判死 | 不适用 | 未文档化 | 利用率 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    tu = to = tr = tn = td = 0
    for s in summary:
        lines.append("| %s | %d | %d | %d | %d | %d | **%.0f%%** |"
                     % (s["layer"], s["used"], s["open"], s["reject"], s["na"],
                        s["undoc"], s["pct"]))
        tu += s["used"]; to += s["open"]; tr += s["reject"]; tn += s["na"]; td += s["undoc"]
    lines.append("| **合计** | **%d** | **%d** | **%d** | **%d** | **%d** | **%.0f%%** |"
                 % (tu, to, tr, tn, td, 100.0 * tu / (tu + to) if (tu + to) else 0))
    lines.append("")

    for layer in LAYER_ORDER:
        items = [r for r in rows if r["layer"] == layer]
        if not items:
            continue
        lines.append("## %s" % layer)
        lines.append("")
        lines.append("| 能力 | 状态 | 说明 |")
        lines.append("|---|---|---|")
        for r in items:
            status = STATUS_LABEL[r["expect"]]
            why = r.get("why", "")
            if r["expect"] == "used" and not why:
                why = "已落地"
            if r["expect"] in ("reject", "na") and r["actual"] == "used":
                why = "⚠️ 检测到用法，与判死结论冲突"
            if r["expect"] == "undocumented" and r["actual"] != "undocumented":
                why = "⚠️ 探测不到该 token：插件里已经不带它了，这行声明该删或写法该恢复"
            lines.append("| %s | %s | %s |" % (r["name"], status, why))
        lines.append("")

    lines.append("## 怎么用这份表")
    lines.append("")
    lines.append("1. **看合计没用**。合计低是正常的：Loon 有一半能力是节点、策略、"
                 "订阅管理，跟去广告无关。")
    lines.append("2. **看每层的「可用未用」**。那是真正还没榨干的地方，每条都附了不用的理由；"
                 "理由站不住就去做。")
    lines.append("3. **看判死那列有没有 ⚠️**。出现了就是结论被推翻（代码里又用回去了），"
                 "`--check` 会直接失败。")
    lines.append("4. **未文档化（⚪）是有数量的债务**。每一条都必须在文档里写清「为什么还留着」，"
                 "并且不被算进任何能力宣称；新增一条需要同时补真机取证步骤（`docs/device-checklist.md`）。")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv):
    rows, drift = evaluate()
    summary = summarize(rows)

    if "--check" in argv:
        if drift:
            print("coverage drift: %d" % len(drift), file=sys.stderr)
            for d in drift:
                print("  - " + d, file=sys.stderr)
            return 1
        # 生成的 md 必须与当前能力表一致，否则报表会悄悄过期
        want = render_md(rows, summary)
        have = read(OUT_MD)
        if have != want:
            print("coverage doc is stale: run `python3 tools/loon-coverage.py --write`",
                  file=sys.stderr)
            return 1
        tu = sum(s["used"] for s in summary)
        to = sum(s["open"] for s in summary)
        td = sum(s["undoc"] for s in summary)
        print("coverage ok: used=%d open=%d reject=%d na=%d undocumented=%d  utilization=%.1f%%"
              % (tu, to, sum(s["reject"] for s in summary), sum(s["na"] for s in summary), td,
                 100.0 * tu / (tu + to) if (tu + to) else 0))
        return 0

    if "--write" in argv:
        md = render_md(rows, summary)
        d = os.path.dirname(OUT_MD)
        if not os.path.isdir(d):
            os.makedirs(d)
        io.open(OUT_MD, "w", encoding="utf-8").write(md)
        print("wrote %s (%d lines)" % (os.path.relpath(OUT_MD, ROOT), md.count("\n")))

    if "--json" in argv:
        print(json.dumps([{k: r[k] for k in ("layer", "key", "name", "expect", "actual")}
                          for r in rows], ensure_ascii=False, indent=2))
        return 0

    render_console(rows, summary)
    if drift:
        print()
        print("⚠️ 漂移 %d 条：" % len(drift))
        for d in drift:
            print("  - " + d)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
