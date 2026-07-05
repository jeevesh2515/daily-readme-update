/**
 * readme-guardian VS Code extension
 *
 * Shows a freshness badge in the status bar and provides
 * one-click README sync commands.
 */
const vscode = require("vscode");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  console.log("🛡️  README Guardian activated");

  // Status bar item
  const statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBarItem.command = "readme-guardian.sync";
  statusBarItem.tooltip = "Click to sync README";
  context.subscriptions.push(statusBarItem);

  // Update status bar based on freshness badge
  function updateStatusBar() {
    const workspaceRoot = getWorkspaceRoot();
    if (!workspaceRoot) {
      statusBarItem.hide();
      return;
    }

    const badgePath = path.join(workspaceRoot, "readme-badge.svg");
    if (fs.existsSync(badgePath)) {
      const svg = fs.readFileSync(badgePath, "utf-8");
      if (svg.includes("fresh") || svg.includes("synced")) {
        statusBarItem.text = "$(shield) README: fresh";
        statusBarItem.backgroundColor = undefined;
      } else if (svg.includes("no-tests")) {
        statusBarItem.text = "$(shield) README: no tests";
        statusBarItem.backgroundColor = new vscode.ThemeColor(
          "statusBarItem.warningBackground"
        );
      } else {
        statusBarItem.text = "$(shield) README: stale";
        statusBarItem.backgroundColor = new vscode.ThemeColor(
          "statusBarItem.errorBackground"
        );
      }
      statusBarItem.show();
    } else {
      // No badge yet — show "unknown" state
      statusBarItem.text = "$(shield) README: unknown";
      statusBarItem.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.warningBackground"
      );
      statusBarItem.show();
    }
  }

  function getWorkspaceRoot() {
    const folders = vscode.workspace.workspaceFolders;
    return folders ? folders[0].uri.fsPath : null;
  }

  function runGuardian(args = []) {
    const root = getWorkspaceRoot();
    if (!root) {
      vscode.window.showErrorMessage("No workspace folder open");
      return;
    }

    try {
      const result = execSync(`readme-guardian ${args.join(" ")}`, {
        cwd: root,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
        timeout: 60000,
      });
      updateStatusBar();
      vscode.window.showInformationMessage("🛡️ README Guardian: synced");
      return result;
    } catch (e) {
      // Try pipx fallback
      try {
        const result = execSync(`pipx run readme-guardian ${args.join(" ")}`, {
          cwd: root,
          encoding: "utf-8",
          stdio: ["pipe", "pipe", "pipe"],
          timeout: 60000,
        });
        updateStatusBar();
        vscode.window.showInformationMessage("🛡️ README Guardian: synced");
        return result;
      } catch (e2) {
        vscode.window.showErrorMessage(
          "🛡️ README Guardian: Install CLI first — `pipx install readme-guardian`"
        );
        return null;
      }
    }
  }

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("readme-guardian.sync", () => {
      runGuardian(["--apply"]);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("readme-guardian.installHook", () => {
      runGuardian(["--install-hook"]);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("readme-guardian.check", () => {
      const result = runGuardian(["--check"]);
      if (result !== null) {
        vscode.window.showInformationMessage("✅ README is current");
      } else {
        vscode.window.showWarningMessage("⚠️ README is stale — run sync");
      }
    })
  );

  // Auto-install hook on first open
  const config = vscode.workspace.getConfiguration("readme-guardian");
  if (config.get("autoInstallHook")) {
    runGuardian(["--install-hook"]);
  }

  // Run on save (optional)
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (config.get("runOnSave")) {
        runGuardian(["--apply", "--pre-push"]);
      }
    })
  );

  // Watch for badge changes and update status bar
  const watcher = vscode.workspace.createFileSystemWatcher("**/readme-badge.svg");
  watcher.onDidChange(updateStatusBar);
  watcher.onDidCreate(updateStatusBar);
  watcher.onDidDelete(updateStatusBar);
  context.subscriptions.push(watcher);

  // Initial check
  setTimeout(updateStatusBar, 1000);
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
