"use strict";

const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const tools = require("./local-tools");
const documents = require("./documents");
const agent = require("./agent");
const updater = require("./update");

// The site to load. `--url=` wins over the DREAMAI_URL environment variable so
// `pnpm start:local` works on every platform without a cross-env shim.
const URL_ARG = "--url=";
const urlArg = process.argv.find((arg) => arg.startsWith(URL_ARG));
const APP_URL =
  (urlArg && urlArg.slice(URL_ARG.length)) ||
  process.env.DREAMAI_URL ||
  "https://liguijiang.com";
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
    frame: false,
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
  mainWindow.on("maximize", () => mainWindow?.webContents.send("win:maximized", true));
  mainWindow.on("unmaximize", () => mainWindow?.webContents.send("win:maximized", false));
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
    "desktop:update-install",
    wrap(async (event, rawManifest) => {
      if (process.platform !== "win32") throw new Error("当前仅支持 Windows 自动更新");
      const manifest = updater.parseManifest(rawManifest);
      if (updater.compareVersions(manifest.version, app.getVersion()) <= 0) {
        throw new Error("当前已经是最新版本");
      }

      const send = (payload) => {
        if (!event.sender.isDestroyed()) event.sender.send("desktop:update-progress", payload);
      };
      const dir = await fs.promises.mkdtemp(path.join(app.getPath("temp"), "dreamai-update-"));
      const destination = path.join(dir, manifest.file);
      send({ phase: "download", received: 0, total: manifest.size, percent: 0 });
      const installer = await updater.downloadInstaller(manifest, {
        destination,
        onProgress: send,
      });

      send({ phase: "installing", percent: 100 });
      const child = spawn(installer, ["/S"], {
        detached: true,
        stdio: "ignore",
        windowsHide: true,
      });
      child.unref();
      setTimeout(() => app.quit(), 1200);
      return { ok: true, version: manifest.version };
    }),
  );

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

async function printPdf(html, target) {
  const pdfWindow = new BrowserWindow({
    show: false,
    width: 900,
    height: 1200,
    webPreferences: {
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      javascript: false,
    },
  });
  try {
    await pdfWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
    const buffer = await pdfWindow.webContents.printToPDF({
      printBackground: true,
      pageSize: "A4",
      margins: { marginType: "none" },
    });
    fs.writeFileSync(target, buffer);
  } finally {
    if (!pdfWindow.isDestroyed()) pdfWindow.destroy();
  }
}

function documentDirectory() {
  const workspace = tools.getWorkspace();
  if (!workspace) throw new Error("请先选择工作文件夹");
  return path.join(workspace, documents.DOC_DIR);
}

function assertDocumentPath(candidate) {
  const dir = documentDirectory();
  const target = path.resolve(String(candidate || ""));
  if (!target.startsWith(dir + path.sep)) throw new Error("文件不在 Dream AI 文档目录中");
  if (!fs.existsSync(target)) throw new Error("文件已不存在");
  return target;
}

function registerExtraIpc() {
  ipcMain.handle("win:minimize", () => {
    mainWindow?.minimize();
  });
  ipcMain.handle("win:toggle-maximize", () => {
    if (!mainWindow) return false;
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
    return mainWindow.isMaximized();
  });
  ipcMain.handle("win:close", () => {
    mainWindow?.close();
  });
  ipcMain.handle("win:is-maximized", () => Boolean(mainWindow?.isMaximized()));

  ipcMain.handle(
    "code:create-project",
    wrap(async (_event, name) => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先选择工作文件夹");
      return agent.createProject(workspace, name);
    }),
  );
  ipcMain.handle(
    "code:write-files",
    wrap(async (_event, payload) => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先选择工作文件夹");
      return agent.writeFiles(workspace, payload?.root, payload?.files);
    }),
  );
  ipcMain.handle(
    "code:run-command",
    wrap(async (_event, payload) => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先选择工作文件夹");
      const project = agent.assertProject(workspace, payload?.root);
      const cmd = String(payload?.cmd || "").trim();
      if (!cmd) return { code: 0, stdout: "", stderr: "" };
      if (agent.needsApproval(cmd, Boolean(payload?.auto))) {
        const ok = await confirmAction(
          `Dream AI 想执行这条命令`,
          `${cmd}\n\n目录：${project}\n\n命令会记录在项目的 dreamai-commands.log 里。`,
        );
        if (!ok) return { blocked: true };
      }
      return agent.runCommand(project, cmd, { timeoutMs: Number(payload?.timeoutMs) || 180000 });
    }),
  );
  ipcMain.handle(
    "code:start-server",
    wrap(async (_event, payload) => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先选择工作文件夹");
      const project = agent.assertProject(workspace, payload?.root);
      const cmd = String(payload?.cmd || "").trim();
      if (!cmd) throw new Error("没有可用的启动命令");
      if (agent.needsApproval(cmd, true)) {
        const ok = await confirmAction(`Dream AI 想启动服务`, `${cmd}\n\n目录：${project}`);
        if (!ok) return { blocked: true };
      }
      return agent.startServer(project, cmd);
    }),
  );
  ipcMain.handle(
    "code:scaffold",
    wrap(async (_event, payload) => agent.scaffoldFiles(payload?.kind, payload?.port)),
  );
  ipcMain.handle("code:server-output", wrap(async (_event, id) => agent.serverOutput(id)));
  ipcMain.handle("code:stop-server", wrap(async (_event, id) => agent.stopServer(id)));
  ipcMain.handle("code:kill-current", wrap(async () => agent.killCurrentCommand()));
  ipcMain.handle(
    "code:list-dir",
    wrap(async (_event, payload) => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先选择工作文件夹");
      return agent.listDir(workspace, payload?.root, payload?.rel);
    }),
  );
  ipcMain.handle(
    "code:read-file",
    wrap(async (_event, payload) => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先选择工作文件夹");
      return agent.readFile(workspace, payload?.root, payload?.rel, Number(payload?.max) || 80000);
    }),
  );
  ipcMain.handle(
    "code:open-folder",
    wrap(async (_event, root) => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先选择工作文件夹");
      const project = agent.assertProject(workspace, root);
      const error = await shell.openPath(project);
      if (error) throw new Error(error);
      return { ok: true };
    }),
  );
  ipcMain.handle(
    "code:open-url",
    wrap(async (_event, url) => {
      const target = String(url || "");
      if (!/^https?:\/\//i.test(target)) throw new Error("链接无效");
      await shell.openExternal(target);
      return { ok: true };
    }),
  );
  ipcMain.handle(
    "doc:create",
    wrap(async (_event, spec) => {
      const workspace = tools.getWorkspace();
      if (!workspace) throw new Error("请先在「本地工作台」选择文件夹");
      return documents.createDocument(spec, workspace, { printPdf });
    }),
  );
  ipcMain.handle(
    "doc:list",
    wrap(async () => documents.listDocuments(tools.getWorkspace())),
  );
  ipcMain.handle(
    "doc:open",
    wrap(async (_event, target) => {
      const file = assertDocumentPath(target);
      const error = await shell.openPath(file);
      if (error) throw new Error(error);
      return { ok: true };
    }),
  );
  ipcMain.handle(
    "doc:reveal",
    wrap(async (_event, target) => {
      shell.showItemInFolder(assertDocumentPath(target));
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
    if (devWorkspace) {
      fs.mkdirSync(devWorkspace, { recursive: true });
      tools.setWorkspace(devWorkspace);
    }
    registerIpc();
    registerExtraIpc();
    createWindow();

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });

  app.on("will-quit", () => agent.stopAll());

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
}
