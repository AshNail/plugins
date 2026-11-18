# 淘宝 · 去广告（原生复写层） v1.3.0

> 淘宝阿里妈妈/Tanx/Simba等独立广告域双栈与黑洞拦截，开屏、推荐与活动广告原生复写清理；交易支付风控零接触。

版本 **1.3.6** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 taobao.plugin](https://img.shields.io/badge/Loon-导入%E6%B7%98%E5%AE%9D%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E5%8E%9F%E7%94%9F%E5%A4%8D%E5%86%99%E5%B1%82%EF%BC%89%20v1.3.0-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Ftaobao%2Ftaobao.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/taobao/taobao.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 阿里广告/UT 独立端点 | B | 启用 | h-adashx.ut.taobao.com=AdashX 广告/UT 分片；adashx4yt.m.taobao.com=优土侧 AdashX 分片；dsp/tmatch/stat/srd.simba.taobao.com=Simba 直通车竞价、定向与曝光统计子域（其余 atanx/atanx2/afpmm/afp/ilce/strip.taobaocdn/kb-render/gma/aecpm/tns.simba/adashx.m/wcp/poplayer/rtb.julang 已由上方 sdks:["alimama"] 统一注入；audid-api/ossgw 已移入红线，hudong 移入默认关 ali_optional）。均为精确广告子域，媒体主域 alicdn.com 不整域。 |
| 阿里互动与促销活动资源（默认关） | C | 默认关闭 | hudong.alicdn.com 在 25 源开源黑名单 0 命中，承载淘宝/天猫互动活动与大促会场 H5 静态资源；仅想彻底屏蔽互动活动、且能接受点不开活动页时可选开启，默认关。 |
| UT 埋点（默认关） | B | 默认关闭 | ut.taobao.com / adash*（含 adash-c / h-adashx4yt）全系 UT/AdashX 分片与 IPv6 节点 / ae-alimelog & alimelog / retcode.taobao.com（ARMS 前端监控）/ umdc.aliapp.org（崩溃/行为采集）/ umengacs / umengjmacs / hydra & abtest & dmtracking & dmtracking2 & stat.alibaba.com=阿里 UT 埋点、性能监测与实验分流；关闭统计不等于去广告，默认关，需要隐私优先再开。 |
| 淘宝客/联盟归因（默认关） | B | 默认关闭 | tunion-api.m.taobao.com=淘宝联盟 CPS 归因；拦了会影响淘宝客取链/返利，默认关。 |
| 阿里 AMDC / 多线 HTTPDNS 调度（默认关） | B | 默认关闭 | amdc.m.taobao.com / amdcopen.m.taobao.com / umc.danuoyi.alicdn.com（阿里云 CDN /multi_dns_resolve 多线 HTTPDNS）=阿里 HTTPDNS 调度；拦后若 App/CDN 无回退可能拖慢建连或影响图床调度，默认关。 |
| 阿里妈妈直通车点击跳转/外链（默认关） | B | 默认关闭 | 直通车推广点击/跳转（simba.taobao.com / click.taobao.com / g.click.taobao.com）与爱淘宝/热卖导购落地域（re/ai.taobao.com、show.re.taobao.com）：若只拦截点击跳转不拦截商品搜索页内的推广展示，结果只是点进推广宝贝/返利导购卡死——默认关。 |
| 阿里妈妈 / TanX / 阿里广告监测（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 25 域 / 0 规则。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 4 条。 |
| pre-DNS 双栈防旁路 | A | 启用 | 由生效 `[Host]` 精确派生 `DOMAIN-SUFFIX`/`DOMAIN` REJECT，在 DNS 解析前同步阻断 IPv4 与 IPv6/AAAA，防止单装插件时 AAAA 旁路。共 27 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

淘宝 iOS 的开屏/推荐/活动广告入口与交易共用 acs.m.taobao.com、guide-acs.m.taobao.com，不能黑洞整域。本层默认启用 Loon 原生 [Rewrite] v2 引擎复写（由 cleanAds 开关控制，零 JS 脚本）：13 条广告 mtop 路径在 request 阶段直接 reject_dict(200) 返回空字典；开屏全屏广告图路径用 reject_img(200) 返回 1px 透明 GIF。

- 解密主机（`[MITM] hostname`，4 个，本层已默认生效）：`acs.m.taobao.com`, `guide-acs.m.taobao.com`, `gw.alicdn.com`, `heic.alicdn.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，4 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：acs.m.taobao.com / guide-acs.m.taobao.com 的 13 条广告 mtop 路径在 request 阶段直接 reject_dict(200) 终止；gw/heic.alicdn.com 开屏推广大图路径用 reject_img(200) 返回 1px 透明图。需已安装并信任 Loon 证书。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-fliggy-screen` | request | `reject_dict` | `cleanAds` | 飞猪频道弹屏与营销资源拉取 |
| `kill-alibaba-getadv` | request | `reject_dict` | `cleanAds` | 阿里通用广告服务拉取接口 |
| `kill-etao-advertise` | request | `reject_dict` | `cleanAds` | 阿里妈妈一淘广告配置拉取 |
| `kill-alimusic-startinit` | request | `reject_dict` | `cleanAds` | 启动初始化营销配置接口 |
| `kill-tao-splash` | request | `reject_dict` | `cleanAds` | 淘宝 noah 开屏广告查询接口 |
| `kill-film-advertise` | request | `reject_dict` | `cleanAds` | 淘票票/影视模块广告查询接口 |
| `kill-o2o-ad` | request | `reject_dict` | `cleanAds` | 本地生活 O2O 广告网关拉取接口 |
| `kill-idle-welcome` | request | `reject_dict` | `cleanAds` | 闲置频道欢迎弹窗营销接口 |
| `kill-trip-tms` | request | `reject_dict` | `cleanAds` | 出行活动 TMS 营销资源查询接口 |
| `kill-guide-secondfloor` | request | `reject_dict` | `cleanAds` | 首页二楼活动配置与开屏引导拉取 |
| `kill-damai-popup` | request | `reject_dict` | `cleanAds` | 淘系内大麦演出商业推广弹窗拉取接口 |
| `kill-homepage-launch` | request | `reject_dict` | `cleanAds` | 首页商业启动营销拉取接口 |
| `kill-home-splash` | request | `reject_dict` | `cleanAds` | 手淘首页开屏广告专口拉取 |
| `kill-splash-img` | request | `reject_img` | `cleanAds` | 淘宝开屏全屏尺寸（1080/1125）octopus/tps 推广图返回 200 + 1px 透明 GIF |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/taobao.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://kelee.one/
- https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Loon/Advertising/Advertising.list

## 怎么落实（分层落地与客户端协同）

### 1. 前置配置与 XQUIC / AMDC 会话缓存破冰

- 插件搭配：启用 `ads.plugin`（或 `ads-next.plugin`，二选一）+ `taobao.plugin`，并在主配置 `[General]` 加入 `hijack-dns = *:53` 与 `domain-reject-mode = DNS`。
- 证书完全信任（必需）：`taobao.plugin` 的 4 台 `[MITM]` 主机（`acs.m.taobao.com`、`guide-acs.m.taobao.com`、`gw.alicdn.com`、`heic.alicdn.com`）已默认启用；必须在 iOS 安装 Loon CA 后进入 `设置 → 通用 → 关于本机 → 证书信任设置` 打开**完全信任**，否则会出现淘宝连不上网或首页空白。
- 消除 XQUIC / AMDC 旧连接缓存（决定是否真能拦住开屏）：手淘通过 `amdc.m.taobao.com` 调度并优先走基于 UDP 的 XQUIC，且会在本地沙盒缓存历史连接策略。首次启用或更新插件后请按顺序执行：① 确保 Loon 运行且开启上述 4 条 `PROTOCOL,QUIC` 回退规则 → ② **彻底划掉杀掉淘宝后台进程** → ③ 开关一次飞行模式或重启 Loon 清空旧 UDP/QUIC 会话池 → ④ 冷启动淘宝并在 Loon 请求日志确认 `acs`/`guide-acs` 请求命中 `[Rewrite]` 返回 `reject_dict(200)`。

### 2. 兼容止损与可选分组边界

- 14 条 `[Rewrite]` 由 `[Argument]` `cleanAds`（默认 `true`）统一驱动（此外 `match.p4p.1688.com` 已随 `alimama` SDK 组默认拦截生效）。若随手淘后续大版本升级出现**首页主体空白或局部楼层消失**，可保留 `kill-home-splash`（`mtop.taobao.wireless.home.splash.awesome.get`），在插件本地副本中先关闭或注释 `kill-homepage-launch`（`wireless.home.newface.awesome.get`）验证恢复；注：`mtop.taobao.cloudvideo`（含商品详情视频）、`mtop.taobao.search` 与 `mtop.relationrecommend` 均与正常商品/搜索混装，切勿整口 `reject_dict`。
- 营销活动 H5 弹层异常：当前 `alibaba` 组收录了 `poplayer.template.alibaba.com`（依据 Cuttlefish/ddgksf2013 拦淘宝弹窗经验），极少数促销活动 H5 若依赖 PopLayer 容器出现白屏/按钮失灵，在主配置顶部为 `poplayer.template.alibaba.com` 加 `DIRECT` 放行即可；如不愿安装 CA 证书，可将 `cleanAds` 改为 `false` 并注释 `[MITM]` 两行退回零证书纯 DNS 形态。
- 严禁开启或误加红线：`amdc` 组（`amdc.m.taobao.com`、`umc.danuoyi.alicdn.com`）保持默认关闭以防重连耗电与卡转圈；`ossgw.alicdn.com`（DinamicX/Weex 模板）、`audid-api(-sg).taobao.com`（订单/风控凭证）、`tce.alicdn.com`、`sjarvis.taobao.com`、`aeis.alicdn.com`（滑块验证）与 `cdn.ynuf.aliapp.org` 永不进黑洞。
- `telemetry`（UT / ARMS / CNZZ / 饿了么分片）与 `simba_click`（直通车推广跳转）默认关闭：仅在日志核对不影响已购订单、返佣跳转与客诉工单后按需取消注释。

### 3. App 内深度降噪 + 系统级掐断「摇一摇」跳转

- **淘宝 / 手机天猫 App 内设置**：① `我的淘宝 → 设置 → 隐私 → 推荐管理 → 关闭个性化推荐`；② `隐私 → 广告管理 → 关闭个性化广告`；③ 顺手关闭 `隐私` 内的 `搜索推荐` 与 `购物车推荐`；④ `设置 → 通知管理` 关闭「发现精选 / 活动提醒 / 营销推送」。
- **iOS 27.2+ 彻底防摇一摇跳转（2026-10-27 上线，需中国大陆 Apple ID）**：`设置 → 隐私与安全 → 运动与健身 → 限制动作数据 → 编辑 → 勾选 淘宝`，从系统底层阻断本地缓存开屏图读取陀螺仪误跳。
- **Android 传感器禁止 + GKD 跳开屏**：系统设置搜索 `设备动作与方向` / `身体传感器` 对 **淘宝** 设为 `禁止`；静态开屏倒计时画面可配合 GKD 订阅自动点击「跳过」。

## 红线与天花板（如实）

- 红线：*.taobao.com / *.tmall.com / *.alicdn.com 整族承载登录、订单、购物车、商品图与播放；本插件只做精确广告子域和广告路径，绝不做 DOMAIN-SUFFIX 整域。
- acs.m.taobao.com 与 guide-acs.m.taobao.com 是 mtop 主网关，交易与广告同域；DNS 层不黑洞它们，只在 MITM + [Rewrite] v2 层按 10 条广告 API 路径返回 200 空字典。
- v1.2.0 启用 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] cleanAds 开关（默认开）驱动 10 条 reject_dict(200) + 1 条 reject_img(200) 规则及 4 台解密主机的 QUIC 回退，解决注释态增强层在订阅插件下无法直接开启的问题。
- 证据基线：可莉淘宝插件规则事实 + blackmatrix7 Advertising + anti-AD；淘宝 IPA 10.68.10 的 mtop 广告前缀已在公开主配置有独立证据。
- 红线补充：h5api.m.taobao.com 是 H5 交易/登录接口；login.taobao.com 是淘宝登录入口；passport.taobao.com 是淘宝账号/通行证；sec.taobao.com 是淘宝风控/安全接口；gw.alicdn.com 是图片/素材 CDN；img.alicdn.com 与 heic.alicdn.com 是商品图 CDN。
- 2026-11-18 深度误杀剔除、UT 分片补齐与 Rewrite 路径加固：① 致命误杀剔除——audid-api.taobao.com 实为阿里设备身份/安全凭证接口（Ali User Device ID），GitHub/StevenBlack 实证拦截后导致「我的订单」加载失败或触发风控，从 ads 阿里妈妈 SDK 组移除并写入本插件红线 audid-api.taobao.com 永不拦截；② 红线与共用渲染域排除——sjarvis.taobao.com（聚安全风控大脑）、cdn.ynuf.aliapp.org（UMID 设备指纹）、tce.alicdn.com（TCE 前端模板引擎，3 份清单设 @@ 白名单）、dorangesource.alicdn.com（Orange 灰度动态配置）、accscdn.m.taobao.com（ACCS 长连接 CDN）、hybrid.miniapp.taobao.com（淘宝小程序混合容器）、asearch.alicdn.com（手淘搜索图与 UI CDN）划入红线；③ 百川套件与初始化依赖排除——mum.alibabachengdun.com / fourier.alibaba.com / fourier.taobao.com / aplus.alibaba.com（拦截报告易致网页白屏或开屏卡顿）、baichuan-sdk.* / nbsdk-baichuan.* / acs4baichuan.m.taobao.com（百川电商跳转与授权套件）进台账排除；④ 纯广告域与埋点补齐——通过 alimama 注入新增 atanx2.alicdn.com / afpmm.alicdn.com / afp.alicdn.com / ilce.alicdn.com / strip.taobaocdn.com / kb-render.alicdn.com；默认关 telemetry 补齐 adash* UT 分片及 retcode.taobao.com / umdc.aliapp.org；默认关 simba_click 补齐 re/ai.taobao.com。⑤ 原生 Rewrite 加固与协议边界——新增 kill-home-splash 拦截 mtop.taobao.wireless.home.splash.awesome.get（手淘首页开屏）；kill-damai-popup 与 kill-homepage-launch 尾锚放宽至 (?:/|\?|$) 兼容 MTOP 版本后缀（/1.0/?）；搜索直通车接口 mtop.taobao.wsearch.appsearch 与自然商品混装数组（暂缺真机响应样本不做猜测性 jq）；amdc.m.taobao.com/amdc/mobileDispatch 下发 Tnet SPDY/XQUIC 策略但拦截易触发重连耗电与卡转圈，故 amdc 保持默认关、先靠 QUIC 回退承接 acs 解密。
- 2026-11-18 第二轮 CDN 模板误杀拆雷与阿里生态全扫描：① 重要拆雷移出生效组——ossgw.alicdn.com 在 25 源仅 1hosts-lite 单源收录，开源社区明确报告其同时托管手淘/天猫 DinamicX 与 Weex 动态布局模板（tb_shop_recommend / detail_o2o），整域黑洞可致商品详情页与推荐模块白屏，正式移出 ali_ad_hosts 并写入红线 ossgw.alicdn.com；hudong.alicdn.com 在 25 源 0 命中且承载店铺互动/大促活动 H5 静态资源，移出默认生效组转入默认关 ali_optional；② 海外设备凭证红线补齐——audid-api-sg.taobao.com（2 源，audid-api.taobao.com 新加坡/跨境镜像）同列红线永不拦截；③ 高共识 0 @@ 纯广告 CDN 与多源遥测补齐——通过 alimama SDK 组自动注入 gma.alicdn.com（4 源 0 @@）与 aecpm.alicdn.com（3 源 0 @@）；阿里云文档实证 umc.danuoyi.alicdn.com 实为 /multi_dns_resolve 多线 HTTPDNS 调度接口（3 源），并入默认关 amdc 组不误作广告域；默认关 telemetry 补齐 hydra.alibaba.com（5 源 0 @@）、dmtracking/dmtracking2.alibaba.com（3~4 源 0 @@）、stat.alibaba.com（2 源 0 @@）、adash-c.m/ut.taobao.com、ae-alimelog/alimelog.taobao.com 及 h-adashx4yt.ut.taobao.com；默认关 simba_click 补齐 g.click.taobao.com / click.taobao.com / show.re.taobao.com。
- 2026-11-18 第三轮阿里全生态 CDN/ARMS/CNAME 与误杀红线纵深勘察：① 补入 3 项明确会触发误杀的阿里域入红线与台账排除：sdkinit.taobao.com（SDK 初始化强依赖，拦截易致冷启白屏或转圈）、tbskip.taobao.com（3 家清单设 @@ 例外，拦则订单搜索与淘口令跳转失效）、err.taobao.com（异常路由提示落地页）及 acs-mum.alibabachengdun.com（城盾初始化依赖）；② 默认关 telemetry（同步入 ads analytics）补全 9 项高共识 0 @@ 阿里/O2O/CNAME 遥测端：adash.man.aliyuncs.com（5 源 0 @@ 阿里移动分析）、rum.aliyuncs.com（6 源 0 @@ ARMS 真实用户体验监控）、all.cnzz.com.danuoyi.tbcache.com（4 源 0 @@ CNZZ CNAME 节点）、umeng.com.gds.alibabadns.com（3 源 0 @@ 友盟 GSLB 别名）、adashx.ut.ele.me / h-adashx.ut.ele.me（4 源 0 @@）/ v6-adashx.ut.ele.me / app-monitor.ele.me（3 源 0 @@ 淘宝内嵌饿了么 O2O UT/监控）及 rj.m.taobao.com（2 源）；③ 默认关 simba_click 补全 simaba.taobao.com（3 源 0 @@ 历史变体）、simaba.m.taobao.com 与 simba.m.taobao.com。
- 2026-11-18 第四轮风控滑块红线与 CNAME 纵深收敛：① 补入阿里 AWSC 滑块/智能验证码核心域 aeis.alicdn.com 入红线与台账排除（避免触发无限滑块或登录风控）；② 默认关 telemetry（同步入 ads analytics）补齐 beacon-api.aliyuncs.com.gds.alibabadns.com（2 源 0 @@，beacon-api.aliyuncs.com GSLB CNAME 别名），triage_exclude 纳入 error.taobao.com.danuoyi.tbcache.com（err.taobao.com CDN 别名）；③ 对照 25 源全部 @@ 例外规则锁定共用根边界（mmstat.com/eg.js 与 count.taobao.com/counter 等 3 源白名单表明核心共用根仅允许精确广告子域/路径）。
- 2026-11-18 第五轮真机落地与协议破冰指引固化：在 plugins/taobao/README.md 增补 XQUIC/AMDC 会话缓存清除冷启流程、kill-homepage-launch（newface.awesome.get）新版兼容性回退策略、poplayer.template.alibaba.com H5 弹层误杀排查，以及手淘隐私设置 + iOS 27.2+「限制动作数据」/ Android 传感器禁止+GKD 联合方案。
- 2026-11-18 第六轮 1688 / 菜鸟 / 飞猪 / 饿了么拓展生态深挖与接口边界锁定：① 通过 alimama SDK 组自动注入 5 源 0 @@ 的 match.p4p.1688.com（阿里 1688 网销宝 P4P 竞价广告匹配引擎）；② 默认关 telemetry 增补 1hosts-lite 0 @@ 的菜鸟/飞猪 UT 分片 adashx.ut.cainiao.com / h-adashx.ut.cainiao.com / adashx.ut.fliggy.com / h-adashx.ut.fliggy.com（同步入 ads analytics）；③ 补齐关联生态主族与业务红线：1688.com（主站仅 b2bxad 路径规则，全族不整域黑洞）、pass.1688.com（3 清单 @@||pass.1688.com^$subdocument 登录入口白名单）、cainiao.com（菜鸟主族不整域黑洞）、fliggy.com（飞猪主族不整域黑洞）、ele.me（饿了么/淘宝闪购主族不整域黑洞），并将社区实证拦截易白屏或断单的 grand.ele.me、client-api.ele.me 与 newton-api.ele.me（饿了么客户端及闪购强依赖业务接口，社区实证拦截引发白屏或下单失败）写入红线与台账排除，cui.m.1688.com 按单源移动 UI 排除；④ 核查确认 mtop.taobao.cloudvideo（含商品详情视频）、mtop.taobao.search 与 mtop.relationrecommend 均属混装业务接口，不盲目整口 reject_dict。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/taobao.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 96 条，[Rule] 31 条。
