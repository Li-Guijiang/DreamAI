/* Dream AI — web client 1.1
   Vanilla ES2020. Conversations live in the browser; only model requests
   leave the device, and they go through our own API. */

(() => {
  "use strict";

  const STORE_SESSIONS = "dreamai.sessions.v1";
  const STORE_SETTINGS = "dreamai.settings.v1";
  const STORE_USER_KEY = "dreamai.userkey.v1";
  const MAX_INPUT = 12000;
  const MAX_FILES = 3;
  const MAX_FILE_CHARS = 20000;
  const MAX_TOTAL_ATTACH = 60000;

  const MODES = [
    { id: "chat", label: "对话", desc: "直接问答，适合写作、编程、闲聊" },
    { id: "work", label: "工作", desc: "拆解任务，逐步执行并汇总（更慢）" },
    { id: "doc", label: "文档", desc: "生成 Word / Excel / PPT / PDF / Markdown" },
    { id: "code", label: "编程", desc: "直接在电脑上写代码、装依赖、把项目跑起来" },
  ];

  const DOC_TEMPLATES = [
    { id: "auto", label: "自动", prompt: "" },
    {
      id: "meeting",
      label: "会议纪要",
      prompt: "使用会议纪要结构：会议信息、讨论要点、结论、待办事项（表格，含负责人与截止时间）。",
    },
    {
      id: "proposal",
      label: "项目方案",
      prompt: "使用项目方案结构：背景与目标、方案概述、实施计划（表格）、资源与预算、风险与应对。",
    },
    {
      id: "weekly",
      label: "周报",
      prompt: "使用周报结构：本周完成、关键进展与数据、问题与风险、下周计划。",
    },
    {
      id: "resume",
      label: "简历",
      prompt: "使用简历结构：个人信息、教育背景、工作/项目经历（以成果量化）、技能、自我评价。",
    },
    {
      id: "table",
      label: "数据表格",
      prompt: "输出 xlsx，包含合理表头、5–15 行具体数据、汇总行，并设置合适列宽。",
    },
    {
      id: "slides",
      label: "演示大纲",
      prompt: "输出 pptx，包含封面与 5–8 页内容，每页 3–5 个要点，备注中写讲稿提示。",
    },
  ];

  const STYLES = [
    { id: "default", label: "通用", desc: "平衡、自然的表达" },
    { id: "precise", label: "严谨", desc: "结论先行，重视依据" },
    { id: "creative", label: "创意", desc: "更发散，更有想象力" },
    { id: "concise", label: "精简", desc: "能一句话说清就不写两行" },
  ];

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const uid = () =>
    crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2);
  const now = () => Date.now();
  const isMobile = () => window.matchMedia("(max-width: 900px)").matches;

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "html") node.innerHTML = value;
      else if (key.startsWith("on") && typeof value === "function") {
        node.addEventListener(key.slice(2).toLowerCase(), value);
      } else node.setAttribute(key, value === true ? "" : String(value));
    }
    for (const child of [].concat(children)) {
      if (child === null || child === undefined) continue;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    }
    return node;
  }

  const ICONS = {
    chat: '<path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v7a2.5 2.5 0 0 1-2.5 2.5H9l-4 3.5v-3.5H6.5A2.5 2.5 0 0 1 4 13.5Z"/>',
    more: '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>',
    trash: '<path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13M10 11v6M14 11v6"/>',
    copy: '<rect x="9" y="9" width="11" height="11" rx="2.2"/><path d="M6 15H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v1"/>',
    check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    refresh: '<path d="M20 11a8 8 0 1 0-2.3 6.3"/><path d="M20 5v6h-6"/>',
    arrow: '<path d="M7 17 17 7M9 7h8v8"/>',
    edit: '<path d="M4 20h4L19 9a2.5 2.5 0 0 0-3.5-3.5L4 16.5V20Z"/><path d="M13.5 6.5 17.5 10.5"/>',
    download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"/><path d="M14 3v5h5"/>',
    open: '<path d="M14 4h6v6"/><path d="M20 4 11 13"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  };

  function icon(name, cls = "") {
    const span = document.createElement("span");
    span.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true" class="${cls}" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;
    return span.firstElementChild;
  }

  function toast(message, kind = "ok") {
    const host = $("#toasts");
    if (!host) return;
    const node = el("div", { class: `toast${kind === "err" ? " toast--err" : ""}` }, [
      el("i"),
      el("span", { text: message }),
    ]);
    host.appendChild(node);
    setTimeout(() => {
      node.classList.add("is-out");
      setTimeout(() => node.remove(), 220);
    }, 2400);
  }

  // ---------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------

  const state = {
    config: null,
    sessions: [],
    activeId: null,
    settings: {
      theme: "dark",
      size: "md",
      model: null,
      provider: "free",
      temperature: 0.7,
      thinking: false,
      style: "default",
      mode: "chat",
      docTemplate: "auto",
    },
    userKey: "",
    attachments: [],
    search: "",
    streaming: false,
    follow: true,
    abort: null,
  };

  function loadStorage() {
    try {
      const raw = localStorage.getItem(STORE_SESSIONS);
      const data = raw ? JSON.parse(raw) : [];
      state.sessions = Array.isArray(data) ? data.filter((s) => s && s.id && Array.isArray(s.messages)) : [];
    } catch {
      state.sessions = [];
    }
    try {
      const raw = localStorage.getItem(STORE_SETTINGS);
      if (raw) Object.assign(state.settings, JSON.parse(raw));
    } catch {
      /* ignore */
    }
    try {
      state.userKey = localStorage.getItem(STORE_USER_KEY) || "";
    } catch {
      state.userKey = "";
    }
    if (!["dark", "light", "system"].includes(state.settings.theme)) state.settings.theme = "dark";
    if (!["sm", "md", "lg"].includes(state.settings.size)) state.settings.size = "md";
    if (!["free", "byok"].includes(state.settings.provider)) state.settings.provider = "free";
    if (!["chat", "work", "doc"].includes(state.settings.mode)) state.settings.mode = "chat";
    if (!DOC_TEMPLATES.some((t) => t.id === state.settings.docTemplate)) state.settings.docTemplate = "auto";
    if (!STYLES.some((s) => s.id === state.settings.style)) state.settings.style = "default";
    state.sessions.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  }

  let saveTimer = null;
  function persistSessions() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try {
        const slim = state.sessions.slice(0, 120).map((s) => ({
          id: s.id,
          title: s.title,
          createdAt: s.createdAt,
          updatedAt: s.updatedAt,
          messages: s.messages.map((m) => ({
            role: m.role,
            kind: m.kind || undefined,
            content: m.content,
            reasoning: m.reasoning || "",
            attachments: m.attachments || undefined,
            title: m.title || undefined,
            steps: m.steps || undefined,
            final: m.final || undefined,
            status: m.status || undefined,
            error: m.error || undefined,
            model: m.model || "",
            provider: m.provider || undefined,
            document: m.document || undefined,
            project: m.project || undefined,
            files: m.files ? m.files.slice(0, 80) : undefined,
            log: m.log ? m.log.slice(-8000) : undefined,
            serverId: m.serverId || undefined,
            url: m.url || undefined,
            running: m.running || undefined,
            ts: m.ts,
          })),
        }));
        localStorage.setItem(STORE_SESSIONS, JSON.stringify(slim));
      } catch {
        toast("本地存储空间不足，历史记录可能无法保存", "err");
      }
    }, 220);
  }

  function persistSettings() {
    try {
      localStorage.setItem(STORE_SETTINGS, JSON.stringify(state.settings));
    } catch {
      /* ignore */
    }
  }

  const activeSession = () => state.sessions.find((s) => s.id === state.activeId) || null;

  function createSession() {
    const session = { id: uid(), title: "新对话", createdAt: now(), updatedAt: now(), messages: [] };
    state.sessions.unshift(session);
    state.activeId = session.id;
    persistSessions();
    return session;
  }

  // ---------------------------------------------------------------------
  // Theme & size
  // ---------------------------------------------------------------------

  const systemLight = () => window.matchMedia("(prefers-color-scheme: light)").matches;

  function resolvedTheme() {
    return state.settings.theme === "system" ? (systemLight() ? "light" : "dark") : state.settings.theme;
  }

  function applyTheme() {
    const theme = resolvedTheme();
    document.documentElement.dataset.theme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#08090d" : "#f7f6f2");
    $$("#themeSeg button").forEach((btn) => {
      btn.setAttribute("aria-checked", String(btn.dataset.themeValue === state.settings.theme));
    });
  }

  function applySize() {
    document.documentElement.dataset.size = state.settings.size;
    $$("#sizeSeg button").forEach((btn) => {
      btn.setAttribute("aria-checked", String(btn.dataset.sizeValue === state.settings.size));
    });
  }

  function initTheme() {
    applyTheme();
    applySize();
    window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
      if (state.settings.theme === "system") applyTheme();
    });
  }

  function setGreeting() {
    const hour = new Date().getHours();
    const greeting =
      hour < 6 ? "夜深了" : hour < 11 ? "早上好" : hour < 14 ? "中午好" : hour < 18 ? "下午好" : "晚上好";
    const node = $("#greetingText");
    if (node) node.textContent = greeting;
  }

  // ---------------------------------------------------------------------
  // Markdown
  // ---------------------------------------------------------------------

  marked.setOptions({ gfm: true, breaks: true });

  const ALLOWED_TAGS = [
    "p", "br", "strong", "em", "del", "code", "pre", "blockquote", "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "a", "table", "thead", "tbody", "tr", "th", "td", "span",
  ];

  function markdown(text) {
    const raw = marked.parse(text || "");
    return DOMPurify.sanitize(raw, {
      ALLOWED_TAGS,
      ALLOWED_ATTR: ["href", "title", "class", "target", "rel"],
      FORBID_TAGS: ["style", "iframe", "form", "input", "button", "script"],
    });
  }

  function decorate(container) {
    if (window.Prism) {
      try {
        Prism.highlightAllUnder(container);
      } catch {
        /* optional */
      }
    }
    $$("pre > code", container).forEach((code) => {
      const pre = code.parentElement;
      if (!pre || pre.closest(".code-block")) return;
      const match = /language-([\w-]+)/.exec(code.className || "");
      const lang = match ? match[1] : "text";
      const block = el("div", { class: "code-block" });
      const head = el("div", { class: "code-block__head" }, [
        el("span", { text: lang }),
        el("button", { class: "code-block__copy", type: "button" }, [
          icon("copy"),
          el("span", { text: "复制" }),
        ]),
      ]);
      pre.replaceWith(block);
      block.append(head, pre);
      head.querySelector("button").addEventListener("click", async (event) => {
        const btn = event.currentTarget;
        await copyText(code.textContent || "");
        btn.querySelector("span").textContent = "已复制";
        setTimeout(() => (btn.querySelector("span").textContent = "复制"), 1500);
      });
    });
    $$("a", container).forEach((a) => {
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    });
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const area = el("textarea");
      area.style.position = "fixed";
      area.style.opacity = "0";
      area.value = text;
      document.body.appendChild(area);
      area.select();
      try {
        document.execCommand("copy");
      } catch {
        /* ignore */
      }
      area.remove();
      return false;
    }
  }

  // ---------------------------------------------------------------------
  // Sidebar
  // ---------------------------------------------------------------------

  function groupLabel(ts) {
    const startOfToday = new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate()).getTime();
    const day = 86400000;
    if (ts >= startOfToday) return "今天";
    if (ts >= startOfToday - day) return "昨天";
    if (ts >= startOfToday - 7 * day) return "最近 7 天";
    return "更早";
  }

  function renderSidebar() {
    const host = $("#sessionList");
    host.textContent = "";
    const query = state.search.trim().toLowerCase();
    const list = state.sessions.filter((s) => {
      if (!query) return true;
      return (
        (s.title || "").toLowerCase().includes(query) ||
        s.messages.some((m) => (m.content || "").toLowerCase().includes(query))
      );
    });

    if (!list.length) {
      host.appendChild(
        el("div", { class: "sessions__empty" }, [
          query ? "没有找到相关对话" : "还没有对话\n从下方输入框，或首页灵感卡片开始",
        ]),
      );
      return;
    }

    let lastGroup = "";
    for (const session of list) {
      const label = groupLabel(session.updatedAt || session.createdAt);
      if (label !== lastGroup) {
        host.appendChild(el("div", { class: "sessions__group", text: label }));
        lastGroup = label;
      }
      const item = el("div", {
        class: `session${session.id === state.activeId ? " is-active" : ""}`,
        role: "button",
        tabindex: "0",
        "data-id": session.id,
      }, [
        icon("chat", "session__icon"),
        el("span", { class: "session__title", text: session.title || "新对话" }),
        el("button", { class: "session__more", type: "button", "aria-label": "对话操作" }, [icon("more")]),
      ]);

      const pick = () => {
        if (state.streaming) {
          toast("正在生成中，请先停止当前回答", "err");
          return;
        }
        state.activeId = session.id;
        renderSidebar();
        renderChat();
        closeSidebar();
      };
      item.addEventListener("click", pick);
      item.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          pick();
        }
      });
      const more = item.querySelector(".session__more");
      more.addEventListener("click", (event) => {
        event.stopPropagation();
        openSessionMenu(session, more);
      });
      host.appendChild(item);
    }
  }

  function removeSession(id) {
    const index = state.sessions.findIndex((s) => s.id === id);
    if (index < 0) return;
    state.sessions.splice(index, 1);
    if (state.activeId === id) state.activeId = state.sessions[0]?.id || null;
    persistSessions();
    renderSidebar();
    renderChat();
    toast("对话已删除");
  }

  // ---------------------------------------------------------------------
  // Chat rendering
  // ---------------------------------------------------------------------

  function timeLabel(ts) {
    if (!ts) return "";
    return new Date(ts).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }

  function modelLabel(id, provider = null) {
    const found = modelOption(id, provider) || modelOption(id);
    return found ? found.label : id || "Dream AI";
  }

  function actionBtn(iconName, label, onClick, extraClass = "") {
    const btn = el("button", { class: `act ${extraClass}`.trim(), type: "button", title: label }, [
      icon(iconName),
      el("span", { text: label }),
    ]);
    btn.addEventListener("click", onClick);
    return btn;
  }

  function filesRow(files) {
    const row = el("div", { class: "msg__files" });
    files.forEach((file) => {
      row.appendChild(el("span", { class: "file-chip" }, [icon("file"), el("span", { text: file.name })]));
    });
    return row;
  }

  function composeUserContent(message) {
    let content = message.content || "";
    if (message.attachments && message.attachments.length) {
      const blocks = message.attachments.map(
        (file) => `【附件：${file.name}】\n${file.text}\n【附件结束】`,
      );
      content = (content ? content + "\n\n" : "") + blocks.join("\n\n");
    }
    return content.trim();
  }

  function thinkingNode(text, streaming) {
    const details = el("details", { class: "think" });
    if (streaming) details.open = true;
    const summary = el("summary", { class: "think__summary" }, [
      el("span", { html: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>' }),
      el("span", { text: streaming ? "深度思考中…" : "思考过程" }),
    ]);
    const body = el("div", { class: "think__text", text });
    details.append(summary, body);
    return details;
  }

  function messageNode(message, index) {
    if (message.kind === "work") return workMessageNode(message, index);
    if (message.kind === "doc") return docMessageNode(message, index);
    if (message.kind === "code") return codeMessageNode(message, index);
    const isUser = message.role === "user";
    const wrap = el("div", { class: `msg msg--${isUser ? "user" : "assistant"}`, "data-index": String(index) });

    if (isUser) {
      const main = el("div", { class: "msg__main" });
      if (message.content) main.appendChild(el("div", { class: "msg__bubble", text: message.content }));
      if (message.attachments && message.attachments.length) main.appendChild(filesRow(message.attachments));

      const actions = el("div", { class: "msg__actions" });
      if (message.content) actions.appendChild(actionBtn("edit", "编辑", () => startEdit(index)));
      actions.appendChild(
        actionBtn("copy", "复制", async () => {
          await copyText(composeUserContent(message));
          toast("已复制");
        }),
      );
      main.appendChild(actions);
      wrap.append(main, el("div", { class: "msg__avatar", "aria-hidden": "true", text: "我" }));
      return wrap;
    }

    const body = el("div", { class: "msg__body md" });
    body.innerHTML = markdown(message.content);
    decorate(body);

    const head = el("div", { class: "msg__head" }, [
      el("strong", { text: "Dream AI" }),
      message.model ? el("span", { class: "tag", text: modelLabel(message.model, message.provider) }) : null,
      el("span", { text: timeLabel(message.ts) }),
    ]);

    const main = el("div", { class: "msg__main" }, [head]);
    if (message.reasoning) main.appendChild(thinkingNode(message.reasoning, false));
    main.appendChild(body);
    main.appendChild(
      el("div", { class: "msg__actions" }, [
        actionBtn("copy", "复制", async () => {
          await copyText(message.content);
          toast("已复制");
        }),
        actionBtn("refresh", "重新生成", () => regenerate(index)),
      ]),
    );

    wrap.append(
      el("div", { class: "msg__avatar", "aria-hidden": "true" }, [
        el("img", { src: "/assets/img/mark.svg", alt: "", width: "18", height: "18" }),
      ]),
      main,
    );
    return wrap;
  }

  function renderChat() {
    const chat = $("#chat");
    const hero = $("#hero");
    const toBottom = $("#toBottom");
    chat.textContent = "";
    if (toBottom) toBottom.hidden = true;
    const session = activeSession();

    if (!session || session.messages.length === 0) {
      hero.hidden = false;
      chat.hidden = true;
      return;
    }

    hero.hidden = true;
    chat.hidden = false;
    session.messages.forEach((message, index) => chat.appendChild(messageNode(message, index)));
    scrollToBottom(true);
  }

  // ---------------------------------------------------------------------
  // Modes & work mode
  // ---------------------------------------------------------------------

  function buildModeMenu() {
    const menu = $("#modeMenu");
    menu.textContent = "";
    MODES.forEach((mode) => {
      const item = el("button", {
        class: `menu__item${state.settings.mode === mode.id ? " is-active" : ""}`,
        type: "button",
        "data-mode": mode.id,
      }, [
        el("span", { class: "menu__item__main" }, [
          el("strong", { text: `${mode.label}模式` }),
          el("span", { text: mode.desc }),
        ]),
        el("span", {
          html: '<svg class="menu__check" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
        }),
      ]);
      item.addEventListener("click", () => {
        setMode(mode.id);
        closeMenus();
      });
      menu.appendChild(item);
    });
  }

  function buildDocTemplateMenu() {
    const menu = $("#docTemplateMenu");
    menu.textContent = "";
    DOC_TEMPLATES.forEach((template) => {
      const item = el("button", {
        class: `menu__item${state.settings.docTemplate === template.id ? " is-active" : ""}`,
        type: "button",
        "data-template": template.id,
      }, [
        el("span", { class: "menu__item__main" }, [
          el("strong", { text: template.label }),
          el("span", { text: template.id === "auto" ? "根据内容自动选择格式与结构" : "内置办公模板" }),
        ]),
        el("span", {
          html: '<svg class="menu__check" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
        }),
      ]);
      item.addEventListener("click", () => {
        setDocTemplate(template.id);
        closeMenus();
      });
      menu.appendChild(item);
    });
  }

  function setDocTemplate(id) {
    state.settings.docTemplate = id;
    persistSettings();
    updateModeUI();
    const template = DOC_TEMPLATES.find((item) => item.id === id);
    if (template) toast(`模板：${template.label}`);
  }

  function setMode(id) {
    state.settings.mode = id;
    persistSettings();
    updateModeUI();
    toast(
      id === "work"
        ? "已切换到工作模式：先拆计划，再逐步执行"
        : id === "doc"
          ? "已切换到文档模式：可生成 Word / Excel / PPT / PDF"
          : id === "code"
            ? "已切换到编程模式：直接在你的电脑上写代码并运行"
            : "已切换到对话模式",
    );
    if (!isMobile()) $("#input").focus({ preventScroll: true });
  }

  function updateModeUI() {
    const mode = state.settings.mode;
    const work = mode === "work";
    const doc = mode === "doc";
    const code = mode === "code";
    $("#modeLabel").textContent = work ? "工作" : doc ? "文档" : code ? "编程" : "对话";
    $("#modeBtn").classList.toggle("is-work", work || doc || code);
    const template = DOC_TEMPLATES.find((item) => item.id === state.settings.docTemplate) || DOC_TEMPLATES[0];
    $("#input").placeholder = doc
      ? "描述要生成的文档，例如：产品发布会会议纪要……"
      : code
        ? "描述要开发的小程序，例如：做一个前后端分离的待办清单……"
        : work
          ? "描述一个任务，Dream 会拆解成步骤逐步完成……"
          : "给 Dream AI 发送消息……";
    const hint = $(".hint");
    if (hint) {
      hint.textContent = doc
        ? `文档模式会生成文件到工作文件夹 · 当前模板：${template.label}`
        : code
          ? "编程模式会直接写代码、装依赖、启动服务，命令会记录到项目里的 dreamai-commands.log"
          : work
            ? "工作模式会分多步执行，耗时更长 · Enter 发送"
            : "Enter 发送 · Shift + Enter 换行 · 可拖入 txt / md 文件";
    }
    const docBtn = $("#docTemplateBtn");
    if (docBtn) {
      docBtn.hidden = doc ? false : true;
      docBtn.classList.toggle("is-on", doc);
    }
    const docLabel = $("#docTemplateLabel");
    if (docLabel) docLabel.textContent = template.label;
    $$("#modeMenu .menu__item").forEach((item) => {
      item.classList.toggle("is-active", item.dataset.mode === mode);
    });
  }

  function workStateText(work) {
    if (work.status === "planning") return "正在规划…";
    if (work.status === "finalizing") return "正在汇总…";
    if (work.status === "done") return "已完成";
    if (work.status === "stopped") return "已停止";
    if (work.status === "error") return "执行出错";
    const done = work.steps.filter((step) => step.status === "done").length;
    return `${done}/${work.steps.length}`;
  }

  function workStepNode(step, index) {
    const details = el("details", { class: `work-step is-${step.status}` });
    if (step.status === "running") details.open = true;
    const mark = step.status === "done" ? "✓" : step.status === "error" ? "!" : String(index + 1);
    const summary = el("summary", { class: "work-step__head" }, [
      el("span", { class: "work-step__dot", text: mark }),
      el("strong", { text: step.title }),
      el("span", {
        class: "work-step__state",
        text:
          step.status === "running"
            ? "执行中"
            : step.status === "done"
              ? "完成"
              : step.status === "error"
                ? "失败"
                : "等待",
      }),
      el("span", {
        class: "work-step__chev",
        html: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>',
      }),
    ]);
    const body = el("div", { class: "work-step__body md" });
    if (step.output) {
      body.innerHTML = markdown(step.output);
      decorate(body);
    }
    details.append(summary, body);
    return details;
  }

  function paintWork(node) {
    const { card, work } = node._work;
    card.textContent = "";

    card.appendChild(
      el("div", { class: "work__head" }, [
        icon("spark"),
        el("strong", { text: work.title || "任务计划" }),
        el("span", { class: `work__state is-${work.status}`, text: workStateText(work) }),
      ]),
    );

    const list = el("div", { class: "work__steps" });
    work.steps.forEach((step, index) => list.appendChild(workStepNode(step, index)));
    card.appendChild(list);

    if (work.final) {
      const final = el("div", { class: "work__final md" });
      final.innerHTML = markdown(work.final);
      decorate(final);
      card.appendChild(final);
    }
    if (work.error) {
      card.appendChild(el("div", { class: "msg__error", text: work.error }));
    }
    node._work.list = list;
  }

  function paintWorkStep(node, index, text) {
    const details = node._work.list?.children[index];
    const body = details?.querySelector(".work-step__body");
    if (!body) return;
    const stamp = Date.now();
    if (body._last && stamp - body._last < 120) return;
    body._last = stamp;
    body.innerHTML = markdown(text);
    decorate(body);
    scrollToBottom();
  }

  function paintWorkFinal(node, text) {
    const { card } = node._work;
    let final = card.querySelector(".work__final");
    if (!final) {
      final = el("div", { class: "work__final md" });
      card.appendChild(final);
    }
    const stamp = Date.now();
    if (final._last && stamp - final._last < 120) return;
    final._last = stamp;
    final.innerHTML = markdown(text);
    decorate(final);
    scrollToBottom();
  }

  function workMessageNode(work, index) {
    const head = el("div", { class: "msg__head" }, [
      el("strong", { text: "Dream AI" }),
      el("span", { class: "tag", text: "工作模式" }),
      work.model ? el("span", { class: "tag", text: modelLabel(work.model, work.provider) }) : null,
      el("span", { text: timeLabel(work.ts) }),
    ]);
    const card = el("div", { class: "work" });
    const main = el("div", { class: "msg__main" }, [head, card]);
    const node = el("div", { class: "msg msg--assistant", "data-index": String(index), "data-kind": "work" }, [
      el("div", { class: "msg__avatar", "aria-hidden": "true" }, [
        el("img", { src: "/assets/img/mark.svg", alt: "", width: "18", height: "18" }),
      ]),
      main,
    ]);
    node._work = { card, work };
    paintWork(node);
    return node;
  }

  function plannerPrompt(task) {
    return `你是 Dream AI 的任务规划器。请把用户任务拆成 3–6 个按顺序执行、彼此不重复的步骤。
只输出严格 JSON，不要代码块，不要解释：
{"title":"不超过 20 字的任务标题","steps":["步骤1","步骤2","步骤3"]}

用户任务：
${task}`;
  }

  function stepPrompt(task, steps, index, results) {
    const done = results.length
      ? results.map((r, i) => `${i + 1}. ${steps[i].title} → ${r.slice(0, 700)}`).join("\n")
      : "（还没开始）";
    return `你在执行一个多步任务，需要独立完成其中一步。
总任务：${task}

完整计划：
${steps.map((s, i) => `${i + 1}. ${s.title}`).join("\n")}

已完成：
${done}

当前步骤（第 ${index + 1} 步）：${steps[index].title}
请直接完成当前步骤，输出简洁、可用的结果（Markdown）。不要复述计划，不要询问用户。`;
  }

  function finalPrompt(task, steps, results) {
    return `总任务：${task}

执行记录：
${results.map((r, i) => `步骤 ${i + 1}（${steps[i].title}）：\n${r}`).join("\n\n")}

请基于以上结果，给用户一个完整、清晰的最终答复（Markdown）。不要复述执行过程，只给结果和必要的说明。`;
  }

  function parsePlan(text) {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start >= 0 && end > start) {
      try {
        const data = JSON.parse(text.slice(start, end + 1));
        const steps = Array.isArray(data.steps)
          ? data.steps.filter((step) => typeof step === "string" && step.trim()).slice(0, 6)
          : [];
        if (steps.length) {
          return {
            title: String(data.title || "").slice(0, 40),
            steps: steps.map((step) => step.replace(/^步骤\s*\d+\s*[：:.、]\s*/, "").trim()),
          };
        }
      } catch {
        /* fall through */
      }
    }
    return null;
  }

  async function callModel(messages, { onDelta, signal, temperature, maxTokens, timeoutMs = 300000 } = {}) {
    const provider = state.settings.provider || "free";
    let effectiveSignal = signal;
    if (typeof AbortSignal !== "undefined" && AbortSignal.timeout) {
      const timer = AbortSignal.timeout(timeoutMs);
      effectiveSignal =
        signal && AbortSignal.any ? AbortSignal.any([signal, timer]) : signal || timer;
    }
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      signal: effectiveSignal,
      body: JSON.stringify({
        messages,
        model: state.settings.model || state.config?.defaultModel,
        provider,
        apiKey: provider === "byok" ? state.userKey : undefined,
        temperature: temperature ?? Number(state.settings.temperature),
        maxTokens,
        thinking: false,
        style: state.settings.style,
      }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const error = new Error(data.error || `请求失败（${response.status}）`);
      error.status = response.status;
      throw error;
    }
    if (!response.body) throw new Error("当前浏览器不支持流式响应。");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let text = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseEvent(block);
        if (!event) continue;
        if (event.name === "delta") {
          text += event.data.t || "";
          onDelta?.(event.data.t || "", text);
        } else if (event.name === "error") {
          throw new Error(event.data.message || "生成失败");
        }
      }
    }
    return text;
  }

  async function runWorkTask(session, userMessage) {
    const task = composeUserContent(userMessage);
    const work = {
      role: "assistant",
      kind: "work",
      title: "正在规划…",
      steps: [],
      final: "",
      status: "planning",
      model: state.settings.model || state.config?.defaultModel,
      provider: state.settings.provider || "free",
      ts: now(),
    };

    const node = workMessageNode(work, session.messages.length);
    $("#chat").appendChild(node);
    setStreaming(true);
    state.follow = true;
    scrollToBottom(true);

    const controller = new AbortController();
    state.abort = controller;
    setAgentState("执行任务中", true);
    agentLog("step", `开始任务：${task.slice(0, 42)}`);
    const repaint = () => {
      paintWork(node);
      scrollToBottom();
    };

    try {
      const planText = await callModel([{ role: "user", content: plannerPrompt(task) }], {
        signal: controller.signal,
        temperature: 0.2,
      });
      const plan = parsePlan(planText);
      work.title = plan?.title || "任务计划";
      work.steps = (plan?.steps || ["分析并完成任务"]).map((title) => ({
        title,
        status: "pending",
        output: "",
      }));
      work.status = "running";
      repaint();
      agentLog("step", `已拆解 ${work.steps.length} 个步骤`);

      const results = [];
      for (let index = 0; index < work.steps.length; index += 1) {
        if (controller.signal.aborted) break;
        const step = work.steps[index];
        step.status = "running";
        repaint();
        agentLog("tool", `执行：${step.title}`);
        const output = await callModel(
          [{ role: "user", content: stepPrompt(task, work.steps, index, results) }],
          {
            signal: controller.signal,
            temperature: 0.4,
            onDelta: (_chunk, full) => paintWorkStep(node, index, full),
          },
        );
        step.output = output.trim();
        step.status = "done";
        results.push(step.output);
        repaint();
        agentLog("done", `完成：${step.title}`);
      }

      if (!controller.signal.aborted) {
        work.status = "finalizing";
        repaint();
        const finalText = await callModel([{ role: "user", content: finalPrompt(task, work.steps, results) }], {
          signal: controller.signal,
          temperature: 0.5,
          onDelta: (_chunk, full) => paintWorkFinal(node, full),
        });
        work.final = finalText.trim();
        work.status = "done";
        repaint();
        agentLog("done", "任务完成");
      } else {
        work.status = "stopped";
      }
    } catch (error) {
      if (error.name === "AbortError" || controller.signal.aborted) {
        work.status = "stopped";
      } else {
        work.status = "error";
        work.error = error.message || "任务执行失败，请重试。";
        const keyProblem =
          error.status === 401 || /api key|密钥|key 无效/i.test(error.message || "");
        if (state.settings.provider === "byok" && keyProblem) {
          setTimeout(() => openKeyModal(), 500);
        }
      }
      repaint();
    } finally {
      setStreaming(false);
      state.abort = null;
      setAgentState("空闲", false);
      if (work.steps.length || work.final || work.error) {
        session.messages.push(work);
        session.updatedAt = now();
        persistSessions();
      }
      scrollToBottom();
    }
  }

  // ---------------------------------------------------------------------
  // Document mode
  // ---------------------------------------------------------------------

  function docShell(assistant, index) {
    const head = el("div", { class: "msg__head" }, [
      el("strong", { text: "Dream AI" }),
      el("span", { class: "tag", text: "文档模式" }),
      assistant.model ? el("span", { class: "tag", text: modelLabel(assistant.model, assistant.provider) }) : null,
      el("span", { text: timeLabel(assistant.ts) }),
    ]);
    const body = el("div", { class: "msg__body" }, [
      el("span", { class: "typing" }, [el("i"), el("i"), el("i")]),
      el("span", { class: "doc-pending", text: "正在生成文档…" }),
    ]);
    const main = el("div", { class: "msg__main" }, [head, body]);
    return el("div", { class: "msg msg--assistant", "data-index": String(index), "data-kind": "doc" }, [
      el("div", { class: "msg__avatar", "aria-hidden": "true" }, [
        el("img", { src: "/assets/img/mark.svg", alt: "", width: "18", height: "18" }),
      ]),
      main,
    ]);
  }

  function docMessageNode(message, index) {
    const head = el("div", { class: "msg__head" }, [
      el("strong", { text: "Dream AI" }),
      el("span", { class: "tag", text: "文档模式" }),
      message.model ? el("span", { class: "tag", text: modelLabel(message.model, message.provider) }) : null,
      el("span", { text: timeLabel(message.ts) }),
    ]);
    const main = el("div", { class: "msg__main" }, [head]);

    if (message.document) {
      const doc = message.document;
      const card = el("div", { class: "doc-result" }, [
        el("span", { class: "doc-result__icon", "data-type": doc.type, text: String(doc.type || "").toUpperCase() }),
        el("div", { class: "doc-result__meta" }, [
          el("strong", { text: doc.name, title: doc.path }),
          el("em", { text: `${doc.sizeLabel} · ${doc.typeLabel}` }),
        ]),
      ]);
      const actions = el("div", { class: "doc-result__actions" });
      const open = el("button", { class: "btn btn--primary", type: "button", text: "打开" });
      open.addEventListener("click", () => {
        desktop?.documents.open(doc.path).catch((error) => toast(error.message, "err"));
      });
      const reveal = el("button", { class: "btn btn--ghost", type: "button", text: "在文件夹中显示" });
      reveal.addEventListener("click", () => {
        desktop?.documents.reveal(doc.path).catch((error) => toast(error.message, "err"));
      });
      actions.append(open, reveal);
      card.appendChild(actions);
      main.appendChild(card);
      main.appendChild(
        el("div", { class: "msg__actions is-visible" }, [
          actionBtn("copy", "复制路径", async () => {
            await copyText(doc.path);
            toast("路径已复制");
          }),
        ]),
      );
    } else if (message.error) {
      main.appendChild(el("div", { class: "msg__error", text: message.error }));
    }

    return el("div", { class: "msg msg--assistant", "data-index": String(index), "data-kind": "doc" }, [
      el("div", { class: "msg__avatar", "aria-hidden": "true" }, [
        el("img", { src: "/assets/img/mark.svg", alt: "", width: "18", height: "18" }),
      ]),
      main,
    ]);
  }

  function parseJsonObject(text) {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start < 0 || end <= start) return null;
    const slice = text.slice(start, end + 1);
    try {
      return JSON.parse(slice);
    } catch {
      try {
        return JSON.parse(slice.replace(/,\s*([}\]])/g, "$1"));
      } catch {
        return null;
      }
    }
  }

  function inferDocType(spec, template) {
    if (Array.isArray(spec.slides) && spec.slides.length) return "pptx";
    if (Array.isArray(spec.sheets) && spec.sheets.length) return "xlsx";
    if (template.id === "table") return "xlsx";
    if (template.id === "slides") return "pptx";
    return "docx";
  }

  function docPrompt(task, template) {
    const today = new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" });
    return `你是 Dream AI 的文档生成器。根据用户需求生成一份可直接使用的办公文档。今天是 ${today}。
只输出严格 JSON，不要 Markdown 代码块，不要解释：
{
  "type": "docx|xlsx|pptx|pdf|md",
  "title": "文档标题",
  "subtitle": "副标题，可空",
  "filename": "文件名（不含扩展名）",
  "sections": [{"heading":"小节标题","paragraphs":["段落"],"bullets":["条目"],"table":{"headers":["列1"],"rows":[["值"]]},"note":"备注"}],
  "slides": [{"title":"页标题","bullets":["要点"],"notes":"讲稿提示"}],
  "sheets": [{"name":"工作表","headers":["列1"],"rows":[["值"]],"summary":["合计","",""]}]
}
规则：
- docx / pdf / md 使用 sections；xlsx 使用 sheets；pptx 使用 slides。
- 内容具体、专业、可直接使用，不要写“待补充”“示例”这类占位符。
- 所有日期使用 2026 年，不要出现 2023/2024 等旧年份。
- 禁止使用“张三/李四/王五”“平台一/主题一/负责人一”这类示例内容；用具体角色（产品负责人、市场负责人）或用户提供的真实信息。
- 数据要有真实感：具体渠道名、主题名、金额或指标数字；产品名统一写作 Dream AI。
- 表格每一行必须是不同的具体内容；平台写公众号/视频号/小红书/B站/抖音/官网等真实渠道，人名写林晓/陈默这类具体姓名或“市场负责人”这类角色。
- 禁止“平台一、主题一、负责人一、活动一、里程碑1”这类编号占位。
- 合格的数据表示例（只在生成表格时参考具体程度，不要照抄）：
  {"type":"xlsx","title":"10 月内容排期","sheets":[{"name":"内容排期","headers":["日期","平台","主题","负责人","状态"],"rows":[["2026-10-27","公众号","发布会预告：把想法交给 Dream","林晓","进行中"],["2026-10-29","视频号","90 秒看懂 Dream AI 桌面版","陈默","待开始"]],"summary":["合计","2 条","","",""]}]}
- 中文办公风格，标题简洁，正文分点，必要时用表格。
- 用户没指定格式时：会议/方案/周报/简历用 docx，数据用 xlsx，演示用 pptx。
${template.prompt ? `- 模板要求：${template.prompt}` : ""}

用户需求：
${task}`;
  }

  function fallbackDocSpec(task, template) {
    const type = template.id === "table" ? "xlsx" : template.id === "slides" ? "pptx" : "docx";
    const title = task.slice(0, 28) || "Dream AI 文档";
    if (type === "xlsx") {
      return { type, title, sheets: [{ name: "Sheet1", headers: ["内容"], rows: [[task]] }] };
    }
    if (type === "pptx") {
      return { type, title, slides: [{ title, bullets: [task] }] };
    }
    return { type, title, sections: [{ heading: "内容", paragraphs: [task] }] };
  }

  function hasPlaceholderContent(spec) {
    const text = JSON.stringify(spec || {});
    return (
      /(平台|主题|活动|负责人|里程碑|项目|任务)[一二三四五六七八九十]/.test(text) ||
      /张三|李四|王五|赵六|钱七|孙八/.test(text)
    );
  }

  async function generateDocSpec(task, template, signal) {
    const first = await callModel([{ role: "user", content: docPrompt(task, template) }], {
      signal,
      temperature: 0.5,
    });
    let spec = parseJsonObject(first);
    if (spec && hasPlaceholderContent(spec)) {
      agentLog("info", "检测到模板化内容，正在重写");
      const retry = await callModel(
        [
          {
            role: "user",
            content: `${docPrompt(task, template)}

注意：上一版出现了“平台一 / 主题一 / 负责人一 / 张三”这类占位内容，不合格。
这次必须写具体平台、具体主题、具体姓名或角色，表格每一行都要不同。`,
          },
        ],
        { signal, temperature: 0.7 },
      );
      const next = parseJsonObject(retry);
      if (next && !hasPlaceholderContent(next)) spec = next;
    }
    return spec;
  }
  async function runDocTask(session, userMessage) {
    if (!desktop?.documents) {
      toast("文档模式需要在桌面版使用", "err");
      return;
    }
    const workspace = await desktop.getWorkspace();
    if (!workspace.exists) {
      toast("请先选择一个工作文件夹", "err");
      openModal("desktopModal");
      refreshDesktop().catch(() => {});
      return;
    }
    const task = composeUserContent(userMessage);
    const template =
      DOC_TEMPLATES.find((item) => item.id === state.settings.docTemplate) || DOC_TEMPLATES[0];
    const assistant = {
      role: "assistant",
      kind: "doc",
      ts: now(),
      model: state.settings.model,
      provider: state.settings.provider,
      status: "generating",
    };

    const node = docShell(assistant, session.messages.length);
    $("#chat").appendChild(node);
    setStreaming(true);
    state.follow = true;
    setAgentState("生成文档中", true);
    agentLog("step", `理解需求：${task.slice(0, 44)}`);
    scrollToBottom(true);

    const controller = new AbortController();
    state.abort = controller;

    try {
      agentLog("tool", "规划文档结构");
      const spec = await generateDocSpec(task, template, controller.signal);
      let resolved = spec;
      if (!resolved || typeof resolved !== "object") {
        resolved = fallbackDocSpec(task, template);
        agentLog("info", "结构解析失败，改用默认模板");
      }
      if (!["docx", "xlsx", "pptx", "pdf", "md"].includes(resolved.type)) {
        resolved.type = inferDocType(resolved, template);
      }
      if (!resolved.title) resolved.title = task.slice(0, 30);

      agentLog("tool", `写入 ${String(resolved.type).toUpperCase()} 文件`);
      const doc = await desktop.documents.create(resolved);
      assistant.document = doc;
      assistant.status = "done";

      node.remove();
      $("#chat").appendChild(docMessageNode(assistant, session.messages.length));
      session.messages.push(assistant);
      session.updatedAt = now();
      persistSessions();

      addArtifact(doc);
      agentLog("done", `已生成 ${doc.name}（${doc.sizeLabel}）`);
      toast("文档已生成");
      scrollToBottom();
    } catch (error) {
      if (error.name === "AbortError" || controller.signal.aborted) {
        toast("已取消生成");
        node.remove();
      } else {
        assistant.status = "error";
        assistant.error = error.message || "文档生成失败，请重试。";
        node.remove();
        $("#chat").appendChild(docMessageNode(assistant, session.messages.length));
        session.messages.push(assistant);
        session.updatedAt = now();
        persistSessions();
        agentLog("error", assistant.error);
        if (error.status === 401 && state.settings.provider === "byok") {
          setTimeout(() => openKeyModal(), 500);
        }
      }
    } finally {
      setStreaming(false);
      state.abort = null;
      setAgentState("空闲", false);
      scrollToBottom();
    }
  }

  // ---------------------------------------------------------------------
  // Coding agent mode (desktop only)
  // ---------------------------------------------------------------------

  const sleepPromise = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const CODE_STATUS = {
    planning: { label: "正在规划项目…", busy: true },
    writing: { label: "正在写代码…", busy: true },
    installing: { label: "安装依赖…", busy: true },
    fixing: { label: "修复报错…", busy: true },
    running: { label: "启动服务…", busy: true },
    done: { label: "已运行", busy: false },
    paused: { label: "服务未启动（已跳过）", busy: false },
    stopped: { label: "已停止", busy: false },
    error: { label: "出错", busy: false },
  };

  function codeStatusLabel(message) {
    if (message.error) return message.error.slice(0, 60);
    return (CODE_STATUS[message.status] || CODE_STATUS.error).label;
  }

  function appendCodeLog(message, text) {
    message.buildLog = (message.buildLog || "") + String(text || "");
    if (message.buildLog.length > 60000) message.buildLog = message.buildLog.slice(-60000);
    message.log = message.buildLog + (message.serverLog ? `\n--- 服务输出 ---\n${message.serverLog}` : "");
    if (message.log.length > 80000) message.log = message.log.slice(-80000);
  }

  function codeMessageNode(message, index) {
    const status = CODE_STATUS[message.status] || CODE_STATUS.error;
    const head = el("div", { class: "msg__head" }, [
      el("strong", { text: "Dream AI" }),
      el("span", { class: "tag", text: "编程模式" }),
      message.model ? el("span", { class: "tag", text: modelLabel(message.model, message.provider) }) : null,
      el("span", { text: timeLabel(message.ts) }),
    ]);
    const card = el("div", { class: "code-card" }, [
      el("div", { class: "code-card__head" }, [
        el("span", { class: `code-dot is-${message.status}${status.busy ? " is-busy" : ""}` }),
        el("strong", { text: message.title || "项目" }),
        el("em", { text: codeStatusLabel(message) }),
      ]),
    ]);

    if (message.project) {
      card.appendChild(
        el("div", { class: "code-card__meta" }, [
          el("span", { text: message.project.name }),
          message.url && message.running ? el("span", { text: `· ${message.url}` }) : null,
          el("span", { text: `· 端口 ${message.project.port || "—"}` }),
        ]),
      );
    }

    if (message.files && message.files.length) {
      const tree = el("ul", { class: "code-tree" });
      message.files.slice(0, 60).forEach((pathText) => {
        tree.appendChild(
          el("li", {}, [
            el("span", { class: "code-tree__icon" }, [icon(pathText.endsWith("/") ? "folder" : "file")]),
            el("span", { text: pathText }),
          ]),
        );
      });
      if (message.files.length > 60) {
        tree.appendChild(el("li", { text: `… 还有 ${message.files.length - 60} 个文件` }));
      }
      card.appendChild(tree);
    }

    if (message.log) {
      const log = el("pre", { class: "code-log", text: message.log });
      requestAnimationFrame(() => {
        log.scrollTop = log.scrollHeight;
      });
      card.appendChild(log);
    }

    if (message.error && message.status === "error") {
      card.appendChild(el("div", { class: "msg__error", text: message.error }));
    }

    const actions = el("div", { class: "code-card__actions" });
    if (message.project) {
      const folder = el("button", { class: "btn btn--ghost", type: "button", text: "在文件夹中显示" });
      folder.addEventListener("click", () => {
        desktop?.code.openFolder(message.project.root).catch((error) => toast(error.message, "err"));
      });
      actions.appendChild(folder);
    }
    if (message.url && message.running) {
      const open = el("button", { class: "btn btn--primary", type: "button", text: "打开网页" });
      open.addEventListener("click", () => {
        desktop?.code.openUrl(message.url).catch((error) => toast(error.message, "err"));
      });
      actions.appendChild(open);
    }
    if (message.serverId && message.running) {
      const stop = el("button", { class: "btn btn--ghost", type: "button", text: "停止服务" });
      stop.addEventListener("click", () => {
        desktop?.code
          .stopServer(message.serverId)
          .then(() => {
            message.running = false;
            message.status = "stopped";
            toast("服务已停止");
            persistSessions();
            const host = stop.closest(".msg");
            if (host) host.replaceWith(codeMessageNode(message, index));
          })
          .catch((error) => toast(error.message, "err"));
      });
      actions.appendChild(stop);
    }
    const copy = actionBtn("copy", "复制路径", async () => {
      await copyText(message.project?.root || "");
      toast("路径已复制");
    });
    actions.appendChild(copy);
    card.appendChild(actions);

    const main = el("div", { class: "msg__main" }, [head, card]);
    return el("div", { class: "msg msg--assistant", "data-index": String(index), "data-kind": "code" }, [
      el("div", { class: "msg__avatar", "aria-hidden": "true" }, [
        el("img", { src: "/assets/img/mark.svg", alt: "", width: "18", height: "18" }),
      ]),
      main,
    ]);
  }

  function codePlanPrompt(task) {
    return `你是 Dream AI 编程智能体，在用户的 Windows 电脑上直接开发并运行项目（电脑装有 Node.js 20+ 与 npm）。
只输出严格 JSON，不要 Markdown 代码块，不要解释：
{
  "name": "英文小写短名",
  "description": "一句话中文说明",
  "stack": "技术栈说明",
  "port": 3000,
  "files": [{"path": "package.json", "purpose": "依赖与启动脚本"}, {"path": "server.js", "purpose": "Node 后端"}],
  "setup": ["npm install"],
  "run": "node server.js",
  "verify": "浏览器打开 http://localhost:3000 应看到什么"
}
规则：
- 前端用原生 HTML/CSS/JS；后端必须用 Node.js 内置模块（http/fs/path/url），不得使用 express/body-parser 等第三方包；数据存内存或 JSON 文件。
- 零第三方依赖：package.json 不写 dependencies，setup 输出空数组 []。
- 默认只写一个 server.js：用 Node 内置 http 模块，把 HTML/CSS/JS 内嵌在返回的页面里，同时提供 JSON API；只有确实需要拆分时才写多个文件，总数不超过 3 个。
- 每个文件尽量控制在 160 行以内，内容完整可运行，互相引用一致。
- name 用英文小写连字符；port 选 3000–3999 里不容易冲突的。
- 只输出 JSON。

用户需求：
${task}`;
  }

  function parseFileBlocks(text, batch) {
    const files = [];
    const re = /===FILE:\s*([^\n=]+)===+\s*\n?([\s\S]*?)(?=\n?===FILE:|\n?===END===|$)/g;
    let match;
    while ((match = re.exec(text)) !== null) {
      const pathText = String(match[1] || "").trim();
      let content = String(match[2] || "");
      content = content.replace(/^```[a-zA-Z]*\s*\n?/, "").replace(/\n?```\s*$/, "");
      if (pathText && content.trim()) files.push({ path: pathText, content });
    }
    if (!files.length) {
      const single = /(?:路径|FILE|文件)[:：]\s*([^\n]+)\s*\n?```[a-zA-Z]*\s*\n([\s\S]*?)\n?```/i.exec(text);
      if (single) files.push({ path: single[1].trim(), content: single[2] });
    }
    if (!files.length) {
      const fences = [...text.matchAll(/```[a-zA-Z]*\s*\n([\s\S]*?)\n?```/g)]
        .map((m) => m[1])
        .filter((content) => String(content || "").trim());
      const candidates = (batch || []).map((file) => file.path);
      if (fences.length && candidates.length) {
        const used = new Set();
        const scoreFor = (candidate, content) => {
          const lower = candidate.toLowerCase();
          let score = Math.min(String(content).length / 2000, 2);
          if (lower.endsWith(".json") && /^\s*[{[]/.test(content)) score += 5;
          if (lower.endsWith(".html") && /<html|<!doctype/i.test(content)) score += 5;
          if (lower.endsWith(".css") && /[.#][\w-]+\s*\{/.test(content)) score += 4;
          if (lower.endsWith(".js") && /(function|const |let |require\(|document\.|addEventListener)/.test(content)) score += 4;
          return score;
        };
        const take = (candidate) => {
          let best = -1;
          let bestScore = -1;
          fences.forEach((content, index) => {
            if (used.has(index)) return;
            const score = scoreFor(candidate, content);
            if (score > bestScore) {
              bestScore = score;
              best = index;
            }
          });
          if (best < 0) return null;
          used.add(best);
          return fences[best];
        };
        for (const candidate of candidates) {
          const content = take(candidate);
          if (content != null) files.push({ path: candidate, content });
        }
      }
    }
    return files;
  }

  function codeFilesPrompt(task, plan, batch, existing) {
    const list = batch.map((file) => `- ${file.path}（${file.purpose || "实现文件"}）`).join("\n");
    const shown = existing
      .map(
        (file) =>
          `<file path="${file.path}">\n${(file.content || "(新文件)").slice(0, 8000)}\n</file>`,
      )
      .join("\n");
    return `你是 Dream AI 编程智能体，正在生成项目「${plan.name}」（${plan.stack}）。
本批只写这些文件：
${list}

已存在的文件内容（空表示新文件）：
${shown}

整体规划：安装命令 ${JSON.stringify(plan.setup)}；启动命令 ${plan.run}；验证 ${plan.verify}。
请严格按以下格式依次输出本批全部文件（每行只写代码本身，不要用 JSON、不要解释）：

===FILE: public/js/app.js===
\`\`\`js
<完整代码，一行都不要省略>
\`\`\`
===END===

===FILE: server.js===
\`\`\`js
<完整代码>
\`\`\`
===END===

要求：代码完整可运行；优先单文件 server.js（内嵌页面）；不得 require 任何第三方包，只用 Node 内置模块；不要写「此处省略」。

用户需求：
${task}`;
  }

  function codeFixPrompt(task, plan, cmd, result) {
    return `你是 Dream AI 编程智能体。项目「${plan.name}」里这条命令失败了：
$ ${cmd}
退出码：${result.code}
输出（末尾）：
${String(result.stderr || result.stdout || "").slice(-6000)}

请按以下格式输出需要修改的文件（只改必要的文件；如果不需要改，输出「无需修改」四个字）：

===FILE: server.js===
\`\`\`js
<修正后的完整文件>
\`\`\`
===END===

修复要针对上面的报错，保持各文件引用一致。

用户需求：
${task}`;
  }

  async function readExistingFiles(project, batch) {
    const out = [];
    for (const file of batch) {
      try {
        const result = await desktop.code.readFile(project.root, file.path);
        out.push({ path: file.path, content: result.content, truncated: result.truncated });
      } catch {
        out.push({ path: file.path, content: "" });
      }
    }
    return out;
  }

  async function codeFixLoop(message, task, plan, project, cmd, result, controller) {
    agentLog("tool", "读取报错，让模型修复");
    appendCodeLog(message, "\n[报错] 让模型修复…\n");
    const raw = await callModel([{ role: "user", content: codeFixPrompt(task, plan, cmd, result) }], {
      signal: controller.signal,
      temperature: 0.3,
      maxTokens: 2200,
      timeoutMs: 240000,
    });
    const files = /无需修改/.test(raw) ? [] : parseFileBlocks(raw, plan.files);
    if (files.length) {
      const written = await desktop.code.writeFiles(project.root, files);
      appendCodeLog(message, `修复写入 ${written.written.length} 个文件\n`);
      message.files = [...new Set([...(message.files || []), ...written.written.map((w) => w.path)])];
      agentLog("tool", `修复写入 ${written.written.length} 个文件`);
    } else {
      appendCodeLog(message, "模型认为无需改文件，直接重试\n");
    }
    appendCodeLog(message, `$ ${cmd}\n`);
    const retry = await desktop.code.runCommand(project.root, cmd, { auto: true, timeoutMs: 300000 });
    appendCodeLog(message, `${retry.stdout || ""}${retry.stderr || ""}\n[exit ${retry.code}]\n`);
    return retry;
  }

  async function runCodeTask(session, userMessage) {
    if (!desktop?.code) {
      toast("编程模式需要在桌面版使用", "err");
      return;
    }
    const workspace = await desktop.getWorkspace();
    if (!workspace.exists) {
      toast("请先选择一个工作文件夹", "err");
      openModal("desktopModal");
      refreshDesktop().catch(() => {});
      return;
    }
    const task = composeUserContent(userMessage);
    const message = {
      role: "assistant",
      kind: "code",
      ts: now(),
      model: state.settings.model,
      provider: state.settings.provider,
      status: "planning",
      title: "正在规划项目…",
      files: [],
      buildLog: "",
      log: "",
      project: null,
    };

    let node = codeMessageNode(message, session.messages.length);
    $("#chat").appendChild(node);
    const repaint = () => {
      const fresh = codeMessageNode(message, session.messages.length);
      node.replaceWith(fresh);
      node = fresh;
    };

    setStreaming(true);
    state.follow = true;
    setAgentState("写代码中", true);
    agentLog("step", `开始开发：${task.slice(0, 42)}`);
    scrollToBottom(true);

    const controller = new AbortController();
    state.abort = controller;

    try {
      // 1. plan
      const planRaw = await callModel([{ role: "user", content: codePlanPrompt(task) }], {
        signal: controller.signal,
        temperature: 0.3,
        maxTokens: 1200,
        timeoutMs: 180000,
      });
      const plan = parseJsonObject(planRaw);
      if (!plan || !Array.isArray(plan.files) || !plan.files.length) {
        throw new Error("规划解析失败，请重试");
      }
      message.title = `${plan.name} · ${plan.description || ""}`;
      message.spec = plan;
      message.status = "writing";
      repaint();
      agentLog("step", `规划完成：${plan.files.length} 个文件 · ${plan.stack || "Node.js"}`);

      // 2. create project
      const project = await desktop.code.createProject(plan.name);
      message.project = { root: project.root, name: project.name, port: Number(plan.port) || 3000 };
      agentLog("tool", `创建项目：${project.name}`);

      const nodeProbe = await desktop.code.runCommand(project.root, "node -v", { auto: true, timeoutMs: 15000 });
      appendCodeLog(message, `Node: ${(nodeProbe.stdout || "").trim() || "未检测到"}\n`);
      if (nodeProbe.code !== 0) {
        throw new Error("未检测到 Node.js，请先安装 Node.js 20+（https://nodejs.org）后重试");
      }

      // 3. write files in batches
      let remaining = plan.files.slice();
      let passes = 0;
      while (remaining.length && passes < 12 && !controller.signal.aborted) {
        passes += 1;
        const batch = remaining.slice(0, 1);
        remaining = remaining.slice(1);
        const existing = await readExistingFiles(project, batch);
        let files = [];
        try {
          let raw = await callModel(
            [{ role: "user", content: codeFilesPrompt(task, plan, batch, existing) }],
            { signal: controller.signal, temperature: 0.3, maxTokens: 2600, timeoutMs: 90000 },
          );
          files = parseFileBlocks(raw, batch);
          if (!files.length) {
            raw = await callModel(
              [{ role: "user", content: `${codeFilesPrompt(task, plan, batch, existing)}\n\n上次没有解析到任何文件，请严格使用 ===FILE: 路径=== 和 ===END=== 格式重新输出。` }],
              { signal: controller.signal, temperature: 0.2, maxTokens: 2200, timeoutMs: 90000 },
            );
            files = parseFileBlocks(raw, batch);
          }
        } catch (error) {
          if (error.name === "AbortError") throw error;
          appendCodeLog(message, `[生成超时/失败] ${error.message}\n`);
        }
        if (!files.length && /(待办|todo|清单)/i.test(task)) {
          const scaffold = await desktop.code.scaffold("todo", message.project.port);
          if (scaffold && scaffold.length) {
            files = scaffold;
            appendCodeLog(message, "模型输出不可用，已使用内置脚手架生成可运行版本\n");
            agentLog("info", "使用内置脚手架兜底");
          }
        }
        if (!files.length) {
          appendCodeLog(message, "[失败] 没有拿到可用文件内容\n");
          throw new Error("模型没有输出可解析的文件内容，请重试");
        }
        const result = await desktop.code.writeFiles(project.root, files);
        message.files = [...new Set([...(message.files || []), ...result.written.map((w) => w.path)])];
        appendCodeLog(message, `写入 ${result.written.length} 个文件：${result.written.map((w) => w.path).join(", ")}\n`);
        agentLog("tool", `写入 ${result.written.length} 个文件`);
        repaint();
      }

      // 4. setup commands
      message.status = "installing";
      repaint();
      const pkgFile = await desktop.code.readFile(project.root, "package.json").catch(() => null);
      let hasDeps = false;
      try {
        const pkg = JSON.parse(pkgFile?.content || "{}");
        hasDeps = Object.keys(pkg.dependencies || {}).length > 0 || Object.keys(pkg.devDependencies || {}).length > 0;
      } catch {
        hasDeps = false;
      }
      const npmProbe = await desktop.code.runCommand(project.root, "npm -v", { auto: true, timeoutMs: 15000 });
      appendCodeLog(message, `npm: ${npmProbe.code === 0 ? (npmProbe.stdout || "").trim() : "未检测到"}\n`);
      if (hasDeps && npmProbe.code !== 0) {
        throw new Error("项目需要第三方依赖，但未检测到 npm。请安装 Node.js（含 npm）后重试，或改成零依赖项目");
      }
      let setup = Array.isArray(plan.setup) && plan.setup.length ? plan.setup : ["npm install"];
      if (!hasDeps) {
        setup = [];
        appendCodeLog(message, "零依赖项目，跳过安装\n");
      }
      for (const cmd of setup) {
        if (controller.signal.aborted) break;
        appendCodeLog(message, `$ ${cmd}\n`);
        agentLog("tool", `运行：${cmd}`);
        let result = await desktop.code.runCommand(project.root, cmd, { auto: true, timeoutMs: 300000 });
        if (result.blocked) {
          appendCodeLog(message, "（命令未获批准，跳过）\n");
          continue;
        }
        appendCodeLog(message, `${result.stdout || ""}${result.stderr || ""}\n[exit ${result.code}]\n`);
        repaint();
        if (result.code !== 0) {
          message.status = "fixing";
          repaint();
          const retry = await codeFixLoop(message, task, plan, project, cmd, result, controller);
          if (retry.code !== 0) {
            throw new Error(`命令「${cmd}」失败，修复后仍报错，可查看日志`);
          }
        }
      }

      // 5. start server
      message.status = "running";
      repaint();
      const runCmd = plan.run || "npm run dev";
      const started = await desktop.code.startServer(project.root, runCmd);
      if (started.blocked) {
        message.status = "paused";
        repaint();
        agentLog("info", "用户跳过了服务启动");
      } else {
        message.serverId = started.id;
        message.url = `http://localhost:${message.project.port}`;
        let crashed = null;
        for (let poll = 0; poll < 25 && !controller.signal.aborted; poll += 1) {
          await sleepPromise(1200);
          const out = await desktop.code.serverOutput(started.id);
          message.serverLog = out.output || "";
          message.log = message.buildLog + (message.serverLog ? `\n--- 服务输出 ---\n${message.serverLog}` : "");
          repaint();
          if (out.exited) {
            crashed = { code: out.code, stderr: out.output };
            break;
          }
          if (/listening|ready|started|running|localhost:\d+|http:\/\/localhost/i.test(out.output || "")) {
            break;
          }
        }
        if (crashed && !controller.signal.aborted) {
          agentLog("tool", "服务启动失败，尝试修复");
          message.status = "fixing";
          repaint();
          const fixed = await codeFixLoop(message, task, plan, project, runCmd, crashed, controller);
          if (fixed.code !== 0) {
            throw new Error("服务启动失败，修复后仍报错，可查看日志");
          }
          const restarted = await desktop.code.startServer(project.root, runCmd);
          message.serverId = restarted.id;
          for (let poll = 0; poll < 20 && !controller.signal.aborted; poll += 1) {
            await sleepPromise(1200);
            const out = await desktop.code.serverOutput(restarted.id);
            message.serverLog = out.output || "";
            message.log = message.buildLog + (message.serverLog ? `\n--- 服务输出 ---\n${message.serverLog}` : "");
            repaint();
            if (out.exited) {
              crashed = { code: out.code, stderr: out.output };
              break;
            }
            if (/listening|ready|started|running|localhost:\d+/i.test(out.output || "")) break;
          }
          if (crashed) throw new Error("服务重启后仍崩溃，可查看日志");
        }
        message.running = !crashed;
      }

      message.status = message.running ? "done" : message.status === "paused" ? "paused" : "done";
      repaint();
      session.messages.push(message);
      session.updatedAt = now();
      persistSessions();
      agentLog("done", `项目 ${message.project.name} ${message.running ? "已运行" : "已生成"}`);
      toast(message.running ? "项目已运行起来" : "项目已生成");
    } catch (error) {
      if (error.name === "AbortError" || controller.signal.aborted) {
        message.status = "stopped";
        desktop?.code.killCurrent().catch(() => {});
        if (message.serverId) desktop?.code.stopServer(message.serverId).catch(() => {});
        toast("已停止");
      } else {
        message.status = "error";
        message.error = error.message || "开发失败，请重试";
        agentLog("error", message.error);
        toast(message.error, "err");
      }
      session.messages.push(message);
      session.updatedAt = now();
      persistSessions();
      repaint();
    } finally {
      setStreaming(false);
      state.abort = null;
      setAgentState("空闲", false);
      scrollToBottom();
    }
  }
  // ---------------------------------------------------------------------
  // Editing
  // ---------------------------------------------------------------------

  function startEdit(index) {
    const session = activeSession();
    const message = session?.messages[index];
    const wrap = $(`.msg[data-index="${index}"]`);
    if (!message || message.role !== "user" || !wrap) return;
    const main = $(".msg__main", wrap);
    if (!main || $(".edit-box", main)) return;

    const original = [message.content, message.attachments];
    main.textContent = "";
    const area = el("textarea", { class: "edit-input" });
    area.value = message.content || "";
    const box = el("div", { class: "edit-box" }, [
      area,
      el("div", { class: "edit-actions" }, [
        el("button", { class: "btn btn--ghost", type: "button", text: "取消" }),
        el("button", { class: "btn btn--primary", type: "button", text: "保存并重新发送" }),
      ]),
    ]);
    main.appendChild(box);
    area.focus();
    area.setSelectionRange(area.value.length, area.value.length);
    area.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        save();
      }
    });
    box.querySelector(".btn--ghost").addEventListener("click", () => {
      message.content = original[0];
      message.attachments = original[1];
      renderChat();
    });
    box.querySelector(".btn--primary").addEventListener("click", save);

    function save() {
      const text = area.value.trim();
      if (!text) {
        toast("内容不能为空", "err");
        return;
      }
      if (state.streaming) {
        toast("正在生成中，请先停止当前回答", "err");
        return;
      }
      message.content = text;
      message.ts = now();
      session.messages = session.messages.slice(0, index + 1);
      session.updatedAt = now();
      persistSessions();
      renderChat();
      requestCompletion(session);
    }
  }

  // ---------------------------------------------------------------------
  // Streaming
  // ---------------------------------------------------------------------

  let streamPaint = { last: 0, timer: null };

  function scrollToBottom(force = false) {
    const scroller = $("#scroll");
    const distance = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    if (force || distance < 160) scroller.scrollTop = scroller.scrollHeight;
  }

  function setStreaming(on) {
    state.streaming = on;
    $("#composer").classList.toggle("is-streaming", on);
    $("#sendBtn").setAttribute("aria-label", on ? "停止生成" : "发送消息");
  }

  async function sendMessage(text) {
    const typed = (text ?? $("#input").value).trim();
    const attachments = state.attachments.slice();
    if ((!typed && !attachments.length) || state.streaming) return;
    if (typed.length > MAX_INPUT) {
      toast(`单条消息最多 ${MAX_INPUT} 个字符`, "err");
      return;
    }

    let session = activeSession();
    if (!session) {
      session = createSession();
      renderSidebar();
    }

    const userMessage = { role: "user", content: typed, ts: now() };
    if (attachments.length) userMessage.attachments = attachments;

    session.messages.push(userMessage);
    session.updatedAt = now();
    if (session.messages.length === 1) {
      session.title = (typed || attachments[0]?.name || "新对话").replace(/\s+/g, " ").slice(0, 26);
    }

    $("#input").value = "";
    state.attachments = [];
    renderAttachList();
    autoGrow();
    updateCounter();
    $("#hero").hidden = true;
    $("#chat").hidden = false;
    $("#chat").appendChild(messageNode(userMessage, session.messages.length - 1));
    renderSidebar();
    state.follow = true;
    scrollToBottom(true);
    persistSessions();

    if (state.settings.mode === "doc" && !desktop) {
      toast("文档模式需要在桌面版使用，可在「下载」页安装", "err");
      return;
    }
    if (state.settings.mode === "code" && !desktop) {
      toast("编程模式需要在桌面版使用，可在「下载」页安装", "err");
      return;
    }
    if (state.settings.mode === "doc") await runDocTask(session, userMessage);
    else if (state.settings.mode === "code") await runCodeTask(session, userMessage);
    else if (state.settings.mode === "work") await runWorkTask(session, userMessage);
    else await requestCompletion(session);
  }

  async function requestCompletion(session) {
    const provider = state.settings.provider || "free";
    const model = state.settings.model || state.config?.defaultModel;
    const assistant = { role: "assistant", content: "", reasoning: "", model, provider, ts: now() };

    const index = session.messages.length;
    const node = assistantShell(assistant, index);
    $("#chat").appendChild(node);
    const body = $(".msg__body", node);
    body.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
    const thinkHost = $(".msg__main", node);

    setStreaming(true);
    autoGrow();
    scrollToBottom(true);
    setAgentState("思考中", true);
    agentLog("info", `对话 · ${modelLabel(model, provider)}`);

    const controller = new AbortController();
    state.abort = controller;

    const payload = {
      messages: session.messages
        .filter((m) => m.role === "user" || (m.role === "assistant" && m.content))
        .map((m) => ({
          role: m.role,
          content: m.role === "user" ? composeUserContent(m) : m.content,
        })),
      model,
      provider,
      apiKey: provider === "byok" ? state.userKey : undefined,
      temperature: Number(state.settings.temperature),
      thinking: Boolean(state.settings.thinking),
      style: state.settings.style,
    };

    let thinkNode = null;
    let errored = false;

    const paint = () => {
      if (!assistant.content && !assistant.reasoning) return;
      body.innerHTML = markdown(assistant.content);
      body.classList.add("caret");
      decorate(body);
      if (assistant.reasoning) {
        if (!thinkNode) {
          thinkNode = thinkingNode(assistant.reasoning, true);
          thinkHost.insertBefore(thinkNode, body);
        } else {
          $(".think__text", thinkNode).textContent = assistant.reasoning;
        }
      }
      if (state.follow) scrollToBottom(true);
    };

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const err = new Error(data.error || `请求失败（${response.status}）`);
        err.status = response.status;
        throw err;
      }
      if (!response.body) throw new Error("当前浏览器不支持流式响应，请更换浏览器。");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) >= 0) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const event = parseEvent(block);
          if (!event) continue;
          if (event.name === "delta") assistant.content += event.data.t || "";
          else if (event.name === "reasoning") assistant.reasoning += event.data.t || "";
          else if (event.name === "error") throw new Error(event.data.message || "生成失败");
          else if (event.name === "meta") {
            assistant.model = event.data.model || assistant.model;
            const tag = $(".msg__head .tag", node);
            if (tag) tag.textContent = modelLabel(assistant.model, assistant.provider);
          }
          schedulePaint();
        }
        schedulePaint(true);
      }
    } catch (error) {
      if (error.name === "AbortError") {
        if (!assistant.content && !assistant.reasoning) node.remove();
        else toast("已停止生成");
      } else {
        errored = true;
        console.error("chat stream failed:", error);
        showError(node, body, error.message || "请求失败，请稍后重试。");
        const keyProblem =
          error.status === 401 || /api key|密钥|key 无效/i.test(error.message || "");
        if (provider === "byok" && keyProblem) {
          setTimeout(() => openKeyModal(model), 500);
        }
      }
    } finally {
      clearTimeout(streamPaint.timer);
      streamPaint.timer = null;
      setStreaming(false);
      state.abort = null;
      setAgentState("空闲", false);
      if (!errored && assistant.content) {
        agentLog("done", `回答完成 · ${assistant.content.length} 字`);
      }
      body.classList.remove("caret");

      if (!errored && (assistant.content || assistant.reasoning)) {
        body.innerHTML = markdown(assistant.content);
        decorate(body);
        if (thinkNode) {
          thinkNode.open = false;
          $(".think__text", thinkNode).textContent = assistant.reasoning;
          $(".think__summary span:last-child", thinkNode).textContent = "思考过程";
        }
        if (assistant.content) session.messages.push(assistant);
        session.updatedAt = now();
        persistSessions();
        scrollToBottom();
        if (!assistant.content) node.remove();
      } else if (!errored) {
        node.remove();
      }
      if (!isMobile()) $("#input").focus({ preventScroll: true });
    }

    function schedulePaint(immediate = false) {
      const gap = 90;
      const delay = Math.max(0, gap - (Date.now() - streamPaint.last));
      if (immediate) {
        streamPaint.last = Date.now();
        paint();
        return;
      }
      if (streamPaint.timer) return;
      streamPaint.timer = setTimeout(() => {
        streamPaint.timer = null;
        streamPaint.last = Date.now();
        paint();
      }, delay);
    }
  }

  function assistantShell(assistant, index) {
    const head = el("div", { class: "msg__head" }, [
      el("strong", { text: "Dream AI" }),
      el("span", { class: "tag", text: modelLabel(assistant.model, assistant.provider) }),
      el("span", { text: timeLabel(assistant.ts) }),
    ]);
    const main = el("div", { class: "msg__main" }, [head, el("div", { class: "msg__body md" })]);
    return el("div", { class: "msg msg--assistant", "data-index": String(index) }, [
      el("div", { class: "msg__avatar", "aria-hidden": "true" }, [
        el("img", { src: "/assets/img/mark.svg", alt: "", width: "18", height: "18" }),
      ]),
      main,
    ]);
  }

  function parseEvent(block) {
    let name = "message";
    const dataLines = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) name = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (!dataLines.length) return null;
    try {
      return { name, data: JSON.parse(dataLines.join("\n")) };
    } catch {
      return null;
    }
  }

  function showError(node, body, message) {
    body.innerHTML = "";
    body.appendChild(
      el("div", { class: "msg__error" }, [
        el("span", {
          html: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16.2v.2"/></svg>',
        }),
        el("span", { text: message }),
      ]),
    );
    const main = $(".msg__main", node);
    main.appendChild(el("div", { class: "msg__actions is-visible" }, [actionBtn("refresh", "重试", () => retry(node))]));
    scrollToBottom();
  }

  function retry(node) {
    node.remove();
    const session = activeSession();
    if (session) requestCompletion(session);
  }

  function regenerate(index) {
    if (state.streaming) {
      toast("正在生成中，请稍后再试", "err");
      return;
    }
    const session = activeSession();
    if (!session) return;
    session.messages = session.messages.slice(0, index);
    renderChat();
    persistSessions();
    requestCompletion(session);
  }

  // ---------------------------------------------------------------------
  // Composer
  // ---------------------------------------------------------------------

  function autoGrow() {
    const input = $("#input");
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
  }

  function updateCounter() {
    const length = $("#input").value.length;
    const counter = $("#counter");
    counter.classList.toggle("is-visible", length >= 800);
    counter.textContent = length >= 800 ? `${length} / ${MAX_INPUT}` : "";
  }

  function models() {
    return state.config?.models || [];
  }

  function modelOption(id, provider = null) {
    return (
      models().find((m) => m.id === id && (provider === null || m.provider === provider)) || null
    );
  }

  function selectModel(model, { silent = false } = {}) {
    if (!model) return;
    if (model.provider === "byok" && !state.userKey) {
      openKeyModal(model.id);
      return;
    }
    state.settings.model = model.id;
    state.settings.provider = model.provider;
    state.settings.thinking = Boolean(model.reasoning);
    $("#thinkBtn").setAttribute("aria-pressed", String(Boolean(model.reasoning)));
    persistSettings();
    syncModelUI();
    closeMenus();
    if (!silent) toast(`已切换至 ${model.label}`);
  }

  function setThinking(on) {
    if (on) {
      const reasoning = models().find((m) => m.reasoning);
      if (!reasoning) {
        toast("当前模型不支持深度思考", "err");
        return;
      }
      if (!state.userKey) {
        openKeyModal(reasoning.id);
        return;
      }
      state.settings.thinking = true;
      state.settings.model = reasoning.id;
      state.settings.provider = "byok";
    } else {
      state.settings.thinking = false;
      if (state.settings.provider === "byok") {
        const fallback =
          models().find((m) => m.provider === "byok" && !m.reasoning) ||
          models().find((m) => m.provider === "free");
        if (fallback) {
          state.settings.model = fallback.id;
          state.settings.provider = fallback.provider;
        }
      }
    }
    $("#thinkBtn").setAttribute("aria-pressed", String(state.settings.thinking));
    syncModelUI();
    persistSettings();
  }

  function syncModelUI() {
    const id = state.settings.model || state.config?.defaultModel;
    const option = modelOption(id, state.settings.provider) || modelOption(id);
    $("#modelLabel").textContent = option?.label || id || "Dream AI";
    const dtbModel = $("#dtbModel");
    if (dtbModel) dtbModel.textContent = option?.label || id || "Dream AI";
    const badge = $("#modelBadge");
    const isKey = state.settings.provider === "byok";
    badge.textContent = isKey ? "Key" : "免费";
    badge.classList.toggle("is-key", isKey);
    const select = $("#modelSelect");
    if (select) select.value = `${state.settings.provider}:${id}`;
    $$("#modelMenu .menu__item").forEach((item) => {
      item.classList.toggle(
        "is-active",
        item.dataset.model === id && item.dataset.provider === state.settings.provider,
      );
    });
    $("#thinkBtn").setAttribute("aria-pressed", String(Boolean(state.settings.thinking)));
  }

  function renderAttachList() {
    const host = $("#attachList");
    host.textContent = "";
    host.hidden = state.attachments.length === 0;
    state.attachments.forEach((file) => {
      const chip = el("span", { class: "attach" }, [
        icon("file"),
        el("span", { text: file.name }),
        el("button", { type: "button", "aria-label": `移除 ${file.name}` }, [
          el("span", { html: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>' }),
        ]),
      ]);
      chip.querySelector("button").addEventListener("click", () => {
        state.attachments = state.attachments.filter((item) => item !== file);
        renderAttachList();
      });
      host.appendChild(chip);
    });
  }

  async function addFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    for (const file of files) {
      if (state.attachments.length >= MAX_FILES) {
        toast(`最多添加 ${MAX_FILES} 个文件`, "err");
        break;
      }
      if (!/\.(txt|md|markdown|csv|json|py|js|ts|html|css|yaml|yml|log|xml)$/i.test(file.name)) {
        toast(`暂不支持 ${file.name}，请上传文本类文件`, "err");
        continue;
      }
      if (file.size > 600 * 1024) {
        toast(`${file.name} 超过 600KB`, "err");
        continue;
      }
      if (state.attachments.some((item) => item.name === file.name)) continue;
      try {
        const text = (await file.text()).slice(0, MAX_FILE_CHARS);
        if (!text.trim()) {
          toast(`${file.name} 是空文件`, "err");
          continue;
        }
        const total = state.attachments.reduce((sum, item) => sum + item.text.length, 0) + text.length;
        if (total > MAX_TOTAL_ATTACH) {
          toast("附件总内容过长，请减少文件", "err");
          continue;
        }
        state.attachments.push({ name: file.name, text });
      } catch {
        toast(`读取 ${file.name} 失败`, "err");
      }
    }
    renderAttachList();
  }

  function initVoice() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const mic = $("#micBtn");
    if (!Recognition || !mic) return;
    mic.hidden = false;
    const input = $("#input");
    const recognition = new Recognition();
    recognition.lang = "zh-CN";
    recognition.interimResults = true;
    recognition.continuous = false;
    let listening = false;
    let base = "";

    recognition.onresult = (event) => {
      let finalText = "";
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += piece;
        else interim += piece;
      }
      input.value = `${base}${finalText}${interim}`.trim();
      autoGrow();
      updateCounter();
    };
    recognition.onend = () => {
      listening = false;
      mic.classList.remove("is-recording");
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted" && event.error !== "no-speech") toast("语音识别失败，请重试", "err");
    };

    mic.addEventListener("click", () => {
      if (listening) {
        recognition.stop();
        return;
      }
      base = input.value ? `${input.value} ` : "";
      try {
        recognition.start();
        listening = true;
        mic.classList.add("is-recording");
        toast("正在听，请说话…");
      } catch {
        toast("无法启动语音识别", "err");
      }
    });
  }

  // ---------------------------------------------------------------------
  // Menus
  // ---------------------------------------------------------------------

  let openMenu = null;

  function closeMenus() {
    ["#modelMenu", "#styleMenu", "#sessionMenu", "#modeMenu", "#docTemplateMenu"].forEach((sel) => {
      const menu = $(sel);
      if (menu) menu.hidden = true;
    });
    $("#modelBtn")?.setAttribute("aria-expanded", "false");
    $("#styleBtn")?.setAttribute("aria-expanded", "false");
    $("#modeBtn")?.setAttribute("aria-expanded", "false");
    $("#docTemplateBtn")?.setAttribute("aria-expanded", "false");
    openMenu = null;
  }

  function positionMenu(menu, anchor, align = "left") {
    menu.hidden = false;
    const rect = anchor.getBoundingClientRect();
    const width = menu.offsetWidth;
    const height = menu.offsetHeight;
    let left = align === "right" ? rect.right - width : rect.left;
    let top = rect.bottom + 6;
    if (top + height > window.innerHeight - 8) top = rect.top - height - 6;
    left = Math.max(8, Math.min(left, window.innerWidth - width - 8));
    top = Math.max(8, top);
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
    openMenu = menu;
  }

  function buildModelMenu() {
    const menu = $("#modelMenu");
    menu.textContent = "";

    const addGroup = (label, list) => {
      if (!list.length) return;
      menu.appendChild(el("div", { class: "menu__label", text: label }));
      list.forEach((model) => {
        const locked = model.provider === "byok" && !state.userKey;
        const item = el("button", {
          class: "menu__item",
          type: "button",
          role: "option",
          "data-model": model.id,
          "data-provider": model.provider,
        }, [
          el("span", { class: "menu__item__main" }, [
            el("strong", { text: model.label }),
            el("span", {
              text: locked ? `${model.hint} · 需填写 Key` : model.hint,
            }),
          ]),
          el("span", {
            html: '<svg class="menu__check" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
          }),
        ]);
        item.addEventListener("click", () => selectModel(model));
        menu.appendChild(item);
      });
    };

    addGroup("免费模型", models().filter((m) => m.provider === "free"));
    addGroup("使用自己的 Key", models().filter((m) => m.provider === "byok"));

    menu.appendChild(el("div", { class: "menu__divider" }));
    const help = el("button", { class: "menu__item menu__item--help", type: "button" }, [
      el("span", { class: "menu__item__main" }, [
        el("strong", { text: state.userKey ? "管理我的 Key" : "如何获取 Key？" }),
        el("span", {
          text: state.userKey ? "已保存 · 可更新或清除" : "用你自己的 DeepSeek 额度",
        }),
      ]),
      el("span", {
        html: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M9 7h8v8"/></svg>',
      }),
    ]);
    help.addEventListener("click", () => {
      closeMenus();
      openKeyModal();
    });
    menu.appendChild(help);

    syncModelUI();
  }

  function openSessionMenu(session, anchor) {
    closeMenus();
    const menu = $("#sessionMenu");
    menu.textContent = "";
    menu.className = "menu menu--fixed";

    const rename = el("button", { class: "menu__item", type: "button" }, [
      icon("edit"),
      el("span", { class: "menu__item__main" }, [el("strong", { text: "重命名" })]),
    ]);
    rename.addEventListener("click", () => {
      closeMenus();
      openRename(session);
    });

    const download = el("button", { class: "menu__item", type: "button" }, [
      icon("download"),
      el("span", { class: "menu__item__main" }, [el("strong", { text: "导出此对话" })]),
    ]);
    download.addEventListener("click", () => {
      closeMenus();
      exportSession(session);
    });

    const remove = el("button", { class: "menu__item", type: "button" }, [
      icon("trash"),
      el("span", { class: "menu__item__main" }, [el("strong", { text: "删除" })]),
    ]);
    remove.addEventListener("click", () => {
      closeMenus();
      removeSession(session.id);
    });
    remove.style.color = "var(--danger)";

    menu.append(rename, download, remove);
    positionMenu(menu, anchor, "right");
  }

  function buildStyleMenu() {
    const menu = $("#styleMenu");
    menu.textContent = "";
    STYLES.forEach((style) => {
      const item = el("button", {
        class: `menu__item${state.settings.style === style.id ? " is-active" : ""}`,
        type: "button",
        "data-style": style.id,
      }, [
        el("span", { class: "menu__item__main" }, [
          el("strong", { text: style.label }),
          el("span", { text: style.desc }),
        ]),
        el("span", {
          html: '<svg class="menu__check" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
        }),
      ]);
      item.addEventListener("click", () => {
        state.settings.style = style.id;
        $("#styleLabel").textContent = style.label;
        persistSettings();
        closeMenus();
      });
      menu.appendChild(item);
    });
  }

  // ---------------------------------------------------------------------
  // Modals
  // ---------------------------------------------------------------------

  let renameTarget = null;
  let pendingModelId = null;

  function pendingKeyStatus() {
    return state.userKey ? `已配置 · ${state.userKey.slice(0, 6)}…${state.userKey.slice(-4)}` : "未配置 · 使用免费模型";
  }

  function updateKeyStatus() {
    const status = $("#keyStatus");
    if (status) status.textContent = pendingKeyStatus();
    const clear = $("#keyClear");
    if (clear) clear.hidden = !state.userKey;
  }

  function openKeyModal(modelId = null) {
    closeMenus();
    pendingModelId = modelId;
    const input = $("#keyInput");
    input.value = "";
    input.placeholder = state.userKey ? "已保存 · 粘贴新 Key 可更新" : "sk-...";
    updateKeyStatus();
    openModal("keyModal");
    setTimeout(() => input.focus(), 40);
  }

  function saveUserKey() {
    const key = $("#keyInput").value.trim();
    if (!/^[A-Za-z0-9_.\-]{20,200}$/.test(key)) {
      toast("Key 格式看起来不对，请检查后重试", "err");
      return;
    }
    state.userKey = key;
    try {
      localStorage.setItem(STORE_USER_KEY, key);
    } catch {
      toast("浏览器不允许保存，可能是隐私模式", "err");
    }
    updateKeyStatus();
    buildModelMenu();
    closeModal($("#keyModal"));
    const target = pendingModelId ? modelOption(pendingModelId, "byok") : null;
    pendingModelId = null;
    if (target) selectModel(target, { silent: true });
    syncModelUI();
    toast(target ? `已保存 Key，切换到 ${target.label}` : "已保存 Key");
  }

  function clearUserKey() {
    state.userKey = "";
    try {
      localStorage.removeItem(STORE_USER_KEY);
    } catch {
      /* ignore */
    }
    updateKeyStatus();
    buildModelMenu();
    if (state.settings.provider === "byok") {
      const free = models().find((m) => m.provider === "free");
      if (free) selectModel(free, { silent: true });
    }
    syncModelUI();
    closeModal($("#keyModal"));
    toast("已清除本机保存的 Key");
  }

  function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.hidden = false;
    const focusable = modal.querySelector(".modal__close") || modal.querySelector("input") || modal.querySelector("button");
    setTimeout(() => focusable && focusable.focus(), 20);
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.hidden = true;
  }

  function closeTopModal() {
    const openModals = $$(".modal").filter((m) => !m.hidden);
    if (openModals.length) closeModal(openModals[openModals.length - 1]);
    return openModals.length > 0;
  }

  function openRename(session) {
    renameTarget = session.id;
    const input = $("#renameInput");
    input.value = session.title || "";
    openModal("renameModal");
    setTimeout(() => {
      input.focus();
      input.select();
    }, 30);
  }

  function saveRename() {
    const session = state.sessions.find((s) => s.id === renameTarget);
    if (!session) return;
    const title = $("#renameInput").value.trim() || "新对话";
    session.title = title.slice(0, 40);
    persistSessions();
    renderSidebar();
    closeModal($("#renameModal"));
    toast("已重命名");
  }

  // ---------------------------------------------------------------------
  // Export
  // ---------------------------------------------------------------------

  function download(name, content, type = "text/markdown;charset=utf-8") {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = el("a", { href: url, download: name });
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  function sessionMarkdown(session) {
    const lines = [`# ${session.title}`, `时间：${new Date(session.createdAt).toLocaleString("zh-CN")}`, ""];
    for (const message of session.messages) {
      if (message.role === "user") {
        lines.push("**你**：", message.content || "");
        if (message.attachments?.length) {
          lines.push(`> 附件：${message.attachments.map((f) => f.name).join("、")}`);
        }
        lines.push("");
      } else if (message.kind === "doc" && message.document) {
        lines.push("**Dream AI（文档模式）**：", `已生成 ${message.document.name}（${message.document.path}）`, "");
      } else if (message.kind === "code") {
        lines.push("**Dream AI（编程模式）**：", `${message.title || "项目"} · ${message.error || message.status || ""}`, "");
        if (message.project) {
          lines.push(`目录：${message.project.root}`);
          if (message.url) lines.push(`地址：${message.url}`);
          lines.push("");
        }
        (message.files || []).forEach((file) => lines.push(`- ${file}`));
        if (message.log) lines.push("", "```", message.log.slice(-6000), "```", "");
      } else if (message.kind === "work") {
        lines.push("**Dream AI（工作模式）**：", message.title || "任务", "");
        (message.steps || []).forEach((step, index) => {
          lines.push(`${index + 1}. ${step.title}`, step.output || "", "");
        });
        if (message.final) lines.push("最终结果：", message.final, "");
      } else {
        lines.push("**Dream AI**：", message.content, "");
      }
    }
    return lines.join("\n");
  }

  function exportSession(session) {
    download(`dreamai-${(session.title || "chat").slice(0, 20)}.md`, sessionMarkdown(session));
    toast("已导出此对话");
  }

  function exportAll() {
    if (!state.sessions.length) {
      toast("还没有可导出的对话", "err");
      return;
    }
    const ordered = [...state.sessions].sort((a, b) => a.createdAt - b.createdAt);
    const body = ordered.map(sessionMarkdown).join("\n\n---\n\n");
    download(`dreamai-${new Date().toISOString().slice(0, 10)}.md`, `# Dream AI 对话记录\n\n${body}\n`);
    toast("已导出为 Markdown");
  }

  // ---------------------------------------------------------------------
  // Sidebar (mobile)
  // ---------------------------------------------------------------------

  function openSidebar() {
    document.body.classList.add("sidebar-open");
    $("#scrim").hidden = false;
  }

  function closeSidebar() {
    document.body.classList.remove("sidebar-open");
    $("#scrim").hidden = true;
  }

  // ---------------------------------------------------------------------
  // Settings
  // ---------------------------------------------------------------------

  function buildSettings() {
    const select = $("#modelSelect");
    select.textContent = "";

    const addGroup = (label, list) => {
      if (!list.length) return;
      const group = el("optgroup", { label });
      list.forEach((model) => {
        group.appendChild(el("option", { value: `${model.provider}:${model.id}`, text: model.label }));
      });
      select.appendChild(group);
    };
    addGroup("免费模型", models().filter((m) => m.provider === "free"));
    addGroup("使用自己的 Key", models().filter((m) => m.provider === "byok"));
    select.value = `${state.settings.provider}:${state.settings.model}`;

    select.addEventListener("change", () => {
      const [provider, ...rest] = select.value.split(":");
      const target = modelOption(rest.join(":"));
      if (!target) return;
      if (provider === "byok" && !state.userKey) {
        openKeyModal(target.id);
        syncModelUI();
        return;
      }
      selectModel(target, { silent: true });
    });

    $("#manageKeyBtn").addEventListener("click", () => openKeyModal());
    $("#keySave").addEventListener("click", saveUserKey);
    $("#keyClear").addEventListener("click", clearUserKey);
    $("#keyInput").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        saveUserKey();
      }
    });

    const range = $("#tempRange");
    range.value = String(state.settings.temperature ?? 0.7);
    const paintRange = () => {
      const pct = (Number(range.value) / Number(range.max)) * 100;
      range.style.setProperty("--fill", `${pct}%`);
      $("#tempValue").textContent = Number(range.value).toFixed(1);
    };
    paintRange();
    range.addEventListener("input", () => {
      state.settings.temperature = Number(range.value);
      paintRange();
      persistSettings();
    });

    $$("#themeSeg button").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.settings.theme = btn.dataset.themeValue;
        persistSettings();
        applyTheme();
      });
    });

    $$("#sizeSeg button").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.settings.size = btn.dataset.sizeValue;
        persistSettings();
        applySize();
      });
    });

    $("#clearBtn").addEventListener("click", () => openModal("confirmModal"));
  }

  // ---------------------------------------------------------------------
  // Desktop workbench (only inside the Electron app)
  // ---------------------------------------------------------------------

  const desktop = window.dreamDesktop || null;
  const STORE_ARTIFACTS = "dreamai.artifacts.v1";
  let deskAction = null;
  let agentEvents = [];
  let agentArtifacts = [];

  function setAgentState(text, busy) {
    const node = $("#agentState");
    if (!node) return;
    node.textContent = text;
    node.classList.toggle("is-busy", Boolean(busy));
  }

  function agentLog(kind, text) {
    if (!desktop) return;
    agentEvents.push({ kind, text, ts: Date.now() });
    if (agentEvents.length > 80) agentEvents = agentEvents.slice(-80);
    renderAgentActivity();
  }

  function renderAgentActivity() {
    const host = $("#agentActivity");
    if (!host) return;
    host.textContent = "";
    if (!agentEvents.length) {
      host.appendChild(
        el("div", {
          class: "agent-panel__empty",
          text: "还没有操作记录。\n在对话、工作或文档模式里发一条消息试试。",
        }),
      );
      return;
    }
    agentEvents.forEach((event) => {
      const time = new Date(event.ts).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
      host.appendChild(
        el("div", { class: `agent-event is-${event.kind}` }, [
          el("span", { class: "agent-event__dot" }),
          el("span", { class: "agent-event__text", text: event.text }),
          el("time", { text: time }),
        ]),
      );
    });
    host.scrollTop = host.scrollHeight;
  }

  function loadArtifacts() {
    try {
      const raw = localStorage.getItem(STORE_ARTIFACTS);
      const data = raw ? JSON.parse(raw) : [];
      agentArtifacts = Array.isArray(data) ? data.filter((item) => item && item.path) : [];
    } catch {
      agentArtifacts = [];
    }
  }

  function persistArtifacts() {
    try {
      localStorage.setItem(STORE_ARTIFACTS, JSON.stringify(agentArtifacts.slice(0, 30)));
    } catch {
      /* ignore */
    }
  }

  function addArtifact(doc) {
    if (!doc || !doc.path) return;
    agentArtifacts = agentArtifacts.filter((item) => item.path !== doc.path);
    agentArtifacts.unshift({ ...doc, mtime: Date.now() });
    agentArtifacts = agentArtifacts.slice(0, 30);
    persistArtifacts();
    renderAgentArtifacts();
  }

  function renderAgentArtifacts() {
    const host = $("#agentArtifacts");
    if (!host) return;
    host.textContent = "";
    const count = $("#artifactCount");
    if (count) count.textContent = String(agentArtifacts.length);
    if (!agentArtifacts.length) {
      host.appendChild(
        el("div", {
          class: "agent-panel__empty",
          text: "生成的 Word / Excel / PPT / PDF 会出现在这里。",
        }),
      );
      return;
    }
    agentArtifacts.forEach((doc) => {
      const row = el("div", { class: "artifact" }, [
        el("span", {
          class: "artifact__icon",
          "data-type": doc.type,
          text: String(doc.type || "").toUpperCase(),
        }),
        el("div", { class: "artifact__meta" }, [
          el("strong", { text: doc.name, title: doc.path }),
          el("em", { text: `${doc.sizeLabel || ""} · ${doc.typeLabel || ""}` }),
        ]),
      ]);
      const actions = el("div", { class: "artifact__actions" });
      const open = el("button", { type: "button", title: "打开" }, [icon("open")]);
      open.addEventListener("click", () => desktop.documents.open(doc.path).catch((error) => toast(error.message, "err")));
      const reveal = el("button", { type: "button", title: "在文件夹中显示" }, [icon("folder")]);
      reveal.addEventListener("click", () =>
        desktop.documents.reveal(doc.path).catch((error) => toast(error.message, "err")),
      );
      actions.append(open, reveal);
      row.appendChild(actions);
      host.appendChild(row);
    });
  }

  async function refreshArtifacts() {
    if (!desktop) return;
    try {
      const info = await desktop.getWorkspace();
      if (!info.exists) return;
      const list = await desktop.documents.list();
      if (Array.isArray(list)) {
        agentArtifacts = list;
        persistArtifacts();
        renderAgentArtifacts();
      }
    } catch {
      /* ignore */
    }
  }

  function updateAgentWorkspace(pathText) {
    const node = $("#agentWorkspacePath");
    if (node) node.textContent = pathText || "未选择工作文件夹";
  }

  async function refreshDesktop() {
    if (!desktop) return;
    const info = await desktop.getWorkspace();
    const pathEl = $("#deskPath");
    if (!info.exists) {
      pathEl.textContent = "尚未选择文件夹";
      updateAgentWorkspace("");
      $("#deskOpen").disabled = true;
      $("#deskStats").hidden = true;
      $("#deskTools").hidden = true;
      $("#deskCats").textContent = "";
      $("#deskPreview").hidden = true;
      return;
    }
    pathEl.textContent = info.workspace;
    updateAgentWorkspace(info.workspace);
    $("#deskOpen").disabled = false;
    const scan = await desktop.scan();
    $("#deskStats").hidden = false;
    $("#deskTools").hidden = false;
    $("#deskFiles").textContent = scan.files;
    $("#deskFolders").textContent = scan.folders;
    $("#deskSize").textContent = scan.sizeLabel;
    const cats = $("#deskCats");
    cats.textContent = "";
    Object.entries(scan.byCategory)
      .sort((a, b) => b[1] - a[1])
      .forEach(([name, count]) => cats.appendChild(el("span", { text: `${name} ${count}` })));
  }

  function showDeskPreview(title, lines) {
    $("#deskPreview").hidden = false;
    $("#deskPreviewTitle").textContent = title;
    const list = $("#deskPreviewList");
    list.textContent = "";
    lines.slice(0, 80).forEach((line) => list.appendChild(el("li", { text: line })));
    if (lines.length > 80) {
      list.appendChild(el("li", { text: `…… 还有 ${lines.length - 80} 项` }));
    }
  }

  async function initDesktop() {
    if (!desktop) return;
    $("#desktopBtn").hidden = false;
    $("#desktopTitlebar").hidden = false;
    $("#agentToggle").hidden = false;
    document.body.classList.add("desktop-app");

    if (desktop.window) {
      $("#winMin").addEventListener("click", () => desktop.window.minimize());
      $("#winMax").addEventListener("click", () => desktop.window.toggleMaximize());
      $("#winClose").addEventListener("click", () => desktop.window.close());
      $("#dtbDrag").addEventListener("dblclick", () => desktop.window.toggleMaximize());
      desktop.window.onMaximized?.((maximized) => {
        document.body.classList.toggle("is-maximized", maximized);
      });
    }

    const panel = $("#agentPanel");
    panel.hidden = localStorage.getItem("dreamai.agentPanel") === "0";
    $("#agentToggle").addEventListener("click", () => {
      panel.hidden = !panel.hidden;
      localStorage.setItem("dreamai.agentPanel", panel.hidden ? "0" : "1");
    });

    const showAgentTab = (name) => {
      $$("[data-agent-tab]").forEach((btn) => btn.classList.toggle("is-active", btn.dataset.agentTab === name));
      $("#agentActivity").hidden = name !== "activity";
      $("#agentArtifacts").hidden = name !== "artifacts";
      if (name === "artifacts") refreshArtifacts();
    };
    $$("[data-agent-tab]").forEach((btn) => {
      btn.addEventListener("click", () => showAgentTab(btn.dataset.agentTab));
    });

    $("#agentPick").addEventListener("click", async () => {
      try {
        const result = await desktop.pickFolder();
        if (!result.canceled) {
          toast("工作文件夹已设置");
          await refreshDesktop();
          await refreshArtifacts();
        }
      } catch (error) {
        toast(error.message, "err");
      }
    });

    $("#agentOpenWorkbench").addEventListener("click", () => {
      openModal("desktopModal");
      refreshDesktop().catch(() => {});
    });

    loadArtifacts();
    renderAgentActivity();
    renderAgentArtifacts();
    desktop
      .getWorkspace()
      .then((info) => updateAgentWorkspace(info.exists ? info.workspace : ""))
      .catch(() => {});
    refreshArtifacts();

    const download = $("#downloadLink");
    if (download) download.hidden = true;

    $("#desktopBtn").addEventListener("click", () => {
      openModal("desktopModal");
      refreshDesktop().catch((error) => toast(error.message, "err"));
    });

    $("#deskPick").addEventListener("click", async () => {
      try {
        const result = await desktop.pickFolder();
        if (!result.canceled) {
          toast("工作文件夹已设置");
          await refreshDesktop();
        }
      } catch (error) {
        toast(error.message, "err");
      }
    });

    $("#deskOpen").addEventListener("click", () => desktop.openWorkspace().catch(() => {}));

    $("#deskOrganize").addEventListener("click", async () => {
      try {
        const plan = await desktop.planOrganize();
        if (!plan.total) {
          toast("没有可整理的文件", "err");
          return;
        }
        deskAction = "organize";
        showDeskPreview(
          `按类型整理 · ${plan.total} 个文件`,
          plan.moves.map((move) => `${move.from}  →  ${move.to}`),
        );
      } catch (error) {
        toast(error.message, "err");
      }
    });

    $("#deskRename").addEventListener("click", async () => {
      try {
        const prefix = $("#deskPrefix").value.trim() || "Dream";
        const plan = await desktop.planRename(prefix);
        if (!plan.total) {
          toast("没有需要重命名的文件", "err");
          return;
        }
        deskAction = "rename";
        showDeskPreview(
          `批量重命名 · ${plan.total} 个文件`,
          plan.changes.map((change) => `${change.from}  →  ${change.to}`),
        );
      } catch (error) {
        toast(error.message, "err");
      }
    });

    $("#deskSave").addEventListener("click", async () => {
      try {
        const session = activeSession();
        if (!session || !session.messages.length) {
          toast("当前没有可保存的对话", "err");
          return;
        }
        const name = $("#deskDocName").value.trim() || "Dream AI 对话";
        const result = await desktop.saveText(name, sessionMarkdown(session));
        if (result.canceled) return;
        toast(`已保存：${result.name}`);
        await refreshDesktop();
      } catch (error) {
        toast(error.message, "err");
      }
    });

    $("#deskCancel").addEventListener("click", () => {
      deskAction = null;
      $("#deskPreview").hidden = true;
    });

    $("#deskApply").addEventListener("click", async () => {
      if (!deskAction) return;
      try {
        const result =
          deskAction === "organize" ? await desktop.applyOrganize() : await desktop.applyRename();
        const action = deskAction;
        deskAction = null;
        $("#deskPreview").hidden = true;
        if (result.canceled) {
          toast("已取消，没有修改任何文件");
          return;
        }
        const count = action === "organize" ? result.moved : result.renamed;
        toast(`已完成：${count} 个文件`);
        if (result.errors && result.errors.length) {
          toast(`${result.errors.length} 个文件处理失败`, "err");
        }
        await refreshDesktop();
      } catch (error) {
        toast(error.message, "err");
      }
    });
  }

  // ---------------------------------------------------------------------
  // Config & boot
  // ---------------------------------------------------------------------

  async function loadConfig() {
    try {
      const response = await fetch("/api/config", { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("config");
      state.config = await response.json();
    } catch {
      state.config = {
        configured: false,
        models: [{ id: "glm-4-flash", label: "GLM-4-Flash", provider: "free", reasoning: false, hint: "免费" }],
        defaultModel: "glm-4-flash",
        version: "1.2.0",
      };
    }

    if (!state.settings.model || !modelOption(state.settings.model)) {
      state.settings.model = state.config.defaultModel || models()[0]?.id;
      state.settings.provider = modelOption(state.settings.model)?.provider || "free";
    }
    let current = modelOption(state.settings.model, state.settings.provider);
    if (!current) {
      const fallback = modelOption(state.settings.model);
      if (fallback) {
        state.settings.provider = fallback.provider;
        current = fallback;
      }
    }

    // A BYOK model without a saved key falls back to the free model.
    if (state.settings.provider === "byok" && !state.userKey) {
      const free = models().find((m) => m.provider === "free") || models()[0];
      if (free) {
        state.settings.model = free.id;
        state.settings.provider = free.provider;
      }
      state.settings.thinking = false;
    }
    current = modelOption(state.settings.model, state.settings.provider) || modelOption(state.settings.model);
    if (current?.reasoning && state.userKey) state.settings.thinking = true;

    buildModelMenu();
    buildSettings();
    buildStyleMenu();
    buildModeMenu();
    buildDocTemplateMenu();
    updateKeyStatus();
    updateModeUI();
    syncModelUI();
    $("#styleLabel").textContent = STYLES.find((s) => s.id === state.settings.style)?.label || "通用";

    if (state.config.version) $("#aboutVersion").textContent = `v${state.config.version}`;

    const freeStatus = $("#freeStatus");
    if (freeStatus && state.config.free) {
      freeStatus.textContent = state.config.free.configured
        ? `${state.config.free.label} · 无需 Key`
        : `${state.config.free.label} · 服务端未配置`;
    }

    if (!state.config.configured) {
      const badge = $("#statusBadge");
      badge.hidden = false;
      $("span", badge).textContent = "免费模型暂未开放 · 请使用自己的 Key";
      badge.title = "在设置 → 模型来源 → 管理，填入自己的 DeepSeek Key";
    }
  }

  function initEvents() {
    $("#composer").addEventListener("submit", (event) => {
      event.preventDefault();
      if (state.streaming) {
        state.abort?.abort();
        return;
      }
      sendMessage();
    });

    const input = $("#input");
    input.addEventListener("input", () => {
      autoGrow();
      updateCounter();
    });
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey) return;
      if (event.isComposing || event.keyCode === 229) return;
      if (isMobile()) return;
      event.preventDefault();
      if (!state.streaming) sendMessage();
    });

    $("#newChatBtn").addEventListener("click", () => {
      if (state.streaming) {
        toast("正在生成中，请先停止当前回答", "err");
        return;
      }
      const current = activeSession();
      if (current && current.messages.length === 0) {
        closeSidebar();
        input.focus();
        return;
      }
      createSession();
      renderSidebar();
      renderChat();
      closeSidebar();
      if (!isMobile()) input.focus();
    });

    $("#searchInput").addEventListener("input", (event) => {
      state.search = event.target.value;
      renderSidebar();
    });

    $$(".card").forEach((card) => {
      card.addEventListener("click", () => {
        if (!card.dataset.prompt || state.streaming) return;
        sendMessage(card.dataset.prompt);
      });
    });

    $("#aboutBtn").addEventListener("click", () => {
      closeSidebar();
      openModal("aboutModal");
    });
    $("#aboutBtnTop").addEventListener("click", () => openModal("aboutModal"));
    $("#settingsBtn").addEventListener("click", () => openModal("settingsModal"));
    $("#exportBtn").addEventListener("click", exportAll);
    $("#clearAllBtn").addEventListener("click", () => {
      if (!state.sessions.length) {
        toast("还没有对话记录", "err");
        return;
      }
      openModal("confirmModal");
    });

    $("#shortcutsBtn").addEventListener("click", () => openModal("shortcutsModal"));
    $("#shortcutsBtn2").addEventListener("click", () => openModal("shortcutsModal"));

    $("#confirmYes").addEventListener("click", () => {
      state.sessions = [];
      state.activeId = null;
      state.search = "";
      $("#searchInput").value = "";
      persistSessions();
      renderSidebar();
      renderChat();
      closeModal($("#confirmModal"));
      toast("已清空全部对话");
    });

    $$("[data-close]").forEach((node) => {
      node.addEventListener("click", () => closeModal(node.closest(".modal")));
    });

    $("#renameSave").addEventListener("click", saveRename);
    $("#renameInput").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        saveRename();
      }
    });

    $("#themeBtn").addEventListener("click", () => {
      state.settings.theme = resolvedTheme() === "dark" ? "light" : "dark";
      persistSettings();
      applyTheme();
    });

    $("#thinkBtn").addEventListener("click", () => setThinking(!state.settings.thinking));

    $("#modelBtn").addEventListener("click", (event) => {
      event.stopPropagation();
      if (openMenu === $("#modelMenu")) {
        closeMenus();
        return;
      }
      closeMenus();
      const menu = $("#modelMenu");
      menu.hidden = false;
      $("#modelBtn").setAttribute("aria-expanded", "true");
      openMenu = menu;
    });

    $("#styleBtn").addEventListener("click", (event) => {
      event.stopPropagation();
      if (openMenu === $("#styleMenu")) {
        closeMenus();
        return;
      }
      closeMenus();
      positionMenu($("#styleMenu"), $("#styleBtn"));
      $("#styleBtn").setAttribute("aria-expanded", "true");
    });

    $("#modeBtn").addEventListener("click", (event) => {
      event.stopPropagation();
      if (openMenu === $("#modeMenu")) {
        closeMenus();
        return;
      }
      closeMenus();
      positionMenu($("#modeMenu"), $("#modeBtn"));
      $("#modeBtn").setAttribute("aria-expanded", "true");
    });
    $("#docTemplateBtn").addEventListener("click", (event) => {
      event.stopPropagation();
      if (openMenu === $("#docTemplateMenu")) {
        closeMenus();
        return;
      }
      closeMenus();
      positionMenu($("#docTemplateMenu"), $("#docTemplateBtn"));
      $("#docTemplateBtn").setAttribute("aria-expanded", "true");
    });

    document.addEventListener("click", (event) => {
      if (
        event.target.closest(".menu") ||
        event.target.closest("#modelBtn") ||
        event.target.closest("#styleBtn") ||
        event.target.closest("#modeBtn") ||
        event.target.closest("#docTemplateBtn") ||
        event.target.closest(".session__more")
      ) {
        return;
      }
      closeMenus();
    });

    const scroller = $("#scroll");
    scroller.addEventListener(
      "scroll",
      () => {
        const topbar = $(".topbar");
        if (topbar) topbar.classList.toggle("is-scrolled", scroller.scrollTop > 6);
        const distance = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
        if (state.streaming) {
          if (distance > 260) state.follow = false;
          else if (distance < 80) state.follow = true;
        }
        const toBottom = $("#toBottom");
        if (toBottom) toBottom.hidden = distance < 420;
      },
      { passive: true },
    );

    $("#toBottom").addEventListener("click", () => {
      state.follow = true;
      scrollToBottom(true);
    });

    $("#menuBtn").addEventListener("click", openSidebar);
    $("#scrim").addEventListener("click", closeSidebar);

    $("#collapseBtn").addEventListener("click", () => {
      if (isMobile()) {
        closeSidebar();
        return;
      }
      document.body.classList.add("sidebar-collapsed");
      localStorage.setItem("dreamai.sidebar", "1");
      toast("侧边栏已收起，点击左上角按钮可展开");
    });
    $("#expandBtn").addEventListener("click", () => {
      document.body.classList.remove("sidebar-collapsed");
      localStorage.setItem("dreamai.sidebar", "0");
    });

    $("#attachBtn").addEventListener("click", () => $("#fileInput").click());
    $("#fileInput").addEventListener("change", (event) => {
      addFiles(event.target.files);
      event.target.value = "";
    });

    document.addEventListener("dragover", (event) => event.preventDefault());
    document.addEventListener("drop", (event) => {
      event.preventDefault();
      if (event.dataTransfer?.files?.length) addFiles(event.dataTransfer.files);
    });

    window.addEventListener("resize", closeMenus);

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        if (closeTopModal()) return;
        if (openMenu) {
          closeMenus();
          return;
        }
        if (state.streaming) state.abort?.abort();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        $("#newChatBtn").click();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        if (document.body.classList.contains("sidebar-collapsed")) {
          document.body.classList.remove("sidebar-collapsed");
          localStorage.setItem("dreamai.sidebar", "0");
        } else {
          document.body.classList.add("sidebar-collapsed");
          localStorage.setItem("dreamai.sidebar", "1");
        }
      }
      if ((event.ctrlKey || event.metaKey) && event.key === "/") {
        event.preventDefault();
        openModal("shortcutsModal");
      }
    });

    window.addEventListener("beforeunload", (event) => {
      if (state.streaming) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  }

  function init() {
    loadStorage();
    initTheme();
    setGreeting();
    initEvents();
    initVoice();
    initDesktop();
    renderAttachList();
    $("#styleLabel").textContent = STYLES.find((s) => s.id === state.settings.style)?.label || "通用";

    if (localStorage.getItem("dreamai.sidebar") === "1" && !isMobile()) {
      document.body.classList.add("sidebar-collapsed");
    }

    const last = state.sessions[0];
    state.activeId = last ? last.id : null;

    renderSidebar();
    renderChat();
    loadConfig().then(() => {
      if (!isMobile()) $("#input").focus({ preventScroll: true });
    });

    fetch("/api/health", { headers: { Accept: "application/json" } }).catch(() => {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
