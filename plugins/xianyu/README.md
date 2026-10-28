# 闲鱼 · 去广告（能力有限）

> 闲鱼广告 100% 内嵌 goofish mtop 主网关（splash.ads / nextfresh bizType / item.recommend bizType=mamaAD 均为同域 API 名，九家主流黑名单 goofish 零命中即侧证）。DNS 层只能补阿里广告 SDK 端点 iyes.youku.com、淘宝客 Tunion 归因接口与 AMDC 调度——零证书收益≈0-5%；信息流同域广告需可选 MITM 层用 Loon 原生 response.json.jq 删字段，默认注释。

版本 **1.4.0** ｜ 最低 Loon **3.5.1(983)** ｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 xianyu.plugin](https://img.shields.io/badge/Loon-导入%E9%97%B2%E9%B1%BC%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E8%83%BD%E5%8A%9B%E6%9C%89%E9%99%90%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fxianyu%2Fxianyu.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/xianyu/xianyu.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 阿里广告 SDK 端点（闲鱼净化模块唯一 REJECT 域） | A | 启用 | iyes.youku.com=阿里广告 SDK 端点（apiv4-iyes 为其分片,整域+通配）;anti-AD/AdGuard/hagezi/wool XianYu 模块四源收录。 |
| 淘宝客/阿里妈妈 API 端点 | B | 启用 | tunion-api.m.taobao.com=淘宝联盟(Tunion) CPS 广告归因接口,taobao.com 是共享主域、全局 ads 插件的 =alimama.com 整域黑洞罩不到它,故在此精确单列;afpapi.alimama.com 已由 ads 插件 alibaba 组整域覆盖,此处只作按 App 开关的完整起见。DoH 实测 afpapi CNAME 终结于 adsz.wagbridge.tanx.alimama.com(Tanx=阿里妈妈 AdX)。 |
| 淘宝系 AMDC HTTPDNS 调度（默认关） | B | 默认关闭 | amdc.m/amdcopen.m.taobao.com=阿里 HTTPDNS 调度;闲鱼净化脚本专改 /amdc/mobileDispatch。拦=广告域解析绕过消失,但阿里系 App 若无回退逻辑可能拖慢建连——默认关,验证后再开。 |
| 阿里妈妈 / TanX / 阿里广告监测（引用组） | A | 启用 | 域名真源见 ads 组/SDK 库 共 3 域 / 0 规则。 |

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

闲鱼 iOS 未做证书固定：开屏/曝光计数是 mtop 主网关 acs.m.goofish.com 的路径名（splash.ads / idle.ad.expose），信息流广告则在同域 API 的 JSON 字段里（nextfresh 分区 / item.recommend 的 bizType=mamaAD）。黑洞整网关=废掉 App，正解是 MITM 后按路径 reject，或用 Loon 原生 response.json.jq 只删广告字段、保留 mtop 包络。下列 jq 来自 ddgksf2013 GoofishAds 与 fmz200 blockAds 两个公开模块（后者已在用同域 http-response-jq），默认整段注释；建议逐条启用、真机确认后再加下一条。fmz200 的 circle.visited（最近访问）与 fun.follow.often.visit（常访问）更像功能/历史而非广告，刻意不收。

- 解密主机（`[MITM] hostname`，2 个）：`acs.m.goofish.com`, `g-acs.m.goofish.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，2 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 与 `response.json.jq` 都会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，2 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https?://(g-)?acs\.m\.goofish\.com/gw/mtop.*splash\.ads,REJECT-DICT
# URL-REGEX,^https?://(g-)?acs\.m\.goofish\.com/gw/mtop\.idle\.ad\.expose,REJECT-DICT
```

- 响应 JSON 改写（`response.json.jq`，15 条，注释态）：MITM 解密后按公开模块的 jq 只删广告字段/节点、保留 mtop 包络；与 Response Script 二选一（本层不含脚本）。建议逐条启用、真机确认后再加下一条。

```text
# 来源 ddgksf2013：商品底部推荐：只删 bizType=mamaAD 的卡片
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idle\.item\.recommend(?:\/|\?|$)/ then response.json.jq(`.data.cardList |= map(select(.cardData.bizType != "mamaAD"))`)
# 来源 ddgksf2013：首页右下角悬浮球：留一个空 strategy 占位
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idle\.user\.strategy\.list(?:\/|\?|$)/ then response.json.jq(`.data.strategies = [{}]`)
# 来源 ddgksf2013：搜索框预填/热词：留一个空占位
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idlemtopsearch\.search\.shade(?:\/|\?|$)/ then response.json.jq(`.data.singleShadeWords = [{}]`)
# 来源 ddgksf2013：搜索页「猜你可能找」卡片
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idlemtopsearch\.item\.search\.activate(?:\/|\?|$)/ then response.json.jq(`.data.cardList = [{}]`)
# 来源 ddgksf2013：首页顶部 Tab：去掉 saveMoney 推广位
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idlehome\.home\.circle\.list(?:\/|\?|$)/ then response.json.jq(`.data.circleList |= map(select(.bizCode != "saveMoney"))`)
# 来源 ddgksf2013：首页信息流：顶部只留首项、分区只留 item（源模块口径较激进）
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idlehome\.home\.nextfresh(?:\/|\?|$)/ then response.json.jq(`.data.homeTopList |= [ .[0] ] | .data.sections |= map(select(.data.bizType == "item"))`)
# 来源 ddgksf2013：搜索结果信息流：只留 item 结果（源模块口径较激进）
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idlemtopsearch\.search(?:\/|\?|$)/ then response.json.jq(`.data.resultList |= map(select(.data.item.main.clickParam.args.biz_type == "item"))`)
# 来源 ddgksf2013：本地信息流：分区只留 item（源模块口径较激进）
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idle\.local\.home(?:\/|\?|$)/ then response.json.jq(`.data.sections |= map(select(.data.bizType == "item"))`)
# 来源 ddgksf2013：搜索发现页：删除 resultList（源模块口径较激进）
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idlemtopsearch\.search\.discover(?:\/|\?|$)/ then response.json.jq(`del(.data.resultList)`)
# 来源 ddgksf2013：我的页面：清空 ability 并只留 head/user/trade 分区（源模块口径最激进，建议最后单开验证）
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.idle\.user\.page\.my\.adapter(?:\/|\?|$)/ then response.json.jq(`.data.ability=[] | .data.container.sections |= map(select(.sectionBizCode | test("head|user|trade")))`)
# 来源 ddgksf2013：我的页面底部商品推荐：删除 sections（源模块口径较激进）
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idle\.item\.buy\.feeds(?:\/|\?|$)/ then response.json.jq(`del(.data.sections)`)
# 来源 fmz200：群聊/消息页 banner 位
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idle\.group\.myself\.banner(?:\/|\?|$)/ then response.json.jq(`.data.bannerList = []`)
# 来源 fmz200：圈子页 banner 位
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idle\.circle\.myself\.banner\/1\.0(?:\/|\?|$)/ then response.json.jq(`.data.bannerList = []`)
# 来源 fmz200：消息页推荐位
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idle\.playboy\.recommend\/2\.0(?:\/|\?|$)/ then response.json.jq(`.data.recommends = [] | .data.items = [] | .data.next = false`)
# 来源 fmz200：商品推荐列表：清空 cardList（fmz200 口径，整列清空）
# response if ${url} ~= /^https?:\/\/(g-)?acs\.m\.goofish\.com\/gw\/mtop\.taobao\.idle\.item\.recommend\.list(?:\/|\?|$)/ then response.json.jq(`.data.cardList = []`)
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rewrite]` 头与所需 `response.json.jq` 行的注释 → ④取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://github.com/ddgksf2013/Rewrite/blob/master/AdBlock/GoofishAds.conf
- https://github.com/fmz200/wool_scripts/blob/main/Surge/module/blockAds.module

## 红线与天花板（如实）

- 红线：*.goofish.com / *.idlefish.com / mtop 网关域（g-acs.m.goofish.com→alibabacorp mtop ingress）全部是核心功能;acs.m.goofish.com 出现在个别模块的 REJECT 里是错误规则,打死整个 App——拒收。
- 取证否决：m.goofish.com / awl.goofish.com 实测 NXDOMAIN（不存在）;xianyu.mobi 与 blackmatrix7 的 16 个乱码域是淘宝短链跳转服务（cname.tb.cn），拦=断分享链接;cdn.ynuf.aliapp.org=阿里无线安全 UMID 指纹,禁拦。
- 证据基线：闲鱼全部广告面在同域 API 名上——开屏 mtop.taobao.idlecommerce.splash.ads、信息流 nextfresh bizType、底部推荐 bizType==mamaAD（字段名直接点名阿里妈妈）;素材共用 *.alicdn.com 共享 CDN。第三方列表 goofish 域零命中。
- 本插件 [Host]/[Rule] 全设备生效(Loon 无法按 App 限定):同一 SDK 域跨 App 共享黑洞,'按 App 插件'只是分组开关;配合全局 ads 插件 httpdns 组防绕过。
- 第二轮取证复检(2026-10-28)：mma.alimama.com 实测 NXDOMAIN(网传『阿里妈妈端点』不存在,禁凭品牌造域);开屏素材无 alicdn 之外的独立 CDN(墨鱼 GoofishAds.conf 亦无单独素材域);h-adashx.ut.taobao.com=阿里 UT/AdashX 埋点,全阿里系 App 共享,属全局 ads 插件的决策面,不进本按 App 插件。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/xianyu.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 9 条，[Rule] 0 条。
