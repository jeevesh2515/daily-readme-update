#!/usr/bin/env node
/**
 * readme-guardian — npm entry point.
 * Automatically installs the Python CLI via pipx on first run,
 * then delegates all commands to it.
 */
const { execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const args = process.argv.slice(2);
const isNpx = process.env.npm_config_user_agent?.includes("npx");

// Check if the Python CLI is available
function findPythonCLI() {
  try {
    const result = execSync("which readme-guardian 2>/dev/null || pipx run --help >/dev/null 2>&1 && echo pipx", {
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });
    return result.trim();
  } catch {
    return null;
  }
}

// Auto-install via pipx if missing
function ensureInstalled() {
  try {
    execSync("readme-guardian --version 2>/dev/null", { stdio: "pipe" });
    return true;
  } catch {
    console.log("\n  🛡️  Installing readme-guardian (one-time setup)...\n");
    try {
      execSync("pipx install readme-guardian 2>&1", { stdio: "inherit" });
      return true;
    } catch {
      // Fallback: run via pipx directly
      return false;
    }
  }
}

// Check for --install-hook or --version locally
if (args.includes("--version") || args.includes("-v")) {
  console.log("readme-guardian v1.0 (npm wrapper)");
  process.exit(0);
}

// Try direct command first
try {
  execSync("readme-guardian --version 2>/dev/null", { stdio: "pipe" });
  // CLI is installed — delegate
  const result = execSync(`readme-guardian ${args.join(" ")}`, {
    stdio: "inherit",
    encoding: "utf-8",
  });
  process.exit(0);
} catch {
  // CLI not installed — install or use pipx
  if (ensureInstalled()) {
    const result = execSync(`readme-guardian ${args.join(" ")}`, {
      stdio: "inherit",
      encoding: "utf-8",
    });
    process.exit(0);
  } else {
    // Last resort: pipx run
    try {
      execSync(`pipx run readme-guardian ${args.join(" ")}`, {
        stdio: "inherit",
        encoding: "utf-8",
      });
      process.exit(0);
    } catch (e) {
      console.error(
        "\n  ❌ Could not run readme-guardian.\n" +
          "  Install it first:\n" +
          "    pipx install readme-guardian\n" +
          "    brew install readme-guardian\n"
      );
      process.exit(1);
    }
  }
}
