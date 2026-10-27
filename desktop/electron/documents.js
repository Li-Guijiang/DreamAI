"use strict";

/**
 * Document generation for the Dream AI desktop app.
 *
 * Everything is produced locally with pure-JS libraries (docx / exceljs /
 * pptxgenjs) so users do not need Microsoft Office installed. PDF is produced
 * by Electron's printToPDF from a styled HTML template (the `printPdf`
 * callback is injected by main.js).
 *
 * File creation is confined to `<workspace>/Dream AI 文档`.
 */

const fs = require("fs");
const path = require("path");
const {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  HeadingLevel,
  Packer,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
} = require("docx");
const ExcelJS = require("exceljs");
const pptxgen = require("pptxgenjs");

const DOC_DIR = "Dream AI 文档";
const BRAND = "4A6EF5";
const INK = "1B1F2A";
const MUTED = "6B7280";
const LINE = "DDE2EC";
const FONT = "Microsoft YaHei";

const TYPE_META = {
  docx: { ext: "docx", label: "Word 文档" },
  xlsx: { ext: "xlsx", label: "Excel 表格" },
  pptx: { ext: "pptx", label: "PowerPoint 演示" },
  pdf: { ext: "pdf", label: "PDF 文档" },
  md: { ext: "md", label: "Markdown 文档" },
};

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function sanitizeName(name, fallback = "Dream AI 文档") {
  const cleaned = String(name || "")
    .replace(/[\\/:*?"<>|]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 60);
  return cleaned || fallback;
}

function normalize(spec) {
  const type = TYPE_META[spec?.type] ? spec.type : "docx";
  const title = String(spec?.title || "未命名文档").slice(0, 80);
  const sections = Array.isArray(spec?.sections) ? spec.sections : [];
  const slides = Array.isArray(spec?.slides) ? spec.slides : [];
  const sheets = Array.isArray(spec?.sheets) ? spec.sheets : [];
  return {
    type,
    title,
    subtitle: String(spec?.subtitle || ""),
    author: String(spec?.author || "Dream AI"),
    filename: spec?.filename ? String(spec.filename) : "",
    sections: sections
      .filter((section) => section && (section.heading || section.paragraphs || section.bullets || section.table))
      .map((section) => ({
        heading: String(section.heading || ""),
        paragraphs: Array.isArray(section.paragraphs) ? section.paragraphs.map(String) : [],
        bullets: Array.isArray(section.bullets) ? section.bullets.map(String) : [],
        note: section.note ? String(section.note) : "",
        table: normalizeTable(section.table),
      })),
    slides: slides.map((slide) => ({
      title: String(slide.title || ""),
      subtitle: String(slide.subtitle || ""),
      bullets: Array.isArray(slide.bullets) ? slide.bullets.map(String) : [],
      notes: String(slide.notes || ""),
    })),
    sheets: sheets.map((sheet) => ({
      name: String(sheet.name || "Sheet1").slice(0, 28),
      headers: Array.isArray(sheet.headers) ? sheet.headers.map(String) : [],
      rows: Array.isArray(sheet.rows) ? sheet.rows.map((row) => (Array.isArray(row) ? row.map(String) : [])) : [],
      summary: Array.isArray(sheet.summary) ? sheet.summary.map(String) : [],
    })),
  };
}

function normalizeTable(table) {
  if (!table || !Array.isArray(table.headers)) return null;
  return {
    headers: table.headers.map(String),
    rows: Array.isArray(table.rows) ? table.rows.map((row) => (Array.isArray(row) ? row.map(String) : [])) : [],
  };
}

function ensureDocDir(workspace) {
  const dir = path.join(workspace, DOC_DIR);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function uniquePath(dir, base, ext) {
  let candidate = path.join(dir, `${base}.${ext}`);
  let index = 2;
  while (fs.existsSync(candidate)) {
    candidate = path.join(dir, `${base} (${index}).${ext}`);
    index += 1;
  }
  return candidate;
}

function today() {
  return new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" });
}

// ---------------------------------------------------------------------------
// Word
// ---------------------------------------------------------------------------

function docxTable(table) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
  const rows = [
    new TableRow({
      tableHeader: true,
      children: table.headers.map(
        (header) =>
          new TableCell({
            shading: { type: ShadingType.CLEAR, fill: "F1F4FB" },
            margins: { top: 90, bottom: 90, left: 120, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: header, bold: true, size: 20, color: INK })] })],
          }),
      ),
    }),
    ...table.rows.map(
      (row) =>
        new TableRow({
          children: row.map(
            (cell) =>
              new TableCell({
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun({ text: cell, size: 20, color: INK })] })],
              }),
          ),
        }),
    ),
  ];
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: border,
      bottom: border,
      left: border,
      right: border,
      insideHorizontal: border,
      insideVertical: border,
    },
    rows,
  });
}

async function buildDocx(doc) {
  const children = [
    new Paragraph({
      spacing: { after: 120 },
      children: [new TextRun({ text: doc.title, bold: true, size: 44, color: INK, font: FONT })],
    }),
  ];
  if (doc.subtitle) {
    children.push(
      new Paragraph({
        spacing: { after: 120 },
        children: [new TextRun({ text: doc.subtitle, size: 24, color: MUTED, font: FONT })],
      }),
    );
  }
  children.push(
    new Paragraph({
      spacing: { after: 360 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LINE } },
      children: [
        new TextRun({ text: `${doc.author}  ·  ${today()}`, size: 18, color: MUTED, font: FONT }),
      ],
    }),
  );

  for (const section of doc.sections) {
    if (section.heading) {
      children.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 320, after: 140 },
          children: [new TextRun({ text: section.heading, bold: true, size: 28, color: INK, font: FONT })],
        }),
      );
    }
    for (const paragraph of section.paragraphs) {
      children.push(
        new Paragraph({
          spacing: { after: 120, line: 340 },
          children: [new TextRun({ text: paragraph, size: 21, color: "333A46", font: FONT })],
        }),
      );
    }
    for (const bullet of section.bullets) {
      children.push(
        new Paragraph({
          bullet: { level: 0 },
          spacing: { after: 80, line: 320 },
          children: [new TextRun({ text: bullet, size: 21, color: "333A46", font: FONT })],
        }),
      );
    }
    if (section.table) {
      children.push(docxTable(section.table));
      children.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
    }
    if (section.note) {
      children.push(
        new Paragraph({
          spacing: { after: 160 },
          children: [new TextRun({ text: section.note, italics: true, size: 18, color: MUTED, font: FONT })],
        }),
      );
    }
  }

  const document = new Document({
    creator: doc.author,
    title: doc.title,
    styles: { default: { document: { run: { font: FONT, size: 21 } } } },
    sections: [
      {
        properties: { page: { margin: { top: 1000, bottom: 900, left: 1000, right: 1000 } } },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [
                  new TextRun({ text: "由 Dream AI 生成  ·  liguijiang.com", size: 16, color: "9AA1AF", font: FONT }),
                ],
              }),
            ],
          }),
        },
        children,
      },
    ],
  });
  return Packer.toBuffer(document);
}

// ---------------------------------------------------------------------------
// Excel
// ---------------------------------------------------------------------------

async function buildXlsx(doc) {
  const workbook = new ExcelJS.Workbook();
  workbook.creator = doc.author;
  workbook.created = new Date();

  let sheets = doc.sheets.filter((sheet) => sheet.headers.length);
  if (!sheets.length) {
    const tables = doc.sections.filter((section) => section.table);
    sheets = tables.map((section, index) => ({
      name: section.heading || `Sheet${index + 1}`,
      headers: section.table.headers,
      rows: section.table.rows,
      summary: [],
    }));
  }
  if (!sheets.length) {
    sheets = [{ name: "Sheet1", headers: ["项目", "内容"], rows: [["标题", doc.title]], summary: [] }];
  }

  sheets.forEach((sheet, sheetIndex) => {
    const name = sanitizeName(sheet.name, `Sheet${sheetIndex + 1}`).slice(0, 28);
    const worksheet = workbook.addWorksheet(name, { views: [{ state: "frozen", ySplit: 1 }] });
    worksheet.columns = sheet.headers.map((header, index) => {
      const lengths = [String(header).length, ...sheet.rows.map((row) => String(row[index] ?? "").length)];
      const width = Math.min(46, Math.max(12, Math.max(...lengths) * 2 + 6));
      return { header, key: header, width };
    });

    sheet.rows.forEach((row) => {
      const values = {};
      sheet.headers.forEach((header, index) => {
        values[header] = row[index] ?? "";
      });
      worksheet.addRow(values);
    });

    const headerRow = worksheet.getRow(1);
    headerRow.height = 26;
    headerRow.font = { bold: true, color: { argb: "FFFFFFFF" }, size: 11, name: FONT };
    headerRow.fill = { type: "pattern", pattern: "solid", fgColor: { argb: `FF${BRAND}` } };
    headerRow.alignment = { vertical: "middle", horizontal: "center" };

    worksheet.eachRow((row, number) => {
      row.eachCell((cell) => {
        cell.border = {
          top: { style: "thin", color: { argb: "FFEDF0F6" } },
          bottom: { style: "thin", color: { argb: "FFEDF0F6" } },
          left: { style: "thin", color: { argb: "FFEDF0F6" } },
          right: { style: "thin", color: { argb: "FFEDF0F6" } },
        };
      });
      if (number === 1) return;
      row.height = 24;
      row.font = { size: 10.5, name: FONT, color: { argb: `FF${INK}` } };
      row.alignment = { vertical: "middle", wrapText: true };
      if (number % 2 === 0) {
        row.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF7F9FD" } };
      }
    });

    if (sheet.summary.length) {
      const row = worksheet.addRow(sheet.summary);
      row.font = { bold: true, size: 10.5, name: FONT };
      row.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFEDF1FA" } };
    }

    worksheet.autoFilter = {
      from: { row: 1, column: 1 },
      to: { row: 1, column: sheet.headers.length },
    };
  });

  return workbook.xlsx.writeBuffer();
}

// ---------------------------------------------------------------------------
// PowerPoint
// ---------------------------------------------------------------------------

function slidesFromSections(doc) {
  return doc.sections.map((section) => ({
    title: section.heading || doc.title,
    bullets: [...section.paragraphs, ...section.bullets].slice(0, 6),
    notes: section.note || "",
  }));
}

async function buildPptx(doc) {
  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = doc.author;
  pptx.company = "Dream AI";
  pptx.subject = doc.title;
  pptx.title = doc.title;
  pptx.theme = { headFontFace: FONT, bodyFontFace: FONT, lang: "zh-CN" };

  const cover = pptx.addSlide();
  cover.background = { color: "08090D" };
  cover.addShape(pptx.ShapeType.ellipse, {
    x: 8.3, y: -1.9, w: 5.8, h: 5.8,
    fill: { color: BRAND, transparency: 88 },
    line: { color: BRAND, transparency: 100 },
  });
  cover.addShape(pptx.ShapeType.ellipse, {
    x: 9.6, y: 4.4, w: 3.6, h: 3.6,
    fill: { color: "B79CFF", transparency: 90 },
    line: { color: "B79CFF", transparency: 100 },
  });
  cover.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: BRAND } });
  cover.addText("DREAM AI", {
    x: 0.9, y: 1.5, w: 6, h: 0.4, fontSize: 12, color: "7C9CFF", charSpacing: 4, bold: true,
  });
  cover.addText(doc.title, {
    x: 0.9, y: 2.1, w: 11.2, h: 2.0, fontSize: 40, bold: true, color: "FFFFFF", breakLine: false,
  });
  if (doc.subtitle) {
    cover.addText(doc.subtitle, { x: 0.9, y: 4.1, w: 10.5, h: 0.8, fontSize: 18, color: "B6BCCC" });
  }
  cover.addText(`${doc.author}  ·  ${today()}`, {
    x: 0.9, y: 6.4, w: 8, h: 0.4, fontSize: 12, color: "8A92A6",
  });

  const slides = doc.slides.length ? doc.slides : slidesFromSections(doc);
  slides.forEach((slide, index) => {
    const page = pptx.addSlide();
    page.background = { color: "FFFFFF" };
    page.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.14, h: 7.5, fill: { color: BRAND } });
    page.addShape(pptx.ShapeType.roundRect, {
      x: 0.8, y: slide.subtitle ? 2.15 : 1.75, w: 11.55, h: 4.65,
      fill: { color: "F7F9FD" }, line: { color: "EEF1F7" }, rectRadius: 0.06,
    });
    page.addText("DREAM AI", {
      x: 9.9, y: 0.52, w: 2.2, h: 0.3, fontSize: 9, color: "A3A9B7", align: "right", charSpacing: 3, bold: true,
    });
    page.addText(slide.title, {
      x: 0.8, y: 0.65, w: 8.8, h: 0.9, fontSize: 26, bold: true, color: "1B1F2A",
    });
    page.addShape(pptx.ShapeType.rect, {
      x: 0.82, y: 1.5, w: 1.1, h: 0.06, fill: { color: BRAND },
    });
    if (slide.subtitle) {
      page.addText(slide.subtitle, { x: 0.8, y: 1.7, w: 11, h: 0.5, fontSize: 14, color: "6B7280" });
    }
    if (slide.bullets.length) {
      page.addText(
        slide.bullets.map((text) => ({ text, options: { bullet: { indent: 18 }, breakLine: true } })),
        {
          x: 1.12, y: slide.subtitle ? 2.42 : 2.02, w: 10.9, h: 4.1,
          fontSize: 18, color: "333A46", lineSpacingMultiple: 1.45, valign: "middle",
        },
      );
    }
    page.addShape(pptx.ShapeType.rect, {
      x: 0.82, y: 6.92, w: 11.6, h: 0.012, fill: { color: "E5E8F0" },
    });
    page.addText("Dream AI  ·  2026", {
      x: 0.82, y: 7.0, w: 5, h: 0.3, fontSize: 9, color: "A3A9B7",
    });
    page.addText(`${index + 1} / ${slides.length}`, {
      x: 11.6, y: 7.0, w: 1, h: 0.3, fontSize: 9, color: "A3A9B7", align: "right",
    });
    if (slide.notes) page.addNotes(slide.notes);
  });

  return pptx.write({ outputType: "nodebuffer" });
}

// ---------------------------------------------------------------------------
// Markdown / PDF
// ---------------------------------------------------------------------------

function buildMarkdown(doc) {
  const lines = [`# ${doc.title}`, ""];
  if (doc.subtitle) lines.push(`> ${doc.subtitle}`, "");
  lines.push(`${doc.author} · ${today()}`, "");
  for (const section of doc.sections) {
    if (section.heading) lines.push(`## ${section.heading}`, "");
    section.paragraphs.forEach((paragraph) => lines.push(paragraph, ""));
    section.bullets.forEach((bullet) => lines.push(`- ${bullet}`));
    if (section.bullets.length) lines.push("");
    if (section.table) {
      lines.push(`| ${section.table.headers.join(" | ")} |`);
      lines.push(`| ${section.table.headers.map(() => "---").join(" | ")} |`);
      section.table.rows.forEach((row) => lines.push(`| ${row.join(" | ")} |`));
      lines.push("");
    }
    if (section.note) lines.push(`_${section.note}_`, "");
  }
  for (const slide of doc.slides) {
    lines.push(`## ${slide.title}`, "");
    slide.bullets.forEach((bullet) => lines.push(`- ${bullet}`));
    lines.push("");
  }
  lines.push("---", "", "由 Dream AI 生成 · liguijiang.com");
  return lines.join("\n");
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildPdfHtml(doc) {
  const sections = doc.sections
    .map((section) => {
      const heading = section.heading ? `<h2>${escapeHtml(section.heading)}</h2>` : "";
      const paragraphs = section.paragraphs.map((p) => `<p>${escapeHtml(p)}</p>`).join("");
      const bullets = section.bullets.length
        ? `<ul>${section.bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>`
        : "";
      const table = section.table
        ? `<table><thead><tr>${section.table.headers
            .map((h) => `<th>${escapeHtml(h)}</th>`)
            .join("")}</tr></thead><tbody>${section.table.rows
            .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
            .join("")}</tbody></table>`
        : "";
      const note = section.note ? `<p class="note">${escapeHtml(section.note)}</p>` : "";
      return `<section>${heading}${paragraphs}${bullets}${table}${note}</section>`;
    })
    .join("");

  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>
    @page { size: A4; margin: 18mm 16mm; }
    body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #1b1f2a; font-size: 11pt; line-height: 1.75; }
    header { border-bottom: 2px solid #4a6ef5; padding-bottom: 14px; margin-bottom: 24px; }
    h1 { font-size: 24pt; margin: 0 0 6px; }
    .subtitle { color: #6b7280; font-size: 12pt; margin: 0 0 10px; }
    .meta { color: #9aa1af; font-size: 9pt; }
    h2 { font-size: 14pt; margin: 22px 0 8px; padding-left: 10px; border-left: 3px solid #4a6ef5; }
    p { margin: 6px 0; }
    ul { margin: 6px 0; padding-left: 22px; }
    li { margin: 3px 0; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9.5pt; }
    th { background: #f1f4fb; text-align: left; }
    th, td { border: 1px solid #dde2ec; padding: 6px 8px; }
    .note { color: #6b7280; font-size: 9pt; font-style: italic; }
    footer { margin-top: 28px; color: #9aa1af; font-size: 8.5pt; text-align: center; }
  </style></head><body>
    <header>
      <h1>${escapeHtml(doc.title)}</h1>
      ${doc.subtitle ? `<p class="subtitle">${escapeHtml(doc.subtitle)}</p>` : ""}
      <p class="meta">${escapeHtml(doc.author)} · ${escapeHtml(today())}</p>
    </header>
    ${sections}
    <footer>由 Dream AI 生成 · liguijiang.com</footer>
  </body></html>`;
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

async function createDocument(spec, workspace, options = {}) {
  if (!workspace || !fs.existsSync(workspace)) throw new Error("请先选择工作文件夹");
  const doc = normalize(spec);
  const meta = TYPE_META[doc.type];
  const dir = ensureDocDir(workspace);
  const base = sanitizeName(doc.filename || doc.title);
  const target = uniquePath(dir, base, meta.ext);

  if (doc.type === "docx") {
    fs.writeFileSync(target, await buildDocx(doc));
  } else if (doc.type === "xlsx") {
    fs.writeFileSync(target, Buffer.from(await buildXlsx(doc)));
  } else if (doc.type === "pptx") {
    fs.writeFileSync(target, Buffer.from(await buildPptx(doc)));
  } else if (doc.type === "md") {
    fs.writeFileSync(target, buildMarkdown(doc), "utf8");
  } else if (doc.type === "pdf") {
    if (typeof options.printPdf !== "function") throw new Error("PDF 渲染器未初始化");
    await options.printPdf(buildPdfHtml(doc), target);
  }

  const stat = fs.statSync(target);
  return {
    path: target,
    name: path.basename(target),
    dir,
    type: doc.type,
    typeLabel: meta.label,
    size: stat.size,
    sizeLabel: formatBytes(stat.size),
    title: doc.title,
  };
}

function listDocuments(workspace) {
  if (!workspace || !fs.existsSync(workspace)) return [];
  const dir = path.join(workspace, DOC_DIR);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && !entry.name.startsWith("."))
    .map((entry) => {
      const full = path.join(dir, entry.name);
      const stat = fs.statSync(full);
      const ext = path.extname(entry.name).slice(1).toLowerCase();
      return {
        path: full,
        name: entry.name,
        type: ext,
        typeLabel: TYPE_META[ext]?.label || ext.toUpperCase(),
        size: stat.size,
        sizeLabel: formatBytes(stat.size),
        mtime: stat.mtimeMs,
      };
    })
    .sort((a, b) => b.mtime - a.mtime)
    .slice(0, 50);
}

module.exports = {
  DOC_DIR,
  TYPE_META,
  createDocument,
  listDocuments,
  formatBytes,
  buildMarkdown,
};
