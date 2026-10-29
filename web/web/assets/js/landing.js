/* ==========================================================================
   Dream AI — landing page stories
   - a greeting that types / pauses / deletes
   - a terminal prompt ticker that can fill the composer
   - tiny mutations that make the app shell feel alive
   ========================================================================== */
(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const dream = window.DreamMotion;

  if (!dream) return;

  const genericGreetings = ["你好呀", "欢迎回来", "一起造梦吧"];

  function timeGreeting(now = new Date()) {
    const hour = now.getHours();
    if (hour >= 5 && hour < 9) return "早上好";
    if (hour < 12) return "上午好";
    if (hour < 14) return "中午好";
    if (hour < 18) return "下午好";
    if (hour < 23) return "晚上好";
    return "夜深了";
  }

  function greetingWords() {
    return [timeGreeting(), ...genericGreetings];
  }

  function syncGreetingLabel() {
    const title = greetingNode?.closest(".hero__title");
    if (title) title.setAttribute("aria-label", `${timeGreeting()}，我是 Dream。`);
  }

  const prompts = [
    "把今晚的灵感，写成一个世界。",
    "帮我设计一个会呼吸的个人主页。",
    "用 Python 写一个带类型注解的小工具。",
    "把这段经历，写成一封不落俗套的信。",
    "为一款宇宙主题的咖啡店起 10 个名字。",
    "拆解一下：如何在一年内学会数据分析？",
  ];

  const greetingNode = $("#greetingText");
  const terminal = $("#heroTerminal");
  const terminalNode = $("#heroTyped");
  const input = $("#input");
  const hero = $("#hero");

  let greetingWriter = null;
  let terminalWriter = null;
  let activePrompt = prompts[0];
  let heroVisible = !hero?.hidden;
  let lastDaypart = timeGreeting();

  function startGreeting() {
    if (!greetingNode) return;
    greetingWriter?.stop();
    syncGreetingLabel();
    if (!dream.enabled) {
      greetingNode.textContent = timeGreeting();
      return;
    }
    greetingWriter = dream.typewriter(greetingNode, {
      words: greetingWords(),
      initial: "",
      typeSpeed: 135,
      eraseSpeed: 70,
      hold: 3600,
      startDelay: document.querySelector(".dream-intro") ? 1050 : 260,
      loop: true,
    });
  }

  function watchDaypart() {
    const refresh = () => {
      const next = timeGreeting();
      if (next === lastDaypart) return;
      lastDaypart = next;
      if (heroVisible) startGreeting();
      else if (greetingNode) {
        greetingNode.textContent = next;
        syncGreetingLabel();
      }
    };
    window.setInterval(refresh, 30000);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) refresh();
    });
  }

  function startTerminal() {
    if (!terminalNode) return;
    terminalWriter?.stop();
    if (!dream.enabled) {
      terminalNode.textContent = prompts[0];
      activePrompt = prompts[0];
      return;
    }
    const initialIndex = Math.max(0, Math.floor(Math.random() * prompts.length));
    const ordered = prompts.slice(initialIndex).concat(prompts.slice(0, initialIndex));
    terminalWriter = dream.typewriter(terminalNode, {
      words: ordered,
      initial: "",
      typeSpeed: 48,
      eraseSpeed: 22,
      hold: 2800,
      startDelay: document.querySelector(".dream-intro") ? 1350 : 1900,
      loop: true,
      onWord(word) {
        activePrompt = word;
      },
    });
  }

  function refreshWriters() {
    if (!heroVisible) {
      greetingWriter?.stop();
      terminalWriter?.stop();
      return;
    }
    startGreeting();
    startTerminal();
  }

  function initTerminalFill() {
    if (!terminal || !input) return;
    terminal.addEventListener("click", () => {
      input.value = activePrompt;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus({ preventScroll: true });
      terminal.classList.remove("is-flashing");
      void terminal.offsetWidth;
      terminal.classList.add("is-flashing");
      window.setTimeout(() => terminal.classList.remove("is-flashing"), 700);
    });
  }

  function observeHero() {
    if (!hero) return;
    const update = () => {
      const next = !hero.hidden;
      if (next === heroVisible) return;
      heroVisible = next;
      refreshWriters();
    };
    new MutationObserver(update).observe(hero, {
      attributes: true,
      attributeFilter: ["hidden", "style", "class"],
    });
  }

  function decorateSessions() {
    const list = $("#sessionList");
    if (!list) return;
    const paint = () => {
      Array.from(list.querySelectorAll(".session")).forEach((item, index) => {
        item.style.setProperty("--session-order", String(Math.min(index, 12)));
      });
    };
    paint();
    new MutationObserver(paint).observe(list, { childList: true, subtree: true });
  }

  function addCardOrnaments() {
    document.querySelectorAll(".card").forEach((card) => {
      if (card.querySelector(".card__index")) return;
      const index = document.createElement("span");
      index.className = "card__index";
      index.setAttribute("aria-hidden", "true");
      index.textContent = String(Array.from(card.parentElement.children).indexOf(card) + 1).padStart(
        2,
        "0",
      );
      card.append(index);
    });
  }

  function init() {
    initTerminalFill();
    observeHero();
    decorateSessions();
    addCardOrnaments();
    watchDaypart();

    if (heroVisible) {
      startGreeting();
      startTerminal();
    }

    document.addEventListener("dreamai:motion", (event) => {
      if (event.detail.enabled) {
        if (heroVisible) {
          startGreeting();
          startTerminal();
        }
      } else {
        greetingWriter?.stop();
        terminalWriter?.stop();
        if (greetingNode) greetingNode.textContent = timeGreeting();
        syncGreetingLabel();
        if (terminalNode) terminalNode.textContent = activePrompt;
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
