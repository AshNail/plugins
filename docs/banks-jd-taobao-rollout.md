# 六大行 + 京东 + 淘宝：分层去广告落地与客户端协同指南

> 本文把三类最复杂、风控与混装特性截然不同的中国大陆日常 App（六大行+全国性信用卡+云闪付、京东、淘宝）收拢到一套可直接按单落地的执行顺序里，只写经本仓库 27 源离线交叉、官方《第三方 SDK 目录》及社区开源规则实证过的配置与边界，不承诺网络层不可能做到的事。各银行与掌上生活/买单吧开屏同域混装深度拆解见 [银行与信用卡 App 去广告深度分析](banks-creditcard-ad-removal.md)。

---

## 一、三端架构差异与能力边界总览

| 维度 | 六大行 + 信用卡 + 云闪付 (`banks`) | 京东 (`jd`) | 淘宝 (`taobao`) |
|---|---|---|---|
| **插件策略** | 零证书 / 零 MITM（仅精确自建广告子域 + 穿山甲企业内网噪音） | 零证书 / 零 MITM（自建广告交易/京媒/监测域 DNS+pre-DNS 阻断） | DNS/pre-DNS + 默认启用 `[MITM]` + 原生 `[Rewrite]` v2 + 4 条 `PROTOCOL,QUIC` 回退 |
| **加密与风控墙** | SSL Pinning + 国密 SM2/SM3/SM4 + 系统 VPN/HTTP 代理/无障碍检测 | JD 13/14+ `api.m.jd.com` 强制 `CertificatePinner` + `h5st` + `dns.jd.com` 硬编码 IP HTTPDNS | 无强 Pinning，但使用 `amdc.m.taobao.com` 调度 + XQUIC(UDP/443) + 本地会话缓存 |
| **核心红线** | 所有银行/卡中心主后缀（含 `.cmbimg.cn`/`.bankcomm.cn`/`955*`/`bosc.cn`/`bankofbeijing.com.cn`）、`wallet.95516.com`、`online.unionpay.com`、`msmp.abchina.com.cn`、`mobilepaas.abchina.com.cn`、`www.abchina.com.cn`、`enjoy.cdn-static.abchina.com.cn`、`yunbusiness.ccb.com`、`login-service.mobile-bank.psbc.com`、`mobile-bank.psbc.com`、`d.psbc.com`、`buy.ccb.com`、`m.icbc.com.cn`、`oisc.icbc.com.cn`、`ccclub/mlife/az1mbasecc.bas/mbmodule-openapi.paas.cmbchina.com`、`res.cc/s3gw.cmbimg.com(.cn)`、`creditcardapp.bankcomm.com(.cn)`、`creditcard.bankcomm.com` | `api.m.jd.com`、`janapi.jd.com`、`cactus.jd.com`/`cactus.joybuy.com`、`dns.jd.com`、`360buyimg.com`/`img-x.jd.com`、`p.3.cn`/`c0.3.cn`/`jstatic.3.cn` | `*.taobao.com`/`*.tmall.com`/`*.alicdn.com` 整族、`ossgw.alicdn.com`、`audid-api(-sg).taobao.com`、`tce.alicdn.com`、`sjarvis.taobao.com`、`aeis.alicdn.com`、`sdkinit/tbskip/err.taobao.com`、`pass.1688.com`、`grand/client-api/newton-api.ele.me` |
| **第一方开屏/信息流** | 主接口同域直出+本地预缓存（如掌上生活 `preCacheAdvertiseSec`、买单吧 `queryGuidePageAds.do`），核心网关不可切；须靠**官方关怀版/大字版 + 端内开关 + iOS 27.2+ 限制动作数据 +（可选 `banks-mitm` 仅切静态/视频图床目录）** | 信息流混用商品 CDN；可封广告交易与可选 HTTPDNS IP + **系统禁摇一摇** | `cleanAds` 拦截 13 个 MTOP 广告/开屏接口 + `imgextra` 推广大图 + **清 QUIC 缓存** |

---

## 二、第 1 步：Loon 主配置可直接合并的协同片段

> 以下 `[General]` 与 `[Rule]` 条目用于补足 Loon 插件白名单无权修改的主配置选项（例如 `hijack-dns`、`domain-reject-mode`、`FINAL` 不受插件控制；`skip-proxy` 属用户全局路由，由主配置接管）。**切勿在 Loon 中照抄 Surge 的 `%APPEND%` 语法**，直接以英文逗号追加到现有行末即可。

```ini
[General]
# 1. DNS 防旁路：劫持 53 端口查询并在 DNS 阶段直接执行域名 REJECT
hijack-dns = *:53
domain-reject-mode = DNS
# 2. 银行防代理检测：把实证触发 HTTP Proxy 检测的银行域加入 skip-proxy（如有原有项请用英文逗号接在后面）
skip-proxy = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, localhost, *.local, www.abchina.com.cn, msmp.abchina.com.cn, mobilepaas.abchina.com.cn, yunbusiness.ccb.com, login-service.mobile-bank.psbc.com, mobile-bank.psbc.com

[Rule]
# 3. 银行与信用卡主域置顶直连（避免被后序分流错送代理节点触发风控或锁卡）
DOMAIN-SUFFIX,icbc.com.cn,DIRECT
DOMAIN-SUFFIX,ccb.com,DIRECT
DOMAIN-SUFFIX,ccb.com.cn,DIRECT
DOMAIN-SUFFIX,abchina.com,DIRECT
DOMAIN-SUFFIX,abchina.com.cn,DIRECT
DOMAIN-SUFFIX,boc.cn,DIRECT
DOMAIN-SUFFIX,bankcomm.com,DIRECT
DOMAIN-SUFFIX,bankcomm.cn,DIRECT
DOMAIN-SUFFIX,psbc.com,DIRECT
DOMAIN-SUFFIX,psbc.com.cn,DIRECT
DOMAIN-SUFFIX,95516.com,DIRECT
DOMAIN-SUFFIX,cup.com.cn,DIRECT
DOMAIN-SUFFIX,cmbchina.com,DIRECT
DOMAIN-SUFFIX,cmbimg.com,DIRECT
DOMAIN-SUFFIX,cmbimg.cn,DIRECT
DOMAIN-SUFFIX,spdb.com.cn,DIRECT
DOMAIN-SUFFIX,spdbccc.com.cn,DIRECT
DOMAIN-SUFFIX,ecitic.com,DIRECT
DOMAIN-SUFFIX,citicbank.com,DIRECT
DOMAIN-SUFFIX,cebbank.com,DIRECT
DOMAIN-SUFFIX,95508.com,DIRECT
DOMAIN-SUFFIX,cib.com.cn,DIRECT
DOMAIN-SUFFIX,cmbc.com.cn,DIRECT
DOMAIN-SUFFIX,pingan.com,DIRECT
DOMAIN-SUFFIX,hxb.com.cn,DIRECT
DOMAIN-SUFFIX,czbank.com,DIRECT
DOMAIN-SUFFIX,cbhb.com.cn,DIRECT
DOMAIN-SUFFIX,hfbank.com.cn,DIRECT
DOMAIN-SUFFIX,bosc.cn,DIRECT
DOMAIN-SUFFIX,bankofbeijing.com.cn,DIRECT
```

- **可选放行（仅当促销 H5 弹层异常时置顶）**：若淘宝个别活动页因 `alibaba` 组拦截 `poplayer.template.alibaba.com` 导致白屏或按钮失效，在上述 `[Rule]` 顶部按需加入 `DOMAIN,poplayer.template.alibaba.com,DIRECT`。

---

## 三、第 2 步：插件安装与分段激活顺序

1. **底座插件二选一**：启用 `plugins/ads/ads.plugin` 或 `plugins/ads-next/ads-next.plugin`（二者互斥，切勿同时启用）。
   - **京东 HTTPDNS 硬编码 IP 旁路封堵**：若冷启动仍能拉出开屏配置，在 `ads.plugin` 本地副本取消以下两条可选规则的注释（同时保持 `dns.jd.com` 域名红线不黑洞）：
     - `IP-CIDR,101.124.19.122/32,REJECT,no-resolve`
     - `IP-CIDR6,2402:db40:5100:1011::5/128,REJECT,no-resolve`
2. **装入 App 插件**：`plugins/banks/banks.plugin`（零证书底座）、`plugins/jd/jd.plugin`、`plugins/taobao/taobao.plugin`（与 `ads` 共享组由构建器统一管理，规则自动去重）。若设备已安装并完全信任 Loon CA 根证书且需对掌上生活（含 `.cmbimg.cn` 双生域与 `.mp4` 视频开屏 `reject_video(200)`）/浦大喜奔/工行/广发做路径级静态广告拦截，可额外叠装可选伴随插件 `plugins/banks-mitm/banks-mitm.plugin`（含 `cleanCmbSplash`/`cleanSpdbAds`/`cleanBankCdnAds` 三个独立开关；与 `banks.plugin` 同装时保持 `banks.plugin` 中 `# lban.spdb.com.cn = 127.0.0.1` 注释不启）。
3. **开启并完全信任 CA 证书（淘宝与可选 `banks-mitm` 原生复写层前置）**：
   - iOS 前往 `设置 → 通用 → 关于本机 → 证书信任设置` 打开 Loon 根证书**完全信任**。
   - **破除手淘 XQUIC / AMDC 会话缓存（关键）**：开启插件与证书后，① **上划彻底杀掉淘宝后台** → ② 切换一次飞行模式或重启 Loon（清空 `amdc.m.taobao.com` 缓存在本地沙盒的 UDP/443 XQUIC 会话池，确保 4 条 `PROTOCOL,QUIC` 回退规则迫使请求改走 TCP）→ ③ 冷启动淘宝，在 Loon 请求日志核对 `acs`/`guide-acs` 命中 `reject_dict(200)`；若叠加了 `banks-mitm.plugin`，同样先杀掉掌上生活后台清缓存以刷新 `preCacheAdvertiseSec` 本地预缓存。
4. **按需试开默认关闭分组**：
   - 银行：`spdb_ad_optional`（`lban.spdb.com.cn`，仅在不装 `banks-mitm.plugin` 且日志确认命中时试开）、`unionpay_optional`（可能触发重试风暴，仅在日志实测无卡包/转账阻塞后开启）与 `bank_telemetry`（含农行 `firefly.abchina.com.cn`、听云/博睿/招行深圳指标 APM）。
   - 京东：`jd_ad_watchlist`（含 `.3.cn` 带 `@@` 白名单的 `ad.3.cn` 与 `1 号店` `api.dsp.yhd.com`）与 `jd_telemetry`。
   - 淘宝：`telemetry`（UT / ARMS / 阿里云 / 饿了么 / 菜鸟 / 飞猪分片）与 `simba_click`（影响点推广跳转与返佣）；**`amdc` 组严禁随意开启**。

---

## 四、第 3 步：端内官方隐私与推荐开关汇总（必做）

> 六大行与强证书固定 App 端的第一方弹窗/推荐由主业务加密通道直出，任何网络层无 MITM 方案都必须在端内手动关闭官方开关：

| App | 客户端内关闭路径 | 补充说明 |
|---|---|---|
| **工商银行 / 工银e生活** | `我的 → 设置 → 个性化设置 → 个性化推荐` | 关闭 |
| **建设银行 / 建行生活** | `我的 → 设置 → 隐私管理 → 个性化推荐管理` | 同时关闭个性化内容与个性化广告推荐 |
| **中国银行** | `我的 → 右上角设置 → 消息设置`（关**营销优惠消息提醒开关** & **营销服务短信通知开关**）+ `个性化设置`（关）；搜索切 **「岁悦长情版」**（长辈版） | 原「缤纷生活」App 已于 2026-06-30 24 时全面停服并迁入「中国银行」App |
| **农业银行** | ① `我的 → 设置 → 个性化推荐`（关）；② `首页 → 消息 → 右上角设置 → 优惠消息 / 服务通知`（关弹窗与定向消息）；可切 `关怀版（大字版）` | `enjoy`/`midc.cdn-static.abchina.com.cn` 误杀致白屏放行；如触发代理风控加 `skip-proxy` |
| **交通银行 / 买单吧** | 交行：`我的 → 设置 → 隐私 / 个性化推荐`（切「关爱版」）；买单吧：`消费者权益保护 → 其他授权管理` + `消息设置/通知管理`（关）；推荐切「关怀版」 | 营销短信回复 `TD` 或致电退订；核实买单吧 SDK 目录仅含个推/厂商 Push 与神策（`ads` 统计组覆盖），无外接广告联盟 |
| **邮储银行 / 邮储信用卡** | `我的 → 设置 → 个性化推荐 / 菜单智能推荐`（推荐切至「关怀版」） | 原「邮储信用卡」公告于 **2026-11-25 24:00** 全面停服迁入「邮储银行」App；未见开关可致电 `95580` 转人工关闭 |
| **招商银行 / 掌上生活** | 招行：`我的 → 设置 → 安全中心 → 设备管理 → 允许个性化推荐`；掌上生活：`隐私管理 → 个性化推荐设置` + `消息通知`（关）；搜或问`小招助理`切「大字版/关爱版」 | 叠加 `banks-mitm` 清理开屏图/视频目录后须强制重开并清缓存以刷新 `preCacheAdvertiseSec` |
| **浦发银行 / 浦大喜奔** | 浦发主端：`我的 → 设置 → 安全设置 → 其他管理选项 → 个性化推荐` + `消息/通知设置` + 切「长辈版」；浦大喜奔：`用户保护中心 → 个性化推荐设置` | 装 `banks-mitm` 可默认拦截 `lban.spdb.com.cn` 开屏列表；`per`/`ebank.spdb.com.cn` 维持红线放行 |
| **动卡空间 / 阳光惠生活 / 发现精彩 / 兴业生活 / 全民生活 / 平安口袋银行 / 华彩生活 / 上银美好生活 / 掌上京彩 / 浙商 / 渤海 / 恒丰** | 动卡空间 `个人中心 → 设置 → 隐私设置 → 个性化广告推荐`；阳光惠生活/全民生活 `隐私管理 → 个性化推荐设置`；平安口袋银行 `授权管理 → 个性化推荐设置`；其余在主端 `隐私设置/授权管理` | **渤海银行信用卡已于 2024-12-30 停服迁入「渤海银行」App**、恒丰原「恒享生活」已合入主端；**上海银行「上银美好生活」将于 2026-11-30 24:00 停服迁入「上海银行」App**；**北京银行「掌上京彩」仍在役** |
| **云闪付** | `我的 → 设置 → 隐私设置 → 个性化推荐设置`（关）+ `设置 → 消息设置`（关）；`首页右上角 "+" → 切换关爱版` | 切勿盲开 `ads.95516.com`/`wallet.95516.com` 拦截，避免版本切换报错、国补页异常与重试风暴 |
| **京东** | `我的 → 设置 → 通用设置 → 隐私设置 → 推荐管理 → 关闭个性化推荐` | 同时在通知管理关闭活动营销推送 |
| **淘宝 / 手机天猫** | `我的淘宝 → 设置 → 隐私`：① `推荐管理 → 关闭个性化推荐`；② `广告管理 → 关闭个性化广告`；③ 关闭 `搜索推荐` 与 `购物车推荐` | `设置 → 通知管理` 关闭「发现精选 / 活动提醒 / 营销推送」 |

---

## 五、第 4 步：操作系统层协同与防风控技巧

### 1. iOS 设备（摇一摇物理阻断 + 银行 VPN 代理检测兜底）

- **彻底消灭「摇一摇」开屏误触（iOS 27.2+，2026-10-27 正式上线）**：
  - 前提：登录**中国大陆 Apple ID** 并升级至 iOS 27.2 及以上版本。
  - 路径：`设置 → 隐私与安全 → 运动与健身 → 限制动作数据 → 编辑`，勾选 **淘宝、京东、掌上生活、买单吧、云闪付及六大行** 等需要阻断的 App，系统底层切断开屏期加速度计与陀螺仪权限。
- **iOS 快捷指令 URL Scheme 启动与真实冷启边界**：掌上生活（`cmblife://`）、买单吧（`mdb://`）等可通过「快捷指令 → 打开 URL → 添加到主屏幕」唤起，但新版将开屏绑定在根启动视图生命周期，**裸无参冷启多已无法稳定跳过开屏**；建议以**官方适老化「关怀版/大字版」+ 端内开关 + `banks-mitm`（掌上生活）+ 限制动作数据**为主（完整 URL Scheme 表与适用范围见 [banks-creditcard-ad-removal.md](banks-creditcard-ad-removal.md)）。
- **银行 App 仍报代理/VPN 检测的三种处理层级**：
  1. 先查 `设置 → 无线局域网 → 当前 Wi-Fi → HTTP 代理` 确认为 `关闭`。
  2. 若已加 `skip-proxy` 仍报错（App 检测本地 HTTP Proxy 服务端口），将 Loon 切换至纯 TUN 模式：`loon://proxymode=tun`。
  3. 若银行 App 强检测系统 `NEVPNStatus`（只要 VPN 亮起即弹窗），在 iOS「快捷指令 → 个人自动化 → App」配置：打开指定银行 App 时「立即运行」`loon://off`；关闭该银行 App 时自动执行 `loon://on`。

### 2. Android 设备（传感器权限 + GKD 无障碍与银行反诈冲突隔离）

- **切断「摇一摇」权限**：在系统设置搜索 `设备动作与方向` 或 `身体传感器`，将 **淘宝、京东** 设为 `禁止`（或 `仅开屏时拒绝`）。
- **GKD 跳开屏的正确使用边界**：
  - **电商（淘宝 / 京东）**：通常不因开启无障碍服务拒服，可配合 GKD 订阅自动点击静态开屏「跳过」按钮。
  - **六大行与信用卡 App（严重注意事项）**：各大行与掌上生活（`com.cmbchina.cmblife`）/买单吧（`com.bankcomm.maidanba`）广泛集成梆梆安全等威胁感知 SDK，通过系统 API 扫描已启用的 `AccessibilityService` 防远控诈骗；**仅把银行放进 GKD 的免打扰（DND）名单并不能从系统无障碍列表中隐身，依然可能触发警告或强退**。
  - **安全解法**：① 通过 MacroDroid / Tasker 配合 Shizuku 在银行进入前台时自动停用无障碍服务、退出后恢复；或 ② 使用 **Island（工作资料）** 沙箱单独克隆运行银行 App，隔断其对个人空间 GKD 无障碍状态的读取。

---

## 六、故障自查与快速回滚清单

| 异常现象 | 最可能原因 | 立即止损方案 |
|---|---|---|
| 淘宝更新插件后全部页面空白或转圈 | 未信任 Loon 根证书，却启用了 `[MITM]` 4 台主机 | 安装并**完全信任** Loon CA 证书；或不装证书时将 `cleanAds` 设为 `false` 并注释 `taobao.plugin` 内 `[MITM]` 两行 |
| 手淘开屏广告依然出现 | XQUIC(UDP/443) 与 `amdc` 旧会话缓存尚未失效 | 完全杀掉淘宝后台 + 开关飞行模式/重启 Loon 后重新冷启动 |
| 手淘大版本更新后首页楼层空白 | `kill-homepage-launch`（`wireless.home.newface.awesome.get`）随新版改版变为强依赖 | 保留 `kill-home-splash`，在本地副本中仅注释 `kill-homepage-launch` |
| 淘宝促销 H5 活动弹窗无法打开 | `alibaba` 组拦截了 `poplayer.template.alibaba.com` | 主配置 `[Rule]` 顶部添加 `DOMAIN,poplayer.template.alibaba.com,DIRECT` |
| 银行提示「存在代理 / 网络风险 / 闪退」 | 遗留 Wi-Fi 代理、`NEProxySettings` 或 `NEVPNStatus` 检测触发 | 按第五节排查：`Wi-Fi 代理=关闭` → `skip-proxy` → `loon://proxymode=tun` → 快捷指令 `loon://off` |
| 京东或银行端突然无图 / 下单失败 | 开启了默认关可选组并命中 CDN/支付校验 | 还原注释 `jd_ad_watchlist`/`jd_telemetry`/`unionpay_optional`/`bank_telemetry`，核对未黑洞 `360buyimg`/`cactus`/`wallet.95516.com` |

> 各插件逐组域名证据与最新统计见对应自动生成文档：[plugins/ads/README.md](../plugins/ads/README.md)、[plugins/banks/README.md](../plugins/banks/README.md)、[plugins/jd/README.md](../plugins/jd/README.md)、[plugins/taobao/README.md](../plugins/taobao/README.md)；全银行与信用卡系深度解析见 [banks-creditcard-ad-removal.md](banks-creditcard-ad-removal.md)；真机逐项验收见 [device-checklist.md](device-checklist.md)。
