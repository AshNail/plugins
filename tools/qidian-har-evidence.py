#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""起点读书真机抓包证据：把「规则写了」和「规则真的在跑」分开。

本轮（2026-11-10，HAR 466_1794290256836）拿到的不是普通 HAR：Loon 在每条
entry 上附了 `_loon` 与 `response._loonOriginal` 两个私有字段——

  * `_loon.rewrite`     这条请求**实际命中**的 [Rewrite] 规则全文；
  * `_loon.script`      实际触发的 [Script] 绑定；
  * `modifiedResponse`  引擎有没有真的改过回包；
  * `_loonOriginal.content.text`  改包**之前**的服务端原文。

于是「规则有效率」不再靠推演：response.content 是复写之后 App 收到的内容，
`_loonOriginal` 是原文，两者一减就是改包的真实效果。特别注意一个反向陷阱——
回包里**看不到**某个字段，可能是它本来就没有，也可能是被复写删掉了；
只拿改写后的 body 判断「规则空转」会把有效规则误删。

本工具做三件事：

  1. `--extract <har>` 从 HAR 生成精简证据快照（提交进仓库，不依赖用户 Downloads）；
  2. `--check` 用快照反向钉住 `src/apps/qidian.json`：零命中的端点不许留、
     红框字段必须被覆盖、业务/激励字段不许被删、每条规则要自证证据等级；
  3. 无参数打印人读报表。

纪律（与前几轮一致）：允许「兜底 / 存疑 / 待真机」存在，但禁止沉默。
服务端当前返回空数组、因此改包没有可见效果的规则，必须标 `fallback-empty`
并写明真机怎么证伪；不允许把「命中了」当成「有效果了」写进报表。

退出码：0 通过；1 断言失败或快照与规则漂移。
"""

import argparse
import base64
import collections
import copy
import json
import os
import re
import subprocess
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(ROOT, "tests", "fixtures", "qidian-har-20261110.json")
CONFIG = os.path.join(ROOT, "src", "apps", "qidian.json")
HAR_NAME = "466_1794290256836.har"
LOG_NAME = "2026-11-10 14.log"

# 真机从未出现过的端点（零命中）；删掉后不许静默加回来。
DEAD_ENDPOINTS = {
    "push/getdialog",
    "maintain/playstrip",
    "followsubscribe/showChapterEndModule",
    "checkin/lottery",
    "booksearch/hotWords",
    "message/pull(Operation|Social)Push",
    "video/adv/reportDialog",
    "video/adv/mainPageDialog",
}
# 功能面 / 保护面：整条 reject_dict 会打断签到、兑换、青少年模式、每日导读。
PROTECTED_ENDPOINTS = (
    "checkin/simpleinfo",
    "checkin/checkinexchangepage",
    "checkin/lottery",
    "young/getconf",
    "dailyrecommend/",
)
# 用户裁决（2026-11-10，HAR 465）保留：每日导读不清空、不改写。
PRESERVED = [
    "dailyrecommend/getdailyrecommend（用户裁决保留每日导读，v4.0.3 已恢复 Items）",
    "widget/daily/rec（每日导读正文，放行）",
    "checkin/checkinexchangepage 的 Data.Goods（章节卡兑换货架，激励出口）",
    "user/getaccountpage 的 Data.UserBasicInfo / Data.AccountBalance（身份与账户）",
]
UNRESOLVED = [
    "HAR 466 抓的是 v4.0.2 插件在跑；v4.0.3/本轮规则尚未真机回抓，命中数由 URL 正则模拟得出。",
    "顶部 banner 的文案「必看神作/最低折扣」是图片（MainInfo.BgImg/TitleImg），HAR 正文搜不到，靠 AdvId 与图片字段定位。",
    "红色箭头指向的「每日导读」条按用户上一轮裁决保留；若真机仍想删，需先抓到它的驱动字段再动手。",
    "深度净化 [Script] 在 HAR 中触发 43 次、其中 49 条 entry 记录 Script evaluate failed；CAPTURE_ENABLE=true 时主通道是 [Rewrite]，失败原因待真机复现。",
    "Loon 内置 jq 与本机 /usr/bin/jq 的语义差异仍待真机验证（沿用第三轮取证项）。",
]


def body_text(container):
    """从 HAR 的 response / _loonOriginal 里取解码后的 body 文本。"""
    content = (container or {}).get("content") or {}
    text = content.get("text")
    if not text:
        return ""
    if content.get("encoding") == "base64":
        try:
            text = base64.b64decode(text).decode("utf-8", "replace")
        except (ValueError, UnicodeDecodeError):
            return ""
    return text


def as_json(text):
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def path_of(url):
    return urllib.parse.urlsplit(url).path


SENSITIVE_KEY = re.compile(
    r"^(UserId|NickName|Head|Avatar|Guid|EncryptedGuid|Token|Cookie|Qimei|"
    r"DeviceId|Phone|Mobile|cmfuToken|YWOpenUserId|TTSUserId|ShareUserCode)$", re.I
)
SAMPLE_ENDPOINTS = (
    "bookshelf/getTopOperation",
    "user/getaccountpage",
    "adv/getadvlistbatch",
    "bookshelf/getad",
    "checkin/checkinexchangepage",
    "user/getsimplediscover",
    "popup/batchget",
    "reddot/getdot",
    "bookshelf/getHoverAdv",
)


def scrub(value):
    """删掉身份/凭据类字段：快照要能提交进仓库，但净化断言不依赖这些值。"""
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items() if not SENSITIVE_KEY.match(k)}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def extract(har_path):
    with open(har_path, encoding="utf-8") as handle:
        har = json.load(handle)
    entries = har["log"]["entries"]

    # 快照只收起点自域 URL：规则正则本来就只打这两个域，且能顺手排除
    # HAR 里那条带 X-Amz-Signature 的第三方上传直链。
    urls = []
    for item in entries:
        url = item["request"]["url"]
        if "qidian.com" in url or "yuewen.com" in url:
            urls.append(url)

    observed = collections.Counter()
    scripts = collections.Counter()
    failed = 0
    modified = 0
    effects = []
    samples = {}
    for idx, item in enumerate(entries):
        meta = item.get("_loon") or {}
        path = path_of(item["request"]["url"])
        if meta.get("modifiedResponse"):
            modified += 1
        for rule in meta.get("rewrite") or []:
            observed[rule] += 1
        for name in meta.get("script") or []:
            scripts[name] += 1
        if "Script evaluate failed" in (meta.get("log") or ""):
            failed += 1
        # 净化作用于服务端原文，所以样本优先取 _loonOriginal；没有改包记录时
        # response.content 本身就是原文。
        for fragment in SAMPLE_ENDPOINTS:
            if fragment in path and fragment not in samples:
                source = item["response"].get("_loonOriginal") or item["response"]
                payload = as_json(body_text(source))
                if isinstance(payload, dict):
                    samples[fragment] = scrub(payload)
        original = item["response"].get("_loonOriginal")
        if not original or "/argus/api/" not in path:
            continue
        before = as_json(body_text(original))
        after = as_json(body_text(item["response"]))
        if not (isinstance(before, dict) and isinstance(after, dict)):
            continue
        old, new = before.get("Data"), after.get("Data")
        if isinstance(old, dict) and isinstance(new, dict):
            removed = sorted(set(old) - set(new))
            changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
        else:
            removed = []
            changed = [] if old == new else ["Data"]
        effects.append({
            "entry": idx,
            "path": path,
            "removed": removed,
            "changed": changed,
        })

    # 红框 / 业务字段的实证：只存字段名与可公开的文案，不落用户昵称、UserId、头像。
    by_path = {}
    for item in entries:
        path = path_of(item["request"]["url"])
        if path in by_path:
            continue
        payload = as_json(body_text(item["response"]))
        if isinstance(payload, dict):
            by_path[path] = payload.get("Data")

    def data_of(fragment):
        for path, value in by_path.items():
            if fragment in path:
                return value
        return None

    top = data_of("bookshelf/getTopOperation") or {}
    account = data_of("user/getaccountpage") or {}
    adv = data_of("adv/getadvlistbatch") or {}
    game = data_of("bookshelf/getad") or {}
    exchange = data_of("checkin/checkinexchangepage") or {}
    ui_evidence = {
        "bookshelf_banner": {
            "endpoint": "bookshelf/getTopOperation",
            "fields": ["Data.MainInfo", "Data.Items"],
            "main_adv_id": (top.get("MainInfo") or {}).get("AdvId"),
            "item_adv_ids": [x.get("AdvId") for x in (top.get("Items") or [])],
            "item_count": len(top.get("Items") or []),
            "note": "MainInfo=顶部大横幅（BgImg/TitleImg 图片），Items=横幅右侧三枚小图标（含游戏手柄）",
        },
        "account_page": {
            "endpoint": "user/getaccountpage",
            "data_keys": sorted(account.keys()) if isinstance(account, dict) else [],
            "member_title": (account.get("Member") or {}).get("Title"),
            "function_buttons": [x.get("Name") for x in (account.get("FunctionButtonList") or [])],
            "bottom_buttons": [x.get("Name") for x in (account.get("BottomButtonList") or [])],
            "school_text": account.get("SchoolText"),
        },
        "account_page_ads": {
            "endpoint": "adv/getadvlistbatch",
            "keys": sorted(adv.keys()) if isinstance(adv, dict) else [],
            "texts": [x.get("ADText") for bucket in ("iosusercenter", "iosusercenter2")
                      for x in (adv.get(bucket) or [])],
        },
        "shelf_game": {
            "endpoint": "bookshelf/getad",
            "keys": sorted(game.keys()) if isinstance(game, dict) else [],
            "show": game.get("Show"),
        },
        "exchange_goods": {
            "endpoint": "checkin/checkinexchangepage",
            "goods_count": len((exchange or {}).get("Goods") or []),
            "note": "章节卡兑换货架，用户激励出口，禁止清空",
        },
    }

    snapshot = {
        "schema": 1,
        "source": {
            "har": HAR_NAME,
            "log": LOG_NAME,
            "entries": len(entries),
            "qidian_url_entries": len(urls),
            "unique_urls": len(set(urls)),
            "modified_responses": modified,
            "script_evaluate_failed": failed,
            "semantics": "response.content 为复写后；_loonOriginal 为复写前；_loon.rewrite 为实际命中规则",
        },
        "urls": sorted(set(urls)),
        "observed_rewrite": [
            {"rule": rule, "count": count}
            for rule, count in observed.most_common()
        ],
        "observed_scripts": dict(scripts),
        "effects": effects,
        "samples": samples,
        "ui_evidence": ui_evidence,
        "preserved": PRESERVED,
        "unresolved": UNRESOLVED,
    }
    return snapshot


def rule_hits(url_regex, urls):
    try:
        pattern = re.compile(url_regex)
    except re.error:
        return -1
    return sum(1 for url in urls if pattern.search(url))


def delete_keys(payload, keys):
    """按 Loon response.json.delete 的点分路径语义就地删键。"""
    for key in keys:
        parts = key.split(".")
        current = payload
        for part in parts[:-1]:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        if isinstance(current, dict):
            current.pop(parts[-1], None)


def action_keys(action):
    found = re.search(r"response\.json\.delete\((\[.*?\])\)", action)
    return json.loads(found.group(1)) if found else []


def simulate(snap, rules):
    """拿脱敏后的真实响应跑一遍改包：广告必须没、业务必须留。

    只断言「广告没了」是单向的——把整个响应清空也能过。这里每一组都
    同时检查业务字段（身份 / 账户 / 兑换货架 / 广告位其余 key）原样。
    """
    problems = []
    samples = snap.get("samples") or {}
    by_id = {rule.get("id"): rule for rule in rules}

    def clean_up(rid, endpoint):
        rule = by_id.get(rid)
        sample = samples.get(endpoint)
        if not rule or not isinstance(sample, dict):
            problems.append("模拟改包缺规则 {} 或样本 {}".format(rid, endpoint))
            return None, None
        before = copy.deepcopy(sample)
        after = copy.deepcopy(sample)
        delete_keys(after, action_keys(rule.get("action", "")))
        return before, after

    # ① 书架红框：MainInfo 大横幅 + Items 三图标必须一起没，响应包络不能整条炸掉。
    before, after = clean_up("kill-topoperation", "bookshelf/getTopOperation")
    if before and after:
        data = before.get("Data") or {}
        problems += [] if data.get("MainInfo") and data.get("Items") else [
            "书架样本里 MainInfo 或 Items 为空，红框断言失去基线"
        ]
        new_data = after.get("Data") or {}
        if "MainInfo" in new_data or "Items" in new_data:
            problems.append("kill-topoperation 模拟后 MainInfo 或 Items 仍在：大横幅或图标没删掉")
        for key in ("Message", "Result"):
            if after.get(key) != before.get(key):
                problems.append("kill-topoperation 把响应包络 {} 也改了".format(key))

    # ② 我的页：4 个红框营销键全删（v4.1.1 回退 9 个崩溃字段），身份与账户原样，且不是把整个 Data 清空。
    before, after = clean_up("clean-accountpage", "user/getaccountpage")
    if before and after:
        removed = [
            "BenefitButtonList", "Member", "FunctionButtonList", "BottomButtonList",
        ]
        old_data, new_data = before.get("Data") or {}, after.get("Data") or {}
        if not isinstance(new_data, dict) or not new_data:
            problems.append("clean-accountpage 把整个 Data 清空了（业务字段一起没了）")
        for key in removed:
            if key in new_data:
                problems.append("clean-accountpage 模拟后营销字段 {} 仍在".format(key))
            if key not in old_data:
                problems.append("我的页原始样本缺 {}，断言失去基线".format(key))
        for key in ("UserBasicInfo", "AccountBalance"):
            if new_data.get(key) != old_data.get(key):
                problems.append("clean-accountpage 动了业务字段 {}".format(key))
        for key in ("Message", "Result"):
            if after.get(key) != before.get(key):
                problems.append("clean-accountpage 把响应包络 {} 也改了".format(key))

    # ③ 我的页广告位：今日偶遇 / 惊喜活动推荐没，其它广告位 key 不动。
    before, after = clean_up("kill-advlistbatch", "adv/getadvlistbatch")
    if before and after:
        old_data, new_data = before.get("Data") or {}, after.get("Data") or {}
        for key in ("iosusercenter", "iosusercenter2"):
            if key in new_data:
                problems.append("kill-advlistbatch 模拟后 {} 仍在".format(key))
            if not old_data.get(key):
                problems.append("广告位原始样本 {} 为空，断言失去基线".format(key))
        if new_data.get("iOS_tab") != old_data.get("iOS_tab"):
            problems.append("kill-advlistbatch 误伤了 Data.iOS_tab")

    # ④ 激励出口：把所有 delete 规则按 URL 实跑一遍，章节卡货架不能被任何人删掉。
    goods = samples.get("checkin/checkinexchangepage")
    if isinstance(goods, dict):
        payload = copy.deepcopy(goods)
        for rule in rules:
            try:
                matched = re.search(rule.get("url", ""), "https://h5.if.qidian.com/argus/api/v3/checkin/checkinexchangepage")
            except re.error:
                continue
            if matched:
                delete_keys(payload, action_keys(rule.get("action", "")))
        left = ((payload.get("Data") or {}).get("Goods") or [])
        if len(left) != len((goods.get("Data") or {}).get("Goods") or []):
            problems.append("章节卡兑换货架 Data.Goods 被某条规则清空——激励出口被打断")

    # ⑤ jq 白名单：正常样本只留 DISCOVER_*，异常样本不能整次失败。
    rule = by_id.get("clean-simplediscover")
    if rule and os.path.exists("/usr/bin/jq"):
        found = re.search(r'response\.json\.jq\("(.*)"\)', rule.get("action", ""))
        expr = found.group(1).replace('\\"', '"') if found else ""
        if not expr:
            problems.append("clean-simplediscover 找不到 jq 表达式")
        else:
            normal = {"Data": {"Items": [
                {"KeyName": "DISCOVER_TUIJIAN"}, {"KeyName": "NEW_YOUXIZHONGXIN"},
                {"KeyName": 123}, "oops", 42,
            ]}}
            proc = subprocess.run(
                ["/usr/bin/jq", "-c", expr], input=json.dumps(normal),
                text=True, capture_output=True,
            )
            if proc.returncode != 0:
                problems.append("jq 正常+异常混合样本执行失败: " + proc.stderr.strip()[:120])
            else:
                left = (json.loads(proc.stdout).get("Data") or {}).get("Items") or []
                if len(left) != 1 or left[0].get("KeyName") != "DISCOVER_TUIJIAN":
                    problems.append("jq 白名单结果不对: " + proc.stdout.strip()[:160])
            for bad in ([1, 2, 3], {"Data": [1, 2]}, {"Result": 0},
                        {"Data": {"Items": None}}, {"Data": {"Items": {"a": 1}}}):
                proc = subprocess.run(
                    ["/usr/bin/jq", "-c", expr], input=json.dumps(bad),
                    text=True, capture_output=True,
                )
                if proc.returncode != 0:
                    problems.append("jq 异常样本 {} 执行失败: {}".format(
                        json.dumps(bad)[:60], proc.stderr.strip()[:80]
                    ))
    return problems


def check():
    with open(SNAPSHOT, encoding="utf-8") as handle:
        snap = json.load(handle)
    with open(CONFIG, encoding="utf-8") as handle:
        cfg = json.load(handle)
    rules = (cfg.get("enhance") or {}).get("rewrite") or []
    urls = snap["urls"]
    problems = []
    by_id = {rule.get("id"): rule for rule in rules}
    ui = snap["ui_evidence"]

    print(
        "qidian HAR evidence: {} entries / {} urls / {} observed rewrite rules / {} modified responses".format(
            snap["source"]["entries"], len(urls),
            len(snap["observed_rewrite"]), snap["source"]["modified_responses"],
        )
    )

    # ① 每条规则都要在真机 URL 上命中；零命中必须显式登记 waiver + 证伪方法。
    zero = []
    for rule in rules:
        rid = rule.get("id", "?")
        hits = rule_hits(rule.get("url", ""), urls)
        evidence = rule.get("evidence") or {}
        if hits < 0:
            problems.append("{}: url 正则非法".format(rid))
            continue
        if hits == 0:
            waiver = evidence.get("zero_hit_waiver") or {}
            if not (waiver.get("reason") and waiver.get("device_check")):
                problems.append(
                    "{}: 真机 {} 条 URL 上零命中，且没有登记零命中 waiver（reason + device_check）".format(
                        rid, len(urls)
                    )
                )
            zero.append(rid)
        kinds = {"effective", "fallback-empty", "field-present", "ui-redbox", "business-guard"}
        if evidence.get("kind") not in kinds:
            problems.append("{}: evidence.kind 必须是 {} 之一，得到 {!r}".format(
                rid, sorted(kinds), evidence.get("kind")
            ))
        if evidence.get("kind") in {"effective", "ui-redbox", "field-present"} and not evidence.get("proof"):
            problems.append("{}: 缺 evidence.proof（抓包证据或复写前后差异）".format(rid))
        if evidence.get("kind") != "effective" and not evidence.get("device_check"):
            problems.append("{}: 未实证生效的规则必须写 evidence.device_check（真机怎么证伪）".format(rid))
        if not evidence.get("har") or evidence["har"] not in snap["source"]["har"]:
            problems.append("{}: evidence.har 必须指向本快照的 HAR".format(rid))
        claimed = evidence.get("url_hits")
        if claimed != hits:
            problems.append("{}: evidence.url_hits={} 与按真机 URL 实算的 {} 不符（禁止手抄命中数）".format(
                rid, claimed, hits
            ))
        action = rule.get("action", "")
        endpoint = rule.get("endpoint", "")
        if "reject_dict" in action and any(p in endpoint for p in PROTECTED_ENDPOINTS):
            problems.append("{}: reject_dict 打在功能/保护面 {} 上".format(rid, endpoint))
        if "Data.Goods" in action or "Data.UserBasicInfo" in action or "Data.AccountBalance" in action:
            problems.append("{}: 动作里出现激励/业务字段（Goods / UserBasicInfo / AccountBalance）".format(rid))
    print("  rule URL hits: {} rules, {} zero-hit waiver(s)".format(len(rules), len(zero)))

    # ② 被删端点不许回潮。
    for rule in rules:
        if rule.get("endpoint") in DEAD_ENDPOINTS:
            problems.append("{}: 真机零命中的端点 {} 又回来了".format(rule.get("id"), rule["endpoint"]))

    # ③ 红框：书架顶部横幅 MainInfo + 三图标 Items 必须一起没。
    top = by_id.get("kill-topoperation")
    if not top:
        problems.append("缺 kill-topoperation（书架顶部红框）")
    else:
        action = top.get("action", "")
        whole = 'response.json.delete(["Data"])' in action
        both = "Data.MainInfo" in action and "Data.Items" in action
        if not (whole or both):
            problems.append(
                "kill-topoperation: 只删 Items 会留下大横幅 MainInfo（AdvId {}）——"
                "红框整块要删 Data 或同时删 MainInfo+Items".format(ui["bookshelf_banner"]["main_adv_id"])
            )
        else:
            print("  redbox bookshelf: MainInfo({}) + Items({}) covered".format(
                ui["bookshelf_banner"]["main_adv_id"], ui["bookshelf_banner"]["item_count"]
            ))

    # ④ 红框：我的页营销块必须删干净，身份/账户必须留着。
    account = by_id.get("clean-accountpage")
    if not account:
        problems.append("缺 clean-accountpage（我的页红框）")
    else:
        action = account.get("action", "")
        must = ["Data.Member", "Data.FunctionButtonList", "Data.BottomButtonList",
                "Data.BenefitButtonList"]
        missing = [key for key in must if key not in action]
        if missing:
            problems.append("clean-accountpage: 少删 {}".format(", ".join(missing)))
        for key in ["Data.UserBasicInfo", "Data.AccountBalance"]:
            if key in action:
                problems.append("clean-accountpage: 业务字段 {} 被删".format(key))
        if not missing:
            print("  redbox account: {} marketing keys removed, UserBasicInfo/AccountBalance kept".format(len(must)))

    # ⑤ 红框：今日偶遇 / 惊喜活动推荐广告位。
    adlist = by_id.get("kill-advlistbatch")
    if not adlist:
        problems.append("缺 kill-advlistbatch（我的页今日偶遇 / 惊喜活动推荐）")
    else:
        action = adlist.get("action", "")
        for key in ["Data.iosusercenter", "Data.iosusercenter2"]:
            if key not in action:
                problems.append("kill-advlistbatch: 少删 {}".format(key))

    # ⑥ 用户裁决保留的每日导读：不许出现清空 getdailyrecommend 的规则。
    for rule in rules:
        if "dailyrecommend/getdailyrecommend" in rule.get("url", ""):
            problems.append("{}: 用户裁决保留每日导读，不许给 getdailyrecommend 挂净化规则".format(rule.get("id")))

    # ⑦ 快照自身的完整性：证据不能被手改成空壳。
    if len(snap["observed_rewrite"]) < 5:
        problems.append("快照 observed_rewrite 少于 5 条，疑似被清空")
    if not snap["effects"]:
        problems.append("快照 effects 为空，无法证明任何一条复写真的改过回包")
    if ui["exchange_goods"]["goods_count"] < 1:
        problems.append("快照里章节卡货架为空，激励出口断言失去基线")
    if not ui["account_page"]["member_title"]:
        problems.append("快照里起点会员卡字段丢失，红框断言失去基线")
    if len(snap.get("samples") or {}) < len(SAMPLE_ENDPOINTS) - 1:
        problems.append("快照 samples 不足，双向改包模拟覆盖不全")

    simulated = simulate(snap, rules)
    problems.extend(simulated)
    print("  simulate: {} real response sample(s), {} two-sided assertion problem(s)".format(
        len(snap.get("samples") or {}), len(simulated)
    ))
    print("  preserved: {} item(s) / unresolved: {} item(s)".format(
        len(snap["preserved"]), len(snap["unresolved"])
    ))

    for problem in problems:
        print("  ERROR:", problem)
    print("qidian HAR evidence: {} problem(s)".format(len(problems)))
    return 1 if problems else 0


def report():
    with open(SNAPSHOT, encoding="utf-8") as handle:
        snap = json.load(handle)
    print("HAR {} / 日志 {}".format(snap["source"]["har"], snap["source"]["log"]))
    print("条目 {} / 起点 URL {} 条（去重 {}）/ 改包 {} / 脚本失败 {}".format(
        snap["source"]["entries"], snap["source"]["qidian_url_entries"],
        snap["source"]["unique_urls"], snap["source"]["modified_responses"],
        snap["source"]["script_evaluate_failed"],
    ))
    print("\n实际命中的复写规则（抓包时跑的是 v4.0.2 插件）：")
    for row in snap["observed_rewrite"]:
        rule = row["rule"]
        found = re.search(r"then (.*)", rule)
        print("  {:3d}× {}".format(row["count"], (found.group(1) if found else rule)[:120]))
    print("\n真正改过回包的端点：")
    for row in snap["effects"]:
        if row["removed"] or row["changed"]:
            print("  {:3d} {} removed={} changed={}".format(
                row["entry"], row["path"], len(row["removed"]), len(row["changed"])
            ))
    print("\n红框证据：")
    for key, value in snap["ui_evidence"].items():
        print("  {}: {}".format(key, json.dumps(value, ensure_ascii=False)[:220]))
    print("\n保留项：")
    for item in snap["preserved"]:
        print("  -", item)
    print("\n待真机：")
    for item in snap["unresolved"]:
        print("  -", item)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", metavar="HAR", help="从 HAR 重建证据快照")
    parser.add_argument("--check", action="store_true", help="门禁：规则必须自证抓包证据")
    args = parser.parse_args()
    if args.extract:
        snap = extract(args.extract)
        os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
        with open(SNAPSHOT, "w", encoding="utf-8") as handle:
            json.dump(snap, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print("wrote {} ({} urls, {} rewrite rules, {} effects)".format(
            SNAPSHOT, len(snap["urls"]), len(snap["observed_rewrite"]), len(snap["effects"])
        ))
        return 0
    if args.check:
        return check()
    return report()


if __name__ == "__main__":
    sys.exit(main())
