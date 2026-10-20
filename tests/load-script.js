"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SET = process.env.SODA_SCRIPT_SET || "src";

if (SET !== "src" && SET !== "dist") {
  throw new Error(`unknown SODA_SCRIPT_SET: ${SET}`);
}

const SCRIPT_DIR =
  SET === "dist"
    ? path.join(ROOT, "plugins", "soda", "scripts")
    : path.join(ROOT, "src", "soda");

module.exports = function loadScript(name) {
  const file = SET === "dist" ? name.replace(/\.js$/, ".min.js") : name;
  return fs.readFileSync(path.join(SCRIPT_DIR, file), "utf8");
};

module.exports.SET = SET;
module.exports.SCRIPT_DIR = SCRIPT_DIR;
