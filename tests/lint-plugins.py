#!/usr/bin/env python3
"""Structural lint for the Loon plugins (one plugin per app family)."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (path, sections, rules, rewrites, scripts, family)
PLUGINS = [
    ("plugins/soda/soda.plugin", 5, 0, 1, 32, "soda"),
    ("plugins/douyin/douyin.plugin", 5, 0, 0, 7, "douyin"),
]

# 只读观测脚本不需要 argument
OBSERVER_SCRIPTS = ("reward-observe.min.js", "observe.min.js")

FAMILY_CHECKS = {
    "soda": {
        "switches": [
            ("rewardSafe", "true"),
            ("cleanAds", "false"),
            ("blockAdDomains", "false"),
            ("settingsClean", "false"),
            ("debugLog", "false"),
            ("splashClean", "true"),
            ("hideDouyinTab", "false"),
        ],
        "enable": {
            "splashClean": 1,
            "cleanAds": 9,
            "blockAdDomains": 1,
            "settingsClean": 1,
            "debugLog": 20,
        },
        "mitm": [
            "api.qishui.com",
            "conf.qishui.com",
            "ad.zijieapi.com",
            "lianmengapi.snssdk.com",
            "ads5-normal-hl.zijieapi.com",
            "zlink.ugsdk.cn",
            "praisewindow.ugsdk.cn",
        ],
        "samples": {
            "search-block": "https://api.qishui.com/luna/search-block",
            "search-categories": "https://api.qishui.com/luna/search-categories",
            "card": "https://api.qishui.com/luna/card",
            "growth": "https://api.qishui.com/luna/growth/activity_entrance",
            "fallback": "https://api.qishui.com/luna/advert/fallback/done/info",
            "feed": "https://api.qishui.com/luna/feed/song-tab",
        },
    },
    "douyin": {
        "switches": [
            ("treasureMinimal", "true"),
            ("cleanFeedAds", "false"),
            ("killRewardAds", "false"),
            ("cleanUpsell", "false"),
            ("blockAdDomains", "false"),
            ("debugLog", "false"),
        ],
        "enable": {
            "treasureMinimal": 1,
            "cleanFeedAds": 1,
            "killRewardAds": 1,
            "cleanUpsell": 2,
            "blockAdDomains": 1,
            "debugLog": 1,
        },
        "mitm": [
            "beta-luna.douyin.com",
            "ad.zijieapi.com",
            "lianmengapi.snssdk.com",
            "ads5-normal-hl.zijieapi.com",
            "zlink.ugsdk.cn",
            "praisewindow.ugsdk.cn",
        ],
        "samples": {
            "treasure-page": "https://beta-luna.douyin.com/luna/treasure/task/page/v2",
            "incentive-config": "https://beta-luna.douyin.com/luna/advert/incentive/config",
            "incentive-retrieve": "https://beta-luna.douyin.com/luna/advert/incentive/retrieve",
            "ads-dsp": "https://beta-luna.douyin.com/luna/ads/dsp/retrieve",
            "upsell": "https://beta-luna.douyin.com/luna/commerce/v2/upsell",
            "music-festival": "https://beta-luna.douyin.com/luna/growth/music_festival/performance_details",
        },
    },
}

errors = []


def parse_plugin(path):
    data = {}
    sections = []
    cur = None
    for line in path.read_text().splitlines():
        s = line.strip()
        m = re.match(r"^\[([A-Za-z]+)\]$", s)
        if m:
            cur = m.group(1)
            sections.append(cur)
            data.setdefault(cur, [])
            continue
        if cur and s and not s.startswith(("#", ";")):
            data[cur].append(s)
    return data, sections


def parse_meta(path):
    meta = {}
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s.startswith("#!"):
            continue
        if "=" not in s:
            continue
        key, value = s[2:].split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


for fp, want_sections, want_rules, want_rewrites, want_scripts, family in PLUGINS:
    path = ROOT / fp
    data, sections = parse_plugin(path)

    rules = [l for l in data.get("Rule", []) if l.startswith("DOMAIN,")]
    rewrites = [l for l in data.get("Rewrite", []) if "reject-" in l]
    scripts = [
        l for l in data.get("Script", [])
        if l.startswith(("http-response", "http-request"))
    ]

    for line in rewrites:
        try:
            re.compile(line.split()[0])
        except re.error as exc:
            errors.append(f"{fp}: rewrite regex: {exc}")

    compiled = []
    for line in scripts:
        m = re.match(r"^(http-(?:response|request))\s+(\S+)\s+script-path=([^,]+)", line)
        if not m:
            errors.append(f"{fp}: malformed script line: {line[:100]}")
            continue
        try:
            compiled.append(re.compile(m.group(2)))
        except re.error as exc:
            errors.append(f"{fp}: script regex: {exc}")
        if not m.group(3).endswith(".min.js"):
            errors.append(f"{fp}: deployable script must be minified (.min.js): {m.group(3)}")

        script_path = path.parent / m.group(3)
        if not script_path.exists():
            errors.append(f"{fp}: missing script file {script_path}")
        else:
            source_name = pathlib.Path(m.group(3)).name.replace(".min.js", ".js")
            source_path = ROOT / "src" / family / source_name
            if not source_path.exists():
                errors.append(f"{fp}: missing source file {source_path}")
            else:
                if script_path.stat().st_size >= source_path.stat().st_size:
                    errors.append(
                        f"{fp}: script is not actually compressed: "
                        f"{source_path.name} {source_path.stat().st_size}B -> "
                        f"{script_path.name} {script_path.stat().st_size}B"
                    )
                try:
                    line_count = len(script_path.read_text().splitlines())
                    if line_count > 5:
                        errors.append(
                            f"{fp}: minified script still has {line_count} lines: "
                            f"{script_path.name}"
                        )
                except UnicodeDecodeError:
                    errors.append(f"{fp}: minified script is not UTF-8: {script_path}")
            try:
                check = subprocess.run(
                    ["node", "--check", str(script_path)],
                    capture_output=True,
                    text=True,
                )
                if check.returncode != 0:
                    errors.append(
                        f"{fp}: invalid minified script {script_path}: "
                        f"{check.stderr.strip()[:200]}"
                    )
            except FileNotFoundError:
                errors.append("node not found; cannot validate minified scripts")

    actual = (len(sections), len(rules), len(rewrites), len(scripts))
    expected = (want_sections, want_rules, want_rewrites, want_scripts)
    if actual != expected:
        errors.append(f"{fp}: counts {actual}, expected {expected}")

    print(
        f"{fp}: sections={len(sections)} rules={len(rules)} "
        f"rewrites={len(rewrites)} scripts={len(scripts)}"
    )

    spec = FAMILY_CHECKS[family]

    meta = parse_meta(path)
    for key in ("name", "desc", "author", "version", "homepage", "icon"):
        if key not in meta:
            errors.append(f"{fp}: missing #!{key} metadata")
    if "icon" in meta and not meta["icon"].startswith("https://"):
        errors.append(f"{fp}: #!icon must be an https URL, got {meta['icon'][:60]}")
    print(f"  meta: {meta.get('name', '?')} v{meta.get('version', '?')} icon={meta.get('icon', '-')[:60]}")

    arg_text = "\n".join(data.get("Argument", []))
    for name, default in spec["switches"]:
        if f"{name} = switch,{default}" not in arg_text:
            errors.append(
                f"{fp}: missing or wrong Argument switch {name} (expected default {default})"
            )

    if rules:
        errors.append(f"{fp}: plugin must not contain active static domain rules")

    for name, want in spec["enable"].items():
        got = sum(1 for line in scripts if f"enable={{{name}}}" in line)
        if got != want:
            errors.append(f"{fp}: enable={{{name}}} used {got} times, expected {want}")

    for line in scripts:
        if "enable={" not in line:
            errors.append(f"{fp}: script missing enable switch: {line[:100]}")
        if "argument=[" not in line and not any(o in line for o in OBSERVER_SCRIPTS):
            errors.append(f"{fp}: script missing argument: {line[:100]}")

    mitm = "\n".join(data.get("MITM", []))
    for host in spec["mitm"]:
        if host not in mitm:
            errors.append(f"{fp}: MITM missing {host}")

    for label, url in spec["samples"].items():
        hit = any(rx.match(url) for rx in compiled)
        print(f"  {family} sample {label:18} {'HIT' if hit else 'MISS'}")
        if not hit:
            errors.append(f"{fp}: sample {label} not matched")

print(f"lint errors: {len(errors)}")
for err in errors:
    print(" -", err)
sys.exit(1 if errors else 0)
