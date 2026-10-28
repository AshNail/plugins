# Loon 能力覆盖与利用率

> 本文由 `tools/loon-coverage.py --write` 生成，**不要手改**。
> 改能力表请改脚本里的 `CAPABILITIES`，再跑一次。

口径：**利用率 = 已用 /（已用 + 可用未用）**。
判死（❌）与不适用（—）不进分母——判死得越认真分数越低，激励就反了。
「已用」是**探测出来的**：脚本在插件有效行与脚本源码里找实际写法，注释里提到不算。

## 总览

| 层 | 已用 | 可用未用 | 判死 | 不适用 | 利用率 |
|---|---:|---:|---:|---:|---:|
| 传输层 | 5 | 0 | 1 | 0 | **100%** |
| 规则层 | 7 | 5 | 7 | 1 | **58%** |
| Host 层 | 2 | 3 | 1 | 0 | **40%** |
| 复写层 | 2 | 4 | 10 | 0 | **33%** |
| 脚本层 | 13 | 8 | 9 | 0 | **62%** |
| 脚本属性 | 6 | 1 | 0 | 0 | **86%** |
| 参数层 | 4 | 2 | 0 | 0 | **67%** |
| 插件段落 | 7 | 0 | 1 | 0 | **100%** |
| 元数据 | 12 | 1 | 0 | 0 | **92%** |
| **合计** | **58** | **24** | **29** | **1** | **71%** |

## 传输层

| 能力 | 状态 | 说明 |
|---|---|---|
| `[MITM]` 域名解密 | ✅ 已用 | 已落地 |
| `[MITM]` 通配 `*` / `?` | ✅ 已用 | Pangle 分片族用一条 `ads?-normal*.zijieapi.com` 覆盖 10 台主机 |
| QUIC→TCP 回退（`PROTOCOL,QUIC`） | ✅ 已用 | 已落地 |
| 压缩协商降到 gzip | ✅ 已用 | 脚本层只有 ungzip；br/zstd 解不开就是静默跳过 |
| `h2 = true` | ✅ 已用 | 官方 MitM 页未收录该键，按「未知键被忽略」的零成本冗余保留，不计入能力点 |
| 免压缩（删 `Accept-Encoding`） | ❌ 判死 | upsell 响应 gzip 后已 183~191 KB，去压缩会膨胀 5~10 倍 |

## 规则层

| 能力 | 状态 | 说明 |
|---|---|---|
| `DOMAIN` | 🟡 可用未用 | 被 `[Host]` 精确映射覆盖（同一批域名），规则层不需要重复一遍 |
| `DOMAIN-SUFFIX` | ✅ 已用 | ads 通配层与 app 插件（banks/qidian/x）整域 REJECT 使用；`[Host]` 的 `*.` 只映射 DNS，SUFFIX 还能表达 REJECT-DROP 等规则动作 |
| `DOMAIN-KEYWORD` | ✅ 已用 | 已落地 |
| `DOMAIN-WILDCARD`（含 `[0-9]` 字符类） | 🟡 可用未用 | 语法仅 3.5.3(1008)+ 提供且当前只在 TestFlight；App Store 正式版 3.5.2(996) 对未知规则类型的行为未文档化，ads 插件把 41 条通配/家族 glob 默认注释收录，3.5.3+ 用户取消注释即生效 |
| `URL-REGEX` | ✅ 已用 | 已写 6 条，**全部锚定 `^http://`**（HTTPDNS 配置与明文上报）。技术上有效、不依赖解密，但只吃明文 HTTP，而现代 App 接口几乎全 HTTPS，实际命中面很窄。见 `docs/rule-effectiveness.md` 第 4 节 |
| `USER-AGENT` | ✅ 已用 | 已写 4 条（`httpdns*` / `httpsdns*`）。⚠️ **前提未满足**：ads 插件**没有 `[MITM]` 段**，而 UA 是 HTTP 请求头、未解密时看不到——能否命中**未经验证**，已登记 waiver（含真机证伪方法）。见 `docs/rule-effectiveness.md` 第 3 节 |
| `IP-CIDR` / `IP-CIDR6` | 🟡 可用未用 | HTTPDNS 接入点拦截已写好但默认注释（换 IP 就失效，需要按版本人工核对） |
| `GEOIP` | ❌ 判死 | 按国家/地区分流与广告拦截无关 |
| `IP-ASN` | ❌ 判死 | 按 ASN 拦会把整个云厂商打死，广告与正常接口同 ASN |
| `SRC-IP` | ❌ 判死 | 按来源 IP 匹配，与「拦哪家广告」无关 |
| `DEST-PORT` | ✅ 已用 | 已落地 |
| `IN-PORT` | ❌ 判死 | 入站端口，插件场景用不到 |
| `PROTOCOL` | ✅ 已用 | 已落地 |
| `AND` | ✅ 已用 | 已落地 |
| `OR` | 🟡 可用未用 | `AND` 已覆盖；多个 `DOMAIN-SUFFIX` 的并集写成多条更易读，`OR` 无额外收益 |
| `NOT` | 🟡 可用未用 | 白名单式「除这些以外都拦」风险太高，没有必须用它的场景 |
| `SSID` | ❌ 判死 | 「只在某个 Wi-Fi 下拦截」不是去广告的需求 |
| `PROCESS-NAME` | ❌ 判死 | 仅 macOS 生效，iOS 直接忽略 |
| `DOMAIN-SET` / `RULE-SET` | ❌ 判死 | 远程列表拉取失败无本地兜底，表现是「广告突然全回来」且用户无感知 |
| `FINAL` | — 不适用 | 插件 `[Rule]` 不支持 `FINAL`，只能在主配置声明 |

## Host 层

| 能力 | 状态 | 说明 |
|---|---|---|
| `域名 = 固定 IP` | ✅ 已用 | 已落地 |
| `*.域名 = 固定 IP` | ✅ 已用 | 已落地 |
| `域名 = 域名别名` | 🟡 可用未用 | 别名只能换解析目标，拦不住广告；拦截要的是黑洞 IP |
| `域名 = server:8.8.8.4` | 🟡 可用未用 | 按域指定 DNS 服务器；本插件用全局 `dns-server` + `doh-server` 解决，按域再拆没有必要 |
| `域名 = ip-mode:...` | 🟡 可用未用 | 按域限制 IPv4/IPv6；全量开 `ipv6-vif=off` 副作用更大，按域做又没有明确的广告收益 |
| `ssid:名称 = ...` | ❌ 判死 | 「只在某个 Wi-Fi 下改解析」不是去广告需求 |

## 复写层

| 能力 | 状态 | 说明 |
|---|---|---|
| `url.replace` | 🟡 可用未用 | 把请求改到另一个域名＝把广告请求变成正常请求，客户端仍会拿到可解析响应；拦就拦干净 |
| `redirect(302\|307)` | ❌ 判死 | 会把客户端送去继续请求，广告位可能被填上别的素材 |
| `reject(status)` | ❌ 判死 | 官方注明返回 `text/plain`；按 JSON 解析的 SDK 会走「解析失败→重试」分支 |
| `reject_dict(status)` | ✅ 已用 | 已落地 |
| `reject_img(status)` | ❌ 判死 | 广告图走 `[Host]` 黑洞，根本到不了 MITM；这条永远命中不了 |
| `reject_array(status)` | 🟡 可用未用 | 当前命中的广告端点都回对象包络（`{data:...}`），没有顶层数组的端点 |
| `reject_video(status)` | ❌ 判死 | 同上，视频素材域名不进 MITM |
| `request.header.add/set/del/replace` | ✅ 已用 | 用 `set` 把 Accept-Encoding 降到 gzip |
| `response.header.add/set/del/replace` | 🟡 可用未用 | 响应头改写要让位给脚本（脚本自己回 `X-Soda-Plugin` 诊断头），两层同时改会互相覆盖 |
| `request.body.replace` | ❌ 判死 | 正文级正则对 JSON 不安全（可能命中字符串内部的同名字段） |
| `response.body.replace` | ❌ 判死 | 同上；且命中后同阶段脚本不再执行，等于用正则换掉全部 JSON 逻辑 |
| `request.json.*` | ❌ 判死 | 本插件不改请求体；请求侧无广告载荷需要剥 |
| `response.json.*` / `jq` / `jq_file` | ❌ 判死 | 原生 JSON 改写命中后同阶段脚本不执行：会整条废掉「保奖励」的条件判断 |
| `request.body.mock` | ❌ 判死 | 同上：改写请求体不属于本插件职责 |
| `response.body.mock` | ❌ 判死 | 包络写错＝白屏，且会把同 URL 的脚本全废掉；收益只在「省一次解码」 |
| 批量数组参数 | 🟡 可用未用 | 单条规则只有一组参数，没有「同 URL 改多个头」的需求 |

## 脚本层

| 能力 | 状态 | 说明 |
|---|---|---|
| `console.log` | ✅ 已用 | 已落地 |
| `$done` | ✅ 已用 | 已落地 |
| `setTimeout` | ❌ 判死 | HTTP 脚本必须尽快 `$done`；延迟返回会挂住连接 |
| `setInterval` | ❌ 判死 | 官方注明运行时里它只执行一次、且没有可靠的 clear，等于坏掉的 API |
| `$loon` | ✅ 已用 | 已落地 |
| `$script.name` / `startTime` | ✅ 已用 | 已落地 |
| `$argument` | ✅ 已用 | 已落地 |
| `$environment.params.nodeInfo` | ✅ 已用 | 已落地 |
| `$environment.params.policyGroup` | 🟡 可用未用 | 策略组只在「从策略入口手动运行」时才有值；插件状态按钮走 generic，拿不到 |
| `$environment.params.proxyChainInfo` | 🟡 可用未用 | 代理链信息与去广告无关，写进状态页只是噪音 |
| `$request.url` / `method` / `headers` | ✅ 已用 | 已落地 |
| `$request.body`（需 `requires_body`） | 🟡 可用未用 | 本插件只改响应；请求体里没有需要剥的广告载荷 |
| `$response.body` | ✅ 已用 | 已落地 |
| `$response.status` | 🟡 可用未用 | `[Script]` 的条件里可以用 `${response.status}`，脚本内部再判断一次是重复劳动 |
| `$request/$response.h2_trailers` | 🟡 可用未用 | gRPC 的 `grpc-status` 在 trailers 里；本插件命中的都是 JSON 端点，用 content-type 判断更直接 |
| `$persistentStore.read/write` | ✅ 已用 | 已落地 |
| `$persistentStore.remove()` | ❌ 判死 | 它会清空**全部**脚本的键，不只是当前脚本 |
| `$notification.post` | ✅ 已用 | 已落地 |
| `attach` 对象（openUrl / clipboard / mediaUrl） | ✅ 已用 | 已落地 |
| `attach.mediaUrl`（Data URI / Base64） | 🟡 可用未用 | 通知里放图要现生成 PNG，收益只是「好看」；剪贴板已经覆盖排障场景 |
| `$httpClient` | ❌ 判死 | 脚本外发数据是明确红线：拦截插件不该有任何出站请求 |
| `$dns.query` | ❌ 判死 | 同上——它会绕过 TUN 直连 DoH，等于在插件里开一条不受控通道 |
| `$utils.ungzip`（Build 988+） | ✅ 已用 | 已落地 |
| `$utils.gzip` | 🟡 可用未用 | 官方写明「改 Body 后 Loon 自己处理 Content-Encoding」，脚本再压一遍会多一次无谓运算 |
| `$crypto.aes.encrypt/decrypt` | ❌ 判死 | 没有需要解密的载荷；拿到密钥也属于破解客户端协议 |
| `$config.getConfig()` | ✅ 已用 | 已落地 |
| `$config.getSelectedPolicy` | 🟡 可用未用 | 要读的是「当前节点」，`$environment.params.nodeInfo` 已给，且不依赖策略组名字 |
| `$config.getSubPolicies` | ❌ 判死 | 异步读策略组列表；插件不管理节点，读完也没有动作可做 |
| `$config.setSelectPolicy` | ❌ 判死 | 自动切节点＝替用户改全局状态，出问题时无法归因 |
| `$config.setRunningModel` | ❌ 判死 | 同上；只读 `running_model` 做诊断，不改 |

## 脚本属性

| 能力 | 状态 | 说明 |
|---|---|---|
| `enable`（可动态） | ✅ 已用 | 已落地 |
| `tag` | ✅ 已用 | 已落地 |
| `debug`（可动态） | ✅ 已用 | 已落地 |
| `timeout` | ✅ 已用 | 已落地 |
| `requires_body` | ✅ 已用 | 已落地 |
| `binary_body_mode` | 🟡 可用未用 | 它只改变 Body 的表示形式（Uint8Array），本插件处理的都是 JSON 文本 |
| `img_url` | ✅ 已用 | 已落地 |

## 参数层

| 能力 | 状态 | 说明 |
|---|---|---|
| `switch` 控件 | ✅ 已用 | 已落地 |
| `select` 控件 | ✅ 已用 | 已落地 |
| `input` 控件 | ✅ 已用 | 已落地 |
| `type=number` | 🟡 可用未用 | 插件的可调项只有开关、二选一和 cron 表达式；cron 是字符串，不是数值 |
| `type=string` | ✅ 已用 | 已落地 |
| `type=boolean` | 🟡 可用未用 | 只有 `input` / `select` 需要声明类型，而两者都不接受 boolean；`switch` 本身就返回布尔 |

## 插件段落

| 能力 | 状态 | 说明 |
|---|---|---|
| `[General]` | ✅ 已用 | 已落地 |
| `[Rule]` | ✅ 已用 | 已落地 |
| `[Rewrite]` | ✅ 已用 | 已落地 |
| `[Script]` | ✅ 已用 | 已落地 |
| `[MITM]` | ✅ 已用 | 已落地 |
| `[Host]` | ✅ 已用 | 已落地 |
| `[Argument]` | ✅ 已用 | 已落地 |
| `[IP Rewrite]` | ❌ 判死 | 只接受精确 IPv4、不支持 CIDR／域名；广告目标 IP 随时变，逐条枚举必然漏 |

## 元数据

| 能力 | 状态 | 说明 |
|---|---|---|
| `#!name` | ✅ 已用 | 已落地 |
| `#!desc` | ✅ 已用 | 已落地 |
| `#!author` | ✅ 已用 | 已落地 |
| `#!version` | ✅ 已用 | 已落地 |
| `#!homepage` | ✅ 已用 | 已落地 |
| `#!openUrl` | ✅ 已用 | 已落地 |
| `#!icon` | ✅ 已用 | 已落地 |
| `#!system` | ✅ 已用 | 已落地 |
| `#!system_version` | 🟡 可用未用 | 一个值同时约束 `#!system` 里列的**所有**平台：ads 写了 `iOS,iPadOS,tvOS,macOS`，填 15.0 等于要求 macOS 15 / tvOS 15。不填＝全部支持，比填错安全 |
| `#!loon_version` | ✅ 已用 | 已落地 |
| `#!date` | ✅ 已用 | 已落地 |
| `#!tag` | ✅ 已用 | 已落地 |
| `#!type` | ✅ 已用 | 已落地 |

## 怎么用这份表

1. **看合计没用**。合计低是正常的：Loon 有一半能力是节点、策略、订阅管理，跟去广告无关。
2. **看每层的「可用未用」**。那是真正还没榨干的地方，每条都附了不用的理由；理由站不住就去做。
3. **看判死那列有没有 ⚠️**。出现了就是结论被推翻（代码里又用回去了），`--check` 会直接失败。

