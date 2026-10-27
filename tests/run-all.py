#!/usr/bin/env python3
"""Run the SodaClean script test suites against source and/or minified scripts."""
import argparse
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUITES = [
    "test_sanitize2.js",
    "test_prune.js",
    "test_taskinfos.js",
    "test_ads_surfaces.js",
    "test_soda_upsell_v2.js",
    "test_treasure_prune2.js",
    "test_settings.js",
    "test_feed_flags.js",
    "test_feed_expand.js",
    "test_reward_observe.js",
    "test_store_scope.js",
    "test_unified_args.js",
    "test_block_domains.js",
    "test_douyin_treasure.js",
    "test_douyin_clean.js",
    "test_douyin_upsell.js",
    "test_douyin_activity.js",
    "test_splash_ad.js",
    "test_soda_douyin_entry.js",
    "test_soda_task_titles.js",
    "test_soda_task_page_v2.js",
    "test_soda_kill_reward.js",
    "test_status.js",
    "test_welfare_stamp.js",
    "test_encoding_guard.js",
    "test_args_schema.js",
]

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group()
group.add_argument("--src", action="store_true", help="test src/soda/*.js only")
group.add_argument("--dist", action="store_true", help="test plugins/soda/scripts/*.min.js only")
args = parser.parse_args()

script_sets = ["src"] if args.src else ["dist"] if args.dist else ["src", "dist"]
total = 0
failed = []

for script_set in script_sets:
    for name in SUITES:
        path = ROOT / "tests" / name
        env = os.environ.copy()
        env["SODA_SCRIPT_SET"] = script_set
        env["SCRIPT_SET"] = script_set
        proc = subprocess.run(
            ["node", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        out = proc.stdout + proc.stderr
        bad = bool(re.search(r"FAILURES|FAIL=[1-9]|^\s*FAIL\b", out, re.M))
        label = f"{name} [{script_set}]"
        if proc.returncode != 0 or bad:
            failed.append(label)

        m = re.search(r"PASS=(\d+)\s+FAIL=\d+", out)
        if not m:
            m = re.search(r"ALL PASS\s+pass=(\d+)\s+fail=\d+", out)
        if m:
            n = int(m.group(1))
        elif re.search(r"^PASS\s*$", out, re.M):
            n = 1
        else:
            n = 0
        total += n
        status = "FAIL" if label in failed else "PASS"
        print(f"{status:4} {name:26} [{script_set:4}] assertions={n:3}")

print(
    f"\nTOTAL suites={len(SUITES) * len(script_sets)} "
    f"assertions={total} failed={len(failed)}"
)
if failed:
    print("failed suites: " + ", ".join(failed))
    sys.exit(1)
