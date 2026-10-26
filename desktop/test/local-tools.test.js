"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const tools = require("../electron/local-tools");

function makeDir(names) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "dreamai-desktop-"));
  for (const name of names) fs.writeFileSync(path.join(dir, name), "x");
  return dir;
}

// 1. organise
const dir1 = makeDir(["photo.jpg", "report.pdf", "clip.mp4", "notes.txt", ".hidden"]);
tools.setWorkspace(dir1);
const scan = tools.scan();
console.log("scan:", scan.files, "files,", Object.keys(scan.byCategory).length, "categories");
const plan = tools.planOrganize();
console.log("organize plan:", plan.total, JSON.stringify(plan.byCategory));
const applied = tools.applyOrganize();
console.log("organize applied:", applied.moved, "errors:", applied.errors.length);
console.log("folders:", fs.readdirSync(dir1).filter((n) => fs.statSync(path.join(dir1, n)).isDirectory()));
console.log("hidden untouched:", fs.existsSync(path.join(dir1, ".hidden")));

// 2. rename
const dir2 = makeDir(["b.jpg", "a.jpg", "c.png"]);
tools.setWorkspace(dir2);
const rename = tools.planRename("图片");
console.log("rename plan:", rename.total, rename.changes);
const renamed = tools.applyRename();
console.log("rename applied:", renamed.renamed, fs.readdirSync(dir2).sort());

// 3. save + containment
tools.setWorkspace(dir2);
const saved = tools.saveText("会议记录", "# 你好\n\n这是测试");
console.log("saved:", saved.name, saved.path.startsWith(dir2));
const sneaky = tools.saveText("../escape", "x");
console.log("traversal neutralised:", sneaky.path.startsWith(dir2), path.basename(sneaky.path));

fs.rmSync(dir1, { recursive: true, force: true });
fs.rmSync(dir2, { recursive: true, force: true });
console.log("OK");
