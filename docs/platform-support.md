# 多端支持矩阵（iOS / iPadOS / macOS / tvOS）

> 结论分三层：**Loon 能力**（官方功能）、**插件声明**（`#!system`）、**真机验证**（本仓实际跑过）。
> 三者不能互相替代。截至 2026-11-01，只有 macOS 做过运行期验证；iPhone / iPad / Apple TV
> 没有接入本机，标为「待真机」。

## 0. 先给结论

- Loon for tvOS 官方说明包含 iOS 版全部功能（复写、脚本、插件、MITM），所以 tvOS 的边界
  不是 Loon 能力，而是 **App 是否存在、插件作者是否声明支持、以及 MITM 是否值得开**。
- `#!system` 为空表示全部平台；写了值就按值声明支持。`#!system_version` 是**一个值约束
  `#!system` 里的所有平台**，所以本仓不写它，避免把 macOS / tvOS 一起挡掉。
- 46 个公开插件里，平台声明分三组：
  - **16 个未写平台**：15 个 kelee 插件 + Badoo，`#!system=` 为空，按官方语义全平台；
  - **22 个四端全声明**：ads、13 个 App 插件、Biliverse Redirect/Global/Enhanced、DualSubs；
  - **8 个部分声明**：见下表。
- macOS 按声明应加载 **39 个**（soda、douyin、BiliBili ADBlock 不声明 macOS）；
  iOS 43 个；iPadOS 在补齐 soda/douyin 的 `iPadOS` 声明后 43 个；
  tvOS 按声明只有 **34 个**（soda、douyin、BiliBili ADBlock、iRingo 三件套、YouTube
  均未声明 tvOS）；即便 Loon 全部加载，其中大量 App 插件对 TV 无消费方，
  建议用 §2 的 Apple TV 精简档。

## 1. 部分平台声明

| 插件 | `#!system` | iOS | iPadOS | macOS | tvOS | 说明 |
|---|---|:---:|:---:|:---:|:---:|---|
| soda | `iOS,iPadOS` | ✅ | ✅ | — | — | 2026-11-01 补 iPadOS；汽水 iPad 兼容运行，规则与脚本按域名工作 |
| douyin | `iOS,iPadOS` | ✅ | ✅ | — | — | 同上；抖音 iPad 兼容运行 |
| BiliBili ADBlock | `iOS,iPadOS` | ✅ | ✅ | — | — | 作者只声明移动端；macOS / tvOS 不覆盖，别为了「统一」硬加 |
| iRingo Maps | `iOS,iPadOS,macOS` | ✅ | ✅ | ✅ | — | 无 tvOS 声明 |
| iRingo LocationService | `iOS,iPadOS,macOS` | ✅ | ✅ | ✅ | — | 无 tvOS 声明 |
| iRingo WeatherKit | `iOS,iPadOS,macOS,watchOS` | ✅ | ✅ | ✅ | — | 含 watchOS；无 tvOS 声明 |
| YouTube 去广告 | `iOS,iPadOS,macOS` | ✅ | ✅ | ✅ | — | YouTube tvOS App 不在覆盖范围 |
| 网易云音乐（规则层） | `iOS,iPadOS,macOS` | ✅ | ✅ | ✅ | — | 本轮新增；无 tvOS 声明 |

其余 34 个插件要么四端全声明，要么未写平台（按官方语义全平台）。未写平台的 16 个里，
绝大多数是可莉的 App 专用 Rewrite；它们在 tvOS 上没有对应 App，但规则本身不会造成额外风险，
只是白白增加加载项——这就是 §2 的 Apple TV 精简档要精简的原因。

## 2. 各端推荐配置

### iPhone / iPad

- 直接用公开主配置的 46 个插件。
- iPad 需要 `soda.plugin` / `douyin.plugin` 的新版（`#!system=iOS,iPadOS`）。
  旧缓存如果还是 `ios`，在 Loon 里删除插件重新导入即可。
- 首次导入要留意 kelee 的 16 个 URL：当前网络实测返回 Cloudflare 403。
  插件面板里缺哪个，就从已安装设备导出缓存，或先用不含 kelee 的临时配置跑通。

### macOS

- Mac 私有档已收敛到 **39 个**（移除 soda、douyin、BiliBili ADBlock：macOS 无对应 App
  或作者不支持）；公开配置仍保留 46 个给 iOS/iPad/TV。Loon 的 `#!system` 检查
  不再产生这 3 个平台告警。
- BiliBili 的 Redirect / Global / Enhanced 声明了 macOS；ADBlock 没有。不要因为
  「B 站 Mac 版也能看」就擅自给 ADBlock 补 macOS——脚本按 iOS 页面结构写的。
- **主配置 `[Host]` 不要写 `*.qq.com = server:...` 这类宽通配解析映射。**
  2026-11-01 实测：主配置通配 Host 会压过插件里更精确的 `= 127.0.0.1` 广告黑洞，
  微信广告主机仍连真实服务器；删掉 17 条 `server:` 映射后黑洞立即恢复，同时 DoH 不再被降级成明文 53。

### Apple TV

TV 端建议用**零 MITM、零脚本**的网络层精简档，而不是原样导入 46 个。
生成命令（用你自己的 `.lcf` 备份；输出含订阅/节点，权限 0600，不要入库）：

```bash
python3 tools/make-private-config.py \
  --lcf ~/Loon-backups/<时间>/Loon.lcf \
  --platform tvos \
  --out ~/Downloads/Loon.tv-private.lcf
```

`--platform tvos` 会自动过滤到下面 3 个插件、删除 `[MITM]`/CA、
清空主配置 `[Rewrite]`/`[Script]`，并保留规则、策略组、订阅与节点。

| 顺序 | 插件 | 作用 | 备注 |
|---|---|---|---|
| 1 | `plugins/ads/ads.plugin` | Host 黑洞 + 广告规则 + HTTPDNS 防绕过 | 公开仓库直链，最可靠 |
| 2 | `BlockAdvertisers.lpx` | 补充广告域名规则 | kelee 直链当前 403，能导入才加 |
| 3 | `Block_HTTPDNS.lpx` | 补充 HTTPDNS / DoH 旁路规则 | 同上 |

- 这三个都是 Host / Rule，不开证书，tvOS 上不会弹信任问题，也不依赖 App。
- 不需要 MITM 的另一个好处：YouTube / Bilibili / Netflix 的 TV 客户端证书固定或内嵌播放器
  广告不会被误伤；代价是**贴片广告无法去除**——HTTPS 路径改写必须有 MITM，而 TV 端这些
  App 的证书固定风险高，本仓不把「强开 MITM 去贴片」作为推荐路径。
- 如果 kelee 两个 URL 也 403，就只保留 `ads.plugin`。它自己的 1497 条 Host + 13 条规则
  已经是可独立工作的底座，比为了凑数留一堆下载失败的条目更稳。
- 不要导入 soda / douyin / JD / 微信 / 银行等 App 插件：TV 上没有这些 App，
  它们的 Host 规则在全局仍然生效，但属于「为不存在的消费方付加载成本」。

## 3. 已知跨端问题

1. **kelee.one 直链 403（Cloudflare challenge）**：16 个 `https://kelee.one/Tool/Loon/Lpx/...`
   在全新设备上可能下载失败；已缓存设备不受影响。公开配置保留这些行是为了已能访问的用户，
   但新设备首次导入必须核对插件面板，不能假设「配置导入成功 = 插件全部生效」。
2. **`#!system` 不匹配时 Loon 是拒绝加载还是只提示，官方文档没有写死**。
   本仓按「声明即边界」保守处理：不支持的平台不硬加系统名，也不依赖它一定被拦截。
3. **MITM 证书是每台设备独立的**：iPhone / iPad / Mac 需要在各自设备安装并信任 Loon CA；
   TV 精简档不需要 MITM。CA、订阅、节点凭据只放私有配置，不进本仓。
4. **Host 优先级**：官方只写了「订阅 Host Map 优先于主配置」，没写「插件 Host 与主配置
   通配谁赢」。当前实测是主配置通配赢，所以主配置应保持 `[Host]` 精简；排障先查
   `[Host]`，再怀疑插件或正则。

## 4. 验证状态

| 平台 | 已验证 | 待真机 |
|---|---|---|
| macOS | Host 黑洞恢复（微信广告主机 5s 黑洞、正常域 200）、DoH 未被明文映射降级、私有档 39 插件全部可用 | 长周期广告/支付/登录回归 |
| iPhone | — | 46 插件导入、soda/douyin 开屏与领奖、CA 信任、TLS 证书错误 |
| iPad | — | soda/douyin 元数据补齐后是否加载、B 站 ADBlock、分屏/兼容模式 |
| Apple TV | — | 三插件精简档导入、DNS 广告拦截、无 MITM 证书问题 |

真机跑完后把结论回填到 [`docs/device-checklist.md`](device-checklist.md)，不要只改本页。
