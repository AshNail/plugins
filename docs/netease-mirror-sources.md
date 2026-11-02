# 网易云模块与可莉镜像研究（2026-11-02）

> 来源：`ios151/NeteasemusicAd`、`fkingikelee/fkikelee`、`ios151` 仓库组、
> Telegram `@Jsforbaby`。本页只记录**可验证、合规**的部分；VIP 解锁、授权绕过、
> 插件解密等内容不纳入本仓库。

## 1. 网易云音乐 `wyy.sgmodule`

- 上游：https://github.com/ios151/NeteasemusicAd
- 类型：Surge module + `wyyad.js`（约 132KB）。
- 脚本自带环境探测，明确识别 **Loon**（`$loon`）、Surge、QX、Stash 等，
  所以不是纯 Surge 专属；Loon 的 response script/MITM 模型可以承载。

模块内容：
- 10 条 `http-response` 绑定：评论/广告/红点、免流推广弹窗、底部 Tab、顶部 Tab、
  收银台广告、首页推荐、发现页、我的页面、关注列表。
- 5 条 Rule：
  `iadmusicmat.music.126.net`、`iadmat.nosdn.127.net`、`iadmatapk.nosdn.127.net`、
  `httpdns.n.netease.com`、`httpdns.music.163.com`。
- Map Local：多条 `music.163.com` API 返回 `{}`。
- MITM：`music.163.com`、`interface.music.163.com`、`interface3/9.music.163.com`、
  `httpdns.n.netease.com`、`ipv4.music.163.com`。

当前落地：
- `iadmusicmat.music.126.net`、`httpdns.n.netease.com`、`httpdns.music.163.com`
  已由 ads 插件覆盖。
- 本轮公开配置补了 `iadmat.nosdn.127.net`、`iadmatapk.nosdn.127.net`
  两个广告材质域（规则 510→512）。
- **脚本和 Map Local 未默认接入**：模块的 Tab/首页改动会直接影响 App UI，
  且 132KB 远程 JS 有供应链风险；本机没有网易云 App，无法做真机回归。
  需要时可按模块的 10 条响应绑定自行转成 Loon 插件，并在真机逐条启用。

## 2. `fkingikelee/fkikelee` 可莉插件镜像

- 仓库：https://github.com/fkingikelee/fkikelee
- 内容：279 个文件，约 254 个 `lpx/` 去广告插件，README 标题 “R.I.P iKeLee”。
- 性质：**可莉插件（luestr/ProxyResource）的 GitHub 镜像**，不是官方仓库。
- 对比：`lpx/BlockAdvertisers.lpx` 与官方 kelee 缓存去掉 `#!loon_version`
  后逐字节一致（diff 0 行），说明是忠实镜像。
- 价值：`kelee.one` 对全新设备返回 Cloudflare 403 时，这个 GitHub raw 仍 200，
  可作为**私用 fallback**。
- 不默认使用的原因：仓库没有 LICENSE/授权说明，属于未授权转存；
  公共配置继续用官方 `kelee.one` URL，避免把用户引向未授权副本。
  若你只在私人设备上使用，可手动把插件 URL 换成该镜像（本仓库不提交替换）。

## 3. `ios151` 仓库组

- 与本任务直接相关的是 `NeteasemusicAd`（见上）。
- `ios151/Rewrite`（603 个文件）包含大量 App 脚本/模块（BiliBili、KuGou、KuWo 等），
  其中不少是 VIP/会员解锁或私有接口改写；没有逐条审计前不批量接入。
- `ios151/Scripting` 是 Scripting App 的脚本集合（JavBus 等），与 Loon 去广告无关。
- `wloc` 是定位修改，`sub-store-workers` 是订阅转换，均不属于 MITM/去广告覆盖。

## 4. Telegram `@Jsforbaby`

公开预览 12 条，主要是：
- TestFlight/应用分发、Rex 测试版、免费砸壳机器人；
- “看理想”广告+VIP 解锁模块（Loon/Surge/QX）；
- Loon 插件解密、Surge 授权解锁。

**不纳入**：VIP 解锁、授权绕过、插件解密、破解/砸壳相关内容，违反本仓库
“只做净化与观测、不绕过付费/授权”的边界。
其中消息 12 只是推荐 `fkingikelee/fkikelee` 镜像，已按 §2 处理。

## 5. 验证

- 网易云新增域在 Mac 私有档与公开配置同步；预期 `127.0.0.1`/000。
- `music.163.com`、`interface.music.163.com` 等核心域保持可达。
- `npm run check` exit 0；公开配置 512 规则。
- 镜像只做内容一致性对比，不进入公开配置，不复制脚本/插件文件。

## 来源

- https://github.com/ios151/NeteasemusicAd
- https://github.com/fkingikelee/fkikelee
- https://github.com/ios151
- https://t.me/Jsforbaby
