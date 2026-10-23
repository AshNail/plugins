# 【听抖音】字段定位工具包（C 步回传 → v2.6.1 预案）

> 状态：**待命**。等待真机 `logTaskTitles=on` 的日志回传（`docs/device-checklist.md` §C）。
> 本文是回传那一刻的接手手册：怎么解析 → 怎么判 → 怎么改。

## 1. C 步日志长什么样

插件 `src/soda/reward-observe.js` 打印（每条福利页响应一行）：

```text
[soda-observe] treasure-task-view {"path":"/luna/treasure/task/view","tasks":[
  {"key":"douyin_listen","type":2,"title":"听抖音","show":1,"status":1,"done":false},
  {"key":"soda_music_sign_in","title":"听歌赢金币"}
]}
```

task 摘要字段（全部源字段见代码注释）：`key | id | type | reward | amount | max |
valid | show | status | done | title | action | adSnap`。
标题只在 `logTaskTitles=on` 时带出，截断 24 字。

## 2. 回传后怎么解析

```bash
pbpaste | python3 tools/parse-task-titles.py        # 从剪贴板粘贴整段 Loon 日志
pbpaste | python3 tools/parse-task-titles.py --json # 机读版
```

自动输出：任务清单、带 ★ 的「抖音」条目、key/type 词根频次、
**两种判定的自动建议**（key 驱动 or 标题校正）。

**实测样本（本仓 fixture 重放，2026-10-22）**——`node /tmp/title-log-replay.js`
用真实 `reward-observe.js` 跑测试 fixture 生成日志后喂解析器：

```text
共提取任务条目 4 条（丢弃不可解析行 0、截断行抢救 0）
  1. key=douyin_listen       title='听抖音'     ★
  2. key=sign_in             title='签到得金币'
  3. key=listen_duration     title='听歌'
  4. key=soda_music_sign_in  title='听抖音'     ★   ← view.title.plain_text 形态
含「抖音」标题条目 2 条；非插件行/异常行零误报；
判定：key 有稳定词根 → 轨道 A（标题匹配退居兜底）
```

链路（插件 → 日志 → 解析器）在设备回传前已闭环验证。

## 3. v2.6.1 预案（两条升级轨道，二选一或并用）

现状（`src/soda/sanitize.js` §236–301）：`hideDouyinTab` 深度遍历（depth 14），
只删「标题类字段含"抖音"」的数组条目，其余一概不动：

```text
titleLike = title / sub_title / subtitle / name / text / plain_text /
            desc / display_name / button_text / tab_name  （含 view.title.plain_text）
```

### 轨道 A：key 驱动（优先；当解析器判定有稳定 key/task_type）

```js
// sanitize.js 增补（示意 diff）
const DOUYIN_KEY_RE = /(?:^|_)(douyin|listen_douyin|douyin_listen)/i; // ← 按真实词根填
function isDouyinEntry(item) {
  const k = item.task_key || item.taskKey || item.key || item.task_type || item.taskType;
  if (typeof k === "string" && DOUYIN_KEY_RE.test(k)) return true;
  ... // 现有标题匹配保留为兜底
}
```

收益：标题可被服务端改文案也不受影响；匹配成本从全字段扫描降为单 key。

### 轨道 B：路径收紧（当解析器发现条目只出现在稳定容器里）

```js
// dropDouyinItems 只在命中容器键时递归数组（示意）
const DOUYIN_CONTAINER = /tabs|tab_items|task_infos|entrances?/; // ← 按真实 path 填
```

收益：改动面收窄到声明的容器，杜绝误删跨端推广条目之外的任何东西。

### 边界（不变）

- 两条轨道都**只删数组条目**；领奖/发奖字段（`amount`/`claim_status`/`incentive`）零接触；
- 默认关（`hideDouyinTab=关`），行为与 `rewardSafe` 完全可叠加；
- 不引入服务端未知字段的前瞻依赖：解析器判不出来时保持现状（宁可多删也可能漏删，
  文档里注明「等 C 步真实样本」，不猜字段）。

## 5. 循环八补充：代码侧证据（2026-10-22）

主二进制（SchubertAppStore，361MB）全字符串节复核 + `luna://` 深链解码 + 类表交叉（REA MCP 通道中断，由本地静态引擎同等完成）：

1. **任务对象零字面键**：`task_type`×28 / `task_key`×4 全域盘点无一属于 treasure 任务对象
   （前者=直播创作/商业挑战/luckydog/byteSync 域；后者=BDARV 兜底/Hybrid 资源/WordCheck 域）。
   task/page 渲染走 **Lynx 服务端模板**（`hybrid://lynxview?surl=…bytegecko.com/…` +
   `loader_name=forest`；听抖音气泡卡资源 `bubble_cards_douyin/center/template.js` 已解码到）。
2. **对双轨的裁决**：客户端**没有**可抄的"任务类型"内部键契约——UI 是服务端模板数据。因此
   Track A 的 key 驱动与 Track B 的路径递归**唯一权威都是观测样本**（`logTaskTitles` 日志），
   代码侧不提供捷径；与两条轨道「只删数组条目、判不出来就保持现状」的边界互洽。
3. **附带发现**（模块存在性证据，非可复用任务键）：`listen_douyin` = BNPlay Widget 播放路由
   枚举值；`listenDouyin` = Swift 播放源 case；`task_douyin_request_result` = tab 埋点事件
   （客户端存在显式的听抖音任务识别点）。

### 5.1 C 步样本第一报：HAR 393（2026-10-23 判读）

真机 task/page/v2 全量样本到手（`tests/fixtures/soda_task_page_v2.json`，tokens 已脱敏）：

- **合同正判**：`task.key` 仍是稳定判别字段；`task.type` 不可靠（`''` / `luna_base_task` /
  `polaris_incentive_ad_v3` 混用）。10 任务键位全量落档：`luna_rewards_ads` / `soda_music_sign_in` /
  `luna_treasure_shop` / `music_incentive_ad` / `luna_treasure_draw_duration` /
  `luna_treasure_red_packet_rain` / `luna_incentive_push_permission` / `luna_treasure_flip_card` /
  `luna_treasure_caijing_daily_cash` / `music_ug_treasure`。
- **负样本定论**：本场 **0 个抖音任务**（仅 douyinpic.com 图标 CDN 命中）——
  v2.6.1 的结构化判别（键 + type 家族 + 标题）先修广告任务与误删回归；
  抖音专属键仍待一场有抖音任务的 `logTaskTitles=开` 日志（见 §6 未勾项）。
- **v2.6.1 已落地**：合并入体 ad-task 判别，basis 见 soda README §11 v2.6.1 条目。

## 6. 完成定义（DoD）

- [ ] 日志回贴 `parse-task-titles.py` 输出**含抖音任务**（签名 ★ 条目）——393 样本为负
  （0 个抖音任务），仍需一场真实出现听抖音任务的 `logTaskTitles=开` 日志
- [ ] 判定行给出轨道建议（.key 驱动 / 标题校正）
- [x] 代码侧 diff 落地（**先行半量**，2026-10-23）：结构化判别（键/类型/标题三分量）
  已进 `src/soda/sanitize.js` 并对合并入体广告任务生效；fixture = 393 真样本；
  抖音专属 key 增量勾在抖音样本到位后（只改 `AD_TASK` 常量 + 1 个断言）
- [x] `npm run check` 全绿 → 版本 `soda 2.6.1`（本机）；发布仍待 `gh auth login`
