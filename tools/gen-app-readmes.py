#!/usr/bin/env python3
"""从 src/apps/*.json 生成 plugins/<slug>/README.md（单一真源：README 不许手写漂移）。"""
import json
import pathlib
import re
import sys
from urllib.parse import quote

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from redlines import expand_rule  # noqa: E402

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
    active_enh = bool(enh.get("active"))
    crons = app.get("crons") or []
    if active_enh:
        # 有的默认增强层只用 [Rule]（config 移植的起点、腾讯新闻）：本仓不再有 [Host] 黑洞时，
        # 别在 README 顶上继续宣称拦截面包含 [Host]。
        host_note = "`[Host]`/`[Rule]`" if any(
            g.get("hosts") for g in app.get("groups", [])
        ) else "`[Rule]`（本插件无 `[Host]` 黑洞层）"
        tier_line = (
            "净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 "
            f"Loon 证书）· 拦截面 {host_note}"
        )
    elif enh:
        tier_line = "零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）"
    elif crons:
        tier_line = "零 MITM · 零证书（拦截面 `[Host]`/`[Rule]` + cron 提醒脚本层，见下）"
    else:
        tier_line = "零证书 · 零 MITM · 零脚本（纯 `[Host]`/`[Rule]`）"
    lines = [
        f"# {name}",
        "",
        f"> {app['desc']}",
        "",
        # 功能基线只写进 README 给人看：iOS/tvOS 是 3.5.x 口径，Loon for Mac 另起 0.x 一条线
        # （构建号自 991 起才与 iOS 统一），所以插件头不带 #!loon_version——反向锁见
        # tests/lint-plugins.py 的 check_loon_version_gate()。
        f"版本 **{app['version']}** ｜ 功能基线 Loon **{app['loonVersion']}**+ "
        "（iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ "
        f"{tier_line}",
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
            meta["hosts"] = list(dict.fromkeys(h for e in ents if "," not in e for h in expand_rule(e)))
            meta["rules"] = [e for e in ents if "," in e]
            meta.setdefault("title", src.get("title", sid))
        n_h = len(meta.get("hosts", []))
        n_r = len(meta.get("rules", []))
        hosts += n_h
        rules += n_r
        title = meta.get("title", sid)
        note = meta.get("note", "域名真源见 ads 组/SDK 库")
        lines.append(f"| {title}（引用组） | A | 启用 | {note} 共 {n_h} 域 / {n_r} 规则。 |")
    if active_enh and enh.get("quic_fallback"):
        n_quic = len([h for h in enh.get("mitm_hosts", []) if not any(c in h for c in "*?[]:")])
        rules += n_quic
        lines.append(
            f"| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 "
            "这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 "
            f"{n_quic} 条。 |"
        )
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
        n_rules = len(enh.get("rewrite") or [])
        n_hosts = len(enh.get("mitm_hosts", []))
        quic = [h for h in enh.get("mitm_hosts", []) if not any(c in h for c in "*?[]:")]
        skipped = [h for h in enh.get("mitm_hosts", []) if h not in quic]
        lines += [
            "",
            "## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）"
            if active_enh
            else "## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）",
            "",
            enh.get("intro", ""),
            "",
            f"- 解密主机（`[MITM] hostname`，{n_hosts} 个，"
            + ("本层已默认生效" if active_enh else "注释态，取消注释才解密")
            + f"）：{', '.join('`' + h + '`' for h in enh.get('mitm_hosts', []))}",
        ]
        # 只有生成器真的下发 QUIC 回退时，README 才能声称有这一层：
        # active 层由 enhance.quic_fallback 决定；注释态由 render_enhance 固定补齐。
        if (not active_enh) or enh.get("quic_fallback"):
            lines.append(
                f"- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，{len(quic)} 条，"
                + ("已生效" if active_enh else "注释态")
                + "）："
                "MITM 只解密 TCP，App 走 HTTP/3 时"
                + (" `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效" if n_rules
                   else " `URL-REGEX` 与 `response.json.jq` 都会静默失效" if n_json
                   else " `URL-REGEX` 会静默失效")
                + ("；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。"
                   if active_enh else "；启用本层时应连同这些行一起取消注释。")
            )
        if active_enh:
            lines += [
                "",
                "### 开关（`[Argument]`）",
                "",
                "| 开关 | 默认 | 作用 |",
                "|---|---|---|",
            ]
            for a in enh.get("arguments", []):
                lines.append(
                    f"| `{a.get('name')}` | {a.get('default')} | {a.get('desc', a.get('tag', ''))} |"
                )
            bindings = enh.get("bindings") or []
            if bindings:
                argmap = {
                    a.get("name"): a.get("default") for a in enh.get("arguments", [])
                }
                bound_switches = [b.get("switch") for b in bindings if b.get("switch")]
                all_on = all(argmap.get(s) == "true" for s in bound_switches if s in argmap)
                if all_on:
                    note = (
                        "> 本层绑定引用的开关默认全开（用户显式裁决，服务端风控后果自担）："
                        "任何一个开关单独关掉即切面停用，不必动插件其余部分。"
                    )
                else:
                    note = (
                        "> 净化类默认开、自动化类默认关：领奖/签到/重放这条线不默认启用是仓库纪律，"
                        "要用就把引用开关的默认值改成 true。"
                    )
                legacy = [b.get("path") for b in bindings if b.get("legacy")]
                if legacy:
                    note = note.rstrip("。") + (
                        "。legacy 引擎绑定（"
                        + "、".join(f"`{p}`" for p in sorted(set(legacy)))
                        + "）按 config 范式不设 enable 门控——cron/generic 一旦门控会静默消失，"
                        "任务取舍由 `argument=[{NAME}]` 参数承担，`{…}` 是 Loon 加载期对 "
                        "`[Argument]` 的占位替换。"
                    )
                lines += ["", note, "", "### 绑定（`[Script]`）", "", "| 脚本 | 触发面 | 开关 | 行为 |", "|---|---|---|---|"]
                for b in bindings:
                    face = b.get("pattern") or b.get("cron") or "generic"
                    probe = "（探针）" if b.get("probe") else ""
                    script_ref = b.get("path") if b.get("legacy") else b.get("script")
                    lines.append(
                        f"| `{script_ref}` | `{face}` | `{b.get('switch') or '—'}` | "
                        f"{b.get('note', b.get('tag', ''))}{probe} |"
                    )
            rewrite_items = enh.get("rewrite") or []
            if rewrite_items:
                lines += [
                    "",
                    "### 净化复写（`[Rewrite]`）",
                    "",
                    "| 规则 | 阶段 | 动作 | 开关 | 行为 |",
                    "|---|---|---|---|---|",
                ]
                for item in rewrite_items:
                    lines.append(
                        f"| `{item.get('id')}` | {item.get('stage')} | "
                        f"`{item.get('action', '').split('(')[0]}` | `{item.get('gate')}` | "
                        f"{item.get('note', '')} |"
                    )
                lines += [
                    "",
                    "> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 "
                    "`Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 "
                    "`$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，"
                    "这正是「净化不生效」的那条链。",
                ]
                if bindings:
                    lines.append(
                        "> 探针纪律：`probe=true` 的绑定与复写命中同一条 URL，按官方口径脚本会被静默抑制，"
                        "所以锚定日志里它**有没有出现**就是**复写有没有命中**的判据。"
                    )
            lines += [
                "",
                f"> 全层由 `src/apps/{slug}.json` 的 `enhance` 整段生成（`tools/build-apps.py`），"
                "lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。",
                "",
            ]
        if skipped:
            lines.append(
                f"- 通配主机（{', '.join('`' + h + '`' for h in skipped)}）无法用 `DOMAIN-SUFFIX` 表达 QUIC 回退，"
                "启用该层的这一域时需另行处理。"
            )
        if n_regex:
            lines += [
                f"- 路径级规则（`URL-REGEX`，{n_regex} 条，命中即拦对应广告接口/素材，不影响同域功能请求）"
                + ("，**保持注释态**——正文与广告位同主机，解密不等于拦截，按需自行启用："
                   if active_enh else "："),
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
                    f" then response.json.jq({json.dumps(item['jq'], ensure_ascii=False)})"
                )
            lines += ["```", ""]
        if active_enh:
            steps = ["Loon 装并信任证书（本层已默认解密这些主机）"]
            if enh.get("arguments"):
                steps.append("要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个）")
            if n_regex:
                steps.append(
                    "要路径级黑洞就取消对应 `URL-REGEX` 行的注释并移进上方已生效的 `[Rule]` 段"
                )
            if n_rules:
                steps.append(
                    "确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，"
                    "再用探针绑定判断复写是否接管（探针消失 = 复写命中）"
                )
        else:
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
        lines.append(
            ("前提与步骤：" if active_enh else "启用步骤：")
            + " → ".join(circled[i] + s for i, s in enumerate(steps)) + "。"
        )
        lines += [
            "",
            "> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，"
            "那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。",
        ]
        if active_enh:
            lines.append(
                "> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——"
                "不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。"
            )
        lines += ["", "证据："]
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
