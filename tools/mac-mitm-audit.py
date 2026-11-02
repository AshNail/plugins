#!/usr/bin/env python3
"""Read-only audit of a macOS Loon profile's main [MITM] host list.

Loon merges the profile [MITM] hostname list with enabled plugins' [MITM]
declarations. Main-list entries that no plugin declares and no Rewrite/Script/
Rule consumes are candidates for removal (smaller TLS decryption surface).

This tool only reads the profile and plugin caches. It never edits either one
and never prints CA material, plugin URLs, subscriptions, or proxy credentials.
Candidate judgement is heuristic: confirm app behavior before deleting a host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

DEFAULT_CONFIG = Path("/Library/Application Support/com.loon.Loon/config/Loon.lcf")
DEFAULT_CACHE = Path("/Library/Application Support/com.loon.Loon/remotePlugin")


def sections(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped.upper()
            out.setdefault(current, [])
            continue
        if current:
            out[current].append(line)
    return out


def main_hostname(text: str) -> list[str]:
    for line in text.splitlines():
        if line.startswith("hostname = "):
            items = [x.strip() for x in line[len("hostname = "):].split(",") if x.strip()]
            return [x for x in items if not x.startswith("-")]
    return []


def mitm_hosts(text: str) -> set[str]:
    hosts: set[str] = set()
    in_mitm = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_mitm = stripped.upper() == "[MITM]"
            continue
        if in_mitm and stripped.lower().startswith("hostname"):
            value = stripped.split("=", 1)[1] if "=" in stripped else ""
            for item in value.replace("%APPEND%", "").split(","):
                item = item.strip().lower()
                if item and not item.startswith("-"):
                    hosts.add(item)
    return hosts


def enabled_plugins(text: str) -> list[str]:
    urls: list[str] = []
    in_plugin = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_plugin = stripped.upper() == "[PLUGIN]"
            continue
        if not in_plugin or not stripped or stripped.startswith("#"):
            continue
        if "enabled=true" in stripped.replace(" ", ""):
            urls.append(stripped.split(",", 1)[0].strip())
    return urls


def plugin_name(text: str, fallback: str) -> str:
    match = re.search(r"^#!name\s*=\s*(.*)$", text, re.M)
    return match.group(1).strip()[:32] if match else fallback[:8]


def covered(host: str, plugin_hosts: set[str]) -> bool:
    host = host.lower()
    if host in plugin_hosts:
        return True
    return any(
        p.startswith("*.") and (host == p[2:] or host.endswith(p[1:]))
        for p in plugin_hosts
    )


def base_host(host: str) -> str:
    return host[2:] if host.startswith("*.") else host


def normalized(text: str) -> str:
    return text.replace("\\.", ".").lower()


def main_consumes(base: str, text: str) -> bool:
    # Optional prefixes such as `(?:beta-)?api.m.jd.com` do not contain the
    # literal `beta-api` token, so also test the label-stripped variant.
    variants = {base}
    first, dot, rest = base.partition(".")
    if dot and "-" in first:
        variants.add(first.split("-", 1)[1] + "." + rest)
    return any(v in text for v in variants)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    if not args.config.is_file():
        raise SystemExit(f"profile not found: {args.config}")
    if not args.cache.is_dir():
        raise SystemExit(f"plugin cache not found: {args.cache}")

    text = args.config.read_text(errors="replace")
    parts = sections(text)
    main_hosts = main_hostname(text)
    main_consumer_text = normalized(
        "\n".join(
            "\n".join(lines)
            for name, lines in parts.items()
            if name not in ("[MITM]", "[PLUGIN]")
        )
    )

    plugin_hosts: set[str] = set()
    plugin_texts: list[tuple[str, str]] = []
    missing = 0
    for url in enabled_plugins(text):
        path = args.cache / f"{hashlib.md5(url.encode()).hexdigest()}.lpx"
        if not path.is_file():
            missing += 1
            continue
        raw = path.read_text(errors="replace")
        plugin_hosts |= mitm_hosts(raw)
        plugin_texts.append((plugin_name(raw, path.name), normalized(raw)))

    rows = []
    for host in main_hosts:
        if covered(host, plugin_hosts):
            continue
        base = base_host(host)
        consumers = [name for name, body in plugin_texts if base in body]
        in_main = main_consumes(base, main_consumer_text)
        rows.append(
            {
                "host": host,
                "consumers": consumers,
                "main_rewrite_or_rule": in_main,
                "candidate": not consumers and not in_main,
            }
        )

    if args.json:
        print(
            json.dumps(
                {
                    "plugins": len(enabled_plugins(text)),
                    "missing_caches": missing,
                    "main_positive_hosts": len(main_hosts),
                    "plugin_positive_hosts": len(plugin_hosts),
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(
        f"plugins={len(enabled_plugins(text))} missing_caches={missing} "
        f"main_positive={len(main_hosts)} plugin_positive={len(plugin_hosts)}"
    )
    print(f"main-only={len(rows)}")
    for row in rows:
        evidence = []
        if row["consumers"]:
            evidence.append("plugins=" + ",".join(row["consumers"]))
        if row["main_rewrite_or_rule"]:
            evidence.append("main")
        suffix = " CANDIDATE" if row["candidate"] else ""
        print(f"  {row['host']:36} {'; '.join(evidence) or '-'}{suffix}")
    print("candidates are heuristic; verify TLS issuer after removing (see docs/device-checklist.md K).")


if __name__ == "__main__":
    main()
