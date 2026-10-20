"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SET = process.env.SCRIPT_SET || process.env.SODA_SCRIPT_SET || "src";

if (SET !== "src" && SET !== "dist") {
  throw new Error(`unknown script set: ${SET}`);
}

function scriptDir(family) {
  return SET === "dist"
    ? path.join(ROOT, "plugins", family, "scripts")
    : path.join(ROOT, "src", family);
}

module.exports = function loadScript(name, family) {
  const fam = family || "soda";
  const file = SET === "dist" ? name.replace(/\.js$/, ".min.js") : name;
  return fs.readFileSync(path.join(scriptDir(fam), file), "utf8");
};

module.exports.SET = SET;
module.exports.scriptDir = scriptDir;
