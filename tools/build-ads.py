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

Ad-subdomain globs in `domain_wildcards` become active
`DOMAIN-WILDCARD,<glob>,REJECT,pre-matching` rules. They require Loon
3.5.3(1008)+ and must never match a protected shared root.

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

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src/ads/domains.json"
PROTECTED = ROOT / "src/ads/protected-roots.json"
OUT_DIR = ROOT / "plugins/ads"
TARGET = "127.0.0.1"
# DOMAIN-WILDCARD 自 Loon 3.5.3(1008) 起提供，插件头必须同步抬高门槛。
LOON_VERSION = "3.5.3(1008)"
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
RULE_PARAMS = {"extended-matching", "pre-matching", "no-resolve"}
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


def load_protected() -> set[str]:
    data = load_json(PROTECTED)
    roots = data.get("roots")
    if not isinstance(roots, list) or not roots:
        raise BuildError(f"{PROTECTED}: roots must be a non-empty list")
    out = set()
    for root in roots:
        if not isinstance(root, str) or not DOMAIN_RE.match(root) or root.startswith("*."):
            raise BuildError(f"{PROTECTED}: invalid protected root: {root!r}")
        out.add(root.lower())
    return out


def expand_rule(rule: str) -> list[str]:
    if rule.startswith("="):
        base = rule[1:]
        if not base:
            raise BuildError("empty '=' rule")
        return [base, "*." + base]
    return [rule]


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


def glob_regex(pattern: str) -> re.Pattern[str]:
    """Translate a Loon DOMAIN-WILDCARD glob for safety checks.

    Loon supports `*` (crosses dots), `?` and `[...]` sets. The ads builder
    only accepts `*`/`?`; character sets are refused so the protected-root
    check cannot drift from Loon's semantics.
    """
    parts = []
    for char in pattern:
        if char == "*":
            parts.append(".*")
        elif char == "?":
            parts.append(".")
        else:
            parts.append(re.escape(char))
    return re.compile("".join(parts) + r"\Z")


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

    if checked and build_number(LOON_VERSION) < WILDCARD_MIN_BUILD:
        raise BuildError(
            f"{where}: DOMAIN-WILDCARD needs Loon build {WILDCARD_MIN_BUILD}+, "
            f"but the plugin declares {LOON_VERSION}"
        )
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

    protected = load_protected()
    if seen is None:
        seen = {}
    lines: list[str] = []
    lines.append(f"#!name={plugin['name']}")
    lines.append(f"#!desc={plugin['desc']}")
    lines.append(f"#!author={plugin['author']}")
    lines.append(f"#!version={plugin['version']}")
    lines.append(f"#!homepage={plugin['homepage']}")
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
        "rules_disabled": 0,
        "ip_rewrite": 0,
        "ip_rewrite_disabled": 0,
        "groups": 0,
        "active": 0,
        "disabled": 0,
        "expanded": 0,
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
    wildcards = validate_domain_wildcards(plugin, protected)
    if rules or wildcards:
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
        lines.append("# 广告子域通配层：DOMAIN-WILDCARD（Loon 3.5.3(1008)+）")
        lines.append("# " + "-" * 76)
        lines.append("# 只锚定广告专用前缀；'*' 跨点匹配，命中 ads.com / ads.a.com / ads.a.b.com，")
        lines.append("# 不命中 a.com、ad.example.com 或 adsl.example.com。")
        lines.append("# pre-matching 让拒绝发生在 DNS 阶段（配合主配置 domain-reject-mode = DNS）。")
        lines.append("# 每条 glob 在 build 与 lint 阶段都校验不命中 protected-roots.json。")
        lines.append("# " + "=" * 76)
        for pattern in wildcards:
            lines.append(f"DOMAIN-WILDCARD,{pattern},REJECT,pre-matching")
            counts["wildcards"] += 1

    rules_disabled = plugin.get("rules_disabled") or []
    if rules_disabled:
        lines.append("")
        lines.append("# " + "=" * 76)
        lines.append("# 可选规则（默认关闭）")
        lines.append("# " + "-" * 76)
        lines.append("# 逐行取消行首的 '# ' 后生效；这些规则不参与上面的计数。")
        lines.append("# " + "=" * 76)
        for raw in rules_disabled:
            if not isinstance(raw, str) or not raw.strip():
                raise BuildError(
                    f"plugin {plugin['file']}: empty rules_disabled line"
                )
            raw = raw.strip()
            if raw.startswith("#"):
                lines.append(raw)
            else:
                validate_rule_line(raw, f"plugin {plugin['file']}, [Rule] optional")
                lines.append("# " + raw)
                counts["rules_disabled"] += 1

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
        if disabled:
            counts["disabled"] += len(group_rules)
        else:
            counts["active"] += len(group_rules)
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
        for key in ("author", "homepage", "icon"):
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
    args = parser.parse_args()

    try:
        outputs, stats = expected_outputs()
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        return check_outputs(outputs)
    if args.stats:
        for name, counts in stats.items():
            print(
                f"{name:18} general={counts['general']:2} rules={counts['rules']:2} "
                f"wildcards={counts['wildcards']:2} "
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
            f"wildcards={counts['wildcards']:2} "
            f"optional_rules={counts['rules_disabled']:2} "
            f"ip_rewrite={counts['ip_rewrite']:2} "
            f"optional_ip_rewrite={counts['ip_rewrite_disabled']:2} "
            f"groups={counts['groups']:2} active={counts['active']:3} "
            f"disabled={counts['disabled']:3} expanded={counts['expanded']:3}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
