#!/usr/bin/env python3
"""核对 GitHub 远端与本地仓库是否一致（上传后必跑）。

用法：
    python3 tools/check-remote.py                 # 默认仓库 AshNail/plugins
    python3 tools/check-remote.py --repo 用户/仓库 --branch main

检查内容（逐个文件）：
    · 远端是否存在
    · 字节数是否一致
    · SHA-256 是否一致
另外打印两个 .plugin 的 #!version，方便确认 Loon 里加载的是新版。

退出码：0 = 全部一致；1 = 有缺失/不一致。
"""
import argparse
import hashlib
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://raw.githubusercontent.com/{repo}/{branch}/"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def fetch(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "loon-plugins-check"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception as exc:  # 网络异常
        return 0, str(exc).encode()


def collect_files():
    """插件引用的脚本 + 插件本身（未引用的脚本不用上传）。"""
    files = []
    for plugin in sorted(ROOT.glob("plugins/*/*.plugin")):
        family = plugin.parent.name
        # 去掉注释行（示例里的 scripts/x.min.js 不算）
        text = "\n".join(
            l for l in plugin.read_text().splitlines() if not l.strip().startswith("#")
        )
        for name in sorted(set(re.findall(r'script\("([^"]+)"', text))):
            if name.endswith(".min.js"):
                files.append(plugin.parent / name)
        files.append(plugin)
    out = []
    for f in files:
        if f in out:
            continue
        out.append(f)
    return sorted(out, key=lambda p: str(p.relative_to(ROOT)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="AshNail/plugins")
    ap.add_argument("--branch", default="main")
    args = ap.parse_args()
    base = BASE.format(repo=args.repo, branch=args.branch)

    print(f"远端: {base}\n")
    bad = 0
    for path in collect_files():
        rel = path.relative_to(ROOT)
        local = path.read_bytes()
        status, remote = fetch(base + str(rel).replace("\\", "/"))
        rel_s = str(rel)
        if status != 200:
            print(f"  [缺失] {rel_s}  (HTTP {status})")
            bad += 1
            continue
        if remote == local:
            print(f"  [一致] {rel_s}  {len(local):,} B  sha {sha256(local)}")
        else:
            print(f"  [不一致] {rel_s}  本地 {len(local):,}B / 远端 {len(remote):,}B  "
                  f"sha {sha256(local)} vs {sha256(remote)}")
            bad += 1

    print("\n远端插件版本：")
    for plugin in sorted(ROOT.glob("plugins/*/*.plugin")):
        rel = plugin.relative_to(ROOT)
        status, remote = fetch(base + str(rel).replace("\\", "/"))
        ver = re.search(rb"^#!version=(.*)$", remote, re.M)
        local_ver = re.search(r"^#!version=(.*)$", plugin.read_text(), re.M)
        if status != 200:
            print(f"  [缺失] {rel}")
            bad += 1
            continue
        rv = ver.group(1).decode() if ver else "?"
        lv = local_ver.group(1) if local_ver else "?"
        flag = "OK" if rv == lv else "旧版"
        print(f"  [{flag}] {rel}  远端 v{rv} / 本地 v{lv}")
        if rv != lv:
            bad += 1

    print()
    if bad:
        print(f"✗ {bad} 处不一致 —— 请把上面标记的文件重新上传到 GitHub")
        return 1
    print("✓ 远端与本地完全一致，Loon 里刷新插件即可生效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
