"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const docs = require("../electron/documents");

const workspace = fs.mkdtempSync(path.join(os.tmpdir(), "dreamai-docs-"));

const meeting = {
  type: "docx",
  title: "产品发布会筹备会议纪要",
  subtitle: "2026 年 10 月 · 第一次筹备会",
  sections: [
    { heading: "会议信息", paragraphs: ["时间：2026-10-24 14:00–15:00", "地点：3 号会议室", "参会：李贵江、市场组、设计组"] },
    { heading: "讨论要点", bullets: ["确认发布会主题为「把想法交给 Dream」", "主视觉沿用星球品牌", "开场视频控制在 90 秒内"] },
    {
      heading: "待办事项",
      table: {
        headers: ["事项", "负责人", "截止时间"],
        rows: [
          ["主视觉定稿", "设计组", "10-28"],
          ["媒体名单", "市场组", "10-30"],
          ["场地确认", "行政", "10-27"],
        ],
      },
    },
  ],
};

const table = {
  type: "xlsx",
  title: "10 月内容排期",
  sheets: [
    {
      name: "内容排期",
      headers: ["日期", "平台", "主题", "负责人", "状态"],
      rows: [
        ["10-27", "公众号", "发布会预告", "小杨", "进行中"],
        ["10-29", "视频号", "产品亮点", "小李", "待开始"],
        ["11-01", "全平台", "发布会直播", "团队", "待开始"],
      ],
      summary: ["合计", "3 条", "", "", ""],
    },
  ],
};

const deck = {
  type: "pptx",
  title: "Dream AI 产品发布会",
  subtitle: "让每一个想法，都被认真对待",
  slides: [
    { title: "我们看到了什么问题", bullets: ["信息过载，思考变浅", "工具很多，协作很少", "AI 很强，但不好用"], notes: "用三个真实场景开场" },
    { title: "Dream AI 的答案", bullets: ["一个会思考、能协作的智能体", "对话与工作双模式", "免费模型开箱即用"] },
    { title: "下一步", bullets: ["桌面端本地文件能力", "文档一键生成", "开放 API 与插件"] },
  ],
};

const md = {
  type: "md",
  title: "周报",
  sections: [{ heading: "本周完成", bullets: ["上线官网", "发布桌面端 MVP"] }],
};

(async () => {
  for (const spec of [meeting, table, deck, md]) {
    const result = await docs.createDocument(spec, workspace);
    const head = fs.readFileSync(result.path).subarray(0, 2).toString("hex");
    console.log(result.type, result.name, result.sizeLabel, "head:", head);
  }
  console.log("listed:", docs.listDocuments(workspace).map((d) => d.name));
  console.log("dir:", path.join(workspace, docs.DOC_DIR));
  fs.rmSync(workspace, { recursive: true, force: true });
})().catch((error) => {
  console.error("FAILED:", error.stack || error.message);
  process.exit(1);
});
