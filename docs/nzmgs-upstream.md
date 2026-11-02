# TG@Nzmgs / ZenmoFeiShi QX 上游研究与移植（2026-11-02）

> 频道：https://t.me/Nzmgs（“怎么个事”）。内容是 **Quantumult X 脚本**，
> 不是 Loon 插件；不能直接导入 Loon。本文只提取其中**明确 host reject**
> 的域名事实，并与现有 ads / App 插件对账；不复制 QX 脚本。

## 上游清单

| snippet | App | 处理方式 |
|---|---|---|
| `helloobike.snippet` | 哈啰 | 多数广告网络已被 ads/meituan 覆盖；脚本逻辑不移植 |
| `xhey-ad-clean.snippet` | 今日水印相机 | TopOn/百度/快手/CLL 广告网络多数已覆盖；补少量缺口 |
| `MT.snippet` | 美团 12.67.403 | 移植 `shark-*` 整主机 reject；脚本私有协议不移植 |
| `TxvideoAD.snippet` | 腾讯视频 | 移植 `iacc.stgw.qq.com` / `tacc.video.qq.com`；共享域不拦 |
| `txsports-ad-clean.snippet` | 腾讯体育 | 移植 `k.ssp.qq.com` / `sports.ssp.qq.com`；`app.sports` 不拦 |

## 本轮已移植（公开主配置）

```ini
DOMAIN,iacc.stgw.qq.com,REJECT
DOMAIN,tacc.video.qq.com,REJECT
DOMAIN,k.ssp.qq.com,REJECT
DOMAIN,sports.ssp.qq.com,REJECT
DOMAIN,shark-mt.meituan.com,REJECT
DOMAIN,shark-default.meituan.com,REJECT
DOMAIN,shark-dp.meituan.com,REJECT
DOMAIN,shark-ps.meituan.com,REJECT
DOMAIN,shark-wm.sankuai.com,REJECT
DOMAIN,shark.dianping.com,REJECT
DOMAIN,mobads-pre-config.bj.bcebos.com,REJECT
DOMAIN,ad.xhey.top,REJECT
DOMAIN-SUFFIX,statisticslinks.com,REJECT
DOMAIN,jt-sdk-ios.oss-cn-beijing.aliyuncs.com,REJECT
DOMAIN,als.baidu.com,REJECT
```

理由：这些在 QX snippet 中是 `host, …, reject` 或广告 SDK 的独立域名；
`statisticslinks.com` 是广告追踪族；`als.baidu.com` 是百度日志。
公开规则 495 → **510**。

## 明确不移植

| 域/规则 | 原因 |
|---|---|
| `app.sports.qq.com` | 腾讯体育核心接口，整域拦会断 App |
| `i.video.qq.com`、`iacc.qq.com`、`config.ab.qq.com`、`rdelivery.qq.com` | 腾讯视频/体育共享配置或播放接口，QX 用 response 脚本按路径改，不用整域拦 |
| `resource.51downapp.cn` | 哈啰广告配置 JSON，QX 用 `script-echo-response` 改写，不是 reject；整域拦可能断功能 |
| `stage2.chelaile.net.cn` | 车来了相关 SDK，跨 App 风险 |
| 40 条 Meituan IP-CIDR / 3 条 IPv6 | 广告 IP 会轮换且可能与其他业务共享；不在无真机验证时硬编码 |
| `MT.js` / `Txvideoad.js` / `txsports-ad-clean.js` / `easybike-ad.js` / `xhey-ad-clean.js` | QX 脚本 API 与 Loon 不同，不能直接运行；需要重写与真机验证 |

## 证据强度与回滚

- 这 15 个域里，`statisticslinks.com` 在 MISP 的 Cloudflare top 列表中可见；
  其余主要是 **QX 单源 host reject**，没有第二份独立规则集交叉证明。
- 已验证：新增域解析 `127.0.0.1`/HTTPS 000；核心域 `app.sports.qq.com`、
  `i.video.qq.com`、`config.ab.qq.com`、`rdelivery.qq.com`、`v.qq.com`、
  `www.meituan.com` 保持可达；Qidian/淘宝/微信广告回归正常。
- **未真机验证**：腾讯视频/腾讯体育/美团/哈啰/水印相机 App 均未安装，
  无法确认域名级拦截是否影响其私有协议。出现“无网络/功能缺失”时，
  按 App 对应行回滚（每行独立，不涉及其它规则）。
- 因此这批规则定位为“可回滚的覆盖补强”，不是与仓库内 A 级 App 插件同级的
  多源证据；后续若拿到第二/第三份公开规则或真机日志，再升级证据口径。

## 验证

- `npm run check` exit 0（54 套件 / 1760 断言，lint 0）。
- 公开配置：41 插件 / **510 规则**。
- 对新增域做 DNS/HTTPS 抽测，预期 `127.0.0.1`/000；核心域
  `app.sports.qq.com`、`i.video.qq.com` 保持可达。

## 来源与边界

- 频道：https://t.me/Nzmgs
- 上游仓库：https://github.com/ZenmoFeiShi/Qx
- 只移植域名事实，不复制脚本代码；原始 QX 脚本版权归原作者。
