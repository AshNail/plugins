#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loon-token-audit.py —— 反向对差：插件里的**语法 token** 能不能在官方文档里查到

正向对差（第十八轮）问的是「文档里有、能力表没有」；它永远查不出反过来那类错：
**我们写了文档里根本没有的东西**。这类错在本仓库已经犯过三次，代价都不小：
  · `ip-mode` 的右值写成 `ipv4-only`——官方值是 `v4-only`，非法行被 Loon 忽略，真机探针得到假阳性；
  · 规则行的 `pre-matching` / `extended-matching`——那是 Surge 的参数；
  · `[MITM] h2 = true` 与 `hostname = %APPEND%`——官方 MitM 参数表只有三行，整站查不到。
前两类已由各处 lint 锁死，但都是「发现一个补一个」。这个工具把方法本身固化下来：

  官方文档是中文的，所以页面里出现的**拉丁小写 token 基本只来自 ini 代码块与参数表**
  ——这就是天然的语法词表。把每段的词表存进 `src/loon-docs/tokens.json`，
  再扫插件的**有效行**与**文档围栏里的 Loon 配置**（用户会整段复制 README/docs 的 ```ini 示例，
  所以第二十三轮起它们和生效配置同标准），凡是落在该段词表外、又不在显式例外表里的 token 就报错。

用法
----
  python3 tools/loon-token-audit.py                 # 报表：逐段列出未登记 token
  python3 tools/loon-token-audit.py --check         # CI：出现新 token 即失败，并自检词表来源
  python3 tools/loon-token-audit.py --build DIR     # 从已抽取的官方正文纯文本重建词表
  python3 tools/loon-token-audit.py --fetch         # 重新抓官网页面再重建（需要联网，手工执行）
  python3 tools/loon-token-audit.py --sitemap       # 在线核对：官方文档页有没有我们没读过的

自证
----
这套对差的结论强度完全取决于**词表本身是否完整**，所以 `--check` 还要过三道自检：
① 每个段的页面 glob 必须真的命中文件（漏一页＝词表小一圈，未文档化 token 会被误判成合法）；
② `FETCH_PAGES` 必须与 `--fetch` 当场从 `sitemap.xml` 记下的官方正文页清单**双向相等**
   （官方新增一页而我们没读，是整类错误的温床）；
③ `UNDOCUMENTED` 例外表必须与 `tools/loon-coverage.py` 里 `expect="undocumented"` 的行
   通过 `token="段名.token"` 一一对应（三处文档对不上，就等于没有例外表）。
"""

import glob
import html
import io
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "loon-docs", "tokens.json")
SITE = "https://nsloon.app"
UA = "loon-plugins-audit"
DEFAULT_DOCS = "/tmp/loon-docs"

# 每段的官方页面（**精确文件名**，相对词表目录，即 FETCH_PAGES 的 slug 把 `/` 换成 `_`）。
# 这里不用通配符：第二十一轮发现旧词表目录里混着历史遗留的 `Plugin_.txt` / `api.txt` /
# `rw2.txt` / `*.md`，glob 会把它们一起吞进池子——池子虚胖、`absent_claims` 的整站断言
# 也可能被一个来路不明的文件洗掉。SCRIPT / REWRITE 共享条件表达式语法，所以两边都把
# 对方的页面并进来；REJECT-DICT / REJECT-DROP 印在「策略与动作」页。
SECTION_PAGES = {
    "METADATA": ["Plugin.txt"],
    "GENERAL": ["General.txt", "Plugin.txt"],
    "MITM": ["MitM.txt", "Plugin.txt"],
    # Node/subscription 是官方唯一完整列出 use-in-proxy、IP→IP 与 Host Map
    # 合并优先级的页面；Host 词表缺它，合法的 use-in-proxy 会被误报。
    "HOST": ["DNS.txt", "DNS_hostmap.txt", "Node_subscription.txt", "Plugin.txt"],
    "RULE": ["Rule.txt", "Policy.txt", "Policy_policygroup.txt"] +
            ["Rule_%s.txt" % s for s in
             ("domain_rule", "http_rule", "ip_rule", "logic_rule", "port_rule",
              "process_rule", "protocol_rule", "sub_rule", "final_rule")],
    "REWRITE": ["Rewrite.txt", "Rewrite_rewrite_v2.txt"],
    "SCRIPT": ["Script.txt", "Script_script_v2.txt", "Script_script_api.txt",
               "Rewrite.txt", "Rewrite_rewrite_v2.txt", "Plugin.txt"],
    "ARGUMENT": ["Plugin.txt", "Script_script_v2.txt", "Rewrite_rewrite_v2.txt"],
    "IP REWRITE": ["General.txt", "Plugin.txt"],
}

# 显式登记的「官方查不到、我们仍在带」的 token，key = 段名。
# 每一条都必须同时在 tools/loon-coverage.py 里有 expect="undocumented" 的行与理由，
# 并且有 docs/device-checklist.md 的真机取证步骤——三处对不上就按未登记处理。
UNDOCUMENTED = {
    "MITM": {"h2"},                      # %APPEND% 出现在 hostname 值里，由 lint 的键面门禁管
    "METADATA": {"version", "openurl"},
}

DOMAINISH = re.compile(r"^(\*\.)?[a-z0-9][a-z0-9.*_-]*\.[a-z]{2,}$|^\d+$")

# 能力表与文档里写过的「整站查不到」断言，逐条变成可回归的计数。
# 每一项都必须在 26 个正文页里 0 命中；一旦官方补了文档，命中数>0 就会把对应结论推翻。
RAW_CLAIMS = ("%append%", "pre-matching", "extended-matching", "#!version", "#!openurl")

# 文档围栏里的 Loon 配置：段名 → 词表池
DOC_GLOBS = ("README.md", "plugins/*/README.md", "docs/*.md")
INI_SECTIONS = {"GENERAL": "GENERAL", "MITM": "MITM", "DNS": "DNS", "HOST": "HOST",
                "RULE": "RULE", "REWRITE": "REWRITE", "SCRIPT": "SCRIPT",
                "ARGUMENT": "ARGUMENT", "IP REWRITE": "IP REWRITE", "URL REWRITE": "REWRITE"}
RULEISH = re.compile(r"^[A-Z][A-Z0-9-]{2,}\s*,")
HOSTISH = re.compile(r"^[A-Za-z0-9.*_-]+\s*=\s*(?:\d{1,3}\.){3}\d{1,3}(?:\s*,#.*)?$")
KEYISH = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*\s*=")


def page_tokens(text):
    """页面正文里的拉丁 token（小写化 + 点号分段展开）。

    展开点号是因为文档渲染器会把 `request.header.set` 拆成几段写，
    逐段登记才不会把合法写法误判成未文档化。
    """
    out = set(re.findall(r"[a-z][a-z0-9_.\-]*", text.lower()))
    for tok in list(out):
        for part in tok.split("."):
            if part:
                out.add(part)
    return out


def build_from_dir(directory, doc_pages=None):
    sections = {}
    for name, patterns in SECTION_PAGES.items():
        text = ""
        used = []
        for pat in patterns:
            for path in sorted(glob.glob(os.path.join(directory, pat))):
                text += io.open(path, encoding="utf-8", errors="ignore").read() + "\n"
                if path not in used:
                    used.append(os.path.basename(path))
        sections[name] = {"pages": used, "tokens": sorted(page_tokens(text))}
    # 全站池：能力表里「整站 26 个正文页都扫不到」这句话，必须由这一池子背书，
    # 而不是靠人记得 grep 过。名单直接取自 FETCH_PAGES，所以目录里混进别的文件也污染不了它。
    all_text, all_pages = "", []
    for slug in FETCH_PAGES:
        name = slug.replace("/", "_") + ".txt"
        path = os.path.join(directory, name)
        if os.path.exists(path):
            all_text += io.open(path, encoding="utf-8", errors="ignore").read() + "\n"
            all_pages.append(name)
    sections["_全站"] = {"pages": all_pages, "tokens": sorted(page_tokens(all_text))}
    claims = {marker: all_text.lower().count(marker) for marker in RAW_CLAIMS}
    return {"_comment": "由 tools/loon-token-audit.py --build/--fetch 生成；官方文档正文的拉丁 token 词表",
            "doc_pages": sorted(doc_pages or []),
            "absent_claims": claims,
            "sections": sections}


FETCH_PAGES = [
    "MitM", "General", "DNS/hostmap", "DNS", "Plugin", "Rule", "Rule/domain_rule",
    "Rule/http_rule", "Rule/ip_rule", "Rule/logic_rule", "Rule/port_rule",
    "Rule/process_rule", "Rule/protocol_rule", "Rule/sub_rule", "Rule/final_rule",
    "Rewrite", "Rewrite/rewrite_v2", "Script", "Script/script_v2", "Script/script_api",
    "Node", "Node/subscription", "Node/nodefilter", "Policy", "Policy/policygroup", "Scheme",
]


def fetch_dir(argv, flag):
    """解析抓取/构建目录。

    坑（第二十一轮实踩）：这里曾按 `sys.argv` 取下一个参数，而 `argv` 已经去掉脚本名，
    off-by-one 把目录解析成字面量 `--fetch` —— 于是 26 个页面被写进**仓库根目录一个叫
    `--fetch` 的文件夹**，命令照样打印 `fetched 26/26`，看起来完全成功。
    所以除了解析正确，还硬性要求解析结果不在仓库内、且是绝对路径。
    """
    i = argv.index(flag)
    directory = argv[i + 1] if len(argv) > i + 1 else DEFAULT_DOCS
    if directory.startswith("-"):
        raise SystemExit("%s 的目录参数缺失（拿到的是 %r）" % (flag, directory))
    directory = os.path.abspath(os.path.expanduser(directory))
    if directory == ROOT or directory.startswith(ROOT + os.sep):
        raise SystemExit("抓取目录不能在仓库内（%s）—— 原始页面只属于临时目录，词表产物才进仓库"
                         % directory)
    return directory


def fetch_to_dir(directory):
    """抓官方正文页并剥成纯文本（手工执行，CI 不碰网络）。

    认页面身份的判据是 Docusaurus 写在 `<html class>` 上的 `docs-doc-id-<slug>` 标记，
    **不是正文长度**：`Rule/protocol_rule` 整页正文只有 147 字节，用长度阈值会把真页面
    当成 404 丢掉（第十八轮踩过反向的那个坑：10110 字节的 404 页被当成正文存下来）。
    """
    os.makedirs(directory, exist_ok=True)
    failed = []
    for slug in FETCH_PAGES:
        url = "%s/docs/%s/" % (SITE, slug)
        try:
            raw = urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": UA}),
                timeout=30).read().decode("utf-8", "replace")
        except Exception as exc:                      # 网络失败不静默：报出来
            print("  ! %s -> %s" % (url, exc), file=sys.stderr)
            failed.append(slug)
            continue
        if ("docs-doc-id-%s" % slug) not in raw:
            print("  ! %s 返回的不是该页面（无 docs-doc-id 标记，疑似 404/改名）" % url, file=sys.stderr)
            failed.append(slug)
            continue
        m = re.search(r"<article.*?</article>", raw, re.S)
        body = m.group(0) if m else raw
        body = re.sub(r"(?is)<(script|style|nav|footer).*?</\1>", "\n", body)
        body = re.sub(r"(?s)<[^>]+>", "\n", body)
        text = html.unescape(body).replace("\x00", "")
        name = slug.replace("/", "_")
        io.open(os.path.join(directory, name + ".txt"), "w", encoding="utf-8").write(text)
    if failed:
        print("抓取不完整：%d/%d 页缺失（%s）"
              % (len(failed), len(FETCH_PAGES), ", ".join(failed)), file=sys.stderr)
        return 0
    print("fetched %d/%d pages" % (len(FETCH_PAGES), len(FETCH_PAGES)))
    return len(FETCH_PAGES)


def sitemap_doc_pages():
    """在线取官方正文页清单（去掉 category 归档页与 intro 首页）。"""
    raw = urllib.request.urlopen(
        urllib.request.Request(SITE + "/sitemap.xml", headers={"User-Agent": UA}),
        timeout=30).read().decode("utf-8", "replace")
    out = []
    for loc in re.findall(r"<loc>(.*?)</loc>", raw):
        m = re.search(r"/docs/([^?#]*)/?$", html.unescape(loc))
        if not m:
            continue
        slug = m.group(1).strip("/")
        if not slug or slug == "intro" or slug.startswith("category/"):
            continue
        out.append(slug)
    return sorted(set(out))


# ---------------------------------------------------------------------------
# 插件侧：按段抽取「应当属于语法」的 token
# ---------------------------------------------------------------------------

def arg_names(text):
    """本插件 [Argument] 声明的参数名——`${这些}` 是数据，不是语法。"""
    m = re.search(r"(?m)^\[Argument\]\s*$(.*?)(?=^\[|\Z)", text, re.S)
    if not m:
        return set()
    return {ln.split("=", 1)[0].strip()
            for ln in m.group(1).splitlines()
            if "=" in ln and not ln.strip().startswith(("#", ";"))}


def candidates(line, section, args):
    """返回该有效行里需要被官方词表解释的 token 集合。"""
    line = re.sub(r'"[^"]*"', '""', line)          # 引号内是用户可见值/URL 路径
    if line.startswith("#!"):
        return {"METADATA": {line.split("=", 1)[0].strip().lstrip("#!").lower()}}
    if section == "_全站":
        # ```ini 围栏里没有段名：只查「这个**键名**官方有没有出现过」，用全站池兜底。
        # 左值必须是裸标识符——`doubleclick.net = 127.0.0.1` 的左值是域名（归 HOST 段管），
        # `ssid:LOON's WIFI = server:system` 的左值是条件形态，都不是键名。
        if "=" not in line:
            return {}
        left = line.split("=", 1)[0].strip().lower()
        return {"_全站": {left} if re.fullmatch(r"[a-z][a-z0-9_-]*", left) else {}}
    if section == "IP REWRITE":
        # 左值是用户的目的 IPv4，不是语法键名；真正需要词表背书的是右值动作。
        rhs = line.split("=", 1)[1] if "=" in line else ""
        return {"IP REWRITE": {t.lower() for t in re.findall(r"[a-z][a-z0-9_-]*", rhs)}}
    if section in ("GENERAL", "MITM", "DNS", "URL REVISION"):
        return {section: {line.split("=", 1)[0].strip().lower()} if "=" in line else set()}
    if section == "HOST":
        rhs = line.split("=", 1)[1] if "=" in line else ""
        return {"HOST": {t.lower() for t in re.findall(r"([a-z][a-z0-9_-]+):", rhs)}
                         | {t.lower() for t in re.findall(r",\s*([a-z][a-z0-9_-]+)\s*=", rhs)}}
    if section == "ARGUMENT":
        out = set(re.findall(r"([a-z_][a-z0-9_-]*)=", line))
        if "," in line:
            ctl = line.split(",", 1)[1].strip().split(",")[0].strip().lower()
            if ctl not in ("", '""'):               # 引号已折叠成 ""，取值不是语法
                out.add(ctl)
        return {"ARGUMENT": out}
    if section == "RULE":
        out = {t.lower() for t in re.findall(r"\b([A-Z][A-Z0-9-]{2,})\b", line)}
        out |= {t.lower() for t in re.findall(r"[,\s]([a-z][a-z0-9_-]*)=", line)}
        return {"RULE": {t for t in out if not DOMAINISH.match(t)}}
    if section in ("REWRITE", "SCRIPT"):
        out = set(re.findall(r"\b([a-z][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+)\s*\(", line))
        out |= set(re.findall(r"\b(?:then|with)\s+([a-z_.]+)", line))
        out |= {t.lower() for t in re.findall(r"[,(\s]([a-z_][a-z0-9_]*)=", line)}
        vars_ = {t.split("[")[0].split(".")[0] for t in
                 re.findall(r"\$\{([a-zA-Z][a-zA-Z0-9_.\[\]'\-]*)", line)}
        out |= {t for t in vars_ if t.lower() not in args}   # 参数插值不算语法
        return {section: {t.lower() for t in out if not DOMAINISH.match(t)}}
    return {}


def doc_lines():
    """README / docs 里围栏代码块中的 Loon 配置——用户会整段复制，所以和插件文件同级对待。

    只用**能自证形态**的行参差：围栏里出现 `[Section]` 段名行就按该段查；
    没有段名时，`大写类型,` 形态算 RULE、`域名 = IPv4` 形态算 HOST，其余一律不猜
    （文档里大量 `key = value` 是接口字段说明，不是 Loon 语法）。
    """
    out = []
    for pattern in DOC_GLOBS:
        for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
            rel = os.path.relpath(path, ROOT)
            text = io.open(path, encoding="utf-8").read()
            for m in re.finditer(r"^```([a-zA-Z0-9]*)\n(.*?)^```", text, re.M | re.S):
                base = text[:m.start()].count("\n")
                lang = m.group(1).lower()
                loose = lang in ("ini", "conf", "config", "loon", "plugin")
                section = None
                for i, raw in enumerate(m.group(2).splitlines(), 1):
                    line = raw.strip()
                    if not line or line.startswith((";", "#")):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        section = INI_SECTIONS.get(line[1:-1].strip().upper())
                        continue
                    if section is None:
                        if RULEISH.match(line):
                            section = "RULE"
                        elif HOSTISH.match(line):
                            section = "HOST"
                        elif loose and "=" in line and KEYISH.match(line):
                            # ```ini 围栏本身就是「这是配置」的声明：键名必须在全站词表里出现
                            section = "_全站"
                        else:
                            continue
                    out.append((rel, base + i, section, line))
    return out


ALL_ALLOWED = {tok for toks in UNDOCUMENTED.values() for tok in toks}


def audit(inventory):
    pools = {k: set(v["tokens"]) for k, v in inventory["sections"].items()}
    findings = {}

    def check(where, sec, line, args):
        # 池子按 candidates() 返回的段名取，不是按当前段取——`#!` 行出现在任何段之前，
        # 它属于 METADATA 池（按当前段取会拿到 None，元数据全体变成假阳性）。
        for name, toks in candidates(line, sec, args).items():
            pool = pools.get(name, set())
            allow = ALL_ALLOWED if name == "_全站" else UNDOCUMENTED.get(name, set())
            for tok in toks:
                if tok and tok not in pool and tok not in allow:
                    findings.setdefault((name, tok), []).append("%s %s" % (where, line[:78]))

    scanned = 0
    for fp in sorted(glob.glob(os.path.join(ROOT, "plugins", "*", "*.plugin"))):
        text = io.open(fp, encoding="utf-8").read()
        args = {a.lower() for a in arg_names(text)}
        section = None
        for num, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].upper()
                continue
            if line.startswith(("#", ";")) and not line.startswith("#!"):
                continue                              # 注释层不参与「生效语法」对差
            scanned += 1
            check("%s:%d" % (os.path.basename(fp), num), section, line, args)
    doc_scanned = 0
    for rel, num, section, line in doc_lines():
        doc_scanned += 1
        check("%s:%d" % (rel, num), section, line, set())
    stale = []
    for sec, allow in UNDOCUMENTED.items():
        for tok in allow:
            if tok in pools.get(sec, set()):
                stale.append((sec, tok))
    return findings, stale, scanned, doc_scanned


def check_source(inventory):
    """词表自证：页面清单与文件是否真的都在。返回问题列表（空＝通过）。"""
    problems = []
    recorded = inventory.get("doc_pages") or []
    if not recorded:
        problems.append("tokens.json 没有 doc_pages —— 重跑 `--fetch` 让它当场记一次官方正文页清单")
    else:
        for slug in sorted(set(FETCH_PAGES) - set(recorded)):
            problems.append("FETCH_PAGES 里的 `%s` 不在官方页清单里 —— 页面改名或我们记错了" % slug)
        for slug in sorted(set(recorded) - set(FETCH_PAGES)):
            problems.append("官方正文页 `%s` 从没被抓过 —— 词表少一页，补进 FETCH_PAGES 再 --fetch" % slug)
    global_pages = (inventory["sections"].get("_全站") or {}).get("pages", [])
    for slug in FETCH_PAGES:
        if slug.replace("/", "_") + ".txt" not in global_pages:
            problems.append("`%s` 不在全站池里 —— 「整站正文页都扫不到」这句话对它不成立" % slug)
    for name, meta in inventory["sections"].items():
        if not meta["pages"]:
            problems.append("[%s] 段的页面 glob 一个都没命中 —— 该段词表为空，任何未文档化 token 都会被放行" % name)
    unused = sorted(set(global_pages) - {p for n, m in inventory["sections"].items()
                                         if n != "_全站" for p in m["pages"]})
    if unused:
        print("  · 提示：以下页面只进全站池、不属任何段词表：%s" % ", ".join(unused))
    claims = inventory.get("absent_claims") or {}
    for marker, count in sorted(claims.items()):
        if count:
            problems.append("断言 `%s` 整站 0 命中已被推翻（现在 %d 次）—— 相关结论要重新判读" % (marker, count))
    missing = [m for m in RAW_CLAIMS if m not in claims]
    if missing:
        problems.append("词表里没有 %s 的命中计数 —— 重跑 --build/--fetch" % ", ".join(missing))
    return problems


def sync_exceptions():
    """例外表必须与能力表的 undocumented 行一一对应（靠 token= 链接钉住）。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import importlib
    cov = importlib.import_module("loon-coverage")
    linked = {c.get("token") for c in cov.CAPABILITIES if c["expect"] == "undocumented"}
    if None in linked:
        missing = [c["key"] for c in cov.CAPABILITIES
                   if c["expect"] == "undocumented" and not c.get("token")]
        return ["能力表有 undocumented 行没登记 token 链接：%s" % ", ".join(missing)]
    registered = {"%s.%s" % (sec, tok) for sec, toks in UNDOCUMENTED.items() for tok in toks}
    problems = []
    for link in sorted(registered - {l for l in linked if not str(l).startswith("lint:")}):
        problems.append("例外 %s 在能力表里没有对应的 undocumented 行" % link)
    for link in sorted({l for l in linked if not str(l).startswith("lint:")} - registered):
        problems.append("能力表的 undocumented 行 %s 没在 UNDOCUMENTED 里登记，反向对差会一直报错" % link)
    for link in sorted(l for l in linked if str(l).startswith("lint:")):
        if link.split(":", 1)[1].split(".")[0] not in SECTION_PAGES:
            problems.append("%s 的 `lint:` 链接指向一个不存在的段" % link)
    return problems


def main(argv):
    if "--sitemap" in argv:
        try:
            pages = sitemap_doc_pages()
        except Exception as exc:
            print("  ! sitemap -> %s" % exc, file=sys.stderr)
            return 1
        new = [p for p in pages if p not in FETCH_PAGES]
        gone = [p for p in FETCH_PAGES if p not in pages]
        print("官方正文页 %d 个（已排除 category 归档页与 intro）" % len(pages))
        for p in new:
            print("  · 没读过：%s —— 补进 FETCH_PAGES 再 --fetch" % p)
        for p in gone:
            print("  · 已下线：%s —— 从 FETCH_PAGES 里删掉" % p)
        if new or gone:
            return 1
        print("sitemap ok: FETCH_PAGES 与官方正文页双向相等")
        return 0
    if "--fetch" in argv:
        directory = fetch_dir(argv, "--fetch")
        if not fetch_to_dir(directory):
            print("抓取失败，词表未更新", file=sys.stderr)
            return 1
        try:
            pages = sitemap_doc_pages()
        except Exception as exc:
            print("  ! sitemap -> %s（doc_pages 沿用旧值）" % exc, file=sys.stderr)
            pages = None
        argv = ["--build", directory] + argv          # 抓完顺手重建
        if pages is not None:
            argv = argv + ["--pages"] + pages
    if "--build" in argv:
        directory = fetch_dir(argv, "--build")
        pages = argv[argv.index("--pages") + 1:] if "--pages" in argv else None
        if pages is None and os.path.exists(DATA):   # 手工 --build 时别把清单洗掉
            pages = (json.loads(io.open(DATA, encoding="utf-8").read()) or {}).get("doc_pages")
        data = build_from_dir(directory, pages)
        os.makedirs(os.path.dirname(DATA), exist_ok=True)
        io.open(DATA, "w", encoding="utf-8").write(
            json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        total = sum(len(v["tokens"]) for v in data["sections"].values())
        print("wrote %s (%d sections, %d tokens, %d doc pages)"
              % (os.path.relpath(DATA, ROOT), len(data["sections"]), total, len(data["doc_pages"])))
        return 0

    if not os.path.exists(DATA):
        print("缺少 %s，先跑 --build/--fetch" % os.path.relpath(DATA, ROOT), file=sys.stderr)
        return 1
    inventory = json.loads(io.open(DATA, encoding="utf-8").read())
    src_problems = check_source(inventory) + sync_exceptions()
    for msg in src_problems:
        print("  · 词表自证失败：%s" % msg)
    findings, stale, scanned, doc_scanned = audit(inventory)

    if stale:
        for sec, tok in stale:
            print("  · 例外过期：[%s] `%s` 现在官方词表里有了 —— 从 UNDOCUMENTED 里删掉，"
                  "并把 loon-coverage 的 undocumented 行改回 used" % (sec, tok))
        if "--check" in argv:
            return 1

    if findings:
        print("undocumented tokens: %d" % len(findings))
        for (sec, tok), hits in sorted(findings.items()):
            print("  [%s] %s  x%d" % (sec, tok, len(hits)))
            for h in hits[:2]:
                print("      " + h)
    else:
        print("token audit ok: 插件有效行 + 文档围栏里的 Loon 配置，语法 token 全部能在官方文档对应段落查到"
              "（扫描 %d 行插件 + %d 行文档；登记例外 %d 个：%s）"
              % (scanned, doc_scanned,
                 sum(len(v) for v in UNDOCUMENTED.values()),
                 " ".join(sorted("%s.%s" % (s, t) for s, ts in UNDOCUMENTED.items() for t in ts))))
        if not src_problems:
            print("word-list self-check ok: %d 个官方正文页全部入表、例外表与能力表一一对应"
                  % len(inventory.get("doc_pages") or FETCH_PAGES))
    return 1 if (findings or stale or src_problems) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
