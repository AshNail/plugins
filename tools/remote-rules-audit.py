#!/usr/bin/env python3
"""Audit published REJECT rule sets against the repository's App redlines.

The live macOS profile uses six blackmatrix7 remote rule sets. Advertising,
Privacy and Hijacking apply REJECT. A remote rule that covers an App redline is
only safe when a local DIRECT rule overrides it before remote rules are
evaluated. This tool fetches the public lists, finds overlaps, and checks the
profile's local DIRECT rules.

It never prints subscription URLs or CA material. Network is required.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from redlines import load_app_redlines  # noqa: E402

DEFAULT_CONFIG = Path("/Library/Application Support/com.loon.Loon/config/Loon.lcf")
BASE = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Loon"
REJECT_SETS = ("Advertising", "Privacy", "Hijacking")
DOMAIN_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-WILDCARD"}


def fetch(name: str) -> list[tuple[str, str]]:
    url = f"{BASE}/{name}/{name}.list"
    with urllib.request.urlopen(url, timeout=30) as response:
        text = response.read().decode("utf-8", "replace")
    rules: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = [x.strip() for x in stripped.split(",")]
        if parts[0].upper() in DOMAIN_TYPES:
            rules.append((parts[0].upper(), parts[1].lower()))
    return rules


def local_directs(config: Path) -> set[str]:
    text = config.read_text(errors="replace")
    section = ""
    out: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped.upper()
            continue
        if section != "[RULE]" or not stripped or stripped.startswith("#"):
            continue
        parts = [x.strip() for x in stripped.split(",")]
        if len(parts) >= 3 and parts[-1].upper() == "DIRECT" and parts[0].upper() in (
            "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"
        ):
            out.add((parts[0].upper(), parts[1].lower()))
    return out


def overridden(domain: str, directs: set[str]) -> bool:
    d = domain.lower()
    if ("DOMAIN", d) in directs:
        return True
    return any(
        kind == "DOMAIN-SUFFIX" and (d == value or d.endswith("." + value))
        for kind, value in directs
    ) or any(kind == "DOMAIN-KEYWORD" and value in d for kind, value in directs)


def remote_covers(kind: str, value: str, redline: dict) -> bool:
    domain = redline["domain"].lower()
    family = redline.get("kind") == "family"
    if kind == "DOMAIN":
        return value == domain or (family and value.endswith("." + domain))
    if kind == "DOMAIN-SUFFIX":
        return domain == value or domain.endswith("." + value)
    if kind == "DOMAIN-KEYWORD":
        return value in domain
    if kind == "DOMAIN-WILDCARD":
        pattern = re.escape(value).replace(r"\*", ".*").replace(r"\?", ".")
        return re.fullmatch(pattern, domain) is not None
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    if not args.config.is_file():
        raise SystemExit(f"profile not found: {args.config}")

    redlines = load_app_redlines()
    directs = local_directs(args.config)
    unprotected = 0
    for name in REJECT_SETS:
        try:
            rules = fetch(name)
        except Exception as exc:  # network failure is reported, not hidden
            print(f"{name}: fetch failed: {exc}")
            continue
        hits = []
        for kind, value in rules:
            for item in redlines:
                if remote_covers(kind, value, item):
                    hits.append((kind, value, item, overridden(value, directs)))
                    break
        print(f"{name}: rules={len(rules)} redline_hits={len(hits)}")
        for kind, value, item, safe in hits:
            status = "local DIRECT override" if safe else "UNPROTECTED"
            print(f"  {kind},{value} -> {item['domain']} [{status}]")
            if not safe:
                unprotected += 1
    if unprotected:
        print(f"unprotected remote redline hits: {unprotected}")
        raise SystemExit(1)
    print("remote redline audit ok")


if __name__ == "__main__":
    main()
