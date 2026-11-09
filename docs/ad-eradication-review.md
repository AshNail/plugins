# 三份外部去广告方案研判：怎么根除广告，以及本仓库的落点

> **本文是一次外部方案的研判记录，不是新的去广告白皮书。**
>
> 输入是三份外部文档（`root-ad-eradication-architecture.md`、
> `multi-type-adblocking-strategies.md`、`deep-adblocking-guide.md`），
> 它们合起来提出了一套「七维根除闭环」的完整去广告工程架构。
>
> 本文的唯一目的是回答一个问题：**这套架构里，哪些我们已经做到了、
> 哪些我们做不到、哪些它写错了、以及它指出了什么我们漏掉的东西。**
>
> 判定一律对着两样东西做，不对着「看起来应该如此」做：
> **Loon 官方文档**（nsloon.app，26 页已逐页核对）与**本仓库的机器可查证据**
> （四个审计工具 + 60 套测试 / 1942 断言）。

---

## 0. 一页结论

**三份文档的架构是对的，但它们描述的是一个「理想态」，而我们早就跑在前面了。**

| 维度 | 外部文档的贡献 | 本仓库的现状 |
|---|---|---|
| 七维闭环的**方法论** | 把去广告从「拦域名」提升为「分层治理 + 代价意识」 | ✅ 早已内化（四个分母、`blocked` 断言、waiver 登记） |
| D0 存储层消毒 | 配置层关掉预加载 | ✅ 已落地（soda/douyin `settings.js` + `sanitize.js`） |
| D1 传感器中和 | 阈值置 0 + 剥离 `shakeInfo` | ✅ 已落地，但**方向性存疑**（见 §3.2） |
| D2 协议层绝育 | QUIC 回退 / 853 / HTTPDNS | ✅ 已落地且更细（按域而非全局 QUIC） |
| D3 聚合中枢熔断 | 黑洞 GroMore / TopOn / 倍孜 | ✅ 已落地；**本轮补 3 个漏网厂商** |
| D4 分流层降维 | `127.0.0.1` 优于 `0.0.0.0` | ✅ 2130 条生效 Host 全部走 `127.0.0.1` |
| D5 载荷层外科净化 | No-Fill 伪装 + **游标保活** | ✅ 净化面已落地；**游标保活本轮才补上门禁**（见 §3.1） |
| D6 遥测反风控 | 上报回 200 空包 | ✅ 已落地（`reject_dict(200)`） |

**真正的新增量只有两条**（都是外部文档指出、我们此前承认有风险却没设防的）：

1. **分页游标完整性**——两文都把它列为硬约束，我们此前**既没有 lint 也没有测试**，
   仓库自己的 `docs/ad-type-strategy.md` 甚至写着「删多了会破分页游标」却无人设防。
   → **本轮已落地：静态门禁 + 36 项回归断言。**
2. **三个漏网的中介/验证厂商**——`yeahmobi.com`（移动广告变现 SDK）、
   `atsod.launch.liveramp.com`（LiveRamp 投放主机）、
   `confiant-integrations.net`（广告验证）。
   → **本轮已落地，附上游源数与用途证据。**

**三处必须纠正的技术错误**（照抄会出事，详见 §2）：
`extended-matching` / `pre-matching` 是 **Surge** 参数不是 Loon 的；
`[IP Rewrite]` 不存在于 Loon（那是文档自造的名字，且我们已用官方 `[Host]`/`[Rule]` 覆盖同一需求）；
全局 `PROTOCOL,QUIC,REJECT` 会打死视频与通话。

**追加工况（第十五轮）**：本文写完后按「最新标准文档」重新抓取官方 26 页正文，
**发现官方新增了一个字段 `#!source`**（下载地址校验）——
这是「按最新标准落实」的直接产物，**已落地 23 个插件 + 全部门禁**，详见 §5。

---

## 1. 三份文档的架构，与我们的对应关系

### 1.1 它们的核心主张

三份文档合起来是一套分层治理架构：

- **root-ad-eradication**：把广告定义成贯穿「本地缓存 → 物理传感器 → 私有协议 →
  聚合中枢 → 分流 → 载荷 → 遥测」的自适应对抗系统，主张**七维同时下手**才能根治。
- **multi-type-adblocking**：按**用户感知的 10 种广告形态**逐类给手段与开关设计。
- **deep-adblocking**：按**客户端实现原理的 8 种形态**逐类给攻防，并给出
  「Loon 五层防御网络」的层级图。

三份的**分类学不同**（对抗维度 / 用户形态 / 实现原理），但**结论一致**：
单一手段（只拦域名）必然漏，必须分层，且每层都有代价。

### 1.2 这套方法论，我们八轮前就有了

我们仓库的四个分母，和它们要解决的问题是同一件事：

| 我们的分母 | 外部文档对应的主张 |
|---|---|
| 能力利用率（分母 = Loon 的功能） | 「分层治理」——每层都要有手段 |
| 广告面覆盖率（分母 = 广告的类型） | multi-type 的 10 种形态 / deep-adblocking 的 8 种形态 |
| 规则有效率（分母 = 已写的规则） | 「写了不等于生效」 |
| 路径封死率（分母 = 绕过的路） | D2 协议层绝育 / 私有协议逃逸 |

而且我们比它们多走了一步：**四个分母全部带「禁止沉默」机制**
（`blocked` 断言 / waiver 登记 / 失效 waiver 抓出 / `--check` 门禁）。
三份文档都没有这一层——它们的「局限」段落是散文，不是可回归的数字。

> 这也是为什么本文不给「七维闭环覆盖率」这种漂亮数字：
> 我们已经有 19 类广告 × 6 族的广告面审计（70.9%）和 17 条旁路的封死率审计，
> 再造一个「七维覆盖率」只会多一个没有分母定义的分子。

---

## 2. 三处必须纠正的技术错误

这一节是本文最有价值的部分：**照抄这三条会直接让规则失效或伤到正常功能。**

### 2.1 `extended-matching` / `pre-matching` 是 Surge 参数，Loon 没有

`multi-type-adblocking-strategies.md` §11.2 写：

```ini
DOMAIN-KEYWORD,httpdns,REJECT-DROP,extended-matching,pre-matching
```

**这两项在 Loon 里不存在。** Loon 规则行只有 `no-resolve` 一个有官方依据的参数，
且只对 IP 类规则有意义。写上去要么被静默忽略（写了白写），
要么让整条规则解析失败（写了更糟）。

我们仓库在**第三轮**就踩过并修掉了这件事，并且专门加了门禁
（`tests/lint-plugins.py` 的 `SURGE_ONLY_RULE_PARAMS`）拦截回归。
`src/ads/domains.json` 的 `[Rule]` 段至今留着这段说明：

```
# 规则行不带参数：Loon 规则只有 `no-resolve` 一个有文档依据的参数（IP 类用），
# Surge 的 `pre-matching` / `extended-matching` 在 Loon 里没有对应写法——
```

**文档给的「正解」在这个仓库是历史踩坑记录。**

### 2.2 `[IP Rewrite]` 不是 Loon 的段落名

`deep-adblocking-guide.md` §4.4 反复用 `[IP Rewrite]` 这个名字，
说它是「Build 1007+ 独占的语法」，收录 16 条 HTTPDNS 单 IPv4 `drop`。

**Loon 官方插件文档里确实有一个类似的东西，但名字不叫这个**——官方叫
`[IP Rewrite]`，且**只允许在插件里声明**，动作是 `reflect` / `reject` / `drop`。
（这一点它说对了。）

问题在**它把这一层当成「最快最彻底」的必选项**，而我们查完官方文档后的结论相反：

- 官方明确写「只接受单个 IPv4，不接受 CIDR 网段、域名或 IPv6」；
- HTTPDNS 的接入点 IP **随时会变**——逐条枚举必漏，漏的那条就是真漏；
- 它命中后**直接丢弃，不再进入规则匹配、策略、Rewrite、脚本或 MitM**，
  也就是**连 HTTPS 请求都到不了**。

我们把它做成了 **16 条默认注释的可选段**，而不是「最快最彻底」的默认层。
理由写在 `docs/loon-native-first.md` §9.1：这是「用户该自己决定」的可选项，
不是插件能替用户做的决定。同样的需求我们用 `[Host]`（域名层）+ `REJECT-DROP`
（规则层）两道覆盖，**不依赖会漂的 IP 清单**。

### 2.3 全局 `PROTOCOL,QUIC,REJECT` 会打死视频与通话

`root-ad-eradication-architecture.md` §维度 2 写：

> 全局配置 `PROTOCOL,QUIC,REJECT` 或在增强插件中针对广告域声明
> `AND,((DOMAIN-SUFFIX,xxx),(PROTOCOL,QUIC)),REJECT`

**前半句不能开。** 全局拒绝 QUIC 会把视频播放、语音通话、实时游戏一起打掉——
这些应用大量依赖 HTTP/3。本仓库在 soda/douyin 里**只做后半句**：
按精确域（18 个 / 16 个）声明 `AND,((DOMAIN-SUFFIX,x),(PROTOCOL,QUIC)),REJECT`，
理由写在 `plugins/soda/soda.plugin` 第 113 行：

```
# 为什么不做全局 PROTOCOL,QUIC,REJECT：那会连视频/通话/直播一起打掉。
```

`docs/bypass-audit.md` 第 5 条把这一层判为**已封死**，
并且写明「不做全局 `PROTOCOL,QUIC,REJECT`」——**外部文档的「全局」方案是本仓库明确拒绝的**。

### 2.4 附带纠正两处细节

| 外部文档写法 | 实际 | 依据 |
|---|---|---|
| `[Rewrite]` 里 `reject(200)` | `reject(200)` 返回**空 body**；要 JSON `{}` 得用 `reject_dict(200)` | 官方 Rewrite 页动作表 |
| `response.body.mock_file("text", ...)` 配 `application/xml` | mock 的 content-type 白名单里**没有** `application/xml`，只有 `text` | 官方 Rewrite 页 Mock 段 |

第二行我们的 `docs/ad-type-strategy.md` 已经记着（「mock 不支持 `application/xml`」），
是外部文档沿用了同一说法，不算错，只是没写全。

---

## 3. 两条真正的增量：外部文档指出了我们的漏洞

### 3.1 分页游标完整性——本轮落地

**外部文档的主张**（两文都列为硬约束）：

> 从信息流数组中剔除广告卡片时，**严禁修改或丢弃 `min_cursor`、`max_cursor`、
> `has_more`、`page_token`**；否则前端滑动到底部时因找不到游标令牌而陷入
> 「死锁无法继续刷新」的故障。

**我们此前的状态**：**零防护**。

- `src/` 与 `tests/` 里 `cursor` / `has_more` / `page_token` **一个都没有**；
- 我们自己的 `docs/ad-type-strategy.md` 第 101 行写着
  「删多了会破分页游标（`cursor`/`has_more` 与广告数耦合）」，
  第 490 行把它列为「需真机取证」——**但承认了风险，却没有一道门禁**。

也就是说：我们的 `kill` / `falsy` / `prune` 三张键表里，
**任何人只要写进一个 `cursor` 字段名，净化脚本就会把游标清空**，
而没有任何 lint 或测试会拦住。这正是我们仓库纪律里说的
「把『做不到 / 存疑』写成散文，而不是可回归的数字」。

**本轮落地两层**：

1. **静态门禁**（`tests/lint-plugins.py` → `check_pagination_integrity`）
   ——扫 `src/soda/sanitize.js` 与 `src/douyin/clean.js` 的三张键表，
   键名归一化（小写 + 去 `_`/`-`）后与 25 个分页字段名比对，
   命中即报错。当前实测：**266 个键，0 命中**。

2. **回归套件**（`tests/test_pagination_integrity.js`）
   ——14 个分页字段 × 3 种书写（`min_cursor` / `minCursor` / `min-cursor`），
   断言净化前后**值与类型原样保留**，同时断言**广告条目仍然被摘掉**
   （防「为了保游标连广告也不摘」这种假修法）。实测：**36 项断言全过**。

**两道门禁都做过证伪**（故意破坏 → 必须失败 → 还原）：

| 变异 | 期望 | 实测 |
|---|---|---|
| 把 `min_cursor` 塞进 `kill` 表 | lint 报错 | ✅ 报出「分页字段 'min_cursor' 出现在净化键表里」 |
| 同时塞 `min_cursor` + `has_more` | 回归套件失败 | ✅ 6 项断言转红 |

**仍然存疑、只能真机取证的部分**：「删掉条目后游标是否仍然连续」是 App 侧语义
（有些 App 的游标与条目数耦合），静态证明不了。已写进
`docs/device-checklist.md` 的 H 段：滑到列表末尾确认能加载下一批。

### 3.2 摇一摇阈值置 0 的方向性——外部文档的两种说法自相矛盾

`root-ad-eradication-architecture.md` §维度 1 对阈值给了**两个互相矛盾的方案**：

> 将 `shake_sensitivity`、`shake_threshold`、`motion_threshold`、`twist_angle`
> 篡改为不可达极大值（如 `99999`）**或直接置 `0`**

`multi-type-adblocking-strategies.md` §3.1 则只给一种：

> `splash_shake_sensitivity: 0`、`splash_acceleration_threshold: 0`

**我们仓库照的是「置 0」这一路**（`src/soda/settings.js` 的 `SCALAR_KEYS`），
理由是「阈值越小越难触发」。

**但这里有个我们此前没写下来的存疑**：这三个键的**语义方向没有官方文档可查**。
如果 SDK 按「运动量 ≥ 阈值即触发」比较，**置 0 反而变成「任何轻微晃动都触发」**——
比不改更糟。三份文档里 `99999` 那个方案在这一点上更稳
（无论朝哪个方向比都不可达），而 `multi-type` 只给 `0` 是不完整的。

**本轮处置**：**不改代码**。理由是——

- 改动的方向依赖对 SDK 内部实现的猜测，而我们的纪律明确
  「任何域名、IP、参数都要有官方页面或抓包证据」；
- 我们已有的更可靠一手手段是**开关置 false**
  （`enable_splash_shake` / `enable_twist_ad` / `enable_motion_ad`
  在 `settings.js` 里已置 false）——**开关关掉比改阈值可靠**，
  且不受阈值语义方向影响。

**改为登记为真机取证项**（`docs/device-checklist.md` H 段）：
开 `settingsClean` 后真的晃一下手机，看是否仍跳电商。
若仍跳，说明键语义与假设相反，此时改走开关那一路。

> 这一条的处理方式本身就是三份文档缺的那一层：**允许「存疑」存在，但禁止沉默。**
> 文档给的两种方案我们都没盲从，而是写下「为什么现在不改」和「怎么证伪」。

### 3.3 三个漏网的中介/验证厂商——本轮落地

外部文档的 D3 主张「击穿聚合中枢」，列举的 GroMore（`toblog.ctobsnssdk.com`）、
TopOn（`selecttopon.com` / `toponad.com`）、倍孜（`beizi.biz`）
**我们早已收录**（`mobile_sdks` 组 + `cn_union` 组）。

但按上游清单逐个反查，**还有三个当时没收的**：

| 域 | 归属组 | 上游源数 | 用途证据 |
|---|---|---:|---|
| `=yeahmobi.com` | `mobile_sdks` | 2（AdGuard-DNS / HaGeZi PRO） | 官方自述 Data Driven Mobile Advertising；Kochava Media Index 收录为 Mobile Display Platform，Requires SDK Integration=Yes |
| `=atsod.launch.liveramp.com` | `adtech` | 2（同上） | LiveRamp 程序化投放侧的 ATS 投放主机 |
| `=confiant-integrations.net` | `adtech` | 7 | 官方自述 Ad Security & Quality Platform，integrations 主机承载创意扫描 JS 与预检 API |

**两条自我约束**（写进 note，不只是写进列表）：

1. **只封 `confiant-integrations.net` 自有域，不封
   `confiant-integrations.global.ssl.fastly.net`**——后者是 Fastly 共享基础设施，
   封它等于封共享 CDN。我们仓库的 `protected-roots` 纪律在这条上直接生效。
2. **只封 LiveRamp 的投放主机，不碰 `liveramp.com` 主域**——它的数据/受众业务与广告共用主域。

### 3.4 一个被拒绝的候选：Branch.io

反查时发现 `branch.io` 有 **6 个上游源**（比 Yeahmobi 的 2 源还多），
按「源数」口径本该收。但我们仓库在更早一轮就明确写过
**「branch.io 是深度链接基础设施，明确不拦」**。

**本轮推翻这个决定吗？没有。** 理由写在 `src/ads/review-queue.json`：
Branch 同时承载深链跳转与归因回调，**主域整封会同时断掉 App 自身的分享落地功能**——
那是功能损坏，不是少看广告。上游清单按「tracker」语义收录它，
与本仓库判断的「广告请求域」语义不是一回事。

> **源数多不等于该收。** 这正是我们仓库
> `src/ads/categories.json` 里 `shared_root_is_ad_evidence: false` 那条策略的现实版本：
> 判定依据是**该域是否承载 App 自身功能**，不是清单里出现了几次。
> 本轮把 Branch 登记进 `review-queue.json`（`defer-no-runtime-change`），
> 并写清解封需要什么证据——而不是静默加进清单或静默丢掉。

---

## 4. 外部文档没提、但我们必须知道的边界

外部文档的「七维闭环」读起来像能根治，但有三类东西**在网络层之外**：

| 外部文档的维度 | 我们的判定 | 依据 |
|---|---|---|
| D0 存储层消毒「双冷启自洁」 | **做不到** | 端上缓存的生命周期由 SDK 内部线程管，网络层碰不到。`docs/bypass-audit.md` 第 16 条判为 `na`（无解） |
| D1 传感器「物理绝育」 | **只能改配置，改不了传感器** | 文档说「SDK 检测不到交互配置就不会调用 `startAccelerometerUpdates`」——这是**推断**，无官方文档佐证，已登记为真机取证项（§3.2） |
| D6 遥测「欺骗反风控」 | **不做** | 我们只做「回 200 + 空包让 SDK 主动清本地重试队列」，**不伪造曝光/点击成功**。伪造上报属于广告欺诈，红线不碰 |

第三条值得展开：外部文档的 D6 写「上报伪造 200 成功，欺骗 SDK 正常结束生命周期」。
我们的做法在**效果上接近**（SDK 以为上报成功、不再重试），
但**边界不同**——我们截断的是 SDK 到广告平台的**回传请求**，
不伪造任何「广告已展示」的信号给广告平台。后者是广告欺诈，本仓库红线不碰。

---

## 5. 追加：官方文档本轮新增了一个能力（第十五轮）

写完本文后按「最新标准文档」重新抓取官方 26 页正文，**词表快照多出 85 个 token**，
逐段比对后确认：**不是措辞变动，是官方新增了一个字段 `#!source`**。

### 5.1 它是什么

> `#!source` —— 插件作者指定下载地址的 SHA-256；多个值使用英文逗号分隔，任意一个匹配即可。
> Loon 通过网络首次安装插件时，会对用户实际填写并保存的完整 URL 字符串计算 SHA-256，
> 并与该字段比较。

官方算例的**两个哈希已用本仓库实现逐字复现**（`tools/source_hash.py` 的 `self_check()` 固化）。

**最容易误解的一点**：它校验的是 **URL 本身**，不是插件文件的内容哈希。
官方自己写明：「不是数字签名，不能单独证明插件作者身份或插件内容未被修改」。

### 5.2 落地：23 个插件全部带上，哈希一律现算

| 项 | 做法 |
|---|---|
| 哈希来源 | `tools/source_hash.py` —— **唯一出口**，两个构建器现算现写，**不接受手抄** |
| 覆盖 | ads + 19 个 App + soda/douyin/netease = 23 个插件 |
| 例外 | `qidian-pro`（第三方逐字移植件，上游作者 3kaiu）—— 替上游表态，**故意不写** |
| 门禁 | `check_source_hash()` 逐个反向复算比对，三种失败形态分别报出 |
| 证伪 | 错哈希 / 删行 / 例外插件擅自声明 —— **三条都做过证伪**，全部还原后 0 problem |

### 5.3 为什么这道门禁不是多余的

官方明写「**Loon 不使用 HTTP 重定向后的地址进行比较**」，
校验对象就是**用户填的那条 URL 字符串**。而 GitHub raw 的内容每个 commit 都变——
若有人改了地址（换分支、换文件名、改成镜像域名）而哈希没跟着变，
那行哈希就成了一句**假话**：它声称「我来自这个地址」，实际校验的却是另一个。

**不写只是「没校验」，写错是「假校验」，后者更危险。**

### 5.4 仍然存疑的部分（只登记，不假装）

- **官方没写校验不匹配时的行为**——是拒绝安装、还是仅提示？三种可能对应的处置完全不同。
- **生态里 0 个真实插件在用**这个字段（官方 Gallery、QX-Loon 等主流仓库实测均无），没有先例。
- 生态证据也说明了一件要紧事：**主流插件作者都没用它**，
  说明这个字段要么价值有限，要么代价（镜像用户会被拦）大于收益。

所以本轮的处置是：**落地 + 全部门禁 + 把未知行为登记成真机取证项**，
而不是「官方有我们就上」也不是「官方有我们就跳过」。

---

## 6. 本轮改动清单（可回归）

| 文件 | 改动 | 门禁 |
|---|---|---|
| `src/ads/domains.json` | +3 个域（yeahmobi / liveramp ATS / confiant），各带源数与用途证据 | `build-ads.py` + 红线/保护根判定 |
| `src/ads/review-queue.json` | +1 个 defer 候选（Branch.io），写清解封条件 | 人工复核入口 |
| `tests/lint-plugins.py` | +`check_pagination_integrity`：266 键扫 25 个分页字段名 | 已证伪（注入 `min_cursor` → 报错） |
| `tests/test_pagination_integrity.js` | 新套件：36 项断言（14 字段 × 3 写法 + 反向断言） | 已证伪（注入 → 6 项转红） |
| `tests/run-all.py` | 注册新套件 | 套件总数 58 → 60 |
| `docs/device-checklist.md` | +2 条真机取证项（阈值方向性 / 分页连续性） | 人工执行 |
| `plugins/ads/README.md`、`docs/loon-native-first.md`、`docs/bypass-audit.md` | 规模数字随域数同步 | `readme numbers` 门禁（25 条声明） |
| `tools/source_hash.py`（新） | `#!source` 的唯一出口：按真实下载 URL 现算 SHA-256，官方两个算例固化为自检 | 自检 + lint 反向复算 |
| `tools/build-ads.py`、`tools/build-apps.py` | 生成物现写 `#!source`（不手抄哈希） | 构建即生成，产物与源一致 |
| `plugins/soda/soda.plugin`、`plugins/douyin/douyin.plugin`、`plugins/netease/netease.plugin` | 手写插件补上 `#!source` | `check_source_hash()` |
| `tests/lint-plugins.py` | +`check_source_hash`：逐插件反向复算比对 | 已证伪（错哈希 / 缺行 / 例外插件擅自声明，三条） |
| `src/loon-docs/tokens.json` | 按最新官方正文刷新（3709 token，+85） | `check:tokens` 门禁 |
| `tools/loon-coverage.py` | 能力表 +`#!source` 一行（175 → 176 条） | `check:loon` 门禁 |
| `docs/device-checklist.md` | +1 条真机取证项（`#!source` 不匹配时的实际行为） | 人工执行 |

**门禁现状**：`npm test` **60 套件 / 1942 断言全过**；
`npm run check` 的下游阶段里除 `check:icons` 外**全部全绿**
（`check:tokens` / `check:loon` / `check:surfaces` /
`check:effective` / `check:bypass` / `check:apps` / `check:app-readmes` /
`check:app-coverage`）。

**两处未绿都与本轮无关，在改动前的 `HEAD` 上同样存在**（`git stash` 对照实测）：

- **8 条 `qidian-pro` lint 错误**——`qidian-pro` 是**逐字保留的移植件**（不重写），
  本轮未触碰；
- **2 处图标漂移**（`x` / `youtube`）——`check:icons` 每次都向 Apple iTunes Lookup
  现取 artwork，而 Apple CDN 路径里的 `<hash>` 段随构建产物重分配，
  旧串会被回收。该项依赖网络，**不是本轮改动引起的**。

---

## 7. 怎么读这三份文档（以及怎么读本文）

1. **架构可以借，参数不能抄。** 它们给的分层方法论是对的；
   但 `extended-matching`、`[IP Rewrite]` 的定位、全局 QUIC 这三处，
   照抄会失效或伤功能。**任何规则参数都要对着官方文档核。**
2. **看它没说「怎么证伪」的地方。** 三份文档的「局限」段落都是散文。
   我们对应位置的产物是 `--check` 门禁 + waiver 登记表 + 真机取证项。
3. **「置 0」这类看似显然的动作，要问方向。** 阈值置 0 在两个方向上是相反的意思，
   而外部文档自己给了两个互相矛盾的方案（§3.2）。
4. **域名的「源数」不是判据，「该域是否承载 App 自身功能」才是。**
   Branch.io 有 6 个源，本仓库仍然不收（§3.4）。
5. **本文的每个数字都可以重算**：`npm run check` 会把域数、套件数、
   断言数、门禁声明数当场算一遍；本文引用的数字若与机器不一致，
   门禁会失败（`readme numbers` 那几道）。

---

## 附：本文引用的机器出口

| 数字 | 来源命令 |
|---|---|
| 2130 条生效 Host（exact 1349 / wildcard 781） | `npm run build:ads -- --stats-json` |
| 19 类广告面覆盖 70.9%（39/55），13 类结构性停住 | `npm run surfaces` |
| 17 条旁路，封死率 54.5% / 加权 72.7% | `npm run bypass` |
| 60 套件 / 1942 断言 | `npm test` |
| 266 个净化键 / 0 个分页字段命中 | `npm run lint` 的 `pagination integrity` 行 |
| 25 条 ads README 规模声明 | `npm run lint` 的 `readme numbers` 行 |
