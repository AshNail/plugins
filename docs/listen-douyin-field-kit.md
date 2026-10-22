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

## 4. 完成定义（DoD）

- [ ] 日志回贴 `parse-task-titles.py` 输出含 ≥1 条 ★ 条目
- [ ] 判定行给出轨道建议（.key 驱动 / 标题校正）
- [ ] `src/soda/sanitize.js` 落地对应 diff（含新 fixture + 断言）
- [ ] `npm run check`（38 套件全绿）→ 版本 `soda 2.6.1` → 发布
