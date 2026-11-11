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
  python3 tools/build-apps.py --check  # 字节级漂移门禁（本地 / npm run check:apps）

设计约束（与 plugins/ads 相同的纪律，零证书网络层拦截）：
- 只用 [Rule]（DOMAIN / DOMAIN-SUFFIX / DOMAIN-KEYWORD / AND 复合）与 [Host] 黑洞两类段；
  不生成拦截/改写型配置（[MITM]/[Rewrite]/request·response 型 [Script]）——
  这些插件服务银行与业务敏感 App，零证书是底线。
- 唯一例外：`enhance.active=true` 的 App（未做证书固定，用户裁决）允许默认输出
  [MITM]+[Rewrite]+[Script] 三层；其中 [Rewrite] 是净化主力（引擎自己解压 gzip），
  每条规则必须逐字带 note+source，且与同 URL 的脚本绑定互斥——只有显式标
  `probe=true` 的绑定才允许被复写抑制，充当「复写是否命中」的锚定探针。
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

from redlines import (
    describe,
    expand_rule,
    load_app_redlines,
    redline_hit,
    redline_roots,
    rule_match_items,
    rule_redline_hits,
)
from source_hash import source_value

ROOT = pathlib.Path(__file__).resolve().parents[1]
APPS = ROOT / "src/apps"
ADS_ROOTS = ROOT / "src/ads/protected-roots.json"

HOST_BLACKHOLE = "127.0.0.1"
DEFAULT_SYSTEM = "iOS,iPadOS,tvOS,macOS"
DEFAULT_ICON = "https://cdn.adguard.com/public/Adguard/Common/logo.png"
DOMAIN_RE = re.compile(r"^(?:\*\.)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)+$")
WILDCARD_GLOB_RE = re.compile(r"^[a-z0-9*?\[\]!.-]+$")
RULE_KINDS = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "AND"}
ACTIONS = {"REJECT", "REJECT-DROP", "DIRECT"}
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


def split_rule(raw: str) -> tuple[str, str, str]:
    """把一条 [Rule] 拆成 (类型, 目标, 动作)。

    `AND,((USER-AGENT,QDReader*),(DOMAIN-KEYWORD,x)),REJECT` 的目标里带逗号，
    按逗号直切会把复合条件切碎——这里从右侧取动作，左侧整体保留。
    """
    raw = raw.strip()
    if raw.startswith("AND,"):
        target, sep, action = raw[4:].rpartition(",")
        if not sep:
            raise BuildError(f"rule needs an action: {raw!r}")
        return "AND", target.strip(), action.strip()
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) not in (2, 3):
        raise BuildError(f"rule needs 2-3 comma fields: {raw!r}")
    return parts[0], parts[1], parts[-1]


def validate_domain_match(kind: str, target: str, raw: str, where: str, roots: set[str]) -> None:
    """域名类匹配项的共享主域保护（顶层项与 AND 嵌套项走同一份判定）。"""
    if kind == "DOMAIN":
        if not DOMAIN_RE.match(target):
            raise BuildError(f"{where}: invalid domain in {raw!r}")
        for root in roots:
            if target == root:
                raise BuildError(f"{where}: DOMAIN {target!r} would blackhole "
                                 f"protected shared root {root!r}")
    elif kind == "DOMAIN-SUFFIX":
        if not DOMAIN_RE.match(target):
            raise BuildError(f"{where}: invalid domain in {raw!r}")
        for root in roots:
            if target == root or root.endswith("." + target):
                raise BuildError(f"{where}: DOMAIN-SUFFIX {target!r} would swallow "
                                 f"protected shared root {root!r}")
    elif kind == "DOMAIN-KEYWORD":
        if not target:
            raise BuildError(f"{where}: empty DOMAIN-KEYWORD in {raw!r}")
        for root in roots:
            if target in root:
                raise BuildError(f"{where}: DOMAIN-KEYWORD {target!r} would swallow "
                                 f"protected shared root {root!r}")


def validate_rule(raw: str, where: str, roots: set[str]) -> None:
    kind, target, action = split_rule(raw)
    if kind not in RULE_KINDS:
        raise BuildError(f"{where}: rule kind {kind!r} not allowed in app plugins "
                         f"(allowed: {sorted(RULE_KINDS)})")
    if action not in ACTIONS:
        raise BuildError(f"{where}: action must be one of {sorted(ACTIONS)}: {raw!r}")
    blocking = action != "DIRECT"
    if kind == "AND":
        if not (target.startswith("((") and target.endswith("))")):
            raise BuildError(f"{where}: AND target must be ((cond),(cond)): {raw!r}")
        items = rule_match_items(raw)
        if not items:
            raise BuildError(f"{where}: AND rule has no domain match item: {raw!r}")
        # UA 限定的 AND（config 的 QDReader* 字节系 SDK 拦截）只对起点 App 生效，
        # 不构成对共享主域的全局黑洞；共享根保护跳过，红线判定仍在 check_rule_redline。
        ua_scoped = "USER-AGENT" in target.upper()
        if blocking and not ua_scoped:
            for item_kind, item_target in items:
                validate_domain_match(item_kind, item_target, raw, where, roots)
        return
    if kind == "DOMAIN-WILDCARD":
        if not WILDCARD_GLOB_RE.match(target):
            raise BuildError(f"{where}: illegal glob chars in {target!r}")
        for root in roots:
            if glob_to_regex(target).fullmatch(root):
                raise BuildError(f"{where}: glob {target!r} matches protected shared root {root!r}")
    elif blocking:
        validate_domain_match(kind, target, raw, where, roots)


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
    `=` 前缀主机（ads 源的整域记法）经 redlines.expand_rule 展开为精确主域 + `*.` 子域通配；
    引用 adsGroup 时非域名类规则行直接报错。
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
                    hosts.extend(expand_rule(item))
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
    active_hosts_seen: dict[str, str] = {}
    active_wildcards_seen: dict[str, str] = {}
    for g in groups:
        gid = g.get("id", "?")
        redlines = [] if g.get("disabled") else all_redlines
        for h in g["hosts"]:
            validate_host(h, f"{where}:{gid}", roots)
            check_redline(h, f"{where}:{gid}", redlines)
            if not g.get("disabled"):
                hl = h.lower()
                if hl in active_hosts_seen:
                    raise BuildError(
                        f"{where}:{gid}: 生效 [Host] {h!r} 与前序组 {active_hosts_seen[hl]!r} 重复"
                    )
                active_hosts_seen[hl] = gid
                if hl.startswith("*."):
                    active_wildcards_seen[hl[2:]] = gid
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

    for hl, gid in active_hosts_seen.items():
        if hl.startswith("*."):
            continue
        for base, wgid in active_wildcards_seen.items():
            if hl != base and hl.endswith("." + base):
                raise BuildError(
                    f"{where}:{gid}: 生效 [Host] {hl!r} 已被 {wgid!r} 的 '*.{base}' 通配覆盖（冗余规则）"
                )
    if active_enh:
        for mh in enh.get("mitm_hosts", []):
            mhl = mh.lower()
            if mhl in active_hosts_seen or any(
                mhl != base and mhl.endswith("." + base) for base in active_wildcards_seen
            ):
                raise BuildError(
                    f"{where}: enhance.mitm_hosts 中的 {mh!r} 同时在生效 [Host] 中被黑洞到 127.0.0.1"
                    "（DNS 阶段即阻断，MITM/Rewrite 永不可达——请从一侧移除）"
                )

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
    # 官方 Plugin 页的 `#!source`：声明插件作者指定下载地址 URL 字符串的 SHA-256，
    # Loon 首次联网安装时对用户实际填写的完整 URL 算哈希并比对（多值逗号分隔，任一匹配即通过）。
    # 哈希一律现算——手抄的 64 位十六进制会与地址脱钩，而「地址变了哈希没变」是个**假的**校验，
    # 比不写更危险。口径见 tools/source_hash.py（唯一出口），lint 的 check_source_hash() 反向复算。
    lines.append(f"#!source={source_value(slug)}")
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
        seen_active: set[str] = set()
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
            # 默认按字典序稳定输出；声明 ordered=true 的组保留源内顺序
            # （config 移植层要与上游 [Rule] 逐行同序，排序会破坏逐行对账）。
            items = dedup(gitems) if g.get("ordered") else dedup(sorted(gitems))
            for item in items:
                line = emit(item)
                if not marked:
                    if line in seen_active:
                        continue
                    seen_active.add(line)
                out.append(prefix + line)
            out.append("")
        return out

    enh = app.get("enhance")
    if active_enh:
        lines += render_arguments(enh, where)
    if rules:
        lines += section("Rule", rules, lambda r: r)
    if hosts:
        lines += section("Host", hosts, lambda h: h + f" = {HOST_BLACKHOLE}")
    cron_lines = render_crons(app)
    lines += cron_lines
    if active_enh:
        lines += render_active_layer(enh, where, bool(cron_lines))
    if enh:
        lines += render_enhance(enh, where, roots, active=active_enh)
    # legacy vendored 引擎指针必须真实落盘：相对 script-path 在 build 期就验存在——
    # 生成一个引用不存在文件的插件等于生成一个静默不执行的绑定（比不引用更糟）。
    blob = "\n".join(lines)
    for rel in sorted(set(re.findall(r"script-path=(scripts/[A-Za-z0-9][A-Za-z0-9._-]*\.js)", blob))):
        if not (ROOT / "plugins" / slug / rel).exists():
            raise BuildError(f"{where}: legacy 绑定引用的 vendored 脚本不存在: plugins/{slug}/{rel}")
    return "\n".join(lines).rstrip("\n") + "\n"


def escape_regex_slashes(pattern: str) -> str:
    return re.sub(r"(?<!\\)/", r"\\/", pattern)


# 增强层「默认启用」是用户裁决的例外，不是给所有 App 开门：只有源里写死
# active=true 的 App 才允许出现 [Argument]/[MITM]/[Script] 三类默认生效配置，
# 且每一行都要能被源逐行重述（tests/lint-plugins.py 的 check_app_plugins 复审）。
BIND_KINDS = {"request", "response", "cron", "generic"}
# [Argument] 控件白名单：官方只定义 switch / input / select 三类。app-json 源目前只用到
# switch 与 input（input 用于 CRONEXP/TIMEOUT 这类文本参数，见 config 范式的 QDREADER_* 体系）。
ARG_TYPES = ("switch", "input")
# legacy（旧式）绑定的 vendored 引擎指针：只能是插件目录内的相对路径，禁远程 URL——
# 旧式 script-path 一旦指向远程，就变成第三方热更依赖，与「本仓自包含」纪律冲突。
VENDORED_PATH_RE = re.compile(r"^scripts/[A-Za-z0-9][A-Za-z0-9._-]*\.js$")
# legacy 绑定里的 [Argument] 占位：旧语法用 {NAME} 指代参数（config 有效基线的逐字形状）。
TIMEOUT_PH = "{TIMEOUT}"
CRON_PH = "{CRONEXP}"
# legacy(旧式) 绑定的阶段行首：config 有效基线的逐字形状（v2 的 request/response 前缀是
# 内联 if/then 语法专用，旧语法下不成立——写错 Loon 会当无效行静默丢弃）。
LEGACY_STAGE = {"request": "http-request", "response": "http-response"}
# active 增强层的引擎复写层（[Rewrite]）：Loon v2 复写语法，一条规则一行。
# 为什么要这一层而不是脚本：起点 Argus 的响应带 Content-Encoding，[Script] 侧读响应体
# 就得先对付压缩，而脚本层只有 $utils.ungzip（gzip）——收到 br/zstd 就是乱码，低 Build 连
# ungzip 都没有，净化静默零生效（真机 HAR 与 2026-11-06 日志见 qidian.json）。
# 这一层的合法形态因此是「把压缩协商改到脚本能处理的形状」：gzip 是让它落进 ungzip 的能力圈，
# identity（v3.5.7 起起点改走这条）是干脆让上游不压。两者都不需要 gate：它服务的是脚本链的
# 解析前提，不是用户的净化开关，cleanAds 仍然只管会改字段的那些规则。
# response.json.* / reject_* 都由引擎完成解压与终止响应，脚本链的 gzip 面整个消失。
REWRITE_STAGES = {"request", "response"}
REWRITE_TERMINATE_RE = re.compile(r"^reject_(dict|array|img|video)\((200|204|404)\)$")
REWRITE_REQ_HEADER_RE = re.compile(
    r'^request\.header\.set\("Accept-Encoding",\s*"(gzip|identity)"\)$'
)
REWRITE_JSON_RE = re.compile(
    r"^response\.json\.(?P<kind>replace|delete|jq)\((?P<args>.*)\)$", re.S
)
REWRITE_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
DOT_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
SCALAR_JSON_RE = re.compile(r'^(?:".*"|-?\d+(?:\.\d+)?|true|false|null)$')
CRON_EXPR_RE = re.compile(r"^\S+ \S+ \S+ \S+ \S+$")
ARG_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
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
    rewrites = enh.get("rewrite") or []
    if not arguments or not (bindings or rewrites):
        raise BuildError(f"{where}: enhance.active 需要 arguments，且 bindings 与 rewrite 至少有一段不为空")
    if enh.get("scripts"):
        raise BuildError(
            f"{where}: enhance.active 用结构化 bindings，不再接受旧的注释态 scripts 字符串"
        )
    if enh.get("rewrite_json"):
        raise BuildError(
            f"{where}: enhance.active 与 rewrite_json 互斥"
            "（默认生效复写请放入 enhance.rewrite）"
        )
    names: list[str] = []
    for a in arguments:
        name = a.get("name", "")
        if not ARG_NAME_RE.match(name):
            raise BuildError(f"{where}: enhance.arguments.name 非法: {name!r}")
        if name in names:
            raise BuildError(f"{where}: 开关重名 {name!r}")
        typ = a.get("type", "switch")
        if typ not in ARG_TYPES:
            raise BuildError(f"{where}: 开关 {name!r} 的 type {typ!r} 不在 {list(ARG_TYPES)}（select 未使用）")
        if typ == "switch":
            if a.get("default") not in ("true", "false"):
                raise BuildError(f"{where}: 开关 {name!r} 的默认值必须是 true/false")
        else:  # input：default 是一行文本；number=true 声明数值形态（Loon type=number）
            default = a.get("default", "")
            if not isinstance(default, str) or not default or "\n" in default or "\r" in default:
                raise BuildError(f"{where}: input {name!r} 的 default 必须是一行非空字符串: {default!r}")
            if "," in default or default.startswith('"'):
                raise BuildError(
                    f"{where}: input {name!r} 的 default 不许含英文逗号或以引号开头: {default!r}"
                )
            if a.get("number") and not re.fullmatch(r"[0-9]+", default):
                raise BuildError(
                    f"{where}: input {name!r} 声明 number=true 但 default 不是 0-9 数字: {default!r}"
                )
        if not a.get("tag") or not a.get("desc"):
            raise BuildError(f"{where}: 开关 {name!r} 缺 tag/desc")
        for text in (a.get("tag", ""), a.get("desc", "")):
            if "," in text:
                raise BuildError(
                    f"{where}: 开关 {name!r} 的 tag/desc 含英文逗号（Loon 按逗号切属性）: {text!r}"
                )
        names.append(name)
    debug_arg = enh.get("debug_arg") or "debugLog"
    if any(not b.get("legacy") for b in bindings) and debug_arg not in names:
        raise BuildError(
            f"{where}: active 脚本层必须有 {debug_arg} 开关"
            f"（v2 绑定都接 with debug=${{{debug_arg}}}）；纯 legacy 引擎绑定可省略"
        )
    lines: list[str] = []
    for b in bindings:
        bid = b.get("id", "?")
        kind = b.get("kind")
        if kind not in BIND_KINDS:
            raise BuildError(f"{where}: bindings[{bid}].kind {kind!r} 不在 {sorted(BIND_KINDS)}")
        legacy = b.get("legacy") is True
        if legacy:
            # config 范式的引擎绑定：本体 vendored 相对路径 + 旧语法 {NAME} 占位参数。
            if not VENDORED_PATH_RE.match(b.get("path", "")):
                raise BuildError(
                    f"{where}: bindings[{bid}].path 需为相对 vendored 指针/scripts/<name>.js: {b.get('path')!r}"
                )
            if b.get("args"):
                raise BuildError(
                    f"{where}: bindings[{bid}] legacy 绑定不吃 args（引擎参数走 argument=[{{NAME}}]）"
                )
        else:
            script = b.get("script", "")
            if not SCRIPT_NAME_RE.match(script):
                raise BuildError(f"{where}: bindings[{bid}].script 非法: {script!r}")
        if not b.get("tag"):
            raise BuildError(f"{where}: bindings[{bid}] 缺 tag")
        if "," in b.get("tag", ""):
            raise BuildError(
                f"{where}: bindings[{bid}].tag 含英文逗号（Loon 按逗号切属性）: {b.get('tag')!r}"
            )
        timeout = b.get("timeout")
        if legacy and timeout == TIMEOUT_PH:
            pass
        elif not isinstance(timeout, int) or not 1 <= timeout <= 600:
            raise BuildError(
                f"{where}: bindings[{bid}].timeout 需在 1..600 或 {{TIMEOUT}} 占位（legacy）: {timeout!r}"
            )
        for arg in b.get("args", []):
            if arg not in names:
                raise BuildError(f"{where}: bindings[{bid}] 透传了未声明的开关 {arg!r}")
        switch = b.get("switch")
        if switch is not None and switch not in names:
            raise BuildError(f"{where}: bindings[{bid}].switch {switch!r} 不在 arguments 里")
        if not legacy and kind in ("request", "response", "cron") and not switch:
            raise BuildError(
                f"{where}: bindings[{bid}] 是 {kind} 型绑定，必须带 switch（自动化不得默认生效）；"
                "legacy 引擎绑定例外——config 范式的任务取舍由 argument=[{SWITCH}] 参数控制，"
                "且 cron/generic 绑定官方纪律是「不得被 enable 门控」（门控会让 cron 静默消失）"
            )
        if legacy and b.get("argument"):
            for arg in b["argument"]:
                if arg not in names:
                    raise BuildError(
                        f"{where}: bindings[{bid}].argument 里的 {arg!r} 不是已声明的参数"
                    )
            if len(b["argument"]) != len(set(b["argument"])):
                dups = [x for x in b["argument"] if b["argument"].count(x) > 1]
                raise BuildError(
                    f"{where}: bindings[{bid}].argument 包含重复参数名 {dups}（无法对齐 Script v2 规范，官方转换器会报 duplicate-plugin-argument）"
                )
        if kind in ("request", "response"):
            pattern = b.get("pattern", "")
            ok_prefix = (
                pattern.startswith(("^https://", "^https?:"))
                if legacy else pattern.startswith("^https://")
            )
            if not ok_prefix:
                raise BuildError(f"{where}: bindings[{bid}].pattern 必须以 ^https:// 开头（legacy 允许 ^https?:）")
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
        if kind == "cron":
            cron = b.get("cron", "")
            if not (legacy and cron == CRON_PH) and not CRON_EXPR_RE.match(cron):
                raise BuildError(
                    f"{where}: bindings[{bid}].cron 需 5 段或 legacy {CRON_PH} 占位: {cron!r}"
                )
        if b.get("probe"):
            if kind not in ("request", "response"):
                raise BuildError(
                    f"{where}: bindings[{bid}].probe 只对 request/response 绑定有意义"
                    "（cron/generic 没有 URL，谈不上被复写抑制）"
                )
            if not enh.get("rewrite"):
                raise BuildError(
                    f"{where}: bindings[{bid}].probe 声称「等着被 enhance.rewrite 抑制」，"
                    "但源里一条复写规则都没有"
                )
        lines.append(render_binding(b, enh.get("debug_arg") or "debugLog"))
    validate_rewrite(enh, where, names, bindings)
    return lines


def render_binding(b: dict, debug_arg: str = "debugLog") -> str:
    """v2 绑定：形状与 soda/douyin 手写接线一致，属性顺序 debug→enable→requires_body→binary_body_mode→timeout→tag。

    binding.debug=true 把这一条的 with debug 常开（取证期用）。注意 21:35 真机日志判死了
    「debug=true 会把脚本 console 落主日志」——官方口径是 console.log 写「当前脚本日志」，
    导出的主日志结构上没有它；debug 常开只保住 App 内那份脚本日志。真正会出现在主日志里的
    是 tag 字面量（match/Trigger/Finished 行原样带），所以取证期的 build 指纹要往 tag 里放。

    legacy=True 的绑定走 render_binding_legacy（config 有效基线的旧式形状）——引擎本体
    （vendored Qidian.js）的参数体系是按旧式 argument=[{NAME}] 写的，v2 换形状等于换
    交付语义，所以这类绑定整体保形状。
    """
    if b.get("legacy"):
        return render_binding_legacy(b)
    kind = b["kind"]
    args = ", ".join(f"${{{a}}}" for a in b.get("args", []))
    call = f'script("scripts/{b["script"]}.min.js"'
    call += f", {{{args}}})" if args else ")"
    attrs = ["debug=true" if b.get("debug") is True else f"debug=${{{debug_arg}}}"]
    if b.get("switch"):
        attrs.append(f'enable=${{{b["switch"]}}}')
    head = ""
    if kind in ("request", "response"):
        if b.get("requires_body"):
            attrs.append("requires_body=true")
        if b.get("binary_body_mode"):
            attrs.append("binary_body_mode=true")
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


def render_binding_legacy(b: dict) -> str:
    """config 有效基线（Plugin/qidian.plugin [Script]）的旧式绑定逐字形状。

    http-request <pattern> script-path=<path>, requires-body=..., timeout=..., tag=<tag>[, enable={SW}][, argument=[{N1},...]]
    cron {CRONEXP} / generic 同形（前缀不同）。引擎本体 vendored Qidian.js 的参数
    体系按旧式 argument=[{NAME}] 写成，绑定形状必须与 config 同源——这是 B 方案
    用户裁决的「引擎不换形」边界。属性顺序按 config：script-path → requires-body →
    timeout → tag → enable → argument；tag 不加引号（config原文），故 tag 禁 ASCII
    逗号（validate 已拦）；`{NAME}` 是旧式 [Argument] 占位，Loon 在加载期替换。
    """
    kind = b["kind"]
    attrs = [f"script-path={b['path']}"]
    if kind in ("request", "response"):
        attrs.append(f"requires-body={'true' if b.get('requires_body') else 'false'}")
        # v4.0.1 裁决（2026-11-10）：声明了 binary_body_mode 的 legacy 绑定必须带出，
        # 否则 Loon 把 gzip 体按 UTF-8 硬解成字符串交给脚本（高位字节已成 U+FFFD），
        # safeJsonParse 必然 null → 深度净化静默透传（same-day HAR：mainPage 三次
        # 回包全是原样 23 键）。v3.6.2 判死的是「旧脚本统一回字符串」，v4.0.1 的脚本
        # 已改为按来路形态回写（字节进→字节出），两者不冲突。probe 面不影响：
        # append 在 requires-body 之后，与 v2 的属性顺序一致。
        if b.get("binary_body_mode"):
            attrs.append("binary_body_mode=true")
    attrs.append(f"timeout={b['timeout']}")
    attrs.append(f"tag={b['tag']}")
    if b.get("switch"):
        attrs.append(f"enable={{{b['switch']}}}")
    if b.get("argument"):
        attrs.append("argument=[" + ",".join("{" + a + "}" for a in b["argument"]) + "]")
    if kind in ("request", "response"):
        # 旧语法里 request/response 阶段的行首是 http-request / http-response
        # （config 有效基线原文）；不带 if/then 也没有 script()——那是 v2 的形状。
        head = f'{LEGACY_STAGE.get(kind, kind)} {escape_regex_slashes(b["pattern"])} '
    elif kind == "cron":
        head = f'cron {b["cron"]} '
    else:
        head = "generic "
    return head + ", ".join(attrs)


def render_argument_line(a: dict) -> str:
    """[Argument] 的一行。switch 形态沿用仓库惯例（不引号 value）；input 形态对
    含空白/特殊值加双引号（config 形状：CRONEXP=input,"11 2 * * *"，TIMEOUT=input,420,type=number）。"""
    if a.get("type") == "input":
        default = str(a["default"])
        if "," in default or re.search(r"[\s*?()\[\]{}]", default):
            default = f'"{default}"'
        meta = ",type=number" if a.get("number") else ""
        return f'{a["name"]} = input,{default}{meta},tag={a["tag"]},desc={a["desc"]}'
    return f'{a["name"]} = switch,{a["default"]},tag={a["tag"]},desc={a["desc"]}'


def split_action_args(text: str) -> list[str]:
    """按顶层逗号切分动作参数：尊重双引号（含 \\" 转义）与中括号嵌套。"""
    parts: list[str] = []
    buf = ""
    depth = 0
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            buf += ch
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            buf += ch
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                raise ValueError("括号不平衡")
        if ch == "," and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if depth != 0 or in_str:
        raise ValueError("括号或引号不平衡")
    parts.append(buf.strip())
    return [p for p in parts if p != ""]


def check_json_action(action: str, where: str) -> None:
    """response.json.replace|delete|jq 的参数形状校验。

    官方《Rewrite 新语法》两条硬约束在这里都会踩：① 批量参数是**两个等长平行数组**
    （keys 与 values 按下标配对，写成扁平单数组会被加载期拒绝）；config 原文另有
    `replace(["key","value"])` 的单对形态（Plugin/qidian.plugin），一并接受；② JSON
    值只支持 String/Number/Boolean/null/变量，**不含数组/对象**——置空数组必须走 json.jq。
    """
    m = REWRITE_JSON_RE.match(action)
    if not m:
        raise BuildError(f"{where}: 不是合法的 response.json.* 动作: {action!r}")
    kind = m.group("kind")
    try:
        args = split_action_args(m.group("args"))
    except ValueError as e:
        raise BuildError(f"{where}: 动作参数解析失败（{e}）: {action!r}") from e
    if kind == "replace":
        if not args:
            raise BuildError(f"{where}: json.replace 需要参数: {action!r}")
        if args[0].startswith("["):
            try:
                first = json.loads(args[0])
            except json.JSONDecodeError as e:
                raise BuildError(f"{where}: json.replace 数组不是合法 JSON（{e}）: {action!r}") from e
            if isinstance(first, list) and len(args) == 1 and len(first) == 2:
                # config 原文的单对形态 `replace(["Data.ActionUrl", ""])`（Plugin/qidian.plugin）。
                # 与批量形态共用同一条「键必须是点分路径、值只能是标量」校验。
                if not (isinstance(first[0], str) and DOT_PATH_RE.match(first[0])):
                    raise BuildError(f"{where}: json.replace 键名不是点分路径: {first[0]!r}")
                if isinstance(first[1], (list, dict)):
                    raise BuildError(
                        f"{where}: json.replace 的值不支持数组/对象（官方口径），置空数组用 json.jq: {first[1]!r}"
                    )
                return
            if len(args) != 2 or not args[1].startswith("["):
                raise BuildError(
                    f"{where}: json.replace 批量形态必须是两个等长平行数组 "
                    f"replace([k1,k2],[v1,v2])，得到 {args!r}"
                )
            try:
                keys, values = first, json.loads(args[1])
            except json.JSONDecodeError as e:
                raise BuildError(f"{where}: json.replace 数组不是合法 JSON（{e}）: {action!r}") from e
            if len(keys) != len(values):
                raise BuildError(
                    f"{where}: json.replace 平行数组长度不等 "
                    f"keys={len(keys)} values={len(values)}"
                )
            for k in keys:
                if not isinstance(k, str) or not DOT_PATH_RE.match(k):
                    raise BuildError(f"{where}: json.replace 键名不是点分路径: {k!r}")
            for v in values:
                if isinstance(v, (list, dict)):
                    raise BuildError(
                        f"{where}: json.replace 的值不支持数组/对象（官方口径），置空数组用 json.jq: {v!r}"
                    )
        else:
            if len(args) != 2:
                raise BuildError(f"{where}: json.replace 单键形态需要 (key, value): {args!r}")
            if not (args[0].startswith('"') and args[0].endswith('"')):
                raise BuildError(f"{where}: json.replace 键必须是双引号字符串: {args[0]!r}")
            if not SCALAR_JSON_RE.match(args[1]):
                raise BuildError(f"{where}: json.replace 值不是标量: {args[1]!r}")
    elif kind == "delete":
        if len(args) != 1:
            raise BuildError(f"{where}: json.delete 只接受一个参数（键或键数组）: {args!r}")
        arg = args[0]
        if arg.startswith("["):
            try:
                keys = json.loads(arg)
            except json.JSONDecodeError as e:
                raise BuildError(f"{where}: json.delete 键数组非法 JSON（{e}）") from e
            if not all(isinstance(k, str) and DOT_PATH_RE.match(k) for k in keys):
                raise BuildError(f"{where}: json.delete 键名不全是点分路径: {arg!r}")
        elif not (DOT_PATH_RE.match(arg.strip('"')) or arg.strip('"') == arg.rstrip('"')):
            raise BuildError(f"{where}: json.delete 键必须是点分路径字符串: {arg!r}")
    else:  # jq
        if len(args) != 1 or not (args[0].startswith('"') and args[0].endswith('"')):
            raise BuildError(f"{where}: json.jq 需要一个双引号表达式: {args!r}")
        if "`" in args[0]:
            raise BuildError(f"{where}: json.jq 表达式不许含反引号: {args[0]!r}")


def render_rewrite_rule(item: dict) -> str:
    """一条 active [Rewrite] 规则。开关前置成 `${gate} == true` 条件（插件参数在
    新语法里就是这么消费的；无 gate 的基础设施规则如 Accept-Encoding 降级只按 URL 匹配），
    正则按 Loon 字面量要求把裸 `/` 转义。"""
    cond = f'${{url}} ~= /{escape_regex_slashes(item["url"])}/'
    if item.get("gate"):
        cond = f'${{{item["gate"]}}} == true && {cond}'
    return f'{item["stage"]} if {cond} then {item["action"]}'


def validate_rewrite(enh: dict, where: str, names: list[str], bindings: list[dict]) -> list[str]:
    """active [Rewrite] 层的源侧校验：返回规则行（生成与 lint 共用同一份判定）。

    官方互斥口径（LOON-FEATURES §1.8）：Response Body Rewrite 命中 → Response Script
    不执行；Request 阶段终止响应 → 两侧脚本均不执行。所以「同一条 URL 既挂复写又挂
    脚本」默认是违规的——只有显式声明 `probe=true` 的绑定才允许被复写抑制，用作
    「复写到底命中没有」的锚定探针。
    """
    rules = enh.get("rewrite") or []
    if not rules:
        return []
    if enh.get("rewrite_json"):
        raise BuildError(
            f"{where}: enhance.rewrite（默认生效）与 rewrite_json（注释态基线）二选一，"
            "同端点两处声明必然漂移"
        )
    lines: list[str] = []
    touched_probe: set[str] = set()
    for item in rules:
        if not isinstance(item, dict):
            raise BuildError(f"{where}: enhance.rewrite 项必须是对象")
        rid = item.get("id", "?")
        where_i = f"{where}: rewrite[{rid}]"
        if not REWRITE_ID_RE.match(rid):
            raise BuildError(f"{where_i}: id 非法（kebab-case）: {rid!r}")
        stage = item.get("stage")
        if stage not in REWRITE_STAGES:
            raise BuildError(f"{where_i}: stage {stage!r} 不在 {sorted(REWRITE_STAGES)}")
        url, endpoint = item.get("url", ""), item.get("endpoint", "")
        # config 新语法复写不写 `^` 锚点（`${url} ~=` 是搜索语义）；本仓早期生成器
        # 强行给每条加了 `^`，与上游原文不一致。两种形态都接受，产物按源逐字渲染。
        if not url.startswith(("^https://", "https://")):
            raise BuildError(
                f"{where_i}: url 必须以 https://（config 原文）或 ^https:// 开头——"
                f"真机 HAR 里起点这些接口只有 HTTPS 形态: {url!r}"
            )
        try:
            re.compile(url)
        except re.error as e:
            raise BuildError(f"{where_i}: url 正则非法: {e}") from e
        if not endpoint or endpoint not in url.replace("\\.", "."):
            raise BuildError(
                f"{where_i}: endpoint {endpoint!r} 必须逐字出现在 url 正则里，"
                "否则互斥判定就是在比一个正则里没有的片段"
            )
        bare_url = url.replace("\\.", ".")
        if not any(".".join(h.split(".")[-2:]) in bare_url for h in enh.get("mitm_hosts", [])):
            raise BuildError(f"{where_i}: url 正则没覆盖任何 enhance.mitm_hosts（复写要先解密）")
        for key in ("note", "source"):
            if not item.get(key):
                raise BuildError(f"{where_i}: 缺 {key}（每条复写都要能自证出处）")
        gate = item.get("gate")
        action = item.get("action", "")
        is_req_header = REWRITE_REQ_HEADER_RE.match(action) is not None
        if gate is not None:
            if gate not in names:
                raise BuildError(f"{where_i}: gate {gate!r} 不在 enhance.arguments 里")
        if REWRITE_JSON_RE.match(action):
            if stage != "response":
                raise BuildError(f"{where_i}: response.json.* 只能挂在 response 侧")
            check_json_action(action, where_i)
        elif REWRITE_TERMINATE_RE.match(action):
            # reject_* 两阶段都合法：request 侧在出网前终止（两侧脚本都不执行），
            # response 侧只替换已经回来的响应（request 脚本照常执行）。
            # config 的起点插件刻意用 response 侧——保留上游验证过的交付语义。
            pass
        elif is_req_header:
            if stage != "request":
                raise BuildError(f"{where_i}: request.header.set 只能挂在 request 侧")
        else:
            raise BuildError(
                f"{where_i}: action 不在白名单（response.json.replace|delete|jq / "
                f"reject_dict|array|img|video / request.header.set Accept-Encoding）: {action!r}"
            )
        if not is_req_header:
            for b in bindings:
                if b.get("kind") not in ("request", "response"):
                    continue
                same_side = b["kind"] == stage
                kills_both = stage == "request" and REWRITE_TERMINATE_RE.match(action) is not None
                if not (same_side or kills_both):
                    continue
                if endpoint in b.get("pattern", ""):
                    if not b.get("probe"):
                        raise BuildError(
                            f"{where_i}: 端点 {endpoint!r} 同时被 [Script] 绑定 "
                            f"{b.get('id')!r}（{b['kind']}）覆盖——复写命中会静默压掉脚本。"
                            "要留它当探针就给绑定加 probe=true，否则把绑定删掉。"
                        )
                    touched_probe.add(b["id"])
        lines.append(render_rewrite_rule(item))
    for b in bindings:
        if b.get("probe") and b["id"] not in touched_probe:
            raise BuildError(
                f"{where}: 绑定 {b['id']!r} 标了 probe=true，但没有任何 enhance.rewrite "
                "规则命中它的端点——探针标记已失效，要么补规则要么去掉标记"
            )
    return lines


def rewrite_rule_lines(enh: dict, where: str) -> list[str]:
    """lint 对账入口：只返回应当逐字出现在产物 [Rewrite] 段里的规则行。"""
    names = [a.get("name") for a in enh.get("arguments") or []]
    return validate_rewrite(enh, where, names, enh.get("bindings") or [])


def render_rewrite_section(enh: dict, where: str) -> list[str]:
    """active [Rewrite] 段整段渲染（含段头说明与逐条注释）。"""
    rules = enh.get("rewrite") or []
    if not rules:
        return []
    stages = {item.get("stage") for item in rules}
    if stages == {"response"}:
        engine_note = [
            "# 由 Loon [Rewrite] v2 引擎直接执行：response 阶段 reject_* 在回包后就地返回",
            "# 合法空载荷，response.json.* 由引擎底层自动完成 gzip/br 解压与字段级改写",
            "# （不依赖脚本层 $utils.ungzip）；请求照常出网，保留上游验证过的交付语义。",
        ]
    elif stages == {"request"}:
        engine_note = [
            "# 由 Loon [Rewrite] v2 引擎直接执行：request 阶段 reject_dict/reject_img 在",
            "# 出网前就地返回合法空载荷，请求不再发出；本层不含响应体改写。",
        ]
    else:
        engine_note = [
            "# 由 Loon [Rewrite] v2 引擎直接执行：request 阶段 reject_* 在出网前就地返回",
            "# 合法空载荷；response 阶段 reject_* 与 response.json.* 在回包后由引擎完成解压",
            "# 与字段级改写（不依赖脚本层 $utils.ungzip）。",
        ]
    lines = [
        "",
        "# " + "=" * 72,
        "# 净化层主力：Loon 原生复写（enhance.rewrite 生成，lint 逐行对账）",
        "# " + "-" * 72,
        *engine_note,
        "# 探针纪律：若存在标了 probe=true 的同 URL [Script] 绑定，复写命中时按官方口径",
        "# 会静默抑制同阶段脚本，可据此在主日志里验证复写是否真实命中。",
        "# " + "=" * 72,
        "",
        "[Rewrite]",
        "",
    ]
    last_group = None
    for item in rules:
        group = item.get("group")
        if group and group != last_group:
            lines.append("# " + "-" * 60)
            lines.append(f"# {group}")
            lines.append("# " + "-" * 60)
            last_group = group
        elif group is None and last_group is not None:
            last_group = None
        lines.append(f'# {item["id"]}: {item["note"]}（来源 {item["source"]}）')
        lines.append(render_rewrite_rule(item))
        lines.append("")
    return lines


def render_arguments(enh: dict, where: str) -> list[str]:
    validate_enhance_active(enh, where)
    out = [
        "",
        "# " + "=" * 72,
        "# 开关（源：src/apps/<slug>.json 的 enhance.arguments；改开关改源后 npm run build:apps）",
        "# " + "-" * 72,
        "# 净化类默认开。自动化类的默认值是显式源内裁决（v3.6.0 起 QDREADER_* 六开关默认"
        "# 开——用户裁决接受服务端风控后果）；每个开关都仍可单独关掉切面停用。",
        "# " + "=" * 72,
        "",
        "[Argument]",
        "",
    ]
    for a in enh.get("arguments", []):
        out.append(render_argument_line(a))
    out.append("")
    return out


def render_active_layer(enh: dict, where: str, has_cron_section: bool) -> list[str]:
    """active 增强层的默认生效配置层：[MITM] hostname + [Rewrite] 复写 + [Script] 绑定。"""
    validate_enhance_active(enh, where)
    hosts = enh.get("mitm_hosts", [])
    out = [
        "",
        "# " + "=" * 72,
        "# 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）",
        "# " + "-" * 72,
        "# 不装证书 = 上述主机的 TLS 握手会被客户端拒绝，本 App 内容加载会失败——",
        "# 这是同域 HTTPS 路径拦截与 JSON 字段净化的必要前置（远程订阅插件无法手工取消",
        "# 注释，故在确认无证书固定后由源显式声明 active=true 默认启用）。",
        "# 若源里登记了注释态 URL-REGEX 路径黑洞，文末仍保持注释：红线业务主机只解密不整域黑洞。",
        "# " + "=" * 72,
        "",
        "[MITM]",
        "",
        f"hostname = {', '.join(hosts)}",
        "",
    ]
    out += render_rewrite_section(enh, where)
    bindings = enh.get("bindings") or []
    if bindings and not has_cron_section:
        out += [
            "# " + "=" * 72,
            "# 脚本层（绑定行由 enhance.bindings 生成，lint 逐行对账）",
            "# " + "-" * 72,
            "# 脚本绑定由 enhance.bindings 生成，lint 逐行对账。v2 内联绑定用",
            "# script(\"scripts/<name>.min.js\", {...})；config 范式的 vendored 引擎走旧式",
            "# 绑定（script-path=scripts/<name>.js），参数经 argument=[{NAME}] 传入。",
            "# 同 URL 的复写与脚本绑定按官方互斥语义注册（命中复写则同阶段脚本不执行）。",
            "# " + "=" * 72,
            "",
            "[Script]",
            "",
        ]
    for b in bindings:
        note = b.get("note")
        if note:
            out.append(f'# {b["id"]}: {note}')
        out.append(render_binding(b, enh.get("debug_arg") or "debugLog"))
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
    if active and not (url_rules or rewrite_json or scripts):
        return []
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
        out.append("# hostname = " + ", ".join(mitm_hosts))
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
                f" then response.json.jq({json.dumps(item['jq'], ensure_ascii=False)})"
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
