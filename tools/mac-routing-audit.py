#!/usr/bin/env python3
"""Read-only routing audit for a Loon profile.

Checks the local [Rule] section for structural mistakes that make rules dead:
FINAL position, duplicates, port/protocol rules after IP rules, domain rules
shadowed by an earlier broader rule, and undefined policy groups. Remote Rule
entries are summarized by policy only; their URLs are never printed.

This tool does not edit the profile. Use it after plugin/config changes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DEFAULT_CONFIG = Path("/Library/Application Support/com.loon.Loon/config/Loon.lcf")
IP_TYPES = {"IP-CIDR", "IP-CIDR6", "IP-ASN", "GEOIP"}
PORT_TYPES = {"DEST-PORT", "SRC-PORT", "PROTOCOL"}
BUILTIN_POLICIES = {
    "DIRECT", "DROP", "REJECT", "REJECT-DICT", "REJECT-IMG", "REJECT-ARRAY",
    "REJECT-DROP", "REJECT-NO-DROP", "REJECT-TINYGIF", "REJECT-200",
}


def parse(path: Path):
    text = path.read_text(errors="replace")
    groups: set[str] = set()
    rules: list[tuple[int, str]] = []
    remote: list[tuple[int, str, str]] = []
    section = ""
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped.upper()
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if section == "[PROXY GROUP]" and "=" in stripped:
            groups.add(stripped.split("=", 1)[0].strip())
        elif section == "[RULE]":
            rules.append((number, stripped))
        elif section == "[REMOTE RULE]":
            policy = re.search(r"(?:^|,)\s*policy\s*=\s*([^,]+)", stripped, re.I)
            tag = re.search(r"(?:^|,)\s*tag\s*=\s*([^,]+)", stripped, re.I)
            remote.append((number, policy.group(1).strip() if policy else "?", tag.group(1).strip() if tag else ""))
    return groups, rules, remote


def domain_key(rule: str) -> tuple[str, str, str] | None:
    parts = [x.strip() for x in rule.split(",")]
    if len(parts) < 3:
        return None
    kind = parts[0].upper()
    if kind not in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD"):
        return None
    return kind, parts[1].lower(), parts[-1]


def audit(path: Path) -> dict:
    groups, rules, remote = parse(path)
    finals = [(n, r) for n, r in rules if r.upper().startswith("FINAL")]
    after_final = [(n, r) for n, r in rules if finals and n > finals[-1][0]]
    duplicates: list[tuple[int, int, str]] = []
    seen: dict[str, int] = {}
    for number, rule in rules:
        key = rule.lower().replace(" ", "")
        if key in seen:
            duplicates.append((number, seen[key], rule))
        else:
            seen[key] = number

    first_ip = None
    late_ports: list[tuple[int, str]] = []
    for number, rule in rules:
        kind = rule.split(",", 1)[0].strip().upper()
        if kind in IP_TYPES and first_ip is None:
            first_ip = number
        if kind in PORT_TYPES and first_ip is not None:
            late_ports.append((number, rule))

    domains = [(n, domain_key(r)) for n, r in rules if domain_key(r)]
    shadowed: list[dict] = []
    for index, (number, item) in enumerate(domains):
        kind, value, policy = item
        for earlier_number, earlier in domains[:index]:
            earlier_kind, earlier_value, earlier_policy = earlier
            hit = (
                earlier_kind == "DOMAIN-SUFFIX"
                and kind in ("DOMAIN", "DOMAIN-SUFFIX")
                and (value == earlier_value.lstrip(".") or value.endswith("." + earlier_value.lstrip(".")))
            ) or (earlier_kind == "DOMAIN-KEYWORD" and earlier_value in value)
            if hit and policy != earlier_policy:
                shadowed.append(
                    {"line": number, "rule": item, "earlier_line": earlier_number, "earlier": earlier}
                )
                break

    undefined: set[str] = set()
    for _, rule in rules:
        parts = [x.strip() for x in rule.split(",")]
        if len(parts) >= 3:
            policy = parts[-1]
            if policy == "no-resolve" and len(parts) >= 4:
                policy = parts[-2]
            if policy not in BUILTIN_POLICIES and policy not in groups:
                undefined.add(policy)

    return {
        "rules": len(rules),
        "groups": len(groups),
        "finals": len(finals),
        "final_lines": [n for n, _ in finals],
        "rules_after_final": len(after_final),
        "duplicates": duplicates,
        "first_ip_line": first_ip,
        "late_port_protocol": late_ports,
        "shadowed_domains": shadowed,
        "undefined_policies": sorted(undefined),
        "remote": remote,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true", help="exit 1 when findings exist")
    args = parser.parse_args()
    if not args.config.is_file():
        raise SystemExit(f"profile not found: {args.config}")

    report = audit(args.config)
    findings = (
        report["finals"] != 1
        or report["rules_after_final"] > 0
        or bool(report["duplicates"])
        or bool(report["late_port_protocol"])
        or bool(report["shadowed_domains"])
        or bool(report["undefined_policies"])
    )
    if args.json:
        print(json.dumps({"findings": findings, **report}, ensure_ascii=False, indent=2))
    else:
        print(
            f"rules={report['rules']} groups={report['groups']} finals={report['finals']} "
            f"after_final={report['rules_after_final']} duplicates={len(report['duplicates'])} "
            f"late_port={len(report['late_port_protocol'])} shadowed={len(report['shadowed_domains'])} "
            f"undefined={len(report['undefined_policies'])}"
        )
        print(f"remote_rules={len(report['remote'])} policies=" +
              ",".join(f"{tag or '?'}:{policy}" for _, policy, tag in report["remote"]))
        for number, earlier, rule in report["duplicates"]:
            print(f"  duplicate line {number} == {earlier}: {rule[:100]}")
        for number, rule in report["late_port_protocol"]:
            print(f"  late port/protocol line {number}: {rule[:100]}")
        for row in report["shadowed_domains"]:
            print(f"  shadowed line {row['line']} {row['rule'][:80]} after {row['earlier_line']} {row['earlier'][:80]}")
        if report["undefined_policies"]:
            print("  undefined policies: " + ", ".join(report["undefined_policies"]))
    if args.check and findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
