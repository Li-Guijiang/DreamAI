"use strict";

const { contextBridge, ipcRenderer } = require("electron");

const invoke = (channel, ...args) => ipcRenderer.invoke(channel, ...args);

contextBridge.exposeInMainWorld("dreamDesktop", {
  isDesktop: true,
  platform: process.platform,
  version: () => invoke("desktop:version"),

  pickFolder: () => invoke("local:pick-folder"),
  getWorkspace: () => invoke("local:workspace"),
  scan: () => invoke("local:scan"),

  planOrganize: () => invoke("local:plan-organize"),
  applyOrganize: () => invoke("local:apply-organize"),

  planRename: (prefix) => invoke("local:plan-rename", prefix),
  applyRename: () => invoke("local:apply-rename"),

  saveText: (name, content) => invoke("local:save-text", name, content),
  openWorkspace: () => invoke("local:open-workspace"),

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
