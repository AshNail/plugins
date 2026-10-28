# App 插件覆盖率审计（生成物）

> 由 `python3 tools/app-coverage-audit.py --write` 生成（缓存快照）。
> 候选 = 上游黑名单收录、含 App 品牌 token、且未被「本 App 插件 ∪ ads.plugin 生效行」覆盖的域。
> **候选≠必拦**：逐条人工定级后才进 `src/apps/`。A=≥3 源独立收录；B=2 源；C=单源（默认不收）。
> 命中 App JSON 里 `triage_exclude` 台账的候选记为「排除·<族>」，不计入缺口——**排除是裁决，不是待办**。

## `banks` — 生效黑洞 1 域；缺口候选 A:0 B:0 C:2（已裁决排除 0 条；已收录但默认关闭 1 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `ads.95516.com` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |

## `bubei-danci` — 生效黑洞 1 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `instagram` — 生效黑洞 6 域；缺口候选 A:0 B:0 C:7（已裁决排除 0 条；已收录但默认关闭 2 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `netseer.com` | 5: adguard-dns,adguard-mobile,anti-ad,hagezi-pro,stevenblack | 已收录·默认关 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `cm.netseer.com` | 2: anti-ad,stevenblack | 已收录·默认关 |

## `jd` — 生效黑洞 5 域；缺口候选 A:0 B:0 C:11（已裁决排除 14 条；已收录但默认关闭 16 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `mllog.jd.com` | 5: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `sgm-w.jd.com` | 5: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `uranus.jd.com` | 5: adrules,anti-ad,awa,easyprivacy,hagezi-pro | 已收录·默认关 |
| `cactus.jd.com` | 4: adrules,anti-ad,easyprivacy,hagezi-pro | 排除·交易/风控红线 |
| `hermes.jd.com` | 4: adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `janapi.jd.com` | 4: adrules,anti-ad,awa,hagezi-pro | 排除·交易/风控红线 |
| `jcm.jd.com` | 4: adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `mercury.jd.com` | 4: adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `xlog.jd.com` | 4: adrules,anti-ad,awa,hagezi-pro | 已收录·默认关 |
| `chat1.jd.com` | 3: anti-ad,awa,hagezi-pro | 排除·推送/客服红线 |
| `im-x.jd.com` | 3: adrules,anti-ad,hagezi-pro | 已收录·默认关 |
| `img-x.jd.com` | 3: anti-ad,awa,hagezi-pro | 排除·商品图 CDN 放行 |
| `img2.360buyimg.com` | 3: anti-ad,awa,hagezi-pro | 排除·商品图 CDN 放行 |
| `kepler.jd.com` | 3: adwars,awa,hagezi-pro | 排除·基础设施红线 |
| `knicks.jd.com` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |
| `mapi.m.jd.com` | 3: anti-ad,awa,hagezi-pro | 排除·交易/风控红线 |
| `orbit.jd.com` | 3: adwars,awa,hagezi-pro | 已收录·默认关 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `blackhole.m.jd.com` | 2: anti-ad,hagezi-pro | 排除·基础设施红线 |
| `cm.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `gia.jd.com` | 2: easyprivacy,hagezi-pro | 排除·基础设施红线 |
| `gias.jd.com` | 2: adrules,easyprivacy | 排除·基础设施红线 |
| `h5speed.m.jd.com` | 2: adrules,easyprivacy | 排除·基础设施红线 |
| `jpushjd.m.jd.com` | 2: anti-ad,hagezi-pro | 排除·推送/客服红线 |
| `jrad.jd.com` | 2: adwars,anti-ad | 已收录·默认关 |
| `log.jd.com` | 2: adguard-dns,hagezi-pro | 已收录·默认关 |
| `policy.jd.com` | 2: anti-ad,hagezi-pro | 排除·基础设施红线 |
| `u-x.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `wl.jd.com` | 2: adrules,easyprivacy | 排除·基础设施红线 |
| `wn.x.jd.com` | 2: anti-ad,awa | 已收录·默认关 |
| `x.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `交易/风控红线` ← `mapi.*`, `janapi.*`, `cactus.*`, `passport.*`
- `推送/客服红线` ← `jpushjd.*`, `chat1.*`
- `消息/凭证红线` ← `msg.m.*`
- `商品图 CDN 放行` ← `img-x.jd.com`, `img2.*`, `*.360buyimg.com`
- `基础设施红线` ← `dns.*`, `blackhole*`, `h5speed.*`, `gia.*`, `gias.*`, `dgstatic.*`, `wl.jd.com`, `policy.*`, `kepler.*`, `union.jd.com`, `cps.*`, `jrclick.*`
- `C 级单源不收` ← `u.x.jd.com`, `bdsp.x.jd.com`, `du.jd.com`, `nfa.jd.com`, `c-nfa.jd.com`, `firevent.jd.com`, `stat.m.jd.com`, `ads.union.jd.com`, `jzt.jd.com`

## `mba-dashi` — 生效黑洞 54 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `meituan` — 生效黑洞 10 域；缺口候选 A:0 B:0 C:2（已裁决排除 0 条；已收录但默认关闭 4 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `catfront.dianping.com` | 7: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro,peterlowe,stevenblack | 已收录·默认关 |
| `report.meituan.com` | 5: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `data-sdk-uuid-log.d.meituan.net` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `dreport.meituan.net` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

## `mijia` — 生效黑洞 6 域；缺口候选 A:0 B:0 C:13（已裁决排除 141 条；已收录但默认关闭 23 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `tracking.miui.com` | 10: adaway,adguard-dns,adrules,anti-ad,awa,easyprivacy,hagezi-pro,hagezi-xiaomi,peterlowe,stevenblack | 已收录·默认关 |
| `logupdate.avlyun.sec.miui.com` | 7: adaway,adguard-dns,anti-ad,awa,hagezi-pro,hagezi-xiaomi,stevenblack | 排除·安全族红线 |
| `api.brs.intl.miui.com` | 6: adguard-dns,adguard-mobile,anti-ad,hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `stat.youpin.mi.com` | 6: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `tracking.intl.miui.com` | 6: adaway,anti-ad,hagezi-pro,hagezi-xiaomi,peterlowe,stevenblack | 已收录·默认关 |
| `abtest.mistat.xiaomi.com` | 5: adguard-dns,adguard-mobile,adwars,anti-ad,stevenblack | 已收录·默认关 |
| `activity.browser.intl.miui.com` | 5: adguard-dns,adguard-mobile,anti-ad,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `data.mistat.xiaomi.com` | 5: adguard-dns,adrules,anti-ad,awa,stevenblack | 已收录·默认关 |
| `tracking.rus.miui.com` | 5: adaway,adrules,anti-ad,awa,stevenblack | 已收录·默认关 |
| `api.setting.intl.miui.com` | 4: adguard-dns,hagezi-pro,hagezi-xiaomi,stevenblack | 排除·账号/设备业务 API |
| `auth.be.sec.miui.com` | 4: adguard-dns,adrules,hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |
| `authbe.sec.intl.miui.com` | 4: adguard-dns,hagezi-pro,hagezi-xiaomi,stevenblack | 排除·安全族红线 |
| `ccc.sys.miui.com` | 4: anti-ad,hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `data.mistat.india.xiaomi.com` | 4: adguard-dns,adrules,anti-ad,awa | 已收录·默认关 |
| `data.mistat.rus.xiaomi.com` | 4: adguard-dns,adrules,anti-ad,awa | 已收录·默认关 |
| `data.sec.intl.miui.com` | 4: adguard-dns,hagezi-pro,hagezi-xiaomi,stevenblack | 排除·安全族红线 |
| `flash.sec.intl.miui.com` | 4: adguard-dns,hagezi-pro,hagezi-xiaomi,stevenblack | 排除·安全族红线 |
| `metok.sys.miui.com` | 4: adguard-dns,adrules,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `stat.xiaomi.com` | 4: hagezi-pro,hagezi-xiaomi,peterlowe,stevenblack | 已收录·默认关 |
| `api.collect.data.intl.miui.com` | 3: hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `api.newsfeed.intl.miui.com` | 3: adguard-dns,adguard-mobile,anti-ad | 排除·账号/设备业务 API |
| `api.sec.miui.com` | 3: adguard-dns,hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |
| `api.tw06.xlmc.sec.miui.com` | 3: adrules,adwars,anti-ad | 排除·安全族红线 |
| `apm-rum.inf.miui.com` | 3: adrules,anti-ad,easyprivacy | 已收录·默认关 |
| `cc.sys.miui.com` | 3: hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `data.mistat.intl.xiaomi.com` | 3: adguard-dns,anti-ad,stevenblack | 已收录·默认关 |
| `data.sec.miui.com` | 3: adguard-dns,hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |
| `geofence.sys.miui.com` | 3: hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `hot.browser.intl.miui.com` | 3: anti-ad,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `inf.miui.com` | 3: adguard-dns,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `mazu.sec.miui.com` | 3: adguard-dns,hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |
| `notify.sec.miui.com` | 3: anti-ad,awa,hagezi-pro | 排除·安全族红线 |
| `stat.pandora.xiaomi.com` | 3: anti-ad,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `update.avlyun.sec.miui.com` | 3: awa,hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `3rdupgrade.pandora.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `abroad.api.comm.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `analytics.ff.avast.sec.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |
| `api-rec.stellar.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.accelerator.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.account.preview.n.xiaomi.net` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.aurogon.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.bbs.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.browser.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.calendar.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.comm.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.competition.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.content.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.device.xiaomi.net` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.g.micloud.xiaomi.net` | 2: hagezi-pro,hagezi-xiaomi | 排除·推送/云红线 |
| `api.game.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.launcher.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.mintbrs.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.muc.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.sms.intl.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·账号/设备业务 API |
| `api.xmpush.global.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·推送/云红线 |
| `api.xmpush.xiaomi.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·推送/云红线 |
| `apkrep.ff.avast.sec.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |
| `app.chat.xiaomi.net` | 2: adrules,easyprivacy | 排除·推送/云红线 |
| `app.greengurad.sec.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `安全族红线` ← `*.sec.miui.com`, `*.sec.intl.miui.com`, `sec-*`, `sec.*`, `security.*`, `*avlyun*`, `*avast*`
- `推送/云红线` ← `*xmpush*`, `resolver.msg.*`, `*.micloud.*`, `findapi.*`, `statusapi.*`, `*.chat.*`
- `账号/设备业务 API` ← `api*`, `*api.*`
- `遥测/日志（隐私面，非广告）` ← `*stat*`, `*tracking*`, `*sentry*`, `*bugreport*`, `*events.*`, `*mlog*`, `*mqs-log*`, `*beehive*`
- `系统服务总线` ← `*.sys.miui.com`
- `浏览器业务（广告位已另收）` ← `*browser*`
- `应用商店后台/升级（广告位已另收）` ← `*.pandora.xiaomi.com`
- `静态资源/下载 CDN` ← `*static*`, `*dl.files*`
- `日志数据通道` ← `miui-l7-data-*`
- `米家业务` ← `*.mihome.xiaomi.net`
- `MIUI 业务域` ← `app.miui.com`, `feedback.miui.com`, `hybrid.miui.com`, `mcc.miui.com`, `rus.miui.com`, `india.miui.com`, `testit.miui.com`, `privacy.miui.com`, `search.miui.com`, `intl.up.w.xk.miui.com`, `gtglobal.intl.miui.com`, `preload.xiaomi.com`, `*.sms.miui.com`

## `qidian` — 生效黑洞 56 域；缺口候选 A:0 B:0 C:3（已裁决排除 0 条；已收录但默认关闭 1 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `qdp.qidian.com` | 3: adrules,anti-ad,hagezi-pro | 已收录·默认关 |

## `ruankao-tong` — 生效黑洞 54 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `wechat` — 生效黑洞 25 域；缺口候选 A:0 B:0 C:3（已裁决排除 0 条；已收录但默认关闭 1 条）

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `xmaterial.tu.qq.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

## `x` — 生效黑洞 3 域；缺口候选 A:0 B:0 C:3（已裁决排除 0 条；已收录但默认关闭 3 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `ads-bidder-api.twitter.com` | 5: adaway,adguard-dns,adguard-mobile,hagezi-pro,stevenblack | 已收录·默认关 |
| `analytics.twitter.com` | 3: adaway,anti-ad,stevenblack | 已收录·默认关 |
| `scribe.twitter.com` | 3: anti-ad,hagezi-pro,stevenblack | 已收录·默认关 |

## `xianyu` — 生效黑洞 6 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `zhihuifangdong` — 生效黑洞 88 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## 排除口径

- 共享主域 root 本身绝不进候选；root 子域需再命中「广告向 hint 词」才有资格（防止把业务子域当缺口）。
- 已被 ads.plugin 生效规则（含通配/关键词/SUFFIX）覆盖的不算缺口。
- `triage_exclude`：App JSON 里的裁决台账（安全/推送/账号云/遥测/业务 API），命中的候选只展示、不计缺口。
- C 级候选默认忽略；出现设备日志证据后再单独升级。
