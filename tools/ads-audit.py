#!/usr/bin/env python3
"""Audit the single ads plugin against public ad/tracker blocklists.

The tool is read-only: it never edits src/ads/domains.json or the plugin.
It reports:
  - per-source coverage of the current active [Host] rules
  - the most common uncovered candidates (for human review)
  - rules that do not appear in any selected upstream list
  - wildcard violations against src/ads/protected-roots.json

It reads only non-comment [Host] lines by default, so the optional
attribution/analytics groups stay out of the audit and are reported separately
instead. Active [Rule] DOMAIN-WILDCARD globs count toward coverage (they are
DNS-stage blocks); commented DOMAIN-WILDCARD lines are treated as optional.

Examples:
  python3 tools/ads-audit.py --top 40
  python3 tools/ads-audit.py --sources anti-ad,hagezi-pro,adguard-dns --top 60
  python3 tools/ads-audit.py --include-disabled --top 60
  python3 tools/ads-audit.py --refresh --json > /tmp/ads-audit.json
  python3 tools/ads-audit.py --offline --sources anti-ad,adaway
"""
from __future__ import annotations

import argparse
import collections
import http.client
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "plugins/ads"
PROTECTED_FILE = ROOT / "src/ads/protected-roots.json"
CACHE_DIR = ROOT / ".cache/ads-audit"

DOMAIN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
ADBLOCK_RE = re.compile(r"^\|\|([a-z0-9.*_-]+)(?:\^|/|$)", re.IGNORECASE)
ADBLOCK_URL_RE = re.compile(r"^\|https?://([^/^$]+)", re.IGNORECASE)

# name -> url, parser, human note. Keep the default list moderate (about 15 MB);
# the large 1Hosts Xtra / Hagezi TIF lists are opt-in.
SOURCES: dict[str, dict] = {
    "anti-ad": {
        "url": "https://anti-ad.net/domains.txt",
        "type": "domains",
        "note": "anti-AD（国内为主）",
    },
    "hagezi-pro": {
        "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/pro.txt",
        "type": "domains",
        "note": "Hagezi Pro",
    },
    "hagezi-tif": {
        "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/tif.txt",
        "type": "domains",
        "note": "Hagezi Threat Intelligence（大，可选）",
    },
    "hagezi-tiktok": {
        "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/native.tiktok.txt",
        "type": "domains",
        "note": "Hagezi TikTok 原生追踪",
    },
    "hagezi-xiaomi": {
        "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/native.xiaomi.txt",
        "type": "domains",
        "note": "Hagezi 小米原生追踪",
    },
    "hagezi-oppo": {
        "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/native.oppo-realme.txt",
        "type": "domains",
        "note": "Hagezi OPPO/realme 原生追踪",
    },
    "hagezi-vivo": {
        "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/native.vivo.txt",
        "type": "domains",
        "note": "Hagezi vivo 原生追踪",
    },
    "hagezi-huawei": {
        "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/native.huawei.txt",
        "type": "domains",
        "note": "Hagezi 华为原生追踪",
    },
    "hagezi-amazon": {
        "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/native.amazon.txt",
        "type": "domains",
        "note": "Hagezi Amazon 原生追踪",
    },
    "adguard-dns": {
        "url": "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt",
        "type": "adblock",
        "note": "AdGuard DNS filter",
    },
    "adguard-cn": {
        "url": "https://filters.adtidy.org/extension/chromium/filters/224.txt",
        "type": "adblock",
        "note": "AdGuard 中文 filter",
    },
    "adguard-mobile": {
        "url": "https://filters.adtidy.org/extension/chromium/filters/11.txt",
        "type": "adblock",
        "note": "AdGuard Mobile Ads filter",
    },
    "easylist": {
        "url": "https://easylist.to/easylist/easylist.txt",
        "type": "adblock",
        "note": "EasyList",
    },
    "easylist-cn": {
        "url": "https://easylist-downloads.adblockplus.org/easylistchina.txt",
        "type": "adblock",
        "note": "EasyList China",
    },
    "easyprivacy": {
        "url": "https://easylist.to/easylist/easyprivacy.txt",
        "type": "adblock",
        "note": "EasyPrivacy",
    },
    "adaway": {
        "url": "https://raw.githubusercontent.com/AdAway/adaway.github.io/master/hosts.txt",
        "type": "hosts",
        "note": "AdAway",
    },
    "stevenblack": {
        "url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "type": "hosts",
        "note": "StevenBlack",
    },
    "peterlowe": {
        "url": "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=hosts&showintro=0&mimetype=plaintext",
        "type": "hosts",
        "note": "Peter Lowe",
    },
    "adwars": {
        "url": "https://raw.githubusercontent.com/jdlingyu/ad-wars/master/hosts",
        "type": "hosts",
        "note": "ad-wars",
    },
    "adrules": {
        "url": "https://raw.githubusercontent.com/Cats-Team/AdRules/main/adblock.txt",
        "type": "adblock",
        "note": "AdRules",
    },
    "awa": {
        "url": "https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/AWAvenue-Ads-Rule.txt",
        "type": "adblock",
        "note": "AWAvenue",
    },
    "1hosts-pro": {
        "url": "https://raw.githubusercontent.com/badmojr/1Hosts/master/Pro/hosts.txt",
        "type": "hosts",
        "note": "1Hosts Pro",
    },
    "1hosts-xtra": {
        "url": "https://raw.githubusercontent.com/badmojr/1Hosts/master/Xtra/hosts.txt",
        "type": "hosts",
        "note": "1Hosts Xtra（大，可选）",
    },
}

DEFAULT_SOURCES = [
    "anti-ad",
    "adaway",
    "peterlowe",
    "adguard-dns",
    "adrules",
    "adwars",
    "awa",
    "easylist-cn",
    "hagezi-pro",
    "stevenblack",
]


def log(message: str) -> None:
    print(message, file=sys.stderr)


def normalize_domain(value: str) -> str | None:
    value = value.strip().lower().rstrip(".")
    if not value or value.startswith("#"):
        return None
    if value.startswith("*."):
        value = value[2:]
    if "@" in value or ":" in value or "/" in value:
        return None
    if not DOMAIN_RE.match(value):
        return None
    return value


def parse_hosts(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and IPV4_RE.match(parts[0]):
            domain = normalize_domain(parts[1])
        elif len(parts) == 1:
            domain = normalize_domain(parts[0])
        else:
            domain = None
        if domain:
            out.add(domain)
    return out


def parse_domains(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        # Some "domains" lists are actually adblock-style; handle both.
        if line.startswith("||"):
            domain = parse_adblock_line(line)
        elif line.startswith("|http"):
            match = ADBLOCK_URL_RE.match(line)
            domain = normalize_domain(match.group(1)) if match else None
        elif line.startswith(("!", "[")):
            domain = None
        else:
            parts = line.split()
            if len(parts) >= 2 and IPV4_RE.match(parts[0]):
                domain = normalize_domain(parts[1])
            else:
                domain = normalize_domain(parts[0])
        if domain:
            out.add(domain)
    return out


def parse_adblock_line(line: str) -> str | None:
    if line.startswith(("!", "#", "[", "@@")):
        return None
    if line.startswith("/") and line.endswith("/"):
        return None
    if line.startswith("||"):
        match = ADBLOCK_RE.match(line)
        if not match:
            return None
        raw = match.group(1)
        if "*" in raw or "_" in raw:
            # A wildcard in the middle cannot be represented as a single
            # [Host] suffix rule; keep the literal base only when clean.
            return None
        return normalize_domain(raw)
    if line.startswith("|http"):
        match = ADBLOCK_URL_RE.match(line)
        if match:
            return normalize_domain(match.group(1))
    return None


def parse_adblock(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.splitlines():
        domain = parse_adblock_line(line.strip())
        if domain:
            out.add(domain)
    return out


def fetch_source(name: str, source: dict, refresh: bool, offline: bool) -> set[str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{name}.txt"
    if cache.exists() and not refresh:
        text = cache.read_text(encoding="utf-8", errors="replace")
        log(f"cache  {name:16} {cache.stat().st_size / 1e6:6.1f} MB")
    else:
        if offline:
            raise RuntimeError(f"{name}: cache missing and --offline is set")
        log(f"fetch  {name:16} {source['url']}")
        request = urllib.request.Request(
            source["url"],
            headers={
                "User-Agent": "loon-plugins-ads-audit/1.0 (+https://github.com/AshNail/plugins)"
            },
        )
        started = time.time()
        last_exc = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    raw = response.read()
                break
            except (urllib.error.URLError, TimeoutError,
                    http.client.IncompleteRead, ConnectionResetError) as exc:
                last_exc = exc
                if attempt < 2:
                    log(f"retry  {name:16} attempt {attempt + 2}/3 after {exc}")
                    time.sleep(1.5)
        else:
            raise RuntimeError(f"{name}: download failed: {last_exc}") from last_exc
        text = raw.decode("utf-8", errors="replace")
        cache.write_text(text, encoding="utf-8")
        log(f"got    {name:16} {len(raw) / 1e6:6.1f} MB in {time.time() - started:.1f}s")

    if source["type"] == "hosts":
        return parse_hosts(text)
    if source["type"] == "domains":
        return parse_domains(text)
    if source["type"] == "adblock":
        return parse_adblock(text)
    raise RuntimeError(f"{name}: unknown parser {source['type']!r}")


def normalize_glob(value: str) -> str | None:
    value = value.strip().lower()
    if not value or value != value.lower():
        return None
    if not re.match(r"^[a-z0-9][a-z0-9-]*(?:\[0-9\]|\.|-)", value):
        return None
    if "*" not in value and "?" not in value and "[0-9]" not in value:
        return None
    if any(char in value.replace("[0-9]", "") for char in "[]!\\ "):
        return None
    for body in re.findall(r"\[([^\]]*)\]", value):
        if body != "0-9":
            return None
    return value


def compile_globs(patterns: set[str]) -> tuple[re.Pattern[str], ...]:
    def translate(pattern: str) -> str:
        parts = []
        index = 0
        while index < len(pattern):
            char = pattern[index]
            if char == "[":
                end = pattern.find("]", index + 1)
                if end == -1 or pattern[index + 1 : end] != "0-9":
                    raise RuntimeError(f"unsupported glob class: {pattern!r}")
                parts.append("[0-9]")
                index = end + 1
                continue
            parts.append(".*" if char == "*" else "." if char == "?" else re.escape(char))
            index += 1
        return "".join(parts) + r"\Z"

    return tuple(re.compile(translate(pattern)) for pattern in sorted(patterns))


def parse_plugin_rules(
    paths: list[pathlib.Path],
) -> tuple[set[str], set[str], set[str], set[str], set[str], set[str]]:
    """Parse active and default-commented [Host] rules plus DOMAIN-WILDCARD.

    Returns (active_exact, active_wildcard, optional_exact, optional_wildcard,
    active_globs, optional_globs). Only comments that look exactly like a host
    rule (`domain = 127.0.0.1`) are treated as optional; prose comments are
    ignored. Commented [Rule] DOMAIN-WILDCARD lines are optional globs.
    """
    exact: set[str] = set()
    wildcard: set[str] = set()
    optional_exact: set[str] = set()
    optional_wildcard: set[str] = set()
    active_globs: set[str] = set()
    optional_globs: set[str] = set()
    for path in paths:
        if not path.exists():
            raise RuntimeError(f"missing plugin: {path}")
        in_host = False
        in_rule = False
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_host = stripped.lower() == "[host]"
                in_rule = stripped.lower() == "[rule]"
                continue
            if in_rule and stripped:
                optional = stripped.startswith("#")
                candidate = stripped[1:].strip() if optional else stripped
                if not candidate.startswith("DOMAIN-WILDCARD,"):
                    continue
                parts = [part.strip() for part in candidate.split(",")]
                pattern = normalize_glob(parts[1]) if len(parts) > 2 else None
                if not pattern:
                    if optional:
                        continue
                    raise RuntimeError(f"{path}: invalid DOMAIN-WILDCARD: {stripped!r}")
                if optional:
                    optional_globs.add(pattern)
                else:
                    active_globs.add(pattern)
                continue
            if not in_host or not stripped:
                continue
            optional = stripped.startswith("#")
            candidate = stripped[1:].strip() if optional else stripped
            if not candidate or "=" not in candidate:
                continue
            left, _, right = candidate.partition("=")
            left = left.strip().lower()
            right = right.strip()
            if right != "127.0.0.1":
                if optional:
                    continue
                raise RuntimeError(f"{path}: unexpected host target: {stripped!r}")
            if left.startswith("*."):
                base = left[2:]
                if not normalize_domain(base):
                    if optional:
                        continue
                    raise RuntimeError(f"{path}: invalid host rule: {stripped!r}")
                if optional:
                    optional_wildcard.add(base)
                else:
                    wildcard.add(base)
            else:
                domain = normalize_domain(left)
                if not domain:
                    if optional:
                        continue
                    raise RuntimeError(f"{path}: invalid host rule: {stripped!r}")
                if optional:
                    optional_exact.add(domain)
                else:
                    exact.add(domain)
    return exact, wildcard, optional_exact, optional_wildcard, active_globs, optional_globs


def load_protected() -> list[str]:
    try:
        data = json.loads(PROTECTED_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {PROTECTED_FILE}: {exc}") from exc
    return sorted(data.get("roots", []), key=len, reverse=True)


def protected_root(domain: str, roots: list[str]) -> str | None:
    for root in roots:
        if domain == root or domain.endswith("." + root):
            return root
    return None


def rule_matches(
    domain: str,
    exact: set[str],
    wildcard: set[str],
    globs: tuple[re.Pattern[str], ...] = (),
) -> bool:
    if domain in exact:
        return True
    labels = domain.split(".")
    for i in range(1, len(labels)):
        if ".".join(labels[i:]) in wildcard:
            return True
    return any(regex.fullmatch(domain) for regex in globs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        default=",".join(DEFAULT_SOURCES),
        help="comma-separated source names (default: %(default)s)",
    )
    parser.add_argument("--list-sources", action="store_true", help="list known sources and exit")
    parser.add_argument("--refresh", action="store_true", help="ignore cache and re-download")
    parser.add_argument("--offline", action="store_true", help="use cache only")
    parser.add_argument("--top", type=int, default=40, help="number of uncovered candidates")
    parser.add_argument(
        "--min-sources",
        type=int,
        default=2,
        help="only show candidates seen in at least this many sources",
    )
    parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="include default-commented [Host] groups in the coverage totals",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    args = parser.parse_args()

    if args.list_sources:
        for name, source in SOURCES.items():
            default = " (default)" if name in DEFAULT_SOURCES else ""
            print(f"{name:18} {source['type']:8} {source['note']}{default}")
        return 0

    selected = [name.strip() for name in args.sources.split(",") if name.strip()]
    unknown = [name for name in selected if name not in SOURCES]
    if unknown:
        log(f"error: unknown sources: {', '.join(unknown)}")
        log("use --list-sources to see available names")
        return 2

    plugin_paths = [PLUGIN_DIR / "ads.plugin"]
    try:
        (
            active_exact,
            active_wildcard,
            optional_exact,
            optional_wildcard,
            active_glob_patterns,
            optional_glob_patterns,
        ) = parse_plugin_rules(plugin_paths)
        roots = load_protected()
    except RuntimeError as exc:
        log(f"error: {exc}")
        return 2

    active_globs = compile_globs(active_glob_patterns)
    optional_globs = compile_globs(optional_glob_patterns)
    combined_exact = active_exact | optional_exact
    combined_wildcard = active_wildcard | optional_wildcard
    combined_globs = compile_globs(active_glob_patterns | optional_glob_patterns)
    if args.include_disabled:
        exact = combined_exact
        wildcard = combined_wildcard
        globs = combined_globs
        glob_patterns = active_glob_patterns | optional_glob_patterns
    else:
        exact = active_exact
        wildcard = active_wildcard
        globs = active_globs
        glob_patterns = active_glob_patterns

    source_domains: dict[str, set[str]] = {}
    failures: list[str] = []
    for name in selected:
        try:
            source_domains[name] = fetch_source(name, SOURCES[name], args.refresh, args.offline)
        except RuntimeError as exc:
            failures.append(str(exc))
            log(f"error: {exc}")
    if not source_domains:
        log("error: no sources available")
        return 2

    # Per-source coverage. Report active rules and the combined view including
    # the default-commented optional groups; the latter does not imply those
    # rules are installed, it just answers "would enabling them help?".
    coverage = {}
    uncovered_counter: collections.Counter[str] = collections.Counter()
    all_domains: set[str] = set()
    for name, domains in source_domains.items():
        active_covered = sum(
            1 for domain in domains if rule_matches(domain, exact, wildcard, globs)
        )
        combined_covered = sum(
            1
            for domain in domains
            if rule_matches(domain, combined_exact, combined_wildcard, combined_globs)
        )
        coverage[name] = {
            "domains": len(domains),
            "covered": active_covered,
            "percent": round(100 * active_covered / len(domains), 2) if domains else 0.0,
            "with_optional_covered": combined_covered,
            "with_optional_percent": round(100 * combined_covered / len(domains), 2)
            if domains
            else 0.0,
        }
        for domain in domains:
            all_domains.add(domain)
            if not rule_matches(domain, exact, wildcard, globs):
                uncovered_counter[domain] += 1

    active_covered_total = sum(
        1
        for domain in all_domains
        if rule_matches(domain, active_exact, active_wildcard, active_globs)
    )
    combined_covered_total = sum(
        1
        for domain in all_domains
        if rule_matches(domain, combined_exact, combined_wildcard, combined_globs)
    )
    selected_covered = combined_covered_total if args.include_disabled else active_covered_total
    overall = {
        "domains": len(all_domains),
        "covered": selected_covered,
        "percent": round(100 * selected_covered / len(all_domains), 2) if all_domains else 0.0,
        "active_covered": active_covered_total,
        "active_percent": round(100 * active_covered_total / len(all_domains), 2)
        if all_domains
        else 0.0,
        "with_optional_covered": combined_covered_total,
        "with_optional_percent": round(100 * combined_covered_total / len(all_domains), 2)
        if all_domains
        else 0.0,
    }

    # Candidates: uncovered, seen in >= min-sources. Annotate shared roots and
    # whether the currently commented optional [Host] groups already cover it.
    candidates = []
    for domain, count in uncovered_counter.most_common():
        if count < args.min_sources:
            break
        shared = protected_root(domain, roots)
        optional_covered = rule_matches(
            domain, optional_exact, optional_wildcard, optional_globs
        )
        candidates.append(
            {
                "domain": domain,
                "sources": count,
                "shared_root": shared,
                "optional_covered": optional_covered,
                "suggestion": (
                    f"exact only (protected root {shared})" if shared else "= domain (apex + wildcard)"
                ),
            }
        )
    candidates = candidates[: max(args.top, 0)]

    # Rules not observed in the selected upstreams. This is informational:
    # platform domains can be missing from consumer lists.
    unobserved_exact = sorted(
        domain for domain in exact if domain not in wildcard and domain not in all_domains
    )
    unobserved_wildcard = sorted(
        domain for domain in wildcard if not any(d == domain or d.endswith("." + domain) for d in all_domains)
    )

    protected_violations = []
    for domain in wildcard:
        root = protected_root(domain, roots)
        if root and domain == root:
            protected_violations.append(domain)
    for pattern, regex in zip(sorted(glob_patterns), globs):
        for root in roots:
            if regex.fullmatch(root):
                protected_violations.append(f"glob {pattern} -> {root}")

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "plugins": [str(path.relative_to(ROOT)) for path in plugin_paths],
        "rules": {
            "exact": len(exact),
            "wildcard": len(wildcard),
            "globs": len(glob_patterns),
            "total": len(exact) + len(wildcard) + len(glob_patterns),
            "active_exact": len(active_exact),
            "active_wildcard": len(active_wildcard),
            "active_globs": len(active_glob_patterns),
            "active_total": len(active_exact)
            + len(active_wildcard)
            + len(active_glob_patterns),
            "optional_exact": len(optional_exact),
            "optional_wildcard": len(optional_wildcard),
            "optional_globs": len(optional_glob_patterns),
            "optional_total": len(optional_exact)
            + len(optional_wildcard)
            + len(optional_glob_patterns),
        },
        "sources": {
            name: {
                **SOURCES[name],
                **coverage[name],
            }
            for name in source_domains
        },
        "overall": overall,
        "candidates": candidates,
        "unobserved": {
            "exact": unobserved_exact[:200],
            "wildcard": unobserved_wildcard[:200],
            "exact_total": len(unobserved_exact),
            "wildcard_total": len(unobserved_wildcard),
        },
        "protected_violations": protected_violations,
        "failures": failures,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("# 广告平台拦截器 · 上游覆盖审计（单插件）")
    print()
    print(f"- 生成时间：`{report['generated_at']}`")
    print(f"- 审计插件：{', '.join(f'`{p}`' for p in report['plugins'])}")
    print(
        f"- 规则：**{report['rules']['total']}** 条"
        f"（exact {report['rules']['exact']} / wildcard {report['rules']['wildcard']} / "
        f"glob {report['rules']['globs']}）"
    )
    if args.include_disabled:
        print(
            f"  - 已含默认注释 [Host] 组与可选 glob {report['rules']['optional_total']} 条；"
            f"核心 {report['rules']['active_total']} 条"
        )
    else:
        print(
            f"  - 另有默认注释 [Host] 组与可选 glob {report['rules']['optional_total']} 条，"
            "不在默认覆盖里（用 --include-disabled 纳入）"
        )
    print(
        f"- 上游去重域名：**{overall['domains']}**，覆盖 **{overall['covered']}**"
        f"（{overall['percent']}%{'；含默认注释组' if args.include_disabled else ''}）"
    )
    if failures:
        print(f"- 下载失败：{len(failures)} 个源（见 stderr / JSON `failures`）")
    print()
    print("## 各源覆盖率")
    print()
    print("| 源 | 类型 | 域名 | 已覆盖 | 覆盖率 | 含可选覆盖 | 含可选覆盖率 | 说明 |")
    print("|---|---:|---:|---:|---:|---:|---:|---|")
    for name, item in coverage.items():
        print(
            f"| `{name}` | {SOURCES[name]['type']} | {item['domains']} | "
            f"{item['covered']} | {item['percent']}% | "
            f"{item['with_optional_covered']} | {item['with_optional_percent']}% | "
            f"{SOURCES[name]['note']} |"
        )
    print()
    print(f"## 未覆盖候选（至少 {args.min_sources} 个源，Top {len(candidates)}）")
    print()
    if candidates:
        print("| 域名 | 命中源数 | 建议 | 共享根 | 默认注释组 |")
        print("|---|---:|---|---|---|")
        for item in candidates:
            print(
                f"| `{item['domain']}` | {item['sources']} | {item['suggestion']} | "
                f"{item['shared_root'] or '-'} | {'已覆盖' if item['optional_covered'] else '-'} |"
            )
    else:
        print("（没有达到阈值的候选）")
    print()
    print("## 规则未在上游出现（信息性）")
    print()
    print(
        f"- exact：{report['unobserved']['exact_total']} 条；"
        f"wildcard：{report['unobserved']['wildcard_total']} 条。"
    )
    print("- 广告平台专域可能本来就不在消费级清单里，不代表规则失效。")
    if unobserved_exact:
        print()
        print("前 40 条 exact：")
        print()
        for domain in unobserved_exact[:40]:
            print(f"- `{domain}`")
    print()
    print("## 共享主域通配违规")
    print()
    if protected_violations:
        for domain in protected_violations:
            print(f"- `*.{domain}`")
    else:
        print("无。")
    print()
    print("---")
    print()
    print("下一步：人工确认候选确实是广告专域后，写入 `src/ads/domains.json`，")
    print("再运行 `python3 tools/build-ads.py && python3 tools/build-ads.py --check`。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
