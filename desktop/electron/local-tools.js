"use strict";

/**
 * Local file tools for the Dream AI desktop app.
 *
 * Everything here is deliberately boring and bounded:
 *  - only the folder the user picked is touched
 *  - only top-level files are considered
 *  - every write goes through a native confirmation dialog in main.js
 *  - symlinks are ignored, paths are resolved and containment-checked
 */

const fs = require("fs");
const path = require("path");

const CATEGORIES = [
  {
    name: "图片",
    exts: ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico", "heic", "avif"],
  },
  {
    name: "文档",
    exts: ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md", "csv", "json", "xml", "rtf"],
  },
  { name: "视频", exts: ["mp4", "mov", "avi", "mkv", "webm", "flv", "wmv"] },
  { name: "音频", exts: ["mp3", "wav", "flac", "aac", "ogg", "m4a"] },
  { name: "压缩包", exts: ["zip", "rar", "7z", "tar", "gz", "bz2", "xz"] },
  { name: "安装包", exts: ["exe", "msi", "apk", "dmg", "pkg", "deb", "rpm"] },
  { name: "代码", exts: ["js", "ts", "jsx", "tsx", "py", "java", "c", "cpp", "h", "go", "rs", "html", "css", "sh", "bat", "ps1"] },
];

const EXT_TO_CATEGORY = new Map();
for (const category of CATEGORIES) {
  for (const ext of category.exts) EXT_TO_CATEGORY.set(ext, category.name);
}

const state = {
  workspace: null,
  pendingOrganize: null,
  pendingRename: null,
};

function setWorkspace(dir) {
  state.workspace = path.resolve(dir);
  state.pendingOrganize = null;
  state.pendingRename = null;
  return state.workspace;
}

function getWorkspace() {
  return state.workspace;
}

function requireWorkspace() {
  if (!state.workspace) {
    const error = new Error("请先选择一个工作文件夹");
    error.code = "NO_WORKSPACE";
    throw error;
  }
  if (!fs.existsSync(state.workspace)) {
    const error = new Error("工作文件夹已不存在，请重新选择");
    error.code = "WORKSPACE_MISSING";
    throw error;
  }
}

function insideWorkspace(relative) {
  requireWorkspace();
  const target = path.resolve(state.workspace, relative);
  const base = state.workspace.endsWith(path.sep) ? state.workspace : state.workspace + path.sep;
  if (target !== state.workspace && !target.startsWith(base)) {
    throw new Error("路径超出了工作文件夹范围");
  }
  return target;
}

function isSafeEntry(entry) {
  return !entry.name.startsWith(".") && !entry.isSymbolicLink();
}

function listTopLevel() {
  requireWorkspace();
  return fs
    .readdirSync(state.workspace, { withFileTypes: true })
    .filter(isSafeEntry);
}

function categoryOf(filename) {
  const ext = path.extname(filename).slice(1).toLowerCase();
  return EXT_TO_CATEGORY.get(ext) || "其他";
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function scan() {
  requireWorkspace();
  const entries = listTopLevel();
  const files = entries.filter((entry) => entry.isFile());
  const dirs = entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name);
  let totalSize = 0;
  const byCategory = {};
  for (const file of files) {
    const full = path.join(state.workspace, file.name);
    try {
      totalSize += fs.statSync(full).size;
    } catch {
      /* skip unreadable */
    }
    const category = categoryOf(file.name);
    byCategory[category] = (byCategory[category] || 0) + 1;
  }
  return {
    path: state.workspace,
    name: path.basename(state.workspace),
    files: files.length,
    folders: dirs.length,
    size: totalSize,
    sizeLabel: formatBytes(totalSize),
    byCategory,
  };
}

function uniqueTarget(dir, filename) {
  const ext = path.extname(filename);
  const stem = path.basename(filename, ext);
  let candidate = path.join(dir, filename);
  let index = 1;
  while (fs.existsSync(candidate)) {
    candidate = path.join(dir, `${stem}-${index}${ext}`);
    index += 1;
  }
  return candidate;
}

function planOrganize() {
  requireWorkspace();
  const entries = listTopLevel().filter((entry) => entry.isFile());
  const moves = entries.map((entry) => {
    const category = categoryOf(entry.name);
    return {
      from: entry.name,
      to: path.join(category, entry.name),
      category,
    };
  });
  state.pendingOrganize = moves;
  const byCategory = {};
  for (const move of moves) byCategory[move.category] = (byCategory[move.category] || 0) + 1;
  return { moves, byCategory, total: moves.length, workspace: state.workspace };
}

function applyOrganize() {
  requireWorkspace();
  const moves = state.pendingOrganize || [];
  if (!moves.length) return { moved: 0, errors: [] };

  const errors = [];
  let moved = 0;
  for (const move of moves) {
    try {
      const source = insideWorkspace(move.from);
      const stat = fs.lstatSync(source);
      if (!stat.isFile()) continue;
      const categoryDir = insideWorkspace(move.category);
      fs.mkdirSync(categoryDir, { recursive: true });
      const destination = uniqueTarget(categoryDir, path.basename(source));
      fs.renameSync(source, destination);
      moved += 1;
    } catch (error) {
      errors.push(`${move.from}: ${error.message}`);
    }
  }
  state.pendingOrganize = null;
  return { moved, errors };
}

function planRename(prefix) {
  requireWorkspace();
  const safePrefix = String(prefix || "Dream").trim().replace(/[\\/:*?"<>|]/g, "-").slice(0, 40) || "Dream";
  const entries = listTopLevel()
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b, "zh-CN", { numeric: true }));

  const width = Math.max(2, String(entries.length).length);
  const taken = new Set(entries);
  const changes = [];
  let index = 0;
  for (const name of entries) {
    index += 1;
    const ext = path.extname(name);
    let next = `${safePrefix}-${String(index).padStart(width, "0")}${ext}`;
    let suffix = 1;
    while (taken.has(next) && next !== name) {
      next = `${safePrefix}-${String(index).padStart(width, "0")}-${suffix}${ext}`;
      suffix += 1;
    }
    taken.add(next);
    if (next !== name) changes.push({ from: name, to: next });
  }
  state.pendingRename = { changes, prefix: safePrefix };
  return { changes, total: changes.length, prefix: safePrefix, workspace: state.workspace };
}

function applyRename() {
  requireWorkspace();
  const pending = state.pendingRename;
  if (!pending || !pending.changes.length) return { renamed: 0, errors: [] };

  const errors = [];
  let renamed = 0;
  for (const change of pending.changes) {
    try {
      const source = insideWorkspace(change.from);
      const destination = insideWorkspace(change.to);
      if (!fs.lstatSync(source).isFile()) continue;
      if (fs.existsSync(destination)) {
        errors.push(`${change.from}: 目标已存在`);
        continue;
      }
      fs.renameSync(source, destination);
      renamed += 1;
    } catch (error) {
      errors.push(`${change.from}: ${error.message}`);
    }
  }
  state.pendingRename = null;
  return { renamed, errors };
}

function sanitizeFilename(name) {
  const cleaned = String(name || "")
    .replace(/[\\/:*?"<>|]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 80);
  return cleaned || "Dream AI 文档";
}

function saveText(name, content) {
  requireWorkspace();
  let filename = sanitizeFilename(name);
  if (!/\.[a-z0-9]{1,8}$/i.test(filename)) filename += ".md";
  const target = insideWorkspace(filename);
  if (fs.existsSync(target)) {
    const error = new Error("同名文件已存在，请换一个名字");
    error.code = "EXISTS";
    throw error;
  }
  fs.writeFileSync(target, String(content || ""), "utf8");
  return { path: target, name: filename };
}

module.exports = {
  CATEGORIES,
  applyOrganize,
  applyRename,
  categoryOf,
  formatBytes,
  getWorkspace,
  planOrganize,
  planRename,
  saveText,
  scan,
  setWorkspace,
};
