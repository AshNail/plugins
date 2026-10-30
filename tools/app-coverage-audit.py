#!/usr/bin/env python3
"""App 插件覆盖率审计：拿成熟黑名单反查每个 src/apps/<slug>.json 漏了哪些广告域。

只读；不改动任何源文件。缓存复用 .cache/ads-audit（由 tools/ads-audit.py 管理）。
候选 = 出现在上游清单、含 App 品牌 token、且未被 (本 App 插件 ∪ ads.plugin 生效行) 覆盖的域。
按命中清单数排序：>=3 源 A 级候选，2 源 B，1 源 C。

用法:
  python3 tools/app-coverage-audit.py            # 离线用缓存
  python3 tools/app-coverage-audit.py --refresh  # 重新下载上游
  python3 tools/app-coverage-audit.py --write    # 写 docs/app-coverage.md（生成物）
  python3 tools/app-coverage-audit.py --check    # 生成物漂移门禁
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

_spec = importlib.util.spec_from_file_location("ads_audit", ROOT / "tools/ads-audit.py")
aa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aa)

# 每个 slug 的品牌正则（在域名全串上 search）；过宽的 registrable root 由 EXCLUDE_ROOTS 挡
PATTERNS: dict[str, re.Pattern] = {
    "qidian": re.compile(r"(^|\.)qidian\.|(^|\.)yuewen\.|qidianad|(^|\.)1ting|tingbook"),
    "wechat": re.compile(r"wxsns|wxsms|wxa\.wxs|wximg\.wxs|wxsmw\.wxs|(^|\.)pgdt\.|gdtimg|(^|\.)qzs\.qq|app-support\.qq|adinall|(^|\.)17g57|zhizi\.qq|xmaterial\.tu\.qq|weixinbridge"),
    "meituan": re.compile(r"(^|\.)meituan\.|(^|\.)sankuai\.|(^|\.)dianping\.|(^|\.)dpfile\.|(^|\.)51ping\."),
    "xianyu": re.compile(r"goofish|idlefish|iyes\.|idle\w*\.(taobao|tmall)\."),
    "banks": re.compile(r"cmbchina|paas\.cmb|cup\.com\.cn|95516|(^|\.)abchina|bocstyle|bsbcdn|(^|\.)boc\.cn|(^|\.)spdb|ecitic|creditcard\.cib|(^|\.)cqcb"),
    "mijia": re.compile(r"xiaomi|(^|\.)mi\.com|(^|\.)miui\.|mistat|adup-xlg|(^|\.)devmi|(^|\.)mi\.cc|shunmi|mijia"),
    "x": re.compile(r"twitter|ads-\w*\.twitter|(^|\.)x\.com"),
    "instagram": re.compile(r"instagram|netseer|(^|\.)pixel\.facebook|(^|\.)an\.facebook|ads\..*facebook"),
    "ruankao-tong": re.compile(r"ruankao|skyvane|(^|\.)51top\."),
    "mba-dashi": re.compile(r"mba168|mbachina|(^|\.)smba"),
    "bubei-danci": re.compile(r"bubei|(^|\.)5cd\.|(^|\.)notword|(^|\.)wanbang|langeasy"),
    "zhihuifangdong": re.compile(r"fangdd|zhihuifangdong|loofz|ttlock"),
    "jd": re.compile(r"(^|\.)jd\.com(\.|$)|(^|\.)360buy(img)?\.com|(^|\.)jd\.hk(\.|$)|(^|\.)jdx\.com|(^|\.)jingxi\.com"),
}

# 品牌根域白名单：候选的 registrable root 必须属于 App 主体（拒掉 typosquat/第三方站点/社区站）
BRAND_ROOTS: dict[str, set[str]] = {
    "qidian": {"qidian.com", "yuewen.com", "qidianad.com", "1ting.com", "tingbook.com"},
    "wechat": {"qq.com", "weixin.qq.com", "gtimg.cn", "adinall.com", "17g57.com"},
    "meituan": {"meituan.com", "meituan.net", "dianping.com", "dpfile.com", "sankuai.com", "51ping.com", "meituan-dianping.net"},
    "xianyu": {"goofish.com", "idlefish.com", "youku.com", "taobao.com", "tmall.com", "alimama.com"},
    "banks": {"cmbchina.com", "cup.com.cn", "95516.com", "abchina.com", "boc.cn", "bocstyle.com",
              "bsbcdn.cn", "spdb.com.cn", "spdbccc.com.cn", "ecitic.com", "cqcb.com", "cib.com.cn", "unionpay.com"},
    "mijia": {"xiaomi.com", "xiaomi.net", "mi.com", "miui.com", "miaozhen.com", "shunmi.com", "mi.cc", "adup-xlg.com"},
    "x": {"twitter.com", "ads-twitter.com", "x.com"},
    "instagram": {"instagram.com", "facebook.com", "fbcdn.net", "netseer.com"},
    "ruankao-tong": {"ruankao.org.cn", "skyvane.com", "51top.com", "ruankao.com"},
    "mba-dashi": {"mba168.net", "mba168.com", "mbachina.com"},
    "bubei-danci": {"bubei.com", "bubei.com.cn", "5cd.com", "wanbang.com", "langeasy.cn", "langeasy.com"},
    "zhihuifangdong": {"ttlock.com", "loofz.com", "fangdd.com", "zhihuifangdong.com"},
    "jd": {"jd.com", "360buyimg.com", "360buy.com", "jd.hk", "jdx.com", "jingxi.com"},
}

# 整 root 不进候选（共享主域/CDN/网关，命中再多也不是「广告专用域」）
EXCLUDE_ROOTS = {
    "qq.com", "weixin.qq.com", "gtimg.com", "gtimg.cn", "sina.com.cn",
    "taobao.com", "tmall.com", "alicdn.com", "tbcdn.cn", "alipay.com", "aliyun.com",
    "meituan.net", "meituan.com", "dianping.com",  # 子域允许，但 root 本身绝不
    "xiaomi.com", "mi.com", "miui.com",
    "twitter.com", "x.com", "t.co", "facebook.com", "instagram.com", "fbcdn.net",
    "qidian.com", "yuewen.com", "boc.cn", "abchina.com", "cmbchina.com", "spdb.com.cn",
    "jd.com", "360buyimg.com", "360buy.com", "jd.hk",
}
# root 本身排除，但其广告向子域仍可进候选（用 token 再筛一层）
ROOT_AD_HINT = {
    "meituan.com": re.compile(r"ad|mads|impdsp|report|log|stat|dpfile|union"),
    "meituan.net": re.compile(r"ad|report|log|stat|d\.|mcdn"),
    "dianping.com": re.compile(r"ad|cat|report|stat|log"),
    "qidian.com": re.compile(r"ad|adv|stat|track|log|tongji|qdp|dw"),
    "xiaomi.com": re.compile(r"ad|stat|mistat|tracking|push|devmi"),
    "mi.com": re.compile(r"ad|stat|tracking"),
    "twitter.com": re.compile(r"ad|pixel|scribe|analytics|syndication"),
    "x.com": re.compile(r"^ads"),
    "facebook.com": re.compile(r"ad|pixel|an\.|audience|netseer"),
    "boc.cn": re.compile(r"ad|log|stat|track|marketing"),
    "cmbchina.com": re.compile(r"ad|log|stat|track|marketing"),
    "abchina.com": re.compile(r"ad|log|stat|track|marketing|abcd"),
    "spdb.com.cn": re.compile(r"ad|log|stat|track|marketing"),
    "jd.com": re.compile(r"ad|union|dsp|x\.|ccc|click|log|stat|track|monitor|cm\.|du\.|firevent|nfa|jcm|jrad|sgm|knicks|orbit|cactus|jpush|chat|dns|h5speed|blackhole|policy|dgstatic|wl\.|gia|img|mercur|uranus|hermes|janapi|mapi|kepler|jrclick|cps|passport|appsec"),
    "360buyimg.com": re.compile(r"img"),
    "360buy.com": re.compile(r"cps|union"),
    "jd.hk": re.compile(r"."),
}

ADBLOCK_RE_EXTRA = re.compile(r"^\|\|([^/*^$]+)\^?", re.IGNORECASE)


# 上游黑名单清单（README 里「N 家上游黑名单」的机器出处，lint 直接 import 这个常量核对）。
SOURCE_NAMES = aa.DEFAULT_SOURCES + ["adguard-cn", "adguard-mobile", "easyprivacy", "hagezi-xiaomi"]


def load_sources(refresh: bool, offline: bool):
    by_domain: dict[str, set[str]] = {}
    for name in SOURCE_NAMES:
        try:
            doms = aa.fetch_source(name, aa.SOURCES[name], refresh, offline)
        except Exception as e:
            aa.log(f"skip {name}: {e}")
            continue
        for d in doms:
            by_domain.setdefault(d, set()).add(name)
    return by_domain


def parse_rule_line(line: str):
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 3:
        return None
    kind = parts[0].strip()
    value = ",".join(parts[1:-1]).strip()
    action = parts[-1].strip()
    if action not in ("REJECT", "REJECT-DROP"):
        return None
    return kind, value


def active_rules(path: pathlib.Path):
    """返回 (suffixes, keywords, wildcard_globs, hosts_exact, hosts_wild, disabled_hosts)——只数生效行。"""
    suffixes, keywords, globs, h_exact, h_wild, h_disabled = set(), set(), [], set(), set(), set()
    section = None
    for line in path.read_text().splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1]
            continue
        if s.startswith("#") and section in ("Host", "Rule"):
            body = s.lstrip("#").strip()
            if section == "Host" and "=" in body:
                host = body.split("=")[0].strip()
                h_disabled.add(host[2:].lower() if host.startswith("*.") else host.lower())
            continue
        if not s or s.startswith(";"):
            continue
        if section == "Host" and "=" in s:
            host = s.split("=")[0].strip()
            if host.startswith("*."):
                h_wild.add(host[2:])
            else:
                h_exact.add(host)
        elif section == "Rule":
            parsed = parse_rule_line(s)
            if not parsed:
                continue
            kind, value = parsed
            if kind == "DOMAIN-SUFFIX":
                suffixes.add(value.lower())
            elif kind == "DOMAIN-KEYWORD":
                keywords.add(value.lower())
            elif kind == "DOMAIN-WILDCARD":
                globs.append(aa_globs(value))
    return suffixes, keywords, globs, h_exact, h_wild, h_disabled


def aa_globs(glob: str):
    return glob.lower()


def covered(d: str, suffixes, keywords, globs, h_exact, h_wild, extra_exact=None) -> bool:
    if extra_exact is None:
        extra_exact = set()
    if d in h_exact or d in extra_exact or d in suffixes:
        return True
    parts = d.split(".")
    for i in range(1, len(parts)):
        anc = ".".join(parts[i:])
        if anc in h_wild or anc in suffixes:
            return True
    if any(k in d for k in keywords):
        return True
    for g in globs:
        rx = aa_glob_regex(g)
        if rx and rx.fullmatch(d):
            return True
    return False


def aa_glob_regex(glob: str):
    # 与 build-apps 相同的 * ? [...] 转换
    out, i = [], 0
    while i < len(glob):
        c = glob[i]
        if c == "*":
            out.append(".*")
        elif c == "?":
            out.append(r"[^.]")
        elif c == "[":
            j = glob.find("]", i)
            if j < 0:
                return None
            cls = glob[i + 1 : j]
            neg = cls.startswith("!")
            if neg:
                cls = cls[1:]
            cls = cls.replace("&", "")
            out.append("[^" + re.escape(cls).replace(r"\-", "-") + "]" if neg else "[" + re.escape(cls).replace(r"\-", "-") + "]")
            i = j
        else:
            out.append(re.escape(c))
        i += 1
    try:
        return re.compile("".join(out))
    except re.error:
        return None


def registrable(d: str) -> str:
    parts = d.split(".")
    if len(parts) >= 3 and parts[-2] in ("com", "net", "org", "cn", "cc", "me", "gov", "edu"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def load_triage(app: dict, slug: str) -> list[tuple[str, list[str]]]:
    """App JSON 的 triage_exclude：已裁决排除的域族（安全/推送/业务），命中不算缺口。"""
    ledger = []
    for ent in app.get("triage_exclude", []):
        label = ent.get("label", "").strip()
        globs = [g.lower() for g in ent.get("globs", []) if g.strip()]
        if not label or not globs:
            raise SystemExit(f"apps/{slug}: triage_exclude entry needs non-empty label+globs")
        ledger.append((label, globs))
    return ledger


def audit(by_domain, offline_note):
    ads_path = ROOT / "plugins/ads/ads.plugin"
    a_suf, a_kw, a_gl, a_he, a_hw, _a_dis = active_rules(ads_path)
    results = {}
    for path in sorted((ROOT / "src/apps").glob("*.json")):
        slug = path.stem
        if slug.startswith("_"):
            continue
        app = json.loads(path.read_text())
        plug = ROOT / "plugins" / slug / f"{slug}.plugin"
        if plug.exists():
            p_suf, p_kw, p_gl, p_he, p_hw, p_dis = active_rules(plug)
        else:
            p_suf, p_kw, p_gl, p_he, p_hw, p_dis = set(), set(), [], set(), set(), set()
        sdk_hosts = set()
        lib = json.loads((ROOT / "src/apps/_sdk.json").read_text())["sdks"]
        ads_groups = {g.get("id"): g for g in json.loads((ROOT / "src/ads/domains.json").read_text())["plugins"]["ads"]["groups"]}
        for sid in app.get("sdks", []):
            meta = lib.get(sid, {})
            if meta.get("adsGroup") and meta["adsGroup"] in ads_groups:
                for e in ads_groups[meta["adsGroup"]].get("rules", []):
                    if "," not in e:
                        sdk_hosts.add(e.lstrip("*=").lower())
                    else:
                        parts = [p.strip() for p in e.split(",")]
                        if parts[0] == "DOMAIN-SUFFIX":
                            suffixes_add = parts[1].lower()
                            p_suf.add(suffixes_add)
        pat = PATTERNS.get(slug)
        triage = load_triage(app, slug)
        cands = []
        if pat:
            for d, lists in by_domain.items():
                if not pat.search(d):
                    continue
                root = registrable(d)
                allow = BRAND_ROOTS.get(slug)
                if allow and root not in allow:
                    continue
                if d == root and root in EXCLUDE_ROOTS:
                    continue
                hint = ROOT_AD_HINT.get(root)
                if root in EXCLUDE_ROOTS and hint and not hint.search(d):
                    continue
                if covered(d, p_suf | a_suf, p_kw | a_kw, p_gl + a_gl, p_he | a_he | sdk_hosts, p_hw | a_hw):
                    continue
                off = any(d == h or d.endswith("." + h) for h in (p_dis | _a_dis))
                why = next((label for label, globs in triage
                            if any(fnmatch.fnmatchcase(d, g) for g in globs)), "")
                cands.append((len(lists), d, sorted(lists), off, why))
            cands.sort(key=lambda x: (-x[0], x[1]))
        own = len(p_he | p_hw)
        results[slug] = {"own_hosts": own, "candidates": cands, "triage": triage}
    return results


def render_md(results, source_note):
    lines = [
        "# App 插件覆盖率审计（生成物）",
        "",
        f"> 由 `python3 tools/app-coverage-audit.py --write` 生成（{source_note}）。",
        "> 候选 = 上游黑名单收录、含 App 品牌 token、且未被「本 App 插件 ∪ ads.plugin 生效行」覆盖的域。",
        "> **候选≠必拦**：逐条人工定级后才进 `src/apps/`。A=≥3 源独立收录；B=2 源；C=单源（默认不收）。",
        "> 命中 App JSON 里 `triage_exclude` 台账的候选记为「排除·<族>」，不计入缺口——**排除是裁决，不是待办**。",
        "",
    ]
    for slug, r in results.items():
        c3 = [c for c in r["candidates"] if c[0] >= 3]
        c2 = [c for c in r["candidates"] if c[0] == 2]
        c1 = [c for c in r["candidates"] if c[0] == 1]
        off = sum(1 for c in c3 + c2 if c[3])
        gap3 = [c for c in c3 if not c[3] and not c[4]]
        gap2 = [c for c in c2 if not c[3] and not c[4]]
        excl = sum(1 for c in c3 + c2 if not c[3] and c[4])
        lines += [
            f"## `{slug}` — 生效黑洞 {r['own_hosts']} 域；缺口候选 A:{len(gap3)} B:{len(gap2)} C:{len(c1)}"
            f"（已裁决排除 {excl} 条；已收录但默认关闭 {off} 条）",
            "",
        ]
        if not c3 and not c2:
            lines.append("无 A/B 级缺口候选。")
            lines.append("")
            continue
        if c3:
            lines += ["| A 候选（≥3 源） | 源 | 状态 |", "|---|---|---|"]
            for n, d, ls, isoff, why in c3[:40]:
                status = "已收录·默认关" if isoff else (f"排除·{why}" if why else "缺口")
                lines.append(f"| `{d}` | {n}: {','.join(ls)} | {status} |")
            lines.append("")
        if c2:
            lines += ["| B 候选（2 源） | 源 | 状态 |", "|---|---|---|"]
            for n, d, ls, isoff, why in c2[:25]:
                status = "已收录·默认关" if isoff else (f"排除·{why}" if why else "缺口")
                lines.append(f"| `{d}` | {n}: {','.join(ls)} | {status} |")
            lines.append("")
        if r.get("triage"):
            lines.append("裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：")
            for label, globs in r["triage"]:
                lines.append(f"- `{label}` ← " + ", ".join(f"`{g}`" for g in globs))
            lines.append("")
    lines += [
        "## 排除口径",
        "",
        "- 共享主域 root 本身绝不进候选；root 子域需再命中「广告向 hint 词」才有资格（防止把业务子域当缺口）。",
        "- 已被 ads.plugin 生效规则（含通配/关键词/SUFFIX）覆盖的不算缺口。",
        "- `triage_exclude`：App JSON 里的裁决台账（安全/推送/账号云/遥测/业务 API），命中的候选只展示、不计缺口。",
        "- C 级候选默认忽略；出现设备日志证据后再单独升级。",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    note = "缓存快照" if not args.refresh else "上游已刷新"
    by_domain = load_sources(args.refresh, args.offline)
    if not by_domain:
        message = (
            "app-coverage: no source list loaded (cache missing under --offline); "
            "run without --offline to fetch"
        )
        if args.check:
            print(f"app-coverage skipped: {message}")
            return
        if args.write:
            raise SystemExit(message)
        aa.log(message)
    results = audit(by_domain, note)

    out = ROOT / "docs/app-coverage.md"
    md = render_md(results, note)
    if args.check:
        if not out.exists() or out.read_text() != md:
            print("app-coverage doc is stale: run `python3 tools/app-coverage-audit.py --write`", file=sys.stderr)
            sys.exit(1)
        print("app-coverage ok")
        return
    if args.write:
        out.write_text(md)
        print(f"wrote {out}")
    for slug, r in results.items():
        a = [c for c in r["candidates"] if c[0] >= 3]
        b = [c for c in r["candidates"] if c[0] == 2]
        gaps = [c for c in a + b if not c[3] and not c[4]]
        aa.log(f"{slug:16} own={r['own_hosts']:4} A-cand={len(a):3} B-cand={len(b):3} gaps={len(gaps):3}")
        for n, d, ls, isoff, why in a[: args.top]:
            tag = " [已默认关]" if isoff else (f" [排除·{why}]" if why else "")
            aa.log(f"    A {d:55} {n} sources{tag}: {','.join(ls)}")


if __name__ == "__main__":
    main()
