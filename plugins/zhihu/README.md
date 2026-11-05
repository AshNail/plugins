# 知乎 · 去广告（原生规则层）

> 吸纳可莉「知乎去广告」的 30 条 Loon Rewrite 事实：请求侧广告/推广接口返回 200 空字典，响应侧用原生 response.json.jq 删除广告与推广字段；不包含脚本。只做精确 API 路径，不黑洞 *.zhihu.com / *.zhimg.com 主域，登录、内容、会员与图片链路保持。

版本 **1.0.0** ｜ 功能基线 Loon **3.5.1(983)**+ （iOS/tvOS 口径；Mac 版是 0.x 独立一条线，插件头不声明门槛）｜ 零证书 · 纯 `[Host]`/`[Rule]`（另含默认注释的可选 MITM 增强层，见下）

## 安装

[![一键导入 zhihu.plugin](https://img.shields.io/badge/Loon-导入%E7%9F%A5%E4%B9%8E%20%C2%B7%20%E5%8E%BB%E5%B9%BF%E5%91%8A%EF%BC%88%E5%8E%9F%E7%94%9F%E8%A7%84%E5%88%99%E5%B1%82%EF%BC%89-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fzhihu%2Fzhihu.plugin)

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/zhihu/zhihu.plugin
```

## 拦截组

| 组 | 置信 | 状态 | 说明 |
|---|---|---|---|

## 可选 MITM 增强层（默认整段注释，不装证书 = 永不生效）

知乎的可莉模块全部是原生 Loon Rewrite：请求侧拒绝广告/推广接口，响应侧删除广告字段。下面按 Loon 原生语法重写，默认整段注释；启用后先验首页/推荐/搜索/回答/评论/登录。

- 解密主机（`[MITM] hostname`，5 个）：`api.zhihu.com`, `www.zhihu.com`, `page-info.zhihu.com`, `m-cloud.zhihu.com`, `zhida.zhihu.com`
- 配套 QUIC 回退（`AND,((DOMAIN-SUFFIX,<域>),(PROTOCOL,QUIC)),REJECT`，5 条，注释态）：MITM 只解密 TCP，App 走 HTTP/3 时 `URL-REGEX` 与 `response.json.jq` 都会静默失效；启用本层时应连同这些行一起取消注释。
- 路径级规则（`URL-REGEX`，15 条，命中即拦对应广告接口/素材，不影响同域功能请求）：

```text
# URL-REGEX,^https://api\.zhihu\.com/ad-style-service/request$,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/commercial_api/,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/commercial_api/banners_v\d/app_float_corner\?,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/next-render\?id=\d+&type=answer,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/commercial_api/answer/\d+/bottom-v\d$,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/related_recommend/feed/waterfall\?,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/search/preset_words\?,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/search/related_queries/question/\d+$,REJECT-DICT
# URL-REGEX,^https://zhida\.zhihu\.com/ai_ingress/knowledge/square/categories/feeds\?categoryId=1%7D$,REJECT-DICT
# URL-REGEX,^https://zhida\.zhihu\.com/ai_ingress/ai_chat/guidance$,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/content-distribution-core/bubble/common/show$,REJECT-DICT
# URL-REGEX,^https://www\.zhihu\.com/api/v\d/members/homepage_card$,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/people/homepage_entry_v\d$,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/kvip/right/my_card\?,REJECT-DICT
# URL-REGEX,^https://api\.zhihu\.com/unlimited/go/my_card/v\d\?,REJECT-DICT
```

- 响应 JSON 改写（`response.json.jq`，14 条，注释态）：MITM 解密后按公开模块的 jq 只删广告字段/节点、保留 mtop 包络；与 Response Script 二选一（本层不含脚本）。建议逐条启用、真机确认后再加下一条。

```text
# 来源 https://kelee.one/：底部 Tab 只保留关注/推荐/热榜/圈层
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/root\/tab\/v\d(?:\?.+)?$/ then response.json.jq(`.tab_list |= map(select(.tab_type == "follow" or .tab_type == "recommend" or .tab_type == "hot" or .tab_type == "ring_tab"))`)
# 来源 https://kelee.one/：推荐流只保留 ComponentCard
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/topstory\/recommend\?/ then response.json.jq(`.data |= map(select(.type == "ComponentCard"))`)
# 来源 https://kelee.one/：问题 feed 删除 ad_info
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/questions\/\d+\/feeds\?/ then response.json.jq(`del(.ad_info)`)
# 来源 https://kelee.one/：评论根节点删除氛围投票配置
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/comment_v\d\/(answers|pins)\/\d+\/root_comment\?/ then response.json.jq(`del(.atmosphere_voting_config)`)
# 来源 https://kelee.one/：回答详情删除第三方商业与浮动搜索词
# response if ${url} ~= /^https?:\/\/(api|page-info)(?:\.zhihu)?\.com\/answers\/v\d\/\d+(?:\?.*)?$/ then response.json.jq(`del(.third_business, .float_search_word)`)
# 来源 https://kelee.one/：回答正文删除 card 片段
# response if ${url} ~= /^https?:\/\/(api|page-info)(?:\.zhihu)?\.com\/answers\/v\d\/\d+(?:\?.*)?$/ then response.json.jq(`.structured_content.segments |= map(select(.type != "card"))`)
# 来源 https://kelee.one/：推荐流子项删除 ring
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/topstory\/recommend\?/ then response.json.jq(`.data[]?.children |= (if type == "array" then map(select(.id != "ring")) else . end)`)
# 来源 https://kelee.one/：文章/回答/想法删除商业与互动插件字段
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/(articles|answers|pins)\/v\d\/\d+\?/ then response.json.jq(`del(.third_business, .ring_info, .interaction_bar_plugins)`)
# 来源 https://kelee.one/：评论列表删除连续消费模块
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/comment_v\d\/answers\/\d+\/list-headers$/ then response.json.jq(`del(.continuous_consumption_module)`)
# 来源 https://kelee.one/：播客 hub 删除 banner
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/podcasts\/hub\/v\d$/ then response.json.jq(`del(.banners)`)
# 来源 https://kelee.one/：搜索推荐词只保留 normal
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/search\/recommend_query\/v\d\?/ then response.json.jq(`.recommend_queries.queries |= map(select(.type == "normal"))`)
# 来源 https://kelee.one/：搜索结果删除 pendant 挂件
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/search_v\d\?/ then response.json.jq(`del(.pendant)`)
# 来源 https://kelee.one/：搜索 Tab 只保留业务类型
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/search\/tabs\?/ then response.json.jq(`.data |= map(select(.t | IN("general", "ai_zhida", "recent", "people", "zvideo", "ring", "topic", "podcast", "column", "pin", "favlist")))`)
# 来源 https://kelee.one/：我的页删除 VIP 推广入口（不改会员状态）
# response if ${url} ~= /^https?:\/\/api\.zhihu\.com\/people\/self$/ then response.json.jq(`del(.vip_info.entrance_new.right_button, .vip_info.entrance_v2)`)
```

启用步骤：①Loon 装并信任证书 → ②取消插件内 `[MITM]` 头与 hostname 行注释 → ③取消 `[Rewrite]` 头与所需 `response.json.jq` 行的注释 → ④取消 `[Rule]` 头、QUIC 回退行与所需规则行的注释（`# [Rule]` 必须一起取消，否则规则会落在上一段的末尾而不生效）。

> 证书固定红线：银行/微信/米家类 App 做了证书固定，MITM 直接失败甚至触发风控，那些插件不提供本层；本层只对未做证书固定的 App 提供，且每条路径都有下方公开证据。

证据：
- https://kelee.one/

## 红线与天花板（如实）

- 红线：*.zhihu.com / *.zhimg.com 承载登录、内容、会员与图片；本插件只做精确 API 路径，不黑洞整域。
- 可莉「知乎去广告」的 30 条 Rewrite 全部是 Loon 原生语法（request reject_dict / response.json.jq / delete），已逐条改写进本插件；没有上游脚本，也不依赖可莉。
- 响应规则只删广告/推广/推荐字段，不做会员状态或权益改写；请求规则只针对明确的广告/推广 API 路径。
- 证据基线：可莉「知乎去广告」插件规则事实；接口路径未在 2026-11-03 逐条真机复测，启用后先验首页、推荐、搜索、回答详情、评论和登录。
- 本插件没有默认生效的 [Host]/[Rule]；MITM 与 Rewrite 整段默认注释，装并信任 Loon 证书后按需启用。

## 证据与验证

- 每条域名的证据链接写在插件文件注释里（`# 证据:`）；置信 A=多源独立收录，B=1-2 源或集群语义自证（默认关），C=猜测/单源（不收）。
- 生效判读：Loon 日志中被本插件命中的域名应显示 `Host Map IP:127.0.0.1`；REJECT-DROP 无日志回包属正常。
- 源文件：`src/apps/zhihu.json`，改源后 `npm run build:apps`。本 README 由 `tools/gen-app-readmes.py` 生成。

统计：精确/通配黑洞 0 条，[Rule] 0 条。
