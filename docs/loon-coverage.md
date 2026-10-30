# Loon 能力覆盖与利用率

> 本文由 `tools/loon-coverage.py --write` 生成，**不要手改**。
> 改能力表请改脚本里的 `CAPABILITIES`，再跑一次。

口径：**利用率 = 已用 /（已用 + 可用未用）**。
判死（❌）、不适用（—）与未文档化（⚪）都不进分母——判死得越认真分数越低，激励就反了；而未文档化根本不是 Loon 的公开能力，进分子就是虚报。
「已用」是**探测出来的**：脚本在插件有效行与脚本源码里找实际写法，注释里提到不算。

**⚪ 未文档化**是第十九轮新增的一档：官方 26 个正文页里查不到、我们却在插件里带着的 token。它的存在本身就是一条待办——要么拿到真机证据证明 Loon 认它，要么把这一行从插件里删掉。它既不进分子也不进分母。「查不到」这句话第二十一轮起由 `npm run tokens` 机器复核：`--fetch` 当场记录官方正文页清单，每页命中数写进 `absent_claims`，非 0 即报「断言已被推翻」；本行也必须带 `token=` 链接指向 `tools/loon-token-audit.py` 的例外表，两边脱钩就红。

**主配置层的 0% 是插件能力分母口径**：插件不能声明 `[Proxy]`/`[Proxy Group]`/`FINAL` 等主配置段落，所以这些条目记为不适用，不代表主配置没有落地。主配置的实际基线见 `examples/loon.conf`，插件外能力台账见 `docs/loon-max-config.md`。

## 总览

| 层 | 已用 | 可用未用 | 判死 | 不适用 | 未文档化 | 利用率 |
|---|---:|---:|---:|---:|---:|---:|
| 传输层 | 4 | 0 | 3 | 0 | 2 | **100%** |
| 规则层 | 10 | 9 | 9 | 1 | 0 | **53%** |
| Host 层 | 2 | 4 | 2 | 0 | 0 | **33%** |
| 复写层 | 4 | 8 | 15 | 0 | 0 | **33%** |
| 脚本层 | 21 | 13 | 13 | 0 | 0 | **62%** |
| 脚本属性 | 6 | 1 | 0 | 0 | 0 | **86%** |
| 参数层 | 4 | 2 | 0 | 0 | 0 | **67%** |
| 插件段落 | 8 | 2 | 3 | 0 | 0 | **80%** |
| 主配置 | 0 | 0 | 2 | 9 | 0 | **0%** |
| 旧版语法 | 0 | 0 | 2 | 0 | 0 | **0%** |
| 分发 | 0 | 0 | 0 | 2 | 0 | **0%** |
| 元数据 | 10 | 1 | 1 | 0 | 2 | **91%** |
| **合计** | **69** | **40** | **50** | **12** | **4** | **63%** |

## 传输层

| 能力 | 状态 | 说明 |
|---|---|---|
| `[MITM]` 域名解密 | ✅ 已用 | 已落地 |
| `[MITM]` 通配 `*` / `?` | ✅ 已用 | Pangle 分片族用一条 `ads?-normal*.zijieapi.com` 覆盖 10 台主机 |
| `[MITM]` 排除 `-域名` | ❌ 判死 | 现有 MITM 名单是精确主机或窄通配（soda/douyin），没有需要排除的敏感兄弟域；排除语法本身可用，但当前没有场景 |
| `hostname = %APPEND% …`（官方查不到该 token） | ⚪ 未文档化 | 官方 MitM 页的参数表只有 `hostname` / `ca-p12` / `ca-passphrase` 三行，整站 26 个正文页都扫不到 `%APPEND%`（这条断言现在是机器数出来的：`tools/loon-token-audit.py` 的 `absent_claims[%append%] == 0`，命中数一变非 0 就报「断言已被推翻」）——它是 Surge 的「追加而非覆盖」写法。插件段与主配置同名键的合并语义官方同样没写（与订阅 Host Map 同一类未定义）。留着它的理由是对称的：Loon 若认识，删掉会让本插件整行覆盖用户主配置的解密名单；若不认识，它只是一个永不匹配的空主机项。**保留但不计入能力口径**；真机取证见 `docs/device-checklist.md` |
| `ca-p12` / `ca-passphrase` | ❌ 判死 | 自带 CA 私钥意味着把私钥塞进公开插件，安全与可移植性双输；统一用 Loon 内置 CA |
| QUIC→TCP 回退（`PROTOCOL,QUIC`） | ✅ 已用 | 已落地 |
| 压缩协商降到 gzip | ✅ 已用 | 脚本层只有 ungzip；br/zstd 解不开就是静默跳过 |
| `h2 = true`（官方查不到该键） | ⚪ 未文档化 | 同 `%APPEND%`：官方 MitM 参数表没有 `h2`，而官方产品页把「解密 HTTPS 与 HTTP/2」写成内置默认行为、没有开关。社区插件通行写 `h2 = true`，我们保留它当作「未知键被忽略」时的零成本保险——但保险不是能力，所以不进利用率；写成 `h2 = false` 才是真错（lint 锁死）。旧文档里那句「不计入能力点」在本轮才真正落地：此前它一直挂在「已用」上 |
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
| `域名 = ip-mode:...` | 🟡 可用未用 | 官方取值是 `v4-only`/`dual`/`prefer-v4`/`prefer-v6`/`v6-only`，其中 `v4-only` 明写「不查询 AAAA，并拒绝 IPv6 连接」——它唯一的广告相关收益是给黑洞域名补一条 v6 封口，正对 `docs/bypass-audit.md` 第 11 条 AAAA 旁路。但官方只给了 `ip-mode:` 单独使用的示例，同一域名多行（`= 127.0.0.1` + `= ip-mode:v4-only`）是否共存未文档化，因此与那条一起停在「未落地」，先做真机三步验证，不拿 1479 条生效黑洞去赌 |
| `ssid:名称 = ...` | ❌ 判死 | 「只在某个 Wi-Fi 下改解析」不是去广告需求 |
| `IP = IP` 映射 | ❌ 判死 | 官方示例是 `198.51.100.10 = 192.0.2.20` 这类固定改址；广告侧 IP 由 CDN 随时轮换，按 IP 映射等于把我们已判死的「静态 IP 枚举」换个写法再来一遍 |
| `域名 = IP, use-in-proxy=true` | 🟡 可用未用 | 官方只写「代理内继续使用映射」，没展开映射后的 IP 是给客户端还是给节点连接用；我们的黑洞域名都落在 REJECT / DIRECT 上，不经过节点，因此既无收益也无从验证——不猜测语义 |

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
| `$done({status})` 单独改状态码 | ❌ 判死 | 只翻状态码、Body 仍是原广告响应，SDK 照样解析；要改回包就整包给（嵌套 `response`），单改 status 没有可用形态。此前标「已用」是探测式写漏了 `{` 边界，把嵌套回包误算成顶层用法 |
| `$done({url})` 改请求 URL | 🟡 可用未用 | 改 URL 归复写层 `url.replace`：正则、捕获和替换范围都在配置里看得见。搬进脚本会变成「先 Rewrite 后 JS 再改一次」，排障时无法归因 |
| `$done({node})` / `$done({policy})` 改本次路由 | ❌ 判死 | 拦截插件替用户决定这条请求走哪个节点，等于把去广告和分流耦合；出问题时无法区分是谁改的路由 |
| `$response.status` | 🟡 可用未用 | 脚本按 URL 与 content-type 就能判定广告响应；再叠状态码条件只会让错误分支静默漏过 |
| `$request/$response.h2_trailers` | 🟡 可用未用 | gRPC 的 `grpc-status` 在 trailers 里；本插件命中的都是 JSON 端点，用 content-type 判断更直接 |
| `$done({response:{status,headers,body}})` 直接回包 | ✅ 已用 | Request Script 跳过上游、自己造响应。选它而不是复写层 `reject`：`reject` 只给 404、`reject(200,"{}")` 是 text/plain，广告 SDK 按 JSON 解析失败会进重试分支；脚本回包可以精确到 200 + `application/json` + `{}`，与 `reject_dict(200)` 对齐 |
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

## 主配置

| 能力 | 状态 | 说明 |
|---|---|---|
| `[General]` 的 `hijack-dns`（3.2.5+） | — 不适用 | 把指定目标的 UDP DNS 查询劫持并返回 Fake IP。插件 [General] 白名单没有此项；劫持范围（`*:53` 还是个别 IP）是主配置主权，写在文档清单里供用户自己决定 |
| `domain-reject-mode` / `dns-reject-mode` | — 不适用 | 决定域名拒绝发生在 DNS 阶段还是转发阶段、以 LoopbackIP / NoAnswer / NXDOMAIN 哪种应答拒绝；两项均不在插件 [General] 白名单内。官方还提醒 HTTP Proxy 与 TUN 下可拦到的系统 DNS 较少，所以部分请求仍会在转发阶段被拒绝——这正是插件层继续保留规则层 REJECT 的原因 |
| `ssid-trigger` / `interface-mode` | — 不适用 | 按 Wi-Fi/蜂窝切换 Loon 运行模式、指定出口网络接口，属设备级网络主权，与广告拦截无关 |
| `disable-udp-ports` / `disable-stun` / `udp-fallback-mode` | — 不适用 | 插件不可声明。STUN 拦截我们已用注释态 `PROTOCOL,STUN` 规则落地；`disable-udp-ports,443` 会连带掐掉 QUIC，`udp-fallback-mode=REJECT` 影响所有不支持 UDP 的节点业务 |
| `allow-wifi-access` / `wifi-access-*-port` | — 不适用 | 把 Loon 变成局域网代理入口：扩大监听面、与去广告无关，且端口选择属用户环境 |
| `proxy-test-url` / `internet-test-url` / `test-timeout` | — 不适用 | 节点测速与连通性探测参数；插件不管理节点，改测速地址还会影响用户其它策略组 |
| `resource-parser`（订阅解析脚本） | — 不适用 | 主配置侧的订阅解析入口。插件侧的对应能力是 `#!type=parser`（已在元数据层单列），但本仓库不出解析器插件 |
| `geoip-url` / `ipasn-url`（自定义数据库） | ❌ 判死 | 换 GeoIP/ASN 数据源会影响整机分流判定；插件既不能声明，也没有需要它的拦截逻辑（`GEOIP`/`IP-ASN` 大网段本身已判死） |
| 已弃用参数（`ipv6` / `force-http-engine-hosts` 等） | ❌ 判死 | 官方明确「仅用于识别旧配置，新配置不应继续使用」：`ipv6` 自 3.2.3(754) 由 `ip-mode` 替代、`force-http-engine-hosts` 自 3.2.3(787) 弃用、`skip-first-packet` 自 3.5.0(968) 由 Loon 自动识别。写进插件等于给升级埋雷 |
| `[Node]` / `[Proxy Group]` / `[Remote Rule]` / `[Remote Script]` | — 不适用 | 节点、策略组与远程引用是主配置段落；插件规则只能落到 DIRECT / REJECT 族 / PROXY，由用户在策略组里选，插件不替用户建组 |
| 订阅 Section 的 `[DNS]` / `[Proxy]` / Host Map 合并 | — 不适用 | 订阅文件可以整段下发 `[DNS]` / `[Host]` / `[Proxy]`，且「Host Map 加载后合并到当前 Host Map，并优先于主配置」。插件没有 `[DNS]` 段，节点与订阅也不属插件分发物——这条的真实意义是排障口径：用户订阅里的同名映射会盖掉主配置，我们的插件 [Host] 若某天不生效，先查订阅 Host Map，不要先怀疑正则 |

## 旧版语法

| 能力 | 状态 | 说明 |
|---|---|---|
| 旧版 Rewrite（`正则 header-del …` / `reject-200` / `\x20`） | ❌ 判死 | 官方定位「仅用于维护旧配置，不再扩展」。它按空格拆参数，正则含空格要写 `\x20`，类型与批量数组也无从表达；本仓库全部落在 3.5.1(978)+ 新语法，lint 禁止旧 token 出现 |
| 旧版 Script（`http-request ^regex script-path=…`） | ❌ 判死 | 3.5.1(983) 起五类脚本统一为 `<type> if <条件> then script(...) with <属性>`。旧语法仍作输入兼容但不再输出，混用会让条件变量、`with` 属性名（`img-url` vs `img_url`）分两套口径 |

## 分发

| 能力 | 状态 | 说明 |
|---|---|---|
| `loon://import?…` 与 `nsloon.com/openloon/` 通用链接 | — 不适用 | 导入入口（插件/规则/解析器/图标集），不是插件段落能力：URL 写在 README 徽章与安装链接里，自定义 Scheme 在网页里打不开时用 `https://www.nsloon.com/openloon/` 等价替换。本仓 16 个插件各自都用上了（38 条链接，其中 25 条安装链接），但探测语料只有插件文件与脚本源码，README 里的链接不属于「插件段落能力」，所以仍记 na；**生效与否由 lint 的 `check_scheme_links()` 按官方 Scheme 页语法逐条校验**（资源键 7 种、地址必须 URL 编码、`<slug>/<slug>.plugin` 自证、指向的插件文件必须存在） |
| `loon://on|off|flowmodel=|proxymode=|update?sub=all` | — 不适用 | 给快捷指令/其它 App 控制 Loon 的外部接口，插件内声明不了；脚本侧的同类能力（`$config.setRunningModel`、通知 `attach.openUrl`）已各自判死。文档里写到的 `on/off/editconfig/flowmodel=/proxymode=/update?sub=all` 六种操作同样受 `check_scheme_links()` 的官方取值表白名单约束——自造取值（如 `flowmodel=fast`）直接报错 |

## 元数据

| 能力 | 状态 | 说明 |
|---|---|---|
| `#!name` | ✅ 已用 | 已落地 |
| `#!desc` | ✅ 已用 | 已落地 |
| `#!author` | ✅ 已用 | 已落地 |
| `#!version`（官方查不到该键） | ⚪ 未文档化 | 官方 Plugin 页把插件信息字段列成一张表：`#!name`/`#!desc`/`#!author`/`#!homepage`/`#!icon`/`#!system`/`#!system_version`/`#!loon_version`/`#!date`/`#!tag`/`#!type` 共 11 个，**没有 `#!version`**；整站 grep 也只有 `system_version` / `loon_version`。它是社区插件的通行写法，Loon 大概率原样忽略（插件面板显示的版本来自 `#!date` 的「按原样显示」语义）。16 个插件都带着它：删掉最多丢一个可能根本不存在的显示项，留着也不影响解析——但它不是能力，不进利用率。取证见 `docs/device-checklist.md` |
| `#!homepage` | ✅ 已用 | 已落地 |
| `#!openUrl`（官方查不到该键） | ⚪ 未文档化 | 同上，官方 11 个 `#!` 字段里没有 `#!openUrl`；`openUrl` 只出现在 Script API 的 `$notification.post(..., attach)` 里，是另一个语法位。我们用它把插件 README 变成用户可点的入口，属于「社区约定 + 可能真的生效」——真机确认插件卡片是否会跳到该 URL，生效则升回 used，不生效则删除该行（`#!homepage` 已经在指仓库主页，功能不缺失） |
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
4. **未文档化（⚪）是有数量的债务**。每一条都必须在文档里写清「为什么还留着」，并且不被算进任何能力宣称；新增一条需要同时补真机取证步骤（`docs/device-checklist.md`）。

