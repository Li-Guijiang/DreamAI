const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const WORKSPACE = process.env.DREAMAI_DEV_WORKSPACE;

(async () => {
  const browser = await puppeteer.connect({ browserURL: "http://127.0.0.1:9227", defaultViewport: null });
  const pages = await browser.pages();
  const page = pages.find((p) => p.url().includes("127.0.0.1:8787")) || pages[0];
  const errors = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));

  await page.bringToFront();
  await sleep(1500);
  console.log("shell:", await page.evaluate(() => ({
    bar: !document.querySelector("#desktopTitlebar").hidden,
    panel: !document.querySelector("#agentPanel").hidden,
  })));

  // window controls
  await page.click("#winMax");
  await sleep(600);
  console.log("maximized:", await page.evaluate(() => document.body.classList.contains("is-maximized")));
  await page.click("#winMax");
  await sleep(400);

  // doc mode + auto template
  await page.click("#modeBtn");
  await sleep(250);
  await page.click('#modeMenu .menu__item[data-mode="doc"]');
  await sleep(250);
  await page.click("#docTemplateBtn");
  await sleep(250);
  await page.click('#docTemplateMenu .menu__item[data-template="auto"]');
  await sleep(250);

  const prompts = [
    "生成一份产品发布会第一次筹备会的会议纪要，包含会议信息、讨论要点和待办事项表格",
    "用 Excel 生成一份 10 月内容排期表，包含日期、平台、主题、负责人、状态五列，至少 5 行数据",
    "生成一份 6 页的产品发布会 PPT，主题是 Dream AI 桌面版发布",
    "生成一份项目启动会会议纪要的 PDF 版本，包含目标、里程碑和风险",
  ];

  for (let index = 0; index < prompts.length; index += 1) {
    await page.click("#input");
    await page.type("#input", prompts[index]);
    await page.keyboard.press("Enter");
    console.log("sent", index + 1, "waiting…");
    await page.waitForFunction(
      (count) => document.querySelectorAll(".doc-result").length >= count,
      { timeout: 180000 },
      index + 1,
    );
    await sleep(900);
    const info = await page.evaluate((i) => {
      const card = document.querySelectorAll(".doc-result")[i];
      return {
        name: card?.querySelector(".doc-result__meta strong")?.textContent,
        meta: card?.querySelector(".doc-result__meta em")?.textContent,
      };
    }, index);
    console.log("done", index + 1, JSON.stringify(info));
  }

  const files = fs.readdirSync(path.join(WORKSPACE, "Dream AI 文档")).map((name) => {
    const full = path.join(WORKSPACE, "Dream AI 文档", name);
    const head = fs.readFileSync(full).subarray(0, 4).toString("hex");
    return { name, size: fs.statSync(full).size, head };
  });
  console.log("files:", JSON.stringify(files, null, 2));

  const artifacts = await page.evaluate(() => ({
    count: document.querySelector("#artifactCount")?.textContent,
    activity: document.querySelectorAll(".agent-event").length,
  }));
  console.log("artifacts:", JSON.stringify(artifacts));

  await page.screenshot({ path: "D:\\Users\\HI MATEBOOK 14\\Documents\\deepseek-harness\\default-workspace\\dreamai-web\\tools\\qa\\shots\\93-doc-real.png" });
  console.log("errors:", errors.length ? errors : "none");
  browser.disconnect();
})().catch((error) => {
  console.error("FAILED:", error.message);
  process.exit(1);
});
