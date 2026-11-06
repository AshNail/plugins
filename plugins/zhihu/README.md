# 知乎 · 去广告与精简

> 知乎 iOS：自建遥测/分析（zhihu-web-analytics/sugar/crash2）+ 商业化数据追踪（udd1i5）零证书 DNS 黑洞；商业化广告接口（commercial_api/ad-style-service）与推广/预置词走可选原生增强层（REJECT-DICT 空字典，200 状态码防重试）；核心问答/文章/个人页/图床/推送严格设防红线。

版本 **1.0.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 zhihu.plugin](https://img.shields.io/badge/Loon-导入%E7%9F%A5%E4%B9%8E%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%E4%B8%8E%E7%B2%BE%E7%AE%80-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fzhihu%2Fzhihu.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/zhihu/zhihu.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|
| 知乎自建遥测 / 崩溃分析 / 商业化追踪 | A | 启用 | zhihu-web-analytics.zhihu.com（9源，知乎官方 Web/移动端分析）、udd1i5.zhihu.com（5源，商业化追踪与素材 CDN）、sugar.zhihu.com（4源，崩溃上报与监控平台）、crash2.zhihu.com（3源，崩溃分析日志端点）。均非业务数据流，DNS 映射 127.0.0.1 阻断。 |

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

知乎 iOS 的信息流广告、开屏及推荐位与核心 API 共用 api.zhihu.com、www.zhihu.com、zhida.zhihu.com，不可 DNS 黑洞整域。下列 12 条 URL-REGEX 采用 Loon 原生 REJECT-DICT（返回 HTTP 200 + 空字典），使客户端认为广告/推广位已正常返回但无内容，阻断重试并实现干净展示。整段默认注释，启用需安装证书。

- 解密主机（`[MITM] hostname`，3 个，注释态，取消注释才解密）：`api.zhihu.com`, `www.zhihu.com`, `zhida.zhihu.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，3 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，12 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https://api\.zhihu\.com/ad-style-service/request,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/commercial_api/,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/commercial_api/banners_v\d+/app_float_corner,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/commercial_api/answer/\d+/bottom-v\d+,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/next-render\?id=\d+&type=answer,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/related_recommend/feed/waterfall,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/search/preset_words,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/search/related_queries/question/\d+,REJECT-DICT
# URL-REGEX,^https://zhida\.zhihu\.com/ai_ingress/ai_chat/guidance,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/content-distribution-core/bubble/common/show,REJECT-DICT
# URL-REGEX,^https://www\.zhihu\.com/api/v\d+/members/homepage_card,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/people/homepage_entry_v\d+,REJECT-DICT
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://github.com/fkingikelee/fkikelee/blob/main/lpx/Zhihu_remove_ads.lpx
- https://kelee.one/

## 红线与天花板（如实）

- 红线（绝不进任何拦截组）：passport.zhihu.com 账号与安全登录网关 / api.zhihu.com 知乎核心业务 API，问答与文章主服务 / zhuanlan.zhihu.com 知乎专栏核心域名 / unpkg.zhihu.com 前端静态资源与组件加载 / mqtt.zhihu.com 实时消息推送长连接通道 / lc-push.zhihu.com 移动端离线/在线推送通道 / pic1.zhimg.com 静态图片与用户头像图床。
- 知乎主站与业务共享根域 *.zhihu.com，禁止整域通配。
- 知乎图片素材与静态资产共享根域 *.zhimg.com，禁止整域通配。
- 能力天花板与原生设计：zhihu-web-analytics、sugar、crash2、udd1i5 四个自建数据与遥测域走 [Host] 127.0.0.1 零证书黑洞；信息流穿插广告与推荐位走可选增强层 REJECT-DICT（HTTP 200 + 空字典），保持零 JS 脚本。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/zhihu.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 4 条，[Rule] 0 条。
