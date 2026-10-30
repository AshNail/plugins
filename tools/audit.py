#!/usr/bin/env python3
"""仓库健康巡检（检修用，可反复跑）。

用法：
    python3 tools/audit.py            # 全部检查，彩色 ✓/✗
    python3 tools/audit.py --quiet    # 只报问题

退出码：0 = 全绿；1 = 有问题（清单见输出）。
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILS = []
QUIET = False
APP_SLUGS = {
    p.stem for p in (ROOT / "src/apps").glob("*.json") if not p.stem.startswith("_")
}


def header(title):
    if not QUIET:
        print(title)


def ok(msg):
    if not QUIET:
        print(f"  ✓ {msg}")


def bad(msg):
    print(f"  ✗ {msg}")
    FAILS.append(msg)


def warn(msg):
    print(f"  ⚠ {msg}")


def plugin_lines(path, hide_comments=True):
    lines = []
    for raw in path.read_text().splitlines():
        s = raw.strip()
        if hide_comments and (s.startswith("#") or s.startswith("//")):
            continue
        lines.append(raw)
    return lines


def section(path, name):
    out, inside = [], False
    for raw in path.read_text().splitlines():
        s = raw.strip()
        if s.startswith("[") and not s.startswith("[#!"):
            if s.startswith(name) or (name + "]") in s.split()[0:1]:
                inside = True
                continue
            if inside:
                break
        if inside:
            out.append(s)
    return out


def script_refs(plugin):
    refs = []
    for l in plugin_lines(plugin):
        for m in re.finditer(r'script\("([^"]+)"', l):
            refs.append((plugin.parent / m.group(1), l.strip()[:90]))
    return refs


def check_refs():
    header("\n【1】引用完整性（script() → 文件存在；min.js ↔ src 三向对账）")
    for plugin in sorted(ROOT.glob("plugins/*/*.plugin")):
        family = plugin.parent.name
        refs = [p for p, _ in script_refs(plugin)]
        missing = [str(p.relative_to(ROOT)) for p in refs if not p.is_file()]
        if missing:
            bad(f"{plugin.name} 引用缺失: {missing}")
        else:
            ok(f"{plugin.name}: {len(refs)} 个 script 引用全部存在")
        src_missing = []
        for p in refs:
            name = p.name
            src = ROOT / "src" / family / name.replace(".min.js", ".js")
            if name.endswith(".min.js") and not src.is_file():
                src_missing.append(str(src.relative_to(ROOT)))
        if src_missing:
            bad(f"{plugin.name} min.js 无源: {src_missing}")
        else:
            ok(f"{plugin.name}: 引用面 ↔ src 对账完整")
        # 孤儿
        orphans = []
        scripts_dir = plugin.parent / "scripts"
        if scripts_dir.is_dir():
            referenced = {p.name for p in refs}
            for f in sorted(scripts_dir.glob("*.min.js")):
                if f.name not in referenced:
                    orphans.append(f.name)
        if orphans:
            bad(f"{plugin.name} 孤儿 min.js（未被引用）: {orphans}")
        else:
            ok(f"{plugin.name}: 无孤儿 min.js")


def check_versions():
    header("\n【2】版本一致性（#!version ↔ 插件 README / 仓库 README）")
    vers = {}
    for plugin in sorted(ROOT.glob("plugins/*/*.plugin")):
        m = re.search(r"^#!version=(.*)$", plugin.read_text(), re.M)
        vers[plugin.name] = (plugin.parent.name, m.group(1).strip() if m else "?")
    rreadme = (ROOT / "README.md").read_text()
    for name, (family, v) in vers.items():
        ok(f"{name}: v{v}")
        preadme = ROOT / "plugins" / family / "README.md"
        if family in APP_SLUGS:
            # App 插件的 README 由 build-apps 生成，首段有唯一显式版本行；
            # 正文里的上游版本号（如「起点 2.5.0 后」）不能参与比较。
            m = re.search(r"^版本 \*\*(\d+\.\d+\.\d+)\*\*", preadme.read_text(), re.M) \
                if preadme.is_file() else None
            got = m.group(1) if m else "?"
            if got != v:
                bad(f"{name}: 插件版本 v{v}，但 plugins/{family}/README.md 版本行是 v{got}")
            else:
                ok(f"{name}: plugins/{family}/README.md 与 #!version 同步（v{v}）")
            continue
        if preadme.is_file():
            # ads 的版本记录写作 `**2.0.0**`，soda/douyin 写作 `v2.6.1`；
            # 只匹配这两种明确格式，避免把 Loon 3.5.1 当成插件版本。
            readme_text = preadme.read_text()
            mention = re.findall(r"\bv(\d+\.\d+\.\d+)\b", readme_text)
            mention += re.findall(r"\*\*(\d+\.\d+\.\d+)\*\*", readme_text)
            newest = max(mention) if mention else "?"
            if newest != v:
                bad(f"{name}: 插件版本 v{v}，但 plugins/{family}/README.md 最新提到 v{newest}")
            else:
                ok(f"{name}: plugins/{family}/README.md 与 #!version 同步（v{v}）")
        if v not in rreadme:
            bad(f"{name} v{v} 未进仓库 README")


def check_switches():
    header("\n【3】开关一致性（enable=${X} ↔ [Argument] ↔ 头注释声明）")
    for plugin in sorted(ROOT.glob("plugins/*/*.plugin")):
        text = "\n".join(plugin_lines(plugin))
        used = set(re.findall(r"\$\{(\w+)\}", text))
        used -= {"url"}   # Loon 内建变量（规则行的请求 URL 代入），不是插件开关
        args = section(plugin, "[Argument]")
        declared = set()
        for l in args:
            m = re.match(r"^(\w+)[\s=:]?", l)
            if m:
                declared.add(m.group(1))
        missing = sorted(used - declared)
        if missing:
            bad(f"{plugin.name}: 引用了但 [Argument] 未定义: {missing}")
        else:
            ok(f"{plugin.name}: {len(used)} 个 ${'{}'} 变量全部有定义")
        orphans = sorted(declared - used)
        if orphans:
            warn(f"{plugin.name}: 定义了但未引用: {orphans}（可留作预留位）")
        # cron 行
        cron_lines = [l.strip() for l in plugin_lines(plugin) if l.strip().startswith("cron ")]
        for l in cron_lines:
            if "then script(" not in l:
                bad(f"{plugin.name} cron 行缺 then script(): {l[:70]}")
        if cron_lines:
            ok(f"{plugin.name}: cron 行 {len(cron_lines)} 条，均含 then script()")


def check_leaks():
    header("\n【4】泄漏扫描（真实 token / 个人路径 / 邮箱）")
    pat = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|/Users/[A-Za-z0-9_]+/|"
                     r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    hit_paths = []
    for p in list((ROOT / "src").rglob("*.js")) + \
             list((ROOT / "docs").rglob("*.md")) + \
             list(ROOT.glob("plugins/*/*.plugin")) + \
             [ROOT / "README.md"]:
        if not p.is_file():
            continue
        for m in pat.finditer(p.read_text()):
            hit_paths.append(f"{p.relative_to(ROOT)}: …{m.group(0)[:50]}…")
    if hit_paths:
        bad("疑似泄漏:\n        " + "\n        ".join(hit_paths[:10]))
    else:
        ok("无 token / 个人路径 / 邮箱泄漏")


def check_mitm():
    header("\n【5】[MITM] 覆盖与目的对账")
    for plugin in sorted(ROOT.glob("plugins/*/*.plugin")):
        if plugin.name == "ads.plugin":
            # 单 ads 插件是零证书设计：lint 明确要求只有
            # [General] + [Rule] + [Host]，因此这里不应有 [MITM]。
            ok("ads.plugin: 零证书设计，无 [MITM]（预期）")
            continue
        text = plugin.read_text()
        m = re.search(r"\[MITM\]\s*\n?\s*hostname\s*=\s*([^\n]+)", text)
        if not m:
            if plugin.stem in APP_SLUGS:
                # App 插件默认零证书；可选 MITM 增强层整段注释，不装证书不生效。
                ok(f"{plugin.name}: 零证书设计，无生效 [MITM]（预期）")
            else:
                bad(f"{plugin.name}: 无 [MITM] hostname")
            continue
        hosts = [h.strip().replace("%APPEND%", "").strip()
                 for h in m.group(1).split(",")]
        hosts = [h for h in hosts if h]
        canonical = text.replace("\\.", ".")   # 规则行里 host 以转义点书写
        unexplained = []
        for h in hosts:
            # host 需在正文（注释/标签/规则）出现 ≥2 次（1 次=MITM 定义孤立）
            if canonical.count(h) < 2:
                unexplained.append(h)
        if unexplained:
            warn(f"{plugin.name}: host 仅出现一次（无用途注释）: {unexplained}")
        else:
            ok(f"{plugin.name}: {len(hosts)} 个 MITM host 均有正文/注释对应")


def main():
    global QUIET
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    QUIET = args.quiet
    check_refs()
    check_versions()
    check_switches()
    check_leaks()
    check_mitm()
    print()
    if FAILS:
        print(f"✗ 检修机发现 {len(FAILS)} 处问题")
        return 1
    print("✓ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
