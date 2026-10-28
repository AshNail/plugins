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
  不生成 [MITM]/[Script]/[Rewrite]——这些插件服务银行与业务敏感 App，零证书是底线。
- 例外：未做证书固定的 App 可带 `enhance` 可选增强层——**整段注释**输出
  （[MITM] hostname + URL-REGEX 路径规则），默认零证书不变，用户装证书后自行取消注释；
  每条路径规则必须附公开可引用 sources，禁止凭空造路径。
- 禁用 DOMAIN-WILDCARD：该语法仅 3.5.3(1008) TestFlight 提供，app 插件必须
  让 App Store 正式版（3.5.2/996）用户可直接导入；通配一律走 [Host] '*.domain'。
- #!loon_version 不得高于 App Store 正式版 build（APPSTORE_STABLE_BUILD）。
- 通配 glob 与精确域都不得命中 src/ads/protected-roots.json 里的共享主域。
- 每个组带 tier（证据分级 A/B/C）与 sources（证据 URL），C 级组默认注释。
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
APPS = ROOT / "src/apps"
ADS_ROOTS = ROOT / "src/ads/protected-roots.json"

HOST_BLACKHOLE = "127.0.0.1"
# App Store 正式版基线（Loon 3.5.2 build 996，官方文档 server-dns 条目佐证）。
# 插件头 loon_version 高于此 = 正式版用户无法导入，永久禁止。
APPSTORE_STABLE_BUILD = 996
DEFAULT_SYSTEM = "iOS,iPadOS,tvOS,macOS"
DEFAULT_ICON = "https://cdn.adguard.com/public/Adguard/Common/logo.png"
DOMAIN_RE = re.compile(r"^(?:\*\.)?[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)+$")
WILDCARD_GLOB_RE = re.compile(r"^[a-z0-9*?\[\]!.-]+$")
RULE_KINDS = {"DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}
ACTIONS = {"REJECT", "REJECT-DROP"}
KEY_ORDER = ("name", "desc", "author", "version", "homepage", "openUrl", "icon",
             "system", "loon_version", "date", "tag", "type")


class BuildError(Exception):
    pass


def load_json(path: pathlib.Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_roots() -> set[str]:
    data = load_json(ADS_ROOTS)
    roots = set()
    for item in data if isinstance(data, list) else data.get("roots", []):
        roots.add(item if isinstance(item, str) else item["domain"])
    return roots


def build_number(version: str) -> int:
    m = re.search(r"\((\d+)\)", version)
    return int(m.group(1)) if m else 0


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


def render(app: dict, sdklib: dict, roots: set[str]) -> str:
    slug = app["slug"]
    where = f"src/apps/{slug}.json"
    groups = collect_groups(app, sdklib)
    hosts: list[str] = []
    rules: list[str] = []
    for g in groups:
        for h in g["hosts"]:
            validate_host(h, f"{where}:{g.get('id', '?')}", roots)
        for r in g["rules"]:
            validate_rule(r, f"{where}:{g.get('id', '?')}", roots)
        hosts += g["hosts"]
        rules += g["rules"]

    has_wildcard = any(r.startswith("DOMAIN-WILDCARD,") for r in rules)
    loon_version = app.get("loonVersion", "3.5.1(983)")
    if has_wildcard:
        raise BuildError(f"{where}: DOMAIN-WILDCARD 语法仅 3.5.3(1008) TestFlight 提供，"
                         "App Store 正式版（3.5.2/996）无法保证解析——"
                         "app 插件一律改用 [Host] '*.domain' 通配黑洞")
    if build_number(loon_version) > APPSTORE_STABLE_BUILD:
        raise BuildError(f"{where}: loonVersion={loon_version!r} 高于 App Store 正式版 "
                         f"build {APPSTORE_STABLE_BUILD}，正式版用户将无法导入")

    meta = {
        "name": app["name"],
        "desc": app["desc"],
        "author": app.get("author", "edy"),
        "version": app["version"],
        "homepage": app.get("homepage", "https://github.com/AshNail/plugins"),
        "openUrl": app.get("openUrl", f"https://github.com/AshNail/plugins/blob/main/plugins/{slug}/README.md"),
        "icon": app.get("icon", DEFAULT_ICON),
        "system": app.get("system", DEFAULT_SYSTEM),
        "loon_version": loon_version,
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

    if rules:
        lines += section("Rule", rules, lambda r: r)
    lines += section("Host", hosts, lambda h: h + f" = {HOST_BLACKHOLE}")

    enh = app.get("enhance")
    if enh:
        lines += render_enhance(enh, where, roots)
    return "\n".join(lines).rstrip("\n") + "\n"


def render_enhance(enh: dict, where: str, roots: set[str]) -> list[str]:
    """可选 MITM 增强层：整段注释输出。

    只对未做证书固定的 App 有效；启用需要用户先装并信任 Loon 证书，再逐行取消
    注释。因为默认全注释，插件头仍是纯 rule/host 零证书形态，lint 的段白名单不受
    影响（注释头不会被解析成 section）。这里的每条 URL-REGEX/脚本都必须来自
    公开可引用的规则源（enhance.sources），不凭空造路径。
    """
    mitm_hosts = enh.get("mitm_hosts", [])
    url_rules = enh.get("url_regex", [])
    scripts = enh.get("scripts", [])
    if not (mitm_hosts or url_rules or scripts):
        raise BuildError(f"{where}: enhance 存在但三段全空")
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
    out = [""]
    out.append("# " + "=" * 72)
    out.append("# 可选 MITM 增强层（下面整段默认注释；不装证书 = 永不生效）")
    out.append("# " + "-" * 72)
    for note in enh.get("intro", "").splitlines():
        out.append(f"# {note}")
    out.append("# 启用步骤：①Loon 里装并信任证书 → ②取消 [MITM] 头与其 hostname 行的注释 →")
    out.append("#           ③按需取消下面 [Rule]/[Script] 行的注释。")
    out.append("# 只对未做证书固定的 App 有效；银行/微信/米家这类做了证书固定，")
    out.append("# MITM 直接失败甚至触发风控——那些插件不提供本层（红线）。")
    out.append("# 本层每一条正则都来自公开可引用规则源，见下方证据；不凭空造路径。")
    for src in enh.get("sources", []):
        out.append(f"# 证据: {src}")
    out.append("# " + "=" * 72)
    out.append("")
    if mitm_hosts:
        out.append("# [MITM]")
        out.append("# " + "-" * 60)
        out.append("# hostname 只列本 App 广告相关的具体接口域，不列整主域；一行取消注释即全部解密。")
        out.append("# hostname = %APPEND% " + ", ".join(mitm_hosts))
    if url_rules or scripts:
        out.append("# [Rule] / [Script]（路径级去广告，需上面 MITM 命中该域才看得到 path）")
        out.append("# " + "-" * 60)
        for r in url_rules:
            out.append(f"# {r}")
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
