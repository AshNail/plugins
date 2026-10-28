# App 插件覆盖率审计（生成物）

> 由 `python3 tools/app-coverage-audit.py --write` 生成（缓存快照）。
> 候选 = 上游黑名单收录、含 App 品牌 token、且未被「本 App 插件 ∪ ads.plugin 生效行」覆盖的域。
> **候选≠必拦**：逐条人工定级后才进 `src/apps/`。A=≥3 源独立收录；B=2 源；C=单源（默认不收）。

## `banks` — 生效黑洞 1 域；缺口候选 A:1 B:0 C:2（其中 1 条已收录但默认关闭）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `ads.95516.com` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |

## `bubei-danci` — 生效黑洞 1 域；缺口候选 A:0 B:0 C:0（其中 0 条已收录但默认关闭）

无 A/B 级缺口候选。

## `instagram` — 生效黑洞 6 域；缺口候选 A:1 B:1 C:7（其中 2 条已收录但默认关闭）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `netseer.com` | 4: adguard-dns,anti-ad,hagezi-pro,stevenblack | 已收录·默认关 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `cm.netseer.com` | 2: anti-ad,stevenblack | 已收录·默认关 |

## `mba-dashi` — 生效黑洞 54 域；缺口候选 A:0 B:0 C:0（其中 0 条已收录但默认关闭）

无 A/B 级缺口候选。

## `meituan` — 生效黑洞 10 域；缺口候选 A:3 B:1 C:2（其中 4 条已收录但默认关闭）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `catfront.dianping.com` | 7: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro,peterlowe,stevenblack | 已收录·默认关 |
| `report.meituan.com` | 5: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `data-sdk-uuid-log.d.meituan.net` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `dreport.meituan.net` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

## `mijia` — 生效黑洞 6 域；缺口候选 A:35 B:145 C:13（其中 32 条已收录但默认关闭）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `tracking.miui.com` | 10: adaway,adguard-dns,adrules,anti-ad,awa,easyprivacy,hagezi-pro,hagezi-xiaomi,peterlowe,stevenblack | 已收录·默认关 |
| `logupdate.avlyun.sec.miui.com` | 7: adaway,adguard-dns,anti-ad,awa,hagezi-pro,hagezi-xiaomi,stevenblack | 缺口 |
| `adv.sec.intl.miui.com` | 6: adguard-dns,anti-ad,awa,hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `adv.sec.miui.com` | 6: adguard-dns,adwars,anti-ad,awa,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `stat.youpin.mi.com` | 6: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `tracking.intl.miui.com` | 6: adaway,anti-ad,hagezi-pro,hagezi-xiaomi,peterlowe,stevenblack | 已收录·默认关 |
| `api.brs.intl.miui.com` | 5: adguard-dns,anti-ad,hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `data.mistat.xiaomi.com` | 5: adguard-dns,adrules,anti-ad,awa,stevenblack | 已收录·默认关 |
| `tracking.rus.miui.com` | 5: adaway,adrules,anti-ad,awa,stevenblack | 已收录·默认关 |
| `abtest.mistat.xiaomi.com` | 4: adguard-dns,adwars,anti-ad,stevenblack | 已收录·默认关 |
| `activity.browser.intl.miui.com` | 4: adguard-dns,anti-ad,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `api.setting.intl.miui.com` | 4: adguard-dns,hagezi-pro,hagezi-xiaomi,stevenblack | 缺口 |
| `auth.be.sec.miui.com` | 4: adguard-dns,adrules,hagezi-pro,hagezi-xiaomi | 缺口 |
| `authbe.sec.intl.miui.com` | 4: adguard-dns,hagezi-pro,hagezi-xiaomi,stevenblack | 缺口 |
| `ccc.sys.miui.com` | 4: anti-ad,hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `data.mistat.india.xiaomi.com` | 4: adguard-dns,adrules,anti-ad,awa | 已收录·默认关 |
| `data.mistat.rus.xiaomi.com` | 4: adguard-dns,adrules,anti-ad,awa | 已收录·默认关 |
| `data.sec.intl.miui.com` | 4: adguard-dns,hagezi-pro,hagezi-xiaomi,stevenblack | 缺口 |
| `flash.sec.intl.miui.com` | 4: adguard-dns,hagezi-pro,hagezi-xiaomi,stevenblack | 缺口 |
| `metok.sys.miui.com` | 4: adguard-dns,adrules,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `stat.xiaomi.com` | 4: hagezi-pro,hagezi-xiaomi,peterlowe,stevenblack | 已收录·默认关 |
| `api.collect.data.intl.miui.com` | 3: hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `api.sec.miui.com` | 3: adguard-dns,hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.tw06.xlmc.sec.miui.com` | 3: adrules,adwars,anti-ad | 缺口 |
| `apm-rum.inf.miui.com` | 3: adrules,anti-ad,easyprivacy | 已收录·默认关 |
| `cc.sys.miui.com` | 3: hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `data.mistat.intl.xiaomi.com` | 3: adguard-dns,anti-ad,stevenblack | 已收录·默认关 |
| `data.sec.miui.com` | 3: adguard-dns,hagezi-pro,hagezi-xiaomi | 缺口 |
| `geofence.sys.miui.com` | 3: hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `hot.browser.intl.miui.com` | 3: anti-ad,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `inf.miui.com` | 3: adguard-dns,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `mazu.sec.miui.com` | 3: adguard-dns,hagezi-pro,hagezi-xiaomi | 缺口 |
| `notify.sec.miui.com` | 3: anti-ad,awa,hagezi-pro | 缺口 |
| `stat.pandora.xiaomi.com` | 3: anti-ad,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `update.avlyun.sec.miui.com` | 3: awa,hagezi-pro,hagezi-xiaomi | 缺口 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `3rdupgrade.pandora.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `abroad.api.comm.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `ad.cdn.pandora.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `ad.eu.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `ad.india.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `ad.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `ad.quickapp.hybrid.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `ad.rus.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `adv.l7.34.sec.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `adx.tv.mi.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `analytics.ff.avast.sec.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api-rec.stellar.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.accelerator.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.account.preview.n.xiaomi.net` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.ads.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `api.aurogon.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.bbs.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.browser.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.calendar.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.comm.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.competition.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.content.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.device.xiaomi.net` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.g.micloud.xiaomi.net` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |
| `api.game.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 缺口 |

## `qidian` — 生效黑洞 56 域；缺口候选 A:1 B:0 C:3（其中 1 条已收录但默认关闭）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `qdp.qidian.com` | 3: adrules,anti-ad,hagezi-pro | 已收录·默认关 |

## `ruankao-tong` — 生效黑洞 54 域；缺口候选 A:0 B:0 C:0（其中 0 条已收录但默认关闭）

无 A/B 级缺口候选。

## `wechat` — 生效黑洞 25 域；缺口候选 A:0 B:2 C:6（其中 1 条已收录但默认关闭）

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `adinall.com` | 2: anti-ad,hagezi-pro | 缺口 |
| `xmaterial.tu.qq.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

## `x` — 生效黑洞 3 域；缺口候选 A:3 B:0 C:3（其中 3 条已收录但默认关闭）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `ads-bidder-api.twitter.com` | 4: adaway,adguard-dns,hagezi-pro,stevenblack | 已收录·默认关 |
| `analytics.twitter.com` | 3: adaway,anti-ad,stevenblack | 已收录·默认关 |
| `scribe.twitter.com` | 3: anti-ad,hagezi-pro,stevenblack | 已收录·默认关 |

## `xianyu` — 生效黑洞 6 域；缺口候选 A:0 B:0 C:0（其中 0 条已收录但默认关闭）

无 A/B 级缺口候选。

## `zhihuifangdong` — 生效黑洞 85 域；缺口候选 A:0 B:0 C:0（其中 0 条已收录但默认关闭）

无 A/B 级缺口候选。

## 排除口径

- 共享主域 root 本身绝不进候选；root 子域需再命中「广告向 hint 词」才有资格（防止把业务子域当缺口）。
- 已被 ads.plugin 生效规则（含通配/关键词/SUFFIX）覆盖的不算缺口。
- C 级候选默认忽略；出现设备日志证据后再单独升级。
