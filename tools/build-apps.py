#!/usr/bin/env python3
"""多 App 去广告插件生成链。

单一真源：
  src/apps/_sdk.json      广告 SDK 基础设施库——默认**引用** src/ads/domains.json 的已审组
                          （adsGroup 引用，杜绝两处真源漂移），只允许整组启用/禁用与少量补充域
  src/apps/<slug>.json    一个插件的源数据（单 App 插件，或银行类聚合插件）
生成物（勿手改）：
  plugins/<slug>/<slug>.plugin

用法：
  python3 tools/build-apps.py          # 生成全部
  python3 tools/build-apps.py --check  # 字节级漂移门禁（CI / npm run check:apps）

设计约束（与 plugins/ads 相同的纪律，零证书网络层拦截）：
- 只用 [Rule]（DOMAIN-SUFFIX / DOMAIN-KEYWORD）与 [Host] 黑洞两类段；
  不生成拦截/改写型配置（[MITM]/[Rewrite]/request·response 型 [Script]）——
  这些插件服务银行与业务敏感 App，零证书是底线。
- 唯一脚本例外：app.get("crons") 声明的 [Script] cron 型本地通知——Loon 定时器
  本地触发、只发 $notification 附 App 内路由深链，零 MITM、零网络请求；
- 例外：未做证书固定的 App 可带 `enhance` 可选增强层——**整段注释**输出
  （[MITM] hostname + URL-REGEX 路径规则），默认零证书不变，用户装证书后自行取消注释；
  每条路径规则必须附公开可引用 sources，禁止凭空造路径。
- 禁用 DOMAIN-WILDCARD：该语法仅 3.5.3(1008) TestFlight 提供，app 插件必须
  让 App Store 正式版（3.5.2/996）用户可直接导入；通配一律走 [Host] '*.domain'。
- 不写 `#!loon_version`：app 插件的 `#!system` 含 macOS，而 Loon for Mac 的营销版本号是
  独立的一条线（0.1(26) → 0.5.0(1011)，官方只从 991 起把 macOS 构建号与 iOS 统一），
  iOS 口径的 `3.5.1(983)` 在 Mac 上到底比什么官方没写，写了就可能把 Mac 用户挡在门外。
  不填＝不带最低版本（官方只对 `#!system` 明写「未填写表示全部支持」，这条属推断），
  裁量同 `#!system_version`（docs/loon-native-first.md §12.3）；
  功能基线只作为 `loonVersion` 留在 src/apps/*.json 供 README 说明，不进插件头。
- 通配 glob 与精确域都不得命中 src/ads/protected-roots.json 里的共享主域。
- 默认生效条目不得命中任何 App 在 `redlines` 里声明的生死线（名单与判定见 tools/redlines.py，
  与 tools/build-ads.py 共用同一条纪律；注释掉的组不参与，因为红线只管默认就会生效的东西）。
- 每个组带 tier（证据分级 A/B/C）与 sources（证据 URL），C 级组默认注释。
"""
from __future__ import annotations

import fnmatch
import json
import pathlib
import re
import sys
from urllib.parse import urlsplit

from redlines import describe, load_app_redlines, redline_hit, redline_roots, rule_redline_hits

ROOT = pathlib.Path(__file__).resolve().parents[1]
APPS = ROOT / "src/apps"
ADS_ROOTS = ROOT / "src/ads/protected-roots.json"

HOST_BLACKHOLE = "127.0.0.1"
DEFAULT_SYSTEM = "iOS,iPadOS,tvOS,macOS"
DEFAULT_ICON = "https://cdn.adguard.com/public/Adguard/Common/logo.png"
DOMAIN_RE = re.compile(r"^(?:\*\.)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)+$")
WILDCARD_GLOB_RE = re.compile(r"^[a-z0-9*?\[\]!.-]+$")
RULE_KINDS = {"DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}
ACTIONS = {"REJECT", "REJECT-DROP"}
KEY_ORDER = ("name", "desc", "author", "version", "homepage", "openUrl", "icon",
             "system", "date", "tag", "type")


class BuildError(Exception):
    pass


def load_json(path: pathlib.Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_roots(redlines: list[dict] | None = None) -> set[str]:
    """共享主域保护表：手写那份 ∪ 由 App 红线派生的根（与 ads 构建器同一个出口）。

    不派生就会留一个具体的洞：`*.meituan.net`、`*.ttlock.com` 这类整族黑洞既不在手写表里，
    也没有一条红线恰好等于那个根，于是能通过全部校验——而它把 App 明写「绝不碰」的主机
    连同子树一起打成 127.0.0.1。
    """
    data = load_json(ADS_ROOTS)
    roots = set()
    for item in data if isinstance(data, list) else data.get("roots", []):
        roots.add((item if isinstance(item, str) else item["domain"]).lower())
    entries = app_redlines() if redlines is None else redlines
    return roots | redline_roots(entries)


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a Loon DOMAIN-WILDCARD glob (* 跨点, ? 单字符, [...] 类) for safety checks."""
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            out.append(".*")
        elif c == "?":
            out.append("[^.]")
        elif c == "[":
            j = pattern.find("]", i)
            if j < 0:
                raise BuildError(f"unterminated char class in glob {pattern!r}")
            cls = pattern[i + 1:j]
            if cls.startswith("!"):
                out.append("[^" + re.escape(cls[1:]) + "]")
            else:
                out.append("[" + re.escape(cls) + "]")
            i = j
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def validate_rule(raw: str, where: str, roots: set[str]) -> None:
    parts = raw.split(",")
    if len(parts) not in (2, 3):
        raise BuildError(f"{where}: rule needs 2-3 comma fields: {raw!r}")
    kind = parts[0]
    if kind not in RULE_KINDS:
        raise BuildError(f"{where}: rule kind {kind!r} not allowed in app plugins "
                         f"(allowed: {sorted(RULE_KINDS)})")
    action = parts[-1]
    if action not in ACTIONS:
        raise BuildError(f"{where}: action must be one of {sorted(ACTIONS)}: {raw!r}")
    target = parts[1]
    if kind == "DOMAIN-WILDCARD":
        if not WILDCARD_GLOB_RE.match(target):
            raise BuildError(f"{where}: illegal glob chars in {target!r}")
        for root in roots:
            if glob_to_regex(target).fullmatch(root):
                raise BuildError(f"{where}: glob {target!r} matches protected shared root {root!r}")
    elif kind in ("DOMAIN-SUFFIX",):
        if not DOMAIN_RE.match(target):
            raise BuildError(f"{where}: invalid domain in {raw!r}")
        for root in roots:
            if target == root or root.endswith("." + target):
                raise BuildError(f"{where}: DOMAIN-SUFFIX {target!r} would swallow "
                                 f"protected shared root {root!r}")


def app_redlines() -> list[dict]:
    """和 ads 构建器同一份红线数据（tools/redlines.py）；ValueError 升格成 BuildError。"""
    try:
        return load_app_redlines()
    except (ValueError, OSError) as exc:
        raise BuildError(str(exc)) from exc


def check_redline(entry: str, where: str, redlines: list[dict], suffix: bool = False) -> None:
    """按 App 插件的默认生效条目同样不许命中红线。

    `suffix=True` 对应 DOMAIN-SUFFIX：它吞掉目标及其全部子域，所以红线域等于目标、
    或落在目标之下，都算命中。[Host] 条目（精确或 `*.`）交给共用的 redline_hit 判定。
    注释掉的组不参与——和 ads 的默认注释层同一纪律：红线只管「默认就会生效」的东西。
    """
    for item in redlines:
        if suffix:
            hit = item["domain"] == entry or item["domain"].endswith("." + entry)
        else:
            hit = redline_hit(entry, item)
        if hit:
            raise BuildError(
                f"{where}: 生效条目 {entry!r} 命中 {describe(item)}——"
                "本仓库纪律：任何默认生效的拦截都不许触碰 App 自己划的生死线"
            )


def check_rule_redline(rule: str, where: str, redlines: list[dict]) -> None:
    """[Rule] 行的红线检查必须走进 AND/OR 复合，并且认得 DOMAIN-KEYWORD。

    第 27 轮这一层写成 `rule.split(",")[0] in ("DOMAIN", "DOMAIN-SUFFIX")`：`AND,((...))`
    的首 token 是 `AND`，嵌套的 DOMAIN-SUFFIX 一条都没被比过；关键词型则压根不在遍历里，
    而它的覆盖面比后缀还宽（`dns` 这种关键词会把 `dns.jd.com` 整个捞走）。
    """
    for kind, target, item in rule_redline_hits(rule, redlines):
        raise BuildError(
            f"{where}: 生效规则 {rule!r} 的 {kind} 匹配项 {target!r} 命中 "
            f"{describe(item)}——本仓库纪律：任何默认生效的拦截都不许触碰 App 自己划的生死线"
        )


def validate_host(entry: str, where: str, roots: set[str]) -> None:
    if not DOMAIN_RE.match(entry):
        raise BuildError(f"{where}: invalid host entry {entry!r} "
                         "(expect exact domain or *.wildcard.root)")
    if entry.startswith("*."):
        apex = entry[2:]
        for root in roots:
            if apex == root or root.endswith("." + apex):
                raise BuildError(f"{where}: refusing wildcard {entry!r} over "
                                 f"protected shared root {root!r}")
    elif entry in roots:
        raise BuildError(f"{where}: refusing to blackhole protected shared root {entry!r}")


def collect_groups(app: dict, sdklib: dict) -> list[dict]:
    """展开 sdks 引用 + 本地 groups 为一个有序组列表（sdk 引用在前）。

    sdk 条目二选一：
      {"adsGroup": "<id>"}    引用 src/ads/domains.json 的已审组（hosts+rules 原样带过来）
      {"hosts": [...], "rules": [...]}  显式列表
    `=` 前缀主机（ads 源的通配记法）转成 `*.`；引用 adsGroup 时非域名类规则行直接报错。
    """
    groups = []
    ads_by_id = None
    for key in app.get("sdks", []):
        if key not in sdklib["sdks"]:
            raise BuildError(f"{app['slug']}: unknown sdk key {key!r} in sdks[]")
        sdk = sdklib["sdks"][key]
        hosts, rules, title = list(sdk.get("hosts", [])), list(sdk.get("rules", [])), sdk.get("title", key)
        if "adsGroup" in sdk:
            if ads_by_id is None:
                ads = load_json(ROOT / "src/ads/domains.json")
                ads_by_id = {g.get("id"): g for g in ads["plugins"]["ads"]["groups"]}
            g = ads_by_id.get(sdk["adsGroup"])
            if g is None:
                raise BuildError(f"_sdk.json: adsGroup {sdk['adsGroup']!r} 在 src/ads/domains.json 中不存在")
            title = title or g.get("title", sdk["adsGroup"])
            # ads 源的组里 `rules` 字段装的是 [Host] 黑洞条目（裸域/=通配/*.通配），
            # 带逗号的才是 [Rule] 行——引用时按此分流。
            raw = list(g.get("hosts", [])) + list(g.get("rules", []))
            for item in raw:
                if "," in item:
                    if item.split(",")[0] not in RULE_KINDS:
                        raise BuildError(f"_sdk.json: adsGroup {sdk['adsGroup']!r} 含不支持的规则 {item!r}")
                    rules.append(item)
                else:
                    hosts.append(_normalize_host(item))
        groups.append({"id": f"sdk:{key}", "title": title,
                       "note": sdk.get("note", ""), "tier": sdk.get("tier", "A"),
                       "sources": sdk.get("sources", []),
                       "hosts": hosts, "rules": rules,
                       "disabled": sdk.get("disabled", False)})
    for g in app.get("groups", []):
        g = dict(g)
        g.setdefault("hosts", [])
        g.setdefault("rules", [])
        g.setdefault("disabled", False)
        g.setdefault("note", "")
        g.setdefault("tier", "")
        g.setdefault("sources", [])
        groups.append(g)
    return groups


def _normalize_host(h: str) -> str:
    return ("*." + h[1:]) if h.startswith("=") else h


def dedup(seq: list[str]) -> list[str]:
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


CRON_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
CRON_FIELD_RE = re.compile(r"^(?:\*|[0-9*/-]+(?:/[0-9]+)*)$")


def validate_crons(app: dict, where: str) -> None:
    """cron 提醒层：app 插件唯一允许的脚本形态（零 MITM · 零证书 · 纯本地通知）。

    与整条「零脚本拦截」纪律的关系：cron 型 [Script] 不监听/不改写/不请求任何
    流量，网络层形状与「零脚本」等价，因此允许；request/response/generic 型
    一律禁止（那是 MITM 领地，app 插件不进）。源码缺失在构建期直接报错，
    避免「插件的 [Script] 指向一个并不存在的部署件」这种静默断链。
    """
    crons = app.get("crons")
    if crons is None:
        return
    if not isinstance(crons, list) or not crons:
        raise BuildError(f"{where}: crons 必须是非空数组（不需要提醒层就删掉该键）")
    src_dir = ROOT / "src" / app["slug"]
    for i, c in enumerate(crons):
        at = f"{where}: crons[{i}]"
        if not isinstance(c, dict):
            raise BuildError(f"{at}: 必须是对象")
        for key in ("id", "script", "cron", "tag"):
            if not c.get(key):
                raise BuildError(f"{at}: missing {key}")
        for key in ("id", "script"):
            if not CRON_ID_RE.match(c[key]):
                raise BuildError(f"{at}: {key}={c[key]!r} 必须匹配 {CRON_ID_RE.pattern}")
        fields = str(c["cron"]).split()
        if len(fields) != 5 or not all(CRON_FIELD_RE.match(f) for f in fields):
            raise BuildError(f"{at}: cron 必须是 5 段 cron 表达式: {c.get('cron')!r}")
        if "," in c["tag"]:
            raise BuildError(f"{at}: tag 不得含逗号（Loon 脚本属性分隔符）")
        if "\n" in str(c.get("note", "")):
            raise BuildError(f"{at}: note 必须单行（渲染为注释）")
        if not (src_dir / f"{c['script']}.js").is_file():
            raise BuildError(
                f"{at}: 缺少脚本源 src/{app['slug']}/{c['script']}.js"
                "（node tools/build.js 会把 src/<slug>/*.js 压缩到 plugins/<slug>/scripts/）"
            )
    if len({c["id"] for c in crons}) != len(crons):
        raise BuildError(f"{where}: crons[].id 重复")
    if len({c["script"] for c in crons}) != len(crons):
        raise BuildError(f"{where}: crons[].script 重复")


def render_crons(app: dict) -> list[str]:
    """渲染 [Script] 提醒层：行形状钉死为 `cron … then script("scripts/x.min.js") with timeout=60, tag="…"`。

    lint（tests/lint-plugins.py 的 APP_CRON_LINE_RE）对生成物逐行按同一形状复审，
    并与 src/apps/<slug>.json 的 crons[] 对账——任何手改生成物都会在双闸处现形。
    """
    crons = app.get("crons") or []
    if not crons:
        return []
    slug = app["slug"]
    lines = [
        "",
        "# " + "=" * 72,
        "# 提醒脚本层 · cron 本地通知（零 MITM · 零证书 · 不监听/不改写/不请求流量）",
        "# " + "-" * 72,
        "# 本插件拦截面全部走 [Host]/[Rule]；[Script] 只允许 cron 类型：Loon 定时器每天",
        "# 本地触发一次，脚本只发一条 $notification，点通知按 openUrl 直达 App 内路由。",
        "# 明确不做：不代打卡、不代领取——签到/领取端点全部要求 App 进程内 encryptSign",
        "# 侧的请求签名（见上方红线注释），脚本层不存在该签名输入（伪造领取=IVT）。",
        f"# 脚本源 src/{slug}/<name>.js（可读）→ 部署件 plugins/{slug}/scripts/<name>.min.js",
        "# （node tools/build.js 压缩）；改时间/文案改 src/apps 的 crons 后重新生成。",
        "",
        "[Script]",
        "",
    ]
    for c in crons:
        if c.get("note"):
            lines.append(f'# {c["id"]}: {c["note"]}')
        lines.append(
            f'cron {c["cron"]} then script("scripts/{c["script"]}.min.js") '
            f'with timeout=60, tag="{c["tag"]}"'
        )
        lines.append("")
    return lines


def render(app: dict, sdklib: dict, roots: set[str]) -> str:
    slug = app["slug"]
    where = f"src/apps/{slug}.json"
    validate_crons(app, where)
    groups = collect_groups(app, sdklib)
    all_redlines = app_redlines()
    hosts: list[str] = []
    rules: list[str] = []
    enh = app.get("enhance") or {}
    active_enh = bool(enh.get("active"))
    if active_enh and enh.get("quic_fallback"):
        groups.append(quic_fallback_group(enh, where, roots))
        rules += groups[-1]["rules"]
    for g in groups:
        gid = g.get("id", "?")
        redlines = [] if g.get("disabled") else all_redlines
        for h in g["hosts"]:
            validate_host(h, f"{where}:{gid}", roots)
            check_redline(h, f"{where}:{gid}", redlines)
        if g.get("raw"):
            # QUIC 回退组：validate_rule 的形状表只收域名拦截类，所以形状跳过、
            # 红线判定不跳过——protocol_scoped_composite 认得「AND + PROTOCOL」不黑洞域名。
            for r in g["rules"]:
                check_rule_redline(r, f"{where}:{gid}", redlines)
            continue
        for r in g["rules"]:
            validate_rule(r, f"{where}:{gid}", roots)
            check_rule_redline(r, f"{where}:{gid}", redlines)
        hosts += g["hosts"]
        rules += g["rules"]

    has_wildcard = any(r.startswith("DOMAIN-WILDCARD,") for r in rules)
    if has_wildcard:
        raise BuildError(f"{where}: DOMAIN-WILDCARD 语法仅 3.5.3(1008) TestFlight 提供，"
                         "App Store 正式版（3.5.2/996）无法保证解析——"
                         "app 插件一律改用 [Host] '*.domain' 通配黑洞")

    meta = {
        "name": app["name"],
        "desc": app["desc"],
        "author": app.get("author", "edy"),
        "version": app["version"],
        "homepage": app.get("homepage", "https://github.com/AshNail/plugins"),
        "openUrl": app.get("openUrl", f"https://github.com/AshNail/plugins/blob/main/plugins/{slug}/README.md"),
        "icon": app.get("icon", DEFAULT_ICON),
        "system": app.get("system", DEFAULT_SYSTEM),
        "date": app.get("date", ""),
        "tag": app.get("tag", "去广告"),
        "type": "normal",
    }
    for key in ("openUrl", "homepage", "icon"):
        if not meta[key].startswith("https://"):
            raise BuildError(f"{where}: {key} 必须是 https URL: {meta[key]!r}")

    lines = []
    for key in KEY_ORDER:
        if meta.get(key):
            lines.append(f"#!{key}={meta[key]}")
    lines.append("")
    lines.append("# " + "=" * 72)
    lines.append(f"# {meta['name']}")
    lines.append("# " + "-" * 72)
    for note in app.get("comment", []):
        lines.append(f"# {note}")
    lines.append(f"# 本文件由 tools/build-apps.py 从 src/apps/{slug}.json 生成，不要手改生成物。")
    lines.append("# " + "=" * 72)
    lines.append("")

    def section(name: str, items: list[str], emit):
        out = [f"[{name}]", ""]
        for g in groups:
            gitems = g[name == "Rule" and "rules" or "hosts"]
            if not gitems:
                continue
            out.append("# " + "-" * 60)
            title = g.get("title") or g.get("id", "")
            tier = f"（置信 {g['tier']}）" if g.get("tier") else ""
            out.append(f"# {title}{tier}")
            if g.get("note"):
                out.append(f"# {g['note']}")
            for src in g.get("sources", []):
                out.append(f"# 证据: {src}")
            prefix = "# " if g["disabled"] else ""
            marked = g["disabled"]
            if marked:
                out.append("# （默认关闭的组：整组注释，取消注释即启用）")
            for item in dedup(sorted(gitems)):
                out.append(prefix + emit(item))
            out.append("")
        return out

    enh = app.get("enhance")
    if active_enh:
        lines += render_arguments(enh, where)
    if rules:
        lines += section("Rule", rules, lambda r: r)
    lines += section("Host", hosts, lambda h: h + f" = {HOST_BLACKHOLE}")
    cron_lines = render_crons(app)
    lines += cron_lines
    if active_enh:
        lines += render_active_layer(enh, where, bool(cron_lines))
    if enh:
        lines += render_enhance(enh, where, roots, active=active_enh)
    return "\n".join(lines).rstrip("\n") + "\n"


def escape_regex_slashes(pattern: str) -> str:
    return re.sub(r"(?<!\\)/", r"\\/", pattern)


# 增强层「默认启用」是用户裁决的例外，不是给所有 App 开门：只有源里写死
# active=true 的 App 才允许出现 [Argument]/[MITM]/[Script] 三类默认生效配置，
# 且每一行都要能被源逐行重述（tests/lint-plugins.py 的 check_app_plugins 复审）。
BIND_KINDS = {"request", "response", "cron", "generic"}
CRON_EXPR_RE = re.compile(r"^\S+ \S+ \S+ \S+ \S+$")
ARG_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*$")
SCRIPT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def plain_hosts(enh: dict) -> list[str]:
    return [h for h in enh.get("mitm_hosts", []) if not any(c in h for c in "*?[]:")]


def quic_fallback_group(enh: dict, where: str, roots: set[str]) -> dict:
    """active 层的配套 QUIC 回退：拒的是 HTTP/3 协议，不是这台主机。

    MITM 只解密 TCP。App 走 QUIC 时净化脚本一条都收不到——真机日志里那些
    `url:(null)` 就是这个形状。不补这条，默认启用的脚本层等于半生效。
    """
    hosts = plain_hosts(enh)
    if not hosts:
        raise BuildError(f"{where}: enhance.quic_fallback 需要可用的 mitm_hosts（无通配主机）")
    for h in hosts:
        if h.lower() in roots:
            raise BuildError(f"{where}: QUIC 回退主机 {h!r} 是共享主域")
    return {
        "id": "quic-fallback",
        "raw": True,
        "disabled": False,
        "hosts": [],
        "title": "QUIC 回退（增强层配套 · 拒的是 HTTP/3 协议，回落 TCP 后正文不受影响）",
        "note": "MITM 只解密 TCP；App 走 HTTP/3 时下面这些主机的响应脚本会静默收不到。"
                "本组只对 PROTOCOL,QUIC 生效，同一主机的 TCP 请求（正文/书架/章节）零影响。",
        "sources": [],
        "rules": [f"AND,((DOMAIN-SUFFIX,{h}),(PROTOCOL,QUIC)),REJECT" for h in hosts],
    }


def validate_enhance_active(enh: dict, where: str) -> list[str]:
    """active 层的源侧校验：返回绑定行（同时供生成与 lint 对账复用）。"""
    arguments = enh.get("arguments") or []
    bindings = enh.get("bindings") or []
    if not arguments or not bindings:
        raise BuildError(f"{where}: enhance.active 需要 arguments 与 bindings 两段都不为空")
    if enh.get("scripts"):
        raise BuildError(
            f"{where}: enhance.active 用结构化 bindings，不再接受旧的注释态 scripts 字符串"
        )
    if enh.get("rewrite_json"):
        raise BuildError(
            f"{where}: enhance.active 与 response.json.jq 互斥"
            "（官方：Response Body Rewrite 命中时同阶段脚本不执行，active 层已经挂了 Response Script）"
        )
    names: list[str] = []
    for a in arguments:
        name = a.get("name", "")
        if not ARG_NAME_RE.match(name):
            raise BuildError(f"{where}: enhance.arguments.name 非法: {name!r}")
        if name in names:
            raise BuildError(f"{where}: 开关重名 {name!r}")
        if a.get("default") not in ("true", "false"):
            raise BuildError(f"{where}: 开关 {name!r} 的默认值必须是 true/false")
        if not a.get("tag") or not a.get("desc"):
            raise BuildError(f"{where}: 开关 {name!r} 缺 tag/desc")
        names.append(name)
    if "debugLog" not in names:
        raise BuildError(f"{where}: active 层必须有 debugLog 开关（所有绑定都接 with debug=）")
    lines: list[str] = []
    for b in bindings:
        bid = b.get("id", "?")
        kind = b.get("kind")
        if kind not in BIND_KINDS:
            raise BuildError(f"{where}: bindings[{bid}].kind {kind!r} 不在 {sorted(BIND_KINDS)}")
        script = b.get("script", "")
        if not SCRIPT_NAME_RE.match(script):
            raise BuildError(f"{where}: bindings[{bid}].script 非法: {script!r}")
        if not b.get("tag"):
            raise BuildError(f"{where}: bindings[{bid}] 缺 tag")
        timeout = b.get("timeout")
        if not isinstance(timeout, int) or not 1 <= timeout <= 600:
            raise BuildError(f"{where}: bindings[{bid}].timeout 需在 1..600: {timeout!r}")
        for arg in b.get("args", []):
            if arg not in names:
                raise BuildError(f"{where}: bindings[{bid}] 透传了未声明的开关 {arg!r}")
        switch = b.get("switch")
        if switch is not None and switch not in names:
            raise BuildError(f"{where}: bindings[{bid}].switch {switch!r} 不在 arguments 里")
        if kind in ("request", "response", "cron") and not switch:
            raise BuildError(
                f"{where}: bindings[{bid}] 是 {kind} 型绑定，必须带 switch（自动化不得默认生效）"
            )
        if kind in ("request", "response"):
            pattern = b.get("pattern", "")
            if not pattern.startswith("^https://"):
                raise BuildError(f"{where}: bindings[{bid}].pattern 必须以 ^https:// 开头")
            try:
                re.compile(pattern)
            except re.error as e:
                raise BuildError(f"{where}: bindings[{bid}].pattern 正则非法: {e}") from e
            declared = b.get("hosts") or []
            if not declared:
                raise BuildError(
                    f"{where}: bindings[{bid}] 缺 hosts——必须写明挂在哪些已解密主机上，"
                    "不然就是「绑了但收不到响应」的假接线"
                )
            bare = pattern.replace("\\.", ".")
            for h in declared:
                if h not in enh.get("mitm_hosts", []):
                    raise BuildError(
                        f"{where}: bindings[{bid}] 声明 {h!r} 不在 enhance.mitm_hosts 里"
                    )
                suffix = ".".join(h.split(".")[-2:])
                if suffix not in bare:
                    raise BuildError(
                        f"{where}: bindings[{bid}] 声明 {h!r}，但正则里找不到它的后缀 {suffix!r}"
                    )
        if kind == "cron" and not CRON_EXPR_RE.match(b.get("cron", "")):
            raise BuildError(f"{where}: bindings[{bid}].cron 需 5 段: {b.get('cron')!r}")
        lines.append(render_binding(b))
    return lines


def render_binding(b: dict) -> str:
    """一条现代语法绑定。形状与 soda/douyin 手写接线一致：属性顺序 debug→enable→requires_body→timeout→tag。"""
    kind = b["kind"]
    args = ", ".join(f"${{{a}}}" for a in b.get("args", []))
    call = f'script("scripts/{b["script"]}.min.js"'
    call += f", {{{args}}})" if args else ")"
    attrs = ["debug=${debugLog}"]
    if b.get("switch"):
        attrs.append(f'enable=${{{b["switch"]}}}')
    head = ""
    if kind in ("request", "response"):
        if b.get("requires_body"):
            attrs.append("requires_body=true")
        attrs.append(f'timeout={b["timeout"]}')
        attrs.append(f'tag="{b["tag"]}"')
        head = f'{kind} if ${{url}} ~= /{escape_regex_slashes(b["pattern"])}/ then {call} with '
    elif kind == "cron":
        attrs.append(f'timeout={b["timeout"]}')
        attrs.append(f'tag="{b["tag"]}"')
        head = f'cron "{b["cron"]}" then {call} with '
    else:
        attrs.append(f'tag="{b["tag"]}"')
        if b.get("imgUrl"):
            attrs.append(f'img_url="{b["imgUrl"]}"')
        attrs.append(f"timeout={b['timeout']}")
        head = f"generic then {call} with "
    return head + ", ".join(attrs)


def render_arguments(enh: dict, where: str) -> list[str]:
    validate_enhance_active(enh, where)
    out = [
        "",
        "# " + "=" * 72,
        "# 开关（源：src/apps/<slug>.json 的 enhance.arguments；改开关改源后 npm run build:apps）",
        "# " + "-" * 72,
        "# 净化类默认开、自动化类默认关——finishWatch 重放、代领奖、广告时长 patch 都是",
        "# 「代打卡/伪造完成」，不默认生效，也不随净化开关一起被打开。",
        "# " + "=" * 72,
        "",
        "[Argument]",
        "",
    ]
    for a in enh.get("arguments", []):
        out.append(
            f'{a["name"]} = switch,{a["default"]},tag={a["tag"]},desc={a["desc"]}'
        )
    out.append("")
    return out


def render_active_layer(enh: dict, where: str, has_cron_section: bool) -> list[str]:
    """active 增强层的默认生效配置层：[MITM] hostname + [Script] 绑定。"""
    validate_enhance_active(enh, where)
    hosts = enh.get("mitm_hosts", [])
    out = [
        "",
        "# " + "=" * 72,
        "# 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）",
        "# " + "-" * 72,
        "# 不装证书 = 这些主机的 TLS 会被客户端掐断，起点内容加载会失败——",
        "# 这是「净化要看响应体」的代价，用户裁决于 v3.2.0（v4.0.0 曾手工开在生成物上，",
        "# 被一次 build:apps 覆盖回注释态，于是整个净化层真机上静默零执行）。",
        "# URL-REGEX 路径级黑洞仍在文末保持注释：magev6/mage/h5.if 是本 App 的红线主机，",
        "# 解密不等于拦截。",
        "# " + "=" * 72,
        "",
        "[MITM]",
        "",
        f"hostname = %APPEND% {', '.join(hosts)}",
        "",
    ]
    if not has_cron_section:
        out += [
            "# " + "=" * 72,
            "# 脚本层（绑定行由 enhance.bindings 生成，lint 逐行对账）",
            "# " + "-" * 72,
            "# 同名脚本 auto-task.min.js 按 URL 分流：捕获 / 净化 / 秒播 / 重放 / 领奖。",
            "# 源码 src/<slug>/auto-task.js（可读）→ plugins/<slug>/scripts/auto-task.min.js。",
            "# " + "=" * 72,
            "",
            "[Script]",
            "",
        ]
    for b in enh.get("bindings", []):
        note = b.get("note")
        if note:
            out.append(f'# {b["id"]}: {note}')
        out.append(render_binding(b))
        out.append("")
    return out


def render_enhance(enh: dict, where: str, roots: set[str], active: bool = False) -> list[str]:
    """增强层尾巴：注释态的路径级黑洞（response.json.jq / URL-REGEX）。

    只对未做证书固定的 App 有效；启用需要用户先装并信任 Loon 证书，再逐行取消
    注释。这里的每条 URL-REGEX / jq 都必须来自公开可引用的规则源
    （enhance.sources），不凭空造路径。`active=True` 时 [MITM]/QUIC/[Script]
    已经由 render_active_layer 默认生效输出，这里只留仍然注释的路径黑洞。
    """
    mitm_hosts = enh.get("mitm_hosts", [])
    url_rules = enh.get("url_regex", [])
    rewrite_json = enh.get("rewrite_json", [])
    scripts = enh.get("scripts", [])
    if not (mitm_hosts or url_rules or rewrite_json or scripts):
        raise BuildError(f"{where}: enhance 存在但各段全空")
    if (url_rules or rewrite_json) and not mitm_hosts:
        raise BuildError(f"{where}: enhance 路径规则需要 mitm_hosts（HTTPS 必须先解密）")
    if rewrite_json and scripts:
        raise BuildError(
            f"{where}: enhance 的 response.json.jq 与 Response Script 互斥"
            "（官方：Response Body Rewrite 命中时同阶段脚本不执行）"
        )
    for h in mitm_hosts:
        if h.lower() in roots:
            raise BuildError(f"{where}: enhance MITM 命中共享主域 {h!r}")
    for r in url_rules:
        kind = r.split(",", 1)[0]
        if kind != "URL-REGEX":
            raise BuildError(f"{where}: enhance 只允许 URL-REGEX，得到 {kind!r}: {r!r}")
        parts = r.split(",")
        if len(parts) != 3:
            raise BuildError(f"{where}: enhance URL-REGEX 需三段（类型,正则,动作）: {r!r}")
        if parts[2] not in ACTIONS | {"REJECT-DICT", "REJECT-IMG"}:
            raise BuildError(f"{where}: enhance 动作不在白名单: {r!r}")
    for item in rewrite_json:
        if not isinstance(item, dict):
            raise BuildError(f"{where}: enhance.rewrite_json 项必须是对象")
        url, jq = item.get("url", ""), item.get("jq", "")
        sample, note, source = item.get("sample", ""), item.get("note", ""), item.get("source", "")
        if not url.startswith("^https?://"):
            raise BuildError(f"{where}: rewrite_json.url 必须以 ^https?:// 开头: {url!r}")
        if not jq or any(c in jq for c in "`\n\r"):
            raise BuildError(f"{where}: rewrite_json.jq 不能为空或含反引号/换行: {jq!r}")
        if not note or not source:
            raise BuildError(f"{where}: rewrite_json 必须带 note 与 source")
        try:
            rx = re.compile(url)
        except re.error as e:
            raise BuildError(f"{where}: rewrite_json.url 正则非法: {e}: {url!r}") from e
        if not sample.startswith(("http://", "https://")):
            raise BuildError(f"{where}: rewrite_json.sample 必须是完整 URL: {sample!r}")
        host = (urlsplit(sample).hostname or "").lower()
        if not host or not any(fnmatch.fnmatch(host, h.lower()) for h in mitm_hosts):
            raise BuildError(
                f"{where}: rewrite_json.sample 主机 {host!r} 不在 mitm_hosts 内（路径规则必须先解密）"
            )
        if not rx.match(sample):
            raise BuildError(
                f"{where}: rewrite_json.url 不匹配 sample（证据路径对不上）: {url!r} vs {sample!r}"
            )
    out = [""]
    out.append("# " + "=" * 72)
    out.append(
        "# 仍然注释的路径级黑洞（本 App 的 MITM/脚本层已默认启用，这一批按需再开）"
        if active else
        "# 可选 MITM 增强层（下面整段默认注释；不装证书 = 永不生效）"
    )
    out.append("# " + "-" * 72)
    for note in enh.get("intro", "").splitlines():
        out.append(f"# {note}")
    circled = "①②③④⑤⑥"
    if active:
        steps = ["确认 Loon 已装并信任证书（本层已默认解密）"]
    else:
        steps = ["Loon 里装并信任证书", "取消 [MITM] 头与其 hostname 行的注释"]
    if rewrite_json:
        steps.append("取消 [Rewrite] 头及其下所需 response.json.jq 行的注释")
    if url_rules:
        steps.append(
            "把需要的 URL-REGEX 行取消注释并移进上方生效的 [Rule] 段"
            if active else
            "取消 [Rule] 头及需要的 QUIC 回退 / URL-REGEX 行"
        )
    if scripts and not active:
        steps.append("如含脚本，再取消 [Script] 头与其脚本行的注释")
    for i, step in enumerate(steps):
        prefix = "# 启用步骤：" if i == 0 else "#           "
        out.append(prefix + circled[i] + step + (" →" if i < len(steps) - 1 else "。"))
    out.append("# 只对未做证书固定的 App 有效；银行/微信/米家这类做了证书固定，")
    out.append("# MITM 直接失败甚至触发风控——那些插件不提供本层（红线）。")
    out.append("# 本层每一条正则都来自公开可引用规则源，见下方证据；不凭空造路径。")
    for src in enh.get("sources", []):
        out.append(f"# 证据: {src}")
    out.append("# " + "=" * 72)
    out.append("")
    if mitm_hosts and not active:
        out.append("# [MITM]")
        out.append("# " + "-" * 60)
        out.append("# hostname 只列本 App 广告相关的具体接口域，不列整主域；一行取消注释即全部解密。")
        out.append("# hostname = %APPEND% " + ", ".join(mitm_hosts))
    if rewrite_json:
        out.append("#")
        out.append("# [Rewrite]")
        out.append("# " + "-" * 60)
        out.append("# 下列响应 JSON 改写必须放在 [Rewrite] 段：取消本行（# [Rewrite]）与所需行的注释才生效。")
        out.append("# response.json.jq 是 Loon 原生 jq：只删广告字段/节点、保留 mtop 包络；")
        out.append("# 与 Response Script 互斥（body rewrite 命中后脚本不执行），本层不含脚本。")
        for item in rewrite_json:
            out.append(f"# 来源 {item['source']}：{item['note']}")
            out.append(
                f"# response if ${{url}} ~= /{escape_regex_slashes(item['url'])}/"
                f" then response.json.jq(`{item['jq']}`)"
            )
    if url_rules:
        out.append("#")
        out.append("# [Rule]" if not active else "# （路径规则请移进文件上方已生效的 [Rule] 段）")
        out.append("# " + "-" * 60)
        out.append(
            "# 这些规则命中即黑洞本 App 自己登记的红线主机，默认保持注释、按需自行启用。"
            if active else
            "# 下列规则必须放在 [Rule] 段：取消本行（# [Rule]）与所需规则行的注释才生效。"
        )
        quic = [h for h in mitm_hosts if not any(c in h for c in "*?[]:")]
        skipped = [h for h in mitm_hosts if h not in quic]
        if quic and not active:
            out.append("# QUIC 回退（与 MITM 配套）：MITM 只解密 TCP，App 走 HTTP/3 时下面的")
            out.append("# " + ("URL-REGEX / response.json.jq 会静默失效。" if rewrite_json else "URL-REGEX 会静默失效。"))
            out.append("# 取消这些行让对应域的 QUIC 直接拒绝、回落 TCP。")
            for h in quic:
                out.append(f"# AND,((DOMAIN-SUFFIX,{h}),(PROTOCOL,QUIC)),REJECT")
        if skipped:
            out.append("# 通配主机无法用 DOMAIN-SUFFIX 表达，QUIC 回退需另行处理: " + ", ".join(skipped))
        for r in url_rules:
            out.append(f"# {r}")
    if scripts and not active:
        out.append("#")
        out.append("# [Script]")
        out.append("# " + "-" * 60)
        out.append("# 下列脚本必须放在 [Script] 段：取消本行（# [Script]）与所需脚本行的注释才生效。")
        for s in scripts:
            out.append(f"# {s}")
    out.append("")
    return out


def app_files() -> list[pathlib.Path]:
    return sorted(p for p in APPS.glob("*.json") if not p.name.startswith("_"))


def main() -> int:
    check = "--check" in sys.argv
    if not APPS.exists():
        print("apps: src/apps/ 不存在，跳过")
        return 0
    sdklib = load_json(APPS / "_sdk.json") if (APPS / "_sdk.json").exists() else {"sdks": {}}
    roots = load_roots()
    outputs: list[tuple[pathlib.Path, str]] = []
    for path in app_files():
        app = load_json(path)
        if app.get("slug", "") != path.stem:
            raise BuildError(f"{path}: slug={app.get('slug')!r} 与文件名 {path.stem!r} 不一致")
        text = render(app, sdklib, roots)
        out = ROOT / "plugins" / app["slug"] / f"{app['slug']}.plugin"
        outputs.append((out, text))
    if check:
        drift = []
        for out, text in outputs:
            current = out.read_text(encoding="utf-8") if out.exists() else None
            if current != text:
                drift.append(str(out))
        if drift:
            print("DRIFT: 生成物与源不一致，请 `npm run build:apps`：")
            for d in drift:
                print(f"  {d}")
            return 1
        print(f"apps: {len(outputs)} 个插件与源一致")
        return 0
    for out, text in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        n_host = text.count(f" = {HOST_BLACKHOLE}")
        n_rule = sum(1 for ln in text.splitlines() if ln.split(",")[0] in RULE_KINDS)
        print(f"apps: {out} host_blackholes={n_host} rules={n_rule}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as e:
        print(f"build-apps error: {e}", file=sys.stderr)
        sys.exit(1)
