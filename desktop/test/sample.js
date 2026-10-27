const path = require("path");
const fs = require("fs");
const docs = require("../electron/documents");
const workspace = path.join(__dirname, "..", "test-output");
fs.mkdirSync(workspace, { recursive: true });
(async () => {
  const deck = {
    type: "pptx",
    title: "Dream AI 桌面版发布",
    subtitle: "让每一个想法，都被认真对待",
    slides: [
      { title: "我们为什么做桌面版", bullets: ["网页很好，但文件都在电脑里", "用户不想在工具之间来回搬运", "AI 应该能直接交付成品，而不只是建议"], notes: "从真实办公场景切入" },
      { title: "三条产品主线", bullets: ["对话：随时问，随时写", "工作：把任务拆成步骤执行", "文档：直接生成 Word / Excel / PPT / PDF"], notes: "强调完整闭环" },
      { title: "本地文件工作台", bullets: ["按类型整理下载文件夹", "批量重命名，保留扩展名", "每次写入都要二次确认"], notes: "演示 4 个文件整理" },
      { title: "安全边界", bullets: ["只访问用户选择的文件夹", "不执行任意命令", "不读取其他位置的文件"], notes: "回应隐私顾虑" },
      { title: "发布节奏", bullets: ["10 月：Windows MVP", "11 月：模板与自动更新", "12 月：macOS 预览版"], notes: "给出现实时间表" },
    ],
  };
  const table = {
    type: "xlsx",
    title: "发布会筹备排期",
    sheets: [{
      name: "筹备排期",
      headers: ["日期", "事项", "负责人", "状态"],
      rows: [
        ["2026-10-27", "主视觉定稿", "设计负责人", "进行中"],
        ["2026-10-28", "媒体名单确认", "市场负责人", "未开始"],
        ["2026-10-30", "场地与设备联调", "行政负责人", "未开始"],
        ["2026-11-01", "全流程彩排", "项目负责人", "未开始"],
        ["2026-11-02", "正式发布", "全体", "未开始"],
      ],
      summary: ["合计", "5 项", "", ""],
    }],
  };
  for (const spec of [deck, table]) {
    const result = await docs.createDocument(spec, workspace);
    console.log(result.type, result.path, result.sizeLabel);
  }
})();