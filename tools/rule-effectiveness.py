#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则有效率审计：「写了」不等于「生效」。
==================================================

前面两轮分别量化了「Loon 的能力用了多少」和「广告类型覆盖了多少」，
但两者都有一个共同盲区：它们只统计**声明**，不检查**前提**。

一条 `USER-AGENT,httpdns*,REJECT` 写在没有 `[MITM]` 段的插件里，
它在能力表上是「已用」，在规则数上是「+1」，但它可能一次都不会命中——
User-Agent 是 HTTP 请求头，未解密的 HTTPS 里根本看不到。

本工具把每条规则的**生效前提**显式化，并检查插件是否提供了该前提：

    none   连接层/DNS 层即可判定（域名、IP、端口、协议）
    plain  需要完整 URL/请求头，但正则锚定了明文 `^http://`
    mitm   需要 HTTP 报文内容 —— 必须由 [MITM] 解密提供

判定为 mitm 但插件没有 [MITM] 段的规则 = **存疑**。

存疑不等于错。官方没有逐字写明「USER-AGENT 未解密时是否匹配」，
所以本工具**不删规则**，而是要求每条存疑规则登记 waiver
（保留理由 + 真机验证方法）。没有 waiver 就 --check 失败。

这个设计与 ad-surface-audit 的 `blocked` 断言同源：
**允许存疑存在，但禁止存疑沉默。**

用法
----
    python3 tools/rule-effectiveness.py          看报表
    python3 tools/rule-effectiveness.py --write 重写 docs/rule-effectiveness.md
    python3 tools/rule-effectiveness.py --check  门禁（缺省接入 npm run check）

退出码：0 通过；1 有未登记 waiver 的存疑规则、失效 waiver、或文档过期。
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(ROOT, "plugins")
OUT_MD = os.path.join(ROOT, "docs", "rule-effectiveness.md")

DOC = "https://nsloon.app/docs"


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


PLUGINS = load_plugins()


def strip_hash_comments(text):
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))


PLUGIN_CFG = {k: strip_hash_comments(v) for k, v in PLUGINS.items()}


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


# ---------------------------------------------------------------------------
# 前提判定
# ---------------------------------------------------------------------------
# RANK 越大，前提越强（越依赖解密）
RANK = {"none": 0, "plain": 1, "mitm": 2}
LABEL = {
    "none": "连接层",
    "plain": "仅明文",
    "mitm": "需解密",
}

# 这些规则类型依赖 HTTP 报文内容，未解密时看不到
HEADER_RULE_TYPES = {"USER-AGENT"}

# URL-REGEX 比较特殊：锚定 ^http:// 的只吃明文流量，不需要解密
URL_RULE_TYPES = {"URL-REGEX"}

# 逻辑规则：前提取内部子规则里最强的那个
LOGIC_RULE_TYPES = {"AND", "OR", "NOT"}

# 连接层可判定的类型（其余未知类型按 none 处理，避免误报）
CONN_RULE_TYPES = {
    "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD",
    "DOMAIN-SET", "DOMAIN-REGEX", "IP-CIDR", "IP-CIDR6", "IP-ASN",
    "GEOIP", "DEST-PORT", "SRC-PORT", "IN-PORT", "PROTOCOL",
    "PROCESS-NAME", "SRC-IP", "DEST-IP", "RULE-SET",
    "FINAL", "MATCH", "PASS", "SUB-RULE",
}

SUB_RULE_RX = re.compile(r"\(([A-Z][A-Z0-9-]*)\s*,\s*([^()]*)\)")


def unescape_rx(rx):
    """插件里正则常写成 ^http:\\/\\/，还原成 ^http:// 便于锚定判断。"""
    return rx.replace("\\/", "/")


def is_plaintext_anchored(rx):
    """URL 正则是否只吃明文 HTTP（锚定 ^http:// 而非 ^https?://）。"""
    r = unescape_rx(rx)
    return r.startswith("^http://") or r.startswith("^http:/")


def premise_of_rule(kind, arg):
    """返回 (前提, 子规则列表)。"""
    kind = (kind or "").upper()
    if kind in LOGIC_RULE_TYPES:
        subs = []
        worst = "none"
        for sk, sa in SUB_RULE_RX.findall(arg or ""):
            p, _ = premise_of_rule(sk, sa)
            subs.append((sk, sa, p))
            if RANK[p] > RANK[worst]:
                worst = p
        return worst, subs
    if kind in HEADER_RULE_TYPES:
        return "mitm", []
    if kind in URL_RULE_TYPES:
        # 只看域名、没有路径部分的 URL 正则，连接层就能判定
        body = unescape_rx(arg or "")
        if is_plaintext_anchored(body):
            return "plain", []
        return "mitm", []
    return "none", []


def strongest(*premises):
    return max(premises, key=lambda p: RANK[p]) if premises else "none"


# ---------------------------------------------------------------------------
# 解析三条会「依赖前提」的段
# ---------------------------------------------------------------------------

RULE_LINE_RX = re.compile(r"^([A-Z][A-Z0-9-]*)\s*,\s*(.+)$")

# Script / Rewrite 条件里形如 ${url} ~= /正则/
URL_COND_RX = re.compile(r"\$\{url\}\s*~=\s*/(.+?)/([a-z]*)\)?")

REWRITE_KIND_RX = re.compile(r"^(request|response|cron|network-changed|generic)\b")


def parse_rules(plugin, text):
    """[Rule] 段：一行一条 `TYPE,arg,POLICY`。"""
    out = []
    for line in section(text, "Rule"):
        m = RULE_LINE_RX.match(line)
        if not m:
            continue
        kind, rest = m.group(1), m.group(2)
        # arg 是最后一个逗号之前的部分（策略名里没有逗号）
        arg = rest.rsplit(",", 1)[0] if "," in rest else rest
        premise, subs = premise_of_rule(kind, arg)
        out.append(dict(plugin=plugin, seg="[Rule]", kind=kind, arg=arg,
                        premise=premise, subs=subs, raw=line))
    return out


def parse_scripts(plugin, text):
    """[Script] 段：能改/读响应体的绑定，URL 正则决定前提。"""
    out = []
    for line in section(text, "Script"):
        m = REWRITE_KIND_RX.match(line)
        if not m:
            continue
        kind = m.group(1)
        if kind in ("cron", "generic", "network-changed"):
            continue  # 不依赖 URL，无前提
        conds = URL_COND_RX.findall(line)
        if not conds:
            # 没有 ${url} 判断：response 脚本会违反官方强制 URL Guard，
            # 由 lint 负责；这里不重复计。
            continue
        worst = "none"
        for rx, _flags in conds:
            p, _ = premise_of_rule("URL-REGEX", rx)
            if RANK[p] > RANK[worst]:
                worst = p
        out.append(dict(plugin=plugin, seg="[Script]", kind=kind,
                        arg=conds[0][0], premise=worst, subs=[], raw=line))
    return out


def parse_rewrites(plugin, text):
    """[Rewrite] 段：改请求头/响应体，必须先解密。"""
    out = []
    for line in section(text, "Rewrite"):
        m = REWRITE_KIND_RX.match(line)
        if not m:
            continue
        kind = m.group(1)
        if kind in ("cron", "generic", "network-changed"):
            continue
        conds = URL_COND_RX.findall(line)
        worst = "none"
        for rx, _flags in conds:
            p, _ = premise_of_rule("URL-REGEX", rx)
            if RANK[p] > RANK[worst]:
                worst = p
        out.append(dict(plugin=plugin, seg="[Rewrite]", kind=kind,
                        arg=conds[0][0] if conds else "", premise=worst,
                        subs=[], raw=line))
    return out


def has_mitm(text):
    """插件是否声明了 [MITM] 且不是空段。"""
    return len(section(text, "MITM")) > 0


def mitm_hosts(text):
    out = []
    for line in section(text, "MITM"):
        if line.lower().startswith("hostname"):
            _, _, val = line.partition("=")
            out.extend(h.strip() for h in val.split(",") if h.strip())
    return out


# ---------------------------------------------------------------------------
# 存疑豁免登记表
# ---------------------------------------------------------------------------
# 存疑规则不删除，但必须登记：为什么保留 + 怎么在真机上证伪。
# key = (插件, 规则类型)；一旦这类规则消失，waiver 就会变成「失效」而被 --check 抓出。

WAIVERS = {
    ("ads", "USER-AGENT"): dict(
        keep="作为 HTTPDNS 的 UA 特征兜底：域名不含 httpdns 但 UA 含的 SDK，"
             "理论上能被这层抓到。保留成本为零——不解密就不会误伤任何明文流量。",
        doubt="ads 插件**没有 [MITM] 段**（它的定位是零证书 DNS 层）。"
              "User-Agent 是 HTTP 请求头，未解密的 HTTPS 里看不到；"
              "官方 HTTP 规则页只写了「匹配请求 Header 中的 User-Agent」，"
              "没有写未解密时是否降级。因此这 4 条很可能命中数为 0。",
        verify="① 日常使用中打开 Loon 请求日志，搜索这 4 条规则的命中记录；"
               "② 若要确证：临时给 ads.plugin 加 `[MITM] hostname = *`，"
               "对比加之前/之后的命中数。若从 0 变为 >0，即证明默认配置下它们不生效，"
               "届时应当删除或改为把 UA 特征并入域名层。",
    ),
}


def waiver_of(plugin, kind):
    return WAIVERS.get((plugin, kind.upper()))


# ---------------------------------------------------------------------------
# 审计
# ---------------------------------------------------------------------------

def collect():
    rows = []
    mitm = {}
    for plugin, raw in PLUGINS.items():
        cfg = PLUGIN_CFG[plugin]
        mitm[plugin] = has_mitm(cfg)
        rows.extend(parse_rules(plugin, cfg))
        rows.extend(parse_scripts(plugin, cfg))
        rows.extend(parse_rewrites(plugin, cfg))
    for r in rows:
        r["has_mitm"] = mitm[r["plugin"]]
        # 前提是否满足
        if r["premise"] == "none":
            r["ok"] = True
            r["state"] = "ok"
        elif r["premise"] == "plain":
            # 明文锚定：不依赖解密，但只吃明文 HTTP
            r["ok"] = True
            r["state"] = "plaintext-only"
        else:
            r["ok"] = r["has_mitm"]
            r["state"] = "ok" if r["has_mitm"] else "doubtful"
        r["waiver"] = waiver_of(r["plugin"], r["kind"]) if r["state"] == "doubtful" else None
    return rows, mitm


def audit(rows):
    """返回 (未登记的存疑, 失效的 waiver)。"""
    unregistered = []
    for r in rows:
        if r["state"] == "doubtful" and not r["waiver"]:
            unregistered.append(r)
    # 失效：登记了但仓库里已经没有这类存疑规则
    live = set((r["plugin"], r["kind"].upper()) for r in rows if r["state"] == "doubtful")
    stale = [k for k in WAIVERS if k not in live]
    return unregistered, stale


# ---------------------------------------------------------------------------
# 报表
# ---------------------------------------------------------------------------

def stats(rows):
    n = len(rows)
    by_state = {}
    for r in rows:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    return n, by_state


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def render_md(rows, mitm):
    L = []
    total, by_state = stats(rows)
    ok = by_state.get("ok", 0)
    plain = by_state.get("plaintext-only", 0)
    doubt = by_state.get("doubtful", 0)

    L.append("# 规则有效率审计：写了 ≠ 生效")
    L.append("")
    L.append("> 本文件由 `tools/rule-effectiveness.py` 生成，请勿手改。")
    L.append("> 改插件后跑 `python3 tools/rule-effectiveness.py --write`。")
    L.append("")
    L.append("## 0. 一页结论")
    L.append("")
    L.append("能力覆盖率回答「Loon 的功能用了多少」，广告面覆盖率回答「广告还剩多少」。")
    L.append("两者都只数**声明**。这一份数**前提**：一条规则写在插件里，")
    L.append("是否具备它命中所需的条件。")
    L.append("")
    L.append("- 共审计 **%d** 条会依赖前提的配置行，分布在 `[Rule]` / `[Script]` / `[Rewrite]`。" % total)
    L.append("- **前提满足 %d 条**（%.0f%%）：连接层可见，或插件已声明 `[MITM]`。" % (ok, pct(ok, total)))
    L.append("- **仅明文 %d 条**（%.0f%%）：正则锚定 `^http://`，不依赖解密，"
             "但也只吃明文 HTTP——现代 App 几乎全 HTTPS，实际命中率很低。"
             % (plain, pct(plain, total)))
    L.append("- **存疑 %d 条**（%.0f%%）：需要 HTTP 报文内容，但插件没有 `[MITM]`。" % (doubt, pct(doubt, total)))
    L.append("")
    L.append("存疑不等于错，但必须登记。当前 %d 条存疑全部已登记 waiver（见第 3 节），"
             "每条都写了保留理由与**真机证伪方法**。" % doubt)
    L.append("")

    # 1. 前提模型
    L.append("## 1. 三种前提")
    L.append("")
    L.append("| 前提 | 含义 | 能被谁满足 |")
    L.append("|---|---|---|")
    L.append("| `none` 连接层 | 只看域名 / IP / 端口 / 协议 | 任何插件，无需证书 |")
    L.append("| `plain` 仅明文 | 需要完整 URL 或请求头，但正则锚定了 `^http://` | 明文 HTTP 流量 |")
    L.append("| `mitm` 需解密 | 需要 URL 路径、请求头或响应体 | **必须有 `[MITM]`** |")
    L.append("")
    L.append("判定规则：")
    L.append("")
    L.append("- `USER-AGENT` 一律 `mitm`——它是 HTTP 请求头。")
    L.append("- `URL-REGEX` 锚定 `^http://` → `plain`；否则 `mitm`。")
    L.append("- `AND` / `OR` / `NOT` 取**内部子规则里最强的那个**（一条 `AND` 里")
    L.append("  掺一个 `USER-AGENT`，整条就需要解密）。")
    L.append("- 其余（域名类、IP 类、端口、协议、进程名）都是 `none`。")
    L.append("")

    # 2. 分插件
    L.append("## 2. 分插件")
    L.append("")
    L.append("| 插件 | `[MITM]` | 审计条数 | 前提满足 | 仅明文 | 存疑 |")
    L.append("|---|---|---:|---:|---:|---:|")
    for plugin in sorted(mitm):
        rs = [r for r in rows if r["plugin"] == plugin]
        if not rs:
            continue
        s = {}
        for r in rs:
            s[r["state"]] = s.get(r["state"], 0) + 1
        L.append("| `%s.plugin` | %s | %d | %d | %d | %d |"
                 % (plugin, "有" if mitm[plugin] else "**无**", len(rs),
                    s.get("ok", 0), s.get("plaintext-only", 0), s.get("doubtful", 0)))
    L.append("")

    # 3. 存疑清单
    L.append("## 3. 存疑清单与豁免登记")
    L.append("")
    doubts = [r for r in rows if r["state"] == "doubtful"]
    if not doubts:
        L.append("无。")
        L.append("")
    else:
        grouped = {}
        for r in doubts:
            grouped.setdefault((r["plugin"], r["kind"].upper()), []).append(r)
        for (plugin, kind), rs in sorted(grouped.items()):
            w = waiver_of(plugin, kind)
            L.append("### `%s.plugin` 的 `%s`（%d 条）" % (plugin, kind, len(rs)))
            L.append("")
            for r in rs:
                L.append("- `%s`" % (r["arg"][:96] if r["arg"] else r["raw"][:96]))
            L.append("")
            if not w:
                L.append("**⚠️ 未登记 waiver——`--check` 会失败。**")
                L.append("")
                continue
            L.append("**为什么保留**　%s" % w["keep"])
            L.append("")
            L.append("**存疑在哪**　%s" % w["doubt"])
            L.append("")
            L.append("**怎么证伪**　%s" % w["verify"])
            L.append("")

    # 4. 仅明文
    L.append("## 4. 仅明文生效的规则")
    L.append("")
    plains = [r for r in rows if r["state"] == "plaintext-only"]
    L.append("这些规则锚定了 `^http://`，不需要解密，因此**不是**存疑——")
    L.append("但它们的生效面只有明文 HTTP，而现代 App 的接口几乎全是 HTTPS。")
    L.append("这是一个「技术上有效、实际上罕见」的夹层，值得单独看见，")
    L.append("否则很容易把它和「前提满足」混为一谈。")
    L.append("")
    if plains:
        L.append("| 插件 | 段 | 规则 |")
        L.append("|---|---|---|")
        for r in plains:
            L.append("| `%s` | %s | `%s` |"
                     % (r["plugin"], r["seg"], (r["arg"] or "")[:80].replace("|", "\\|")))
        L.append("")
    else:
        L.append("无。")
        L.append("")

    # 5. 与既有度量的关系
    L.append("## 5. 三个数，三个分母")
    L.append("")
    L.append("| 度量 | 分母 | 回答什么 | 当前 |")
    L.append("|---|---|---|---|")
    L.append("| 能力利用率 | Loon 的功能 | 功能用了多少 | 见 `docs/loon-coverage.md` |")
    L.append("| 广告面覆盖率 | 广告的类型 | 广告还剩多少 | 见 `docs/ad-type-strategy.md` |")
    L.append("| **规则有效率** | 已写的规则 | **写了的有多少真会命中** | 本文件 |")
    L.append("| 路径封死率 | 绕过的路 | **拦了的是不是真拦住** | 见 `docs/bypass-audit.md` |")
    L.append("")
    L.append("前两个数的分子都是「声明」。**声明可以被写错、被架空、被前提卡住**，")
    L.append("所以还需要第三个分母来兜底；而第三个分母默认了「请求会走到规则面前」，")
    L.append("于是还需要第四个。四者不是替代关系，是层层收紧。")
    L.append("")

    # 6. 自查方式
    L.append("## 6. 门禁与自查")
    L.append("")
    L.append("`--check` 三条断言：")
    L.append("")
    L.append("1. **存疑必须登记**：判定为 `mitm` 前提却没有 `[MITM]` 的规则，"
             "必须在本文件的 `WAIVERS` 里写明保留理由与验证方法。")
    L.append("2. **失效 waiver 必须清掉**：登记了但仓库里已无对应存疑规则的，"
             "会被报为 stale——避免豁免表越积越多，最后变成新的盲区。")
    L.append("3. **文档不过期**：`docs/rule-effectiveness.md` 必须与工具输出一致。")
    L.append("")
    L.append("与 `ad-surface-audit` 的 `blocked` 断言同源：")
    L.append("**允许存疑存在，但禁止存疑沉默。**")
    L.append("")

    return "\n".join(L) + "\n"


def render_console(rows, mitm):
    total, by_state = stats(rows)
    out = []
    out.append("rule-effectiveness: %d 条" % total)
    for st in ("ok", "plaintext-only", "doubtful"):
        if by_state.get(st):
            out.append("  %-14s %3d" % (st, by_state[st]))
    unreg, stale = audit(rows)
    out.append("  未登记 waiver: %d   失效 waiver: %d" % (len(unreg), len(stale)))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv):
    rows, mitm = collect()
    unreg, stale = audit(rows)

    if "--check" in argv:
        bad = False
        for r in unreg:
            print("存疑但未登记 waiver: %s.plugin %s %s"
                  % (r["plugin"], r["kind"], (r["arg"] or "")[:60]), file=sys.stderr)
            bad = True
        for k in stale:
            print("失效 waiver（已无对应存疑规则）: %s / %s" % k, file=sys.stderr)
            bad = True
        if bad:
            return 1
        want = render_md(rows, mitm)
        have = read(OUT_MD)
        if have != want:
            print("effectiveness doc is stale: run "
                  "`python3 tools/rule-effectiveness.py --write`", file=sys.stderr)
            return 1
        total = len(rows)
        doubt = len([r for r in rows if r["state"] == "doubtful"])
        print("effectiveness ok: %d rules  ok=%d  plaintext=%d  doubtful=%d(waived)"
              % (total, len([r for r in rows if r["state"] == "ok"]),
                 len([r for r in rows if r["state"] == "plaintext-only"]), doubt))
        return 0

    if "--write" in argv:
        io.open(OUT_MD, "w", encoding="utf-8").write(render_md(rows, mitm))
        print("wrote %s" % OUT_MD)
        return 0

    print(render_console(rows, mitm))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
