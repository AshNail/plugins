#!/usr/bin/env node
/*
 * Single source for every user-facing plugin parameter.
 *
 *   src/args/<family>.json  ->  [Argument] block in plugins/<family>/<family>.plugin
 *                           ->  SWITCH_LABELS in src/common/status.js
 *                           ->  parameter table in plugins/<family>/README.md
 *
 * Generated regions are delimited by marker comments. Hand edits inside a
 * marker pair are overwritten; everything outside is untouched.
 *
 *   node tools/gen-args.js           rewrite generated regions
 *   node tools/gen-args.js --check   fail if any region is stale (CI / lint)
 */
"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const ARGS_DIR = path.join(ROOT, "src", "args");
const COMMON_FILE = path.join(ARGS_DIR, "common.json");

const PLUGIN_START = (family) =>
  `# >>> GENERATED ARGUMENTS from src/args/${family}.json -- do not edit (npm run build:args)`;
const PLUGIN_END = "# <<< GENERATED ARGUMENTS";
const LABELS_START =
  "/* >>> GENERATED SWITCH_LABELS from src/args/*.json -- do not edit (npm run build:args) */";
const LABELS_END = "/* <<< GENERATED SWITCH_LABELS */";
const README_START = (family) =>
  `<!-- >>> GENERATED ARG-TABLE from src/args/${family}.json -- do not edit (npm run build:args) -->`;
const README_END = "<!-- <<< GENERATED ARG-TABLE -->";

const FAMILY_KEYS = new Set(["comment", "family", "app", "switches"]);
const TYPE_KEYS = {
  switch: new Set(["name", "type", "default", "tag", "desc", "label", "readme"]),
  input: new Set(["name", "type", "default", "tag", "desc", "readme"]),
  select: new Set([
    "name", "type", "default", "values", "valueType", "tag", "desc", "readme"
  ])
};
const NAME_RE = /^[A-Za-z][A-Za-z0-9]*$/;

function rel(file) {
  return path.relative(ROOT, file);
}

function readJson(file) {
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (error) {
    throw new Error(`${rel(file)}: cannot read (${error.message})`);
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${rel(file)}: invalid JSON (${error.message})`);
  }
}

function oneLine(errors, where, field, value) {
  if (typeof value !== "string" || !value.trim()) {
    errors.push(`${where}: ${field} must be a non-empty string`);
    return false;
  }
  if (/[\r\n]/.test(value)) {
    errors.push(`${where}: ${field} must be a single line`);
    return false;
  }
  return true;
}

function validateFamily(schema, file) {
  const errors = [];
  const where = rel(file);
  for (const key of Object.keys(schema)) {
    if (!FAMILY_KEYS.has(key)) errors.push(`${where}: unknown key "${key}"`);
  }
  oneLine(errors, where, "family", schema.family);
  oneLine(errors, where, "app", schema.app);
  if (path.basename(file, ".json") !== schema.family) {
    errors.push(`${where}: family "${schema.family}" must match the file name`);
  }
  if (!Array.isArray(schema.switches) || schema.switches.length === 0) {
    errors.push(`${where}: switches must be a non-empty array`);
    return errors;
  }

  const seen = new Set();
  schema.switches.forEach((item, index) => {
    const at = `${where}: switches[${index}]`;
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      errors.push(`${at}: must be an object`);
      return;
    }
    const allowed = TYPE_KEYS[item.type];
    if (!allowed) {
      errors.push(`${at}: type must be switch | input | select`);
      return;
    }
    for (const key of Object.keys(item)) {
      if (!allowed.has(key)) errors.push(`${at}: unknown key "${key}" for type ${item.type}`);
    }
    if (!oneLine(errors, at, "name", item.name)) return;
    if (!NAME_RE.test(item.name)) {
      errors.push(`${at}: name must match ${NAME_RE}`);
    }
    if (seen.has(item.name)) errors.push(`${at}: duplicate name "${item.name}"`);
    seen.add(item.name);
    oneLine(errors, at, "tag", item.tag);
    oneLine(errors, at, "desc", item.desc);
    if (typeof item.tag === "string" && item.tag.includes(",")) {
      errors.push(`${at}: tag must not contain a comma (Loon attribute separator)`);
    }
    if (typeof item.desc === "string" && item.desc.includes(",")) {
      errors.push(`${at}: desc must not contain a comma (Loon attribute separator)`);
    }
    if (item.readme !== undefined) oneLine(errors, at, "readme", item.readme);

    if (item.type === "switch") {
      if (typeof item.default !== "boolean") {
        errors.push(`${at}: switch default must be true or false`);
      }
      if (!oneLine(errors, at, "label", item.label)) return;
      if (item.label.includes(",")) errors.push(`${at}: label must not contain a comma`);
    } else {
      if (item.label !== undefined) {
        errors.push(`${at}: only switch parameters may have a label`);
      }
      oneLine(errors, at, "default", item.default);
    }

    if (item.type === "input") {
      if (typeof item.default === "string" && item.default.includes('"')) {
        errors.push(`${at}: input default must not contain a double quote`);
      }
    }

    if (item.type === "select") {
      if (!Array.isArray(item.values) || item.values.length < 2) {
        errors.push(`${at}: select values must be an array with at least two entries`);
      } else {
        const values = new Set();
        for (const value of item.values) {
          if (typeof value !== "string" || !value) {
            errors.push(`${at}: select values must be non-empty strings`);
            continue;
          }
          if (/[",\r\n]/.test(value)) {
            errors.push(`${at}: select value "${value}" must not contain a quote or comma`);
          }
          if (values.has(value)) errors.push(`${at}: duplicate select value "${value}"`);
          values.add(value);
        }
        if (!values.has(item.default)) {
          errors.push(`${at}: select default "${item.default}" is not in values`);
        }
      }
      if (item.valueType !== undefined && item.valueType !== "string") {
        errors.push(`${at}: only valueType=string is supported`);
      }
    }
  });
  return errors;
}

function loadSchemas() {
  if (!fs.existsSync(ARGS_DIR)) {
    throw new Error("src/args/ is missing");
  }
  const files = fs
    .readdirSync(ARGS_DIR)
    .filter((name) => name.endsWith(".json") && name !== "common.json")
    .sort();
  if (files.length === 0) throw new Error("src/args/: no family schema files");

  const errors = [];
  const common = readJson(COMMON_FILE);
  if (!Array.isArray(common.labelOrder)) {
    errors.push("src/args/common.json: labelOrder must be an array");
  } else {
    const seen = new Set();
    for (const name of common.labelOrder) {
      if (typeof name !== "string" || !name) {
        errors.push("src/args/common.json: labelOrder entries must be non-empty strings");
      } else if (seen.has(name)) {
        errors.push(`src/args/common.json: duplicate labelOrder entry "${name}"`);
      }
      seen.add(name);
    }
  }

  const families = {};
  for (const name of files) {
    const file = path.join(ARGS_DIR, name);
    const schema = readJson(file);
    errors.push(...validateFamily(schema, file));
    families[schema.family] = schema;
  }
  if (errors.length) throw new Error(errors.join("\n"));
  return { common, families };
}

function argumentLine(item) {
  let head;
  if (item.type === "switch") {
    head = `${item.name} = switch,${item.default}`;
  } else if (item.type === "input") {
    head = `${item.name} = input,"${item.default}"`;
  } else {
    const values = [item.default].concat(item.values.filter((v) => v !== item.default));
    head =
      `${item.name} = select,` +
      values.map((v) => `"${v}"`).join(",") +
      `,type=${item.valueType || "string"}`;
  }
  return `${head},tag=${item.tag},desc=${item.desc}`;
}

function renderArgumentBlock(schema) {
  return (
    [PLUGIN_START(schema.family), "[Argument]"]
      .concat(schema.switches.map(argumentLine))
      .concat([PLUGIN_END])
      .join("\n") + "\n"
  );
}

function labelEntries(schemas) {
  const families = schemas.families || schemas;
  const labels = new Map();
  for (const family of Object.keys(families).sort()) {
    for (const item of families[family].switches) {
      if (item.type !== "switch") continue;
      const previous = labels.get(item.name);
      if (previous) {
        if (previous.label !== item.label) {
          throw new Error(
            `label for "${item.name}" differs: ${previous.family}=${previous.label} / ` +
              `${family}=${item.label}`
          );
        }
        continue;
      }
      labels.set(item.name, { label: item.label, family });
    }
  }
  const byLabel = new Map();
  for (const [name, entry] of labels) {
    if (byLabel.has(entry.label)) {
      throw new Error(
        `label "${entry.label}" is used by both "${byLabel.get(entry.label)}" and "${name}"`
      );
    }
    byLabel.set(entry.label, name);
  }
  const order = [];
  const seen = new Set();
  for (const name of schemas.common.labelOrder) {
    if (!labels.has(name)) {
      throw new Error(
        `src/args/common.json: labelOrder entry "${name}" is not a declared switch`
      );
    }
    order.push(name);
    seen.add(name);
  }
  for (const name of labels.keys()) {
    if (!seen.has(name)) order.push(name);
  }
  return order.map((name) => [name, labels.get(name).label]);
}

function renderLabelsBlock(schemas) {
  const entries = labelEntries(schemas);
  return (
    [LABELS_START, "var SWITCH_LABELS = ["]
      .concat(entries.map(([name, label]) => `  [${JSON.stringify(name)}, ${JSON.stringify(label)}],`))
      .concat(["];", LABELS_END])
      .join("\n") + "\n"
  );
}

function defaultLabel(item) {
  if (item.type === "switch") return item.default ? "开" : "关";
  return "`" + item.default + "`";
}

function renderReadmeBlock(schema) {
  const escape = (text) => text.replace(/\|/g, "\\|");
  const rows = schema.switches.map((item) => {
    const summary = item.readme || `${item.tag}：${item.desc}`;
    return `| \`${item.name}\` | ${defaultLabel(item)} | ${escape(summary)} |`;
  });
  return (
    [README_START(schema.family), "| 开关/参数 | 默认 | 作用 |", "|---|---|---|"]
      .concat(rows)
      .concat([README_END])
      .join("\n") + "\n"
  );
}

function replaceRegion(file, text, startMarker, endMarker, block) {
  const start = text.indexOf(startMarker);
  if (start < 0) {
    throw new Error(`${rel(file)}: missing start marker: ${startMarker}`);
  }
  if (text.indexOf(startMarker, start + startMarker.length) >= 0) {
    throw new Error(`${rel(file)}: duplicate start marker: ${startMarker}`);
  }
  const end = text.indexOf(endMarker, start + startMarker.length);
  if (end < 0) {
    throw new Error(`${rel(file)}: missing end marker after start marker`);
  }
  let endPos = end + endMarker.length;
  if (text[endPos] === "\n") endPos += 1;
  return text.slice(0, start) + block + text.slice(endPos);
}

function buildTargets(schemas) {
  const targets = [];

  for (const family of Object.keys(schemas.families).sort()) {
    const schema = schemas.families[family];
    const pluginFile = path.join(ROOT, "plugins", family, `${family}.plugin`);
    const readmeFile = path.join(ROOT, "plugins", family, "README.md");
    const pluginText = fs.readFileSync(pluginFile, "utf8");
    const readmeText = fs.readFileSync(readmeFile, "utf8");
    targets.push({
      file: pluginFile,
      current: pluginText,
      next: replaceRegion(
        pluginFile,
        pluginText,
        PLUGIN_START(family),
        PLUGIN_END,
        renderArgumentBlock(schema)
      )
    });
    targets.push({
      file: readmeFile,
      current: readmeText,
      next: replaceRegion(
        readmeFile,
        readmeText,
        README_START(family),
        README_END,
        renderReadmeBlock(schema)
      )
    });
  }

  const labelsFile = path.join(ROOT, "src", "common", "status.js");
  const labelsText = fs.readFileSync(labelsFile, "utf8");
  targets.push({
    file: labelsFile,
    current: labelsText,
    next: replaceRegion(
      labelsFile,
      labelsText,
      LABELS_START,
      LABELS_END,
      renderLabelsBlock(schemas)
    )
  });
  return targets;
}

function firstDiffLine(current, next) {
  const a = current.split("\n");
  const b = next.split("\n");
  const max = Math.max(a.length, b.length);
  for (let i = 0; i < max; i++) {
    if (a[i] !== b[i]) {
      return `line ${i + 1}:\n  have: ${a[i] === undefined ? "<missing>" : a[i]}\n  want: ${b[i] === undefined ? "<missing>" : b[i]}`;
    }
  }
  return "line ending difference";
}

function plan(schemas) {
  const targets = buildTargets(schemas);
  return targets.map((target) => {
    const changed = target.current !== target.next;
    return {
      file: target.file,
      changed,
      diff: changed ? firstDiffLine(target.current, target.next) : "",
      next: target.next
    };
  });
}

function main(argv) {
  const check = argv.includes("--check");
  const schemas = loadSchemas();
  const results = plan(schemas);
  const changed = results.filter((result) => result.changed);

  if (check) {
    if (changed.length) {
      for (const result of changed) {
        console.error(`stale ${rel(result.file)} (${result.diff})`);
      }
      console.error(
        `gen-args: ${changed.length} generated file(s) are stale; run npm run build:args`
      );
      process.exit(1);
    }
    console.log(
      `args schema: ${Object.keys(schemas.families).length} families / ` +
        `${labelEntries(schemas).length} labels, generated files up-to-date`
    );
    return;
  }

  for (const result of changed) {
    fs.writeFileSync(result.file, result.next);
    console.log(`update ${rel(result.file)}`);
  }
  console.log(
    `args schema: ${Object.keys(schemas.families).length} families / ` +
      `${labelEntries(schemas).length} labels / ${changed.length} file(s) updated`
  );
}

if (require.main === module) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    console.error("gen-args: " + (error && error.message ? error.message : error));
    process.exit(1);
  }
}

module.exports = {
  loadSchemas,
  validateFamily,
  labelEntries,
  argumentLine,
  renderArgumentBlock,
  renderLabelsBlock,
  renderReadmeBlock,
  plan
};
