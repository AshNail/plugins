#!/usr/bin/env node
/*
 * Minify src/<family>/*.js into plugins/<family>/scripts/*.min.js.
 *
 * Layout contract:
 *   src/common/*.js                         shared single-source scripts (soda+douyin)
 *   src/common/families.json                per-family tokens for expanding them
 *   src/<family>/<name>.js                  readable source (shared ones are generated)
 *   plugins/<family>/<Name>.plugin         deployable plugin
 *   plugins/<family>/scripts/<name>.min.js deployable script
 *
 * The plugin must reference scripts with a relative path, using the v2 inline
 * form (legacy script-path= is still recognized):
 *   script("scripts/<name>.min.js", {...})
 */
"use strict";

const fs = require("fs");
const path = require("path");
const terser = require("terser");

const ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(ROOT, "src");
const PLUGINS_DIR = path.join(ROOT, "plugins");
const COMMON_DIR = path.join(SRC_DIR, "common");

// Keep the feature switches recognizable in the minified output. Everything
// else (including top-level helpers) is mangled to make the deployed scripts
// genuinely compressed rather than just renamed.
const RESERVED_NAMES = [
  "AGGRESSIVE",
  "DRY_RUN",
  "INJECT_MISSING",
  "ENABLED",
  "VERBOSE",
  "FORCE_OK",
  "EXTEND_EXPIRY",
  "EXTEND_DAYS"
];

function listDirs(dir) {
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

function listJs(dir) {
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".js"))
    .map((entry) => entry.name)
    .sort();
}

// ---------------------------------------------------------------------------
// Shared-script layer (src/common):
//   src/common/block-domains.js / daily-reminder.js / welfare-stamp.js are the
//   single editable sources for scripts used by BOTH soda and douyin. Per-app
//   differences live in src/common/families.json; this build expands them into
//   src/<family>/<name>.js (readable, committed, do not hand-edit) which the
//   regular per-family minify pass then turns into plugins/<family>/scripts/.
// ---------------------------------------------------------------------------
function loadCommonConfig() {
  const file = path.join(COMMON_DIR, "families.json");
  const data = JSON.parse(fs.readFileSync(file, "utf8"));
  const scripts = data.sharedScripts || [];
  const tokens = (data.tokens || []).map(([token, key]) => ({ token, key }));
  const families = data.families || {};
  if (scripts.length === 0) throw new Error(`${file}: sharedScripts is empty`);
  if (tokens.length === 0) throw new Error(`${file}: tokens is empty`);
  if (Object.keys(families).length === 0) throw new Error(`${file}: families is empty`);
  for (const script of scripts) {
    if (!fs.existsSync(path.join(COMMON_DIR, script))) {
      throw new Error(`${file}: shared script src/common/${script} is missing`);
    }
  }
  return { scripts, tokens, families, file };
}

function tokenValue(value) {
  if (value === true) return "true";
  if (value === false) return "false";
  return String(value);
}

function expandSharedScripts(family, common) {
  const cfg = common.families[family];
  if (!cfg) {
    throw new Error(`src/common/families.json: family "${family}" has no config`);
  }
  for (const script of common.scripts) {
    let source = fs.readFileSync(path.join(COMMON_DIR, script), "utf8");
    for (const { token, key } of common.tokens) {
      if (!(key in cfg)) {
        throw new Error(`src/common/families.json: family "${family}" misses key "${key}" (${token})`);
      }
      source = source.split(token).join(tokenValue(cfg[key]));
    }
    if (source.includes("@@")) {
      throw new Error(`src/common/${script}: unresolved @@ tokens for family ${family}`);
    }
    const outputFile = path.join(SRC_DIR, family, script);
    fs.writeFileSync(outputFile, source);
    console.log(`common/${script} -> src/${family}/${script} (${family} config)`);
  }
}

function pluginScriptRefs(pluginFile) {
  const refs = [];
  const lines = fs.readFileSync(pluginFile, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith(";")) continue;
    // Current plugins use the v2 inline form: script("scripts/x.min.js", {...}).
    for (const match of trimmed.matchAll(/\bscript\(\s*["']([^"']+)["']/g)) {
      refs.push(match[1]);
    }
    // Keep the legacy custom-node syntax covered as well.
    for (const match of trimmed.matchAll(/\bscript-path=([^,\s]+)/g)) {
      refs.push(match[1]);
    }
  }
  return [...new Set(refs)];
}

async function minifyFile(family, file) {
  const sourceFile = path.join(SRC_DIR, family, file);
  const outputName = file.replace(/\.js$/, ".min.js");
  const outputFile = path.join(PLUGINS_DIR, family, "scripts", outputName);
  const source = fs.readFileSync(sourceFile, "utf8");

  const result = await terser.minify(source, {
    compress: {
      passes: 2,
      toplevel: true,
      drop_console: false,
      // Keep top-level feature flags (AGGRESSIVE / DRY_RUN / ...) visible so
      // tests can toggle them in both source and minified builds.
      evaluate: false
    },
    mangle: {
      toplevel: true,
      reserved: RESERVED_NAMES
    },
    format: {
      comments: false,
      preamble: `/*! ${family}/${file} | minified from src/${family}/${file} */`
    }
  });

  if (result.error) throw result.error;
  if (!result.code) throw new Error(`empty minified output for ${family}/${file}`);

  const output = result.code + "\n";
  const sourceBytes = Buffer.byteLength(source);
  const outputBytes = Buffer.byteLength(output);
  if (outputBytes >= sourceBytes) {
    throw new Error(
      `minified output is not smaller for ${family}/${file}: ` +
        `${sourceBytes} -> ${outputBytes} bytes`
    );
  }
  if (result.code.split("\n").length > 5) {
    throw new Error(`minified output still has too many lines for ${family}/${file}`);
  }

  fs.mkdirSync(path.dirname(outputFile), { recursive: true });
  fs.writeFileSync(outputFile, output);
  return {
    sourceFile,
    outputFile,
    sourceBytes,
    outputBytes
  };
}

async function main() {
  if (!fs.existsSync(SRC_DIR)) {
    throw new Error(`missing source directory: ${SRC_DIR}`);
  }

  const families = listDirs(SRC_DIR).filter((name) => name !== "common");
  if (families.length === 0) {
    throw new Error(`no plugin families found under ${SRC_DIR}`);
  }

  let totalSource = 0;
  let totalOutput = 0;
  let totalFiles = 0;

  for (const family of families) {
    if (fs.existsSync(COMMON_DIR)) {
      const common = loadCommonConfig();
      if (common.families[family]) {
        expandSharedScripts(family, common);
      } else if (family === "soda" || family === "douyin") {
        throw new Error(`${family}: needs src/common/families.json config for shared scripts`);
      }
    }

    const sourceFiles = listJs(path.join(SRC_DIR, family));
    if (sourceFiles.length === 0) {
      console.log(`skip ${family}: no source scripts`);
      continue;
    }

    const scriptsDir = path.join(PLUGINS_DIR, family, "scripts");
    fs.mkdirSync(scriptsDir, { recursive: true });

    const expected = new Set(sourceFiles.map((file) => file.replace(/\.js$/, ".min.js")));
    for (const existing of fs.readdirSync(scriptsDir)) {
      if (existing.endsWith(".min.js") && !expected.has(existing)) {
        fs.unlinkSync(path.join(scriptsDir, existing));
        console.log(`remove stale plugins/${family}/scripts/${existing}`);
      }
    }

    for (const file of sourceFiles) {
      const result = await minifyFile(family, file);
      totalSource += result.sourceBytes;
      totalOutput += result.outputBytes;
      totalFiles += 1;
      const ratio = ((1 - result.outputBytes / result.sourceBytes) * 100).toFixed(1);
      console.log(
        `${family}/${file} -> plugins/${family}/scripts/${path.basename(result.outputFile)} ` +
          `(${result.sourceBytes} -> ${result.outputBytes} B, -${ratio}%)`
      );
    }
  }

  let missingRefs = 0;
  for (const family of families) {
    const familyDir = path.join(PLUGINS_DIR, family);
    if (!fs.existsSync(familyDir)) {
      console.log(`warn ${family}: no plugins/${family}/ directory`);
      continue;
    }

    const plugins = fs
      .readdirSync(familyDir, { withFileTypes: true })
      .filter((entry) => entry.isFile() && entry.name.endsWith(".plugin"))
      .map((entry) => entry.name)
      .sort();

    for (const plugin of plugins) {
      const pluginFile = path.join(familyDir, plugin);
      for (const ref of pluginScriptRefs(pluginFile)) {
        if (!ref.endsWith(".min.js")) {
          console.error(`error plugins/${family}/${plugin}: script is not minified: ${ref}`);
          missingRefs += 1;
          continue;
        }
        if (!fs.existsSync(path.join(familyDir, ref))) {
          console.error(`error plugins/${family}/${plugin}: missing ${ref}`);
          missingRefs += 1;
        }
      }
    }
  }

  const ratio = totalSource ? ((1 - totalOutput / totalSource) * 100).toFixed(1) : "0.0";
  console.log(
    `\nminified ${totalFiles} file(s): ${totalSource} -> ${totalOutput} bytes (-${ratio}%)`
  );

  if (missingRefs > 0) {
    throw new Error(`${missingRefs} plugin script reference(s) are broken`);
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
});
