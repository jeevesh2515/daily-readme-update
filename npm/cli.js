#!/usr/bin/env node
/**
 * readme-guardian npm entry point.
 *
 * The npm tarball includes the matching Python wheel. `pipx run` executes that
 * local wheel in an isolated environment: no shell interpolation, no global
 * Python installation, and no second package-registry download.
 */
const { spawnSync } = require("child_process");
const { existsSync } = require("fs");
const { join } = require("path");
const packageMeta = require("./package.json");

const args = process.argv.slice(2);
const wheel = join(__dirname, `readme_guardian-${packageMeta.version}-py3-none-any.whl`);

function run(command, commandArgs) {
  return spawnSync(command, commandArgs, { stdio: "inherit" });
}

function printInstallHelp() {
  console.error(
    "\n  readme-guardian needs pipx to run its bundled Python wheel.\n" +
      "  Install pipx, then retry:\n" +
      "    python3 -m pip install --user pipx\n" +
      "    python3 -m pipx ensurepath\n" +
      "\n  Or install the Python package directly:\n" +
      "    pipx install readme-guardian\n"
  );
}

if (args.includes("--version") || args.includes("-v")) {
  console.log(`readme-guardian v${packageMeta.version} (npm wrapper)`);
  process.exit(0);
}

if (!existsSync(wheel)) {
  console.error("\n  The bundled readme-guardian wheel is missing; reinstall this npm package.\n");
  process.exit(1);
}

const result = run("pipx", ["run", "--spec", wheel, "readme-guardian", ...args]);
if (result.error && result.error.code === "ENOENT") {
  printInstallHelp();
  process.exit(1);
}
process.exit(result.status ?? 1);
