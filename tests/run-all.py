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
    "test_check_update.js",
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
per_set: dict[str, dict[str, int]] = {}
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
        per_set.setdefault(script_set, {})[name] = n
        status = "FAIL" if label in failed else "PASS"
        print(f"{status:4} {name:26} [{script_set:4}] assertions={n:3}")

print(
    f"\nTOTAL suites={len(SUITES) * len(script_sets)} "
    f"assertions={total} failed={len(failed)}"
)
if failed:
    print("failed suites: " + ", ".join(failed))
    sys.exit(1)

# 测试自己跑出来的数字是「套件数 / 断言数」唯一的机器出处，所以文档里的这些声明由这里核对：
# ①tests/README.md 的「N 套件 ×2 = M 套件 / K 断言」；②同页断言分布表逐行 + 合计。
# 靠人记得回来改文档 = 这些数字一定会漂；跑测试的那一步顺手把它们钉住，漂了当场红。


def check_doc_claims():
    problems = []
    suite_docs = (ROOT / "tests/README.md").read_text(encoding="utf-8")
    claim = re.search(r"(\d+) 套件 ×2 = (\d+) 套件 / (\d+) 断言", suite_docs)
    if claim is None:
        problems.append("tests/README.md 缺少「N 套件 ×2 = M 套件 / K 断言」声明")
    else:
        want = [len(SUITES), len(SUITES) * 2, total]
        got = [int(x) for x in claim.groups()]
        if got != want:
            problems.append(f"tests/README.md 声明 {got}，本次实跑 {want}")

    rows = dict(
        (m.group(1), int(m.group(2)))
        for m in re.finditer(r"^\| `(test_[A-Za-z0-9_]+\.js)` \| (\d+) \|", suite_docs, re.M)
    )
    if not rows:
        problems.append("tests/README.md 找不到断言分布表")
    for script_set in script_sets:
        for name, n in per_set[script_set].items():
            if name not in rows:
                problems.append(f"tests/README.md 断言分布表缺少 {name}")
            elif rows[name] != n:
                problems.append(
                    f"tests/README.md 断言分布表 {name} 声明 {rows[name]}，"
                    f"[{script_set}] 实跑 {n}"
                )
    for name in rows:
        if name not in per_set[script_sets[0]]:
            problems.append(f"tests/README.md 断言分布表有多余行 {name}")
    if len(script_sets) == 2 and rows:
        single = sum(per_set["src"].values())
        total_claim = re.search(
            r"合计 \*\*(\d+)\*\* 条断言；源码与压缩版各一遍，共 \*\*(\d+)\*\* 条", suite_docs
        )
        if total_claim is None:
            problems.append("tests/README.md 缺少「合计 **N** 条断言…」声明")
        else:
            got = [int(x) for x in total_claim.groups()]
            want = [single, total]
            if got != want:
                problems.append(f"tests/README.md 合计声明 {got}，本次实跑 {want}")
    # docs/loon-native-first.md 里「N 断言」也是声明：整套的钉给本次总数，逐套名的钉给该套实跑数。
    native_doc = ROOT / "docs/loon-native-first.md"
    if native_doc.exists():
        native = native_doc.read_text(encoding="utf-8")
        for m in re.finditer(r"`(\d+) 断言`", native):
            if int(m.group(1)) != total:
                problems.append(
                    f"docs/loon-native-first.md 「{m.group(0)}」声明 {m.group(1)}，本次实跑 {total}"
                )
        if len(script_sets) == 2:
            for m in re.finditer(r"本仓库 (\d+) 套件 / (\d+) 断言现状", native):
                got = [int(x) for x in m.groups()]
                want = [len(SUITES) * 2, total]
                if got != want:
                    problems.append(f"docs/loon-native-first.md 声明 {got}，本次实跑 {want}")
        for line in native.splitlines():
            named = re.search(r"(test_[a-z0-9_]+)", line)
            claimed = re.search(r"(\d+) 断言", line)
            if not named or not claimed:
                continue
            suite = named.group(1)
            if not suite.endswith(".js"):
                suite += ".js"
            want = {per_set[s].get(suite) for s in script_sets}
            if want == {None}:
                problems.append(f"docs/loon-native-first.md 引用了不存在的套件 {suite}")
            elif None in want or len(want) != 1 or str(next(iter(want))) != claimed.group(1):
                problems.append(
                    f"docs/loon-native-first.md: 「{line.strip()[:60]}」声明 {claimed.group(1)} 断言，"
                    f"本次 {suite} 实跑 {sorted(x for x in want if x is not None)}"
                )
    return problems


problems = check_doc_claims()
for problem in problems:
    print(f"readme numbers: {problem}", file=sys.stderr)
if problems:
    sys.exit(1)
print(
    f"readme numbers: suite/assertion claims in tests/README.md, "
    f"docs/loon-native-first.md match this run ({len(SUITES)} × {len(script_sets)} = {len(SUITES) * len(script_sets)} "
    f"suites, {total} assertions)"
)
