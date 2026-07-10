#!/usr/bin/env node
/**
 * readme-guardian npm entry point.
 *
 * Prefer an installed Python CLI. If it is missing, install it through pipx,
 * then delegate with argument arrays so user flags are never shell-expanded.
 */
const { spawnSync } = require("child_process");

const args = process.argv.slice(2);

function run(command, commandArgs, options = {}) {
  return spawnSync(command, commandArgs, {
    stdio: options.stdio || "inherit",
    encoding: "utf-8",
  });
}

function isAvailable(command, commandArgs) {
  const result = run(command, commandArgs, { stdio: "pipe" });
  return result.status === 0;
}

function printInstallHelp() {
  console.error(
    "\n  Could not run readme-guardian.\n" +
      "  Install it first:\n" +
      "    pipx install readme-guardian\n" +
      "    brew install jeevesh2515/homebrew-tap/readme-guardian\n"
  );
}

if (args.includes("--version") || args.includes("-v")) {
  console.log("readme-guardian v1.0.1 (npm wrapper)");
  process.exit(0);
}

if (!isAvailable("readme-guardian", ["--version"])) {
  console.error("\n  Installing readme-guardian through pipx...\n");
  const install = run("pipx", ["install", "readme-guardian"]);
  if (install.error || install.status !== 0) {
    const fallback = run("pipx", ["run", "readme-guardian", ...args]);
    if (fallback.error || fallback.status !== 0) {
      printInstallHelp();
      process.exit(fallback.status || 1);
    }
    process.exit(fallback.status || 0);
  }
}

let delegated = run("readme-guardian", args);
if (delegated.error) {
  delegated = run("pipx", ["run", "readme-guardian", ...args]);
}
if (delegated.error) {
  printInstallHelp();
  process.exit(1);
}
process.exit(delegated.status || 0);
