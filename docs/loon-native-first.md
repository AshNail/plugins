# Loon 原生优先：能力盘点、差距分析与探索路线

> **一句话结论**：本仓库把「能开关的」做到了极致，但 Loon 有近一半能力**天生不能开关**——它们只能用构建期/发行期手段启用。缺的不是功能，是**开关模型**。
>
> 依据：`docs/loon-feature-checklist.md`（官方文档逐页核对）、两份外部去广告指南、iRingo / Biliverse / DualSubs 三个线上插件工程的实际产物、本仓库 54 套件 / 1646 断言现状。
> 适用门槛：soda/douyin 3.5.1(983)+（gzip 清理 988+）、ads 3.5.3(1008)+。
> 证据标注：**【文档】**= Loon 官方手册明示；**【实证】**= 第三方线上 Loon 插件正在使用；**【未收录】**= 第三方在用但官方手册未收录——**可以保留，但不能当能力点宣称**；**【待证】**= 假设，需真机。

> **落地状态（2026-10-27 第七轮 · soda v2.8.4 / douyin v0.8.4 / ads v2.4.0）**
> 本文的结论已按「常开的进静态层、要改主意的才进开关」落地，不再用发行变体：
>
> | 项 | 状态 | 落点 |
> |---|---|---|
> | E1 QUIC 强制回退 | ✅ 常开 | soda 17 条 / douyin 16 条 `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC)),REJECT`（含 Pangle 10 个分片） |
> | E2 请求免压缩 | ❌ 实测后放弃 | 自家 HAR：upsell gzip 后 183–191 KB，去压缩会膨胀 5~10 倍 |
> | E8a `h2` | ✅ 常开 | `[MITM] h2 = true` |
> | E5 跨层命中矩阵 | ✅ 进 lint | 真实 URL 交叉验证 + 允许清单，可拦截注入的短路配置 |
> | E6 参数 schema | ✅ 第四轮落地 | `src/args/<family>.json` 单源 → `[Argument]` / `SWITCH_LABELS` / README 表；`gen-args --check` 漂移门禁 |
> | E7 lite/strict 变体 | ❌ 取消 | 静态层本来就是常开，不需要靠“装哪个版本”来开关 |
> | E3 `body.mock` / E4 `jq` | ❌ 判死 | 与脚本二选一（§8），且需要完整包络样本；理由见 §9.1 |
> | E9 `DOMAIN-WILDCARD` 字符类 | ✅ 第二轮落地 | ads 11 条数字分片家族 glob（`[0-9]`），覆盖 30+ 台已枚举主机的兄弟分片 |
> | E10 `[MITM]` 通配 | ✅ 第二轮落地 | soda/douyin 用 `ads?-normal*.zijieapi.com` 一条覆盖 Pangle 全族 |
> | E11 层序 | ✅ 结案 | 官方原文：Rewrite 在规则匹配前执行；MITM 内部 Rewrite → Script（§8） |
> | E12 原生 Body 改写短路 | ✅ 进 lint | `response.json.*` / `body.mock` / `body.replace` 命中时同阶段脚本不执行 |
> | E13 规则参数 | 🐞 第三轮修 bug | 72 条规则删掉 Surge 的 `pre-matching`；Loon 只有 `no-resolve`（§10.1） |
> | E14 `[Argument]` schema | ✅ 第三轮进 lint | 25 条声明校验控件/类型/默认值，拦截 `type=bool` 这类别名（§10.6） |
> | E15 `[Host]` 通配右值 | ✅ 语法正交，已在用 | 左值 `*.` 有官方示例（`*.apple.com`），右值 `= IP` 也有官方示例；两者正交，第八轮时 1301 条、当前生效条数以 `plugins/ads/ads.plugin` 为准（§10.3） |
> | E16 压缩协商降级 | ✅ 第四轮落地 | `[Rewrite]` 把 br 降到 gzip，脚本层才解得开（§11.1） |
> | E17 回写 body 清压缩头 | ✅ 第四轮修 bug | `content-encoding` / `content-length` 指向旧压缩体，必须删（§11.2） |
> | E18 存储作用域 | 🐞 第五轮修 bug | `$persistentStore.remove(key)` 会清空**全部**键；改 `write(undefined,key)`（§12.1） |
> | E19 全局直连静默失效 | ✅ 第五轮落地 | `running_model=0` 时插件完全不生效，状态页点名告警（§12.2） |
> | E20 能力覆盖率量化 | ✅ 第五轮落地，第十一轮扩表 | `tools/loon-coverage.py` 把能力表变成可执行清单；第五轮 70.4%，第十一轮补 REJECT 策略变体与注释态口径后为 61 用 / 27 未用 / 28 判死（69.3%，分母变大非退步） |
> | E21 广告面覆盖率量化 | ✅ 第六轮落地 | `tools/ad-surface-audit.py` 把分母从「功能」换成「19 类广告」，现状 71% / 零证书天花板 42%（§13） |
> | E22 「下一步」不许许愿 | ✅ 第七轮落地 | 每类新增 `blocked`（为什么提不了档），`--check` 强制它与 `next_to` 互斥；撤回上一版 90.9% 的假承诺（§13.6） |

---

## 0. 五条判断

1. **增量不在「堆总量」，在「按类型补齐」。** ads 已有 1301 条展开 `[Host]` 映射、30 条 `DOMAIN-WILDCARD` + 11 条字符类家族，域名总量接近饱和；但**按广告类型看仍有整类空白**——贴片、大屏、聚合长尾、直播挂件。第六轮补的是「类」不是「量」：FreeWheel / Sizmek / 倍孜三个域，把视频贴片从「无效」提到「弱效」，并用 `tools/ad-surface-audit.py` 把这条判断变成可回归的数字。`[Rewrite]` 生效动作此前只有 `reject_dict(200)`；第十七轮起 xianyu 在注释态 MITM 层新增 `response.json.jq` ×15（只删信息流广告字段），生效项仍为 0。`header.*` / `body.mock` / `reject_array` 仍未使用（`reject_img` 已在 meituan 注释增强层落地；`header.del` 经实测后主动放弃，见 E2）。
2. **MITM 的真实边界是传输层，不是规则层。** 脚本只能看见 TCP+TLS。两个绕过面：HTTPDNS（已有 `[Host]` + `REJECT-DROP` + `[IP Rewrite]` 三重）与 QUIC/HTTP/3（soda 17 / douyin 16 域常开；meituan/xianyu/qidian 的可选 MITM 层按精确主机带注释态回退，通配主机 `p?.meituan.net` 无法用 `DOMAIN-SUFFIX` 表达、已在生成物中注明）。
3. **三个站点证明的范式是「一份源码 → 多端产物 + 参数 schema + 原生降级版」。** 本仓库第 1 项已做到（`families.json`），参数 schema 已由 E6 补上；原生降级版按 E7 结论明确不做。
4. **当前最大风险是一致性，不是功能不足。** soda 39 条 `response if`、37 处 `requires_body`；同一批开关名曾散在 5 个地方手写，E6 已把 `[Argument]`、`SWITCH_LABELS`、README 表收敛到 `src/args/*.json`，lint 的开关清单也改为从 schema 派生。只剩 `[Script]` 绑定是行为接线，继续由 lint 对账。
5. **边界不动。** 不做激励欺诈；外部资源依赖（`mock_file`、第三方网关）继续拒绝。但**内联 `body.mock`** 不引入任何外部依赖，不在禁令范围内。

---

## 1. 外部资料综述

### 1.1 两份指南：合并后的「形态 × 层」表

两文合计 18 种形态，去重后 10 类。关键不是清单长度，而是**每一类只有一个层真正有效**——打错层的典型症状写在最后一列。

| 形态 | 下发/呈现载体 | 唯一有效的层 | 打错层的症状 |
|---|---|---|---|
| 开屏（在线） | 启动接口 JSON | 响应体裁剪 + 请求拦截 | 空白等待 → 1.5~3s 超时降级 |
| 开屏（离线缓存） | 本地沙盒 | **设置层**关预载 + 素材 CDN | 断网照样出广告 |
| 摇一摇 / 扭一扭 | 设置阈值 + 广告元数据 | **设置层**置零 + 元数据删除 | 只阻断跳转 → 卡在倒计时 |
| 信息流穿插 | Feed JSON 混排 | 字段级裁剪（保留包络） | 整包 reject → 白屏 / 重试 |
| 弹窗 / Upsell | 商业化配置字典 | 字典 + 排序数组**双清** | 只删字典 → 唤起时 NPE |
| 贴片 / 音频插播 | 播放器预配置 | 字段置空 + 状态解绑 | 拦截 → 黑屏等广告超时 |
| 搜索 / 推荐词 | `search-block` | 结构化过滤 | 同信息流 |
| WebView / H5 联盟 | 联盟 JS + 素材 CDN | `[Host]` 127.0.0.1（网络层主场） | 拦接口没用，广告是前端拉的 |
| 激励视频 | `time_token` + 设备签名 | 只做**开关分流**，不伪造 | 伪造 = IVT，封号 / `amount=-1` |
| HTTPDNS / 上报 | 单 IPv4 / 埋点 | `REJECT-DROP` + `REJECT-DICT` | 200 空包 → 秒级重试风暴 |

三条可复用的方法论：

- **「保留包络」原则**：凡是客户端会解析结构体再渲染的接口，删字段不删响应。整包 reject 只适用于 fire-and-forget 的上报端点。
- **「双事实源」陷阱**：凡是「字典 + 排序数组」「开关 + 名单」成对下发的配置，必须同步清理，否则触发客户端空指针。
- **「二次伤害」意识**：广告拦截的代价常常不是漏广告，而是重试风暴、耗电、白屏。`REJECT-DROP` 与 `REJECT-DICT` 就是为二次伤害准备的两个反向工具。

### 1.2 三个站点：六条共同范式

三者同属一个生态（同文档骨架、同 Telegram、同 BoxJs 体系），但产物形态恰好覆盖了 Loon 插件的三个层次。

| 范式 | 证据（实际产物） | 本仓库 |
|---|---|---|
| **① 参数 schema 单一来源** | `arguments-builder.full.config.ts` 一份 TS 配置 → 同时生成 Surge/Loon/QX/Stash/Shadowrocket 的 `[Argument]` + `d.ts` + `boxjs.settings.json` | `src/args/*.json` → `[Argument]` + `SWITCH_LABELS` + README 表（E6） |
| **② 原生假响应，而非脚本造包** | `response.body.mock("text","AAAAAAA=",200,true)` + `response.header.set("grpc-status","0")` 直接伪造 gRPC 空响应 | 只有 `reject_dict(200)` |
| **③ 原生结构化裁剪** | `response-body-json-jq 'del(.data.payment)'`；`mock-response-body data-type=text ...` | 全部走 JS |
| **④ HTTP/2 显式开启** | `[Mitm]` 段 `h2 = true` | 未开 |
| **⑤ 降级发行版** | `loon.rewrite.handlebars` → 零脚本纯 Rewrite 版（同一功能的第二条产品线） | 无 |
| **⑥ 文档骨架固定** | 简介 / 使用方式 / 功能列表 / 安装链接 / 默认设置 / 更新日志 / 相关链接 | 部分（缺更新日志与默认设置表） |

**最有价值的一条是 ⑤**：它不是「多写一个模板」，而是承认**静态能力无法运行时开关**，于是用「发行变体」把它补回来。这一点直接命中本仓库的结构性缺口（见第 3 节）。

### 1.3 一条明确不采纳

Biliverse 的 Rewrite 版把 JSON 接口整体重定向到第三方网关 `app.nanocat.cloud` 由边缘侧改写。效果确实好、零脚本、全平台一致，但**响应数据出境到第三方**，与「自包含、不外发」的仓库纪律冲突。列入不采纳。

---

## 2. 能力矩阵：Loon 全栈 × 本仓库

图例：✅ 在用 / 🟡 半成品（注释里、可选组里）/ ❌ 未用。

| 段 | 能力 | 生效阶段 | 本仓库 |
|---|---|---|---|
| `[Host]` | 精确域 + `*.` 通配 → 127.0.0.1 | DNS | ✅ 1286 条（约 700 根域） |
| `[Rule]` | `DOMAIN` / `-SUFFIX` / `-KEYWORD` / `-WILDCARD` | 规则 | ✅ 30 条通配 |
| `[Rule]` | `IP-CIDR` / `IP-CIDR6` / `USER-AGENT` / `URL-REGEX` | 规则 | ⚠️ 可选组；`USER-AGENT` 前提未满足（ads 无 `[MITM]`），见 §14 |
| `[Rule]` | `PROTOCOL,QUIC` | 规则 | ✅ 常开，soda 17 / douyin 16 域（含 Pangle 10 分片） |
| `[Rule]` | `DOMAIN-WILDCARD` 的 `[0-9]` 字符类 | 规则 | ✅ ads 11 条家族 glob（第二轮） |
| `[Rule]` | `AND` / `OR` / `NOT` 逻辑组合 | 规则 | ✅ `AND,((DOMAIN-SUFFIX,…),(PROTOCOL,QUIC))` |
| `[Rule]` | `REJECT` / `-DROP` / `-DICT` | 规则 | ✅ |
| `[Rule]` | `REJECT-IMG` / `REJECT-ARRAY` | 规则 | ❌ 见 §9.1 |
| `[Rewrite]` | `reject` 族六种（含 `reject_video`） | 复写（规则匹配前）**【文档】** | ✅ 生效仅 `reject_dict` ×3；xianyu 注释层另有 `response.json.jq` ×15；其余见 §9.1 |
| `[Rewrite]` | `header-add` / `header-del` / `header-replace` | 复写 | ❌ 评估后放弃（E2） |
| `[Rewrite]` | URL 重写 / 302 / 307 | 复写 | ❌ |
| `[Rewrite]` v2 | `response.body.mock(...)` / `response.header.set(...)` | 复写 | ❌ **实证可用** |
| `[Rewrite]` | `json.add/replace/delete/jq` · `body.replace` · `body.mock` | 复写 | 🟡 `response.json.jq` 在 xianyu 注释层；其余与脚本二选一，见 §8 / §9.1 |
| `[Rewrite]` | 批量数组参数（`*.header.set([...],[...])`） | 复写 | ❌ 等价多写几条，见 §9.1 |
| `[Script]` | `http-request` / `http-response` | 脚本 | ✅ 57 条绑定（soda 43 / douyin 14） |
| `[Script]` | `cron` / `generic` | 脚本 | ✅ 提醒 + 状态看板 |
| `[Script]` | `network-changed` | 脚本 | ❌ 全量执行、只能弹通知（§9.3） |
| `[Script]` | `${response.status}` / `${response.header[…]}` / `${request.method}` 条件 | 脚本 | ❌ 与 `readBody` 的 not-json 分支重复（§9.2） |
| `[Script]` | `with debug` / `binary_body_mode` / 动态 `timeout` | 脚本 | 🟡 debug 备用；timeout 已用；binary 不用 |
| `[Script]` | `$done()` 无参 = 断开连接 **【文档】** | 脚本 | ❌（未用中断语义） |
| `[MITM]` | `hostname = %APPEND% ...` **【未收录】** | 解密 | ⚪ 未文档化：保留待真机取证（§9.3） |
| `[MITM]` | `h2 = true` **【未收录】** | 解密 | ⚪ 未文档化：防御性冗余，不进能力口径（§9.3） |
| `[MITM]` | `*` / `?` 通配、`-` 排除 **【文档】** | 解密 | ✅ `ads?-normal*.zijieapi.com`（第二轮） |
| `[IP Rewrite]` | 单 IPv4 `drop` | TUN（最早） | 🟡 16 条全注释 |
| `[General]` | `dns/doh/doh3-server` | 解析 | ✅ ads |
| `[Argument]` | `switch` / `input` / `select` | 配置 | ✅ |
| 通知 | `$notification.post` + `openUrl` + `clipboard` | 输出 | ✅ 点通知复制诊断（第二轮） |
| 元数据 | `#!openUrl` **【实证】** | 安装页 | ✅ 三插件详情页直达各自 README（第十轮） |

**统计口径**（第十九轮起由 `tools/loon-coverage.py` 的 `undocumented` 档强制执行）：脚本层 100%，DNS 层 95%，**传输层 100%**（QUIC 回退 + MITM 通配；`h2` 与 `%APPEND%` 不计入，理由见 §9.3），规则层通配 100%（`*` / `?` / `[0-9]` 三类都用上了）；原生响应层仍是 1/20 个动作（`reject_dict`），其余 19 个的判决在 §9.1——**不是没能力用，是每一条的代价都比脚本高**。

---

## 3. 核心发现：开关模型的断层

### 3.1 三层开关模型

Loon 的能力按「能否在运行时改变」分成三层。本仓库只建设了第一层。

| 层 | 机制 | 生效时机 | 能覆盖的能力 | 本仓库 |
|---|---|---|---|---|
| **L1 运行时** | `[Argument]` + `enable=${x}` + 脚本内分支 | 每次请求 | 字段级裁剪、日志、cron、通知 | ✅ 做到极致 |
| **L2 构建时** | 数据源 `disabled` 标志 / 生成器条件 / 注释块 | 打包时 | 静态规则分组、名单批量启停 | 🟡 仅 ads 的 `domains.json` |
| **L3 发行时** | 变体插件（lite / strict） | 用户选装 | **QUIC 拒绝、静态 REJECT、`[IP Rewrite]`、`h2`、纯 Rewrite 版** | ❌ 完全缺失 |

### 3.2 代价：静态层全部躺在注释里

仓库里曾有三处「写好了但永远不生效」的静态能力，它们不是没做，是**没有启用通道**：

| 位置 | 内容 | 现状（v2.8.1 / v0.8.0 后） |
|---|---|---|
| `soda.plugin` / `douyin.plugin` 的 `[Rule]` 段 | 5 行 `DOMAIN,...,REJECT` 严格模式 | **已删除**：被 `blockAdDomains` + QUIC 回退取代，不再提供“手改注释”的分叉 |
| `ads.plugin` 的 `[IP Rewrite]` 段 | 16 条 HTTPDNS 单 IPv4 `drop` | 仍注释：这些 IP 可能与其他业务共用，属于“用户该自己决定”的可选项 |
| `ads.plugin` 的 `PROTOCOL,STUN` | WebRTC 防泄漏 | 仍注释：会打断部分 App 的语音/视频，同上 |

**这就是「全部开关化」原则的隐性代价**：`[Rule]`/`[Rewrite]`/`[MITM]`/`[IP Rewrite]` 都是静态配置，一旦坚持「一切进 `[Argument]`」，等价于**永久放弃静态层**。

但复查时要把“静态层”再拆一刀：

- **前置条件型**（QUIC 回退、h2）：关掉它，所有脚本都失效。**必须常开，不该有开关**——本次落地就是这一刀。
- **策略选择型**（`[IP Rewrite]` 网段、STUN 阻断、整域 REJECT）：关掉只是少一个效果，代价明确。**继续留在注释/开关里**，让用户自己决定。

---

## 4. 八个探索项（按杠杆排序）

### E1 传输层：QUIC 强制回退（杠杆最高）

- **现状**：`blockSplashAd`、`blockAdDomains`、全部 sanitize 脚本都依赖 MITM。如果目标域走 HTTP/3，脚本完全看不见——`device-checklist.md` 的 F 节已经在怀疑这一点，但没有解法。
- **做法**：对**仅有的 8 个 MITM 目标域**加逻辑规则，把 QUIC 打掉，逼客户端回退 TCP+TLS：
  ```ini
  AND,((DOMAIN-SUFFIX,api.qishui.com),(PROTOCOL,QUIC)),REJECT
  AND,((DOMAIN-SUFFIX,beta-luna.douyin.com),(PROTOCOL,QUIC)),REJECT
  ```
  只限定精确域名，不要用 `PROTOCOL,QUIC,REJECT` 全局规则（会伤视频/通话）。
  落地时**没有加任何参数**：Loon 的规则参数只有 `no-resolve`（IP 类用），Surge 的 `pre-matching` 在 Loon 里没有对应写法（§10）；
  域名能否被识别取决于 Loon 的 Fake IP / DNS 关联——如果 App 自己走 HTTPDNS 直连 IP，
  这条规则不会命中（`ads.plugin` 的 HTTPDNS 拦截可以补上这个前提）。
- **收益**：把「可能拦不住」变成「一定拦得住」，是所有脚本型功能的前置条件。
- **风险**：若 App 对这几个域强依赖 H3，回退会慢 100~300ms（首包）；极少数实现不回退 → 接口挂。**必须逐域灰度**。
- **验证**：开规则前后各冷启 3 次，看 Loon 日志中目标 URL 是否出现在「脚本命中」列表（而不是无记录）；同时观察 App 首屏耗时。
- **结论**：**P0，已常开落地**（soda 8 域 / douyin 7 域）。它天生不该有开关——关掉等于让所有脚本看不见流量。这也直接推翻了 E7：「变体」不是必需，直接开就行。

### E2 压缩层：`header-del Accept-Encoding` —— **实测后放弃**

- **原设想**：请求侧删掉压缩协商，让响应以明文回来，从而解除 988 门槛、省一次 `ungzip`。
- **为什么放弃**：自家 HAR 就写着答案——`/luna/commerce/v2/upsell` 在 `content-encoding: gzip` 下是 **183–191 KB**，
  `/luna/treasure/task/page/v2` 是 **16–21 KB**。JSON 的 gzip 比通常 5~10 倍，去压缩等于把这些响应放大一个数量级。
  为了省一次原生 `ungzip`（微秒级）去换每屏几十 KB 到 1 MB 的流量，是负收益。
- **唯一真实收益**：983–987（无 `$utils.ungzip`）能真正清理。但这批用户占比极低，且脚本已有“跳过并打标”的兜底。
- **保留的可能性**：若将来出现“响应体很小、且 Loon gzip 交接有 bug”的端点，可以**只针对该端点**加一条，
  并用 `tests/lint-plugins.py` 的 `Accept-Encoding` 反向断言改名放行。现在默认锁死。
- **后来发现的更精确杠杆**：E2 真正的用途不是「免压缩」而是「禁 br」——把该端点的 `Accept-Encoding`
  **设成** `gzip`（`request.header.set("Accept-Encoding","gzip")`），压缩照旧、体积不变，
  只是不许服务端选 br。当前两个家族所有端点实测都是 gzip，所以不加；一旦诊断头出现 `;ce=br`
  （v2.8.1 起可观测），这条就是最小修法。
- **结论**：**不做**。lint 反向锁死：插件 `[Rewrite]` 里出现 `Accept-Encoding` 直接报错。

### E3 响应层：内联 `body.mock`

- **现状**：`reject_dict(200)` 只能回 `{}`。凡是需要**特定信封**的接口（例如 `{"code":0,"data":{"closeType":"close_win"}}` 这种「告诉客户端没有弹窗」的响应），现在只能写脚本。
- **做法**：v2 复写直接造包，不落盘、不外链：
  ```ini
  response if ${url} ~= /^https:\/\/api\.qishui\.com\/luna\/commerce\/v2\/upsell/ then response.body.mock("json", "{\"code\":0,\"data\":{}}", 200) | response.header.set("Content-Type","application/json")
  ```
  第三方已在这种写法上跑生产**【实证】**；`mock_file`（外链文件）继续禁用，但 `body.mock` 是**内联字符串**，不违反自包含。
- **收益**：把「开关常开、逻辑恒定」的端点从 JS 迁到原生，省一次 JSC 启动 + 整包 parse。
- **风险**：**必须先有 HAR 证明该端点不承载奖励语义**；一旦误伤领奖链路，回滚需要发版。
- **验证**：对候选端点做 A/B：原生 mock vs 现脚本，比对 App 表现与发奖结果。
- **结论**：**P1，本轮未落地**。道理上成立，但当前没有“响应恒为固定信封”的端点能拿出 HAR 证据；误伤领奖链路的回滚要发版，不划算。等真机抓到候选再迁。

### E4 响应层：`json-jq` 承接「纯删除」

- **现状**：`sanitize.js` 1008 行、`settings.js` 629 行，其中相当一部分是「遍历数组删若干 key」。
- **做法**：官方/实证支持 `response-body-json-jq 'del(...)'`**【实证】**。把**无开关分支、无统计副作用**的纯删除迁到 jq：
  ```ini
  ^https:\/\/api\.qishui\.com\/luna\/search-block response-body-json-jq 'del(.data[] | select(.block_type=="advert"))'
  ```
- **收益**：减少 JS 面积 = 减少回归面；jq 在代理核内执行，无 JS 引擎开销。
- **风险**：jq 表达式可读性差、无日志、无法做「保留包络」之外的判断；复杂条件仍应留 JS。
- **验证**：同一份 HAR fixture 分别跑 JS 与 jq，diff 输出应完全一致（可复用现有 `tests/fixtures`）。
- **结论**：**P2，本轮未落地**。原生 `response.json.*` 对 gzip 响应体的行为未确认：脚本自己 `ungzip`，原生动作未必会；若它不解 gzip，迁移后会在 988 以下静默失效。先保留 JS，等拿到“Loon 对 gzip 响应执行 json 动作”的实证再谈减负。
- **追加理由（v2.8.1 补）**：脚本层能解压的只有 `$utils.ungzip`，br / zstd 一律无解码器，且 br 没有魔数、官方复写文档对压缩一字未提。把已知边界的 JS 换成一个行为完全未知的原生动作，等于用一个确定换两个不确定。

### E5 判定层：跨层命中矩阵（治理项，零运行时风险）

- **现状**：lint 已经锁了「脚本 vs 脚本」首条命中，但**没有锁「Rewrite vs Script」「Rule vs Script」**。`soda.plugin` 的 `[Rewrite]` 与 `[Script]` 存在同域绑定（`splash/brand/report` 与 `splash/brand/retrieve` 同前缀），一旦有人把 Rewrite 正则放宽，脚本会静默失效——这正是历史上「settings 双绑定」那类 bug 的同构版本。
- **做法**：给 lint 增加一层矩阵：对每个 URL 样本，列出所有可能命中的 `[Rule]` / `[Rewrite]` / `[Script]`，标出「跨层短路」；允许清单显式登记「故意短路」。
- **收益**：把「注释里写清楚」升级为「CI 挡住」。
- **风险**：无（纯静态检查）。
- **结论**：**P0**，与 E1 无关，可立即做。

### E6 参数层：schema 单一来源

- **原状**：一个开关要改 5 处（`[Argument]`、`[Script]` 绑定、`SWITCH_LABELS`、README、lint 清单）。`SWITCH_LABELS` 是纯手工镜像，已经出现过「加了开关忘了加标签」的情况（状态看板显示不全但不报错）。
- **落地**：`src/args/<family>.json` 是唯一事实源，`src/args/common.json` 只管状态看板的显示顺序。`tools/gen-args.js` 生成三处：
  1. `plugins/<family>/<family>.plugin` 的 `[Argument]` 段（标记 `# >>> GENERATED ARGUMENTS` 之间）；
  2. `src/common/status.js` 的 `SWITCH_LABELS`（标记 `// >>> GENERATED SWITCH_LABELS` 之间）；
  3. `plugins/<family>/README.md` 的参数表（标记 `<!-- >>> GENERATED ARG-TABLE -->` 之间）。
- **没有生成 `[Script]` 绑定**：绑定是「哪个脚本吃哪些参数」的行为接线，不是声明；生成它需要再造一层映射，反而扩大回归面。lint 继续做 `${名字}` ↔ `[Argument]` 对账，typo 仍会被挡住。
- **门禁**：`node tools/gen-args.js --check` 逐字节比对三处生成物，已接入 `tests/lint-plugins.py` 与 `npm run check:args`（在 build 之前跑，防止 build 自动修复后掩盖漂移）。lint 里手写的开关名、默认值、generic 透传清单全部删除，改为从 schema 派生。
- **golden diff**：迁移时两插件 `[Argument]` 43 行与手写版逐字节一致；`SWITCH_LABELS` 只多一个尾逗号；README 表按 `[Argument]` 顺序重排，并补回此前漏掉的 `dailyReminder` / `reminderCron`。
- **收益**：新增开关只改 1 个 JSON；声明、标签、文档不可能再漏。共享开关（`killRewardAds` 等）跨家族语义由测试锁定。
- **验证**：`tests/test_args_schema.js` 37 条断言（源码/压缩各一遍）；坏输入（非布尔 switch 默认值等）由生成器验证器拒绝。
- **结论**：**✅ 已落地**。`[Argument]` 的语法/类型校验仍由 `check_argument_schema()` 独立把关，生成器只保证「三处一致」。

### E7 发行层：lite / strict 变体 —— **已取消**

- **原做法**：给静态能力单独发一个 `-strict` 变体，靠“装哪个版本”来开关。
- **为什么取消**：变体是「静态能力不能运行时开关」的补丁；但本轮真正需要的静态能力（QUIC 回退 / h2）**本来就不该由用户关**——它们是所有脚本的前置条件，不是可选项。给不可选项做变体，等于把“默认正确”拆成“默认可能错”。
- **保留的纪律**：真要给用户选择的（`blockAdDomains`、`blockSplashAd`、`cleanAds`）仍然是 `[Argument]` 开关；`ads.plugin` 的归因/统计组仍是 `domains.json` 的 `disabled` 构建期开关。
- **结论**：**不做**。发行物继续只有三个插件，减少一倍维护面。

### E8 观测层：`h2` 与原生层计数

- **现状**：状态看板能看到 Loon 版本、节点、运行模式、gzip 能力，但看不到「这次请求走的什么协议」「原生层有几条在生效」。
- **做法**：① `[MITM]` 加 `h2 = true`（**当时标注「第三方实证」，第三轮复核后降级**：官方 MitM 文档只列 `hostname` / `ca-p12` / `ca-passphrase` 三个键，没有 `h2`；官方产品页把「解密 HTTPS 和 HTTP/2」列为**默认能力**、没有开关。社区插件通行写这一句，保留它是因为**未知键会被忽略、零成本**，而不是因为它是 HTTP/2 可见的前提）；② 状态看板增加一行「原生层：Rule N / Rewrite M / 脚本 K」——由构建器把计数写进 `families.json` 常量，脚本只读不算。
- **收益**：把「看不见的层」变成可观测数字。
- **风险**：`h2 = true` 若在某个 build 上被当成非法键导致配置加载失败，删掉这一行即可回滚（`[MITM]` 其余键不受影响）。
- **结论**：**P2，部分落地**：`h2 = true` 已进两插件 `[MITM]`（**定位改为防御性冗余，不再计入能力点**——这句直到第十九轮才由工具兑现：`tools/loon-coverage.py` 新增 `undocumented` 档，`%APPEND%` 与 `h2` 从「已用」摘出、既不进分子也不进分母，`tests/lint-plugins.py` 的 `check_mitm_surface()` 再把 `[MITM]` 键面锁成「官方三键 + 这两个显式登记的例外」，`ca-p12`/`ca-passphrase` 永久禁止；取证步骤见 `docs/device-checklist.md` F 段）；计数没有走“构建器写常量”，而是 `families.json.quicCount` + lint 对账真实规则数（更简单，且漂移会直接报错）。

---

## 5. 决策树：什么时候用原生，什么时候用脚本

```text
这个改动能不能用一条原生表达式写完？
├─ 能，且是 [Rewrite] 能表达的（改头 / 拦包 / 假包 / 删固定 key）
│   ├─ 需要用户开关？ ── 是 ──> 条件 Rewrite（${开关} == true && …）★ 仍比脚本轻
│   └─ 不需要 ───────────────> 静态 Rewrite（常开）
├─ 能，但只能落在 [Rule] / [MITM] / [IP Rewrite]（不吃 [Argument]）
│   ├─ 关掉它会让其它功能全部失效？ ── 是 ──> 静态常开，不做开关 ★ 本次做法
│   └─ 用户真的会想关？ ─────────────> 换脚本实现（或让用户改主配置）
└─ 不能
    ├─ 需要读状态 / 写状态 / 发通知？ ── 是 ──> 脚本
    ├─ 需要按字段语义决定「删还是留」？ ── 是 ──> 脚本
    └─ 只是「整包丢弃 / 固定假包 / 删固定字段」 ──> 原生（reject 族 / body.mock / jq）
```

五条判据，按顺序问：

1. **静态可表达？** 能 → 原生。省一次 JSC 启动，少一个失败面。
2. **这段配置能不能吃 `[Argument]`？** Loon v2 的 `[Rewrite]` 能（`${开关} == true`）；`[Rule]` / `[MITM]` / `[IP Rewrite]` **不能**。只有“不能 + 又必须可关”才退回脚本。
3. **关掉它会不会让其它功能全部失效？** 会 → 它是前置条件，必须常开，别做成开关（QUIC 回退、h2 都属于这档）。
4. **需要跨请求状态？** （打卡、统计、去重）需要 → 脚本。
5. **需要「保留包络」的字段判断？** 需要 → 脚本；纯删固定 key → jq。

> 旧版本文写的是“需要开关就只能脚本”，这句在 v2 Rewrite 上是错的：`[Argument]` 在 Rewrite 条件里可用（官方 Plugin 文档的 `response if ${enabled} == true …` 就是例子）。本次没有因此迁移现有脚本，是因为现有开关绑定的都是响应体字段逻辑，不是“拦/不拦”这种一句话判断。

---

## 6. 路线图（2026-10-27 更新）

### 已完成（本次落地）

| 项 | 动作 | 验收 |
|---|---|---|
| E1 | soda 17 / douyin 16 条 `AND+PROTOCOL,QUIC` 回退（含 Pangle 分片族），常开 | lint 锁定集合；真机 F 段观察回退耗时 |
| E8a | `[MITM] h2 = true` | lint 锁定；状态看板不再显示“未知协议” |
| E8b | 状态看板「静态层：QUIC 回退 N 域」 | `families.json.quicCount` + lint 对账 + `test_status` 4 条断言 |
| E5 | lint 跨层命中矩阵 | 注入 `DOMAIN,api.qishui.com,REJECT` / 终止型 Rewrite 均能报错 |
| E6 | `src/args/*.json` 单源生成 `[Argument]` / `SWITCH_LABELS` / README 表 | `gen-args --check` 漂移门禁 + `test_args_schema` 39 断言 ×2 |
| 清理 | 删除两插件注释里的 `[Rule]` 严格模式 | 常量面 -10 行，不再有“手改配置”的分叉 |

### 待真机（不改代码，只观察）

| 项 | 观察点 | 回滚 |
|---|---|---|
| E1 | 冷启 3 次首屏耗时；Loon 规则日志命中 QUIC 回退 | 删该域一行 |
| E2 | `/luna/*` 响应是否还有 `Content-Encoding` | 删对应 rewrite 行 |
| E8a | 若报网络错误，先删 `h2 = true` 复测 | 删一行 |
| §8 层序 | 同域放 Rewrite reject 与 Rule REJECT-DICT，看日志谁命中 | 实验后删除 |

### 明确不做（见第 7 节）

`body.mock` / `json.jq` 的批量迁移、请求免压缩（E2）、`-strict` 变体、全局 QUIC 拒绝、第三方改写网关。

---

## 7. 不采纳清单（增量）

| 项 | 理由 |
|---|---|
| `mock_file` / 远程 mock 文件 | 外部依赖，断网即失效；与自包含冲突 |
| 第三方改写网关（`*.nanocat.cloud` 类） | 响应数据出境，违背边界 |
| 全局 `PROTOCOL,QUIC,REJECT` | 伤视频/通话；只允许按域 + `AND` 组合 |
| 用 `302` 把广告请求重定向到本地服务 | 需要额外进程；`body.mock` 已能覆盖同一场景且零依赖 |
| 把 `[Argument]` 开关写进 `[Rule]` / `[MITM]` / `[IP Rewrite]` | 语法上不成立（这几段不支持变量）；但 `[Rewrite]` **支持** `${开关}`，所以“需要开关”不再是退回脚本的理由 |
| `-strict` 变体 | 静态层（QUIC / h2）是前置条件，不是可选项；给它做变体等于把正确拆成可能错 |
| 静态层开关（`quicFallback=true/false` 之类） | 关掉后所有脚本静默失效，属于“看起来能配、实际只会配错”的开关 |
| 手改注释启用严格模式 | 用户改不了 raw 插件；已用 `blockAdDomains` + QUIC 回退覆盖同一场景 |
| 引入 BoxJs 作为配置面板 | 多一个外部依赖；现有 `[Argument]` + 状态看板已覆盖单 App 场景 |

---

## 8. 附：层序已结案（第二轮，2026-10-27）

上一轮这里是 `[待证]`。本轮把官方复写文档的「生效范围」原文抓了下来，不用再猜：

> **Rewrite 仅对 HTTP 和经过 MitM 解密的 HTTPS 请求生效，并在规则匹配前执行。**
> —— [nsloon.app/docs/Rewrite/rewrite_v2](https://nsloon.app/docs/Rewrite/rewrite_v2)【文档】

同一页还给了三条决定性的执行规则：

| 文档原文 | 对配置的含义 |
|---|---|
| Request 阶段产生终止响应时，Request / Response Script 均不执行 | 终止型 request 复写 = 该 URL 的脚本全废 |
| Response Body Rewrite 命中时，Response Script 不执行 | 原生 Body 改写与脚本**二选一**，不是叠加 |
| Request Body Rewrite 或 Request Body Mock 命中时，Request Script 不执行 | 同上，请求方向 |
| 只修改 Request Header 的 Rewrite 不会因此新增禁用行为 | header 级复写可以和脚本共存 |

于是 MITM 内部的顺序是 **Rewrite → Script**，两个阶段都各自「第一条命中」。
`[Rule]` 位于复写之后（文档原话），而 `[Host]` 127.0.0.1 是 DNS 阶段、必定最早。

**这正好解释了 lint 为什么必须保守**：只有进入 HTTP 引擎的连接才会有 Rewrite/Script，
被 DNS 黑洞吃掉的请求根本走不到那一步；而一个 MITM 域上同时写 `[Rule] ...,REJECT`
与脚本时，谁先命中取决于实现细节，文档没有承诺。所以 `check_cross_layer` 继续按
「两层都可能先命中」报错，不押注顺序。

但它现在多锁了一类**有文档依据**的短路：`response.json.*` / `body.mock` / `body.replace`
这类原生 Body 改写命中时，同阶段脚本不会执行。这条不是保守假设，是官方明写的二选一——
以后谁想「用原生 json.delete 顺手再挂个脚本事后处理」，lint 会先拦住。

原计划的「5 分钟同域对照实验」取消：它能证明的只是实现是否符合文档，
而**按文档写配置本来就是纪律**，没必要用一次真机实验去换一个已知答案。

---

## 9. 第二轮：把「没用到的能力」逐个判死

第一轮只回答了「还能加什么」。这一轮把 Loon 3.5.1(978/983) 之后新增、以及我们一直没碰的能力**全部列一遍**，
每条给出判决和理由——**没写理由的「暂不支持」不算判决**。判决只有四种：✅ 在用 / 🟡 备用（说清触发条件） / ❌ 不用（说清代价） / ⛔ 禁用（会破坏安全或纪律）。

### 9.1 复写 v2：20 个 Action 的完整判决

| Action | 判决 | 理由 |
|---|---|---|
| `reject_dict(status)` | ✅ | 上报端点专用：200 + `{}` + `application/json`，SDK 解包不报错、不出网 |
| `url.replace` | ❌ | 只对「换后端继续请求」有意义；本仓库没有镜像源，广告的正确处理是不出网 |
| `redirect(302/307)` | ❌ | 重定向会把客户端**送去另一个地址**继续请求；`reject_dict` 零成本达成同一目的 |
| `reject(status)` / `reject(status, body)` | ❌ | 空包与文本包的 `Content-Type` 是 `text/plain`，按 JSON 解的 SDK 会进错误分支 |
| `reject_img(status)` | ❌ | 1×1 GIF 适合「图位需要一张图」；我们的广告图走 `[Host]` 黑洞，根本到不了 MITM |
| `reject_array(status)` | 🟡 | 端点响应必须是数组时才换（`[]`）；目前没有一个这样的上报接口 |
| `reject_video(status)` | 🟡 | 开屏/激励素材若**直接在 MITM 可见的接口上返回视频字节**，用空视频比空包友好（播放器解码成功、不进重试）。现实里素材都走 CDN 域名拦截，用不上 |
| `*.header.add/set/del/replace` | ❌ | 我们改 Body 不改头；唯一想改的 `Accept-Encoding` 已由体积实测否决（E2，见 §4） |
| `*.body.replace(Regex, …)` | ❌ | 正文级正则替换对 JSON 不安全：嵌套括号、转义序列、同名字段都会误伤。字段级裁剪必须走解析 |
| `*.json.add/replace/delete(KeyPath)` | ❌ | 现有 sanitize 全是字段级 + 正则 prune + 开关分支，且与脚本二选一（§8）；同一 App 内没有「无脚本、只删固定 key」的端点 |
| `*.json.jq(JQ)`（原生 jq） | 🟡 **xianyu 注释态落地** | 与脚本二选一，但在**没有响应脚本**的可选 MITM 层成立：xianyu 用 15 条 jq 只删信息流广告字段/节点、保留 mtop 包络，证据来自 ddgksf2013/fmz200 的 `http-response-jq`；默认注释、逐条启用 |
| `*.json.jq_file` | ❌ | 插件资源文件是包外依赖，违背自包含纪律；内联 jq 已够用 |
| `request.body.mock(_file)` | ❌ | `mock_file` 依赖外部资源（纪律禁止）；内联 `mock` 需要完整包络样本，违背「保留包络、只删字段」 |
| `response.body.mock(_file)` | ❌ | 同上；且 mock 响应在请求出网前生成，会把同 URL 的脚本全废掉（§8） |
| 批量数组参数（`header.set([...],[...])`） | 🟡 | 等价于多写几条，只省配置行数；等真的出现「一次改 5 个 key」再换 |

### 9.2 脚本 v2：条件与 `with` 属性

| 能力 | 判决 | 理由 |
|---|---|---|
| `${request.method}` | ❌ | 现有端点没有按方法区分的行为 |
| `${request.header['x']}` | 🟡 | 可用于按 `x-tt-*` 区分端侧版本；现在没有需要分版本的处理 |
| `${response.header['Content-Type']}` | 🟡 | 能做「只处理 JSON 响应」的匹配层守卫，但与脚本内 `readBody` 的 `not-json` 分支重复；且 `Content-Type` 写错的接口会被静默漏掉 |
| `${response.status}` | 🟡 | 能做「只改 200」的守卫，省一次 Body 交接；代价是错误响应彻底不可见，与 `debugLog` 的排障目的冲突 |
| `with enable=${开关}` | ✅ | 全部 57 条绑定在用 |
| `with timeout` / 动态 `timeout=${参数}` | ✅ | 每条 10s（cron 60s） |
| 动态 `cron ${reminderCron}` | ✅ | 每日提醒的 cron 由 `[Argument]` input 提供 |
| `with tag` / `with img_url` | ✅ | 状态按钮的图标与分组 |
| `with debug=${开关}` | 🟡 | Loon 自己的脚本调试开关；现在 `X-Soda-Plugin` 头 + `console.log` 已能回答「跑没跑、跑到哪步」，等真机排障需要更细粒度时再挂 |
| `binary_body_mode` | ❌ | 处理的全部是 JSON 文本 |
| `$done()` 无参（断开连接） | ❌ | 等价于 `REJECT-DROP`，会给客户端「连接被掐」而不是「服务器回了空」，反而更容易触发秒级重试 |

### 9.3 规则、MITM、General

| 能力 | 判决 | 理由 |
|---|---|---|
| `DOMAIN-WILDCARD` 的 `[0-9]` 字符类 | ✅ **本轮落地** | 官方支持 `*` / `?` / `[...]` 三类通配；`[0-9]` 不能把匹配扩散到别的品牌主机，`[a-z]` / `[!0-9]` 会，所以只放开数字类 |
| `DOMAIN-WILDCARD` 的 `[abc]` / `[!abc]` | ❌ | 同上：字母类会让「保护名单不可被通配命中」这条保证失效 |
| `[MITM]` 的 `*` / `?` 通配 | ✅ **本轮落地** | `ads?-normal*.zijieapi.com` 一条覆盖 Pangle 全部分片 |
| `[MITM]` 的 `h2` | 🟡 **本轮降级** | 官方 MitM 文档只列 `hostname` / `ca-p12` / `ca-passphrase`，**没有 `h2`**；官方产品页把「解密 HTTPS 和 HTTP/2」当成默认能力、无开关。社区插件通行写，保留是因为未知键被忽略、零成本——但**不能再当能力点宣称**，统计口径已剔除（第十九轮才真正兑现：`tools/loon-coverage.py` 新增 `undocumented` 档，`%APPEND%` 与 `h2` 一起退出分子分母；真机取证三条见 `docs/device-checklist.md` F 段） |
| `[MITM]` 的 `skip-server-cert-verify` | ⛔ | 全局键、插件改不到；语义是「不校验服务端证书」，等于对任意中间人放行，安全降级 |
| `[MITM]` 的 `ca-p12` / `ca-passphrase` | ⛔ | 用户私钥，插件绝不能写入或覆盖。第十九轮起是断言：`check_mitm_surface()` 扫每个插件 `[MITM]` 段有效行，出现即报错 |
| `[MITM]` 的 `-` 排除 | 🟡 | 只在「宽通配 + 个别域不解密」时有意义；现在没有宽通配的业务域 |
| `PROCESS-NAME`（进程规则） | ❌ | 仅 macOS 生效，iOS/tvOS 忽略；本仓库只服务 iOS |
| `REJECT-IMG` / `REJECT-ARRAY`（规则层） | ❌ | 与 `reject_img`/`reject_array` 同因；规则层还会丢掉「逐请求日志」 |
| 插件 `[General]` 9 个白名单键 | 🟡 | 只用了 `dns-server` / `doh-server` / `doh3-server`；`real-ip` 与 FakeIP 相关，但本仓库走 `[Host]` 静态映射，不需要 |
| `network-changed` 脚本 | ❌ | 一次网络变化会执行**所有**已启用的 Network Changed 脚本；能做的事只有「换网弹通知」，属于纯打扰 |
| `$dns.query` / `$crypto.aes` / `$utils.gzip` 上行 | ❌ | 无对应需求；`$dns.query` 还会突破「脚本不外发」的安全门禁 |
| `$persistentStore.remove()` | ❌ | 清空**全部**脚本的存储键，会误删其他插件的数据 |
| `$notification` 的 `mediaUrl` / `delay` | 🟡 | `mediaUrl` 需要额外下载图片；`delay` 想解决的「先出结果页再弹通知」在 generic 里本来就不成立 |
| `$notification` 的 `clipboard` | ✅ **本轮落地** | 点通知即复制完整诊断，用户可直接粘进 issue |
| `$config.setRunningModel` / `setSelectPolicy` | ❌ | 会改全局运行状态，插件不该有这种副作用 |

### 9.4 本轮真正落地的四件事

1. **ads 插件新增「数字分片家族层」**：11 条 `DOMAIN-WILDCARD` + `[0-9]`，把 `ads3/ads5 × 5 后缀`、
   `p3/p6/p9-ad-sign`、`v1/v2/v3-ad.video.yximgs`、`pangolin-sdk-toutiao1..5`、`dns9..12.quad9` 等
   **11 个真实家族、30+ 台已枚举主机**折叠成族，顺带覆盖没见过的兄弟分片。build 阶段强制「必须覆盖 ≥2 台已枚举主机」，
   凭想象造的家族进不来。
2. **soda/douyin 的广告拦截从「单分片」升级为「全族」**：`[MITM]` 用一条 `ads?-normal*.zijieapi.com`，
   `[Rule]` 逐个列 10 个分片做 QUIC 回退，`block-domains.js` 的 `BLOCKED_HOSTS` 支持 `?`/`*`。
   以前只要服务端把分片从 ads5 换成 ads3，`blockAdDomains` 就整个静默失效。
3. **层序结案 + 新增跨层守卫**：原生 Body 改写与脚本的互斥关系进 lint（§8）。
4. **状态通知带剪贴板**：`attach.clipboard` 复制完整诊断。

### 9.5 仍然不碰的两件事

- **不做「响应体免压缩」**（E2）：`commerce/v2/upsell` gzip 后 183–191 KB，去压缩膨胀 5~10 倍，负收益。lint 反向锁死。
- **不做 `body.mock` 造数据**：需要完整包络样本，而包络一旦写错就是白屏/NPE；「保留包络、只删字段」这条原则不破。

### 9.6 分发层：唯一「不在插件文件里」的官方能力（第二十二轮补上门禁）

官方 `docs/Scheme/` 把 URL Scheme 列成两张表：常用操作 `on` / `off` / `editconfig` /
`flowmodel=direct|filter|proxy` / `proxymode=tun|mix` / `update?sub=all`，导入资源七种键
`sub` / `nodelist` / `rules` / `plugin` / `iconset` / `geoip` / `parser`，格式
`loon://import?plugin=encode(url)` 并明写「**导入地址需要先进行 URL 编码**」；网页打不开自定义
Scheme 时把 `loon://` 整段换成 `https://www.nsloon.com/openloon/`，两者作用相同。

这一层过去是**门禁的空白**：所有语法面检查的语料都是插件文件与脚本源码，README 里的安装链接一条没被查过，
能力表只能记 `na`。但它是用户接触插件的第一道门——`[Host]` 写错只少拦一个域名，
`import?plugin=` 写错是**用户点了导入、装进的是别人的插件**。第二十二轮起由
`tests/lint-plugins.py::check_scheme_links()` 逐条校验（第四条官方语法面门禁）：操作名与取值走白名单、
资源键限官方七种、地址必须已编码、`plugin` 解码后必须匹配 `…/plugins/<slug>/<slug>.plugin`
（目录名 ≠ 文件名也算错）且文件真实存在、表格同一行标注的 slug 必须与链接一致，并要求
**16 个插件每个都在自己的 README 里至少链向自己一次**。当前读数 38 条链接、16 个自链、0 错误；
七道变异（假操作名 / 假资源键 / 未编码 / 指向别的 slug / 目录文件名不一致 / 指向不存在的插件 /
自造 `flowmodel=fast`）各报 1 条。插件内声明不了的结论不变——`na` 依然不进利用率，
但从「没人管」变成「有白名单、有回归」。

### 9.7 文档里的数字也是数据源（第二十四轮补上门禁）

一个仓库里最容易陈旧的句子不是配置，是「一共有多少条」：`1499 条生效 Host`、`13 个 App 插件`、
`官方文档 26 页`、`1646 断言`。它们今天都对，但只对是因为有人记得改——而这类声明会被读者当成
**风险面的规模**来用：加一批域名忘了改文档，读者就照着虚高（或虚低）的数字判断该不该装。

第二十四轮起，每个数字都有一个**唯一的机器出口**，文档只是它的一种显示方式：

| 文档里的声明 | 机器出口 |
|---|---|
| `plugins/ads/README.md` 的分组条数、生效/注释 Host、exact/wildcard、通配与家族拆分、可选 Rule 的 27/16/1 | `tools/build-ads.py --stats-json` |
| 规模页 `docs/repo-metrics.md` 的正文页数、能力表 175 条与五档分布、旁路路径数、广告类型数、上游黑名单家数、App 插件数 / 覆盖 App 数 / 增强层个数 | `tokens.json`、`loon-coverage --check`、`bypass-audit --check`、`ad-surface-audit --check`、`app-coverage-audit.SOURCE_NAMES`、`src/apps/*.json` |
| 「N 套件 ×2 = M 套件 / K 断言」与 `tests/README.md` 的断言分布表 | `tests/run-all.py` 本次实跑的 per-suite 计数 |
| 本节自己的 `1499 条生效 Host`、`13 个 App 插件`、「官方文档 26 页」、「能力表 175 条」 | 同一批出口（ads 计数在同一次 lint 进程里缓存复用） |
| 文档里复述的「门禁管了 N 条声明」与 `readme numbers: N …` 成功行 | 同一次 lint 真实核对成功的条数 |
| 文档任意一行同时出现 `test_xxx` 与「N 断言」 | 该套件本次实跑数（查不到套件名直接报错） |
| 真机清单的 J 段插件数、正文页数、`ads=<版本>` 式版本引用 | `src/apps/*.json`、`tokens.json`、各插件 `#!version` |
| 「共 N 个（a b c …）」这类自数式列举 | 括号里真列出的项数（文内自证，不需要外部出口） |

比法是**题注锚定**而不是按位置数列：`(\d+) 条生效 Host`、`exact (\d+) / wildcard (\d+)`、
表格行标签 → 该行所有 `N 组 / N 条`。改一句不会牵动另一句，调换顺序也蒙不上。
第一次运行抓到的是**四条**真漂移（正文页数 30→26、核心广告组 1166→1349、HTTPDNS 层 129→130 与 72→73、
Scheme 导入种类 6→7），分属四个不同出口——说明「数字散落在叙述里没人回头改」是系统性缺口，不是某次手误。
第二十五轮把这层的**自己**也放进去：连「门禁管了 N 条」这句元声明都由门禁复算，于是扩容门禁时
说明文档一旦不跟着改就立刻变红（实测：给本节加绑定，另外两个文件里复述的旧数当场各报一条）。
同一轮把手写文档过了一遍**数字普查**（每个文件「N 条/N 个/N 页」式陈述的密度），据此把真机取证清单
也纳入口径——那里连「共 11 个（列举）」这种自数句都被要求列举数与声明数一致。

### 9.8 「红线」也是数据源（第二十七轮补上门禁）

§9.7 把「N 条」钉死之后，文档里还剩一类**长得像名单、其实是散文**的句子：每个 App 插件的
`红线（绝不进任何拦截组）：mapi.m.jd.com / cactus.jd.com / dns.jd.com …`。没有任何门禁能回答
「这条规则碰没碰红线」，因为红线在一个字符串里，规则在另一个数组里。

第二十七轮把它结构化成 `src/apps/<slug>.json` 的 `redlines`（当前 111 条 App 红线，覆盖 13 个 App 的红线声明）：

| 字段 | 作用 |
|---|---|
| `domain` | 红线域（精确主机或主域） |
| `kind` | `host`=这台主机绝不碰；`family`=这个主域不做整族操作（其下的精确广告子域仍然允许——那正是全局插件处理共享域的一贯纪律） |
| `quote` | 该 App `comment` 里的原文片段，必须**逐字存在** |
| `why` | 为什么不能拦 |

`quote` 是防伪层：把猜测写成字段是最容易从结构化里钻回来的造假路径。凭品牌名补一个
`sso.jd.com`、或从 `api.io.mi.com` 里截出 `io.mi.com` 当主域，都会因为「quote 不在原文里」
或「domain 不是 quote 中的独立 token」当场构建失败。111 条红线的规模不是估的——它就是
`tools/build-ads.py --stats-json` 数出来的，本节这两个数字也钉在那个出口上。

判定只禁两种操作：把红线名字本身黑洞掉，或用任意一层通配/后缀把它捞进去；红线之下的精确广告子域
不算命中。执行点在两个构建器：`build-ads.py` 管全局插件的默认生效组，`build-apps.py` 管按 App 插件
自己的组与 `DOMAIN-SUFFIX` 规则（后缀吞整族，判定方向相反）。注释掉的组不参与——红线只管默认就会生效的东西。

上门禁当轮抓到的不是别人，是 ads 自己：`dns.jd.com` 在 httpdns 组默认黑洞、`=union.jd.com` 在 cn_union 组
默认黑洞（`=` 会连子树一起拦），而 `jd.json` 的红线原文逐字写着这两条。**「全局插件拦、按 App 插件说绝不碰」
这类矛盾只有把两边都读成集合才会暴露**——它同时躺在两个文件里很久，此前没有任何一步会去比。处置不是删掉能力，
而是把两条移进新的默认注释组，把两面理由（防绕过收益 vs 无回退取证）一起印在组注释里，让选择权回到用户。

同一轮补了认罪层 `redline_overlap`：DOMAIN-WILDCARD 没有例外语法，`ads.*` 一定会连微信声明必须放行的
`ads.privacy.qq.com` 一起命中。取舍不许藏在叙述里——**命中集由 glob 与 redlines 实算，必须与显式列举的
认罪清单逐条相等**，漏一条或多一条都构建失败，插件段首注释也会打出这条取舍。默认关闭的能力层，
同样要交代它一旦打开会踩到谁。

### 9.9 同一个文件里的第二份红线名单（第二十八轮）

第 27 轮把红线从 `comment` 散文里搬进数据之后，还剩一个没问过的问题：**这个文件里还有谁在划红线？**
答案是每个 App 自己就有的另一份名单——`triage_exclude`（「上游清单建议拦、我们裁决不拦」的判决台账），
它的 label 里就写着「交易/风控红线」「推送/云红线」「基础设施红线」。台账只被覆盖率审计器读过，
从不参与构建判定，于是同一个 App 文件里并存两份红线、两种写法，互相不知道对方存在。

第二十八轮把它们接成一条链：

- `redlines` 条目多第二种出处 `ledger: {"label", "glob"}`，要求这一对**逐字存在于本文件 `triage_exclude`**，
  且 `fnmatch(domain, glob)` 成立——域名必须是那条 glob 表达出来的形态，不许借台账的名义另起名字。
- 反向门禁：台账里 label 带「红线」二字的每条 glob，本文件 `redlines` 必须至少有一条能解释它，
  否则构建失败，报错直接把「要么补域名、要么改标签」两条路都写出来。

第一跑抓到三条，性质各不相同：

1. **真冲突**：`resolver.msg.xiaomi.net` 在 ads 的 httpdns 组默认黑洞，而 `mijia.json` 的台账把它归在
   「推送/云红线 `resolver.msg.*`」下。它逃过第 27 轮那道门禁，只因为红线写的是台账而不是那句 comment。
   处置与 `dns.jd.com` 一致：移进「与按 App 插件红线冲突的候选」默认注释组，两面理由印在组注释里（ads 2.7.9）。
2. **宽度不一致**：`*xmpush*` 比 comment 里那句「`api.xmpush.xiaomi.com` 系」宽，覆盖率报告里
   `api.xmpush.global.xiaomi.com` 是真实候选，结构化名单却没有它——同一件事的两种宽度互不知情，补成独立条目。
   `gia.*` / `gias.*` 同理：第 27 轮把它们记成「散文里只有 `gia(s).jd.com` 这种合并写法、无法编码」的残留，
   其实台账里就是两条字面 glob，于是残留当场关闭。
3. **散文 glob 的宽度 ≠ 红线的宽度**：`*.sec.miui.com` 名义上把 ads **有意**黑洞的 `adv.sec.miui.com`
   （小米系统广告位）也划进红线。把它钉成成员主机 `api.sec.miui.com` 之后语义才对：任何整族黑洞
   （`*.sec.miui.com`）依然被禁，而红线之下的精确广告子机照拦——这正是 §9.8 那条判定本来就在做的事。

最后剩五个 glob（`sec-*`、`sec.*`、`security.*`、`findapi.*`、`statusapi.*`）在十四份上游清单的
全站候选里**一次都没有命中过**——覆盖率报告里没有一行属于它们。没有可钉域名的 catch-all 不是红线，
是防御性散文。处置是改标签，不是改解析器：把它们从「安全族红线」「推送/云红线」拆进
「…模式放行（未取证到域名的 catch-all）」。「红线」二字从此只出现在结构化得了的地方，与第 50 条
「格式纪律而不是解析宽容」、第 48 条「拆分归属应当是数据结构」是同一条纪律。

### 9.10 红线管的是「域名类匹配面」，而这种面有四种载体（第二十九轮）

前两轮把红线变成可判定的集合运算之后，还剩一个没问过的问题：**判定读的是哪些载体？**
`redline_hit()` 拿到的输入只有 `[Host]` 条目和 `[Rule]` 行的**首 token**——于是域名类拦截面里
另外三种从来不在比较之内：

| 载体 | 本轮实测（全部插件的生效 `[Rule]` 行，共 50 行 / 39 个域名匹配项） | 第 27/28 轮的门禁看得见吗 |
|---|---|---|
| `[Host]` 精确 / `*.` 条目 | ads 生效 1499 条 + 各 App 插件自己的条目 | 看得见 |
| 顶层 `DOMAIN` / `DOMAIN-SUFFIX` | 4 项 | 看得见 |
| **`AND((DOMAIN-SUFFIX,…),(PROTOCOL,…))` 里嵌套的后缀** | 33 项 | **看不见**（首 token 是 `AND`） |
| **`DOMAIN-KEYWORD`** | 2 项 | **看不见**（压根不在遍历里） |

盲区不是理论风险，宽度关系是反的：**关键词比后缀更宽**。ads 现在写的是
`DOMAIN-KEYWORD,httpdns,REJECT-DROP`，哪天有人把它「简化」成 `dns`，就会默认生效地把
`dns.jd.com`（京东自建 HTTPDNS， jd 插件的 host 型红线）整条捞走；写成 `io.mi` 会捞走
`api.io.mi.com`（米家掉设备）；写成 `ads` 会捞走 `ads.privacy.qq.com`——正是 §9.8 认罪层里
那条「微信声明必须放行」的主机。三条都在本轮实算出来，不是推测。

处置分三层，都住在 `tools/redlines.py`，构建器与 lint 共用同一份判定：

1. **抽取表由分类表生成**：`DOMAIN_MATCH_TYPES`（`DOMAIN` / `DOMAIN-SUFFIX` / `DOMAIN-KEYWORD`）
   既决定「谁受红线约束」，也决定「`rule_match_items()` 从规则里读出什么」——加一种类型进分类表，
   判定自动认得它，不需要再改第二个正则（第 48 条「拆分归属应当是数据结构」的又一次应用）。
   三种类型三种语义：精确等于、后缀吞整族、**关键词命中主机名任意位置**。
2. **两个构建器都补上嵌套与关键词**：`build-apps.py` 不再用 `split(",")[0]` 判类型，
   `build-ads.py` 对 `[Rule]` 段的每条**生效**行跑同一套比较。默认注释的行照旧豁免。
3. **lint 在产物层收口，并审计「有没有未登记的新匹配面」**：`check_rule_vectors()` 扫全部
   16 个插件的生效 `[Rule]` 行（`npm run build` 生成的 douyin/soda 那两个插件不经过任何
   Python 构建器，只有产物层看得见它们），把出现过的类型 token 与分类表对差——
   **出现没登记过的类型就构建失败**，要求人先回答「它碰不碰得到红线」。这条是防未来的：
   今日写 `DOMAIN-REGEX` 或 `URL-KEYWORD` 不会悄悄绕过红线判定，它会当场要求归类。

URL 路径 / UA / 端口这几类匹配面**不**在禁止之列，因为它们不黑洞主机：`URL-REGEX` 命中某个
路径形态才动作，红线保护的是「这台主机还能不能被解析到」。这个边界本轮写进分类表
（`NON_DOMAIN_MATCH_TYPES`）和文档，而不是留在叙述里——读表的人知道哪些面被管、哪些面是有意放过。

### 9.11 还有一张手写的保护名单，它成型时还没有 App 插件（第三十轮）

红线链上有第三份名单，此前一直没人和它对过差：`src/ads/protected-roots.json`——
「共享主域禁止整族黑洞，只允许精确广告子域」那张表。它是**手写**的，103 个根全部来自全球广告
网络的视角（`qq.com` / `jd.com` / `xiaomi.com` / `meituan.com`…），写它的时候按 App 拆分的插件
还不存在。拿它和红线的可注册根逐条对差，当场发现**一批不在表上的根**：`xiaomi.net`（米家解析/云）、
`meituan.net`、`ttlock.com`（门锁控制协议）、`cmbchina.com`、`cup.com.cn`（银联）、`goofish.com` /
`idlefish.com`（闲鱼）、`yuewen.com` / `qidian.com`（起点）、`twimg.com` / `t.co`——具体几条归
当轮那条清单记录复述（第 51 条定的口径：历史叙述不钉今天的值，现在的总数钉在
`protected roots: …` 那行机器输出上）。

漏掉的不是「能不能拦住红线」那一层——`*.meituan.net` 会被红线判定抓住，因为 `api-map.meituan.net`
在它下面。漏掉的是**这张表独有的那两种操作**，实算前后对比：

| 探针 | 改前 | 改后 |
|---|---|---|
| `[Host] meituan.net = 127.0.0.1`（apex 精确黑洞：既不等于任何红线域，也不是通配） | 接受 | 拒绝 |
| `[Host] xiaomi.net` / `ttlock.com` / `goofish.com` / `yuewen.com` 同型 | 接受 | 拒绝 |
| 默认关的 `DOMAIN-WILDCARD` glob `ttlock.*` / `qidian.*` / `mi.*`（只要求认罪，不禁止） | 允许 | 直接拒绝 |

处置不是把那批根抄进表里（抄一次就漂一次），而是**派生**：`tools/redlines.py` 的
`redline_roots()` 从红线实算可注册根，`protected_roots()` 返回「手写表 ∪ 派生根」，
`build-ads.py`、`build-apps.py`、`lint-plugins.py` 三处读取器全部换成这一个出口。
红线增删，保护面自动跟着变——与第 48 条「拆分归属应当是数据结构」、第 28 轮「同一个文件里的
第二份名单」是同一条纪律的第三次落地。lint 另加一条产物层审计：16 个插件的全部生效 `[Host]`
（含 node 构建器生成的 `soda`/`douyin`）都要过这条判据，本轮实算命中 **0** 条，
所以补保护层**没有改动任何产物**。

边界也要说清楚，免得下一轮把保护层用歪：派生只从**红线**取根，不从「这个 App 的流量里出现过这个根」
取。广告专用主域（`alimama.com`、`miaozhen.com`、`adinall.com`、`ads-twitter.com`、`qidianad.com`）
在覆盖率里同样是「品牌根」，但整族黑洞它们**正是**本仓库要做的动作，保护它们等于自废。
谁该进保护面由 App 自己的判决说话，不由流量统计说话。

### 9.12 `[MITM]` 的 hostname 名单是第四种载体——它不拦流量，它把流量变成明文（第三十一轮）

`hostname = %APPEND% acs.m.goofish.com` 这一行取消注释之后，发生的不是「拦截」，是这台主机的
TLS 被本地解密：登录态、请求体、响应体全部可读。`[Host]` 黑洞只让流量失联，`[MITM]` 名单把
流量掀开。红线说的是「这台主机绝不碰」，那掀开它显然也在「碰」的范围内——而且是最深那一层。
名单还支持通配（`p?.meituan.net`、`ads?-normal*.zijieapi.com`），所以比较必须是 glob 语义，
字符串相等会同时漏报和误报。`tools/redlines.py` 新增 `hostname_glob_regex()`（`*` 吃任意、
`?` 吃单字符）与 `mitm_reaches()`（整串匹配 + `*.` 罩子树两种形态）。

写门禁前先只读体检（第 30 轮同一课：先量清现状，别把门禁写成给今天定罪）。全部 hostname 逐项
与红线比较，命中 **4** 处：

| hostname | 所在插件 | 罩住的红线 | 状态 |
|---|---|---|---|
| `apimobile.meituan.com` | `meituan` | 美团主业务 API | 默认注释的增强层，本 App 自己声明 |
| `magev6.if.qidian.com` | `qidian` | Argus 主接口 | 同上 |
| `mage.if.qidian.com` | `qidian` | 同接口的旧版主机（本轮新补的红线） | 同上 |
| `acs.m.goofish.com` | `xianyu` | mtop 主网关 | 同上 |

固定证书那批 App（银行 / 微信 / 米家 / 京东）一条 hostname 都没有——它们的增强层根本不存在，
这正是「MITM 只对未固定 App 提供」那条判决的落地形态。`soda` 与 `douyin` 是仅有的**生效**名单，
15 项逐个与红线比较命中 **0**（`ad.zijieapi.com` 不在任何红线之下，`ads?-normal*.zijieapi.com`
这条通配也罩不到任何红线主机）。所以这轮门禁买到的仍是「以后不许漂」。

判定住在 `tests/lint-plugins.py: check_mitm_reach()`，四条：①App 插件的 hostname 不许默认生效
（整层默认注释是仓库纪律：不装证书 = 永不生效）；②罩住**别家** App 红线的 hostname 禁止——
诚实说，这一条今天和将来都近似冗余，Loon 的 hostname 是全局解密面，别家 App 的流量本来就不在
本插件里走，写这条是为了让「声明绝不碰」的主机不许出现在任何人的解密名单里，它管的是文档一致性
而不是运行时安全；③罩住**自己**红线的 hostname 只在该 App 声明了 `enhance.mitm_hosts` 时允许——
没有增强层就是「这个 App 做了证书固定 / 风控」的判决，取消注释即断 App；④`enhance.mitm_hosts`
与产物渲染出的 hostname 必须**集合相等**，源多写、产物多出一条都当场给差集。

**这轮的电池抓到了一条真缺口**：起点增强层那 8 条 `URL-REGEX` 全写作 `^https?://magev?6?\.if\.
qidian\.com/…`，`magev?6?` 意味着旧版 Argus 主机 `mage.if.qidian.com` 与 `magev6` 承载同一套接口
（hostname 名单里也确实列着它，旧客户端走旧主机）——而红线只写了 `magev6.if.qidian.com`。
于是 `[Host] mage.if.qidian.com = 127.0.0.1` 这条「黑洞旧版正文接口，起点废掉」的写法，改前同时
躲过红线判定（名单里没这个名字）和保护根判定（那一层管整族，不管精确 apex）。处置是补进
`redlines`，quote 逐字取自同一文件 `comment` 的红线声明行（第 27 轮的防伪层对新条目同样有效），
两个构建器与第 30 轮的派生根立刻同时看得见它。产物只变了 `qidian.plugin` 头部那句红线声明，
拦截规则一条没动。

第四种载体的对差不是「又打一行机器输出」：它把一条「声明绝不碰、其实一直躺在解密名单旁边」的
主机钉回了数据结构里。这正是第 24 轮那条老纪律的第六次兑现——凡是「以为能用」的判断，
都要有一个当场能算的东西替它作证。

---

### 9.13 正则面分「整主机」和「带路径」两种形状，而宣称 HTTPS 却不在解密名单里的面是假宣告（第三十二轮）

第 29 轮给规则类型建了分类表，其中 `URL-REGEX` 被判为「按 URL（含路径）匹配，不黑洞主机」，
理由是它命中靠路径形态。这句话当时是对的，但它**依赖一个没被检查的前提**：那条正则真的写了路径。
`^https?://ad\.zijieapi\.com/` 结尾只留一个斜杠，等于「这台主机的所有请求」——它不是路径面，
是**整主机面**，只是用正则写了出来。分类表管不到它，`[MITM]` 名单也不是它。于是第五种载体浮出水面：
**所有用正则表达匹配面的地方**（`[Rule]` 的 `URL-REGEX`、`[Script]` / `[Rewrite]` 的
`${url} ~= /…/` 过滤器），按形状分成两类，各归各的判定。

`tests/lint-plugins.py: check_regex_scopes()` 干的就是这件事。它把每条**生效**正则面的主机段抽出来
（按括号深度切第一个裸 `/`，所以 `(?:a|b)/path` 不会被括号里的 `\/` 骗到），把交替展开成候选，
再把正则片段折成能与 `[MITM]` hostname 通配比较的形态（`[0-9-]*`→`*`、可选点 `.?`→`.`；
不折的话 `[a-z0-9.-]+\.` 会读成 `*.?…` 这种四不像）。实算：

| 量 | 本轮值 | 含义 |
|---|---|---|
| 生效正则面 | 60 | `URL-REGEX` + Script/Rewrite 过滤器里的 `${url}` 正则 |
| 其中 HTTPS 面 | 56 | 需要解密才可能命中的那些 |
| 整主机面（无路径段） | 4 | 按域名拦截，必须过红线判定 |
| 罩在 `[MITM]` 名单外且已认罪 | 3 | 见下，逐条钉到具体正则原文 |

两条判据：

1. **整主机面必须过红线**。这 4 条（`douyin`/`soda` 各自的 `blockAdDomains` 域名族与静态层族）
   逐个与红线比较，命中 **0**——`ad.zijieapi.com`、`lianmengapi.snssdk.com`、`zlink.ugsdk.cn`
   这些都不在任何红线之下。判据把「以后有人把整主机正则写到 `magev6.if.qidian.com/` 上」这条路堵死：
   那一刻它和第 29 轮那 33 条嵌套后缀一样是域名类拦截面，必须过同一道判定。
2. **按 HTTPS 匹配却罩不住自己 `[MITM]` 名单的面，必须逐条认罪**。这抓到的是仓库里真实存在的
   三处：`douyin`/`soda` 的开屏族与观测族写作 `(?:[a-z0-9.-]+\.)?zijieapi\.com/api/ad/…`，
   想罩住穿山甲的任意分片子域，而 Loon 的 hostname 是**枚举式**的（`ads?-normal*.zijieapi.com`
   罩不到 `abc123.zijieapi.com`）。名单没写全的主机不解密、正则不命中，所以这三条面**今天就是
   静默不生效**——不是误伤，是「以为能用、其实不能用」第 10 章那一类。认罪项的键钉到
   `(插件, 段, 正则原文)` 三元组，不是钉到主机形态：把正则收窄或删掉，那条认罪立刻变成
   「今天没被任何生效面命中」而报错，例外不许预留；真要扩面时的正解是把取证到的主机补进 hostname 名单。

顺带量到一件与全局插件有关的事：ads 那 6 条生效 `URL-REGEX` **全是 `^http://`**（明文），
本来就不需要解密，所以第二条判据与它们无关——这条事实以前只在叙述里，现在由分类计数打印出来。

**电池（纯内存，合成夹具放在临时目录，红线数据仍从真实 `src/apps/*.json` 装载）**：M1 整主机正则
`^https?://magev6\.if\.qidian\.com/` → 同时报「罩住 qidian 红线」与「罩在 [MITM] 之外」；
M2 名单外的 `api.foo.com` 面 → 报；M3 把 douyin 已认罪那条正则改窄一格 → 越界照报，
且三条认罪项全部报「写旧」；M4 纯 `http://` 的 weibo 面 → 不报（判据与它无关）；
M5 IP 字面量面 → 跳过主机比较，但同夹具里那条 `^https://dns\.jd.com/` 照报红线命中。跑完
`npm run check` 全绿。

### 9.14 主机搬家：正则写对、解密名单也写了，绑定照样可以一条都不命中（第三十三轮）

第 32 轮的 `regex scopes` 只问两个问题：这条面是不是 HTTPS、它罩得住自己的 `[MITM]` 名单吗？
两个都通过，它就「可能命中」。但「可能」离「实际」还差一个前提：**正则里写的主机，App 今天还在用**。
2026-10-29 的 23 小时真机日志（Luna 21.4.0，1,538,207 行）给出了反例：

| 量 | 值 | 含义 |
|---|---:|---|
| `beta-luna.douyin.com/luna/*` 请求 | 784 | 新主机，占 luna 流量 99.6% |
| `api.qishui.com/luna/*` 请求 | 3 | 旧主机只剩非广告端点（`commerce/ecommerce/order_list`） |
| 旧版 34 条 api 单主机绑定的命中 | 0 / 784 | 整版另靠两条 beta-only task/page 绑定命中 1 条；插件在跑、开关全开、清理不到 |
| v2.8.6 双主机绑定回放命中 | 149 / 787 | 广告相关面；其余 638 条 luna 请求是 `me/`、`media-stats/` 等非广告面，故意不绑 |
| 同时命中 douyin 响应绑定的请求 | 43 / 787 | 两个插件共享 `beta-luna.douyin.com` |

这暴露的不是正则写错，而是**主机漂移**：`api.qishui.com` 仍然是合法的 luna 主机，
`[MITM]` 里也还在，所以第 32 轮的两条判据全部通过；失效发生在「正则的主机段」这层，
它既不是规则载体、也不是解密名单，之前没有任何门禁在看它。判据只有一条：
**一个 luna 绑定必须同时显式写全该 App 取证到的全部 luna 主机**，少一个就是静默失效。
`tests/lint-plugins.py: check_luna_host_parity()` 扫 `soda.plugin` 生效 `[Rewrite]`/`[Script]`
过滤器里所有含 `/luna` 的正则（条数由门禁当场打印），要求 `api.qishui.com` 与 `beta-luna.douyin.com`
两个转义后的 token 同时出现；另外单独要求两条主机都在生效 `[MITM] hostname` 里——
否则「绑定写全了也解不了密」，那是另一种假宣告。

门禁本轮真红过一次：两条 beta-only 的 `task/page` 绑定被点名，确认它们与新加宽的双主机绑定
完全重复后删除（[Script] 40 → 38 条）。保留它们不会报错，但会让同一条响应链上多一个
永远被前一条遮蔽的绑定——按第 15 章「拦了 ≠ 拦住」的口径，这种影子绑定不值得留。

**已知边界（写进文档，不写成代码）**：`beta-luna.douyin.com` 同时服务汽水和抖音，
日志里 787 条 luna 请求有 43 条同时命中两个插件的响应绑定；Loon 对同一响应只跑
**第一条命中的**响应脚本，所以两个插件都开清理时，跑哪条取决于绑定顺序，可能拿错脚本
处理另一个 App 的响应。可靠的分流条件（UA / 应用标识）在现有日志里没有取证到，
不写未经验证的 `${request.header[...]}` 条件；处置是产品层的：**同时安装时清理开关只开在一个插件里**，
写进 soda README 10.6 与 douyin README 6.3，并由 `luna host parity` 门禁保证至少不会
因为少写主机而整片失效。

### 9.15 默认值也是宣告：`[Host]` 会把 Loon 自己的加密 DNS 一起黑洞（第三十四轮）

前十四节问的都是「插件声明的能力能不能生效」；这一节问的是反方向——**一个默认生效的条目，
会不会先把用户的环境打坏**。2026-10-29 那份 23 小时真机日志（1,538,207 行）里，最大的命中类
不是任何 App 的广告请求，而是 Loon 自己的加密 DNS：

| 量 | 值 | 含义 |
|---|---:|---|
| `Host Map IP:127.0.0.1` 总数 | 28,547 | 涉及 13 个主机 |
| 其中 `dns.alidns.com` | 17,073 | 主配置 `doq-server` 的域名形式 |
| 其中 `doh.pub` | 11,239 | 主配置 `doh-server` 的域名形式 |
| 两者合计占比 | 28,312（99.2%） | 其余 11 个主机合计仅 235 次 |
| 两条上游 DoH 连接失败 | 10,389 | 5,203（alidns）+ 5,186（doh.pub），整条加密 DNS 链持续重试 |
| DoQ 建立尝试 / 失败 | 5,239 / 5,236 | 被黑洞后的 DoQ 重试 |
| `NGQUIC-CLOSE host=127.0.0.1` | 9,389 | 6,576@443 + 2,813@853，黑洞后的必然噪声 |

机制在 Loon 的 `[Host]` 语义里：它不只作用于 App 流量，也作用于 Loon 自己发起的 DoH/DoQ 解析。
主配置写域名形式 `doh-server = https://doh.pub/dns-query` / `doq-server = quic://dns.alidns.com:853`
时，这两个域名恰好也是本仓库「公共 DoH/DoT 防泄漏」组的成员——于是插件把 Loon 的解析请求
当广告流量黑洞掉，用户的系统级解析从此每秒重试。插件读不到主配置，也无法把规则限定在
「只对 App 流量生效」；在国内用户常配的域名形式加密 DNS 下，**默认全拦的防泄漏收益远小于把解析链打瘫的代价**。

处置是撤回这部分的默认值，而不是删掉能力：阿里云、DNSPod、360 的 9 条国内公共 DoH/DoT
（`dns.alidns.com`、`doh.aliyun.com`、`doh.pub`、`dns.pub`、`dot.pub`、`sm2.doh.pub`、
`doh.360.cn`、`dot.360.cn`、`dot.alidns.com`）移入新组 `doh_public_cn`，整组默认注释；
海外 48 条仍默认生效。生效 Host 1475→1466（exact 900→891，wildcard 575 不变），
默认注释 122→131、组 19→20、公共 DoH 组 57→48。开启本组的前置条件写在组注释与 README 里：
主配置的 dns/doh/doq 必须先全部改成 IP 形式，否则打开就是把日志里的故障原样复现。

门禁落在 `tests/lint-plugins.py`，是永久锁而不是一次性修复：这 9 条只要出现在生效 `exact`
集合、被任何生效 `*.` 通配捞到、缺少 `# <domain> = 127.0.0.1` 的注释形态，或
`doh_public_cn` 的 `rules` 不等于这 9 条，`npm run check` 当场失败。这样新增/删除国内入口
必须同时回答「它会不会打到 Loon 自己」，而不是只回答「它是不是公共 DoH」。

这一轮补上的判定与第 30 轮的「写了 ≠ 生效」互补：那一层问「声明的东西有没有真在跑」，
这一层问「真在跑的东西会不会伤到宿主」。**默认值本身也是一种宣告**——一条默认生效的黑洞
在说「这对所有人都安全」，当它可能打坏解析链时，诚实的做法是默认关闭、把前置条件与
取证签名一起交给用户，而不是让用户在故障里自己发现。

---

## 10. 第三轮：按文档章节全扫，抓出「以为能用、其实不能用」

前两轮是按**能力条目**扫，这一轮换成按**文档章节**扫：先把 `sitemap.xml` 里的 16 个文档页取全，
逐个和我们实际写的配置对照。结果抓到一类更危险的问题——**不是「没用到」，而是「用了一个不存在的写法」**。

### 10.1 规则参数：Loon 只有 `no-resolve`，`pre-matching` 是 Surge 的

官方 `Rule/domain_rule`、`Rule/ip_rule`、`Rule/logic_rule` 三页里，规则行尾出现的参数只有一个
`no-resolve`（且只对 IP 类规则有意义）。`pre-matching` / `extended-matching` **不在任何官方页面里**，
官方示例配置 `LoonExampleConfig` 也一条都没有。

它们来自 Surge。对照关系（社区实证）：

| Surge 参数 | Loon 的对应物 | 我们能不能用 |
|---|---|---|
| `pre-matching` | 主配置 `[General] domain-reject-mode = DNS` | ❌ 插件 `[General]` 白名单不含此项 |
| `extended-matching`（HTTPS 按 SNI 匹配） | Loon 默认开启，无需声明 | ❌ 写了没有意义 |
| `no-resolve` | 同名，仅 IP 类规则 | ✅ 已用于 `IP-CIDR` 可选组 |

**这是个真 bug，不是理论问题**：本轮之前，插件的 72 条规则里带着 `pre-matching`（41 条 `DOMAIN-WILDCARD`
+ 2 条 `DOMAIN-KEYWORD` + 4 条 `URL-REGEX` 实际生效时），构建器 `RULE_PARAMS` 还把它列进白名单，
lint 甚至**强制**每条 `DOMAIN-WILDCARD` 必须写成 `REJECT,pre-matching`。也就是说，三层工具链一起在
维护一个不存在的参数。要么被 Loon 静默忽略（写了白写），要么让整条规则解析失败（写了更糟）——两种都不该要。

已处理：

- 生成物改成 `DOMAIN-WILDCARD,<glob>,REJECT`，`RULE_PARAMS` 收缩为 `{"no-resolve"}`。
- lint 新增 `SURGE_ONLY_RULE_PARAMS`：出现 `pre-matching` / `extended-matching` 直接报错，并在消息里指向本节。
- 想要「DNS 阶段就拒绝」的正解写进 README：在主配置加 `domain-reject-mode = DNS`（插件改不到）。

### 10.2 `REJECT` 族 12 种是真的，但规则层生效有条件

`REJECT` / `REJECT-DROP` / `REJECT-NO-DROP` / `REJECT-IMG` / `REJECT-IMG-NO-DROP` / `REJECT-VIDEO` /
`REJECT-VIDEO-NO-DROP` / `REJECT-DICT` / `REJECT-DICT-NO-DROP` / `REJECT-ARRAY` / `REJECT-ARRAY-NO-DROP`
全部是合法**规则策略**（不只是 Rewrite Action）。我们用了 `REJECT`、`REJECT-DROP`、`REJECT-DICT` 三种。

官方附带说明：**规则层的 REJECT 类型只在 HTTP 或解密后的 HTTPS 中生效；其他情况除了 `REJECT-DROP`
之外直接断开连接**。这条解释了为什么 HTTPDNS 那两条用 `REJECT-DROP` 是对的——它们本来就是纯 TCP/UDP
请求，走不到「返回 200 空包」那条路。

### 10.3 `[Host]` 有四种右值，我们只用了最窄的一种

官方 `DNS/hostmap` 明确支持：

```ini
example.com = 192.168.1.20          # 固定 IP（我们在用，1200 条全是 127.0.0.1）
example.com = example.com.cn        # 域名别名
*.testflight.apple.com = server:8.8.4.4   # 指定 DNS 服务器（且左值支持 * 通配）
example.com = ip-mode:v4-only     # 指定 IP 模式
ssid:LOON's WIFI = server:system    # 按 SSID
```

两个值得记的点：

1. **左值支持 `*.` 通配**（官方示例就是 `*.testflight.apple.com`）。理论上可以把「同一父域下大批子域」
   折叠成一条 `*.foo.com = 127.0.0.1`。
2. 但官方**只给了通配 + `server:` 的组合示例**，没给通配 + 固定 IP 的示例。

所以这条**不落地**：`[Host]` 是整个插件的拦截主力（1200 条），拿一个没有官方示例的组合去改写主力层，
风险与收益不成比例。记录为待真机项：拿一条无关域名试 `*.example.org = 127.0.0.1`，确认是否解析到该 IP
（`nslookup` 即可），确认可用后再评估折叠。

### 10.4 `[General]`：插件能改的只有 9 个键

官方 `Plugin/` 页列全了插件可声明的 General 参数。这解释了为什么一堆「看起来很有用」的开关写不进插件：

| 参数 | 主配置 | 插件 | 对我们意味着 |
|---|---|---|---|
| `dns-server` / `doh-server` / `doq-server` / `doh3-server` | ✅ | ✅ | 已用前三；`doq-server` 未用（DoQ 只是第四种加密 DNS，不增加拦截力） |
| `bypass-tun` / `skip-proxy` / `real-ip` | ✅ | ✅ | 与拦截无关，不用 |
| `include-tun`（1007+） | ✅ | ✅ | 只控制进不进 TUN，不是拦截手段 |
| `ipv6-vif = off`（1007+） | ✅ | ✅ | **能改但判死**：关掉的是整个 TUN 的 IPv6，副作用远超广告范围 |
| `hijack-dns` | ✅ | ❌ | 真正能「劫持 App 自带 DNS」的开关，**插件改不到**，只能写进 README 的主配置加固 |
| `domain-reject-mode` / `dns-reject-mode` | ✅ | ❌ | 同上——`pre-matching` 的正解在这里，但插件无权声明 |
| `disable-stun` / `disable-udp-ports` / `udp-fallback-mode` | ✅ | ❌ | 同上 |
| `ip-mode` | ✅ | ❌ | 想按域设只能用 `[Host]` 的 `ip-mode:` 右值 |

结论：**「插件能做什么」的上限由 `Plugin/` 那一页决定，不由 `General/` 决定**。以后想加某个全局开关，
先确认它在不在白名单里，别写完才发现是无效行。

### 10.5 订阅规则（`sub_rule`）判死

官方支持一行挂远程列表：`https://.../xxx.list,REJECT`，规则来源优先级 **本地 > 插件 > 订阅**。

不采纳的理由不是能力问题，是可靠性：订阅列表拉取失败时没有任何本地兜底，会表现为「广告突然全回来了」，
而用户完全不知道发生了什么。现有 `[Host]` 1200 条 + `DOMAIN-WILDCARD` 41 条全部内联在插件里，
断网、换源、CDN 挂掉都不影响。**拦截规则的可用性应该跟插件本体一样可靠**。

### 10.6 `[Argument]` 只有三种控件，类型别名会静默失效

官方只定义 `input` / `select` / `switch` 三种控件，`type=` 只有 `string` / `number` / `boolean`，
并明确写着「`integer`、`float`、`bool` 等别名均不能解析」，`input/select` 也不会自动推断类型
（`input,123` 仍是字符串）。

这类错误**不会报错**，只会让参数在脚本里变成 `undefined`。所以新增 `check_argument_schema()`：
控件名、类型名、`switch` 默认值必须是 `true`/`false`、`select` 至少两个候选、`type=number` 的值必须真能转数字、
参数名不许重复。当前覆盖 25 条声明。

### 10.7 本轮落地清单

| 项 | 类型 | 说明 |
|---|---|---|
| 删除 72 条规则里的 Surge 参数 | 🐞 修 bug | `DOMAIN-WILDCARD,<glob>,REJECT`；`RULE_PARAMS` 收缩 |
| lint 新增 Surge 参数拦截 | 🛡 守卫 | `SURGE_ONLY_RULE_PARAMS`，报错指向本节 |
| lint 新增 `[Argument]` schema 校验 | 🛡 守卫 | 25 条声明的控件/类型/默认值全查 |
| `[Host]` 通配 + 固定 IP | 🟡 待真机 | 无官方示例，先在主力层之外验一条 |
| `doq-server` / `ipv6-vif` / `hijack-dns` / `sub_rule` | ❌ 判死 | 理由见 10.4 / 10.5 |

### 10.8 顺带确认的三条运行时事实

1. **规则来源优先级：本地 > 插件 > 订阅**（官方 `Rule/` 首页）。这解释了为什么用户在主配置里手写一条
   `DOMAIN-SUFFIX,xxx,DIRECT` 就能盖掉插件里的 `REJECT`——也意味着「插件里加 `FINAL`」毫无意义
   （插件 `[Rule]` 本来就不支持 `FINAL`，lint 早有守卫）。
2. **`DOMAIN-WILDCARD` 的真机性能**（官方 1008 实测，5 万条 `*`/`?`/`[...]` 混合规则、543 次查询）：
   平均 **0.031 ms**，P95 0.061 ms，P99 0.110 ms，最大 0.860 ms。这条数据把「通配层会不会拖慢启动」
   这个顾虑直接消掉了——我们只有 41 条 glob，比压测规模小三个数量级。
3. **零 MITM 下的 `REJECT` 实际行为**：官方注明「规则层 REJECT 类型只在 HTTP 或解密后的 HTTPS 生效，
   其他情况除 `REJECT-DROP` 外**直接断开连接**」。ads 插件不装证书、不解密，所以那 50 条
   `DOMAIN-WILDCARD,…,REJECT` 在真机上的表现是「连接被断开」而不是「返回 200 空包」。
   对拦截广告来说这正是想要的（快速失败，客户端不会拿到可解析的空 JSON 去重试）；
   真正需要「返回可解析空包」的场景都放在 MITM 层的 `reject_dict` 里，两者分工是清楚的。


---

## 11. 第四轮：把能力落成插件行为，而不是文档条目

前三轮都在盘点能力，这一轮只做一件事：**把已经查实的能力写进插件本体**。
四条改动全部落在生成物或脚本里，能跑测试、能被 lint 拦住。

### 11.1 压缩协商：从「事后诊断」到「事前统一」

脚本层只有 `$utils.ungzip`（gzip）。br / zstd / deflate 没有解码器，响应体会以乱码落进
「不是 JSON」分支——和「这个端点本来就没广告」长得一模一样。上一版只做到 `ce=br` 诊断，
这一版用 `[Rewrite]` 把协商改掉：

```ini
request if ${url} ~= /^https?:\/\/(?:api\.qishui\.com|…)\// then request.header.set("Accept-Encoding", "gzip")
```

- **是降级不是免压缩**：br → gzip 只多 10~20% 体积；E2 否决的是「删掉 Accept-Encoding」，
  那会让 183~191 KB 的 upsell 膨胀 5~10 倍。
- **不在条件里写 `${request.header['Accept-Encoding']} ~= /br/`**：多一个正则会让 lint 的
  `regex_literal()` 取不到 URL 正则，跨层检查直接失明。条件只留 URL，覆盖关系改由
  「降级规则必须覆盖 `[MITM]` 每个域名」这条新断言保证。
- 写这条时踩了个真错误：正则结尾 `)\/` 后漏了闭合 `/`，Loon 会解析失败——是 lint 报出来的。

### 11.2 回写 body 必须清掉过期的压缩头

`readBody()` 解压后返回明文，`$done({body})` 再把它交回去。此时原响应头的
`content-encoding: gzip` 指向的是**压缩体**，`content-length` 也是压缩后长度：

| 头 | 留着会怎样 |
|---|---|
| `content-encoding: gzip` | 客户端拿明文按 gzip 解 → JSON 解析失败 |
| `content-length: 191234` | 长度对不上 → 连接挂住或截断 |

`markHeaders(reason, bodyChanged)` 在 `bodyChanged=true` 时删掉这两个头，交给 Loon 按实际
body 重算。两种实现下都对：Loon 自己重压 → 它补头；Loon 原样转发 → 就是 identity。
只加诊断头的跳过分支**不动**这两个头——那里的 body 没变。

### 11.3 拦截回包与 `reject_dict` 对齐

`blockAdDomains` 原来回 `200 + 空 text/plain`。官方写明「`reject(200,"{}")` 返回普通文本，
需要 JSON Content-Type 时用 `reject_dict`」——两条拦截路径形状不一致。现在脚本也回
`200 + application/json + {}`，SDK 不会再把「拦截」当成「响应坏了」去重试。

### 11.4 `with debug` 接上已有开关

官方 `with` 里 `debug` 支持引用插件 Boolean 参数。43 + 14 条 `[Script]` 全挂
`debug=${debugLog}`：打开「只读日志」时同时开 Loon 原生调试输出（命中哪条、耗时、异常）。
注意 `tag` / `img_url` / `requires_body` / `binary_body_mode` **不接受变量**（文档明写），
别顺手改成动态——那会让整条规则失效。

### 11.5 新增/改写的守卫

| 守卫 | 拦什么 |
|---|---|
| `AE_SET_GZIP` 白名单 | `[Rewrite]` 里出现 `header.del` / `header.replace` 改 Accept-Encoding 直接报错 |
| 降级覆盖断言 | `[MITM]` 每个域名都必须被降级规则命中，漏一个即报错 |
| `markHeaders(...,true)` 单测 | 回写 body 时两个头必须消失；只加诊断头时必须保留 |


---

## 12. 第五轮：把「能力表」变成可执行清单，顺手抓到一处数据丢失

前四轮都是人工扫。这一轮换了个做法：**写一个脚本，让覆盖率可以被计算、被回归**。
能力表落进 `tools/loon-coverage.py` 的 `CAPABILITIES`，脚本去插件有效行与脚本源码里
探测真实写法（**注释里提到不算**），分五档输出：已用 / 可用未用 / 判死 / 不适用 / 未文档化。
后三档都不进分母；「未文档化」是第十九轮新增的——官方文档查不到、我们却在插件里带着的 token
（`%APPEND%`、`[MITM] h2 = true`），它既不算能力也不算缺口，只欠一次真机取证。

口径上做了两个决定：

1. **判死与不适用不进分母**。否则「判死得越认真，分数越低」，激励正好反了。
2. **「已用」必须是探测出来的**。所以 `docs/loon-coverage.md` 是生成物，
   `--check` 会同时校验三件事：声明的「已用」还能探测到、声明的「判死」没被用回去、
   生成的 md 没有过期。

结果：**57 已用 / 24 可用未用 / 29 判死 / 1 不适用，利用率 70.4%**（第五轮口径；第十一轮扩表后为 117 条能力，61 / 27 / 28 / 1，69.3%——见 `docs/loon-coverage.md`）。分层看：

| 层 | 利用率 | 说明 |
|---|---:|---|
| 传输层 | 100% | QUIC 回退、MITM 通配、压缩降级全用上；只剩「免压缩」是判死；`h2` / `%APPEND%` 记为**未文档化**，两边都不计（§9.3） |
| 插件段落 | 100% | 8 个段落里 7 个在用，`[IP Rewrite]` 判死 |
| 元数据 | 92% | 只剩 `#!system_version`——见下方说明，**故意不写** |
| 脚本属性 | 86% | 只剩 `binary_body_mode` |
| 参数层 | 67% | 只剩 `type=number` / `type=boolean`，本插件没有数值参数 |
| 脚本层 | 62% | 未用大多与拦截无关（`$httpClient`/`$dns.query`/AES 判死，其余无收益） |
| 规则层 | 58% | `DOMAIN`/`DOMAIN-SUFFIX` 被 `[Host]` 覆盖，`OR`/`NOT` 无场景 |
| Host 层 | 40% | 别名 / `server:` / `ip-mode:` 三种右值，对拦截都没有增益 |
| 复写层 | 33% | 31 个 Action 里 10 个判死，剩下 4 个是「能用但没必要」 |

**合计 70% 这个数字本身没有意义**。有意义的是分布：**凡是能直接提高拦截率的层，
都到了 100%；剩下的缺口全部集中在「不增加拦截力」的旁支**。这不是巧合——是因为前四轮
把「能用」和「值得用」分开判过了。

### 12.1 抓到一处真 bug：删一个键，把整个存储清空了

探测脚本把 `$persistentStore.remove` 标成「判死」，结果一跑就报漂移：
**`src/soda/reward-observe.js` 与 `src/douyin/observe.js` 里都在调它**。

回查官方 Script API 5.3：

> `$persistentStore.remove()`——清空通过脚本存储 API 保存的**全部**数据。
> 该操作不是删除当前脚本的默认 Key；只需删除一项时，应使用
> `$persistentStore.write(undefined, key)`。

也就是说 **`remove()` 不接受参数**，原来那句 `$persistentStore.remove(AD_START_KEY)`
里传的 key 被完整忽略，实际动作是「把这一侧所有脚本的持久化数据全部抹掉」。

后果不是报错，是**静默丢数据**：每量一次广告时长，就顺手清掉
`<family>-welfare-seen`（当日打卡）、`<family>-ad-stats`（广告统计）、每日提醒的已读标记。
用户看到的现象只是「状态页说今天还没打卡」，很难联想到是「量广告时长」造成的。

为什么之前没测出来：`tests/` 的脚本桩**都没有注入 `$persistentStore`**，
`typeof $persistentStore !== "undefined"` 直接为假，整条分支被跳过。测试覆盖率是 100%
的「分支没进去」——这比没测试更危险，因为它给人已经测过的错觉。

修法与守卫：

- 改成 `$persistentStore.write(undefined, AD_START_KEY)`（官方 5.1 的唯一正确写法）。
- 新增 `tests/test_store_scope.js`：带完整存储桩跑一遍「广告结束」链路，
  断言 **`welfare-seen` 与 `ad-stats` 必须还在**。只断言「开始时间键没了」是抓不到这个 bug 的。
- lint 新增 `SAFE_STORE_WIPE_RX`：再出现 `$persistentStore.remove(` 直接报错。
  守卫在**剥掉注释后**的文本上匹配——否则解释这条规则的注释本身会把自己判违规
  （第一次跑就踩到了）。

### 12.2 抓到一处静默失效：全局直连时插件等于没装

`$config.getConfig()` 的 `running_model` 有三个取值：`0` 全局直连、`1` 分流、`2` 全局代理。
状态页一直有显示，但只写「运行模式 直连」——**没人会从这四个字里读出「你装的插件一个动作都没执行」**。

全局直连下 Loon 不走规则、不进 `[MITM]`、不跑脚本，所以这个提示必须点名：

```
运行模式 直连（⚠️ 插件不生效）
⚠️ 当前是「全局直连」：Loon 不执行规则、不解密、不跑脚本，本插件所有功能都不会生效。
   改成「分流」或「全局代理」后再看。
```

`running_model` 是字符串 `"0"` 的情况也覆盖了（`Number()` 归一），测试里两条都断言了。

### 12.3 关于 `#!system_version`：能写，但故意不写

官方 `Plugin/` 页有这个键（最低系统版本，如 `15.0`）。但它是**一个值约束 `#!system` 里列的所有平台**：
ads 插件声明的是 `iOS,iPadOS,tvOS,macOS`，填 `15.0` 等于同时要求 macOS 15 与 tvOS 15——
macOS 14 用户会被这个插件直接挡在门外，而实际上它跑得好好的。

不填的语义是「全部支持」（官方原文）。**在不掌握 Loon 与各平台版本对应关系的情况下，
不填比填错安全**。这条在能力表里标 `open` 而不是 `used`，理由写在 `docs/loon-coverage.md` 里。

### 12.4 新增的守卫与产物

| 项 | 类型 | 说明 |
|---|---|---|
| `tools/loon-coverage.py` | 🛠 工具 | 能力表 → 探测 → 报表；`--check` 同时查漂移与文档过期 |
| `docs/loon-coverage.md` | 📄 生成物 | 按 9 层列出 117 条能力与判决（第十一轮起），`--write` 生成 |
| `tests/test_store_scope.js` | 🛡 测试 | 12 断言 × 2 套件，锁「删一个键不能动别的键」 |
| `SAFE_STORE_WIPE_RX` | 🛡 lint | `$persistentStore.remove(` 出现即报错，附官方条款 |
| `RUNNING_MODEL` 告警 | ✅ 功能 | 状态页点名「全局直连 = 插件不生效」 |

### 12.5 仍待真机

- **能力表里 24 条「可用未用」没有一条值得做**，这是结论不是借口：它们或是被 `[Host]`/`[Argument]` 更早覆盖，
  或是要读写与本插件无关的全局状态（节点、策略、运行模式）。下一次如果还想提利用率，
  应该先问「这条能力能不能提高拦截率」，而不是「还能不能多用一点」。
- **`$done({response: {...}})`（请求脚本直接合成响应）在官方文档里没有示例**，
  只有 Surge 时代的通行写法。`block-domains.js` 依赖它，且是 `blockAdDomains` 开关打开时唯一的拦截路径。
  如果 Loon 忽略了这层包络，表现会是「脚本跑了但广告照旧」，没有报错。
  列入真机核对项：打开 `blockAdDomains`，抓一次 `ad.zijieapi.com` 的请求，看是否返回 200 + `{}`。
- `[0-9]` 字符类语义、17/16 条 QUIC 回退的首屏耗时（沿用第三/四轮的待办）。

---

## 13. 第六轮：把分母从「功能」换成「广告类型」

§12 解决了「Loon 的功能用了多少」。但它回答不了另一个问题：**广告还剩多少。**
两者不是同一件事——功能利用率到 70% 时，仍可能有整类广告（贴片、直播挂件、Push）一条没碰。
所以第六轮换轴：分母改成「广告有多少种」。

### 13.1 分类：6 族 19 类

按「长相」分（开屏/信息流/激励）只对用户有意义，对拦截没有指导性：同一个「开屏」，
来自 SDK 的可以 DNS 一次拦死，来自自家中台的必须 MITM 剥 JSON，手段与上限完全不同。
所以用两层——**族**按广告在链路的哪一段分，**类**按用户感知的形态分：

| 族 | 类数 | 包含 |
|---|---:|---|
| 展示位 | 9 | 开屏、信息流、激励、插屏、Banner、贴片、搜索、直播挂件、推广弹窗 |
| 触达面 | 4 | Push、H5/WebView、音频、OTT |
| 数据面 | 3 | 投放配置、曝光上报、归因竞价 |
| 绕路面 | 3 | HTTPDNS、QUIC、链路劫持 |

每类再标一个**协议形态**（标准协议 / 半标准 / 私有 / 系统通道）。这一列决定能不能用 mock：
标准协议（VAST/VMAP/OpenRTB）格式确定，空清单可以直接写；私有 JSON 只能脚本。

### 13.2 覆盖率：71% 现状、42% 是零证书天花板

逐类声明「理论可达档」与「当前档」，用 `●●●●`~`○○○○` 五档表示，再从插件与脚本里探测证据。
结果：

- **现状 71%（39/55）**。到顶的是 5 类：开屏、H5/WebView、HTTPDNS、QUIC、链路劫持。
- **没有「可达」这个数了**。上一版写的 91% 是假的，见 §13.6。
- **零证书天花板 42%（23/55）**。不装 CA、不开 MITM，无论域名清单多全，都拿不到同域 JSON 的分。
  这是给「不想装证书」的人的期望管理——**DNS 层的边际收益已经见底，剩下的分必须用证书换。**
- 结构不可达 7 项：Push、DAI 音频、端上缓存素材、传感器交互、正文劫持、证书固定、素材同 CDN。
  写进 `docs/ad-type-strategy.md` 第 5 节，以后不再重复讨论。

一个反直觉的发现：**「协议越标准越好拦」是错觉。** 标准协议类的覆盖率只有 69%，
私有类反而能到 full——因为标准协议解决的是「广告怎么描述」，不解决「素材和内容同 CDN」；
而私有类一旦 MITM 进去，字段是可以删干净的。**好拦的不是协议，是域名。**

### 13.3 本轮补的三个域

按类型审计出来的空白，只有三个是「零风险、只加域名」就能补的：

| 域 | 归属 | 补的是哪一类 |
|---|---|---|
| `fwmrm.net`（+`*.v.fwmrm.net`）、`stickyadstv.com` | FreeWheel（Comcast） | 视频贴片 / CTV 的 VAST 广告决策服务器 |
| `serving-sys.com` | Sizmek（Amazon Ads） | 同上，另一家主流广告服务器 |
| `beizi.biz`、`adn-plus.com.cn` | 倍孜 | 国内第三方聚合 SDK（TopOn 之外的长尾） |

贴片类因此从「无效」提到「弱效」：能拉到的清单域已经拦死，剩下的是国内长视频
「广告接口与业务同域」——那必须 MITM 定制，投入产出比低，明确不做。

### 13.4 产物与守卫

| 项 | 类型 | 说明 |
|---|---|---|
| `tools/ad-surface-audit.py` | 🛠 工具 | 19 类 × 6 族 → 探测 → 报表；`--check` 拦三种漂移 |
| `docs/ad-type-strategy.md` | 📄 生成物 | 每类的特征、规则思路、覆盖、局限 + 六种可复制写法 |
| `npm run check:surfaces` | 🛡 门禁 | 接入 `npm run check`，与 `check:loon` 并列 |

`--check` 的三条断言：**声明做了但探不到证据**、**声明没做却探到了**、**当前档高于上限**。
这三条正好对应文档最容易犯的三种错：吹牛、过期、自相矛盾。

### 13.5 仍待真机

- `response.body.mock_file` 返回空 VAST 时，播放器是否接受 `text` 而不是 `application/xml`。
- 信息流删除 item 后，分页 `cursor` 是否仍连续（不同 App 行为不同）。
- 证书固定的 App 清单：哪些 App 在 MITM 开启后直接拒绝连接。

### 13.6 第七轮：把 90.9% 撤回

第六轮末尾算出「落地下一步可到 90.9%」。第七轮逐条核对这 11 条「下一步」时发现：
**只有 3 条是真待办，其余 8 条撞在 Loon 的机制或市场结构上，根本做不到。**

这不是算错，是**分类错**——把「还没做」和「做不了」放进同一个池子，再用一个加法算出总额，
数字当然好看。90.9% 是这么来的。

#### 三条机制边界（本轮测得，写进文档以免重犯）

| 边界 | 实测结论 | 撞上它的「下一步」 |
|---|---|---|
| `[Argument]` 的作用域 | 只作用于 `[Script]` / `[Rewrite]` 的 `enable`；**管不到 `[Host]` 与静态 `[Rule]`**（soda.plugin 第 57 行早已记录） | 把归因组做成可见开关——做不到，除非拆成独立插件 |
| `URL-REGEX` 与 HTTPS | 未 MITM 时只能看到域名，**取不到路径**；`^http://` 那几条只对明文生效 | 补 `/impression`、`/click` 路径特征到 `full`——零证书插件看不到 |
| `REJECT-DICT` 的包络 | 要返回「最小合法包络」必须改响应体，**只有 MITM 能做**；Loon 的 REJECT 系列在未解密时退化为断开 | 把投放配置的 `reject_dict` 换成带包络的空配置——零证书做不到 |

第四条不属于机制，属于成本：**私有 JSON 提档 = 多适配一个 App。**
soda/douyin 的规则表都已到各自端点的上限，再涨需要抓包读第三个 App 的 JSON。
这条最容易被误当成「写个通用引擎就能解决」——不是，字段名是 App 自己的。

#### 本轮真的落实了什么

| 域 | 为什么算真缺口 |
|---|---|
| `rayjump.com`（+`*.rayjump.com`） | 清单里原本只有品牌域 `mintegral.com`，而 Mintegral SDK 的广告请求与统计实际走 `net.rayjump.com` / `setting.rayjump.com` / `analytics.rayjump.com`——**拦了品牌域等于没拦** |
| `mtgglobals.com`、`mintegral.net` | 同一家的备用与全球域，与 rayjump 一起构成 Mintegral 的完整请求面 |

展开 `[Host]` 1295 → 1301 条（3 个域 × 2 行），版本 ads 2.4.0。

**三类仍停在 `strong`，没有升到 `full`。** 因为它们差的不是 Mintegral 这一家，而是所有
「没有公开请求域证据」的长尾聚合：AdTiming 的 SDK 端点不公开，Smaato 走 `smaato.net`（已在清单），
Ogury 走 `ogury.io`（已在清单）。补完 Mintegral 不等于补完长尾——**这一次没有把「补了一家」
写成「补完了一类」**。

#### 顺带抓到自己的一个错

第一版补域时我加了 `adtiming.com`、`smaato.com`、`ogury.com`，理由是「这三家缺」。
核实后发现三个都不是 SDK 请求域，是**官网域**：Smaato 的广告请求走 `smaato.net`、
Ogury 走 `ogury.io`、AdTiming 的端点根本没公开。加进去的结果是——**拦不到广告，还把人家的官网拦了**。

三条全删。

这个错的形状和上一轮那 8 条「下一步」一模一样：**从「公司叫什么」推出「域名是什么」**。
品牌名与请求域之间没有必然关系（Mintegral → rayjump 就是反例）。
所以现在这条也进了 `blocked`：要补只能抓包，抓不到就不补。

#### 机制：`blocked` 与 `next_to` 互斥

光把数字改小没有意义——下一个人还是会把「做不了」重新写成「下一步」。
所以给每类加 `blocked` 字段，并让 `--check` 强制它与 `next_to` 互斥：

- `next_to > 现状` → **不许**写 `blocked`（承诺了就别喊难）
- `现状 < 上限` 且停在原地 → **必须**写 `blocked`（停下了就交代为什么）

两条断言都验过会触发（删 `feed` 的 `blocked` → 退出 1；把 `feed` 的 `next_to` 提回 `strong`
但留着理由 → 退出 1），还原归零。

这条守卫的价值不在当下，在于**它让「偷偷降低预期」和「假装还能做」都编不下去**：
删掉一行 `next_to` 就能把「做不到」伪装成「没在做」，而 `blocked` 断言不允许这种沉默。

#### 现在的数字，以及怎么读它

**70.9%（39/55），待做增分 0，结构性停住 13 类。**

三个数字要一起看，单看任何一个都会误判：

- **70.9%** —— 装了证书 + 做了 2 个 App 适配。
- **42%（23/55）** —— 只用 ads 插件、零证书。**同一个仓库，两套成本，两个数。**
- **0** —— 不是「没有提升空间」，是「提升的代价从代码变成了抓包」。

第 7 节现在按「谁挡住了」分四组：这类广告自己的上限 / 成本 / Loon 的机制 / 物理不可达。
四组的共同点是**都必须写理由**，而不是留一个箭头指向未来。


---

## 14. 第八轮：写了 ≠ 生效

§12 量化「功能用了多少」，§13 量化「广告还剩多少」。两者有一个共同盲区：
**它们只数声明，不检查前提。**

一条 `USER-AGENT,httpdns*,REJECT` 写在没有 `[MITM]` 段的插件里——它在能力表上是「已用」，
在规则计数上是「+1」，但它可能一次都不会命中，因为 User-Agent 是 HTTP 请求头，
未解密的 HTTPS 里根本看不到。

### 14.1 三种前提

| 前提 | 能被谁满足 | 典型规则 |
|---|---|---|
| `none` 连接层 | 任何插件，无需证书 | 域名类、IP 类、`DEST-PORT`、`PROTOCOL`、`PROCESS-NAME` |
| `plain` 仅明文 | 明文 HTTP 流量 | `URL-REGEX` 锚定 `^http://` |
| `mitm` 需解密 | **必须有 `[MITM]`** | `USER-AGENT`、含路径的 `URL-REGEX` |

`AND` / `OR` / `NOT` 取**内部子规则里最强的那个**：一条 `AND` 里掺一个 `USER-AGENT`，
整条就需要解密。这条规则很容易漏——写的人看的是 `DOMAIN-SUFFIX`，没注意括号里还有个 UA。

### 14.2 审计结果

143 条会依赖前提的配置行（`[Rule]` / `[Script]` / `[Rewrite]`）：

- **前提满足 133 条**。soda/douyin 的脚本与复写都在 `[MITM]` 覆盖内。
- **仅明文 6 条**。ads 的 6 条 `URL-REGEX` 全部锚定 `^http://`——技术上有效、不依赖解密，
  但只吃明文 HTTP。现代 App 接口几乎全 HTTPS，所以这是一个「技术上有效、实际上罕见」的夹层。
- **存疑 4 条**。ads 的 4 条 `USER-AGENT`。

### 14.3 存疑怎么处理：登记，不删除

官方 HTTP 规则页只写了「匹配请求 Header 中的 User-Agent」，**没有写未解密时是否降级**。
所以本轮**不删这 4 条**——万一 Loon 在未解密时也有办法匹配，删了就是自己制造缺口。

但也不能继续让它们躺在「✅ 已用」里。做法是要求每条存疑规则登记 waiver，必须写清三件事：

1. **为什么保留** —— 成本为零（不解密就不会误伤任何明文流量）
2. **存疑在哪** —— ads 无 `[MITM]`，UA 是请求头，很可能命中数为 0
3. **怎么证伪** —— 临时给 ads 加 `[MITM] hostname = *`，对比加之前/之后的命中数。
   若从 0 变为 >0，即证明默认配置下不生效，届时删除或把 UA 特征并入域名层

`--check` 三条断言：**存疑必须登记**、**失效 waiver 必须清掉**、**文档不过期**。
三条都验过会触发（清空 `WAIVERS` → 退出 1；塞入不存在的 key → 退出 1；改文档 → 退出 1），还原归零。

这条与 §13.6 的 `blocked` 断言同源：**允许存疑存在，但禁止存疑沉默。**

### 14.4 三个分母

| 度量 | 分母 | 回答什么 |
|---|---|---|
| 能力利用率 | Loon 的功能 | 功能用了多少 |
| 广告面覆盖率 | 广告的类型 | 广告还剩多少 |
| **规则有效率** | 已写的规则 | **写了的有多少真会命中** |

前两个的分子都是「声明」。**声明可以被写错、被架空、被前提卡住**，所以需要第三个分母兜底。
三者不是替代关系，是层层收紧。

### 14.5 顺带确认的三件事

查这一轮的资料时顺手确认了三条官方机制，仓库此前只在注释里推测过：

- **Response URL Guard 是强制的**（3.5.1+）：每条 response 脚本的条件里必须含 `${url}` 判断，
  且必须是**必要条件**（不能用 `||` 让 URL 判断被绕过），否则整条脚本被判无效、直接跳过。
  仓库 55 条 script 绑定里 **47 条 response 绑定全部合规**（条件都是
  `${开关} == true && ${url} ~= ...` 或纯 URL，没有出现用 `||` 绕过 URL 判断的写法）。
- **「第一条命中即止」**：同一响应最多执行一条 response 脚本；`enable=false` 的规则**不占位**，
  被完全跳过。所以清理组与观测组按开关分层是正确的——但两者同开时观测组不会执行。
- **`Accept-Encoding` 降级已在用**（soda:154 / douyin:143）：请求阶段把它压成 `gzip`，
  绕开 br/zstd 无解码器的死路。这条此前只在脚本注释里，现在能对着文档确认写法合规。

---

## 15. 第九轮：拦了 ≠ 拦住（第四个分母）

前三个分母分别数「功能」「广告类型」「规则前提」，它们**都默认同一件事**：

> 广告请求会走到我们的规则面前。

这个默认不成立。广告请求有很多条路可以**绕开整个插件**——不是规则写错，
不是前提没满足，而是**路径没封死**。所以第九轮换第四个分母：**分母 = 旁路**。

### 15.1 十七条旁路，四态

`tools/bypass-audit.py` 枚举 17 条旁路，每条必须回答四件事：

| 状态 | 含义 | `--check` 的要求 |
|---|---|---|
| `sealed` 已封死 | Loon 有手段，且已落地 | 证据必须探得到；**不许**写 blocked |
| `partial` 部分封死 | 手段落地，只覆盖部分场景 | 证据必须探得到；**必须**写 blocked |
| `open` 有手段未落地 | 能做但没做 | 证据必须**探不到**；**必须**写 blocked |
| `na` 无解 | Loon 侧没有手段 | **必须**写 blocked |

**「证据探不到」对 `sealed` 是错误，对 `open` 是正确。**这套互斥关系
就是为了防止把「没做」伪装成「做了」——和 §13.6 的 `blocked`、§14 的 waiver 同源。

当前：已封死 6 / 部分封死 4 / **有手段未落地 1** / 无解 6。
封死率 54.5%，加权（partial 记 0.5）72.7%。
**最重要的一行是「有手段未落地」**——它不是做不到，是还没验证。

### 15.2 唯一未落地项：IPv6 / AAAA 旁路

`[Host]` 的 1301 条黑洞**全部只映射 IPv4**（127.0.0.1）。
如果 Loon 对命中域名仍然放行真实的 AAAA 记录，App 走 IPv6 直连就绕过了整个黑洞。

官方 `DNS/hostmap` 确实支持 `ip-mode:v4-only` 右值。但**只给了单独使用的示例**，
没有给「同一域名同时写 `= 127.0.0.1` 与 `= ip-mode:v4-only`」。

如果 Loon 一个域名只认最后一条，补 ip-mode 会把黑洞**覆盖掉**——
比不补更糟：广告全回来，而且排查方向会完全错（会以为是域名清单失效）。

所以**刻意不落地**，真机两步验证通过后才批量补：

1. **先验多行共存**：`probe.example = 127.0.0.1` 与 `probe.example = ip-mode:v4-only`
   各写一行，看 A 记录是否仍是 127.0.0.1。
2. **再验旁路是否存在**：只写 `= 127.0.0.1` 一条，查 AAAA。返回空 → 没有旁路，
   什么都不用做；返回真实 IPv6 → 旁路成立，才值得补。
3. **若多行不共存，改走规则层**：给同一域名补
   `DOMAIN-SUFFIX,probe.example,REJECT`。域名规则在解析前就命中、**不看地址族**，
   AAAA 一样被拒——这是唯一不依赖未知语义、可以直接落地的封法。

> **第十八轮的更正（重要）**：本节与 `docs/bypass-audit.md` 第 11 条此前把取值写成
> `ipv4-only` / `ipv4-preferred` / `ipv6-preferred`。官方 `DNS/hostmap` 与「通用配置」的
> `ip-mode` 值表是 `v4-only`、`dual`、`prefer-v4`、`prefer-v6`、`v6-only`——前者的写法
> 不是 Loon 的取值。**照错误值做真机探针会得到假阳性**：非法行被 Loon 忽略，
> A 记录「看起来仍是 127.0.0.1」，会让人误判「多行不共存」，而真正的原因是那行根本没生效。
> 教训：**探针的每一个字面量都必须能在官方语法里对上号，否则测的是解释器不是网络。**

这和第七轮「从品牌名推域名」是同一个教训的另一面：
**不是「看起来应该补」就补，而是先确认补了不会更糟。**

### 15.3 本轮真落地：公共解析器 IP 直连阻断

App 直连 `8.8.8.8:443` / `1.1.1.1:853` 做 DNS 时，连接层**没有域名**：

- `[Host]` 黑洞——看不到域名，无效
- `DOMAIN-KEYWORD` / `URL-REGEX`——同样无效
- `DEST-PORT,853`——只挡端口，挡不住跑在 **443 上的 DoH**

**唯一还能生效的是 `IP-CIDR`**：它只看 IP，不需要域名也不需要解密。
于是补齐 Google / Cloudflare / Quad9 / AdGuard 四家共 16 个官方 IPv4 + IPv6，
**逐条取自各服务商官方页面**（Google / Cloudflare / Quad9 / AdGuard 四页都核过原文），
不凭印象填 IP。

**默认注释**，理由写在生成的插件里：用户主配置若拿这些 IP 当 `dns-server`，
开启会掐断 Loon 自己的解析链——表现是**整网不可用**，比广告回来严重得多。
lint 新增 `check_bypass_dns_guard()` 双保险：

- 本插件自用的 5 个 DNS（`223.5.5.5` / `223.6.6.6` / `119.29.29.29` /
  `180.184.1.1` / `1.12.12.12`）一旦出现在阻断清单 → 报错
- 四家解析器的 16 个 IP 缺一个 → 报错

### 15.4 三条结论性无解

| 旁路 | 为什么封不了 |
|---|---|
| 主配置规则盖掉插件规则 | 官方 `Rule/` 写明来源优先级 **本地 > 插件 > 订阅**，插件读不到主配置 |
| `bypass-tun` | 只在主配置声明；插件声明它就是全局接管 TUN，不该由去广告插件决定网络边界 |
| 证书固定 | 官方 MitM 页只有 `hostname` / `ca-p12` / `ca-passphrase`，没有 `skip-server-cert-verify` |

这三条是写进审计、而不是硬做的。**知道封不了，也是一种封**——
它至少把「为什么这个 App 的广告拦不掉」从猜测变成了有据可查的结论。

### 15.5 四个分母

| 度量 | 分母 | 回答什么 |
|---|---|---|
| 能力利用率 | Loon 的功能 | 功能用了多少 |
| 广告面覆盖率 | 广告的类型 | 广告还剩多少 |
| 规则有效率 | 已写的规则 | 写了的有多少真会命中 |
| **路径封死率** | **绕过的路** | **拦了的是不是真拦住** |

四者层层收紧：功能用了 → 广告覆盖了 → 规则生效了 → **但请求还有别的路**。
