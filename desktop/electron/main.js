"use strict";

const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const path = require("path");
const fs = require("fs");
const tools = require("./local-tools");

const APP_URL = process.env.DREAMAI_URL || "https://liguijiang.com";
const PRODUCT = "Dream AI";

let mainWindow = null;
let pendingOrganize = null;
let pendingRename = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 980,
    minHeight: 640,
    show: false,
    backgroundColor: "#08090d",
    title: PRODUCT,
    icon: path.join(__dirname, "..", "build", "icon.ico"),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webviewTag: false,
      spellcheck: false,
    },
  });

  mainWindow.loadURL(APP_URL);
  mainWindow.once("ready-to-show", () => mainWindow.show());

  // Never let the app navigate away from the official site.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, url) => {
    const allowed = url.startsWith(APP_URL);
    if (!allowed) {
      event.preventDefault();
      if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    }
  });
  mainWindow.webContents.on("will-attach-webview", (event) => event.preventDefault());

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

async function confirmAction(message, detail) {
  if (process.env.DREAMAI_DEV_AUTO_CONFIRM === "1") return true;
  if (!mainWindow) return false;
  const { response } = await dialog.showMessageBox(mainWindow, {
    type: "warning",
    buttons: ["取消", "确认执行"],
    defaultId: 0,
    cancelId: 0,
    noLink: true,
    title: `${PRODUCT} · 确认操作`,
    message,
    detail: String(detail || "").slice(0, 3000),
  });
  return response === 1;
}

function wrap(handler) {
  return async (...args) => {
    try {
      return await handler(...args);
    } catch (error) {
      throw new Error(error && error.message ? error.message : "操作失败");
    }
  };
}

function registerIpc() {
  ipcMain.handle("desktop:version", () => app.getVersion());

  ipcMain.handle(
    "local:pick-folder",
    wrap(async () => {
      if (!mainWindow) throw new Error("窗口尚未准备好");
      const result = await dialog.showOpenDialog(mainWindow, {
        title: "选择 Dream AI 的工作文件夹",
        buttonLabel: "使用这个文件夹",
        properties: ["openDirectory", "createDirectory"],
      });
      if (result.canceled || !result.filePaths.length) return { canceled: true };
      const workspace = tools.setWorkspace(result.filePaths[0]);
      return { canceled: false, workspace, scan: tools.scan() };
    }),
  );

  ipcMain.handle(
    "local:workspace",
    wrap(async () => {
      const workspace = tools.getWorkspace();
      if (!workspace) return { workspace: null, exists: false };
      return { workspace, exists: fs.existsSync(workspace) };
    }),
  );

  ipcMain.handle("local:scan", wrap(async () => tools.scan()));

  ipcMain.handle(
    "local:plan-organize",
    wrap(async () => {
      const plan = tools.planOrganize();
      pendingOrganize = plan;
      return plan;
    }),
  );

  ipcMain.handle(
    "local:apply-organize",
    wrap(async () => {
      if (!pendingOrganize || !pendingOrganize.total) return { moved: 0, errors: [] };
      const sample = pendingOrganize.moves
        .slice(0, 12)
        .map((move) => `${move.from}  →  ${move.to}`)
        .join("\n");
      const more =
        pendingOrganize.total > 12 ? `\n…… 还有 ${pendingOrganize.total - 12} 个文件` : "";
      const ok = await confirmAction(
        `将 ${pendingOrganize.total} 个文件按类型移动到子文件夹？`,
        `${sample}${more}\n\n位置：${pendingOrganize.workspace}`,
      );
      if (!ok) return { canceled: true };
      const result = tools.applyOrganize();
      pendingOrganize = null;
      return result;
    }),
  );

  ipcMain.handle(
    "local:plan-rename",
    wrap(async (_event, prefix) => {
      const plan = tools.planRename(prefix);
      pendingRename = plan;
      return plan;
    }),
  );

  ipcMain.handle(
    "local:apply-rename",
    wrap(async () => {
      if (!pendingRename || !pendingRename.total) return { renamed: 0, errors: [] };
      const sample = pendingRename.changes
        .slice(0, 12)
        .map((change) => `${change.from}  →  ${change.to}`)
        .join("\n");
      const more =
        pendingRename.total > 12 ? `\n…… 还有 ${pendingRename.total - 12} 个文件` : "";
      const ok = await confirmAction(
        `将重命名 ${pendingRename.total} 个文件？`,
        `${sample}${more}\n\n前缀：${pendingRename.prefix}`,
      );
      if (!ok) return { canceled: true };
      const result = tools.applyRename();
      pendingRename = null;
      return result;
    }),
  );

  ipcMain.handle(
    "local:save-text",
    wrap(async (_event, name, content) => {
      const text = String(content || "");
      const ok = await confirmAction(
        `把内容保存到工作文件夹？`,
        `文件名：${name}\n大小：${(Buffer.byteLength(text, "utf8") / 1024).toFixed(1)} KB\n位置：${tools.getWorkspace()}`,
      );
      if (!ok) return { canceled: true };
      return tools.saveText(name, text);
    }),
  );

  ipcMain.handle(
    "local:open-workspace",
    wrap(async () => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先选择工作文件夹");
      await shell.openPath(workspace);
      return { ok: true };
    }),
  );
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    Menu.setApplicationMenu(null);
    app.setAppUserModelId("com.dreamai.desktop");
    const devWorkspace = process.env.DREAMAI_DEV_WORKSPACE;
    if (devWorkspace && fs.existsSync(devWorkspace)) tools.setWorkspace(devWorkspace);
    registerIpc();
    createWindow();

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
}
