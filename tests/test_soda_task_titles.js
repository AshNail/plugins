const load = require("./load-script");
const code = load("reward-observe.js", "soda");

function run(url, body, argument) {
  let out = null;
  const logs = [];
  const fn = new Function(
    "$request", "$response", "$done", "console", "$argument", code
  );
  fn(
    { url },
    { body: typeof body === "string" ? body : JSON.stringify(body) },
    (v) => { out = v; },
    { log: (...a) => logs.push(a.join(" ")) },
    argument
  );
  return { out, logs };
}

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) {
    pass++;
    console.log("  PASS  " + name);
  } else {
    fail++;
    console.log("  FAIL  " + name + (extra ? "  got=" + extra : ""));
  }
}

const TASK_BODY = {
  status_code: 0,
  task_infos: [
    { task_key: "douyin_listen", title: "听抖音", reward_amount: 50, can_show: true },
    { task_key: "sign_in", title: "签到得金币", reward_amount: 10, can_show: true },
    { task_key: "listen_duration", title: "听歌", reward_amount: 20 }
  ]
};

console.log("\n== 1. logTaskTitles=false：日志里不出现任务文案 ==");
{
  const r = run("https://api.qishui.com/luna/treasure/task/view", TASK_BODY, { logTaskTitles: false });
  const text = r.logs.join(" ");
  check("有日志输出", text.length > 0);
  check("不含“听抖音”", text.indexOf("听抖音") === -1, text.slice(0, 200));
  check("仍能看到 task_key", text.indexOf("douyin_listen") !== -1, text.slice(0, 200));
}

console.log("\n== 2. logTaskTitles=true：日志带任务标题 ==");
{
  const r = run("https://api.qishui.com/luna/treasure/task/view", TASK_BODY, { logTaskTitles: true });
  const text = r.logs.join(" ");
  check("包含“听抖音”", text.indexOf("听抖音") !== -1, text.slice(0, 300));
  check("包含“签到得金币”", text.indexOf("签到得金币") !== -1, text.slice(0, 300));
  check("仍然只读（不返回 body）", !(r.out && r.out.body), JSON.stringify(r.out));
}

console.log("\n== 3. view.title 形态的标题也能取到 ==");
{
  const body = {
    status_code: 0,
    sections: [
      {
        key: "gold_task_section",
        task_group: {
          tasks: [
            {
              id: "600585",
              key: "soda_music_sign_in",
              view: { title: { type: 1, plain_text: "听抖音" } }
            }
          ]
        }
      }
    ]
  };
  const r = run("https://api.qishui.com/luna/treasure/task/view", body, { logTaskTitles: true });
  check("取到 view.title.plain_text",
    r.logs.join(" ").indexOf("听抖音") !== -1, r.logs.join(" ").slice(0, 300));
}

console.log("\n" + (fail === 0 ? "ALL PASS" : "FAILURES") +
  "  pass=" + pass + " fail=" + fail);
process.exit(fail === 0 ? 0 : 1);
