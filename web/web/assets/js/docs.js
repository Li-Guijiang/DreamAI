/* ==========================================================================
   Dream AI — documentation interactions
   Scrollspy, copy buttons, a typed terminal command, and a small reading
   progress accent. All optional; the document is readable without JS.
   ========================================================================== */
(() => {
  "use strict";

  const dream = window.DreamMotion;
  const command = document.querySelector("#docsCommand");
  const commandText = "python -m dream_ai";
  let writer = null;

  function startCommand() {
    if (!command) return;
    writer?.stop();
    if (!dream || !dream.enabled) {
      command.textContent = commandText;
      return;
    }
    writer = dream.typewriter(command, {
      words: [commandText],
      initial: "",
      typeSpeed: 52,
      hold: 0,
      loop: false,
      erase: false,
      startDelay: document.querySelector(".dream-intro") ? 1350 : 500,
    });
  }

  function initScrollSpy() {
    const links = Array.from(document.querySelectorAll(".docs-toc__nav a, .docs-toc-mobile a"));
    const sections = Array.from(document.querySelectorAll(".doc-section[id]"));
    if (!links.length || !sections.length) return;

    const setActive = (id) => {
      links.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === `#${id}`);
      });
    };

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          const visible = entries
            .filter((entry) => entry.isIntersecting)
            .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
          if (visible[0]) setActive(visible[0].target.id);
        },
        { rootMargin: "-18% 0px -62% 0px", threshold: [0, 0.12, 0.4] },
      );
      sections.forEach((section) => observer.observe(section));
    }

    // A cheap fallback / correction for very short sections.
    let scheduled = false;
    window.addEventListener(
      "scroll",
      () => {
        if (scheduled) return;
        scheduled = true;
        window.requestAnimationFrame(() => {
          scheduled = false;
          const offset = window.innerHeight * 0.24;
          let current = sections[0]?.id;
          for (const section of sections) {
            if (section.getBoundingClientRect().top <= offset) current = section.id;
          }
          if (current) setActive(current);
        });
      },
      { passive: true },
    );

    const mobile = document.querySelector(".docs-toc-mobile");
    links.forEach((link) => {
      link.addEventListener("click", () => {
        if (mobile?.open) mobile.open = false;
      });
    });
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.append(textarea);
      textarea.select();
      let ok = false;
      try {
        ok = document.execCommand("copy");
      } catch {
        ok = false;
      }
      textarea.remove();
      return ok;
    }
  }

  function initCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach((button) => {
      button.addEventListener("click", async () => {
        const card = button.closest(".code-card, .tree-card");
        const code = card?.querySelector("pre");
        if (!code) return;
        const ok = await copyText(code.innerText || "");
        const previous = button.textContent;
        button.textContent = ok ? "已复制 ✓" : "复制失败";
        button.classList.toggle("is-copied", ok);
        window.setTimeout(() => {
          button.textContent = previous;
          button.classList.remove("is-copied");
        }, 1800);
      });
    });
  }

  function initYear() {
    const year = document.querySelector("#docsYear");
    if (year) year.textContent = String(new Date().getFullYear());
  }

  function init() {
    initScrollSpy();
    initCopyButtons();
    initYear();
    startCommand();

    document.addEventListener("dreamai:motion", (event) => {
      if (event.detail.enabled) startCommand();
      else {
        writer?.stop();
        if (command) command.textContent = commandText;
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
