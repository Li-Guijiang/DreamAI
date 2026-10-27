const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const WORKSPACE = process.env.DREAMAI_DEV_WORKSPACE;

(async () => {
  const browser = await puppeteer.connect({
    browserURL: "http://127.0.0.1:9235",
    defaultViewport: null,
    protocolTimeout: 900000,
  });
  const pages = await browser.pages();
  const page = pages.find((p) => p.url().includes("127.0.0.1:8787")) || pages[0];
  const errors = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));

  await page.bringToFront();
  await sleep(1200);
  await page.click("#modeBtn");
  await sleep(250);
  await page.click('#modeMenu .menu__item[data-mode="code"]');
  await sleep(250);

  const prompt = "写一个零依赖的待办清单小程序：只写一个 server.js，内嵌 HTML/CSS/JS 前端页面，提供 GET /api/tasks 和 POST /api/tasks，端口 3100，页面能添加任务和勾选完成";
  for (let i = 0; i < 3; i += 1) {
    await page.click("#input");
    await page.type("#input", prompt);
    if ((await page.evaluate(() => document.querySelector("#input").value)).length > 10) break;
    await sleep(400);
  }
  await page.keyboard.press("Enter");
  console.log("sent, waiting…");
  const t0 = Date.now();
  await page.waitForFunction(
    () => document.querySelector(".code-card .code-dot.is-done, .code-card .msg__error, .code-dot.is-error"),
    { timeout: 720000 },
  );
  await sleep(1200);
  const info = await page.evaluate(() => ({
    title: document.querySelector(".code-card__head strong")?.textContent,
    status: document.querySelector(".code-card__head em")?.textContent,
    meta: document.querySelector(".code-card__meta")?.innerText.replace(/\s+/g, " "),
    files: [...document.querySelectorAll(".code-tree li")].map((n) => n.innerText),
    logTail: document.querySelector(".code-log")?.textContent.slice(-400),
    error: document.querySelector(".code-card .msg__error")?.textContent,
    actions: [...document.querySelectorAll(".code-card__actions .btn")].map((b) => b.textContent),
  }));
  console.log("elapsed", Math.round((Date.now() - t0) / 1000) + "s");
  console.log(JSON.stringify(info, null, 2));
  await page.screenshot({ path: "D:\\Users\\HI MATEBOOK 14\\Documents\\deepseek-harness\\default-workspace\\dreamai-web\\tools\\qa\\shots\\111-code-real.png" });
  console.log("errors:", errors.length ? errors.slice(0, 5) : "none");

  // disk check
  const root = fs.existsSync(WORKSPACE) ? fs.readdirSync(WORKSPACE) : [];
  console.log("workspace:", root);
  const projects = path.join(WORKSPACE, "Dream AI 项目");
  if (fs.existsSync(projects)) {
    const name = fs.readdirSync(projects)[0];
    const project = path.join(projects, name);
    console.log("project files:", fs.readdirSync(project));
    console.log("node_modules exists:", fs.existsSync(path.join(project, "node_modules")));
  }

  // server check
  try {
    const res = await fetch("http://127.0.0.1:3100/api/tasks");
    console.log("GET /api/tasks:", res.status, (await res.text()).slice(0, 80));
  } catch (e) {
    console.log("server not reachable:", e.message);
  }

  // stop button
  const stopped = await page.evaluate(() => {
    const btn = [...document.querySelectorAll(".code-card__actions .btn")].find((b) => b.textContent === "停止服务");
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  });
  console.log("stop clicked:", stopped);
  await sleep(2500);
  try {
    await fetch("http://127.0.0.1:3100/api/tasks", { signal: AbortSignal.timeout(2000) });
    console.log("server still up (unexpected)");
  } catch {
    console.log("server stopped OK");
  }
  browser.disconnect();
})().catch((e) => {
  console.error("FAILED", e.message);
  process.exit(1);
});
