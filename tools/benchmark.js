#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");

function loadScript(filePath) {
  const code = fs.readFileSync(path.join(ROOT, filePath), "utf8");
  return new vm.Script(code, { filename: filePath });
}

function runScript(script, context) {
  const sandbox = {
    $request: context.$request,
    $response: context.$response,
    $done: context.$done || (() => {}),
    $argument: context.$argument || "",
    $persistentStore: context.$persistentStore || { read: () => null, write: () => true },
    $notification: context.$notification || { post: () => {} },
    $httpClient: context.$httpClient || {},
    $loon: context.$loon || {},
    console: context.console || { log: () => {}, warn: () => {}, error: () => {} },
    setTimeout: (fn) => fn(),
    clearTimeout: () => {},
  };
  vm.createContext(sandbox);
  script.runInContext(sandbox);
}

function benchmark(name, fn, iterations = 5000) {
  // Warmup
  for (let i = 0; i < Math.min(iterations, 500); i++) fn();

  const gc = global.gc;
  if (gc) gc();

  const startMem = process.memoryUsage().heapUsed;
  const t0 = process.hrtime.bigint();

  for (let i = 0; i < iterations; i++) {
    fn();
  }

  const t1 = process.hrtime.bigint();
  const endMem = process.memoryUsage().heapUsed;

  const totalNs = Number(t1 - t0);
  const totalMs = totalNs / 1e6;
  const avgUs = totalNs / iterations / 1e3;
  const opsSec = Math.round((iterations / (totalNs / 1e9)));
  const memDiffKb = Math.round((endMem - startMem) / 1024);

  console.log(
    `  ${name.padEnd(45)} | ${String(iterations).padStart(6)} runs | ` +
    `${totalMs.toFixed(1).padStart(7)} ms | ` +
    `${avgUs.toFixed(2).padStart(8)} µs/op | ` +
    `${String(opsSec).padStart(8)} ops/s | ` +
    `${memDiffKb >= 0 ? "+" : ""}${memDiffKb} KB heap`
  );

  return { name, totalMs, avgUs, opsSec };
}

console.log("================================================================================");
console.log("  Loon Proxy Scripts Benchmark (V8 / JSC Simulation)");
console.log("================================================================================");

const sodaSanitize = loadScript("plugins/soda/scripts/sanitize.min.js");
const douyinClean = loadScript("plugins/douyin/scripts/clean.min.js");
const sodaSettings = loadScript("plugins/soda/scripts/settings.min.js");
const douyinTreasure = loadScript("plugins/douyin/scripts/treasure.min.js");

const sampleFeedBody = JSON.stringify({
  status_code: 0,
  aweme_list: [
    { aweme_id: "1", desc: "normal video", is_ads: false },
    { aweme_id: "2", desc: "ad video", is_ads: true, ads_info: { id: "ad1" } },
    { aweme_id: "3", desc: "normal video 2", is_ads: false }
  ]
});

console.log("\n[1] Soda Sanitize (plugins/soda/scripts/sanitize.min.js):");

benchmark("Soda: Non-matching URL (quick passthrough)", () => {
  runScript(sodaSanitize, {
    $request: { url: "https://api.qishui.com/unrelated/path", method: "GET" },
    $response: { status: 200, body: sampleFeedBody },
    $done: () => {}
  });
});

benchmark("Soda: Feed with ads (active sanitization)", () => {
  runScript(sodaSanitize, {
    $request: { url: "https://api.qishui.com/luna/feed/list", method: "POST" },
    $response: { status: 200, body: sampleFeedBody },
    $argument: "cleanAds=true&rewardSafe=false",
    $done: () => {}
  });
});

console.log("\n[2] Douyin Clean (plugins/douyin/scripts/clean.min.js):");

benchmark("Douyin: Non-matching URL (passthrough)", () => {
  runScript(douyinClean, {
    $request: { url: "https://api.douyin.com/other/path", method: "GET" },
    $response: { status: 200, body: sampleFeedBody },
    $done: () => {}
  });
});

benchmark("Douyin: Feed with ads (cleanFeedAds)", () => {
  runScript(douyinClean, {
    $request: { url: "https://beta-luna.douyin.com/luna/ads/retrieve", method: "POST" },
    $response: { status: 200, body: sampleFeedBody },
    $argument: "cleanFeedAds=true",
    $done: () => {}
  });
});

console.log("\n[3] Soda Settings (plugins/soda/scripts/settings.min.js):");

benchmark("Soda Settings: Non-matching URL", () => {
  runScript(sodaSettings, {
    $request: { url: "https://api.qishui.com/other/config", method: "GET" },
    $response: { status: 200, body: "{}" },
    $done: () => {}
  });
});

console.log("\n[4] Douyin Treasure (plugins/douyin/scripts/treasure.min.js):");

benchmark("Douyin Treasure: Non-matching URL", () => {
  runScript(douyinTreasure, {
    $request: { url: "https://beta-luna.douyin.com/luna/other/endpoint", method: "GET" },
    $response: { status: 200, body: "{}" },
    $done: () => {}
  });
});

console.log("================================================================================\n");
