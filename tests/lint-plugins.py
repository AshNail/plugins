#!/usr/bin/env python3
"""Structural lint for the Loon plugins."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGINS = [
    # 一个 App 一个插件：Soda 只部署聚合开关版 soda.plugin。
    ("plugins/soda/soda.plugin", 5, 0, 1, 32),
]
SAMPLES = {
    "search-block": "https://api.qishui.com/luna/search-block",
    "search-categories": "https://api.qishui.com/luna/search-categories",
    "card": "https://api.qishui.com/luna/card",
    "growth": "https://api.qishui.com/luna/growth/activity_entrance",
    "fallback": "https://api.qishui.com/luna/advert/fallback/done/info",
    "feed": "https://api.qishui.com/luna/feed/song-tab",
}
REWARD_POSITIVE = {
    "splash": "https://api.qishui.com/luna/advert/splash/brand/retrieve",
}
REWARD_NEGATIVE = {
    "incentive-config": "https://api.qishui.com/luna/advert/incentive/config",
    "incentive-retrieve": "https://api.qishui.com/luna/advert/incentive/retrieve",
    "ads-config": "https://api.qishui.com/luna/ads/config",
    "ads-retrieve": "https://api.qishui.com/luna/ads/retrieve",
    "task-view": "https://api.qishui.com/luna/treasure/task/view",
    "treasure-entrance": "https://api.qishui.com/luna/treasure/entrance/config",
    "growth-entrance": "https://api.qishui.com/luna/growth/activity_entrance",
    "feed": "https://api.qishui.com/luna/feed/song-tab",
    "fallback": "https://api.qishui.com/luna/advert/fallback/done/info",
    "fallback-action": "https://api.qishui.com/luna/treasure/task/fallback/do_action",
    "flip-card-action": "https://api.qishui.com/luna/treasure/task/flip_card/do_action",
    "guide-action": "https://api.qishui.com/luna/treasure/task/guide/do_action",
    "browse-mall-action": "https://api.qishui.com/luna/treasure/task/browse_mall/do_action",
    "upsell": "https://api.qishui.com/luna/commerce/upsells",
    "upsell-v2": "https://api.qishui.com/luna/commerce/v2/upsell_sort_decision",
}
DEBUG_POSITIVE = {
    "incentive-config": "https://api.qishui.com/luna/advert/incentive/config",
    "incentive-retrieve": "https://api.qishui.com/luna/advert/incentive/retrieve",
    "incentive-done": "https://api.qishui.com/luna/advert/incentive/done",
    "ads-config": "https://api.qishui.com/luna/ads/config",
    "ads-retrieve": "https://api.qishui.com/luna/ads/retrieve",
    "ads-dsp-retrieve": "https://api.qishui.com/luna/ads/dsp/retrieve",
    "reward-receive": "https://api.qishui.com/luna/ads/reward/receive",
    "reward-settle": "https://api.qishui.com/luna/ads/reward/settle",
    "validate-reward": "https://api.qishui.com/luna/commerce/validate_reward",
    "task-view": "https://api.qishui.com/luna/treasure/task/view",
    "treasure-entrance": "https://api.qishui.com/luna/treasure/entrance/config",
    "reward-ads-action": "https://api.qishui.com/luna/treasure/task/reward_ads/do_action",
    "fallback-action": "https://api.qishui.com/luna/treasure/task/fallback/do_action",
    "flip-card-action": "https://api.qishui.com/luna/treasure/task/flip_card/do_action",
    "guide-action": "https://api.qishui.com/luna/treasure/task/guide/do_action",
    "browse-mall-action": "https://api.qishui.com/luna/treasure/task/browse_mall/do_action",
    "growth-entrance": "https://api.qishui.com/luna/growth/activity_entrance",
    "growth-finish": "https://api.qishui.com/luna/growth/activity/finish",
    "fallback-done": "https://api.qishui.com/luna/advert/fallback/done/info",
    "upsell-v2": "https://api.qishui.com/luna/commerce/v2/upsell",
}
DEBUG_NEGATIVE = {
    "splash": "https://api.qishui.com/luna/advert/splash/brand/retrieve",
    "upsell": "https://api.qishui.com/luna/commerce/upsells",
    "upsell-sort": "https://api.qishui.com/luna/commerce/v2/upsell_sort_decision",
    "feed": "https://api.qishui.com/luna/feed/song-tab",
}
REWARD_RULE_FORBIDDEN = [
    "ad.zijieapi.com",
    "lianmengapi.snssdk.com",
    "ads5-normal-hl.zijieapi.com",
    "zlink.ugsdk.cn",
]
errors = []

for fp, want_sections, want_rules, want_rewrites, want_scripts in PLUGINS:
    path = ROOT / fp
    data = {}
    cur = None
    sections = []
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
            family = path.parent.name
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

    if fp.endswith("soda.plugin"):
        for label, url in SAMPLES.items():
            hit = any(rx.match(url) for rx in compiled)
            print(f"  sample {label:18} {'HIT' if hit else 'MISS'}")
            if not hit:
                errors.append(f"{fp}: sample {label} not matched")

    if fp.endswith("SodaClean-Reward-Debug.plugin"):
        for label, url in DEBUG_POSITIVE.items():
            hit = any(rx.match(url) for rx in compiled)
            print(f"  debug+ {label:18} {'HIT' if hit else 'MISS'}")
            if not hit:
                errors.append(f"{fp}: debug sample {label} not matched")
        for label, url in DEBUG_NEGATIVE.items():
            hit = any(rx.match(url) for rx in compiled)
            print(f"  debug- {label:18} {'MATCHED' if hit else 'left out'}")
            if hit:
                errors.append(f"{fp}: debug endpoint {label} should not be observed")

    if fp.endswith("SodaClean-Reward.plugin"):
        rule_domains = [l.split(",", 2)[1] for l in rules if l.count(",") >= 2]
        if rule_domains:
            errors.append(f"{fp}: reward plugin should not block any domain, got {rule_domains}")
        for forbidden in REWARD_RULE_FORBIDDEN:
            if any(forbidden in line for line in rules):
                errors.append(f"{fp}: reward plugin must not block {forbidden}")
        for label, url in REWARD_POSITIVE.items():
            hit = any(rx.match(url) for rx in compiled)
            print(f"  reward+ {label:18} {'HIT' if hit else 'MISS'}")
            if not hit:
                errors.append(f"{fp}: reward sample {label} not matched")
        for label, url in REWARD_NEGATIVE.items():
            hit = any(rx.match(url) for rx in compiled)
            print(f"  reward- {label:18} {'BLOCKED' if hit else 'left intact'}")
            if hit:
                errors.append(f"{fp}: reward endpoint {label} would be modified")

    if fp.endswith("soda.plugin"):
        arg_text = "\n".join(data.get("Argument", []))
        for name, default in [
            ("rewardSafe", "true"),
            ("cleanAds", "false"),
            ("blockAdDomains", "false"),
            ("settingsClean", "false"),
            ("debugLog", "false"),
            ("splashClean", "true"),
            ("hideDouyinTab", "false"),
        ]:
            if f"{name} = switch,{default}" not in arg_text:
                errors.append(
                    f"{fp}: missing or wrong Argument switch {name} (expected default {default})"
                )

        if rules:
            errors.append(f"{fp}: unified plugin must not contain static domain rules")

        expected_enable = {
            "splashClean": 1,
            "cleanAds": 9,
            "blockAdDomains": 1,
            "settingsClean": 1,
            "debugLog": 20,
        }
        for name, want in expected_enable.items():
            got = sum(1 for line in scripts if f"enable={{{name}}}" in line)
            if got != want:
                errors.append(
                    f"{fp}: enable={{{name}}} used {got} times, expected {want}"
                )

        for line in scripts:
            if "enable={" not in line:
                errors.append(f"{fp}: unified script missing enable switch: {line[:100]}")
            if "reward-observe" not in line and "argument=[" not in line:
                errors.append(f"{fp}: unified rewrite script missing argument: {line[:100]}")

        mitm = "\n".join(data.get("MITM", []))
        for host in [
            "api.qishui.com",
            "conf.qishui.com",
            "ad.zijieapi.com",
            "lianmengapi.snssdk.com",
            "ads5-normal-hl.zijieapi.com",
            "zlink.ugsdk.cn",
            "praisewindow.ugsdk.cn",
        ]:
            if host not in mitm:
                errors.append(f"{fp}: MITM missing {host}")

print(f"lint errors: {len(errors)}")
for err in errors:
    print(" -", err)
sys.exit(1 if errors else 0)
