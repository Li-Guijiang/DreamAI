"use strict";

/**
 * Coding agent backend for the Dream AI desktop app.
 *
 * Everything the agent does is confined to `<workspace>/Dream AI 项目/<project>`:
 *  - files are written only inside the project directory (path containment check)
 *  - commands run with the project as cwd, have a timeout and an output cap
 *  - unsafe commands require explicit approval; every command is appended to
 *    `dreamai-commands.log` inside the project for transparency
 *  - long-running dev servers are tracked so they can be read, stopped, and
 *    are killed when the app quits
 */

const fs = require("fs");
const path = require("path");
const { exec, spawn } = require("child_process");

const PROJECTS_DIR = "Dream AI 项目";
const MAX_OUTPUT = 60000;

const SAFE_PREFIXES = [
  "npm ", "npm.cmd ", "npx ", "pnpm ", "yarn ", "node ", "python ", "py ", "pip ", "pip3 ",
  "git ", "tsc ", "vite ",
];

const UNSAFE_PATTERNS = [
  /rm\s+(-\w+\s+)*\//i, /rm\s+-\w*r\w*f/i, /del\s+\/[sqf]/i, /rd\s+\/[sq]/i, /deltree/i,
  /format\s+[a-z]:/i, /shutdown/i, /taskkill/i, /reg\s+(add|delete|import)/i,
  /powershell/i, /mkfs/i, /chmod\s+777/i, /chown\s+-R/i, /wget\s/i, /curl\s/i,
  /git\s+(push|clone|pull)/i, /scp\s/i, /ssh\s/i, />\s*\/dev\//i,
];

const servers = new Map();
let serverSeq = 0;
let currentCommand = null;

function projectsRoot(workspace) {
  if (!workspace || !fs.existsSync(workspace)) throw new Error("请先选择工作文件夹");
  const dir = path.join(workspace, PROJECTS_DIR);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function sanitizeName(name) {
  return (
    String(name || "")
      .replace(/[\\/:*?"<>|]/g, "-")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 40)
      .toLowerCase() || "dream-project"
  );
}

function createProject(workspace, name) {
  const base = path.join(projectsRoot(workspace), sanitizeName(name));
  let root = base;
  let index = 2;
  while (fs.existsSync(root)) {
    root = `${base}-${index}`;
    index += 1;
  }
  fs.mkdirSync(root, { recursive: true });
  return { root, name: path.basename(root) };
}

function assertProject(workspace, root) {
  const base = projectsRoot(workspace);
  const abs = path.resolve(String(root || ""));
  if (abs !== base && !abs.startsWith(base + path.sep)) throw new Error("项目目录无效");
  return abs;
}

function insideProject(root, relative) {
  const abs = path.resolve(root, String(relative || "").replace(/^[\\/]+/, ""));
  if (abs !== root && !abs.startsWith(root + path.sep)) {
    throw new Error(`路径越界：${relative}`);
  }
  return abs;
}

function writeFiles(workspace, root, files) {
  const project = assertProject(workspace, root);
  const written = [];
  for (const file of files || []) {
    const relative = String(file.path || "").replace(/^[\\/]+/, "");
    if (!relative || path.isAbsolute(file.path)) continue;
    const target = insideProject(project, relative);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, String(file.content || ""), "utf8");
    written.push({ path: relative, size: Buffer.byteLength(String(file.content || "")) });
  }
  return { written };
}

function listDir(workspace, root, relative) {
  const project = assertProject(workspace, root);
  const dir = insideProject(project, relative || ".");
  if (!fs.existsSync(dir)) return { entries: [] };
  const entries = [];
  const walk = (current, depth) => {
    if (depth > 4) return;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (entry.name === "node_modules" || entry.name === ".git") continue;
      const full = path.join(current, entry.name);
      const rel = path.relative(project, full).split(path.sep).join("/");
      if (entry.isDirectory()) {
        entries.push({ path: rel, type: "dir" });
        walk(full, depth + 1);
      } else {
        entries.push({ path: rel, type: "file", size: fs.statSync(full).size });
      }
    }
  };
  walk(dir, 0);
  return { entries };
}

function readFile(workspace, root, relative, maxBytes = 80000) {
  const project = assertProject(workspace, root);
  const target = insideProject(project, relative);
  if (!fs.existsSync(target)) throw new Error("文件不存在");
  const stat = fs.statSync(target);
  const size = Math.min(stat.size, maxBytes);
  return { path: relative, content: fs.readFileSync(target, "utf8").slice(0, size), truncated: stat.size > maxBytes, size: stat.size };
}

function isSafe(cmd) {
  const text = String(cmd || "").trim();
  if (!text) return false;
  if (UNSAFE_PATTERNS.some((pattern) => pattern.test(text))) return false;
  return SAFE_PREFIXES.some((prefix) => text.startsWith(prefix));
}

function needsApproval(cmd, auto) {
  const text = String(cmd || "").trim();
  if (!text) return false;
  if (UNSAFE_PATTERNS.some((pattern) => pattern.test(text))) return true;
  if (auto) return false;
  return !SAFE_PREFIXES.some((prefix) => text.startsWith(prefix));
}

function logCommand(root, cmd) {
  try {
    const line = `${new Date().toISOString()}  ${cmd}\n`;
    fs.appendFileSync(path.join(root, "dreamai-commands.log"), line, "utf8");
  } catch {
    /* ignore */
  }
}

function tail(text) {
  const value = String(text || "");
  return value.length > MAX_OUTPUT ? value.slice(-MAX_OUTPUT) : value;
}

function runCommand(project, cmd, { timeoutMs = 180000, env = {} } = {}) {
  return new Promise((resolve) => {
    logCommand(project, cmd);
    const child = exec(
      cmd,
      {
        cwd: project,
        windowsHide: true,
        timeout: timeoutMs,
        maxBuffer: 4 * 1024 * 1024,
        env: { ...process.env, FORCE_COLOR: "0", NO_COLOR: "1", ...env },
      },
      (error, stdout, stderr) => {
        currentCommand = null;
        const code =
          error && typeof error.code === "number" ? error.code : error ? 1 : 0;
        resolve({
          code,
          killed: Boolean(error && (error.killed || error.signal)),
          stdout: tail(stdout),
          stderr: tail(stderr),
        });
      },
    );
    currentCommand = child;
  });
}

function startServer(project, cmd, { env = {} } = {}) {
  logCommand(project, cmd);
  const child = spawn(cmd, {
    cwd: project,
    shell: true,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, FORCE_COLOR: "0", NO_COLOR: "1", ...env },
  });
  const id = `server-${Date.now()}-${(serverSeq += 1)}`;
  const entry = { id, pid: child.pid, cmd, project, output: "", exited: false, code: null };
  const absorb = (data) => {
    entry.output = tail(entry.output + String(data || ""));
  };
  child.stdout.on("data", absorb);
  child.stderr.on("data", absorb);
  child.on("error", (error) => {
    entry.output = tail(`${entry.output}\n${error.message}`);
    entry.exited = true;
    entry.code = 1;
  });
  child.on("exit", (code) => {
    entry.exited = true;
    entry.code = code;
  });
  servers.set(id, entry);
  return { id, pid: child.pid };
}

function serverOutput(id) {
  const entry = servers.get(id);
  if (!entry) return { missing: true };
  return { id, output: entry.output, exited: entry.exited, code: entry.code, pid: entry.pid };
}

function stopServer(id) {
  const entry = servers.get(id);
  if (!entry) return { missing: true };
  try {
    spawn("taskkill", ["/PID", String(entry.pid), "/T", "/F"], { windowsHide: true, stdio: "ignore" });
  } catch {
    /* ignore */
  }
  entry.exited = true;
  return { ok: true };
}

function killCurrentCommand() {
  if (currentCommand) {
    try {
      exec(`taskkill /PID ${currentCommand.pid} /T /F`, { windowsHide: true, stdio: "ignore" });
    } catch {
      /* ignore */
    }
  }
}

function stopAll() {
  for (const id of [...servers.keys()]) stopServer(id);
  killCurrentCommand();
}

function todoScaffold(port) {
  const html = [
    "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
    "<title>待办清单</title><style>",
    "body{font-family:system-ui,'Microsoft YaHei',sans-serif;max-width:560px;margin:60px auto;padding:0 20px;background:#f7f9fd;color:#1b1f2a}",
    "h1{font-size:24px;margin:0 0 18px}",
    ".row{display:flex;gap:8px}.row input{flex:1;padding:10px 12px;border:1px solid #dde2ec;border-radius:8px;font-size:14px}",
    ".row button{padding:10px 16px;border:0;border-radius:8px;background:#4a6ef5;color:#fff;font-size:14px;cursor:pointer}",
    "ul{list-style:none;padding:0;margin:20px 0}li{display:flex;align-items:center;gap:10px;padding:12px;background:#fff;border:1px solid #eef1f7;border-radius:10px;margin-bottom:8px}",
    "li.done span{text-decoration:line-through;color:#9aa1af}li span{flex:1}li button{border:0;background:none;color:#9aa1af;cursor:pointer}",
    "</style></head><body><h1>待办清单</h1>",
    "<div class=\"row\"><input id=\"text\" placeholder=\"输入一个任务，回车添加\"><button id=\"add\">添加</button></div>",
    "<ul id=\"list\"></ul><script>",
    "const list=document.getElementById('list');",
    "async function load(){const r=await fetch('/api/tasks');const data=await r.json();list.innerHTML='';",
    "data.forEach(t=>{const li=document.createElement('li');if(t.done)li.className='done';",
    "li.innerHTML='<input type=\"checkbox\"'+(t.done?' checked':'')+'><span></span><button>删除</button>';",
    "li.querySelector('span').textContent=t.text;",
    "li.querySelector('input').onchange=()=>toggle(t.id);",
    "li.querySelector('button').onclick=()=>removeTask(t.id);list.appendChild(li);});}",
    "async function add(){const input=document.getElementById('text');const text=input.value.trim();if(!text)return;",
    "await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});input.value='';load();}",
    "async function toggle(id){await fetch('/api/tasks/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});load();}",
    "async function removeTask(id){await fetch('/api/tasks/'+id,{method:'DELETE'});load();}",
    "document.getElementById('add').onclick=add;",
    "document.getElementById('text').addEventListener('keydown',e=>{if(e.key==='Enter')add();});",
    "load();</script></body></html>",
  ].join("");
  const server = [
    "const http = require('http');",
    `const PORT = ${Number(port) || 3100};`,
    "let tasks = [{ id: 1, text: '试试添加一个任务', done: false }];",
    "let nextId = 2;",
    `const html = ${JSON.stringify(html)};`,
    "function json(res, code, data) { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(data)); }",
    "function body(req) { return new Promise((resolve) => { let raw = ''; req.on('data', (c) => (raw += c)); req.on('end', () => { try { resolve(JSON.parse(raw || '{}')); } catch { resolve({}); } }); }); }",
    "const server = http.createServer(async (req, res) => {",
    "  const url = new URL(req.url, 'http://localhost');",
    "  if (url.pathname === '/api/tasks' && req.method === 'GET') return json(res, 200, tasks);",
    "  if (url.pathname === '/api/tasks' && req.method === 'POST') { const data = await body(req); const text = String(data.text || '').trim(); if (!text) return json(res, 400, { error: 'empty' }); tasks.push({ id: nextId++, text, done: false }); return json(res, 201, tasks); }",
    "  if (url.pathname === '/api/tasks/toggle' && req.method === 'POST') { const data = await body(req); const task = tasks.find((t) => t.id === Number(data.id)); if (task) task.done = !task.done; return json(res, 200, tasks); }",
    "  if (url.pathname.startsWith('/api/tasks/') && req.method === 'DELETE') { const id = Number(url.pathname.split('/').pop()); tasks = tasks.filter((t) => t.id !== id); return json(res, 200, tasks); }",
    "  if (url.pathname === '/' || url.pathname === '/index.html') { res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); return res.end(html); }",
    "  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }); res.end('Not found');",
    "});",
    "server.listen(PORT, () => console.log('server listening on http://localhost:' + PORT));",
  ].join("\n");
  return [{ path: "server.js", content: server }];
}

function scaffoldFiles(kind, port) {
  if (kind === "todo") return todoScaffold(port);
  return [];
}

module.exports = {
  scaffoldFiles,
  PROJECTS_DIR,
  assertProject,
  createProject,
  insideProject,
  isSafe,
  killCurrentCommand,
  listDir,
  needsApproval,
  projectsRoot,
  readFile,
  runCommand,
  sanitizeName,
  serverOutput,
  startServer,
  stopAll,
  stopServer,
  writeFiles,
};
