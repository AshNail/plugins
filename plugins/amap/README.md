# 高德地图 · 去广告与精简 v1.2.1

> 高德地图开屏与同域商业化广告原生复写清理，遥测及日志域黑洞拦截；核心定位导航零接触。

版本 **1.2.1** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 amap.plugin](https://img.shields.io/badge/Loon-导入%E9%AB%98%E5%BE%B7%E5%9C%B0%E5%9B%BE%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%E4%B8%8E%E7%B2%BE%E7%AE%80%20v1.2.1-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Famap%2Famap.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/amap/amap.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 高德自建日志遥测 / 阿里 UT 埋点 / 配置更新 | A | 启用 | logs.amap.com（6源）、dualstack-logs.amap.com（4源）、amap-aos-info-nogw.amap.com（3源）、adashx.ut.amap.com（3源）、h-adashx.ut.amap.com（2源）、v6-adashx.ut.amap.com（2源）。DNS 映射 127.0.0.1 阻断。 |
| 高德商业化广告与擎天广告系统 | A | 启用 | optimus-ads.amap.com（4源，高德擎天广告投放系统）、optimus-ads-ykx.amap.com（1源，广告分片）。DNS 映射 127.0.0.1 阻断。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 4 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

高德地图 iOS 的开屏广告、首页推荐流、路线规划推广卡片、营销消息拉取与打车页面推广信息与核心 API 共用 m5.amap.com、m5-zb.amap.com、center.amap.com 等接口，不可 DNS 黑洞整域。本层默认启用 Loon 原生 [Rewrite] v2 引擎复写（由 cleanAds 开关控制，零 JS 脚本），对 8 条广告与推广路径在 request 阶段直接返回 200 + 空字典（reject_dict(200)），使客户端认为推广位已正常返回但无内容，阻断重试并实现干净展示。

- 解密主机（`[MITM] hostname`，4 个，本层已默认生效）：`m5.amap.com`, `m5-zb.amap.com`, `center.amap.com`, `ai.amap.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，4 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：alimama 开屏、AI 推荐流、路线规划推广卡片、打车订单 Tip、消息中心营销拉取（msgbox/pull）、ASA 广告归因、场景推荐与天气推广位在 request 阶段直接 reject_dict(200) 终止。需已安装并信任 Loon 证书。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-splash` | request | `reject_dict` | `cleanAds` | 高德 alimama 开屏广告接口（aos 与 valueadded 双路径）直接返回 200 + 空字典 |
| `kill-ai-rec` | request | `reject_dict` | `cleanAds` | AI 智能推荐卡片流直接返回 200 + 空字典 |
| `kill-route-card` | request | `reject_dict` | `cleanAds` | 路线规划底部推广服务卡片直接返回 200 + 空字典 |
| `kill-order-tip` | request | `reject_dict` | `cleanAds` | 打车/订单页顶部营销提示横幅直接返回 200 + 空字典 |
| `kill-asa-attribution` | request | `reject_dict` | `cleanAds` | ASA 广告归因上报接口直接返回 200 + 空字典 |
| `kill-scene-recommend` | request | `reject_dict` | `cleanAds` | 首页场景推荐推广位直接返回 200 + 空字典 |
| `kill-weather-ad` | request | `reject_dict` | `cleanAds` | 增值天气挂件推广卡片直接返回 200 + 空字典 |
| `kill-msgbox-pull` | request | `reject_dict` | `cleanAds` | 消息中心营销推送与活动横幅拉取直接返回 200 + 空字典 |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/amap.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://github.com/ddgksf2013/Rewrite/blob/master/AdBlock/Amap.conf
- https://github.com/limbopro/Adblock4limbo

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：restapi.amap.com 核心路线规划、地点搜索与地理编码网关 / ts.amap.com 猎鹰轨迹服务与定位上报核心 API / sns.amap.com 账号与安全服务 / apsrgeo.amap.com 逆地理编码服务，经纬度转换道路门牌地址依赖 / cgicol.amap.com 与 dualstack-cgicol.amap.com 基站定位服务，室内与隧道定位依赖。
- 高德地图业务共享根域 *.amap.com，禁止整域通配。
- 高德基础地图数据共享根域 *.autonavi.com，禁止整域通配。
- 能力天花板与原生设计：logs.amap.com、dualstack-logs.amap.com、amap-aos-info-nogw.amap.com、adashx.ut.amap.com、h-adashx.ut.amap.com、v6-adashx.ut.amap.com、optimus-ads.amap.com、optimus-ads-ykx.amap.com 八个日志遥测与广告域走 [Host] 127.0.0.1 零证书黑洞；开屏、信息流与路线规划推广走 Loon 原生 [Rewrite] v2 引擎复写（reject_dict(200)），零 JS 脚本。
- v1.2.1 升级 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] cleanAds 开关（默认开）驱动 8 条 request 阶段 reject_dict(200) 规则（覆盖 ws/(aos|valueadded)/alimama/splash_screen 与 ws/msgbox/pull 等）+ 4 台同域业务主机的 QUIC 回退（已从 [MITM] 移出已在 [Host] 黑洞的 amap-aos-info-nogw 与 optimus-ads）。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/amap.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 8 条，[Rule] 4 条。
