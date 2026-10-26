const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

const SHOTS = path.join(__dirname, "shots");
const WORKSPACE = process.env.DREAMAI_DEV_WORKSPACE;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.connect({ browserURL: "http://127.0.0.1:9222", defaultViewport: null });
  const pages = await browser.pages();
  const page = pages.find((p) => p.url().includes("127.0.0.1:8787")) || pages[0];
  const errors = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));

  await page.bringToFront();
  await sleep(1500);

  const bridge = await page.evaluate(() => ({
    isDesktop: !!window.dreamDesktop?.isDesktop,
    version: window.dreamDesktop?.version ? "fn" : null,
  }));
  console.log("bridge:", JSON.stringify(bridge));

  await page.click("#desktopBtn");
  await sleep(600);
  const stats = await page.evaluate(() => ({
    path: document.querySelector("#deskPath").textContent,
    files: document.querySelector("#deskFiles").textContent,
    folders: document.querySelector("#deskFolders").textContent,
    size: document.querySelector("#deskSize").textContent,
  }));
  console.log("stats:", JSON.stringify(stats));

  await page.click("#deskOrganize");
  await sleep(600);
  const preview = await page.evaluate(() => document.querySelectorAll("#deskPreviewList li").length);
  console.log("preview rows:", preview);
  await page.screenshot({ path: path.join(SHOTS, "73-electron-preview.png") });

  await page.click("#deskApply");
  await sleep(1200);
  const toast = await page.evaluate(() => document.querySelector("#toasts").innerText.trim());
  console.log("toast:", JSON.stringify(toast));

  const folders = fs.readdirSync(WORKSPACE, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name);
  console.log("folders on disk:", folders);
  console.log("top-level files left:", fs.readdirSync(WORKSPACE).filter((n) => fs.statSync(path.join(WORKSPACE, n)).isFile()));

  await page.screenshot({ path: path.join(SHOTS, "74-electron-done.png") });
  console.log("errors:", errors.length ? errors : "none");

  browser.disconnect();
})().catch((error) => {
  console.error("E2E FAILED:", error.message);
  process.exit(1);
});
