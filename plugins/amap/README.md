# 高德地图 · 去广告与精简

> 高德地图 iOS/iPadOS：日志与遥测（logs/dualstack-logs/amap-aos-info-nogw/adashx）+ 商业化广告域（optimus-ads）走 [Host] 127.0.0.1 零证书黑洞；开屏 alimama 广告、首页推荐流、路线规划推广卡片、订单 Tip 与通用归因走可选原生增强层（REJECT-DICT / REJECT，保持零 JS 脚本）；核心逆地理编码（apsrgeo）、基站定位（cgicol）、路线规划网关（restapi）与轨迹定位（ts）严格设防红线。

版本 **1.0.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 amap.plugin](https://img.shields.io/badge/Loon-导入%E9%AB%98%E5%BE%B7%E5%9C%B0%E5%9B%BE%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%E4%B8%8E%E7%B2%BE%E7%AE%80-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Famap%2Famap.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/amap/amap.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 高德自建日志遥测 / 阿里 UT 埋点 / 配置更新 | A | 启用 | logs.amap.com（6源）、dualstack-logs.amap.com（4源）、amap-aos-info-nogw.amap.com（3源）、adashx.ut.amap.com（3源）、h-adashx.ut.amap.com（2源）、v6-adashx.ut.amap.com（2源）。DNS 映射 127.0.0.1 阻断。 |
| 高德商业化广告与擎天广告系统 | A | 启用 | optimus-ads.amap.com（4源，高德擎天广告投放系统）、optimus-ads-ykx.amap.com（1源，广告分片）。DNS 映射 127.0.0.1 阻断。 |

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

高德地图 iOS 的开屏广告、首页推荐流、路线规划推广卡片与打车页面推广信息与核心 API 共用 m5.amap.com、m5-zb.amap.com、center.amap.com 等接口，不可 DNS 黑洞整域。下列 7 条 URL-REGEX 采用 Loon 原生 REJECT-DICT 与 REJECT，使客户端认为推广位已正常返回但无内容，阻断重试并实现干净展示。整段默认注释，启用需安装证书。

- 解密主机（`[MITM] hostname`，6 个，注释态，取消注释才解密）：`m5.amap.com`, `m5-zb.amap.com`, `center.amap.com`, `amap-aos-info-nogw.amap.com`, `ai.amap.com`, `optimus-ads.amap.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，6 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，7 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https?://.*\.amap\.com/ws/aos/alimama/splash_screen(\?.*)?$,REJECT-DICT
# URL-REGEX,^https?://.*\.amap\.com/v\d/ai_rec/.*$,REJECT-DICT
# URL-REGEX,^https?://.*\.amap\.com/ws/faas/amap-navigation/card-service-route-plan(\?.*)?$,REJECT-DICT
# URL-REGEX,^https?://.*\.amap\.com/ws/boss/order_web/\w{8}_information(\?.*)?$,REJECT-DICT
# URL-REGEX,^https?://.*\.amap\.com/ws/asa/ads_attribution(\?.*)?$,REJECT
# URL-REGEX,^https?://.*\.amap\.com/ws/shield/scene/recommend(\?.*)?$,REJECT-DICT
# URL-REGEX,^https?://.*\.amap\.com/ws/valueadded/weather(\?.*)?$,REJECT-DICT
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://github.com/ddgksf2013/Rewrite/blob/master/AdBlock/Amap.conf
- https://github.com/limbopro/Adblock4limbo

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：restapi.amap.com 核心路线规划、地点搜索与地理编码网关 / ts.amap.com 猎鹰轨迹服务与定位上报核心 API / sns.amap.com 账号与安全服务 / apsrgeo.amap.com 逆地理编码服务，经纬度转换道路门牌地址依赖 / cgicol.amap.com 与 dualstack-cgicol.amap.com 基站定位服务，室内与隧道定位依赖。
- 高德地图业务共享根域 *.amap.com，禁止整域通配。
- 高德基础地图数据共享根域 *.autonavi.com，禁止整域通配。
- 能力天花板与原生设计：logs.amap.com、dualstack-logs.amap.com、amap-aos-info-nogw.amap.com、adashx.ut.amap.com、h-adashx.ut.amap.com、v6-adashx.ut.amap.com、optimus-ads.amap.com、optimus-ads-ykx.amap.com 八个日志遥测与广告域走 [Host] 127.0.0.1 零证书黑洞；开屏、信息流与路线规划推广走可选增强层 REJECT-DICT，保持零 JS 脚本。
- 证据：ddgksf2013、Adblock4limbo、anti-AD、AdRules 公开规则库的高德地图广告处置逻辑。本插件不搬运其混淆 JS（如 amap.js），改用 Loon 原生 URL-REGEX 与 REJECT-DICT 规则实现等价效果。整段默认注释，安装证书后按需启用。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/amap.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 8 条，[Rule] 0 条。
