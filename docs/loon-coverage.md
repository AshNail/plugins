# Loon 能力覆盖与利用率

> 本文由 `tools/loon-coverage.py --write` 生成，**不要手改**。
> 改能力表请改脚本里的 `CAPABILITIES`，再跑一次。

口径：**利用率 = 已用 /（已用 + 可用未用）**。
判死（❌）与不适用（—）不进分母——判死得越认真分数越低，激励就反了。
「已用」是**探测出来的**：脚本在插件有效行与脚本源码里找实际写法，注释里提到不算。

## 总览

| 层 | 已用 | 可用未用 | 判死 | 不适用 | 利用率 |
|---|---:|---:|---:|---:|---:|
| 传输层 | 6 | 0 | 3 | 0 | **100%** |
| 规则层 | 10 | 9 | 9 | 1 | **53%** |
| Host 层 | 2 | 3 | 1 | 0 | **40%** |
| 复写层 | 4 | 8 | 15 | 0 | **33%** |
| 脚本层 | 21 | 12 | 11 | 0 | **64%** |
| 脚本属性 | 6 | 1 | 0 | 0 | **86%** |
| 参数层 | 4 | 2 | 0 | 0 | **67%** |
| 插件段落 | 8 | 2 | 3 | 0 | **80%** |
| 元数据 | 12 | 1 | 1 | 0 | **92%** |
| **合计** | **73** | **38** | **43** | **1** | **66%** |

## 传输层

| 能力 | 状态 | 说明 |
|---|---|---|
| `[MITM]` 域名解密 | ✅ 已用 | 已落地 |
| `[MITM]` 通配 `*` / `?` | ✅ 已用 | Pangle 分片族用一条 `ads?-normal*.zijieapi.com` 覆盖 10 台主机 |
| `[MITM]` 排除 `-域名` | ❌ 判死 | 现有 MITM 名单是精确主机或窄通配（soda/douyin），没有需要排除的敏感兄弟域；排除语法本身可用，但当前没有场景 |
| `hostname = %APPEND%` 合并 | ✅ 已用 | 官方 MitM 页未收录该前缀，但它是社区插件通行写法：把本插件主机追加到主配置，而不是整行覆盖。soda/douyin 生效，qidian/xianyu/meituan 注释层也使用 |
| `ca-p12` / `ca-passphrase` | ❌ 判死 | 自带 CA 私钥意味着把私钥塞进公开插件，安全与可移植性双输；统一用 Loon 内置 CA |
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
| `SRC-PORT` | ❌ 判死 | 按来源端口匹配，插件场景没有可用的判断维度 |
| `no-resolve`（IP 类规则参数） | 🟡 可用未用 | 只对 IP 类规则有意义；当前 16 条 HTTPDNS 网关 IP 规则默认注释，生效项为 0 |
| `PROXY` 策略 | ❌ 判死 | 插件规则只允许 DIRECT / REJECT 族 / PROXY；去广告只做拒绝或直连，把广告流量交给代理组只会让广告正常加载 |
| `PROTOCOL,STUN` | 🟡 可用未用 | ads 可选组以注释态收录（防 WebRTC/STUN 探测），默认关；主配置 `disable-stun` 更彻底，但插件不能声明 |
| `DEST-PORT` | ✅ 已用 | 153/853 等明文 DNS 端口直接拒绝；官方还支持 `80-443` 区间与 `>=443` 比较，当前按单端口精确匹配，避免误伤业务端口 |
| `IN-PORT` | ❌ 判死 | 入站端口，插件场景用不到 |
| `PROTOCOL` | ✅ 已用 | 已落地 |
| `AND` | ✅ 已用 | 已落地 |
| `OR` | 🟡 可用未用 | `AND` 已覆盖；多个 `DOMAIN-SUFFIX` 的并集写成多条更易读，`OR` 无额外收益 |
| `NOT` | 🟡 可用未用 | 白名单式「除这些以外都拦」风险太高，没有必须用它的场景 |
| `SSID` | ❌ 判死 | 「只在某个 Wi-Fi 下拦截」不是去广告的需求 |
| `PROCESS-NAME` | ❌ 判死 | 仅 macOS 生效，iOS 直接忽略 |
| `DOMAIN-SET` / `RULE-SET` | ❌ 判死 | 远程列表拉取失败无本地兜底，表现是「广告突然全回来」且用户无感知 |
| `FINAL` | — 不适用 | 插件 `[Rule]` 不支持 `FINAL`，只能在主配置声明 |
| `REJECT`（404 + 空 body） | ✅ 已用 | 已落地 |
| `REJECT-DROP`（丢包防重试风暴） | ✅ 已用 | HTTPDNS 关键词域命中后 SDK 会对 200 空包秒级重试，丢包静默超时是从根上断重试 |
| `REJECT-DICT`（200 + `{}`） | ✅ 已用 | 上报/配置接口按 JSON 解析：返回空对象让 SDK 判定成功并清本地重试队列 |
| `REJECT-IMG`（200 + 1px GIF） | 🟡 可用未用 | meituan 可选 MITM 增强层里以注释态收录（p[0-9].meituan.net 广告图路径）——图片加载器拿到合法图像不会走「破损图→重试」，该层默认关，生效项仍为 0 |
| `REJECT-ARRAY`（200 + `[]`） | 🟡 可用未用 | 当前可引用的广告端点都回对象包络（`{data:...}`），没有顶层数组端点，无法诚实启用 |

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
| 条件 `&&` / 多条件 | ✅ 已用 | 开关参数 + URL 同时成立才拒绝（`${cleanFeedAds} == true && ${url} ~= ...`） |
| 条件引用 `[Argument]` | ✅ 已用 | 布尔开关直接进条件；String/Number 参数按声明类型比较 |
| 条件 `${request.method}` | 🟡 可用未用 | 命中的广告端点全部由 URL 唯一确定，方法维度没有额外区分价值 |
| 条件 `${request/response.header[...]}` | 🟡 可用未用 | Header 可能缺失或被网关改写，URL 条件更可靠；脚本内部已按 Content-Type 判断 |
| 条件 `${response.status}` | 🟡 可用未用 | 拒绝不依赖状态码；需要按响应内容判断时用脚本，而不是在 Rewrite 里再判一次 |
| 条件命名捕获 `as` / `${name.n}` | ❌ 判死 | 广告端点按固定路径拒绝，不需要把 URL 片段回填到 Header/Body |
| `url.replace` | 🟡 可用未用 | 把请求改到另一个域名＝把广告请求变成正常请求，客户端仍会拿到可解析响应；拦就拦干净 |
| `redirect(302\|307)` | ❌ 判死 | 会把客户端送去继续请求，广告位可能被填上别的素材 |
| `reject(status)` | ❌ 判死 | 官方注明返回 `text/plain`；按 JSON 解析的 SDK 会走「解析失败→重试」分支 |
| `reject_dict(status)` | ✅ 已用 | 已落地 |
| `reject_img(status)` | ❌ 判死 | 图片路径已由规则层 `REJECT-IMG` 覆盖（meituan 增强层）；同一请求再写一条 Rewrite 拒绝只会互相覆盖 |
| `reject_array(status)` | 🟡 可用未用 | 当前命中的广告端点都回对象包络（`{data:...}`），没有顶层数组的端点 |
| `reject_video(status)` | ❌ 判死 | 同上，视频素材域名不进 MITM |
| `request.header.add/set/del/replace` | ✅ 已用 | 用 `set` 把 Accept-Encoding 降到 gzip |
| `response.header.add/set/del/replace` | 🟡 可用未用 | 响应头改写要让位给脚本（脚本自己回 `X-Soda-Plugin` 诊断头），两层同时改会互相覆盖 |
| `request.body.replace` | ❌ 判死 | 正文级正则对 JSON 不安全（可能命中字符串内部的同名字段） |
| `response.body.replace` | ❌ 判死 | 同上；且命中后同阶段脚本不再执行，等于用正则换掉全部 JSON 逻辑 |
| `request.json.*` | ❌ 判死 | 本插件不改请求体；请求侧无广告载荷需要剥 |
| `response.json.add/delete/replace` | ❌ 判死 | soda/douyin 的响应层是字段级脚本 + 开关分支；原生 JSON 改写命中后同阶段脚本不执行，会整条废掉「保奖励」判断 |
| `response.json.jq` | 🟡 可用未用 | xianyu 可选 MITM 层以注释态落地 15 条（ddgksf2013/fmz200 同域 http-response-jq 证据）；默认不生效，生效项为 0。soda/douyin 因与响应脚本互斥不用 |
| `response.json.jq_file` | ❌ 判死 | 插件资源文件会引入包外依赖；本仓库要求自包含 |
| `request.body.mock` | ❌ 判死 | 同上：改写请求体不属于本插件职责 |
| `response.body.mock` | ❌ 判死 | 包络写错＝白屏，且会把同 URL 的脚本全废掉；收益只在「省一次解码」 |
| 多 Action 管道 `\|` | ❌ 判死 | 每条命中 URL 只需要一个动作；多动作会增加同一请求的副作用面，没有收益 |
| `reject(status, body)` 自定义 body | ❌ 判死 | 自定义 body 不如 `reject_dict` 语义清楚；按 JSON 解析的 SDK 回 `{}` 最稳 |
| `body.mock_file` / 远程文件 | ❌ 判死 | Mock 会整包替换响应，包络写错就是白屏；插件也不应依赖运行时远程拉取 |
| 批量数组参数 | 🟡 可用未用 | 单条规则只有一组参数，没有「同 URL 改多个头」的需求 |

## 脚本层

| 能力 | 状态 | 说明 |
|---|---|---|
| Request Script（`request if ...`） | ✅ 已用 | 广告域名阻断、开屏请求拦截在请求阶段执行，省掉一次出网 |
| Response Script（`response if ...`） | ✅ 已用 | 已落地 |
| Cron Script（`cron ...`） | ✅ 已用 | 每日领取提醒；插件参数可提供动态 Cron |
| Generic Script（`generic ...`） | ✅ 已用 | 插件状态自检按钮；可配合 `img_url` 显示图标 |
| Network Changed Script（`network-changed ...`） | ❌ 判死 | 广告拦截不依赖网络类型；网络切换时重跑脚本只会增加噪音，没有可执行动作 |
| `console.log` | ✅ 已用 | 已落地 |
| `$done` | ✅ 已用 | 已落地 |
| `setTimeout` | ❌ 判死 | HTTP 脚本必须尽快 `$done`；延迟返回会挂住连接 |
| `setInterval` | ❌ 判死 | 官方注明运行时里它只执行一次、且没有可靠的 clear，等于坏掉的 API |
| `$loon` | ✅ 已用 | 已落地 |
| `$script.name` / `startTime` | ✅ 已用 | 已落地 |
| `$argument` | ✅ 已用 | 已落地 |
| 脚本参数白名单 `{${a},...}` | ✅ 已用 | 每条脚本只拿自己需要的参数，避免 20+ 个开关全量注入成 `$argument` |
| 脚本条件 `&&` | 🟡 可用未用 | 脚本条件目前只按 URL 命中；开关用 `with enable=${arg}` 控制，不再在条件里重复一次 |
| 脚本条件 `${request.method}` | 🟡 可用未用 | 命中的广告端点由 URL 唯一确定，方法维度没有额外区分价值 |
| 脚本条件 `${request/response.header[...]}` | 🟡 可用未用 | Header 可能缺失或被网关改写，URL 条件更可靠；脚本内部已处理非 JSON |
| 脚本条件 `${response.status}` | 🟡 可用未用 | 脚本内部按响应内容判断即可；把状态码写进条件会让同一端点的错误分支静默漏过 |
| `$environment.params.nodeInfo` | ✅ 已用 | 已落地 |
| `$environment.params.policyGroup` | 🟡 可用未用 | 策略组只在「从策略入口手动运行」时才有值；插件状态按钮走 generic，拿不到 |
| `$environment.params.proxyChainInfo` | 🟡 可用未用 | 代理链信息与去广告无关，写进状态页只是噪音 |
| `$request.url` / `method` / `headers` | ✅ 已用 | 已落地 |
| `$request.body`（需 `requires_body`） | 🟡 可用未用 | 本插件只改响应；请求体里没有需要剥的广告载荷 |
| `$response.body` | ✅ 已用 | 已落地 |
| `$done({headers})` 改响应头 | ✅ 已用 | 回写 body 时同步补 `Content-Encoding`/诊断标记，避免过期压缩头 |
| `$done({status})` 改状态码 | ✅ 已用 | 拦截类脚本用 200 + JSON 空壳回包，避免 SDK 把非 2xx 当成失败后重试 |
| `$response.status` | 🟡 可用未用 | 脚本按 URL 与 content-type 就能判定广告响应；再叠状态码条件只会让错误分支静默漏过 |
| `$request/$response.h2_trailers` | 🟡 可用未用 | gRPC 的 `grpc-status` 在 trailers 里；本插件命中的都是 JSON 端点，用 content-type 判断更直接 |
| `$persistentStore.read/write` | ✅ 已用 | 已落地 |
| `$persistentStore.remove()` | ❌ 判死 | 它会清空**全部**脚本的键，不只是当前脚本 |
| `$persistentStore.write(undefined, key)` | ✅ 已用 | 删单个键只能这么写：`remove()` 会清空所有键；奖励计时器用完即删，避免跨次误算 |
| `$notification.post` | ✅ 已用 | 已落地 |
| `attach` 对象（openUrl / clipboard / mediaUrl） | ✅ 已用 | 已落地 |
| `attach.mediaUrl`（Data URI / Base64） | 🟡 可用未用 | 通知里放图要现生成 PNG，收益只是「好看」；剪贴板已经覆盖排障场景 |
| `$httpClient` | ❌ 判死 | 脚本外发数据是明确红线：拦截插件不该有任何出站请求 |
| `$dns.query` | ❌ 判死 | 同上——它会绕过 TUN 直连 DoH，等于在插件里开一条不受控通道 |
| `$utils.ungzip`（Build 988+） | ✅ 已用 | 已落地 |
| `$utils.gzip` | 🟡 可用未用 | 官方写明「改 Body 后 Loon 自己处理 Content-Encoding」，脚本再压一遍会多一次无谓运算 |
| `$utils.geoip` / `ipasn` / `ipaso` | ❌ 判死 | IP 地理/ASN 查询与「拦哪家广告」无关，还会给脚本引入 IP 数据库依赖 |
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
| `[General]` 的 `dns-server` / `doh-server` / `doh3-server` | ✅ 已用 | 已落地 |
| `[General]` 的 `doq-server` | 🟡 可用未用 | DoQ 要配 853 端口且很多网络直接封 UDP 853；现有 DoH/DoH3 已覆盖同三家 DNS，再加 DoQ 只增加失败面，不增加广告拦截效果 |
| `[General]` 的 `bypass-tun` / `skip-proxy` / `real-ip` | ❌ 判死 | 这些是「让流量绕过代理 / 改写解析结果」的全局路由开关，属用户主配置主权；插件替用户改会让别家规则或局域网访问静默失效，且与去广告无关 |
| `[General]` 的 `include-tun`（Build 1007+） | ❌ 判死 | 仅 Build 1007+ 且同样是全局路由开关；3.5.2(996) 不识别，写进去等于给未来埋雷 |
| `[General]` 的 `ipv6-vif`（Build 1007+） | ❌ 判死 | 同上：3.5.2 不识别，且改 IPv6 出口接口会影响整个设备的连通性，插件无权替用户决定 |
| `[IP Rewrite]` | 🟡 可用未用 | 作为广告目标 IP 的拦截手段是死路（IP 随时变）；唯一落地形态是 16 条 HTTPDNS 网关单 IPv4 以注释态收录（Build 1007+，默认关），生效项为 0 |

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
| `#!type=parser`（规则/复写片段） | ❌ 判死 | parser 型插件只补规则/复写、不能带脚本与参数面板；本项目每个插件都要带 JS 与可关开关，必须是 normal 型 |

## 怎么用这份表

1. **看合计没用**。合计低是正常的：Loon 有一半能力是节点、策略、订阅管理，跟去广告无关。
2. **看每层的「可用未用」**。那是真正还没榨干的地方，每条都附了不用的理由；理由站不住就去做。
3. **看判死那列有没有 ⚠️**。出现了就是结论被推翻（代码里又用回去了），`--check` 会直接失败。

