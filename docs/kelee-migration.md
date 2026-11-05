# 可莉插件 → 自研实现对照（2026-11-03）

> 原则：只吸收可公开复用的规则事实，用 Loon 原生 `[Host]` / `[Rule]` /
> `[Rewrite]` / `response.json.jq` 重写；不复制可莉 JS，不做会员/地区/青少年
> 绕过。可莉插件本身不再作为本仓运行依赖。

## Mac 当前启用（16 个可莉插件）

| 可莉插件 | 自研状态 | 说明 |
|---|---|---|
| 广告平台拦截器 | 已覆盖 | `ads.plugin` 的 921 个可莉广告平台域全部覆盖（域名差集 0） |
| HTTPDNS 拦截器 | 基本覆盖 | `ads` 已覆盖 63/70 个端点；剩 Youku XPIS/inkuai/q2cdn/k-dyn 等 7 个，未默认吸收 |
| 可莉广告过滤器 | **已完成-原生子集** | `plugins/adfilter`：52 条 API 级 URL 规则（默认注释）+ 11 个精确广告域；排除钱包/核心 API/共享 CDN/图片硬编码 |
| 淘宝去广告 | **已完成** | `plugins/taobao`：12 个精确 DNS 域 + 11 条可选 MITM URL 规则；可莉 JS 未复制 |
| 闲鱼去广告 | **已完成** | `plugins/xianyu`：DNS 组 + 15 条可选 `response.json.jq` |
| 知乎去广告 | 已撤下 | 2026-11-05 随仓库策略移除（曾为 `plugins/zhihu`：16 条请求拒绝 + 14 条响应 jq）；历史实现见 git 记录 |
| 什么值得买去广告 | 待评估 | 22 条 Rewrite，需逐条分流原生/脚本 |
| 快捷搜索 | 待评估 | 8 条 URL 重定向，原生 Rewrite 可行 |
| 航旅纵横去广告 | 待评估 | 1 条 Rule + 1 条 Script，脚本部分不可等价 |
| 盖得排行去广告 | 待评估 | 11 条 Rewrite，原生可行性待拆 |
| 滴滴去广告 | 待评估 | 27 条 Rewrite，原生可行性待拆 |
| YouTube 去广告 | 不移植 | 3 条 response 脚本，依赖 JS/YouTube 内部字段；Loon 原生 jq 不等价 |
| TestFlight 地区解锁 | 待评估 | 1 条 Rewrite；地区/账号行为，按红线谨慎处理 |
| Telegram 重定向 | 待评估 | 2 条 URL 重定向，原生可行 |
| Google 搜索重定向 | 待评估 | 2 条 URL 重定向，原生可行 |
| 12306 去广告 | 待评估 | 1 条 Rewrite + 1 条 Script，脚本部分不可等价 |

## 明确不移植

- B 站 Pro 的 VIP 状态、青少年模式、地区 302、核心 `api.bilibili.com` /
  `api.biliapi.net` / `playurl` 拒绝：属于权益/地区/播放链路，触犯本仓红线。
- 任何 `response-body-json-jq` 以外的可莉私有脚本、加密参数、会员解锁逻辑。
- 只保留可独立验证的广告/推广端点与 DNS 域。

## 迁移顺序

1. 先完成纯原生插件：可莉广告过滤器安全子集、快捷搜索、Telegram/Google 重定向。
2. 再评估 SMZDM/滴滴/盖得/12306/航旅，逐条判定原生/脚本。
3. Mac 私有配置替换前先备份；新插件 URL 未推送前用本地缓存注入验证，不能直接删可莉插件。
4. 每次替换后跑 `npm run check`、`tools/mac-mitm-audit.py`、`tools/mac-routing-audit.py`、
   `tools/remote-rules-audit.py`，并做核心 App 冒烟。
