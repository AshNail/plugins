#!/usr/bin/env python3
"""App 红线：唯一的数据出口，供 build-ads.py 与 build-apps.py 共同执行同一条纪律。

「红线」过去只存在于每个 App 插件的 comment 散文里，因此任何门禁都读不到它——
散文无法判断「这条规则到底触没触碰生死线」。把它结构化进 src/apps/*.json 的
`redlines` 之后，两个构建器都能拒绝任何默认生效的拦截条目命中红线域。

条目形状：{"domain", "kind"("host"|"family"), "why", 以及 quote 或 ledger 二选一}
  quote 必须逐字出现在同一文件的 comment 里，且 domain 在 quote 中是独立 token
  （允许 `*.` 前缀）。这样红线只能从既有取证转录，不能凭品牌名扩写或新造域名。
  ledger = {"label", "glob"} 是第二种出处：同一个 App 文件里的 `triage_exclude` 台账
  （「上游建议拦、我们裁决不拦」的判决记录）。台账 label 里写着「红线」的 glob 同样是一条
  红线声明，只不过它此前只被覆盖率审计器读过、从不参与构建判定。用 ledger 出处时要求：
    1. (label, glob) 这一对逐字存在于该文件的 triage_exclude；
    2. fnmatch(domain, glob) 成立——域名是 glob 表达出来的那个形态；
    3. 可注册域落在该 App 的品牌根内（品牌根表来自覆盖率审计器，不复制）；
    4. 域名在仓库已有语料里被记过（docs/app-coverage.md + src/**/*.json，redlines 自身除外，
       否则新造的域名会自己给自己作证），family 型允许「它自己没有、下面有已记录的成员」。
  glob 是模式，光靠 fnmatch 拦不住「借 `resolver.msg.*` 新造一个 resolver.msg.mi.com」，
  所以 3、4 是模式类出处的额外凭证。

两个方向的凭证规则（check_file_ledger）：
  台账说「红线」而结构化名单里没有 → 报错（判决只是装饰）；
  结构化名单里的 ledger 出处造假 → 报错（凭想象写门禁的老毛病，作用在新字段自己身上）。

红线约束的是「域名类拦截面」，而这种面有四种载体，判定必须都读到（第二十九轮）：
  `[Host]` 精确/`*.` 条目（redline_hit）、`[Rule]` 顶层的 DOMAIN/DOMAIN-SUFFIX、
  `AND((DOMAIN-SUFFIX,…),…)` 里**嵌套**的后缀项、以及覆盖面比后缀更宽的 DOMAIN-KEYWORD
  （关键词命中主机名任意一段，`dns` 就会连 `dns.jd.com` 一起捞走）。
后三种由 rule_match_items() 从规则串里抽出——它的正则由 DOMAIN_MATCH_TYPES 生成，
所以「哪种类型算域名类」与「从规则里读什么」是同一张表，不存在第二份要分别维护的名单。
URL 路径 / UA / 端口类匹配面不在禁止之列：它们不黑洞主机，而红线保护的是主机可达性。
"""
from __future__ import annotations

import fnmatch
import pathlib
import re
import json

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS_DIR = ROOT / "src/apps"

REDLINE_KINDS = {"host", "family"}
REDLINE_WORD = "红线"

DOMAIN_RE = re.compile(
    r"^(?:\*\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


def expand_rule(rule: str) -> list[str]:
    if rule.startswith("="):
        base = rule[1:]
        if not base:
            raise ValueError("empty '=' rule")
        return [base, "*." + base]
    return [rule]


def ledger_entries(data: dict) -> list[tuple[str, str]]:
    """该文件 triage_exclude 里的 (label, glob) 全集——台账原文，不做任何解释。"""
    pairs = []
    for ent in data.get("triage_exclude") or []:
        label = ent.get("label") or ""
        for glob in ent.get("globs") or []:
            pairs.append((label, glob))
    return pairs


def red_lines_in_ledger(data: dict) -> list[tuple[str, str]]:
    """台账里 label 带「红线」二字的 (label, glob)：这些是散文形式的红线声明。"""
    return [(label, glob) for label, glob in ledger_entries(data) if REDLINE_WORD in label]


_AUDIT = None


def coverage_audit():
    """覆盖率审计器装载一次：品牌根表与 registrable() 都从它那里取，不在这里复制第二份。"""
    global _AUDIT
    if _AUDIT is None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "app_coverage_audit", str(ROOT / "tools/app-coverage-audit.py")
        )
        if spec is None or spec.loader is None:
            raise ValueError("无法装载 tools/app-coverage-audit.py（红线品牌根来自它）")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _AUDIT = module
    return _AUDIT


def brand_roots(slug: str) -> set[str]:
    """该 App 的品牌根集合，出处是覆盖率审计器自己那张表。"""
    return set(coverage_audit().BRAND_ROOTS.get(slug, ()))


def registrable(domain: str) -> str:
    return coverage_audit().registrable(domain)


TOKEN_RE = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
_CORPUS: set[str] | None = None


def attested_domains() -> set[str]:
    """仓库已经记下的域名全集：覆盖率报告 + 所有源数据（**不含 redlines 自己**）。

    台账 glob 是模式（`resolver.msg.*` 允许任何后缀），只凭 fnmatch 拦不住「借 glob 的名义
    新造一个主机」。域名必须先在这个语料里出现过，才算「转录」而不是「发明」。
    `plugins/*.plugin` 是 redlines 的下游产物、`redlines` 字段是待验证对象本身——两者都不进语料，
    否则新造的域名会自己给自己作证。
    """
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = set()
        files = [(ROOT / "docs/app-coverage.md").read_text(encoding="utf-8")]
        for path in sorted((ROOT / "src").rglob("*.json")):
            if "apps" in path.parts:
                data = json.loads(path.read_text(encoding="utf-8"))
                data.pop("redlines", None)
                files.append(json.dumps(data, ensure_ascii=False))
            else:
                files.append(path.read_text(encoding="utf-8"))
        for text in files:
            _CORPUS.update(TOKEN_RE.findall(text.lower()))
    return _CORPUS


def attestation_ok(domain: str, kind: str) -> bool:
    corpus = attested_domains()
    if domain in corpus:
        return True
    return kind == "family" and any(d.endswith("." + domain) for d in corpus)


def load_app_redlines() -> list[dict]:
    """读取 src/apps/*.json 的 redlines；缺失、空、造假都直接失败。"""
    entries: list[dict] = []
    for path in sorted(APPS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        slug = data.get("slug") or path.stem
        redlines = data.get("redlines")
        comments = " ".join(data.get("comment") or [])
        ledger = ledger_entries(data)
        if not isinstance(redlines, list) or not redlines:
            raise ValueError(
                f"{path}: 缺少非空 redlines——App 的「红线」段落要结构化，"
                "门禁才有数据可读（删字段等于把门禁关掉）"
            )
        for entry in redlines:
            if not isinstance(entry, dict):
                raise ValueError(f"{path}: redlines 条目必须是对象")
            domain = entry.get("domain")
            kind = entry.get("kind")
            quote = entry.get("quote")
            source = entry.get("ledger")
            why = entry.get("why")
            where = f"{path}: redline {domain!r}"
            if not isinstance(domain, str) or not DOMAIN_RE.match(domain):
                raise ValueError(f"{where}: 不是合法域名")
            if kind not in REDLINE_KINDS:
                raise ValueError(f"{where}: kind 只能是 {sorted(REDLINE_KINDS)}")
            if bool(quote) == bool(source):
                raise ValueError(
                    f"{where}: quote（comment 原文）与 ledger（台账条目）必须恰好提供一个——"
                    "红线的出处只有这两种，都要写或都不写等于没有出处"
                )
            if quote:
                if not isinstance(quote, str) or quote not in comments:
                    raise ValueError(
                        f"{where}: quote 不在本文件 comment 原文里——"
                        "红线只能从已有取证转录，不能新造"
                    )
                token = re.compile(
                    r"(?:^|[^a-z0-9.-])(?:\*\.)?" + re.escape(domain) + r"(?:$|[^a-z0-9-])"
                )
                if not token.search(quote):
                    raise ValueError(f"{where}: domain 不是 quote 里的独立 token（不许凭品牌名扩写域名）")
                origin = quote
            else:
                if not isinstance(source, dict):
                    raise ValueError(f"{where}: ledger 出处必须是 {{label, glob}}")
                pair = (source.get("label"), source.get("glob"))
                if pair not in ledger:
                    raise ValueError(
                        f"{where}: 台账里没有 {pair[0]!r} / {pair[1]!r} 这一对——"
                        "ledger 出处只能转录本文件 triage_exclude 的原文"
                    )
                if not fnmatch.fnmatch(domain, pair[1]):
                    raise ValueError(
                        f"{where}: domain 不满足台账 glob {pair[1]!r}——"
                        "红线要按 glob 表达的那个形态写，不许借台账的名义另起域名"
                    )
                roots = brand_roots(slug)
                if roots and registrable(domain) not in roots:
                    raise ValueError(
                        f"{where}: 可注册域 {registrable(domain)} 不在 {slug} 的品牌根里"
                        f"（{sorted(roots)}）——`resolver.msg.*` 这类前缀 glob 允许任意后缀，"
                        "品牌根是它唯一的额外凭证"
                    )
                if not attestation_ok(domain, kind):
                    raise ValueError(
                        f"{where}: 这个域名仓库里从没记过（查遍 docs/app-coverage.md 与 "
                        "src/**/*.json 里除 redlines 以外的部分）——台账 glob 允许前缀，"
                        "但红线必须是转录已有取证，不能借 glob 新造主机"
                    )
                origin = f"台账 {pair[0]}: {pair[1]}"
            if not isinstance(why, str) or not why:
                raise ValueError(f"{where}: 缺 why（为什么不能拦）")
            entries.append(
                {
                    "slug": slug,
                    "domain": domain.lower(),
                    "kind": kind,
                    "why": why,
                    "quote": origin,
                }
            )
        check_file_ledger(str(path), data, entries, slug)
    if not entries:
        raise ValueError(f"{APPS_DIR}: 没有任何 redlines 数据")
    return entries


def check_file_ledger(path, data, entries, slug):
    """台账用「红线」二字声明的每条 glob，都必须有对应的结构化红线。"""
    declared = [entry["domain"] for entry in entries if entry["slug"] == slug]
    orphans = [
        f"{label}/{glob}"
        for label, glob in red_lines_in_ledger(data)
        if not any(fnmatch.fnmatch(domain, glob) for domain in declared)
    ]
    if orphans:
        raise ValueError(
            f"{path}: 台账里这些条目自称「红线」却没有结构化红线与之对应：{'、'.join(orphans)}——"
            "要么把域名补进 redlines（用 ledger 出处），要么把 label 里的「红线」二字改成"
            "「模式放行」：没有可钉域名的 catch-all 不是红线，是散文"
        )
    return entries



# 规则向量的分类：域名类匹配项能直接决定「哪些主机被拦」，所以它们受红线约束；
# 非域名类（按 URL 路径、UA、端口、协议匹配）不黑洞主机本身，落在红线的允许面上。
# 这个表必须**穷举**——lint 会拿实际插件里出现的类型来对，出现没登记的类型就构建失败：
# 新增一种规则匹配面时，必须先回答「它碰不碰得到红线」，门禁不许沉默。
DOMAIN_MATCH_TYPES = {
    "DOMAIN": "精确主机",
    "DOMAIN-SUFFIX": "后缀吞整族",
    "DOMAIN-KEYWORD": "关键词命中主机名任意位置",
}
NON_DOMAIN_MATCH_TYPES = {
    "URL-REGEX": "按 URL（含路径）匹配，不黑洞主机",
    "USER-AGENT": "按 UA 匹配，与主机无关",
    "DEST-PORT": "按端口匹配，与主机无关",
    "PROTOCOL": "按协议匹配，只在 AND 复合里作附加条件",
    "IP-CIDR": "按 IP 段匹配，域名红线无从比较",
    "IP6-CIDR": "按 IPv6 段匹配，域名红线无从比较",
    "PROCESS-NAME": "按进程名匹配，仅 macOS",
    "GEOSITE": "按内置地理集匹配，与广告无关",
    "GEOIP": "按内置地理 IP 段匹配",
    "FINAL": "兜底策略，不拦截",
}
COMPOSITE_TYPES = {"AND", "OR", "NOT"}
NON_MATCH_TOKENS = {
    "NO-RESOLVE": "规则参数，不是匹配面",
    "REJECT": "动作",
}
RULE_TYPES = (
    set(DOMAIN_MATCH_TYPES)
    | set(NON_DOMAIN_MATCH_TYPES)
    | set(COMPOSITE_TYPES)
    | set(NON_MATCH_TOKENS)
)

# 抽取表由分类表生成：把一种匹配面登记为「域名类」，判定就自动认得它——
# 分类与解析不许是两份要分别维护的名单（否则新类型的门禁只是装饰）。
_MATCH_ITEM_RE = re.compile(
    r"\b("
    + "|".join(
        sorted((re.escape(kind) for kind in DOMAIN_MATCH_TYPES), key=len, reverse=True)
    )
    + r")\s*,\s*([^,()\s]+)"
)
_TYPE_RE = re.compile(r"\b([A-Z][A-Z0-9-]{2,})\s*,")


def rule_match_items(rule: str) -> list[tuple[str, str]]:
    """一条 [Rule] 里的全部域名类匹配项，含 `AND((...))` 复合里的**嵌套**项。

    这一层存在是因为第 27 轮的检查只看 `rule.split(",")[0]`：`AND,((DOMAIN-SUFFIX,...),
    (PROTOCOL,QUIC)),REJECT` 的首个 token 是 `AND`，于是嵌套的 DOMAIN-SUFFIX 从来没被拿去
    比过红线；`DOMAIN-KEYWORD` 更是压根不在遍历范围内（`httpdns` 这种关键词若写成 `dns`，
    就会默认生效地捞走 `dns.jd.com`）。嵌套项与顶层项在 Loon 里对域名的作用范围相同，
    判定就必须相同。
    """
    return [(kind.upper(), target.lower()) for kind, target in _MATCH_ITEM_RE.findall(rule)]


def rule_type_tokens(rule: str) -> set[str]:
    """规则里出现过的类型 token（含嵌套），用于「有没有未归类的新匹配面」这项审计。"""
    return {token for token in _TYPE_RE.findall(rule)}


def match_item_hit(kind: str, target: str, entry: dict) -> bool:
    """域名类匹配项是否覆盖某条红线域。三种类型的语义各不相同，判定也必须不同。"""
    domain = entry["domain"]
    if kind == "DOMAIN":
        return domain == target
    if kind == "DOMAIN-SUFFIX":
        return domain == target or domain.endswith("." + target)
    if kind == "DOMAIN-KEYWORD":
        return target in domain
    raise ValueError(f"未知域名类匹配项 {kind!r}")


def rule_redline_hits(rule: str, entries: list[dict]) -> list[tuple[str, str, dict]]:
    """返回 (匹配类型, 目标, 红线条目) 三元组；一条规则能同时踩到几条就都报出来。"""
    hits = []
    for kind, target in rule_match_items(rule):
        for entry in entries:
            if match_item_hit(kind, target, entry):
                hits.append((kind, target, entry))
    return hits


def redline_hit(rule: str, entry: dict) -> bool:
    """一条拦截条目是否命中一条红线。

    禁止的是两种操作：把红线名字本身黑洞掉（`dns.jd.com = 127.0.0.1`），或用任何一层
    通配/后缀（`*.jd.com`、`DOMAIN-SUFFIX,jd.com`）把它捞进去。红线之下的**精确广告
    子域**不算命中——那正是全局 ads 插件对共享域的一贯纪律（只列广告专用主机，不碰主域）。
    host / family 两种记法在散文里语气不同（「这个主机绝不碰」vs「这个主域不做整族」），
    在这个判定里同构，所以不分支；kind 保留是为了让 quote 的语义可读。
    """
    domain = entry["domain"]
    if rule == domain:
        return True
    if rule.startswith("*."):
        base = rule[2:]
        return domain == base or domain.endswith("." + base)
    return False


def describe(entry: dict) -> str:
    return (
        f"{entry['slug']} 插件声明的红线 ({entry['domain']}, kind={entry['kind']}, "
        f"原文「{entry['quote']}」) ——{entry['why']}"
    )


def hostname_glob_regex(pattern: str) -> re.Pattern:
    """把 `[MITM] hostname` 的一项编译成匹配器：Loon 这里用 `*`（任意串）与 `?`（单字符）。

    字符串相等比不出 `p?.meituan.net` 这类形态到底罩住了谁，「没有红线被解密」这种结论
    就只能靠人肉看。判定必须发生在展开后的语义空间里（与第 27 轮 `=` 简写那次同课）。
    """
    out = []
    for ch in pattern:
        if ch == "*":
            out.append(".*")
        elif ch == "?":
            out.append(".")
        else:
            out.append(re.escape(ch))
    return re.compile("^" + "".join(out) + "$")


def mitm_reaches(pattern: str, entry: dict) -> bool:
    """一条 `[MITM]` hostname 是否会解密到某条红线主机（含 `*.` 罩住子树的情况）。"""
    pattern = pattern.lower()
    domain = entry["domain"]
    if hostname_glob_regex(pattern).fullmatch(domain):
        return True
    if pattern.startswith("*."):
        rest = hostname_glob_regex(pattern[2:])
        parts = domain.split(".")
        return any(rest.fullmatch(".".join(parts[i:])) for i in range(len(parts) - 1))
    return False


PROTECTED_SOURCE = ROOT / "src/ads/protected-roots.json"


def hand_protected_roots() -> set[str]:
    """人工维护的那张「共享主域不许整族黑洞」表（全球广告网络与消费互联网品牌）。"""
    data = json.loads(PROTECTED_SOURCE.read_text(encoding="utf-8"))
    return {item for item in data.get("roots", []) if isinstance(item, str)}


def redline_roots(entries: list[dict] | None = None) -> set[str]:
    """红线域的可注册根——这张表由红线**派生**，不靠人记得同步（第二十八/二十九轮的同一课）。

    `protected-roots.json` 是手写表，写它的时候还没有 13 个 App 插件，所以 `meituan.net`、
    `ttlock.com`、`cmbchina.com`、`cup.com.cn`、`goofish.com` 这些「某款 App 明写绝不碰」的根
    一个都不在里面。后果不是拦了红线（那条有独立判定），而是**整族黑洞**这一层失守：
    `*.meituan.net` 今天能通过所有校验，而它等于把美团的开放平台、外卖、点评、二维码域名一起
    打成 127.0.0.1。红线说这个根下的主机碰不得，那这个根就属于「只准精确打击」的那一类。
    """
    entries = load_app_redlines() if entries is None else entries
    return {registrable(entry["domain"]) for entry in entries}


def protected_roots(entries: list[dict] | None = None) -> set[str]:
    """两个构建器与 lint 都读这一个出口：手写表 ∪ 红线派生根。"""
    return hand_protected_roots() | redline_roots(entries)


if __name__ == "__main__":
    rows = load_app_redlines()
    print(f"redlines: {len(rows)} 条，覆盖 {len({r['slug'] for r in rows})} 个 App")
