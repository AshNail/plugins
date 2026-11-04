# Loon 去广告插件集

只分发**独立插件**：无主配置、无分流规则、无节点/订阅、无证书私钥。装一个是一个，开关都在插件自己的 `[Argument]` 里。
零 MITM 的插件导入即用；带 `[MITM]` 的要先在 Loon → 设置 → MITM 生成并信任证书，否则那层静默不生效。
一个 App 只装一个。证书固定的 App（银行 / 微信 / 米家 / 京东 / X / Instagram）只有 DNS 与规则层——能力边界，不是遗漏。

## 插件与一键导入

点「导入」→ Loon 打开该插件 → 确认；边界、开关与取证结论见各插件 README。

| 插件 | 管什么 | 导入 |
|---|---|---|
| `ads.plugin` | 通用底座：广告域 DNS 黑洞 + HTTPDNS 防绕过 + 公共 DoH/DoT 防泄漏。建议第一个装 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fads%2Fads.plugin) |
| `soda.plugin` | 汽水音乐：福利页精简、信息流与激励广告清理、商业化弹窗、版本检查静音 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fsoda%2Fsoda.plugin) |
| `douyin.plugin` | 抖音：福利页精简、信息流广告清理、商城/演出弹窗、开屏广告请求拦截 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fdouyin%2Fdouyin.plugin) |
| `jd.plugin` | 京东：可 DNS 切断的自建广告交易与点击监测域（信息流广告与商品同 API，切不掉） | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fjd%2Fjd.plugin) |
| `qidian.plugin` | 起点读书：穿山甲 / 腾讯七巧板 SDK 黑洞 + 起点自有广告统计端点 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fqidian%2Fqidian.plugin) |
| `wechat.plugin` | 微信：广点通 / 优量汇素材主机黑洞（朋友圈条目本身不可移除） | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fwechat%2Fwechat.plugin) |
| `banks.plugin` | 6 款银行 App：已证实的自建广告端点与穿山甲内网域；登录 / 支付 / 二维码 / 推送零接触 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbanks%2Fbanks.plugin) |
| `meituan.plugin` | 美团 / 点评：第三方变现 SDK（Sigmob/ToBid/美数）+ 自建广告端点 + 纯遥测家族 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fmeituan%2Fmeituan.plugin) |
| `xianyu.plugin` | 闲鱼：阿里广告 SDK 补位。广告 100% 内嵌 goofish 主网关，DNS 层能力有限 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fxianyu%2Fxianyu.plugin) |
| `mijia.plugin` | 米家：小米统一广告平台黑洞；设备控制 / 账号 / 推送零接触 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fmijia%2Fmijia.plugin) |
| `x.plugin` | X：广告像素、嵌入 syndication 与广告后台域。广告数量不变，收益在隐私侧 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fx%2Fx.plugin) |
| `instagram.plugin` | Instagram：转化像素、网页播放器 VAST 域与已死徽章服务；不碰主域 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Finstagram%2Finstagram.plugin) |
| `zhihuifangdong.plugin` | 智慧房东：穿山甲 / 优量汇 / 快手联盟 / 倍孜黑洞，广告位加载失败即生效 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fzhihuifangdong%2Fzhihuifangdong.plugin) |
| `bubei-danci.plugin` | 不背单词：官方 SDK 目录没有广告联盟，本插件只裁埋点组 | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fbubei-danci%2Fbubei-danci.plugin) |
| `ruankao-tong.plugin` | 软考通：开屏 / 插屏走穿山甲 + 优量汇。**启用即断「看广告解锁真题」** | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fruankao-tong%2Fruankao-tong.plugin) |
| `mba-dashi.plugin` | MBA大师：开屏穿山甲、课程列表插屏优量汇。**启用即断「看广告领课程」** | [导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fmba-dashi%2Fmba-dashi.plugin) |

2026-11-04 撤下主配置层：`configs/loon.conf`、`examples/loon*.conf`、两份配置文档、两个配置工具与 `npm run check:config` 全部删除——整份 profile 会替换用户现有配置，而去广告能力插件层已经自带。历史实现见 git 记录。

开发：改 `src/apps/<slug>.json` 或 `src/ads/domains.json`，再 `npm run build`，勿手改 `plugins/**/*.plugin`；全量门禁 `npm run check`。
