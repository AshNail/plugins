#!/usr/bin/env python3
"""Generate the single ads plugin from src/ads/domains.json.

Source of truth:
  src/ads/domains.json          metadata + [General]/[Rule]/[Host] data
  src/ads/protected-roots.json  shared roots that must never be wildcarded

Generated artifact:
  plugins/ads/ads.plugin

Rule shorthand in [Host]:
  =example.com   -> example.com AND *.example.com
  *.example.com  -> wildcard only
  example.com    -> exact only

Ad-subdomain globs in `domain_wildcards` become `DOMAIN-WILDCARD,<glob>,REJECT`
rules. The rule type requires Loon 3.5.3(1008)+ (currently TestFlight-only),
so both wildcard layers are emitted COMMENTED by default — uncommented only on
3.5.3+. Globs must never match a protected shared root.

Note: Loon rules take no parameters other than the documented `no-resolve`
(and only IP rules use it). `pre-matching` / `extended-matching` are *Surge*
parameters — Loon's equivalents are on by default (`domain-reject-mode`
lives in the main config, which a plugin cannot set), so emit neither.

Usage:
  python3 tools/build-ads.py            # write the generated plugin
  python3 tools/build-ads.py --check    # verify the committed plugin is current
  python3 tools/build-ads.py --stats    # print rule counts
"""
from __future__ import annotations

import argparse
import difflib
import ipaddress
import json
import pathlib
import re
import sys

from redlines import describe as describe_redline
from redlines import expand_rule as shared_expand_rule
from redlines import load_app_redlines, redline_hit, redline_roots
from redlines import rule_match_items, rule_redline_hits

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src/ads/domains.json"
PROTECTED = ROOT / "src/ads/protected-roots.json"
OUT_DIR = ROOT / "plugins/ads"
TARGET = "127.0.0.1"
# 版本门槛 = App Store 正式版基线：Loon 3.5.2(996)。
# DOMAIN-WILDCARD 自 3.5.3(1008)（当前仅 TestFlight）起提供，低版本对未知规则类型
# 是「跳过还是整段报错」官方文档未详述——因此两层通配默认注释输出，
# 3.5.2 用户不受任何影响，3.5.3+ 用户逐行去掉 '# ' 即可启用。
LOON_VERSION = "3.5.2(996)"
WILDCARD_MIN_BUILD = 1008

# Loon plugin [General] only supports this whitelist. Anything else is ignored
# by Loon, so fail loudly instead of shipping a switch that looks useful.
GENERAL_KEYS = {
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

# Plugin rules may only use DIRECT, REJECT* or PROXY. The ads plugin is a
# blocking plugin, so we additionally refuse DIRECT/PROXY here.
REJECT_POLICIES = {
    "REJECT",
    "REJECT-IMG",
    "REJECT-DICT",
    "REJECT-ARRAY",
    "REJECT-DROP",
    "REJECT-NO-DROP",
    "REJECT-IMG-NO-DROP",
    "REJECT-VIDEO",
    "REJECT-VIDEO-NO-DROP",
    "REJECT-DICT-NO-DROP",
    "REJECT-ARRAY-NO-DROP",
}
IP_REWRITE_ACTIONS = {"reflect", "reject", "drop"}
RULE_PARAMS = {"no-resolve"}
RULE_TYPES = {
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

# A conservative hostname check. Loon [Host] accepts hostnames, not IPs, on the
# left-hand side. `*` is only allowed as a whole leading label.
DOMAIN_RE = re.compile(
    r"^(?:\*\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
# DOMAIN-WILDCARD globs must be anchored to a literal label plus '.'/'-'.
# This keeps a typo like `*` or `ads*` from turning into a broad block.
WILDCARD_LITERAL_RE = re.compile(
    r"[a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)*[.-]"
)
META_KEYS = ("name", "desc", "author", "version", "homepage", "icon", "tag", "system")


class BuildError(RuntimeError):
    pass


def load_json(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BuildError(f"missing source file: {path}")
    except json.JSONDecodeError as exc:
        raise BuildError(f"invalid JSON in {path}: {exc}")


def load_protected(redlines: list[dict] | None = None) -> set[str]:
    """手写表 ∪ 由 App 红线派生的根——两个构建器与 lint 都走 tools/redlines.py 这一个出口。

    手写表成型时还没有 13 个 App 插件，`meituan.net`、`ttlock.com`、`cmbchina.com` 这些
    「某款 App 明写绝不碰」的根都不在里面；靠人记得同步必然再漏一次，所以派生层写进代码。
    """
    data = load_json(PROTECTED)
    roots = data.get("roots")
    if not isinstance(roots, list) or not roots:
        raise BuildError(f"{PROTECTED}: roots must be a non-empty list")
    out = set()
    for root in roots:
        if not isinstance(root, str) or not DOMAIN_RE.match(root) or root.startswith("*."):
            raise BuildError(f"{PROTECTED}: invalid protected root: {root!r}")
        out.add(root.lower())
    return out | redline_roots(redlines)


def expand_rule(rule: str) -> list[str]:
    try:
        return shared_expand_rule(rule)
    except ValueError as exc:
        raise BuildError(str(exc)) from exc


# 「红线」必须是数据，不是散文：每个 App 插件在自己的 JSON 里结构化声明绝不触碰的域，
# 全局 ads 插件与按 App 插件的**默认生效条目**都不许命中它。名单和判定住在
# tools/redlines.py，两个构建器共用同一份纪律；这里只把 ValueError 升格成 BuildError。
def app_redlines() -> list[dict]:
    try:
        return load_app_redlines()
    except (ValueError, OSError) as exc:
        raise BuildError(str(exc)) from exc


def check_rule_vectors(plugin: dict, rules: list[str], redlines: list[dict]) -> int:
    """[Rule] 段里的域名类匹配项同样受红线约束——包括 AND 复合里嵌套的那一层。

    第 27 轮只检查了 `[Host]` 条目，`DOMAIN-KEYWORD,httpdns` 这类关键词面从来没被拿去比过红线：
    关键词的覆盖面比后缀还宽，写成 `dns` 就会默认生效地捞走 `dns.jd.com`。
    返回检查过的匹配项条数（供 --stats-json 打印，不写进文档当声明）。
    """
    items = 0
    for raw in rules:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        hits = rule_redline_hits(line, redlines)
        items += len(rule_match_items(line))
        for kind, target, item in hits:
            raise BuildError(
                f"plugin {plugin['file']}, [Rule]: {kind} 匹配项 {target!r} 命中 "
                f"{describe_redline(item)}——本仓库纪律：默认生效的域名类拦截不许触碰 App 红线，"
                "要留就留在默认注释组并写明两面理由"
            )
    return items


def validate_host_rule(rule: str, where: str, protected: set[str]) -> None:
    if not DOMAIN_RE.match(rule):
        raise BuildError(f"{where}: invalid hostname: {rule!r}")
    if rule != rule.lower():
        raise BuildError(f"{where}: hostnames must be lowercase: {rule!r}")
    if rule.startswith("*."):
        base = rule[2:]
        if base in protected:
            raise BuildError(
                f"{where}: refusing to wildcard protected shared root: {rule!r} "
                "(use an exact ad subdomain instead)"
            )
    elif rule in protected:
        raise BuildError(
            f"{where}: refusing to block a protected shared apex: {rule!r} "
            "(use an exact ad subdomain instead)"
        )


def build_number(version: str) -> int:
    match = re.search(r"\((\d+)\)", version or "")
    if not match:
        raise BuildError(f"cannot parse Loon build number from {version!r}")
    return int(match.group(1))


CLASS_RE = re.compile(r"\[([^\]]*)\]")


def glob_regex(pattern: str) -> re.Pattern[str]:
    """Translate a Loon DOMAIN-WILDCARD glob for safety checks.

    Loon supports `*` (crosses dots), `?` and `[...]` sets. The ads builder
    accepts `*`/`?` everywhere and exactly one character class, `[0-9]`:
    a digit class cannot widen a match to a different brand's host the way
    `[a-z]` or `[!0-9]` could, so the protected-root check stays meaningful.
    """
    parts = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "[":
            end = pattern.find("]", index + 1)
            if end == -1:
                raise BuildError(f"unterminated character class: {pattern!r}")
            body = pattern[index + 1 : end]
            if body != "0-9":
                raise BuildError(
                    f"only the [0-9] character class is supported: {pattern!r}"
                )
            parts.append("[0-9]")
            index = end + 1
            continue
        if char == "*":
            parts.append(".*")
        elif char == "?":
            parts.append(".")
        else:
            parts.append(re.escape(char))
        index += 1
    return re.compile("".join(parts) + r"\Z")


def redline_glob_hits(patterns: list[str], redlines: list[dict]) -> list[tuple[str, dict]]:
    """DOMAIN-WILDCARD 层与 App 红线的重叠：glob 无法带例外，只能如实列出来。"""
    hits: list[tuple[str, dict]] = []
    for pattern in patterns:
        regex = glob_regex(pattern)
        for entry in redlines:
            if regex.fullmatch(entry["domain"]):
                hits.append((pattern, entry))
    return hits


def validate_redline_overlap(plugin: dict, patterns: list[str], redlines: list[dict]) -> list[dict]:
    """通配层命中红线时，必须在数据里逐条认罪（glob + domain 集合要精确相等）。

    Loon 的 DOMAIN-WILDCARD 没有例外语法，`ads.*` 命中 `ads.privacy.qq.com` 这类
    「必须放行」的合规入口是无解的取舍。默认注释 + 手工开启的那一层不许藏着这种取舍，
    所以命中集必须被显式列举：漏一条构建失败，多列一条（红线已不重叠了还挂着）也失败。
    """
    where = f"plugin {plugin.get('file', '?')}, redline_overlap"
    disclosed = plugin.get("redline_overlap") or []
    if not isinstance(disclosed, list):
        raise BuildError(f"{where}: must be a list")
    by_domain = {entry["domain"]: entry for entry in redlines}
    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    for item in disclosed:
        if not isinstance(item, dict):
            raise BuildError(f"{where}: 条目必须是对象")
        glob, domain, app, why = (item.get(key) for key in ("glob", "domain", "app", "why"))
        if glob not in patterns:
            raise BuildError(f"{where}: {glob!r} 不在 domain_wildcards/family_wildcards 里")
        entry = by_domain.get(domain)
        if entry is None:
            raise BuildError(f"{where}: {domain!r} 不是任何 App 声明的红线域")
        if entry["slug"] != app:
            raise BuildError(f"{where}: {domain!r} 属于 {entry['slug']}，不是 {app!r}")
        if not isinstance(why, str) or not why:
            raise BuildError(f"{where}: {glob!r}/{domain!r} 缺 why")
        if (glob, domain) in seen:
            raise BuildError(f"{where}: 重复条目 {glob!r}/{domain!r}")
        seen.add((glob, domain))
        rows.append({"glob": glob, "domain": domain, "app": app, "why": why})
    actual = {(glob, entry["domain"]) for glob, entry in redline_glob_hits(patterns, redlines)}
    missing = sorted(actual - seen)
    extra = sorted(seen - actual)
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"未认罪的重叠 {missing}")
        if extra:
            parts.append(f"已不再重叠却仍挂着的认罪条目 {extra}")
        raise BuildError(f"{where}: {'；'.join(parts)}——命中集由 glob 与 redlines 实算，不许各自漂")
    return sorted(rows, key=lambda row: (row["glob"], row["domain"]))


def validate_domain_wildcards(plugin: dict, protected: set[str]) -> list[str]:
    where = f"plugin {plugin.get('file', '?')}, domain_wildcards"
    patterns = plugin.get("domain_wildcards") or []
    if not isinstance(patterns, list):
        raise BuildError(f"{where}: must be a list")
    checked: list[str] = []
    for raw in patterns:
        if not isinstance(raw, str) or not raw.strip():
            raise BuildError(f"{where}: empty glob")
        pattern = raw.strip()
        if pattern != pattern.lower():
            raise BuildError(f"{where}: globs must be lowercase: {pattern!r}")
        if any(char in pattern for char in "[]!\\ "):
            raise BuildError(
                f"{where}: only '*' and '?' are supported in generated globs: {pattern!r}"
            )
        if "*" not in pattern and "?" not in pattern:
            raise BuildError(f"{where}: glob has no wildcard: {pattern!r}")
        literal = pattern.split("*", 1)[0].split("?", 1)[0]
        if len(literal) < 4 or not WILDCARD_LITERAL_RE.fullmatch(literal):
            raise BuildError(
                f"{where}: glob must start with a literal label of 3+ chars "
                f"followed by '.' or '-': {pattern!r}"
            )
        regex = glob_regex(pattern)
        for root in protected:
            if regex.fullmatch(root):
                raise BuildError(
                    f"{where}: glob {pattern!r} matches protected shared root {root!r}"
                )
        if pattern in checked:
            raise BuildError(f"{where}: duplicate glob: {pattern!r}")
        checked.append(pattern)

    return checked


def enumerated_hosts(plugin: dict) -> set[str]:
    """Every concrete hostname the [Host] layer already enumerates."""
    out: set[str] = set()
    for group in plugin.get("groups") or []:
        for raw in group.get("rules") or []:
            if not isinstance(raw, str):
                continue
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            for rule in expand_rule(raw):
                if not rule.startswith("*."):
                    out.add(rule.lower())
    return out


def validate_family_wildcards(
    plugin: dict, protected: set[str], enumerated: set[str]
) -> list[str]:
    """Digit-shard family globs: `ads[0-9]-normal*.zijieapi.com`.

    These exist to cover siblings the [Host] layer never saw. Each pattern has
    to earn its place, so the build refuses anything that is not a real family:
    at least two already-enumerated hosts must match, the first label must keep
    four literal characters, and no protected shared root may be matched.
    """
    where = f"plugin {plugin.get('file', '?')}, family_wildcards"
    patterns = plugin.get("family_wildcards") or []
    if not isinstance(patterns, list):
        raise BuildError(f"{where}: must be a list")
    checked: list[str] = []
    for raw in patterns:
        if not isinstance(raw, str) or not raw.strip():
            raise BuildError(f"{where}: empty glob")
        pattern = raw.strip()
        if pattern != pattern.lower():
            raise BuildError(f"{where}: globs must be lowercase: {pattern!r}")
        if any(char in pattern for char in "!\\ "):
            raise BuildError(f"{where}: unsupported character in glob: {pattern!r}")
        if "[0-9]" not in pattern:
            raise BuildError(
                f"{where}: family globs must contain a [0-9] class: {pattern!r}"
            )
        for body in CLASS_RE.findall(pattern):
            if body != "0-9":
                raise BuildError(
                    f"{where}: only [0-9] is supported, got [{body}]: {pattern!r}"
                )
        if pattern.count("[") != pattern.count("]"):
            raise BuildError(f"{where}: unbalanced character class: {pattern!r}")
        first_label = re.sub(r"\[0-9\]", "", pattern.split(".", 1)[0])
        literal = first_label.replace("*", "").replace("?", "")
        if len(literal) < 3:
            raise BuildError(
                f"{where}: first label needs 3+ literal characters: {pattern!r}"
            )
        regex = glob_regex(pattern)
        for root in protected:
            if regex.fullmatch(root):
                raise BuildError(
                    f"{where}: glob {pattern!r} matches protected shared root {root!r}"
                )
        hits = sorted(host for host in enumerated if regex.fullmatch(host))
        if len(hits) < 2:
            raise BuildError(
                f"{where}: glob {pattern!r} covers {len(hits)} enumerated host(s); "
                "a family needs at least 2 (use domain_wildcards otherwise)"
            )
        if pattern in checked:
            raise BuildError(f"{where}: duplicate glob: {pattern!r}")
        checked.append(pattern)

    return checked


def is_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        return False
    return True


def validate_general_line(raw: str, where: str) -> None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return
    if "=" not in line:
        raise BuildError(f"{where}: [General] line must be key = value: {raw!r}")
    key, value = (part.strip() for part in line.split("=", 1))
    if key not in GENERAL_KEYS:
        raise BuildError(
            f"{where}: unsupported plugin [General] key {key!r}; "
            "Loon ignores keys outside its plugin whitelist"
        )
    if not value:
        raise BuildError(f"{where}: empty [General] value for {key!r}")

    values = [item.strip() for item in value.split(",") if item.strip()]
    if key == "dns-server":
        if any(item.lower() == "system" for item in values):
            raise BuildError(
                f"{where}: dns-server must not contain 'system' in the ads plugin; "
                "the main config decides whether system DNS is enabled"
            )
        for item in values:
            if not (is_ipv4(item) or DOMAIN_RE.match(item)):
                raise BuildError(f"{where}: invalid dns-server value: {item!r}")
    elif key == "doh-server":
        for item in values:
            if not item.startswith("https://"):
                raise BuildError(f"{where}: doh-server must use https://: {item!r}")
            host = item[len("https://") :].split("/", 1)[0].split(":", 1)[0]
            if not is_ipv4(host):
                raise BuildError(
                    f"{where}: doh-server must use an IP literal, not a hostname "
                    f"(avoids blocking its own bootstrap): {item!r}"
                )
    elif key in {"doh3-server"}:
        for item in values:
            if not item.startswith("h3://"):
                raise BuildError(f"{where}: doh3-server must use h3://: {item!r}")
            host = item[len("h3://") :].split("/", 1)[0].split(":", 1)[0]
            if not is_ipv4(host):
                raise BuildError(
                    f"{where}: doh3-server must use an IP literal, not a hostname "
                    f"(avoids blocking its own bootstrap): {item!r}"
                )
    elif key == "doq-server":
        # Loon accepts both quic:// and a bare host:port. The ads plugin does
        # not currently use DoQ, so keep this permissive but explicit.
        for item in values:
            if not item.startswith(("quic://", "doq://")):
                raise BuildError(f"{where}: doq-server must use quic:// or doq://: {item!r}")


# docs/cn/protocol_rule.md：Loon（3.1.7+）PROTOCOL 规则支持的全量取值。
PROTOCOL_VALUES = {"HTTP", "HTTPS", "TCP", "QUIC", "STUN", "UDP"}


def validate_rule_line(raw: str, where: str) -> None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 3:
        raise BuildError(f"{where}: malformed [Rule] line: {raw!r}")
    rule_type = parts[0]
    if rule_type == "FINAL":
        raise BuildError(f"{where}: FINAL is not allowed in the ads plugin")
    if rule_type not in RULE_TYPES:
        raise BuildError(f"{where}: unsupported [Rule] type: {rule_type!r}")
    if rule_type == "PROTOCOL" and parts[1] not in PROTOCOL_VALUES:
        raise BuildError(
            f"{where}: unsupported PROTOCOL value: {parts[1]!r}"
            " (expected HTTP/HTTPS/TCP/QUIC/STUN/UDP)"
        )
    policy = parts[2]
    if policy not in REJECT_POLICIES:
        raise BuildError(
            f"{where}: ads [Rule] policy must be a REJECT variant, got {policy!r}"
        )
    for param in parts[3:]:
        if param and param not in RULE_PARAMS:
            raise BuildError(f"{where}: unsupported [Rule] parameter: {param!r}")


def validate_ip_rewrite_line(raw: str, where: str, ip_seen: set[str]) -> tuple[str, str]:
    line = raw.strip()
    if not line or line.startswith("#"):
        return "", ""
    if "=" not in line:
        raise BuildError(f"{where}: [IP Rewrite] line must be IP = action: {raw!r}")
    ip, action = (part.strip() for part in line.split("=", 1))
    if not is_ipv4(ip) or "/" in ip:
        raise BuildError(
            f"{where}: [IP Rewrite] only supports single IPv4 address (no CIDR/IPv6): {ip!r}"
        )
    if ip == "119.29.29.29":
        raise BuildError(f"{where}: refusing to rewrite 119.29.29.29 (own dns-server)")
    if action not in IP_REWRITE_ACTIONS:
        raise BuildError(
            f"{where}: unsupported [IP Rewrite] action {action!r}; "
            "expected reflect/reject/drop"
        )
    if ip in ip_seen:
        raise BuildError(
            f"{where}: duplicate IPv4 in [IP Rewrite] (breaks Loon module): {ip!r}"
        )
    ip_seen.add(ip)
    return ip, action


def wrap_comment(text: str) -> list[str]:
    """Render source comments verbatim (one '#' line per source line).

    The notes contain English product names and Chinese punctuation; wrapping
    at spaces splits names like "Unity Ads" or "Amazon Ads" across lines, which
    makes the generated plugin harder to read. Loon ignores comment length, so
    preserve the author's line structure instead.
    """
    lines: list[str] = []
    for raw in text.splitlines():
        raw = raw.strip()
        lines.append("# " + raw if raw else "#")
    return lines


def render_lines(lines: list[str], raw_lines: list[str], where: str, validator) -> None:
    for raw in raw_lines:
        if not isinstance(raw, str) or not raw.strip():
            raise BuildError(f"{where}: empty line")
        validator(raw, where)
        lines.append(raw.strip())


def render_plugin(
    plugin: dict, meta: dict, seen: dict[str, str] | None = None
) -> tuple[str, dict]:
    missing = [key for key in META_KEYS if not plugin.get(key)]
    if missing:
        raise BuildError(f"plugin {plugin.get('file', '?')}: missing metadata {missing}")
    if not plugin.get("groups"):
        raise BuildError(f"plugin {plugin['file']}: no groups")

    redlines = app_redlines()
    protected = load_protected(redlines)
    if seen is None:
        seen = {}
    lines: list[str] = []
    lines.append(f"#!name={plugin['name']}")
    lines.append(f"#!desc={plugin['desc']}")
    lines.append(f"#!author={plugin['author']}")
    lines.append(f"#!version={plugin['version']}")
    lines.append(f"#!homepage={plugin['homepage']}")
    if plugin.get("openUrl"):
        lines.append(f"#!openUrl={plugin['openUrl']}")
    lines.append(f"#!icon={plugin['icon']}")
    lines.append(f"#!system={plugin['system']}")
    lines.append(f"#!loon_version={LOON_VERSION}")
    lines.append(f"#!date={meta['updated']}")
    lines.append(f"#!tag={plugin['tag']}")
    lines.append("#!type=normal")
    lines.append("")
    lines.append("# " + "=" * 76)
    lines.append(f"# {plugin['name']}")
    lines.append("# " + "-" * 76)
    lines.extend(wrap_comment("\n".join(plugin.get("intro", []))))
    lines.append("# " + "=" * 76)

    counts = {
        "general": 0,
        "rules": 0,
        "wildcards": 0,
        "family_wildcards": 0,
        "rules_disabled": 0,
        "ip_rewrite": 0,
        "ip_rewrite_disabled": 0,
        "groups": 0,
        "active": 0,
        "disabled": 0,
        "expanded": 0,
        "host_exact": 0,
        "host_wildcard": 0,
        "optional_protocol": 0,
        "optional_httpdns_ip": 0,
        "optional_public_ip": 0,
        "redline_entries": len(redlines),
        "redline_apps": len({entry["slug"] for entry in redlines}),
        "by_group": [],
    }

    general = plugin.get("general") or []
    if general:
        lines.append("")
        lines.append("")
        lines.append("[General]")
        for raw in general:
            if not isinstance(raw, str):
                raise BuildError(f"plugin {plugin['file']}: non-string [General] line")
            validate_general_line(raw, f"plugin {plugin['file']}, [General]")
            if raw.strip() and not raw.strip().startswith("#"):
                counts["general"] += 1
            lines.append(raw.strip())

    rules = plugin.get("rules") or []
    counts["rule_match_items"] = check_rule_vectors(plugin, rules, redlines)
    wildcards = validate_domain_wildcards(plugin, protected)
    families = validate_family_wildcards(plugin, protected, enumerated_hosts(plugin))
    overlaps = validate_redline_overlap(plugin, wildcards + families, redlines)
    counts["redline_overlap"] = len(overlaps)
    if rules or wildcards or families:
        lines.append("")
        lines.append("")
        lines.append("[Rule]")
    if rules:
        render_lines(
            lines,
            rules,
            f"plugin {plugin['file']}, [Rule]",
            validate_rule_line,
        )
        counts["rules"] = sum(
            1 for raw in rules if raw.strip() and not raw.strip().startswith("#")
        )
    if wildcards:
        lines.append("")
        lines.append("# " + "=" * 76)
        lines.append("# 广告子域通配层：DOMAIN-WILDCARD（Loon 3.5.3(1008)+，当前仅 TestFlight）")
        lines.append("# " + "-" * 76)
        lines.append("# 只锚定广告专用前缀；'*' 跨点匹配，命中 ads.com / ads.a.com / ads.a.b.com，")
        lines.append("# 不命中 a.com、ad.example.com 或 adsl.example.com。")
        lines.append("# 每条 glob 在 build 与 lint 阶段都校验不命中 protected-roots.json。")
        if overlaps:
            lines.append(
                "# 已知与 App 红线重叠（DOMAIN-WILDCARD 无例外语法，只能二选一）："
            )
            for row in overlaps:
                lines.append(
                    f"#   {row['glob']} 命中 {row['domain']}"
                    f"（{row['app']} 红线）：{row['why']}"
                )
            lines.append("# 开启本层前，请先删除命中的那条 glob，或接受上面写明的后果。")
        lines.append("# 默认保持注释：App Store 正式版仍是 3.5.2(996)，低版本遇到未知规则类型")
        lines.append("# 的行为官方未文档化（可能跳过、也可能整段失效），不拿 [Rule] 核心层冒险。")
        lines.append("# 已装 3.5.3+（TF build 1008-1011）的用户：逐行去掉行首 '# ' 即启用本层。")
        lines.append("# " + "=" * 76)
        for pattern in wildcards:
            lines.append(f"# DOMAIN-WILDCARD,{pattern},REJECT")
            counts["wildcards"] += 1

    if families:
        lines.append("")
        lines.append("# " + "=" * 76)
        lines.append("# 数字分片家族层：DOMAIN-WILDCARD + [0-9] 字符类（Loon 3.5.3(1008)+，仅 TF）")
        lines.append("# " + "-" * 76)
        lines.append("# 上一层的 glob 只能表达「左标签锚定」，覆盖不到 ads1/ads3/ads5 这类")
        lines.append("# 编号分片。字符类是 Loon 3.5.3(1008) 起支持的第三类通配符：")
        lines.append("#   DOMAIN-WILDCARD,ads[0-9]-normal*.zijieapi.com")
        lines.append("# 命中 ads3-normal-hl / ads5-normal / ads7-normal-xh 等全部分片，")
        lines.append("# 不命中 ads-normal（类必须恰好一位数字）或 adsxx-normal。")
        lines.append("# 每条家族 glob 在 build 阶段必须覆盖 2 个以上已枚举主机才被接受，")
        lines.append("# 因此这里只会出现「已经在用、但只列了一个分片」的真实家族。")
        lines.append("# " + "=" * 76)
        for pattern in families:
            lines.append(f"# DOMAIN-WILDCARD,{pattern},REJECT")
            counts["family_wildcards"] += 1

    rules_disabled = plugin.get("rules_disabled") or []
    if rules_disabled:
        lines.append("")
        lines.append("# " + "=" * 76)
        lines.append("# 可选规则（默认关闭）")
        lines.append("# " + "-" * 76)
        lines.append("# 逐行取消行首的 '# ' 后生效；这些规则不参与上面的计数。")
        lines.append("# " + "=" * 76)
        clean_rules = [raw.strip() for raw in rules_disabled]
        for raw in clean_rules:
            if not raw:
                raise BuildError(f"plugin {plugin['file']}: empty rules_disabled line")
        # 可选层在 README 里按「HTTPDNS 网关 IP / 公共 DNS 解析器 IP / STUN」三档拆分。
        # 题注约定：含「可选：」的注释开启一个新块，其下的「# —— 子题注 ——」只做补充。
        # 归属看当前块，不看单条 IP 长什么样——两档都是 IP-CIDR，机器分不出来。
        block = ""
        for raw in clean_rules:
            if raw.startswith("#"):
                if "可选：" in raw:
                    block = raw
                else:
                    block += " " + raw
                continue
            validate_rule_line(raw, f"plugin {plugin['file']}, [Rule] optional")
            counts["rules_disabled"] += 1
            if raw.startswith("PROTOCOL,"):
                counts["optional_protocol"] += 1
            elif "HTTPDNS" in block:
                counts["optional_httpdns_ip"] += 1
            else:
                counts["optional_public_ip"] += 1
        if counts["rules_disabled"] != (
            counts["optional_protocol"]
            + counts["optional_httpdns_ip"]
            + counts["optional_public_ip"]
        ):
            raise BuildError(f"plugin {plugin['file']}: optional [Rule] buckets do not sum")
        for raw in clean_rules:
            if raw.startswith("#"):
                lines.append(raw)
            else:
                lines.append("# " + raw)

    ip_rewrite = plugin.get("ip_rewrite") or []
    ip_rewrite_disabled = plugin.get("ip_rewrite_disabled") or []
    ip_seen: set[str] = set()

    if ip_rewrite:
        lines.append("")
        lines.append("")
        lines.append("[IP Rewrite]")
        for raw in ip_rewrite:
            if not isinstance(raw, str) or not raw.strip():
                raise BuildError(f"plugin {plugin['file']}: empty ip_rewrite line")
            validate_ip_rewrite_line(raw, f"plugin {plugin['file']}, [IP Rewrite]", ip_seen)
            lines.append(raw.strip())
            counts["ip_rewrite"] += 1

    if ip_rewrite_disabled:
        lines.append("")
        lines.append("# " + "=" * 76)
        lines.append("# 可选：[IP Rewrite]（Loon Build 1007+ 插件专属，TUN 阶段最快拦截）")
        lines.append("# " + "-" * 76)
        lines.append("# 语法：单 IPv4 = reflect|reject|drop。只收单 IPv4（不收 CIDR/域名/IPv6/参数）。")
        lines.append("# 在 [Rule]/Rewrite/脚本之前（TUN 阶段）生效=最快最彻底。")
        lines.append("# 同一 IP 重复声明按插件内首条生效；非法条目或重复的 [IP Rewrite] 段才会让整段失效。")
        lines.append("# 逐行取消行首的 '# ' 后生效。")
        lines.append("# ============================================================================ ")
        for raw in ip_rewrite_disabled:
            if not isinstance(raw, str) or not raw.strip():
                raise BuildError(f"plugin {plugin['file']}: empty ip_rewrite_disabled line")
            raw = raw.strip()
            if raw.startswith("#"):
                lines.append(raw)
            else:
                validate_ip_rewrite_line(raw, f"plugin {plugin['file']}, [IP Rewrite] optional", ip_seen)
                lines.append("# " + raw)
                counts["ip_rewrite_disabled"] += 1

    lines.append("")
    lines.append("")
    lines.append("[Host]")

    for group in plugin["groups"]:
        gid = group.get("id", "?")
        title = group.get("title")
        raw_rules = group.get("rules") or []
        if not title:
            raise BuildError(f"plugin {plugin['file']}: group {gid}: missing title")
        if not raw_rules:
            raise BuildError(f"plugin {plugin['file']}: group {gid}: empty rules")
        disabled = bool(group.get("disabled"))
        lines.append("")
        lines.append("# " + "=" * 76)
        lines.append(f"# {title}")
        lines.append("# " + "-" * 76)
        if group.get("note"):
            lines.extend(wrap_comment(group["note"]))
        if disabled:
            lines.append("#")
            lines.append("# ---- 默认关闭：逐行取消行首的 '# ' 后生效 ----")
        lines.append("# " + "=" * 76)

        group_rules: list[str] = []
        for raw in raw_rules:
            if not isinstance(raw, str) or not raw.strip():
                raise BuildError(f"plugin {plugin['file']}: group {gid}: empty rule")
            raw = raw.strip()
            for rule in expand_rule(raw):
                where = f"plugin {plugin['file']}, group {gid}"
                validate_host_rule(rule, where, protected)
                if rule in seen:
                    raise BuildError(
                        f"{where}: duplicate rule {rule!r} "
                        f"(already in {seen[rule]})"
                    )
                seen[rule] = f"plugin {plugin['file']}, group {gid}"
                group_rules.append(rule)

        counts["groups"] += 1
        if not disabled:
            for rule in group_rules:
                for entry in redlines:
                    if redline_hit(rule, entry):
                        raise BuildError(
                            f"plugin {plugin['file']}, group {gid}: 生效规则 {rule!r} 命中 "
                            f"{describe_redline(entry)}。全局插件不许拦按 App 插件自己划的生死线："
                            "要么删掉这条，要么把它放进默认注释组并写明两面理由。"
                        )
        counts["by_group"].append(
            {"id": gid, "title": title, "disabled": disabled, "rules": len(group_rules)}
        )
        if disabled:
            counts["disabled"] += len(group_rules)
        else:
            counts["active"] += len(group_rules)
            for rule in group_rules:
                if rule.startswith("*."):
                    counts["host_wildcard"] += 1
                else:
                    counts["host_exact"] += 1
        counts["expanded"] += len(group_rules)

        for rule in group_rules:
            line = f"{rule} = {TARGET}"
            lines.append(("# " + line) if disabled else line)

    lines.append("")
    text = "\n".join(lines)
    return text, counts


def expected_outputs() -> tuple[dict[str, str], dict[str, dict]]:
    source = load_json(SOURCE)
    meta = {
        "updated": source.get("updated"),
        "author": source.get("author"),
        "homepage": source.get("homepage"),
        "openUrl": source.get("openUrl"),
        "icon": source.get("icon"),
    }
    for key in ("updated", "author", "homepage", "icon"):
        if not meta[key]:
            raise BuildError(f"{SOURCE}: missing top-level {key!r}")
    plugins = source.get("plugins")
    if not isinstance(plugins, dict) or not plugins:
        raise BuildError(f"{SOURCE}: plugins must be a non-empty object")

    outputs: dict[str, str] = {}
    stats: dict[str, dict] = {}
    seen: dict[str, str] = {}
    for name, plugin in plugins.items():
        plugin = dict(plugin)
        # Inherit top-level metadata so a new plugin file only carries the
        # fields that differ.
        for key in ("author", "homepage", "icon", "openUrl"):
            plugin.setdefault(key, meta[key])
        file_name = plugin.get("file")
        if not file_name or not file_name.endswith(".plugin"):
            raise BuildError(f"plugin {name}: invalid file name: {file_name!r}")
        if file_name != "ads.plugin":
            raise BuildError(
                f"plugin {name}: only ads.plugin is allowed after the single-plugin merge"
            )
        if file_name in outputs:
            raise BuildError(f"duplicate output file: {file_name}")
        text, counts = render_plugin(plugin, meta, seen)
        outputs[file_name] = text
        stats[name] = counts
    return outputs, stats


def write_outputs(outputs: dict[str, str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for file_name, text in outputs.items():
        path = OUT_DIR / file_name
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


def check_outputs(outputs: dict[str, str]) -> int:
    failed = False
    for file_name, text in outputs.items():
        path = OUT_DIR / file_name
        if not path.exists():
            print(f"MISSING {path.relative_to(ROOT)}", file=sys.stderr)
            failed = True
            continue
        current = path.read_text(encoding="utf-8")
        if current == text:
            print(f"ok {path.relative_to(ROOT)}")
            continue
        failed = True
        print(f"STALE {path.relative_to(ROOT)}", file=sys.stderr)
        diff = difflib.unified_diff(
            current.splitlines(),
            text.splitlines(),
            fromfile=f"{path.name} (committed)",
            tofile=f"{path.name} (generated)",
            lineterm="",
            n=2,
        )
        for i, line in enumerate(diff):
            if i >= 120:
                print("... diff truncated ...", file=sys.stderr)
                break
            print(line, file=sys.stderr)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="verify the generated plugin is current")
    group.add_argument("--stats", action="store_true", help="print rule counts")
    group.add_argument(
        "--stats-json",
        action="store_true",
        help="print rule counts as JSON (single source for the README number gate)",
    )
    args = parser.parse_args()

    try:
        outputs, stats = expected_outputs()
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        return check_outputs(outputs)
    if args.stats_json:
        print(json.dumps(stats, ensure_ascii=False))
        return 0
    if args.stats:
        for name, counts in stats.items():
            print(
                f"{name:18} general={counts['general']:2} rules={counts['rules']:2} "
                f"wildcards_opt={counts['wildcards']:2} "
                f"families_opt={counts['family_wildcards']:2} "
                f"optional_rules={counts['rules_disabled']:2} "
                f"ip_rewrite={counts['ip_rewrite']:2} "
                f"optional_ip_rewrite={counts['ip_rewrite_disabled']:2} "
                f"groups={counts['groups']:2} active={counts['active']:3} "
                f"disabled={counts['disabled']:3} expanded={counts['expanded']:3}"
            )
        return 0

    write_outputs(outputs)
    for name, counts in stats.items():
        print(
            f"{name:18} general={counts['general']:2} rules={counts['rules']:2} "
            f"wildcards_opt={counts['wildcards']:2} "
            f"families_opt={counts['family_wildcards']:2} "
            f"optional_rules={counts['rules_disabled']:2} "
            f"ip_rewrite={counts['ip_rewrite']:2} "
            f"optional_ip_rewrite={counts['ip_rewrite_disabled']:2} "
            f"groups={counts['groups']:2} active={counts['active']:3} "
            f"disabled={counts['disabled']:3} expanded={counts['expanded']:3}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
