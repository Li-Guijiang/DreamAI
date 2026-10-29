"use strict";

const { contextBridge, ipcRenderer } = require("electron");

const invoke = (channel, ...args) => ipcRenderer.invoke(channel, ...args);

contextBridge.exposeInMainWorld("dreamDesktop", {
  isDesktop: true,
  platform: process.platform,
  version: () => invoke("desktop:version"),

  update: {
    install: (manifest) => invoke("desktop:update-install", manifest),
    onProgress: (callback) => {
      const listener = (_event, payload) => callback(payload);
      ipcRenderer.on("desktop:update-progress", listener);
      return () => ipcRenderer.removeListener("desktop:update-progress", listener);
    },
  },

  pickFolder: () => invoke("local:pick-folder"),
  getWorkspace: () => invoke("local:workspace"),
  scan: () => invoke("local:scan"),

  planOrganize: () => invoke("local:plan-organize"),
  applyOrganize: () => invoke("local:apply-organize"),

  planRename: (prefix) => invoke("local:plan-rename", prefix),
  applyRename: () => invoke("local:apply-rename"),

  saveText: (name, content) => invoke("local:save-text", name, content),
  openWorkspace: () => invoke("local:open-workspace"),

  code: {
    createProject: (name) => invoke("code:create-project", name),
    writeFiles: (root, files) => invoke("code:write-files", { root, files }),
    runCommand: (root, cmd, options) => invoke("code:run-command", { root, cmd, ...(options || {}) }),
    startServer: (root, cmd) => invoke("code:start-server", { root, cmd }),
    scaffold: (kind, port) => invoke("code:scaffold", { kind, port }),
    serverOutput: (id) => invoke("code:server-output", id),
    stopServer: (id) => invoke("code:stop-server", id),
    killCurrent: () => invoke("code:kill-current"),
    listDir: (root, rel) => invoke("code:list-dir", { root, rel }),
    readFile: (root, rel, max) => invoke("code:read-file", { root, rel, max }),
    openFolder: (root) => invoke("code:open-folder", root),
    openUrl: (url) => invoke("code:open-url", url),
  },
  documents: {
    create: (spec) => invoke("doc:create", spec),
    list: () => invoke("doc:list"),
    open: (target) => invoke("doc:open", target),
    reveal: (target) => invoke("doc:reveal", target),
  },

  window: {
    minimize: () => invoke("win:minimize"),
    toggleMaximize: () => invoke("win:toggle-maximize"),
    close: () => invoke("win:close"),
    isMaximized: () => invoke("win:is-maximized"),
    onMaximized: (callback) => ipcRenderer.on("win:maximized", (_event, value) => callback(value)),
  },
});
