#!/usr/bin/env python3
"""从 src/apps/*.json 生成 plugins/<slug>/README.md（单一真源：README 不许手写漂移）。"""
import json
import pathlib
import re
import sys
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS = ROOT / "src/apps"
RAW = "https://raw.githubusercontent.com/AshNail/plugins/main/plugins"
REPO = "https://github.com/AshNail/plugins"


def escape_regex_slashes(pattern):
    return re.sub(r"(?<!\\)/", r"\\/", pattern)


def render(app, sdklib, ads_groups):
    slug = app["slug"]
    name = app["name"]
    url = f"{RAW}/{slug}/{slug}.plugin"
    badge = (
        f"[![一键导入 {slug}.plugin](https://img.shields.io/badge/Loon-导入{quote(name)}-red?"
        f"style=for-the-badge&logo=safari&logoColor=white)]"
        f"(https://www.nsloon.com/openloon/import?plugin={quote(url, safe='')})"
    )
    enh = app.get("enhance") or {}
    crons = app.get("crons") or []
    tier_line = (
        "零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）"
        if enh
        else (
            "零 MITM · 零证书（拦截面 `[Host]`/`[Rule]` + cron 提醒脚本层，见下）"
            if crons
            else "零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）"
        )
    )
    lines = [
        f"# {name}",
        "",
        f"> {app['desc']}",
        "",
        f"版本 **{app['version']}** ｜ 最低 Loon **{app['loonVersion']}** ｜ {tier_line}",
        "",
        "## 安装",
        "",
        badge,
        "",
        "```text",
        url,
        "```",
        "",
        "## 拦截组",
        "",
        "| 组 | 置信 | 状态 | 说明 |",
        "|---|---|---|---|",
    ]
    for g in app.get("groups", []):
        status = "默认关闭" if g.get("disabled") else "启用"
        note = g.get("note", "").replace("\n", " ")
        lines.append(f"| {g['title']} | {g.get('tier','B')} | {status} | {note} |")
    hosts = sum(len(g.get("hosts", [])) for g in app.get("groups", []))
    rules = sum(len(g.get("rules", [])) for g in app.get("groups", []))
    for sid in app.get("sdks", []):
        meta = dict(sdklib.get(sid, {}))
        if meta.get("adsGroup") and meta["adsGroup"] in ads_groups:
            src = ads_groups[meta["adsGroup"]]
            ents = src.get("rules", [])
            meta["hosts"] = [e for e in ents if "," not in e]
            meta["rules"] = [e for e in ents if "," in e]
            meta.setdefault("title", src.get("title", sid))
        n_h = len(meta.get("hosts", []))
        n_r = len(meta.get("rules", []))
        hosts += n_h
        rules += n_r
        title = meta.get("title", sid)
        note = meta.get("note", "域名真源见 ads 组/SDK 库")
        lines.append(f"| {title}（引用组） | A | 启用 | {note} 共 {n_h} 域 / {n_r} 规则。 |")
    if crons:
        lines += [
            "",
            "## 提醒脚本（cron · 零 MITM · 零证书）",
            "",
            "| 脚本 | 触发 | 行为 |",
            "|---|---|---|",
        ]
        for c in crons:
            lines.append(f"| `{c.get('script')}` | cron `{c.get('cron')}` | {c.get('note', '')} |")
        lines += [
            "",
            "> 只发一条本地通知并携带 App 内路由（点通知直达）；不发起任何网络请求、不代打卡、不代领取。",
            "> 签到/领取端点全部要求 App 进程内 encryptSign 的请求签名，插件侧不存在该签名输入。",
            f"> 改提醒时间/文案：改 `src/apps/{slug}.json` 的 `crons[]` 后 `npm run build:apps`（脚本源 `src/{slug}/<name>.js` 由 `npm run build` 压缩）。",
        ]
    if enh:
        n_regex = len(enh.get("url_regex", []))
        n_json = len(enh.get("rewrite_json", []))
        n_hosts = len(enh.get("mitm_hosts", []))
        quic = [h for h in enh.get("mitm_hosts", []) if not any(c in h for c in "*?[]:")]
        skipped = [h for h in enh.get("mitm_hosts", []) if h not in quic]
        lines += [
            "",
            "## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）",
            "",
            enh.get("intro", ""),
            "",
            f"- 解密主机（`[MITM] hostname`，{n_hosts} 个）：{', '.join('`' + h + '`' for h in enh.get('mitm_hosts', []))}",
            f"- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，{len(quic)} 条，注释态）："
            "MITM 只解密 TCP，App 走 HTTP/3 时"
            + (" `URL-REGEX` 与 `response.json.jq` 都会静默失效" if n_json else " `URL-REGEX` 会静默失效")
            + "；启用本层时应连同这些行一起取消注释。",
        ]
        if skipped:
            lines.append(
                f"- 通配主机（{', '.join('`' + h + '`' for h in skipped)}）无法用 `DOMAIN-SUFFIX` 表达 QUIC 回退，"
                "启用该层的这一域时需另行处理。"
            )
        if n_regex:
            lines += [
                f"- 路径级规则（`URL-REGEX`，{n_regex} 条，命中即拦对应广告接口/素材，不影响同域功能请求）：",
                "",
                "```text",
            ]
            for r in enh.get("url_regex", []):
                lines.append(f"# {r}")
            lines += ["```", ""]
        if n_json:
            lines += [
                f"- 响应 JSON 改写（`response.json.jq`，{n_json} 条，注释态）：MITM 解密后按公开模块的 jq "
                "只删广告字段/节点、保留 mtop 包络；与 Response Script 二选一（本层不含脚本）。"
                "建议逐条启用、真机确认后再加下一条。",
                "",
                "```text",
            ]
            for item in enh.get("rewrite_json", []):
                lines.append(f"# 来源 {item['source']}：{item['note']}")
                lines.append(
                    f"# response if ${{url}} ~= /{escape_regex_slashes(item['url'])}/"
                    f" then response.json.jq(`{item['jq']}`)"
                )
            lines += ["```", ""]
        steps = ["Loon 装并信任证书", "取消插件内 `[MITM]` 头与 hostname 行注释"]
        if n_json:
            steps.append("取消 `[Rewrite]` 头与所需 `response.json.jq` 行的注释")
        if n_regex:
            steps.append(
                "取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，"
                "否则规则会落在上一段的末尾而不生效）"
            )
        if enh.get("scripts"):
            steps.append("取消 `[Script]` 头与所需脚本行的注释")
        circled = "①②③④⑤⑥"
        lines.append("启用步骤：" + " → ".join(circled[i] + s for i, s in enumerate(steps)) + "。")
        lines += [
            "",
            "> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，"
            "那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。",
            "",
            "证据：",
        ]
        for src in enh.get("sources", []):
            lines.append(f"- {src}")
    lines += ["", "## 红线与天花板（如实）", ""]
    for c in app.get("comment", []):
        lines.append(f"- {c}")
    lines += [
        "",
        "## 证据与验证",
        "",
        "- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。",
        "- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。",
        f"- 源文件：`src/apps/{slug}.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。",
        "",
        f"统计：精确/通配黑洞 {hosts} 条，[Rule] {rules} 条。",
        "",
    ]
    return "\n".join(lines)


def main():
    write = "--check" not in sys.argv
    sdklib = json.loads((APPS / "_sdk.json").read_text())["sdks"]
    ads = json.loads((ROOT / "src/ads/domains.json").read_text())
    ads_groups = {g.get("id"): g for g in ads["plugins"]["ads"]["groups"]}
    for path in sorted(APPS.glob("*.json")):
        if path.name.startswith("_"):
            continue
        app = json.loads(path.read_text())
        md = render(app, sdklib, ads_groups)
        out = ROOT / "plugins" / app["slug"] / "README.md"
        if write:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md)
        elif not out.exists() or out.read_text() != md:
            print(f"README drift: {out.relative_to(ROOT)}", file=sys.stderr)
            sys.exit(1)
        print(f"apps-readme: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
