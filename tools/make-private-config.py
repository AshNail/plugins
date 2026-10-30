#!/usr/bin/env python3
"""Build a private Loon profile from configs/loon.conf + a local .lcf backup.

The public config intentionally contains no nodes, subscription URL, or CA.
This tool injects those three things from a Loon-exported .lcf, and writes the
result outside the repository with mode 0600.

It also preserves advanced .lcf settings the public baseline does not define:
extra [General] keys (include-tun, ssid-trigger, resource-parser, ipasn-url,
disable-udp-ports, ...), active [Host] maps, [Remote Script], [IP Rewrite],
and the active [Remote Filter]/[Remote Rule] lines. doq-server is the one
deliberate exception: the public baseline keeps it off (5,236/5,239 connections
failed in the 2026-10-29 device log), so it is dropped with a warning.

Security rules:
  * never print a subscription URL, CA blob, or passphrase;
  * refuse to write inside this repository;
  * refuse to overwrite an existing file unless --force is passed.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import ipaddress
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "configs/loon.conf"
HEADER_RE = re.compile(r"(?m)^\[([^\]]+)\]\s*$")
BUILTIN_POLICIES = {
    "DIRECT", "REJECT", "REJECT-IMG", "REJECT-DICT", "REJECT-ARRAY",
    "REJECT-DROP", "PROXY",
}
SECTION_ALIASES = {
    "general": "General",
    "host": "Host",
    "proxy": "Proxy",
    "remote proxy": "Remote Proxy",
    "proxy group": "Proxy Group",
    "rule": "Rule",
    "rewrite": "Rewrite",
    "script": "Script",
    "remote script": "Remote Script",
    "remote filter": "Remote Filter",
    "remote rule": "Remote Rule",
    "ip rewrite": "IP Rewrite",
    "mitm": "MITM",
    "plugin": "Plugin",
}
# The public baseline deliberately keeps DoQ off; see configs/loon.conf.
GENERAL_DROP = {"doq-server"}
ADVANCED_RULE_TYPES = (
    "AND", "OR", "NOT", "PROTOCOL", "SRC-PORT", "DEST-PORT", "IP-ASN",
    "DOMAIN-WILDCARD", "URL-REGEX", "USER-AGENT", "PROCESS-NAME",
)


def fail(message: str) -> None:
    print(f"ERROR {message}", file=sys.stderr)
    raise SystemExit(1)


def split_sections(text: str) -> tuple[str, dict[str, str]]:
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return text, {}
    preamble = text[: matches[0].start()]
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw_name = match.group(1).strip()
        name = SECTION_ALIASES.get(raw_name.lower())
        if name is None:
            continue
        if name in sections:
            fail(f"duplicate section [{name}]")
        sections[name] = text[match.end():end].strip("\n")
    return preamble, sections


def active_lines(content: str) -> list[str]:
    return [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def key_of(line: str) -> str:
    return line.split("=", 1)[0].strip().lower() if "=" in line else ""


def is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def host_entries(line: Optional[str]) -> list[str]:
    if not line or "=" not in line:
        return []
    return [x.strip() for x in re.split(r"[,\s]+", line.split("=", 1)[1]) if x.strip()]


def host_glob(entry: str):
    body = entry.lstrip("-")
    parts = []
    for ch in body:
        if ch == "*":
            parts.append(".*")
        elif ch == "?":
            parts.append(".")
        else:
            parts.append(re.escape(ch))
    return re.compile("^" + "".join(parts) + "$", re.IGNORECASE)


# The public config deliberately replaced the blanket Apple exclusion with
# push/apns-only exclusions so iRingo can decrypt Apple services.
LCF_HOSTNAME_OVERRIDES = {"-*.apple.com"}


def merge_hostname(public_line: str, lcf_line: Optional[str]) -> tuple[str, int, int]:
    """Keep .lcf hostnames, minus policy overrides and public-excluded positives."""
    public = host_entries(public_line)
    negatives = [host_glob(e) for e in public if e.startswith("-")]
    positives = [host_glob(e) for e in public if not e.startswith("-")]
    kept: list[str] = []
    dropped = 0
    for entry in host_entries(lcf_line):
        if entry.lower() in LCF_HOSTNAME_OVERRIDES:
            dropped += 1
            continue
        host = entry.lstrip("-")
        if entry.startswith("-"):
            if any(rx.match(host) for rx in positives):
                dropped += 1
                continue
        elif any(rx.match(host) for rx in negatives):
            dropped += 1
            continue
        if entry not in kept:
            kept.append(entry)
    for entry in public:
        if entry not in kept:
            kept.append(entry)
    return ",".join(kept), len(kept), dropped


def merge_general(public_text: str, lcf_text: str) -> tuple[str, dict]:
    """Public keys win; keep .lcf-only advanced keys; drop doq-server on policy."""
    public_map = {key_of(line): line for line in active_lines(public_text) if key_of(line)}
    extras: list[str] = []
    extra_keys: set[str] = set()
    overridden: list[str] = []
    dropped: list[str] = []
    for line in active_lines(lcf_text):
        key = key_of(line)
        if not key:
            continue
        if key in GENERAL_DROP:
            dropped.append(key)
            continue
        if key in public_map:
            if line != public_map[key]:
                overridden.append(key)
            continue
        if key in extra_keys:
            continue
        extra_keys.add(key)
        extras.append(line)
    content = public_text.strip("\n")
    if extras:
        content += (
            "\n\n# 以下 [General] 键来自 .lcf（公开基线未定义），保留以维持本机高级功能\n"
            + "\n".join(extras)
        )
    return content, {
        "extras": [key_of(line) for line in extras],
        "overridden": overridden,
        "dropped": dropped,
    }


def merge_hosts(public_text: str, lcf_text: str) -> tuple[str, dict]:
    content = public_text.strip("\n")
    seen = {
        line.split("=", 1)[0].strip().lower()
        for line in active_lines(public_text)
        if "=" in line
    }
    extras: list[str] = []
    conflicts: list[str] = []
    for line in active_lines(lcf_text):
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip().lower()
        if key in seen:
            conflicts.append(key)
            continue
        seen.add(key)
        extras.append(line)
    if extras:
        content += (
            "\n\n# 以下 [Host] 映射来自 .lcf；本地 Host 优先于插件，"
            "广告拦截异常时先查这里\n" + "\n".join(extras)
        )
    return content, {"injected": len(extras), "conflicts": conflicts}


def merge_plugins(public_text: str, lcf_text: str, keep_lcf_plugins: bool) -> tuple[str, dict]:
    content = public_text.strip("\n")
    urls = {line.split(",", 1)[0].strip() for line in active_lines(public_text)}
    extras: list[str] = []
    skipped = 0
    for line in active_lines(lcf_text):
        url = line.split(",", 1)[0].strip()
        if not url or url in urls:
            continue
        if keep_lcf_plugins:
            urls.add(url)
            extras.append(line)
        else:
            skipped += 1
    if extras:
        content += "\n\n# 以下插件行来自 .lcf（--keep-lcf-plugins）\n" + "\n".join(extras)
    return content, {"kept": len(extras), "skipped": skipped}


def policy_of(rule: str) -> str:
    parts = [part.strip() for part in rule.split(",")]
    if not parts:
        return ""
    if parts[0].upper() == "FINAL":
        return parts[1] if len(parts) > 1 else ""
    if parts[-1] == "no-resolve":
        return parts[-2] if len(parts) > 1 else ""
    return parts[-1]


def validate_private(
    rules: list[str],
    groups: list[str],
    remote_proxy: list[str],
    plugins: list[str],
    ca_lines: list[str],
) -> dict[str, int]:
    group_names = {line.split("=", 1)[0].strip() for line in groups if "=" in line}
    if not group_names:
        fail("[Proxy Group] 没有有效策略组")
    if not remote_proxy:
        fail("[Remote Proxy] 没有有效订阅行（无法保留节点）")
    if not rules:
        fail("[Rule] 为空")
    if rules[-1].split(",", 1)[0].strip().upper() != "FINAL":
        fail("FINAL 必须是最后一条规则")
    if sum(1 for rule in rules if rule.split(",", 1)[0].strip().upper() == "FINAL") != 1:
        fail("FINAL 必须恰好一条")
    for rule in rules:
        policy = policy_of(rule)
        if rule.split(",", 1)[0].strip().upper() == "FINAL":
            if policy not in group_names and policy not in BUILTIN_POLICIES:
                fail(f"FINAL 指向未声明的策略 {policy!r}")
            continue
        if policy not in group_names and policy not in BUILTIN_POLICIES:
            fail(f"规则指向未声明的策略 {policy!r}")
    if not plugins:
        fail("[Plugin] 为空")
    if not ca_lines:
        print("WARN no ca-p12/ca-passphrase in the .lcf; MITM plugins need a certificate", file=sys.stderr)
    return {
        "groups": len(group_names),
        "rules": len(rules),
        "plugins": len(plugins),
        "ca": len(ca_lines),
    }


def group_type_counts(lines: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in lines:
        if "=" not in line:
            continue
        gtype = line.split("=", 1)[1].split(",", 1)[0].strip().lower()
        if gtype:
            counts[gtype] = counts.get(gtype, 0) + 1
    return counts


def advanced_rule_counts(lines: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in lines:
        kind = line.split(",", 1)[0].strip().upper()
        if kind in ADVANCED_RULE_TYPES:
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def host_kind_counts(lines: list[str]) -> dict[str, int]:
    counts = {
        "fixed-ip": 0, "alias": 0, "server": 0,
        "ip-mode": 0, "ssid": 0, "ip-to-ip": 0, "use-in-proxy": 0,
    }
    for line in lines:
        if "=" not in line:
            continue
        left, right = [part.strip() for part in line.split("=", 1)]
        if left.startswith("ssid:"):
            counts["ssid"] += 1
        if "use-in-proxy=" in right:
            counts["use-in-proxy"] += 1
        targets = [
            part.strip() for part in right.split(",")
            if part.strip() and not part.strip().startswith("use-in-proxy=")
        ]
        for target in targets:
            if target.startswith("server:"):
                counts["server"] += 1
            elif target.startswith("ip-mode:"):
                counts["ip-mode"] += 1
            elif is_ip(left) and is_ip(target):
                counts["ip-to-ip"] += 1
            elif is_ip(target):
                counts["fixed-ip"] += 1
            else:
                counts["alias"] += 1
    return counts


def build(public: dict[str, str], lcf: dict[str, str], keep_lcf_plugins: bool = False) -> tuple[str, dict]:
    public_rule = active_lines(public.get("Rule", ""))
    public_plugin = active_lines(public.get("Plugin", ""))
    lcf_proxy = active_lines(lcf.get("Proxy", ""))
    lcf_remote = active_lines(lcf.get("Remote Proxy", ""))
    lcf_groups = active_lines(lcf.get("Proxy Group", ""))
    lcf_mitm = active_lines(lcf.get("MITM", ""))
    lcf_rule = active_lines(lcf.get("Rule", ""))
    ca_lines = [line for line in lcf_mitm if key_of(line) in ("ca-p12", "ca-passphrase")]
    dropped_mitm = sorted(
        {key_of(line) for line in lcf_mitm if key_of(line) not in ("hostname", "ca-p12", "ca-passphrase")}
    )
    if dropped_mitm:
        print(
            "WARN .lcf [MITM] 含公开策略不接受的键，已丢弃：" + ", ".join(dropped_mitm),
            file=sys.stderr,
        )

    general_text, general_stats = merge_general(public.get("General", ""), lcf.get("General", ""))
    if general_stats["dropped"]:
        print(
            "WARN .lcf [General] 含 doq-server，按公开基线丢弃"
            "（2026-10-29 日志 5,236/5,239 次建立失败）",
            file=sys.stderr,
        )
    if general_stats["extras"]:
        print(
            "INFO .lcf [General] 保留公开基线未定义的键：" + ", ".join(general_stats["extras"]),
            file=sys.stderr,
        )
    if general_stats["overridden"]:
        print(
            "WARN .lcf [General] 以下键与公开基线不同，采用公开值："
            + ", ".join(sorted(set(general_stats["overridden"]))),
            file=sys.stderr,
        )

    host_text, host_stats = merge_hosts(public.get("Host", ""), lcf.get("Host", ""))
    if host_stats["injected"]:
        print(
            f"WARN .lcf [Host] 注入 {host_stats['injected']} 条映射；"
            "本地 Host 优先于插件，广告拦截异常时先查这里",
            file=sys.stderr,
        )
    if host_stats["conflicts"]:
        print(
            "WARN .lcf [Host] 以下键与公开基线冲突，采用公开值："
            + ", ".join(sorted(set(host_stats["conflicts"]))),
            file=sys.stderr,
        )

    plugin_text, plugin_stats = merge_plugins(
        public.get("Plugin", ""), lcf.get("Plugin", ""), keep_lcf_plugins
    )
    if plugin_stats["skipped"]:
        print(
            f"WARN .lcf 有 {plugin_stats['skipped']} 条插件行不在公开清单内，未注入；"
            "需要时加 --keep-lcf-plugins（可能含失效或未审计插件）",
            file=sys.stderr,
        )
    lcf_only_rules = len(set(lcf_rule) - set(public_rule))
    if lcf_only_rules:
        print(
            f"WARN .lcf 有 {lcf_only_rules} 条规则不在公开规则集内，未注入（公开规则集为准）",
            file=sys.stderr,
        )

    public_mitm = active_lines(public.get("MITM", ""))
    hostname = next((line for line in public_mitm if key_of(line) == "hostname"), None)
    if hostname is None:
        fail("configs/loon.conf has no [MITM] hostname")
    lcf_host = next((line for line in lcf_mitm if key_of(line) == "hostname"), None)
    merged_host, host_count, host_dropped = merge_hostname(hostname, lcf_host)

    stats = validate_private(public_rule, lcf_groups, lcf_remote, public_plugin, ca_lines)
    remote_script = active_lines(lcf.get("Remote Script", ""))
    ip_rewrite = active_lines(lcf.get("IP Rewrite", ""))
    remote_filter = active_lines(lcf.get("Remote Filter", ""))
    remote_rule = active_lines(lcf.get("Remote Rule", ""))
    if remote_script:
        print(
            f"WARN 保留 {len(remote_script)} 条 [Remote Script]；远程脚本不经本仓审计",
            file=sys.stderr,
        )
    if ip_rewrite:
        print(
            f"WARN 保留 {len(ip_rewrite)} 条 [IP Rewrite]；仅 Build 1007+ 生效",
            file=sys.stderr,
        )

    summary = dict(stats)
    summary.update({
        "rule_total": len(public_rule),
        "advanced_rules": advanced_rule_counts(public_rule),
        "general": general_stats,
        "host": host_stats,
        "host_total": len(active_lines(host_text)),
        "host_kinds": host_kind_counts(active_lines(host_text)),
        "plugins": {
            "total": len(active_lines(plugin_text)),
            "kept": plugin_stats["kept"],
            "skipped": plugin_stats["skipped"],
        },
        "group_types": group_type_counts(lcf_groups),
        "lcf_only_rules": lcf_only_rules,
        "remote_script": len(remote_script),
        "ip_rewrite": len(ip_rewrite),
        "remote_filter": len(remote_filter),
        "remote_rule": len(remote_rule),
        "mitm_hosts": host_count,
        "host_dropped": host_dropped,
    })

    group_desc = ",".join(f"{name} {count}" for name, count in sorted(summary["group_types"].items())) or "无"
    parts: list[str] = []
    parts.append(
        "# ============================================================================\n"
        "# Loon 私有全功能配置（本机生成）\n"
        "# ----------------------------------------------------------------------------\n"
        "# 来源：configs/loon.conf + 本地 Loon 导出的 .lcf。\n"
        "# 本文件含你的订阅链接与 CA 私钥/口令：不要提交、不要上传、不要分享。\n"
        f"# 生成日期：{date.today().isoformat()}；文件权限：0600。\n"
        f"# 插件 {summary['plugins']['total']} 个；规则 {summary['rule_total']} 条；"
        f"策略组 {summary['groups']} 个（{group_desc}）。\n"
        f"# Host 映射 {summary['host_total']} 条；远程脚本 {summary['remote_script']} 条；"
        f"IP Rewrite {summary['ip_rewrite']} 条。\n"
        f"# .lcf 中未注入的规则 {summary['lcf_only_rules']} 条、插件 "
        f"{summary['plugins']['skipped']} 个（公开清单为准）。\n"
        "# 导入：Loon → 配置 → 导入；或把文件放到「文件」App 后用 Loon 打开。\n"
        "# ============================================================================\n"
    )
    parts.append("[General]\n" + general_text.strip("\n"))
    parts.append("[Host]\n" + host_text.strip("\n"))
    parts.append(
        "[Proxy]\n# 由 .lcf 注入；节点不会出现在公开配置中。\n"
        + "\n".join(lcf_proxy)
    )
    parts.append(
        "[Remote Proxy]\n# 由 .lcf 注入；订阅链接只存在于本机文件。\n"
        + "\n".join(lcf_remote)
    )
    parts.append(
        "[Proxy Group]\n# 由 .lcf 注入；组顺序与当前使用中的配置一致。\n"
        + "\n".join(lcf_groups)
    )
    parts.append("[Rule]\n" + public.get("Rule", "").strip("\n"))

    rewrite = public.get("Rewrite", "").strip("\n")
    script = public.get("Script", "").strip("\n")
    for name, content in (("Rewrite", rewrite), ("Script", script)):
        extra = active_lines(lcf.get(name, ""))
        block = f"[{name}]\n{content}"
        if extra:
            block += "\n\n# 以下来自 .lcf\n" + "\n".join(extra)
        parts.append(block)

    if remote_script:
        parts.append(
            "[Remote Script]\n# 来自 .lcf；远程脚本不经本仓审计，供应链风险自负。\n"
            + "\n".join(remote_script)
        )

    for name, extra in (("Remote Filter", remote_filter), ("Remote Rule", remote_rule)):
        if extra:
            parts.append(f"[{name}]\n" + "\n".join(extra))

    if ip_rewrite:
        parts.append(
            "[IP Rewrite]\n# 来自 .lcf；仅 Build 1007+ 生效。\n"
            + "\n".join(ip_rewrite)
        )

    mitm = [
        "[MITM]",
        "# 私有配置：CA 来自 .lcf；不要分享此段。",
        *ca_lines,
        "# hostname 合并 .lcf 原有主机与公开排除表：保留银行/支付/微信/QQ 钱包等",
        "# 证书固定域的排除，去掉整段 -*.apple.com 以便 iRingo 工作，仅排除 push/apns。",
        f"# hostname 条目 {host_count} 个（.lcf 中被公开排除表拦下 {host_dropped} 个）",
        f"hostname = {merged_host}",
    ]
    parts.append("\n".join(mitm))
    parts.append("[Plugin]\n" + plugin_text.strip("\n"))
    return "\n\n".join(part.rstrip() for part in parts) + "\n", summary


def print_report(summary: dict) -> None:
    groups = summary["group_types"]
    group_desc = ",".join(f"{name}={count}" for name, count in sorted(groups.items())) or "none"
    rules = summary["advanced_rules"]
    rule_desc = ",".join(f"{name}={count}" for name, count in sorted(rules.items())) or "none"
    kinds = summary["host_kinds"]
    kind_desc = ",".join(f"{name}={count}" for name, count in kinds.items() if count) or "none"
    print(
        f"advanced: groups={sum(groups.values())} ({group_desc}) "
        f"rules={summary['rule_total']} advanced_rules={rule_desc}"
    )
    print(
        f"advanced: host_maps={summary['host_total']} ({kind_desc}) "
        f"remote_script={summary['remote_script']} ip_rewrite={summary['ip_rewrite']} "
        f"remote_filter={summary['remote_filter']} remote_rule={summary['remote_rule']}"
    )
    print(
        f"advanced: general_from_lcf={len(summary['general']['extras'])} "
        f"public_overrides={len(set(summary['general']['overridden']))} "
        f"forbidden_dropped={len(summary['general']['dropped'])} "
        f"lcf_rules_not_injected={summary['lcf_only_rules']} "
        f"lcf_plugins_not_injected={summary['plugins']['skipped']}"
    )


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"self-test FAILED: {message}")


def self_test() -> int:
    public = {
        "General": "ip-mode = v4-only\nreal-ip = *.icloud.com\n",
        "Host": "example.com = 192.0.2.1\n",
        "Rule": "DOMAIN,a.example,DIRECT\nFINAL,DIRECT\n",
        "Plugin": "https://example.com/a.plugin,enabled=true\n",
        "MITM": "hostname = -*.push.apple.com,example.com\n",
    }
    lcf = {
        "General": (
            "ip-mode = dual\n"
            "ssid-trigger = \"home\":DIRECT\n"
            "allow-wifi-access = true\n"
            "dns-server = 8.8.8.8\n"
            "doq-server = quic://1.1.1.1:853\n"
        ),
        "Host": "cdn.example.com = 203.0.113.10\nexample.com = 203.0.113.11\n",
        "Proxy": "N1 = Shadowsocks,node.example.com,443,aes-128-gcm,\"pass\"\n",
        "Remote Proxy": "Sub = https://sub.example/secret-token,enabled=true\n",
        "Proxy Group": "Proxy = select,DIRECT\nAuto = url-test,DIRECT\n",
        "Rule": "DOMAIN,a.example,DIRECT\nDOMAIN,custom.example,DIRECT\nFINAL,DIRECT\n",
        "MITM": (
            "hostname = -*.apple.com,private.example.com\n"
            "ca-p12 = SECRETCA\nca-passphrase = SECRETPASS\n"
        ),
        "Remote Script": "https://example.com/remote.js, tag=remote\n",
        "IP Rewrite": "203.0.113.9 drop\n",
        "Plugin": "https://private.example/extra.plugin,enabled=true\n",
    }
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        body, summary = build(public, lcf)
        body_keep, _ = build(public, lcf, keep_lcf_plugins=True)
    output = captured.getvalue()

    _expect("ssid-trigger" in body, "extra General key not preserved")
    _expect("allow-wifi-access = true" in body, "advanced General key not preserved")
    _expect("doq-server" not in body, "doq-server must be dropped")
    _expect("ip-mode = v4-only" in body, "public General value must win")
    _expect("ip-mode = dual" not in body, "lcf General value must not override public")
    _expect("cdn.example.com = 203.0.113.10" in body, "lcf Host map not injected")
    _expect("example.com = 192.0.2.1" in body, "public Host map missing")
    _expect("example.com = 203.0.113.11" not in body, "conflicting Host map must be dropped")
    _expect("[Remote Script]" in body and "remote.js" in body, "Remote Script not preserved")
    _expect("[IP Rewrite]" in body, "IP Rewrite not preserved")
    hostname_line = next(line for line in body.splitlines() if line.startswith("hostname = "))
    hostname_entries = hostname_line.split("=", 1)[1].split(",")
    _expect("-*.apple.com" not in hostname_entries, "apple blanket exclusion must be dropped")
    _expect("-*.push.apple.com" in hostname_entries, "push exclusion must survive")
    _expect("SECRETCA" in body and "SECRETPASS" in body, "CA must be written to private file")
    _expect("https://private.example/extra.plugin" not in body, "lcf plugin must be opt-in")
    _expect("https://private.example/extra.plugin" in body_keep, "keep flag must preserve lcf plugin")
    _expect(summary["lcf_only_rules"] == 1, "lcf-only rule count")
    _expect(summary["plugins"]["skipped"] == 1, "lcf plugin skip count")
    _expect(summary["group_types"].get("url-test") == 1, "group type count")
    _expect(summary["advanced_rules"].get("PROTOCOL") is None, "no phantom advanced rules")
    for secret in ("SECRETCA", "SECRETPASS", "secret-token"):
        _expect(secret not in output, f"secret leaked to output: {secret}")

    print(
        "private config self-test ok: general/host/remote-script/ip-rewrite preserved, "
        "doq-server dropped, secrets not printed"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lcf", type=Path, help="Loon 导出的 .lcf 备份")
    parser.add_argument("--out", type=Path, help="输出路径（默认 ~/Downloads）")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的输出文件")
    parser.add_argument("--dry-run", action="store_true", help="只构建并打印高级功能摘要，不写文件")
    parser.add_argument("--keep-lcf-plugins", action="store_true",
                        help="保留 .lcf 中不在公开清单里的插件行（可能含失效/未审计插件）")
    parser.add_argument("--self-test", action="store_true", help="用内存样本自检合并逻辑，不读写文件")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.lcf is None:
        parser.error("--lcf is required unless --self-test")
    if not PUBLIC.exists():
        fail(f"missing {PUBLIC.relative_to(ROOT)}")
    if not args.lcf.is_file():
        fail(f".lcf not found: {args.lcf}")
    out = args.out or (Path.home() / "Downloads" / f"Loon-AllInOne-Private-{date.today().isoformat()}.conf")
    out = out.expanduser()
    if not args.dry_run:
        try:
            out.resolve().relative_to(ROOT.resolve())
        except ValueError:
            pass
        else:
            fail("拒绝把私有配置写入仓库目录；请用 --out 指定仓库外的路径")
        if out.exists() and not args.force:
            fail(f"输出已存在（加 --force 覆盖）: {out}")
        out.parent.mkdir(parents=True, exist_ok=True)

    public_text = PUBLIC.read_text(encoding="utf-8")
    lcf_text = args.lcf.read_text(encoding="utf-8")
    _, public_sections = split_sections(public_text)
    _, lcf_sections = split_sections(lcf_text)
    if "General" not in public_sections or "Rule" not in public_sections:
        fail("configs/loon.conf 缺少 [General]/[Rule]")

    body, summary = build(public_sections, lcf_sections, args.keep_lcf_plugins)
    if args.dry_run:
        print(f"dry-run: would write {out} (no file written)")
        print(
            f"plugins={summary['plugins']['total']} "
            f"rules={summary['rule_total']} "
            f"groups={summary['groups']} "
            f"remote_proxy=1 ca_keys={summary['ca']} "
            f"mitm_hosts={summary['mitm_hosts']}"
        )
        print_report(summary)
        print("subscription URL and CA values were not printed; keep this file off GitHub.")
        return 0

    fd, tmp_name = tempfile.mkstemp(prefix=".loon-private-", suffix=".conf", dir=str(out.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, out)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)

    print(f"private config written: {out}")
    print(
        f"plugins={summary['plugins']['total']} "
        f"rules={summary['rule_total']} "
        f"groups={summary['groups']} "
        f"remote_proxy=1 ca_keys={summary['ca']} "
        f"mitm_hosts={summary['mitm_hosts']}"
    )
    print_report(summary)
    print("subscription URL and CA values were not printed; keep this file off GitHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
