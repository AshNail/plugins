#!/usr/bin/env node
/*
 * Minify src/<family>/*.js into plugins/<family>/scripts/*.min.js.
 *
 * Layout contract:
 *   src/<family>/<name>.js                 readable source
 *   plugins/<family>/<Name>.plugin         deployable plugin
 *   plugins/<family>/scripts/<name>.min.js deployable script
 *
 * The plugin must reference scripts with a relative path:
 *   script-path=scripts/<name>.min.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const terser = require("terser");

const ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(ROOT, "src");
const PLUGINS_DIR = path.join(ROOT, "plugins");

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

function pluginScriptRefs(pluginFile) {
  const refs = [];
  const lines = fs.readFileSync(pluginFile, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith(";")) continue;
    const match = trimmed.match(/\bscript-path=([^,\s]+)/);
    if (match) refs.push(match[1]);
  }
  return refs;
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

  const families = listDirs(SRC_DIR);
  if (families.length === 0) {
    throw new Error(`no plugin families found under ${SRC_DIR}`);
  }

  let totalSource = 0;
  let totalOutput = 0;
  let totalFiles = 0;

  for (const family of families) {
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
