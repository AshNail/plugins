#!/usr/bin/env python3
"""从 Loon 日志里提取任务标题快照（插件 logTaskTitles=on 的输出）。

背景：
    插件的 reward-observe.js 会把福利页任务摘要打成一行 JSON：
        [soda-observe] <rule-id> {"path":...,"tasks":[{"key":..,"title":..},...]}
    tasks[] 每项字段：key | id | type | reward | amount | max | valid | show |
                       status | done | title（仅 logTaskTitles=on 时有）| adSnap

用法：
    # 从剪贴板（Loon 日志整段粘贴）：
    pbpaste | python3 tools/parse-task-titles.py
    pbpaste | python3 tools/parse-task-titles.py --json   # 机读

输出：
    · 全部任务清单（key/id/type/title/状态）
    · 标题里出现「抖音」的条目（★ 标记，即【听抖音】候选）
    · 字段词汇频次（判断该用 key 驱动还是标题匹配做 v2.6.1）
"""
import argparse
import json
import re
import sys

# 行首是插件前缀（soda-observe / douyin-observe 等），行尾是一段 JSON 摘要；
# MAX_LOG 截断的行没有干净结尾，所以不锚定行尾，交给抢救逻辑处理
LINE_RE = re.compile(r"^\[[a-zA-Z0-9._-]+\]\s+\S+\s+(\{.*)$", re.UNICODE)
DOUYIN_WORDS = ("抖音", "douyin", "Douyin", "DOUYIN")

TASK_FIELDS = ("key", "id", "type", "reward", "amount", "max", "valid",
               "show", "status", "done", "title", "action", "adSnap")


def norm_task(t):
    out = {}
    if not isinstance(t, dict):
        return out
    for f in TASK_FIELDS:
        if f in t:
            out[f] = t[f]
    return out


def collect(lines):
    entries = []
    dropped, truncated = 0, 0
    for ln in lines:
        m = LINE_RE.match(ln.strip())
        if not m:
            continue
        raw = m.group(1)
        try:
            obj = json.loads(raw)
        except Exception:
            # 正常失败 → 回收到最后一个 '}' 再试（截断行/尾随脏字符都覆盖）
            cut = raw.rfind("}")
            obj = None
            if cut > 0:
                try:
                    obj = json.loads(raw[: cut + 1])
                    if raw.rstrip().endswith("…"):
                        truncated += 1
                except Exception:
                    obj = None
            if obj is None:
                dropped += 1
                continue
        for t in obj.get("tasks", []):
            nt = norm_task(t)
            if nt:
                entries.append(nt)
    return entries, dropped, truncated


def report(entries, dropped, truncated):
    print(f"共提取任务条目 {len(entries)} 条"
          f"（丢弃不可解析行 {dropped}、截断行抢救 {truncated}）\n")

    if not entries:
        print("没有解析到 tasks[] —— 检查是否：logTaskTitles 已开、日志含 [soda-observe] 行、"
              "或福利页请求发生在开启之前。")
        return 1

    print("【任务清单】")
    for i, t in enumerate(entries, 1):
        title = str(t.get("title", ""))
        star = " ★" if any(w in title for w in DOUYIN_WORDS) else ""
        key = t.get("key") or t.get("id") or "-"
        print(f"  {i:>3}. key={key}  type={t.get('type', '-')}  "
              f"title={title!r}{star}  "
              f"show={t.get('show', '-')} status={t.get('status', '-')} "
              f"done={t.get('done', '-')}")

    douyin_hits = [t for t in entries
                   if any(w in str(t.get("title", "")) for w in DOUYIN_WORDS)]
    print(f"\n【含「抖音」标题条目】{len(douyin_hits)} 条")

    print("\n【key/task_type 词根频次】")
    words = {}
    for t in entries:
        for v in (t.get("key"), t.get("type"), t.get("reward")):
            if isinstance(v, str):
                for part in re.split(r"[^A-Za-z0-9_]+", v):
                    if len(part) >= 4:
                        words[part] = words.get(part, 0) + 1
    for w, c in sorted(words.items(), key=lambda kv: (-kv[1], kv[0]))[:15]:
        mark = " ◄- 建议纳入 v2.6.1 key 匹配" if "douyin" in w.lower() or "listen" in w.lower() else ""
        print(f"  {w:24s} ×{c}{mark}")

    if douyin_hits:
        stable = [t for t in douyin_hits
                  if isinstance(t.get("key"), str) and (
                      "douyin" in t["key"].lower() or "listen" in t["key"].lower())]
        if stable:
            print("\n判定：抖音条目存在稳定 key/task_type → v2.6.1 用 key 驱动收紧"
                  "（标题匹配退居兜底）。")
        else:
            print("\n判定：抖音条目只出现在标题里 → v2.6.1 维持标题匹配，"
                  "仅把标题字段清单按真实结构校正。")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出机读 JSON")
    args = ap.parse_args()
    lines = sys.stdin.read().splitlines()
    entries, dropped, truncated = collect(lines)
    if args.json:
        json.dump({"tasks": entries, "dropped_lines": dropped,
                   "truncated_saved": truncated}, sys.stdout, ensure_ascii=False,
                  indent=1)
        print()
        return 0
    return report(entries, dropped, truncated)


if __name__ == "__main__":
    sys.exit(main())
