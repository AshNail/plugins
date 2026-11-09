#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件图标：把 #!icon 变成构建产物，而不是手抄常量。
==================================================

仓库里的图标一直是按「看着对」维护的：从某个第三方清单抄一条
`is1-ssl.mzstatic.com/image/thumb/PurpleNNN/v4/<hash>/<name>.png/512x512bb.jpg`
写进源里。问题是 Apple 那条 URL 的**身份在 hash 段**——

    · `<hash>` 段是 Apple 按构建产物分配的，App 每次更新都可能换新串；
    · 旧串短期通常还活着，但**会被 CDN 回收**，回收后就是 404；
    · `country=CN` 与 `US` 返回的 token 也可能不同。

所以手抄的图标不是「丑」的问题，是**迟早会挂**的问题：本轮体检里 21 个图标
有 17 个 token 已过期，知乎那条已经被回收成 404（Loon 卡片上图标直接空）。

正解是别抄 URL，抄**身份**：`src/icons.json` 只存 bundleId / trackId，
本工具现取现写——

    iTunes Lookup（Apple 官方、免 key、免费）
      → artworkUrl100（同 token 下尺寸段是自由参数）
      → 末段换成统一的 512x512bb.jpg
      → HEAD 校验 200 + image/*
      → 写回 src/apps/<slug>.json 的 icon，或手写插件的 #!icon 行

`is1-ssl.mzstatic.com` 就是 App Store 自己的图片 CDN，因此「统一的免费官方
logo CDN」这件事不需要另外找——它就是图标文件的原始出处。

用法
----
    python3 tools/refresh-icons.py            看现状（离线读，不发请求）
    python3 tools/refresh-icons.py --check    门禁：取在线 URL 比对，漂移就 exit 1
    python3 tools/refresh-icons.py --write    取在线 URL 并写回源

`--check` 需要网络；离线时它报「取不到」并按失败处理，不静默通过。
`--check` 对 Apple CDN 的 `<hash>` 段做**身份级比对**：hash 不同但源里那条 URL
HEAD 仍是 `200 image/*` 时判 `token-ok`（CDN 换了分配串，图标没坏）；
只有源 URL 真的被回收成 404、或非 hash 部分变了才报 drift。
这样既不会被同一次会话里来回变的 token 误报，也不会放过「图标已死」。
生成物（`plugins/<slug>/<slug>.plugin` 里由 `tools/build-apps.py` 渲染的那些）
只改源——改生成物会在下一次 `npm run build:apps` 被覆盖，这是仓库的既定纪律。
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "src" / "icons.json"
MZSTATIC_PREFIX = "https://is1-ssl.mzstatic.com/image/thumb/"
LOOKUP = "https://itunes.apple.com/lookup"
UA = "AshNail-plugins-icon-refresh/1.0"
TIMEOUT = 20

ICON_LINE_RE = re.compile(r'^(!#icon|"icon")\s*[=:]\s*"?(https://[^"\s]+)"?[,;]?\s*$', re.M)
# /v4/<hash>/ 里的 hash 是 Apple 按构建产物分配的串，不是图标身份：
# 同一次 lookup 就可能返回多个等价 token，逐字比对会误报漂移。
# 两种真实形态都要盖住（x / youtube 用分层短段，soda 用单段 UUID）：
#   /v4/a16db478-33e0-fc41-bc84-d5dd33f10762/AppIcon...
#   /v4/ce/44/5f/ce445f10-c40b-8aa9-9d18-32d97dade1fb/ProductionAppIcon...
CDN_TOKEN_RE = re.compile(
    r"(/v\d+/)(?:[0-9a-fA-F]{2}/)*[0-9a-fA-F-]{20,}(?=/)"
)


def cdn_identity(url: str) -> str:
    """把 CDN 分配串抹掉，只留图标身份（bundle 版本段 / 文件名 / 尺寸段）。"""
    return CDN_TOKEN_RE.sub(r"\1<token>", url)


def load_spec() -> dict:
    data = json.loads(ICONS.read_text(encoding="utf-8"))
    return {
        "plugins": data["plugins"],
        "country": data["_country"],
        "size": data["_size"],
        "exceptions": data.get("_exceptions", {}),
    }


def app_files() -> dict:
    """slug -> 该插件真正该写的那一个文件（有源就写源，没源才写插件头）。"""
    out = {}
    for path in sorted((ROOT / "plugins").glob("*/*.plugin")):
        slug = path.parent.name
        src = ROOT / "src" / "apps" / f"{slug}.json"
        out[slug] = src if src.exists() else path
    return out


def expected_url(entry: dict, country: str, size: str) -> tuple[str, str]:
    """按 bundleId（首选）或 trackId 现取 artwork URL。返回 (url, 说明)。"""
    params = []
    if entry.get("bundleId"):
        params.append(("bundleId", entry["bundleId"]))
    elif entry.get("trackId"):
        params.append(("id", str(entry["trackId"])))
    else:
        raise ValueError("条目既没有 bundleId 也没有 trackId")
    params.append(("country", country))
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params)
    req = urllib.request.Request(f"{LOOKUP}?{qs}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    results = payload.get("results") or []
    if not results:
        raise LookupError(f"iTunes Lookup 零结果：{qs}")
    if len(results) > 1:
        raise LookupError(f"iTunes Lookup 返回 {len(results)} 条，身份不唯一：{qs}")
    art = results[0].get("artworkUrl100")
    if not art:
        raise LookupError(f"结果里没有 artworkUrl100：{qs}")
    name = results[0].get("trackName", "")
    return art.rsplit("/", 1)[0] + "/" + size, name


def head_ok(url: str) -> str:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        ctype = resp.headers.get("Content-Type", "")
        if not ctype.startswith("image/"):
            raise LookupError(f"HEAD 返回 Content-Type={ctype}")
        return f"{resp.status} {ctype}"


def current_url(path: Path) -> str:
    """读一个文件里当前的图标 URL；插件头缺这一行时返回空串。"""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        m = re.search(r'^\s*"icon"\s*:\s*"([^"]+)",?\s*$', text, re.M)
    else:
        m = re.search(r"^#!icon=(\S+)\s*$", text, re.M)
    return m.group(1) if m else ""


def write_url(path: Path, url: str) -> None:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        new, n = re.subn(r'(^(\s*)"icon"\s*:\s*)"[^"]+"(,?)$',
                         lambda m: f"{m.group(1)}\"{url}\"{m.group(3)}",
                         text, count=1, flags=re.M)
    else:
        new, n = re.subn(r"^#!icon=\S+\s*$", f"#!icon={url}", text, count=1, flags=re.M)
        if n == 0:
            # 移植件类插件头里本来就没有这一行：插到头部连续 #! 块的末尾，
            # 不动正文任何一行——Loon 只认头部区的 #! 键。
            lines = text.split("\n")
            last = 0
            for i, line in enumerate(lines):
                if line.startswith("#!"):
                    last = i
                elif line.strip():
                    break
            lines.insert(last + 1, f"#!icon={url}")
            new, n = "\n".join(lines), 1
    if n != 1:
        raise SystemExit(f"{path.relative_to(ROOT)}: 找不到可写的 icon 行")
    if new != text:
        path.write_text(new, encoding="utf-8")


def report(rows: list[dict]) -> int:
    drift = sum(1 for r in rows if r["state"] in ("drift", "missing", "dead"))
    for r in rows:
        print(f"  {r['state']:8s} {r['slug']:16s} {r['target']:34s} {r['detail']}")
    return drift


def main(argv: list[str]) -> int:
    spec = load_spec()
    targets = app_files()
    write = "--write" in argv
    checking = "--check" in argv

    rows = []
    failures = 0
    for slug, entry in sorted(spec["plugins"].items()):
        if slug in spec["exceptions"]:
            rows.append({"slug": slug, "state": "except", "target": "-",
                         "detail": spec["exceptions"][slug][:60]})
            continue
        path = targets.get(slug)
        if path is None:
            rows.append({"slug": slug, "state": "orphan", "target": "-",
                         "detail": "src/icons.json 里有、plugins/ 里没有这个插件"})
            failures += 1
            continue
        rel = str(path.relative_to(ROOT))
        have = current_url(path)
        if not checking and not write:
            state = "ok" if have.startswith(MZSTATIC_PREFIX) else "offcdn"
            rows.append({"slug": slug, "state": state, "target": rel,
                         "detail": have[:52] or "缺 #!icon 行"})
            continue
        try:
            want, name = expected_url(entry, spec["country"], spec["size"])
            verified = head_ok(want)
        except (urllib.error.URLError, LookupError, ValueError, TimeoutError) as exc:
            rows.append({"slug": slug, "state": "dead", "target": rel,
                         "detail": f"取不到：{type(exc).__name__} {exc}"})
            failures += 1
            continue
        if have == want:
            rows.append({"slug": slug, "state": "ok", "target": rel,
                         "detail": f"{name} · {verified}"})
            continue
        # hash 段漂移不等于图标坏了：源 URL 还能 200 image/* 就仍是同一张图。
        # 反过来，旧串被 CDN 回收（404）必须继续报 dead，不能靠放宽比较蒙过去。
        if checking and have.startswith(MZSTATIC_PREFIX) and \
                cdn_identity(have) == cdn_identity(want):
            try:
                live = head_ok(have)
            except (urllib.error.URLError, LookupError, ValueError, TimeoutError):
                live = ""
            if live.startswith("200"):
                rows.append({"slug": slug, "state": "token-ok", "target": rel,
                             "detail": f"{name} · CDN token 漂移，原 URL 仍 {live}"})
                continue
            rows.append({"slug": slug, "state": "dead", "target": rel,
                         "detail": f"{name} · 原 URL 已失效（{live or 'HEAD 失败'}），需 --write"})
            failures += 1
            continue
        state = "drift" if have else "missing"
        rows.append({"slug": slug, "state": state, "target": rel,
                     "detail": f"{name} · {verified} · 现值 {have[-24:] or '无'}"})
        if write:
            write_url(path, want)
            rows[-1]["state"] = "wrote"
        else:
            failures += 1

    print(f"icons: {len(rows)} plugin(s) 经 iTunes Lookup + HEAD 校验")
    drift = report(rows)
    if write:
        print("wrote 源；生成物请跑 `npm run build:apps` 同步（本工具不碰生成物）")
        return 0
    if checking:
        if drift:
            print(f"icons drift: {drift} 处与在线 artwork 不一致"
                  f"（跑 `python3 tools/refresh-icons.py --write`）", file=sys.stderr)
            return 1
        print("icons ok")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
