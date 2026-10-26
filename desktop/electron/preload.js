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
});
