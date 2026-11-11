const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const ROOT = path.join(__dirname, "..");
const QIDIAN_JSON = path.join(ROOT, "src", "apps", "qidian.json");
const QIDIAN_PLUGIN = path.join(ROOT, "plugins", "qidian", "qidian.plugin");
const QIDIAN_SCRIPT = fs.existsSync(path.join(ROOT, "plugins", "qidian", "Qidian.js"))
  ? path.join(ROOT, "plugins", "qidian", "Qidian.js")
  : path.join(ROOT, "plugins", "qidian", "scripts", "Qidian.js");

test("qidian argument duplicate check in json and plugin", () => {
  const json = JSON.parse(fs.readFileSync(QIDIAN_JSON, "utf8"));
  const bindings = json.enhance.bindings || [];
  for (const b of bindings) {
    if (b.argument) {
      const set = new Set(b.argument);
      assert.strictEqual(
        b.argument.length,
        set.size,
        `Binding ${b.id} in src/apps/qidian.json has duplicate arguments: ${JSON.stringify(b.argument)}`
      );
    }
  }

  const pluginText = fs.readFileSync(QIDIAN_PLUGIN, "utf8");
  const matches = pluginText.matchAll(/argument=\[([^\]]+)\]/g);
  for (const m of matches) {
    const rawArgs = m[1].split(",").map((s) => s.trim().replace(/^\{|\}$/g, ""));
    const set = new Set(rawArgs);
    assert.strictEqual(
      rawArgs.length,
      set.size,
      `Plugin line has duplicate argument: ${m[0]}`
    );
  }
});

test("qidian script argument normalization and switch off handling", () => {
  const scriptContent = fs.readFileSync(QIDIAN_SCRIPT, "utf8");

  function runWithArg(arg) {
    const sandbox = {
      $argument: arg,
      $persistentStore: { read: () => null, write: () => true },
      $notification: { post: () => {} },
      $done: () => {},
      console: { log: () => {}, warn: () => {}, error: () => {} },
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);

    // Extract normalizeGlobalArgument and engineTaskSwitchesOff definitions
    const code = `
      ${scriptContent.slice(
        scriptContent.indexOf("function normalizeGlobalArgument"),
        scriptContent.indexOf("const $ = new Env")
      )}
      ${scriptContent.slice(
        scriptContent.indexOf("function engineTaskSwitchesOff"),
        scriptContent.indexOf("async function executeCronTasks")
      )}
      result = {
        switchesOff: engineTaskSwitchesOff(),
        resolvedArg: (typeof globalThis !== 'undefined' && globalThis.$argument) || $argument
      };
    `;
    vm.runInContext(code, sandbox);
    return sandbox.result;
  }

  // 1. Script v2 object argument with AUTO_ENABLE = false
  {
    const { switchesOff, resolvedArg } = runWithArg({
      QDREADER_DEBUG: false,
      QDREADER_AUTO_ENABLE: false,
    });
    assert.strictEqual(switchesOff, true, "Should detect switches off when QDREADER_AUTO_ENABLE is false");
    assert.strictEqual(resolvedArg.QDREADER_ADV_JOB_ENABLE, false);
    assert.strictEqual(resolvedArg.QDREADER_EXTRA_ADV_JOB_ENABLE, false);
    assert.strictEqual(resolvedArg.QDREADER_LOTTERY_ENABLE, false);
    assert.strictEqual(resolvedArg.QDREADER_WEEKLY_EXCHANGE_ENABLE, false);
  }

  // 2. Script v2 object argument with AUTO_ENABLE = true
  {
    const { switchesOff, resolvedArg } = runWithArg({
      QDREADER_DEBUG: false,
      QDREADER_AUTO_ENABLE: true,
    });
    assert.strictEqual(switchesOff, false, "Should not detect switches off when QDREADER_AUTO_ENABLE is true");
    assert.strictEqual(resolvedArg.QDREADER_ADV_JOB_ENABLE, true);
    assert.strictEqual(resolvedArg.QDREADER_EXTRA_ADV_JOB_ENABLE, true);
  }

  // 3. Legacy positional array argument: [false, false]
  {
    const { switchesOff, resolvedArg } = runWithArg([false, false]);
    assert.strictEqual(switchesOff, true, "Should detect switches off for positional array [false, false]");
    assert.strictEqual(resolvedArg.QDREADER_ADV_JOB_ENABLE, false);
  }

  // 4. Legacy positional array argument: [false, true]
  {
    const { switchesOff, resolvedArg } = runWithArg([false, true]);
    assert.strictEqual(switchesOff, false, "Should not detect switches off for positional array [false, true]");
    assert.strictEqual(resolvedArg.QDREADER_ADV_JOB_ENABLE, true);
  }

  // 5. Undefined argument (defaults to running full tasks)
  {
    const { switchesOff } = runWithArg(undefined);
    assert.strictEqual(switchesOff, false, "Undefined argument should default to switches not off");
  }
});
