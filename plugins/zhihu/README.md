# 知乎 · 去广告与精简

> 知乎 iOS：自建遥测/分析（zhihu-web-analytics/sugar/crash2）+ 商业化数据追踪（udd1i5）零证书 DNS 黑洞；同域商业化广告接口（commercial_api/ad-style-service）与推广/预置词默认启用 Loon 原生 [Rewrite] v2 引擎复写（cleanAds 开关默认开，request 阶段 reject_dict(200) 返回空字典防重试，零 JS 脚本）；核心问答/文章/个人页/图床/推送严格设防红线。前置：同域复写层需已安装并信任 Loon 证书。

版本 **1.1.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 净化层默认启用（`[Argument]`+`[MITM]`+`[Script]` 三层已在文件里生效，须已装并信任 Loon 证书）· 拦截面 `[Host]`/`[Rule]`

## 安装

[![一键导入 zhihu.plugin](https://img.shields.io/badge/Loon-导入%E7%9F%A5%E4%B9%8E%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%E4%B8%8E%E7%B2%BE%E7%AE%80-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fzhihu%2Fzhihu.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/zhihu/zhihu.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 知乎自建遥测 / 崩溃分析 / 商业化追踪 | A | 启用 | zhihu-web-analytics.zhihu.com（9源，知乎官方 Web/移动端分析）、udd1i5.zhihu.com（5源，商业化追踪与素材 CDN）、sugar.zhihu.com（4源，崩溃上报与监控平台）、crash2.zhihu.com（3源，崩溃分析日志端点）。均非业务数据流，DNS 映射 127.0.0.1 阻断。 |
| QUIC 回退（增强层配套） | A | 启用 | 只对 `PROTOCOL,QUIC` 生效：拒的是 HTTP/3 这条通道、不是这台主机，同一主机的 TCP 正文/书架零影响。共 3 条。 |

## 默认启用的 MITM 层（本 App 未做证书固定；必须已装并信任 Loon 证书）

知乎 iOS 的信息流广告、开屏及推荐位与核心 API 共用 api.zhihu.com、www.zhihu.com、zhida.zhihu.com，不可 DNS 黑洞整域。本层默认启用 Loon 原生 [Rewrite] v2 引擎复写（由 cleanAds 开关控制，零 JS 脚本），对 13 条商业化广告、推荐流与预置词路径在 request 阶段直接返回 200 + 空字典（reject_dict(200)），使客户端认为广告/推广位已正常返回但无内容，阻断重试并实现干净展示。

- 解密主机（`[MITM] hostname`，3 个，本层已默认生效）：`api.zhihu.com`, `www.zhihu.com`, `zhida.zhihu.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，3 条，已生效）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX`、`[Rewrite]` 复写与脚本绑定全部静默失效；它拒的是 QUIC 这条通道，同一主机的 TCP 请求零影响。

### 开关（`[Argument]`）

| 开关 | 默认 | 作用 |
|---|---|---|
| `cleanAds` | true | 启用 Loon 原生 [Rewrite] v2 引擎复写：commercial_api、ad-style-service、回答底部推广、瀑布流推荐、搜索预置词、直答引导与营销气泡在 request 阶段直接 reject_dict(200) 终止。需已安装并信任 Loon 证书。 |

### 净化复写（`[Rewrite]`）

| 规则 | 阶段 | 动作 | 开关 | 行为 |
|---|---|---|---|---|
| `kill-ad-style` | request | `reject_dict` | `cleanAds` | 知乎广告样式服务请求直接返回 200 + 空字典 |
| `kill-api-commercial` | request | `reject_dict` | `cleanAds` | api.zhihu.com 商业化广告接口整族（开屏/Banner/角标/回答底部）直接返回 200 + 空字典 |
| `kill-float-corner` | request | `reject_dict` | `cleanAds` | 右下角悬浮角标推广位直接返回 200 + 空字典 |
| `kill-answer-bottom` | request | `reject_dict` | `cleanAds` | 回答底部商业推广位直接返回 200 + 空字典 |
| `kill-next-render` | request | `reject_dict` | `cleanAds` | 回答下方穿插渲染卡片直接返回 200 + 空字典 |
| `kill-related-waterfall` | request | `reject_dict` | `cleanAds` | 相关推荐瀑布流直接返回 200 + 空字典 |
| `kill-preset-words` | request | `reject_dict` | `cleanAds` | 搜索框预置推广词直接返回 200 + 空字典 |
| `kill-related-queries` | request | `reject_dict` | `cleanAds` | 问题页相关搜索词推广直接返回 200 + 空字典 |
| `kill-zhida-guidance` | request | `reject_dict` | `cleanAds` | 知乎直答 AI 引导卡片直接返回 200 + 空字典 |
| `kill-bubble-show` | request | `reject_dict` | `cleanAds` | 内容分发气泡提示直接返回 200 + 空字典 |
| `kill-homepage-card` | request | `reject_dict` | `cleanAds` | 个人主页推广卡片直接返回 200 + 空字典 |
| `kill-www-commercial` | request | `reject_dict` | `cleanAds` | www.zhihu.com 网页/混合容器商业化广告接口整族直接返回 200 + 空字典 |
| `kill-homepage-entry` | request | `reject_dict` | `cleanAds` | 个人中心推广入口模块直接返回 200 + 空字典 |

> 净化主力放在引擎侧：`reject_*` 与 `response.json.*` 由 Loon 自己解压 `Content-Encoding: gzip`，脚本链不碰压缩体。脚本读响应体必须先 ungzip，而 `$utils.ungzip` 只有 Build ≥ 988 才有——低版本就是静默 passthrough，这正是「净化不生效」的那条链。

> 全层由 `src/apps/zhihu.json` 的 `enhance` 整段生成（`tools/build-apps.py`），lint 逐行对账产物——直接改生成物会在下一次构建被覆盖。

前提与步骤：①Loon 装并信任证书（本层已默认解密这些主机） → ②要自动化就把 `[Argument]` 里的对应开关改成 true（默认关的那几个） → ③确认可用：冷启动后看日志里复写装载计数（`Reload rewrites:`）与脚本侧锚点行，再用探针绑定判断复写是否接管（探针消失 = 复写命中）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。
> 反过来说：本层已经默认写在生效配置里，**证书没装好时这些主机的 TLS 会失败**——不是「没生效」而是「连不上」。装好证书再评估，或直接把 `[MITM]` 那两行注释掉退回零证书形态。

证据：
- https://github.com/fkingikelee/fkikelee/blob/main/lpx/Zhihu_remove_ads.lpx
- https://kelee.one/
- https://github.com/limbopro/Adblock4limbo/blob/main/Zhihu.conf

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：passport.zhihu.com 账号与安全登录网关 / api.zhihu.com 知乎核心业务 API，问答与文章主服务 / zhuanlan.zhihu.com 知乎专栏核心域名 / unpkg.zhihu.com 前端静态资源与组件加载 / mqtt.zhihu.com 实时消息推送长连接通道 / lc-push.zhihu.com 移动端离线/在线推送通道 / pic1.zhimg.com 静态图片与用户头像图床。
- 知乎主站与业务共享根域 *.zhihu.com，禁止整域通配。
- 知乎图片素材与静态资产共享根域 *.zhimg.com，禁止整域通配。
- 能力天花板与原生设计：zhihu-web-analytics、sugar、crash2、udd1i5 四个自建数据与遥测域走 [Host] 127.0.0.1 零证书黑洞；信息流穿插广告与推荐位走 Loon 原生 [Rewrite] v2 引擎复写（reject_dict(200)，HTTP 200 + 空字典），保持零 JS 脚本。
- v1.1.0 启用 Loon 原生 [Rewrite] v2 引擎复写层（enhance.active=true）：通过 [Argument] cleanAds 开关（默认开）驱动 13 条 request 阶段 reject_dict(200) 规则 + 3 台解密主机的 QUIC 回退，解决注释态增强层在订阅插件下无法直接开启的问题。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/zhihu.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 4 条，[Rule] 3 条。
