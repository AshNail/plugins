# 广告平台拦截器 · Loon 3.5.3+ 全开版（Zero-Config Full Edition）

> **定位**：基于 [`ads.plugin`](../ads/README.md) 单真源（[`src/ads/domains.json`](../../src/ads/domains.json)）派生的 **Loon 3.5.3(1008)+ 全开版**。
> 零手工取消注释：直接激活 **40 条**无红线冲突的 `DOMAIN-WILDCARD` 广告子域/数字分片通配规则，以及 **16 条** `[IP Rewrite]` TUN 阶段 HTTPDNS 接入点拦截。
>
> **兼容边界**：本插件声明 `#!system=iOS,iPadOS,tvOS` 与 `#!loon_version=3.5.3(1008)`。如果你使用的是 App Store 正式版 `3.5.2(996)` 或 **Loon for Mac**，请继续使用 [`ads.plugin`](../ads/README.md)（全平台兼容版）。

---

## 版本

- **v2.8.33**（与 [`ads.plugin`](../ads/README.md) 共享全部 `[Host]` / `[Rule]` / `[General]` 真源数据）

---

## 安装

[![一键导入 ads-next.plugin](https://img.shields.io/badge/Loon-导入广告拦截器3.5.3+-red?style=for-the-badge&logo=safari&logoColor=white)](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fads-next%2Fads-next.plugin)

直链地址：

```text
https://raw.githubusercontent.com/AshNail/plugins/main/plugins/ads-next/ads-next.plugin
```

Loon 导入链接：

```text
loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FAshNail%2Fplugins%2Fmain%2Fplugins%2Fads-next%2Fads-next.plugin
```

---

## 与 `ads.plugin` 的差异

| 维度 | `ads.plugin`（基线全平台） | `ads-next.plugin`（3.5.3+ 全开版） |
|---|---|---|
| 目标平台（`#!system`） | `iOS,iPadOS,tvOS,macOS` | `iOS,iPadOS,tvOS` |
| 最低版本（`#!loon_version`） | 不声明（3.5.2(996) / Mac 均可导入） | `3.5.3(1008)` |
| `[Host]` / pre-DNS 双栈 `[Rule]` / `[General]` | 全量生效 | 全量生效（同源） |
| `DOMAIN-WILDCARD`（30 广告左标签 + 11 数字分片家族） | 41 条全注释 | **40 条默认激活**；命中微信红线 `ads.privacy.qq.com` 的 `ads.*` 保持注释保护 |
| `[IP Rewrite]`（16 条单 IPv4 HTTPDNS 网关） | 默认注释 | **16 条默认激活**（TUN 阶段最早拦截） |
| `IP-CIDR` 可选组 / 归因统计组 / 国内 DoH | 默认注释 | 默认注释（同源红线与防自伤纪律） |

---

## 说明与红线保护

1. **为什么 `ads.*` 保持注释？** `DOMAIN-WILDCARD` 语法不支持排除，激活 `ads.*` 会命中微信红线 `ads.privacy.qq.com`。本版在构建阶段自动跳过存在红线重叠的 `ads.*`，仅默认启用其余 40 条无冲突通配规则。
2. **为什么与 `ads.plugin` 互斥？** 两份插件共享相同的 `[General]` / `[Host]` / pre-DNS `[Rule]`，二选一安装即可，切勿同时启用。
3. **刷激励广告**：与 `ads.plugin` 相同，已排除 `ad.zijieapi.com` 以保护穿山甲奖励回调；优量汇/快手激励期间需临时关闭或删除对应条目。
