# 起点官网 Web 资源实测（2026-11-01）

> 目标：搞清楚 `www.qidian.com` 首页到底加载了什么、哪些是内容、哪些是推广/统计，
> 以及 Loon 当前挡住了什么。样本为 2026-11-01 一次冷加载，动态推荐位会随地区/账号变化。

## 方法

- Chrome headless（真实浏览器 JS）加载 `https://www.qidian.com/`，`--virtual-time-budget=15000`。
- 同时抓最终 DOM 与 Chrome netlog；按请求实际传输字节聚合，排除 Chrome 自身后台请求
  （Google 更新、Optimization Guide、账号检查等，约 33MB 噪声）。
- 首屏初始 HTML 只有 209B 的 JS 挑战页，真实 DOM 约 214KB；以下统计来自挑战通过后的页面。

## 总量

- 有效 Web 资源约 **5.1MB**（已排除 Chrome 后台噪声），DOM 资源标签 129 个。
- 页面自身 + 内容 CDN 约 1.7MB；第三方推广/验证码/统计约 3.4MB。
- 起点主域流量很小：`www.qidian.com` 354KB，主要是 probe/挑战脚本和接口。

## 主要资源（按传输字节）

| 域名 | 约字节 | 请求 | 性质 | 建议 |
|---|---:|---:|---|---|
| `qdfepccdn.qidian.com` | 1.14MB | 22 | 起点静态 CDN：CSS/JS/图标/字体 | 保留 |
| `sj.qq.com` | 823KB | 2 | 腾讯应用宝分享/推广 iframe SDK | 可选拦（会断 App 下载/分享入口） |
| `bossaudioandcomic-1252317822.image.myqcloud.com` | 820KB | 10 | 起点活动/有声/漫画推广图 | 可选拦（可能影响有声/漫画活动位） |
| `turing.captcha.gtimg.com` + `turing.captcha.qcloud.com` | 817KB | 5 | 腾讯验证码 | **必须保留** |
| `gameapp-1252317822.file.myqcloud.com` | 429KB | 9 | 游戏推广图/游戏中心素材 | 可选拦（会少游戏推广） |
| `static.pc.yyb.qq.com` | 341KB | 1 | 应用宝 PC JS SDK | 可选拦（同 `sj.qq.com`） |
| `bookcover.yuewen.com` | 125KB | 19 | 书籍封面 | 保留 |
| `webfontsource.yuewen.com` | 81KB | 1 | 字体 | 保留 |
| `open.weixin.qq.com` + `res.wx.qq.com` | 73KB | 4 | 微信登录/分享 | 保留 |
| `readx-her-*.image.myqcloud.com` | 35KB | 2 | 写作/活动功能图 | 保留（混有活动） |
| `imgservices-*.image.myqcloud.com` | 28KB | 11 | 站内图片/活动资源 | 保留 |
| `hm.baidu.com` | 0（已拦） | 1 | 百度统计 | 已拦 |
| `aegis.cdn-go.cn` | 0（已拦） | 1 | 腾讯 Aegis 前端监控 | 已拦 |
| `rumt-zh.com` | 142B | 2 | 腾讯云 RUM 真实用户监控 | 已拦 |
| `h.trace.qq.com` / `otheve.beacon.qq.com` | 0（已拦） | 多 | 腾讯/起点遥测 | 已拦 |
| `qdp.qidian.com` | 14B | 7 | 起点推送网关 `qreport` | 不拦：拦了断推送 |
| `ptlogin.qidian.com` / `ptlogin.yuewen.com` | 极低 | 2 | 登录态检查 | 保留 |

## 本轮落地

公开主配置新增（不影响内容/验证码/登录）：

```ini
DOMAIN,hm.baidu.com,REJECT
DOMAIN-SUFFIX,rumt-zh.com,REJECT
```

`aegis.cdn-go.cn`、`h.trace.qq.com`、`otheve.beacon.qq.com` 已有规则；
`qdp.qidian.com` 属推送网关，继续放行。

Mac 复核：`hm.baidu.com` / `rumt-zh.com` 均解析 `127.0.0.1`、HTTPS 不可达；
Chrome 仍拿到约 236KB 完整 DOM，标题正常，`turing.captcha.*`、
`qdfepccdn.qidian.com`、`bookcover.yuewen.com` 均可达。

## 可选优化（默认不启用）

如果目标是进一步降低首屏体积、且不需要 App 下载/游戏推广：

```ini
# 应用宝分享/下载 SDK，约 1.16MB
DOMAIN-SUFFIX,sj.qq.com,REJECT
DOMAIN,static.pc.yyb.qq.com,REJECT
# 起点活动/游戏推广图，约 1.25MB；可能影响有声/漫画/游戏活动位
DOMAIN,bossaudioandcomic-1252317822.image.myqcloud.com,REJECT
DOMAIN,gameapp-1252317822.file.myqcloud.com,REJECT
```

不要拦 `turing.captcha.*`（登录/风控验证码）、`ptlogin.*`（登录态）、
`open.weixin.qq.com`/`res.wx.qq.com`（微信登录分享）、`qdfepccdn.qidian.com`/
`bookcover.yuewen.com`（正文与封面内容）。

## 限制

- 单次样本，且起点首页有反爬挑战；不同地区/登录态的资源与推广位会变化。
- netlog 的 `byte_count` 是本次实际传输量，不包含浏览器缓存命中；第二次访问会更小。
- 本轮只落地统计/监控域；1.16MB 应用宝 SDK 与 1.25MB 推广图属于功能/运营取舍，未默认拦。
