#!/usr/bin/env python3
"""Validate examples/loon.conf, configs/loon.conf, the max-config ledger, and
the routing manual.

This is intentionally stricter than Loon itself in four places:
  * DoH/DoH3/DoQ upstreams may use a domain only when no active plugin [Host]
    maps that domain (or a covering wildcard) to 127.0.0.1/0.0.0.0.  This is
    the real failure mode behind the 2026-10-29 blackhole, not "domain form is
    always wrong": ads 2.8.0 moved the domestic public DoH entries to a
    commented optional group;
  * the public config must not contain an active [Remote Proxy]/[Proxy] node
    or ca-p12/ca-passphrase;
  * logical rules must use the documented AND,((...),(...)),POLICY shape;
  * every in-repo plugin must be auto-loaded by configs/loon.conf.

It also binds docs/loon-max-config.md to the example file and to the ledger
counts, and docs/loon-routing-host-asn.md to an exhaustive rule-type and
Host-map matrix, so the documents cannot drift away from the config they
describe.
"""
from __future__ import annotations

import functools
import ipaddress
import pathlib
import re
import sys
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/loon.conf"
PUBLIC_CONFIG = ROOT / "configs/loon.conf"
ROUTING_EXAMPLE = ROOT / "examples/loon-routing.conf"
DOC = ROOT / "docs/loon-max-config.md"
DEEP_DIVE = ROOT / "docs/loon-routing-host-asn.md"
OUR_PLUGIN_BASE = "https://raw.githubusercontent.com/AshNail/plugins/main/plugins/"

GENERAL_KEYS = {
    "include-tun", "bypass-tun", "skip-proxy", "dns-server", "doh-server",
    "doq-server", "doh3-server", "hijack-dns", "ip-mode", "ipv6-vif",
    "allow-wifi-access", "wifi-access-http-port", "wifi-access-socks5-port",
    "proxy-test-url", "internet-test-url", "test-timeout", "resource-parser",
    "ssid-trigger", "interface-mode", "real-ip", "disable-udp-ports",
    "disable-stun", "udp-fallback-mode", "geoip-url", "ipasn-url",
    "domain-reject-mode", "dns-reject-mode", "sni-sniffing",
}
DEPRECATED_GENERAL = {
    "ipv6", "switch-node-after-failure-times", "force-http-engine-hosts",
    "skip-first-packet",
}
# Present in the current app-exported profile but not in the official General
# parameter table. Keep it explicit instead of silently treating it as official.
UNDOCUMENTED_GENERAL = {"sni-sniffing"}
PLUGIN_KEYS = {"tag", "proxy", "enabled", "enable", "pin"}
ENUMS = {
    "ip-mode": {"v4-only", "dual", "prefer-v4", "prefer-v6", "v6-only"},
    "ipv6-vif": {"off", "auto", "always"},
    "interface-mode": {"auto", "cellular", "performance", "balance"},
    "udp-fallback-mode": {"DIRECT", "REJECT"},
    "domain-reject-mode": {"DNS", "Request"},
    "dns-reject-mode": {"LOOPBACKIP", "NOANSWER", "NXDOMAIN"},
}
SECTION_NAMES = {
    "General", "Host", "Rule", "Rewrite", "Script", "MITM", "Proxy",
    "Proxy Group", "Remote Proxy", "Plugin",
}
RULE_TYPES = {
    "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD",
    "URL-REGEX", "USER-AGENT", "IP-CIDR", "IP-CIDR6", "GEOIP", "IP-ASN",
    "AND", "OR", "NOT", "SRC-PORT", "DEST-PORT", "PROCESS-NAME",
    "PROTOCOL", "FINAL",
}
IP_RULE_TYPES = {"IP-CIDR", "IP-CIDR6", "GEOIP", "IP-ASN"}
POLICIES = {
    "DIRECT", "REJECT", "REJECT-IMG", "REJECT-DICT", "REJECT-ARRAY",
    "REJECT-DROP", "PROXY",
}
PROTOCOLS = {"HTTP", "HTTPS", "TCP", "QUIC", "STUN", "UDP"}
SURGE_ONLY = ("pre-matching", "extended-matching")
# Official example.conf reserved/documentation ranges. The public config claimed
# to carry the full set but had dropped these; keep them pinned so prose cannot
# drift away from the file again.
OFFICIAL_RESERVED_RANGES = {
    "192.0.0.0/24", "192.0.2.0/24", "192.88.99.0/24",
    "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
}
HOST_MAP_TYPES = {
    "ipv4", "ipv6", "alias", "server", "ssid", "ip-mode", "ip-to-ip",
    "use-in-proxy",
}
DOMAIN_RE = re.compile(r"(\*\.)?[A-Za-z0-9._-]+\.[A-Za-z]{2,}")
HOST_KEY_RE = re.compile(r"[A-Za-z0-9.*?_-]+\.[A-Za-z]{2,}")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def strip_comment(line: str) -> str:
    """Loon has no inline comment syntax we rely on; only full-line comments."""
    return line.strip()


def parse_sections(text: str, label: str = "examples/loon.conf"):
    section = None
    out = []
    for num, raw in enumerate(text.splitlines(), 1):
        line = strip_comment(raw)
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            if section not in SECTION_NAMES:
                err(f"{label}:{num}: unknown section [{section}]")
            out.append((section, num, None))
            continue
        if section is None:
            err(f"{label}:{num}: line outside any section: {line[:80]}")
            continue
        out.append((section, num, line))
    return out


def split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def check_dns_token(token: str, key: str, where: str, allow_system: bool = False) -> None:
    if allow_system and token == "system":
        return
    if token.startswith(("http://", "https://", "h3://", "quic://")):
        err(f"{where}: {key} 不允许 URL 形态: {token}")
        return
    host = token
    if token.startswith("["):
        m = re.fullmatch(r"\[([0-9a-fA-F:]+)\](?::(\d+))?", token)
        if not m or not is_ip(m.group(1)):
            err(f"{where}: {key} 非法 IPv6 地址: {token}")
            return
        host = m.group(1)
        port = m.group(2)
    else:
        port = None
        if token.count(":") == 1:
            host, port = token.split(":", 1)
    if not is_ip(host):
        err(f"{where}: {key} 必须是 IP 或 system: {token}")
    if port is not None and not (port.isdigit() and 1 <= int(port) <= 65535):
        err(f"{where}: {key} 端口非法: {token}")


@functools.lru_cache(maxsize=1)
def plugin_host_blackholes() -> tuple[frozenset[str], frozenset[str]]:
    """Active plugin [Host] -> 127.0.0.1/0.0.0.0, as exact and wildcard suffixes."""
    exact: set[str] = set()
    wildcard: set[str] = set()
    for plugin in sorted((ROOT / "plugins").glob("*/*.plugin")):
        section = None
        for raw in plugin.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip()
                continue
            if section != "Host" or not line or line.startswith("#") or "=" not in line:
                continue
            left, right = line.split("=", 1)
            target = right.split(",", 1)[0].strip()
            if target not in ("127.0.0.1", "0.0.0.0"):
                continue
            host = left.strip().lower().rstrip(".")
            if host.startswith("*."):
                wildcard.add(host[2:])
            else:
                exact.add(host)
    return frozenset(exact), frozenset(wildcard)


def plugin_blackholes(host: str) -> bool:
    host = host.lower().rstrip(".")
    exact, wildcard = plugin_host_blackholes()
    if host in exact:
        return True
    return any(host == suffix or host.endswith("." + suffix) for suffix in wildcard)


def check_dns_url(token: str, scheme: str, where: str) -> None:
    if scheme == "https":
        ok = token.startswith("https://")
    elif scheme == "h3":
        ok = token.startswith("h3://")
    else:
        ok = token.startswith("quic://")
    if not ok:
        err(f"{where}: 需要 {scheme}:// 开头: {token}")
        return
    parsed = urlsplit(token)
    if not parsed.hostname:
        err(f"{where}: {scheme} 上游缺少主机名: {token}")
        return
    if not is_ip(parsed.hostname) and plugin_blackholes(parsed.hostname):
        err(
            f"{where}: {scheme} 上游域名被当前生效的插件 [Host] 黑洞: "
            f"{parsed.hostname}（改 IP 形式或关闭对应插件的可选 DoH 组）"
        )
        return
    if parsed.port is not None and not (1 <= parsed.port <= 65535):
        err(f"{where}: 端口非法: {token}")


def check_cidr_list(value: str, where: str, key: str) -> None:
    for token in split_csv(value):
        if token in ("localhost",) or token.startswith("*."):
            continue
        if "/" in token:
            try:
                ipaddress.ip_network(token, strict=False)
            except ValueError:
                err(f"{where}: {key} 非法 CIDR: {token}")
        elif not is_ip(token):
            # Official bypass-tun/skip-proxy accept domains too; keep a shape check.
            if not re.fullmatch(r"[A-Za-z0-9.*_-]+\.[A-Za-z]{2,}", token):
                err(f"{where}: {key} 非法地址: {token}")


def check_port(value: str, where: str, key: str) -> None:
    if not value.isdigit() or not (1 <= int(value) <= 65535):
        err(f"{where}: {key} 端口必须是 1-65535: {value}")


def check_general(key: str, value: str, where: str) -> None:
    if key in DEPRECATED_GENERAL:
        err(f"{where}: 已弃用参数 {key}（官方明确新配置不应继续使用）")
        return
    if key not in GENERAL_KEYS:
        err(f"{where}: 未知 [General] 键 {key}")
        return
    if key in UNDOCUMENTED_GENERAL:
        warn(f"{where}: {key} 不在官方《通用配置》参数表；本次按 App 导出值保留，不作为官方依据")
    if key in ENUMS:
        allowed = {item.lower(): item for item in ENUMS[key]}
        for item in split_csv(value):
            if item.lower() not in allowed:
                err(f"{where}: {key} 取值 {item!r} 不在 {sorted(ENUMS[key])} 内")
    if key in ("allow-wifi-access", "disable-stun"):
        if value not in ("true", "false"):
            err(f"{where}: {key} 必须是 true/false: {value}")
    if key in ("wifi-access-http-port", "wifi-access-socks5-port"):
        check_port(value, where, key)
    if key == "test-timeout":
        try:
            if float(value) <= 0:
                raise ValueError
        except ValueError:
            err(f"{where}: test-timeout 必须是正数: {value}")
    if key == "dns-server":
        for token in split_csv(value):
            check_dns_token(token, key, where, allow_system=True)
    if key == "doh-server":
        for token in split_csv(value):
            check_dns_url(token, "https", f"{where} {key}")
    if key == "doh3-server":
        for token in split_csv(value):
            check_dns_url(token, "h3", f"{where} {key}")
    if key == "doq-server":
        for token in split_csv(value):
            check_dns_url(token, "quic", f"{where} {key}")
    if key in ("bypass-tun", "skip-proxy"):
        check_cidr_list(value, where, key)
    if key == "include-tun":
        for token in split_csv(value):
            if "/" not in token:
                err(f"{where}: include-tun 必须带前缀长度: {token}")
                continue
            try:
                net = ipaddress.ip_network(token, strict=False)
            except ValueError:
                err(f"{where}: include-tun 非法 CIDR: {token}")
                continue
            if net.version != 4:
                err(f"{where}: include-tun 只接受 IPv4: {token}")
    if key == "hijack-dns":
        for token in split_csv(value):
            if token in ("*:53", "*:0"):
                continue
            if ":" in token:
                host, port = token.rsplit(":", 1)
                if host != "*" and not is_ip(host):
                    err(f"{where}: hijack-dns 非法目标: {token}")
                if port != "*" and not (port.isdigit() and int(port) <= 65535):
                    err(f"{where}: hijack-dns 端口非法: {token}")
            elif not is_ip(token):
                err(f"{where}: hijack-dns 非法目标: {token}")
    if key == "disable-udp-ports":
        for token in split_csv(value):
            check_port(token, where, key)
    if key in ("resource-parser", "geoip-url", "ipasn-url"):
        if not value.startswith(("http://", "https://")):
            err(f"{where}: {key} 需要 http(s) URL: {value}")
    if key == "ssid-trigger":
        if not re.fullmatch(r'.+', value) or ":" not in value:
            err(f"{where}: ssid-trigger 形态应为 \"SSID\":策略,...: {value}")
    if key == "real-ip":
        for token in split_csv(value):
            # `stun.*` is used in the current profile to cover STUN hosts in any
            # TLD; the wildcard TLD is intentional, not a typo.
            if not re.fullmatch(r"(\*\.)?[A-Za-z0-9.*_-]+\.(?:[A-Za-z]{2,}|\*)", token):
                err(f"{where}: real-ip 非法域名: {token}")


def split_top_level(text: str, track_parens: bool = False) -> list[str]:
    """Split on commas outside quotes (and, for logical rules, parentheses)."""
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_quote = False
    for ch in text:
        if in_quote:
            buf.append(ch)
            if ch == '"':
                in_quote = False
            continue
        if ch == '"':
            in_quote = True
            buf.append(ch)
        elif track_parens and ch == "(":
            depth += 1
            buf.append(ch)
        elif track_parens and ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf).strip())
    return parts


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def check_policy(policy: str, where: str, group_names: set[str]) -> bool:
    if policy not in POLICIES and policy not in group_names:
        err(f"{where}: 策略 {policy!r} 未声明")
        return False
    return True


def check_rule_atom(kind: str, value: str, extras: list[str], where: str,
                    context: str = "config") -> str:
    value = unquote(value)
    if not value:
        err(f"{where}: {kind} 的值不能为空")
        return kind
    if kind in ("SRC-PORT", "DEST-PORT"):
        if value.startswith(">="):
            value = value[2:]
        elif "-" in value:
            a, b = value.split("-", 1)
            if not (a.isdigit() and b.isdigit() and 1 <= int(a) <= int(b) <= 65535):
                err(f"{where}: {kind} 区间非法: {value}")
            value = a
        if not value.isdigit() or not (1 <= int(value) <= 65535):
            err(f"{where}: {kind} 端口非法: {value}")
    elif kind == "PROTOCOL":
        if value.upper() not in PROTOCOLS:
            err(f"{where}: PROTOCOL 取值非法: {value}")
    elif kind in ("IP-CIDR", "IP-CIDR6"):
        try:
            net = ipaddress.ip_network(value, strict=False)
        except ValueError:
            err(f"{where}: {kind} 非法网段: {value}")
            net = None
        if net and kind == "IP-CIDR" and net.version != 4:
            err(f"{where}: IP-CIDR 只能放 IPv4: {value}")
        if net and kind == "IP-CIDR6" and net.version != 6:
            err(f"{where}: IP-CIDR6 只能放 IPv6: {value}")
    elif kind == "IP-ASN":
        if not value.isdigit():
            err(f"{where}: IP-ASN 必须是数字: {value}")
        elif not 1 <= int(value) <= 4294967295:
            err(f"{where}: IP-ASN 超出 32 位 ASN 范围: {value}")
    elif kind == "GEOIP":
        if not re.fullmatch(r"[A-Za-z]{2}", value):
            err(f"{where}: GEOIP 必须是两位国家代码: {value}")
    elif kind in ("DOMAIN", "DOMAIN-SUFFIX"):
        if not DOMAIN_RE.fullmatch(value):
            err(f"{where}: {kind} 域名形态可疑: {value}")
    elif kind in ("DOMAIN-KEYWORD", "URL-REGEX", "USER-AGENT"):
        pass
    elif kind == "DOMAIN-WILDCARD":
        if not re.fullmatch(r"[A-Za-z0-9.*?\[\]!^_-]+", value):
            err(f"{where}: DOMAIN-WILDCARD 含 Glob 之外的字符: {value}")
        if context == "config":
            warn(f"{where}: DOMAIN-WILDCARD 需要 Build 1008+，当前 App Store 3.5.2(996) 不识别")
    elif kind == "PROCESS-NAME":
        if context == "config":
            warn(f"{where}: PROCESS-NAME 只在 macOS 生效；iOS/tvOS 忽略，含进程条件的整条逻辑规则也会被忽略")
    else:
        err(f"{where}: 未知原子规则类型 {kind}")
    if "no-resolve" in extras and kind not in IP_RULE_TYPES:
        err(f"{where}: no-resolve 只用于 IP 类规则: {kind}")
    for extra in extras:
        if extra and extra != "no-resolve":
            err(f"{where}: 未知规则参数 {extra!r}（Loon 文档只定义 no-resolve）")
    return kind


DOMAIN_RULE_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD"}


def check_logic_rule(line: str, kind: str, where: str, group_names: set[str],
                     context: str = "config", expect_policy: bool = True) -> str:
    rest = line.split(",", 1)[1].strip() if "," in line else ""
    if not rest.startswith("(("):
        err(f"{where}: {kind} 子规则必须写成 ((...),(...)) 形态")
        return kind
    depth = 0
    end = None
    for i, ch in enumerate(rest):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        err(f"{where}: {kind} 括号不闭合")
        return kind
    inner = rest[1:end]
    tail = rest[end + 1:].strip()
    if expect_policy:
        if not tail.startswith(","):
            err(f"{where}: {kind} 缺少策略")
        else:
            policy = tail[1:].strip()
            if not policy or "," in policy:
                err(f"{where}: {kind} 策略只能有一个: {policy!r}")
            else:
                check_policy(policy, where, group_names)
    elif tail:
        err(f"{where}: 逻辑子规则不能自带策略: {tail[:40]}")
    subs = split_top_level(inner, track_parens=True)
    if not subs:
        err(f"{where}: {kind} 没有子规则")
        return kind
    for sub in subs:
        if not (sub.startswith("(") and sub.endswith(")")):
            err(f"{where}: {kind} 子规则必须用括号包裹: {sub[:60]}")
            continue
        check_subrule(sub[1:-1].strip(), where, context)
    if kind == "NOT":
        if len(subs) != 1:
            err(f"{where}: NOT 只能包含一个子规则，当前 {len(subs)}")
    elif len(subs) < 2:
        warn(f"{where}: {kind} 官方语义是组合多个子规则，当前只有 {len(subs)} 个")
    atom_kinds = []
    for sub in subs:
        inner_s = sub[1:-1].strip() if sub.startswith("(") and sub.endswith(")") else sub
        atom_kinds.append(inner_s.split(",", 1)[0].strip().upper())
    ip_positions = [i for i, k in enumerate(atom_kinds) if k in IP_RULE_TYPES]
    domain_positions = [i for i, k in enumerate(atom_kinds) if k in DOMAIN_RULE_TYPES]
    if ip_positions and domain_positions and min(ip_positions) < min(domain_positions):
        warn(f"{where}: 官方建议逻辑规则里的 IP 子规则放在域名子规则之后，减少不必要的 DNS 查询")
    return kind


def check_subrule(inner: str, where: str, context: str = "config") -> None:
    if not inner:
        err(f"{where}: 空子规则")
        return
    kind = inner.split(",", 1)[0].strip().upper()
    if kind in ("AND", "OR", "NOT"):
        check_logic_rule(inner, kind, where, set(), context, expect_policy=False)
        return
    parts = split_top_level(inner)
    if len(parts) < 2:
        err(f"{where}: 子规则至少需要 类型,值: {inner[:60]}")
        return
    if kind not in RULE_TYPES:
        err(f"{where}: 未知子规则类型 {kind}")
        return
    if kind == "FINAL":
        err(f"{where}: FINAL 不能作为逻辑子规则")
        return
    check_rule_atom(kind, parts[1], parts[2:], where, context)


def check_rule(line: str, where: str, group_names: set[str],
               context: str = "config") -> str | None:
    for token in SURGE_ONLY:
        if token in line:
            err(f"{where}: {token} 是 Surge 写法，Loon 无此参数")
    kind = line.split(",", 1)[0].strip().upper()
    if kind not in RULE_TYPES:
        err(f"{where}: 未知规则类型 {kind}")
        return None
    if kind in ("AND", "OR", "NOT"):
        return check_logic_rule(line, kind, where, group_names, context)
    parts = split_top_level(line)
    if kind == "FINAL":
        if len(parts) != 2:
            err(f"{where}: FINAL 只接受一个策略")
            return "FINAL"
        check_policy(parts[1], where, group_names)
        return "FINAL"
    if len(parts) < 3:
        err(f"{where}: 规则至少需要 类型,值,策略: {line}")
        return kind
    check_policy(parts[2], where, group_names)
    check_rule_atom(kind, parts[1], parts[3:], where, context)
    return kind


def check_host_server(value: str, where: str, context: str = "config") -> None:
    value = value.strip()
    if value == "system":
        return
    if value.startswith(("https://", "h3://", "quic://")):
        parsed = urlsplit(value)
        if not parsed.hostname:
            err(f"{where}: server: URL 缺少主机名: {value}")
            return
        if parsed.port is not None and not (1 <= parsed.port <= 65535):
            err(f"{where}: server: URL 端口非法: {value}")
        if context == "config" and not is_ip(parsed.hostname):
            warn(f"{where}: server: 使用域名形式加密 DNS；若该域名被 ads 插件黑洞，会解析失败（全局 DoH 基线要求 IP 形式）")
        return
    host = value
    port = None
    if value.startswith("["):
        m = re.fullmatch(r"\[([0-9a-fA-F:]+)\](?::(\d+))?", value)
        if not m:
            err(f"{where}: server: 非法 IPv6 地址: {value}")
            return
        host, port = m.group(1), m.group(2)
    elif value.count(":") == 1:
        host, port = value.split(":", 1)
    if not is_ip(host):
        err(f"{where}: server: 值必须是 system、IP[:端口] 或 https/h3/quic URL: {value}")
        return
    if port is not None and not (port.isdigit() and 1 <= int(port) <= 65535):
        err(f"{where}: server: 端口非法: {value}")


def check_host_line(line: str, where: str, context: str = "config") -> set[str]:
    kinds: set[str] = set()
    if "=" not in line:
        err(f"{where}: [Host] 行缺少 '=': {line}")
        return kinds
    left, right = [p.strip() for p in line.split("=", 1)]
    if not left or not right:
        err(f"{where}: [Host] 行左右不能为空: {line}")
        return kinds
    primary: list[str] = []
    for token in split_top_level(right):
        if token.startswith("use-in-proxy="):
            val = token.split("=", 1)[1].strip()
            if val not in ("true", "false"):
                err(f"{where}: use-in-proxy 必须是 true/false: {token}")
            else:
                kinds.add("use-in-proxy")
        else:
            primary.append(token)
    if not primary:
        err(f"{where}: [Host] 缺少映射目标: {line}")
        return kinds
    if len(primary) > 1:
        warn(f"{where}: 官方 Host 示例一行只写一个映射目标；组合写法未文档化")
    if left.startswith("ssid:"):
        kinds.add("ssid")
        if not re.fullmatch(r"ssid:.+", left):
            err(f"{where}: SSID 左值形态可疑: {left}")
        for target in primary:
            if not target.startswith("server:"):
                err(f"{where}: SSID 映射只文档化了 server: 右值: {target}")
            else:
                check_host_server(target.split(":", 1)[1].strip(), where, context)
                kinds.add("server")
        return kinds
    if is_ip(left):
        for target in primary:
            if not is_ip(target):
                err(f"{where}: IP 到 IP 映射的右值必须是 IP: {target}")
            else:
                kinds.add("ip-to-ip")
        return kinds
    if not HOST_KEY_RE.fullmatch(left):
        err(f"{where}: Host 左值域名形态可疑: {left}")
    for target in primary:
        if target.startswith("server:"):
            check_host_server(target.split(":", 1)[1].strip(), where, context)
            kinds.add("server")
        elif target.startswith("ip-mode:"):
            mode = target.split(":", 1)[1].strip()
            if mode not in ENUMS["ip-mode"]:
                err(f"{where}: ip-mode 取值非法: {mode}")
            else:
                kinds.add("ip-mode")
        elif is_ip(target):
            try:
                version = ipaddress.ip_address(target).version
            except ValueError:
                version = 4
            kinds.add("ipv6" if version == 6 else "ipv4")
        elif DOMAIN_RE.fullmatch(target):
            kinds.add("alias")
        else:
            err(f"{where}: 无法识别的 Host 右值: {target}")
    return kinds


def validate_example(text: str, label: str = "examples/loon.conf", public: bool = False) -> dict:
    items = parse_sections(text, label)
    seen_general = set()
    general_values: dict[str, str] = {}
    seen_sections = set()
    group_names: set[str] = set()
    rule_active = []
    plugin_urls: list[str] = []
    ours: set[str] = set()
    mitm_hostname = False
    stats = {"general": 0, "optional": 0, "rules": 0, "plugins": 0}
    for section, num, line in items:
        if line is None:
            seen_sections.add(section)
            continue
        where = f"{label}:{num}"
        if section == "General":
            key, sep, value = line.partition("=")
            if not sep:
                err(f"{where}: [General] 行缺少 '=': {line}")
                continue
            key = key.strip().lower()
            value = value.strip()
            if key in seen_general:
                err(f"{where}: [General] 重复键 {key}")
            seen_general.add(key)
            general_values[key] = value
            check_general(key, value, where)
            stats["general"] += 1
        elif section == "Host":
            check_host_line(line, where)
        elif section == "Rule":
            rule_active.append((num, line))
            check_rule(line, where, group_names)
            stats["rules"] += 1
        elif section == "MITM":
            key = line.split("=", 1)[0].strip().lower() if "=" in line else line
            if key in ("ca-p12", "ca-passphrase"):
                err(f"{where}: 公开示例禁止内嵌 CA 私钥/口令（{key}）")
            elif key in ("enable", "skip-server-cert-verify"):
                err(f"{where}: {key} 不在官方 MitM 三参数表内")
            elif key != "hostname":
                err(f"{where}: [MITM] 未知键 {key}")
            else:
                mitm_hostname = True
        elif section == "Plugin":
            parts = split_top_level(line)
            url = parts[0].strip()
            if not url.startswith(("http://", "https://")):
                err(f"{where}: [Plugin] 行必须是 URL,...: {line[:80]}")
                continue
            if public and not url.startswith("https://"):
                err(f"{where}: 公开配置的插件 URL 必须是 https: {url[:80]}")
            opts: dict[str, str] = {}
            for opt in parts[1:]:
                key, sep, value = opt.partition("=")
                key, value = key.strip(), value.strip()
                if not sep or not key or not value:
                    err(f"{where}: [Plugin] 选项必须是 key=value: {opt!r}")
                    continue
                if key not in PLUGIN_KEYS:
                    err(f"{where}: [Plugin] 未知选项 {key!r}（允许 {sorted(PLUGIN_KEYS)}）")
                    continue
                if key in opts:
                    err(f"{where}: [Plugin] 重复选项 {key}")
                opts[key] = value
            if "enabled" in opts and "enable" in opts:
                err(f"{where}: [Plugin] enabled/enable 只能写一个")
            if not ({"enabled", "enable"} & opts.keys()):
                if public:
                    err(f"{where}: [Plugin] 必须显式 enabled=true/false")
                else:
                    warn(f"{where}: [Plugin] 行建议显式 enable=true/false")
            for key in ("enabled", "enable", "pin"):
                if key in opts and opts[key] not in ("true", "false"):
                    err(f"{where}: [Plugin] {key} 必须是 true/false: {opts[key]}")
            if "proxy" in opts:
                check_policy(opts["proxy"], where, group_names)
            if url in plugin_urls:
                err(f"{where}: [Plugin] 重复登记 {url}")
            plugin_urls.append(url)
            stats["plugins"] += 1
            if url.startswith(OUR_PLUGIN_BASE):
                rel = url[len(OUR_PLUGIN_BASE):]
                m = re.fullmatch(r"([^/]+)/([^/]+)\.plugin", rel)
                if m and m.group(1) == m.group(2):
                    ours.add(m.group(1))
                else:
                    err(f"{where}: 本仓插件 URL 必须是 plugins/<slug>/<slug>.plugin: {url}")
        elif section in ("Proxy Group",):
            name = line.split("=", 1)[0].strip()
            if name:
                group_names.add(name)
        elif section in ("Proxy", "Remote Proxy") and public:
            err(f"{where}: 公开配置禁止写入节点/订阅（[{section}] 有效行）")
    if "FINAL" not in [l.split(",")[0].upper() for _, l in rule_active]:
        err(f"{label}: [Rule] 缺少 FINAL")
    elif rule_active and rule_active[-1][1].split(",")[0].upper() != "FINAL":
        err(f"{label}: FINAL 必须是 [Rule] 的最后一条")
    final_count = sum(1 for _, l in rule_active if l.split(",")[0].upper() == "FINAL")
    if final_count != 1:
        err(f"{label}: FINAL 只能有一条，当前 {final_count}")
    required = {"General", "Rule"}
    if public:
        required |= {"Proxy Group", "Plugin", "MITM"}
    missing = required - seen_sections
    if missing:
        err(f"{label}: 缺少段 {sorted(missing)}")
    if public:
        if len(text.encode("utf-8")) >= 1_000_000:
            err(f"{label}: 超过 Loon 配置导入 1 MB 上限（{len(text.encode('utf-8'))} bytes）")
        for key in ("bypass-tun", "skip-proxy"):
            missing = sorted(OFFICIAL_RESERVED_RANGES - set(split_csv(general_values.get(key, ""))))
            if missing:
                err(f"{label}: {key} 缺少官方 example.conf 的保留网段 {missing}")
        if "*.icloud.com" not in split_csv(general_values.get("real-ip", "")):
            err(f"{label}: real-ip 缺少官方示例的 *.icloud.com")
        if stats["plugins"] < 40:
            err(f"{label}: 公开全功能配置应自动加载至少 40 个插件，当前 {stats['plugins']}")
        if stats["rules"] < 400:
            err(f"{label}: 公开全功能配置应包含完整分流规则（>=400），当前 {stats['rules']}")
        if not mitm_hostname:
            err(f"{label}: 公开配置缺少 [MITM] hostname 排除表")
        repo_plugins = {p.stem for p in (ROOT / "plugins").glob("*/*.plugin")}
        missing_plugins = sorted(repo_plugins - ours)
        if missing_plugins:
            err(f"{label}: 本仓插件未被自动加载: {missing_plugins}")
    stats["general_keys"] = len(seen_general)
    stats["sections"] = len(seen_sections)
    stats["ours"] = len(ours)
    stats["plugin_urls"] = len(plugin_urls)
    return stats


def extract_marked(text: str, start: str, end: str) -> str | None:
    if start not in text or end not in text:
        return None
    block = text.split(start, 1)[1].split(end, 1)[0]
    m = re.search(r"```(?:ini|conf|config|loon)?\n(.*?)^```", block, re.M | re.S)
    if not m:
        return None
    return m.group(1).rstrip() + "\n"


def check_doc(example_text: str) -> tuple[int, tuple[int, int, int, int, int]] | None:
    if not DOC.exists():
        err(f"missing {DOC.relative_to(ROOT)}")
        return None
    text = DOC.read_text(encoding="utf-8")
    marked = extract_marked(text, "<!-- base-config:start -->", "<!-- base-config:end -->")
    if marked is None:
        err("docs/loon-max-config.md: 缺少 base-config 标记/围栏")
    elif marked.rstrip() != example_text.rstrip():
        err("docs/loon-max-config.md: base-config 围栏与 examples/loon.conf 不一致")
    if "examples/loon.conf" not in text:
        err("docs/loon-max-config.md: 必须指向 examples/loon.conf")
    if "<!-- ledger:start -->" not in text or "<!-- ledger:end -->" not in text:
        err("docs/loon-max-config.md: 缺少 ledger 标记")
        return None
    ledger = text.split("<!-- ledger:start -->", 1)[1].split("<!-- ledger:end -->", 1)[0]
    rows = [ln for ln in ledger.splitlines() if re.match(r"^\|\s*\d+\s*\|", ln)]
    m = re.search(r"<!-- ledger-count:\s*(\d+)\s*-->", text)
    if not m:
        err("docs/loon-max-config.md: 缺少 ledger-count")
    elif int(m.group(1)) != len(rows):
        err(f"docs/loon-max-config.md: ledger-count={m.group(1)}，实际 {len(rows)} 行")
    counts = {"✅": 0, "🟡": 0, "❌": 0, "—": 0, "⚪": 0}
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 4:
            err(f"docs/loon-max-config.md: ledger 行列数不足: {row[:80]}")
            continue
        status = cells[3]
        for mark in counts:
            if status.startswith(mark):
                counts[mark] += 1
                break
        else:
            err(f"docs/loon-max-config.md: ledger 行状态无法识别: {status}")
    got = (counts["✅"], counts["🟡"], counts["❌"], counts["—"], counts["⚪"])
    m = re.search(r"<!-- ledger-counts:\s*(\d+)/(\d+)/(\d+)/(\d+)/(\d+)\s*-->", text)
    if not m:
        err("docs/loon-max-config.md: 缺少 ledger-counts")
    elif tuple(int(x) for x in m.groups()) != got:
        err(f"docs/loon-max-config.md: ledger-counts={m.groups()}，实际 {got}")
    return len(rows), got


def extract_marked_code(text: str, start: str, end: str) -> tuple[str, int] | None:
    """Return (code, first_code_line) for the first fenced block between markers."""
    lines = text.splitlines()
    i0 = next((i for i, line in enumerate(lines) if start in line), None)
    if i0 is None:
        return None
    i1 = next((i for i in range(i0 + 1, len(lines)) if end in lines[i]), None)
    if i1 is None:
        return None
    code: list[str] = []
    fence_line = None
    for i in range(i0 + 1, i1):
        line = lines[i]
        if fence_line is None:
            if line.strip().startswith("```"):
                fence_line = i + 2
            continue
        if line.strip().startswith("```"):
            break
        code.append(line)
    if fence_line is None or not code:
        return None
    return "\n".join(code) + "\n", fence_line


def check_deep_dive() -> tuple[int, int, int, int, int] | None:
    if not DEEP_DIVE.exists():
        err(f"missing {DEEP_DIVE.relative_to(ROOT)}")
        return None
    text = DEEP_DIVE.read_text(encoding="utf-8")
    rel = DEEP_DIVE.relative_to(ROOT).as_posix()
    m = re.search(r"<!--\s*routing-counts:\s*(\d+)/(\d+)\s*-->", text)
    if not m:
        err(f"{rel}: 缺少 routing-counts")
    elif (int(m.group(1)), int(m.group(2))) != (len(RULE_TYPES), len(HOST_MAP_TYPES)):
        err(f"{rel}: routing-counts={m.groups()}，实际 {len(RULE_TYPES)}/{len(HOST_MAP_TYPES)}")
    if "../examples/loon.conf" not in text:
        err(f"{rel}: 必须指向 examples/loon.conf")
    if "examples/loon-routing.conf" not in text:
        err(f"{rel}: 必须指向 examples/loon-routing.conf")

    block = extract_marked_code(text, "<!-- rule-matrix:start -->", "<!-- rule-matrix:end -->")
    rule_lines = 0
    rule_types: set[str] = set()
    if block is None:
        err(f"{rel}: 缺少 rule-matrix 标记/围栏")
    else:
        code, line0 = block
        for i, raw in enumerate(code.splitlines(), line0):
            line = raw.strip()
            if not line or line.startswith("#") or (line.startswith("[") and line.endswith("]")):
                continue
            kind = check_rule(line, f"{rel}:{i}", set(), context="matrix")
            if kind:
                rule_types.add(kind)
            rule_lines += 1
        missing = sorted(RULE_TYPES - rule_types)
        if missing:
            err(f"{rel}: 规则矩阵缺少类型 {missing}")

    block = extract_marked_code(text, "<!-- host-matrix:start -->", "<!-- host-matrix:end -->")
    host_lines = 0
    host_types: set[str] = set()
    if block is None:
        err(f"{rel}: 缺少 host-matrix 标记/围栏")
    else:
        code, line0 = block
        for i, raw in enumerate(code.splitlines(), line0):
            line = raw.strip()
            if not line or line.startswith("#") or (line.startswith("[") and line.endswith("]")):
                continue
            host_types |= check_host_line(line, f"{rel}:{i}", context="matrix")
            host_lines += 1
        missing = sorted(HOST_MAP_TYPES - host_types)
        if missing:
            err(f"{rel}: Host 矩阵缺少映射类型 {missing}")

    block = extract_marked_code(text, "<!-- routing-recipe:start -->", "<!-- routing-recipe:end -->")
    recipe_lines = 0
    recipe: list[tuple[str | None, str]] = []
    if block is None:
        err(f"{rel}: 缺少 routing-recipe 标记/围栏")
    else:
        code, line0 = block
        for i, raw in enumerate(code.splitlines(), line0):
            line = raw.strip()
            if not line or line.startswith("#") or (line.startswith("[") and line.endswith("]")):
                continue
            recipe.append((check_rule(line, f"{rel}:{i}", set(), context="recipe"), line))
            recipe_lines += 1
        if not recipe:
            err(f"{rel}: routing-recipe 为空")
        else:
            if recipe[-1][0] != "FINAL":
                err(f"{rel}: routing-recipe 的 FINAL 必须是最后一条")
            if sum(1 for kind, _ in recipe if kind == "FINAL") != 1:
                err(f"{rel}: routing-recipe 必须有且只有一条 FINAL")

    return len(RULE_TYPES), len(HOST_MAP_TYPES), rule_lines, host_lines, recipe_lines


def check_routing_example() -> tuple[int, int] | None:
    if not ROUTING_EXAMPLE.exists():
        err(f"missing {ROUTING_EXAMPLE.relative_to(ROOT)}")
        return None
    text = ROUTING_EXAMPLE.read_text(encoding="utf-8")
    validate_example(text, "examples/loon-routing.conf")
    rules = [(num, line) for section, num, line in
             parse_sections(text, "examples/loon-routing.conf")
             if section == "Rule" and line is not None]
    kinds = [line.split(",", 1)[0].strip().upper() for _, line in rules]
    if not rules:
        err("examples/loon-routing.conf: [Rule] 为空")
        return None
    if kinds[-1] != "FINAL":
        err("examples/loon-routing.conf: FINAL 必须是最后一条")
    if kinds.count("FINAL") != 1:
        err(f"examples/loon-routing.conf: FINAL 只能有一条，当前 {kinds.count('FINAL')}")
    for kind in ("DOMAIN-SUFFIX", "IP-ASN", "GEOIP", "DEST-PORT"):
        if kind not in kinds:
            err(f"examples/loon-routing.conf: 缺少顺序演示规则 {kind}")
    domain_pos = [i for i, kind in enumerate(kinds)
                  if kind in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD")]
    ip_pos = [i for i, kind in enumerate(kinds) if kind in IP_RULE_TYPES]
    if domain_pos and ip_pos and min(domain_pos) > min(ip_pos):
        err("examples/loon-routing.conf: 域名规则必须排在 IP 规则之前")
    if "IP-ASN" in kinds and "GEOIP" in kinds and kinds.index("IP-ASN") > kinds.index("GEOIP"):
        err("examples/loon-routing.conf: IP-ASN 应排在 GEOIP 之前（更具体 → 更宽）")
    for num, line in rules:
        if line.upper().startswith("IP-ASN,") and "no-resolve" in line:
            err(f"examples/loon-routing.conf:{num}: 顺序演示必须让域名触发解析，不能写 no-resolve")
    return len(rules), len(set(kinds))


def main() -> int:
    text = EXAMPLE.read_text(encoding="utf-8")
    stats = validate_example(text)
    if not PUBLIC_CONFIG.exists():
        err(f"missing {PUBLIC_CONFIG.relative_to(ROOT)}")
        public_stats = None
    else:
        public_stats = validate_example(
            PUBLIC_CONFIG.read_text(encoding="utf-8"), "configs/loon.conf", public=True
        )
    ledger = check_doc(text)
    routing = check_deep_dive()
    routing_example = check_routing_example()
    for msg in warnings:
        print(f"WARN {msg}")
    for msg in errors:
        print(f"ERROR {msg}", file=sys.stderr)
    if errors:
        print(f"config check failed: {len(errors)} error(s)", file=sys.stderr)
        return 1
    if ledger:
        rows, counts = ledger
        print(f"ledger ok: {rows} rows (✅{counts[0]} / 🟡{counts[1]} / ❌{counts[2]} / —{counts[3]} / ⚪{counts[4]})")
    if routing:
        rule_types, host_types, rule_lines, host_lines, recipe_lines = routing
        print(
            f"routing ok: {rule_types} rule types / {host_types} host map types "
            f"({rule_lines} rule lines, {host_lines} host lines, {recipe_lines} recipe lines)"
        )
    if routing_example:
        rule_lines, rule_kinds = routing_example
        print(f"routing example ok: {rule_lines} rule(s) / {rule_kinds} type(s) "
              f"(domain -> asn -> geoip -> port -> final)")
    print(
        "config ok: "
        f"sections={stats['sections']} general={stats['general_keys']} "
        f"rules={stats['rules']} base-config matches examples/loon.conf"
    )
    if public_stats:
        print(
            "public config ok: "
            f"plugins={public_stats['plugins']} (in-repo={public_stats['ours']}) "
            f"rules={public_stats['rules']} sections={public_stats['sections']} "
            f"general={public_stats['general_keys']} no nodes/CA"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
