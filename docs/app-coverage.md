# App 插件覆盖率审计（生成物）

> 由 `python3 tools/app-coverage-audit.py --write` 生成（缓存快照）。
> 候选 = 上游黑名单收录、含 App 品牌 token、且未被「本 App 插件 ∪ ads.plugin 生效行」覆盖的域。
> **候选≠必拦**：逐条人工定级后才进 `src/apps/`。A=≥3 源独立收录；B=2 源；C=单源（默认不收）。
> 命中 App JSON 里 `triage_exclude` 台账的候选记为「排除·<族>」，不计入缺口——**排除是裁决，不是待办**。

## `amap` — 生效黑洞 8 域；缺口候选 A:0 B:0 C:0（已裁决排除 3 条；已收录但默认关闭 0 条）

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `apsrgeo.amap.com` | 2: adguard-dns,hagezi-pro | 排除·业务·逆地理编码 |
| `cgicol.amap.com` | 2: adguard-dns,hagezi-pro | 排除·业务·基站定位服务 |
| `dualstack-cgicol.amap.com` | 2: adguard-dns,hagezi-pro | 排除·业务·基站定位服务 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `业务·逆地理编码` ← `apsrgeo.amap.com`
- `业务·基站定位服务` ← `cgicol.amap.com`, `dualstack-cgicol.amap.com`

## `banks-mitm` — 生效黑洞 0 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `banks` — 生效黑洞 7 域；缺口候选 A:0 B:0 C:4（已裁决排除 0 条；已收录但默认关闭 1 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `ads.95516.com` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `核心银行与卡权益红线` ← `ad.abchina.com`, `jf365.boc.cn`, `cdn2.jf365.boc.cn`, `mlife.jf365.boc.cn`, `marketing.unionpayintl.com`, `online.unionpay.com`, `v.icbc.com.cn`, `elife.icbc.com.cn`, `image2.elife.icbc.com.cn`, `msmp.abchina.com.cn`, `enjoy.cdn-static.abchina.com.cn`, `midc.cdn-static.abchina.com.cn`, `tysdk.95516.com`, `content.95516.com`, `switch.cup.com.cn`, `pv.elife.icbc.com.cn`, `xykpay.3d2.icbc.com.cn`, `trip.cmbchina.com`, `ccclub.cmbchina.com`, `mlife.cmbchina.com`, `az1mbasecc.bas.cmbchina.com`, `intellicc.bas.cmbchina.com`, `res.cc.cmbimg.com`, `s3gw.cmbimg.com`, `site.cc.cmbimg.com`, `resource.cmbchina.com`, `creditcardapp.bankcomm.com`, `creditcard.bankcomm.com`, `cdn1.mbs.boc.cn`, `d.psbc.com`, `image.spdbccc.com.cn`, `m.creditcard.ecitic.com`, `imcs.citicbank.com`, `m.citiccardcdn.citicbank.com`, `yghsh.cebbank.com`, `static.cebbank.com`, `static.95508.com`, `images.cib.com.cn`, `rs.creditcard.cmbc.com.cn`, `static.creditcard.hxb.com.cn`, `iobs.pingan.com.cn`, `base.95516.com`, `account.95516.com`, `www.abchina.com.cn`, `yunbusiness.ccb.com`, `login-service.mobile-bank.psbc.com`, `mobile-bank.psbc.com`, `wallet.95516.com`, `buy.ccb.com`, `m.icbc.com.cn`, `pic1cdn.cmbchina.com`, `cmbc.maam.cc`
- `非银行品牌误配（历史误收录）` ← `marketing.ccbtechnology.com`, `*.ccbtechnology.com`
- `C 级单源/内网 APM/待实证端点（不默认拦截）` ← `oisc.icbc.com.cn`, `vads.bankcomm.cn`

## `bilibili` — 生效黑洞 6 域；缺口候选 A:0 B:0 C:1（已裁决排除 1 条；已收录但默认关闭 0 条）

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `miniapp.bilibili.com` | 2: anti-ad,hagezi-pro | 排除·业务·小程序平台 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `业务·小程序平台` ← `miniapp.bilibili.com`
- `业务·接口服务` ← `interface.bilibili.com`

## `bubei-danci` — 生效黑洞 1 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `instagram` — 生效黑洞 7 域；缺口候选 A:0 B:0 C:2（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `jd` — 生效黑洞 5 域；缺口候选 A:0 B:0 C:17（已裁决排除 12 条；已收录但默认关闭 21 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `atom-log.3.cn` | 4: adguard-dns,adrules,anti-ad,easyprivacy | 已收录·默认关 |
| `cactus.joybuy.com` | 4: adrules,anti-ad,easyprivacy,hagezi-pro | 排除·交易/风控红线 |
| `clk-m.joybuy.com` | 4: adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `h5log.joybuy.com` | 4: adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `log-h5.imdada.cn` | 4: adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `mllog.jd.com` | 4: adguard-dns,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `sgm-w.jd.com` | 4: adguard-dns,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `uranus.jd.com` | 4: anti-ad,awa,easyprivacy,hagezi-pro | 已收录·默认关 |
| `cactus.jd.com` | 3: anti-ad,easyprivacy,hagezi-pro | 排除·交易/风控红线 |
| `chat1.jd.com` | 3: anti-ad,awa,hagezi-pro | 排除·推送/客服红线 |
| `hermes.jd.com` | 3: anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `img-x.jd.com` | 3: anti-ad,awa,hagezi-pro | 排除·商品图 CDN 放行 |
| `img2.360buyimg.com` | 3: anti-ad,awa,hagezi-pro | 排除·商品图 CDN 放行 |
| `janapi.jd.com` | 3: anti-ad,awa,hagezi-pro | 排除·交易/风控红线 |
| `kepler.jd.com` | 3: adwars,awa,hagezi-pro | 排除·基础设施红线 |
| `knicks.jd.com` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |
| `mapi.m.jd.com` | 3: anti-ad,awa,hagezi-pro | 排除·交易/风控红线 |
| `mercury.jd.com` | 3: anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `orbit.jd.com` | 3: adwars,awa,hagezi-pro | 已收录·默认关 |
| `xlog.jd.com` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `blackhole.m.jd.com` | 2: anti-ad,hagezi-pro | 排除·基础设施红线 |
| `cm.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `dns.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `gia.jd.com` | 2: easyprivacy,hagezi-pro | 排除·基础设施红线 |
| `im-x.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `jcm.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `jpushjd.m.jd.com` | 2: anti-ad,hagezi-pro | 排除·推送/客服红线 |
| `jrad.jd.com` | 2: adwars,anti-ad | 已收录·默认关 |
| `log.jd.com` | 2: adguard-dns,hagezi-pro | 已收录·默认关 |
| `policy.jd.com` | 2: anti-ad,hagezi-pro | 排除·基础设施红线 |
| `u-x.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `wn.x.jd.com` | 2: anti-ad,awa | 已收录·默认关 |
| `x.jd.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `交易/风控红线` ← `mapi.*`, `janapi.*`, `cactus.*`, `passport.*`
- `推送/客服红线` ← `jpushjd.*`, `chat1.*`
- `消息/凭证红线` ← `msg.m.*`
- `商品图 CDN 放行` ← `img-x.jd.com`, `img2.*`, `*.360buyimg.com`
- `基础设施红线` ← `dns.*`, `blackhole*`, `h5speed.*`, `gia.*`, `gias.*`, `dgstatic.*`, `wl.jd.com`, `policy.*`, `kepler.*`, `union.jd.com`, `cps.*`, `jrclick.*`
- `业务·京准通商家投放后台` ← `jzt.jd.com`
- `C 级单源/风控运维不收` ← `blackhole-m.*`, `ddms.*`
- `3.cn 商品价库与静态白名单红线` ← `p.3.cn`, `c0.3.cn`, `jstatic.3.cn`, `cactus.joybuy.com`

## `mba-dashi` — 生效黑洞 68 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `meituan` — 生效黑洞 13 域；缺口候选 A:0 B:0 C:2（已裁决排除 0 条；已收录但默认关闭 4 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `catfront.dianping.com` | 7: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro,peterlowe,stevenblack | 已收录·默认关 |
| `report.meituan.com` | 5: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro | 已收录·默认关 |
| `data-sdk-uuid-log.d.meituan.net` | 3: anti-ad,awa,hagezi-pro | 已收录·默认关 |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `dreport.meituan.net` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

## `mijia` — 生效黑洞 8 域；缺口候选 A:0 B:0 C:14（已裁决排除 143 条；已收录但默认关闭 22 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `tracking.miui.com` | 10: adaway,adguard-dns,adrules,anti-ad,awa,easyprivacy,hagezi-pro,hagezi-xiaomi,peterlowe,stevenblack | 已收录·默认关 |
| `logupdate.avlyun.sec.miui.com` | 7: adaway,adguard-dns,anti-ad,awa,hagezi-pro,hagezi-xiaomi,stevenblack | 排除·安全族红线 |
| `api.brs.intl.miui.com` | 6: adguard-dns,adguard-mobile,anti-ad,hagezi-pro,hagezi-xiaomi,stevenblack | 已收录·默认关 |
| `stat.youpin.mi.com` | 6: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
| `tracking.intl.miui.com` | 6: adaway,anti-ad,hagezi-pro,hagezi-xiaomi,peterlowe,stevenblack | 已收录·默认关 |
| `abtest.mistat.xiaomi.com` | 5: adguard-dns,adguard-mobile,adwars,anti-ad,stevenblack | 已收录·默认关 |
| `activity.browser.intl.miui.com` | 5: adguard-dns,adguard-mobile,anti-ad,hagezi-pro,hagezi-xiaomi | 已收录·默认关 |
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
| `staging-notify.sec.miui.com` | 3: anti-ad,awa,hagezi-pro | 排除·安全族红线 |
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
| `app.greengurad.sec.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·安全族红线 |
| `app.miui.com` | 2: hagezi-pro,hagezi-xiaomi | 排除·MIUI 业务域 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `安全族红线` ← `*.sec.miui.com`, `*.sec.intl.miui.com`, `*avlyun*`, `*avast*`
- `安全族模式放行（未取证到域名的 catch-all）` ← `sec-*`, `sec.*`, `security.*`
- `推送/云模式放行（未取证到域名的 catch-all）` ← `findapi.*`, `statusapi.*`
- `推送/云红线` ← `*xmpush*`, `resolver.msg.*`, `*.micloud.*`, `*.chat.*`
- `账号/设备业务 API` ← `api*`, `*api.*`
- `遥测/日志（隐私面，非广告）` ← `*stat*`, `*tracking*`, `*sentry*`, `*bugreport*`, `*events.*`, `*mlog*`, `*mqs-log*`, `*beehive*`
- `系统服务总线` ← `*.sys.miui.com`
- `浏览器业务（广告位已另收）` ← `*browser*`
- `应用商店后台/升级（广告位已另收）` ← `*.pandora.xiaomi.com`
- `静态资源/下载 CDN` ← `*static*`, `*dl.files*`
- `日志数据通道` ← `miui-l7-data-*`
- `米家业务` ← `*.mihome.xiaomi.net`
- `MIUI 业务域` ← `app.miui.com`, `feedback.miui.com`, `hybrid.miui.com`, `mcc.miui.com`, `rus.miui.com`, `india.miui.com`, `testit.miui.com`, `privacy.miui.com`, `search.miui.com`, `intl.up.w.xk.miui.com`, `fb.xk.miui.com`, `gtglobal.intl.miui.com`, `preload.xiaomi.com`, `*.sms.miui.com`, `huangye.miui.com`

## `qidian` — 生效黑洞 0 域；缺口候选 A:0 B:0 C:4（已裁决排除 1 条；已收录但默认关闭 0 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `qdp.qidian.com` | 3: adrules,anti-ad,hagezi-pro | 排除·业务·起点推送与通知网关（拦后断推送，且本插件严格对齐 config 不设 [Host] 黑洞层） |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `业务·起点推送与通知网关（拦后断推送，且本插件严格对齐 config 不设 [Host] 黑洞层）` ← `qdp.qidian.com`

## `qqnews` — 生效黑洞 0 域；缺口候选 A:0 B:0 C:1（已裁决排除 3 条；已收录但默认关闭 0 条）

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `ssp.qq.com` | 2: anti-ad,hagezi-pro | 排除·腾讯共享 SSP 根域与运营后台（news.ssp 父域，仅做路径级复写） |
| `uplog.inews.qq.com` | 2: adguard-dns,hagezi-pro | 排除·遥测/日志（隐私面，非广告） |
| `w.inews.qq.com` | 2: anti-ad,hagezi-pro | 排除·业务·H5 新闻与分享页 API |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `业务·H5 新闻与分享页 API` ← `w.inews.qq.com`
- `腾讯共享 SSP 根域与运营后台（news.ssp 父域，仅做路径级复写）` ← `ssp.qq.com`, `op.ssp.qq.com`
- `遥测/日志（隐私面，非广告）` ← `uplog.inews.qq.com`

## `ruankao-tong` — 生效黑洞 68 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `taobao` — 生效黑洞 27 域；缺口候选 A:0 B:0 C:24（已裁决排除 14 条；已收录但默认关闭 33 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `rum.aliyuncs.com` | 6: adguard-dns,anti-ad,easyprivacy,hagezi-pro,peterlowe,stevenblack | 已收录·默认关 |
| `aplus.alibaba.com` | 5: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro | 排除·统计初始化依赖（拦截易致网页白屏/卡开屏） |
| `audid-api.taobao.com` | 5: adaway,adguard-dns,adwars,awa,stevenblack | 排除·基础设施/安全风控与页面引擎红线 |
| `fourier.alibaba.com` | 5: adguard-dns,adrules,anti-ad,easyprivacy,hagezi-pro | 排除·统计初始化依赖（拦截易致网页白屏/卡开屏） |
| `adash.m.taobao.com` | 4: adguard-dns,adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `adashbc.ut.taobao.com` | 4: adwars,anti-ad,awa,hagezi-pro | 已收录·默认关 |
| `adashx4ae.ut.taobao.com` | 4: adaway,adguard-dns,hagezi-pro,stevenblack | 已收录·默认关 |
| `adashxgc.ut.taobao.com` | 4: adwars,anti-ad,awa,hagezi-pro | 已收录·默认关 |
| `dmtracking2.alibaba.com` | 4: adguard-dns,hagezi-pro,peterlowe,stevenblack | 已收录·默认关 |
| `fourier.taobao.com` | 4: adguard-dns,anti-ad,easyprivacy,hagezi-pro | 排除·统计初始化依赖（拦截易致网页白屏/卡开屏） |
| `tunion-api.m.taobao.com` | 4: adguard-dns,adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `umdc.aliapp.org` | 4: adrules,adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `accscdn.m.taobao.com` | 3: adguard-dns,anti-ad,hagezi-pro | 排除·基础设施/安全风控与页面引擎红线 |
| `acs4baichuan.m.taobao.com` | 3: adwars,anti-ad,hagezi-pro | 排除·业务·阿里百川电商跳转与授权套件 |
| `adash.man.aliyuncs.com` | 3: adguard-dns,adwars,anti-ad | 已收录·默认关 |
| `adashbc.m.taobao.com` | 3: adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `adashx.ut.ele.me` | 3: adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `all.cnzz.com.danuoyi.tbcache.com` | 3: adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `baichuan-sdk.taobao.com` | 3: anti-ad,awa,hagezi-pro | 排除·业务·阿里百川电商跳转与授权套件 |
| `dmtracking.alibaba.com` | 3: hagezi-pro,peterlowe,stevenblack | 已收录·默认关 |
| `h-adashx.ut.ele.me` | 3: adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `h-adashx4ae.ut.taobao.com` | 3: adguard-dns,hagezi-pro,stevenblack | 已收录·默认关 |
| `h-adashx4yt.ut.taobao.com` | 3: adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `hybrid.miniapp.taobao.com` | 3: anti-ad,awa,hagezi-pro | 排除·基础设施/安全风控与页面引擎红线 |
| `hydra.alibaba.com` | 3: adaway,anti-ad,stevenblack | 已收录·默认关 |
| `mum.alibabachengdun.com` | 3: adguard-dns,anti-ad,hagezi-pro | 排除·统计初始化依赖（拦截易致网页白屏/卡开屏） |
| `nbsdk-baichuan.taobao.com` | 3: adguard-dns,anti-ad,hagezi-pro | 排除·业务·阿里百川电商跳转与授权套件 |
| `openjmacs.m.taobao.com` | 3: adwars,anti-ad,hagezi-pro | 排除·关联·跨 App 阿里长连接通道（高德/优酷） |
| `sjarvis.taobao.com` | 3: adwars,anti-ad,hagezi-pro | 排除·基础设施/安全风控与页面引擎红线 |
| `stat.alibaba.com` | 3: adguard-dns,hagezi-pro,stevenblack | 已收录·默认关 |
| `umeng.com.gds.alibabadns.com` | 3: adwars,anti-ad,hagezi-pro | 已收录·默认关 |
| `youku-acs.m.taobao.com` | 3: adwars,anti-ad,hagezi-pro | 排除·关联·跨 App 阿里长连接通道（高德/优酷） |

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `adashx.ut.alibaba.com` | 2: adguard-dns,hagezi-pro | 已收录·默认关 |
| `adashx.ut.taobao.com` | 2: hagezi-pro,stevenblack | 已收录·默认关 |
| `adashx4id.ut.taobao.com` | 2: adguard-dns,hagezi-pro | 已收录·默认关 |
| `ai.m.taobao.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `ai.taobao.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `app-monitor.ele.me` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `c-adash.m.taobao.com` | 2: adwars,anti-ad | 已收录·默认关 |
| `gaode-jmacs.m.taobao.com` | 2: anti-ad,hagezi-pro | 排除·关联·跨 App 阿里长连接通道（高德/优酷） |
| `h-adashx.ut.alibaba.com` | 2: adguard-dns,hagezi-pro | 已收录·默认关 |
| `h-adashx4id.ut.taobao.com` | 2: adguard-dns,hagezi-pro | 已收录·默认关 |
| `m-adash.m.taobao.com` | 2: adwars,anti-ad | 已收录·默认关 |
| `re.taobao.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `retcode.taobao.com` | 2: easyprivacy,hagezi-pro | 已收录·默认关 |
| `umc.danuoyi.alicdn.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |
| `v6-adashx.ut.taobao.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `业务·直通车收藏与卖家移动后台` ← `fav.simba.taobao.com`, `m.simba.taobao.com`
- `基础设施/安全风控与页面引擎红线` ← `audid-api.*`, `audid-api-sg.*`, `sdkinit.taobao.com`, `tbskip.taobao.com`, `err.taobao.com`, `error.taobao.com.danuoyi.tbcache.com`, `aeis.alicdn.com`, `sjarvis.*`, `cdn.ynuf.*`, `tce.alicdn.com`, `dorangesource.alicdn.com`, `ossgw.alicdn.com`, `accscdn.*`, `hybrid.miniapp.*`, `asearch.alicdn.com`, `pass.1688.com`, `grand.ele.me`, `client-api.ele.me`, `newton-api.ele.me`
- `业务·1688 移动端 UI 与非纯广告子域（单源不收）` ← `cui.m.1688.com`
- `统计初始化依赖（拦截易致网页白屏/卡开屏）` ← `mum.alibabachengdun.*`, `acs-mum.alibabachengdun.*`, `fourier.*`, `aplus.alibaba.com`
- `业务·阿里百川电商跳转与授权套件` ← `baichuan-sdk.*`, `nbsdk-baichuan.*`, `acs4baichuan.*`
- `关联·跨 App 阿里长连接通道（高德/优酷）` ← `gaode-jmacs.*`, `openjmacs.*`, `youku-acs.*`

## `wechat` — 生效黑洞 36 域；缺口候选 A:0 B:0 C:1（已裁决排除 0 条；已收录但默认关闭 1 条）

| B 候选（2 源） | 源 | 状态 |
|---|---|---|
| `xmaterial.tu.qq.com` | 2: anti-ad,hagezi-pro | 已收录·默认关 |

## `x` — 生效黑洞 3 域；缺口候选 A:0 B:0 C:3（已裁决排除 0 条；已收录但默认关闭 2 条）

| A 候选（≥3 源） | 源 | 状态 |
|---|---|---|
| `analytics.twitter.com` | 3: adaway,anti-ad,stevenblack | 已收录·默认关 |
| `scribe.twitter.com` | 3: anti-ad,hagezi-pro,stevenblack | 已收录·默认关 |

裁决台账（命中即排除；改台账需改 App JSON 并重新生成）：
- `业务·广告宣传官网与旧版嵌入源（非客户端投放域）` ← `advertising.twitter.com`, `syndication-o.twitter.com`

## `xianyu` — 生效黑洞 23 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `youtube` — 生效黑洞 2 域；缺口候选 A:0 B:0 C:2（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `zhihu` — 生效黑洞 5 域；缺口候选 A:0 B:0 C:4（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## `zhihuifangdong` — 生效黑洞 137 域；缺口候选 A:0 B:0 C:0（已裁决排除 0 条；已收录但默认关闭 0 条）

无 A/B 级缺口候选。

## 排除口径

- 共享主域 root 本身绝不进候选；root 子域需再命中「广告向 hint 词」才有资格（防止把业务子域当缺口）。
- 已被 ads.plugin 生效规则（含通配/关键词/SUFFIX）覆盖的不算缺口。
- `triage_exclude`：App JSON 里的裁决台账（安全/推送/账号云/遥测/业务 API），命中的候选只展示、不计缺口。
- C 级候选默认忽略；出现设备日志证据后再单独升级。
