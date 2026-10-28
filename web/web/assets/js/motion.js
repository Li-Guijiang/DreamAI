/* ==========================================================================
   Dream AI — motion engine (shared)
   A tiny, dependency-free animation layer for every page.

   - starfield / shooting stars / pointer parallax
   - optional intro, cursor aura, click sparks and page transitions
   - scroll reveals, counters, tilt and magnetic interactions
   - a global motion switch, persisted in localStorage
   - all effects honour `prefers-reduced-motion`

   Public API: window.DreamMotion
   ========================================================================== */
(() => {
  "use strict";

  const root = document.documentElement;
  const STORE_KEY = "dreamai.motion";
  const INTRO_KEY = "dreamai.intro.seen";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const changeListeners = new Set();
  const finePointer = window.matchMedia("(pointer: fine)").matches;

  let enabled = true;
  try {
    const stored = window.localStorage.getItem(STORE_KEY);
    enabled = stored ? stored === "on" : !reduceMotion.matches;
  } catch {
    enabled = !reduceMotion.matches;
  }

  const sleep = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

  function commitMotion() {
    root.setAttribute("data-motion", enabled ? "on" : "off");
    root.classList.add("motion-ready");
    document.querySelectorAll("[data-motion-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(enabled));
      button.classList.toggle("is-off", !enabled);
      const label = enabled ? "暂停全站动效" : "开启全站动效";
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
      const text = button.querySelector("[data-motion-label]");
      if (text) {
        text.textContent = button.hasAttribute("data-motion-custom")
          ? enabled
            ? "暂停全站动效"
            : "开启全站动效"
          : enabled
            ? "动态"
            : "静态";
      }
    });
  }

  function setMotion(next, { persist = true } = {}) {
    enabled = Boolean(next);
    if (persist) {
      try {
        window.localStorage.setItem(STORE_KEY, enabled ? "on" : "off");
      } catch {
        /* storage can be disabled in private mode */
      }
    }
    commitMotion();
    changeListeners.forEach((listener) => {
      try {
        listener(enabled);
      } catch {
        /* a broken listener must not stop the page */
      }
    });
    document.dispatchEvent(new CustomEvent("dreamai:motion", { detail: { enabled } }));
    starfield?.setEnabled(enabled);
    if (!enabled) removeIntro();
  }

  /* ---------------------------------------------------------------------
     Starfield: one canvas, two star depths, a handful of shooting stars.
     --------------------------------------------------------------------- */

  class Starfield {
    constructor(host) {
      this.host = host;
      this.canvas = document.createElement("canvas");
      this.canvas.className = "cosmos-canvas";
      this.canvas.setAttribute("aria-hidden", "true");
      this.ctx = this.canvas.getContext("2d", { alpha: true });
      this.stars = [];
      this.meteors = [];
      this.pointer = { x: 0, y: 0, tx: 0, ty: 0 };
      this.running = false;
      this.enabled = false;
      this.last = 0;
      this.nextMeteor = 1800;
      this.width = 0;
      this.height = 0;
      this.dpr = 1;
      this.host.append(this.canvas);

      this.onResize = this.resize.bind(this);
      window.addEventListener("resize", this.onResize, { passive: true });
      window.addEventListener("pointermove", (event) => {
        if (!finePointer) return;
        this.pointer.tx = (event.clientX / Math.max(1, window.innerWidth) - 0.5) * 2;
        this.pointer.ty = (event.clientY / Math.max(1, window.innerHeight) - 0.5) * 2;
      }, { passive: true });
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
          this.stop();
        } else if (this.enabled) {
          this.start();
        }
      });

      this.resize();
      this.setEnabled(enabled);
    }

    palette() {
      const styles = getComputedStyle(root);
      const dark = root.dataset.theme !== "light";
      return {
        dark,
        core: dark ? "244, 246, 255" : "39, 49, 78",
        accent: dark ? "124, 156, 255" : "74, 110, 245",
        teal: dark ? "94, 234, 212" : "15, 158, 138",
        violet: dark ? "183, 156, 255" : "124, 92, 240",
        bg: styles.getPropertyValue("--bg").trim() || (dark ? "#08090d" : "#f7f6f2"),
      };
    }

    resize() {
      const rect = this.host.getBoundingClientRect();
      this.width = Math.max(320, window.innerWidth || rect.width);
      this.height = Math.max(320, window.innerHeight || rect.height);
      this.dpr = Math.min(2, window.devicePixelRatio || 1);
      this.canvas.width = Math.floor(this.width * this.dpr);
      this.canvas.height = Math.floor(this.height * this.dpr);
      this.canvas.style.width = `${this.width}px`;
      this.canvas.style.height = `${this.height}px`;
      this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      this.build();
      if (!this.running) this.draw(performance.now(), true);
    }

    build() {
      const lowPower = (navigator.hardwareConcurrency || 8) <= 4;
      const target = Math.min(lowPower ? 90 : 190, Math.round((this.width * this.height) / 9000));
      const palette = this.palette();
      this.stars = Array.from({ length: target }, (_, index) => {
        const depth = index % 4 === 0 ? 1.6 : index % 3 === 0 ? 1.1 : 0.6;
        return {
          x: Math.random() * this.width,
          y: Math.random() * this.height,
          r: (Math.random() * 1.1 + 0.25) * depth,
          depth,
          alpha: Math.random() * 0.55 + 0.2,
          phase: Math.random() * Math.PI * 2,
          speed: Math.random() * 0.00045 + 0.00012,
          tint: Math.random() > 0.82 ? (index % 2 ? palette.accent : palette.teal) : palette.core,
        };
      });
      this.meteors = [];
      this.nextMeteor = 1200 + Math.random() * 2600;
    }

    setEnabled(value) {
      this.enabled = value;
      if (value) this.start();
      else {
        this.stop();
        this.draw(performance.now(), true);
      }
    }

    start() {
      if (this.running || !this.enabled) return;
      this.running = true;
      this.last = performance.now();
      this.frame = requestAnimationFrame((time) => this.tick(time));
    }

    stop() {
      this.running = false;
      if (this.frame) cancelAnimationFrame(this.frame);
      this.frame = null;
    }

    tick(time) {
      if (!this.running) return;
      const delta = Math.min(48, time - this.last);
      this.last = time;
      this.draw(time, false, delta);
      this.frame = requestAnimationFrame((next) => this.tick(next));
    }

    draw(time, still = false, delta = 16) {
      const ctx = this.ctx;
      const palette = this.palette();
      ctx.clearRect(0, 0, this.width, this.height);

      this.pointer.x += (this.pointer.tx - this.pointer.x) * 0.035;
      this.pointer.y += (this.pointer.ty - this.pointer.y) * 0.035;

      for (const star of this.stars) {
        if (!still) {
          star.y += star.depth * 0.006 * (delta / 16);
          star.x += Math.sin(time * star.speed + star.phase) * 0.035 * star.depth;
          if (star.y > this.height + 4) star.y = -4;
          if (star.x > this.width + 4) star.x = -4;
          if (star.x < -4) star.x = this.width + 4;
        }
        const twinkle = 0.55 + Math.sin(time * star.speed * 4 + star.phase) * 0.35;
        const x = star.x - this.pointer.x * star.depth * 12;
        const y = star.y - this.pointer.y * star.depth * 8;
        ctx.beginPath();
        ctx.fillStyle = `rgba(${star.tint}, ${(star.alpha * twinkle).toFixed(3)})`;
        ctx.arc(x, y, star.r, 0, Math.PI * 2);
        ctx.fill();
        if (star.depth > 1.4 && twinkle > 0.78) {
          ctx.strokeStyle = `rgba(${star.tint}, ${(star.alpha * 0.24).toFixed(3)})`;
          ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(x - 3.5, y);
          ctx.lineTo(x + 3.5, y);
          ctx.moveTo(x, y - 3.5);
          ctx.lineTo(x, y + 3.5);
          ctx.stroke();
        }
      }

      if (!still) {
        this.nextMeteor -= delta;
        if (this.nextMeteor <= 0) {
          this.spawnMeteor(palette);
          this.nextMeteor = 2800 + Math.random() * 5200;
        }
      }

      for (let i = this.meteors.length - 1; i >= 0; i -= 1) {
        const meteor = this.meteors[i];
        meteor.x += meteor.vx * (delta / 16);
        meteor.y += meteor.vy * (delta / 16);
        meteor.life -= delta / 900;
        if (meteor.life <= 0 || meteor.x < -180 || meteor.y > this.height + 180) {
          this.meteors.splice(i, 1);
          continue;
        }
        const gradient = ctx.createLinearGradient(
          meteor.x,
          meteor.y,
          meteor.x - meteor.vx * 11,
          meteor.y - meteor.vy * 11,
        );
        gradient.addColorStop(0, `rgba(${palette.core}, ${(meteor.life * 0.8).toFixed(3)})`);
        gradient.addColorStop(0.24, `rgba(${palette.accent}, ${(meteor.life * 0.45).toFixed(3)})`);
        gradient.addColorStop(1, "rgba(124, 156, 255, 0)");
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 1.3;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(meteor.x, meteor.y);
        ctx.lineTo(meteor.x - meteor.vx * 9, meteor.y - meteor.vy * 9);
        ctx.stroke();
        ctx.beginPath();
        ctx.fillStyle = `rgba(${palette.core}, ${(meteor.life * 0.75).toFixed(3)})`;
        ctx.arc(meteor.x, meteor.y, 1.2, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    spawnMeteor(palette) {
      const fromLeft = Math.random() > 0.45;
      const startX = fromLeft ? Math.random() * this.width * 0.55 : this.width * 0.55 + Math.random() * this.width * 0.45;
      this.meteors.push({
        x: startX,
        y: Math.random() * this.height * 0.42,
        vx: (fromLeft ? 5.2 : -4.5) + Math.random() * 2,
        vy: 2.4 + Math.random() * 1.8,
        life: 1,
      });
      if (this.meteors.length > 3) this.meteors.shift();
      this.canvas.classList.add("is-meteor");
      window.setTimeout(() => this.canvas.classList.remove("is-meteor"), 800);
    }
  }

  let starfield = null;

  /* ---------------------------------------------------------------------
     Intro
     --------------------------------------------------------------------- */

  let intro = null;

  function showIntro() {
    if (!enabled || intro) return;
    let seen = false;
    try {
      seen = window.sessionStorage.getItem(INTRO_KEY) === "1";
    } catch {
      seen = false;
    }
    if (seen) return;
    try {
      window.sessionStorage.setItem(INTRO_KEY, "1");
    } catch {
      /* ignore */
    }

    intro = document.createElement("div");
    intro.className = "dream-intro";
    intro.setAttribute("aria-hidden", "true");
    intro.innerHTML = `
      <div class="dream-intro__stage">
        <span class="dream-intro__ring dream-intro__ring--a"></span>
        <span class="dream-intro__ring dream-intro__ring--b"></span>
        <span class="dream-intro__orbit"><i></i></span>
        <img src="/assets/img/mark.svg" alt="" width="72" height="72">
      </div>
      <p class="dream-intro__word"><span>DREAM</span><span>AI</span></p>
      <p class="dream-intro__status"><i></i>ENTERING THE DREAM UNIVERSE</p>
      <span class="dream-intro__bar"><i></i></span>`;
    document.body.append(intro);
    requestAnimationFrame(() => intro?.classList.add("is-active"));
    window.setTimeout(() => {
      intro?.classList.add("is-leaving");
      window.setTimeout(removeIntro, 760);
    }, 980);
  }

  function removeIntro() {
    if (!intro) return;
    intro.classList.add("is-leaving");
    const node = intro;
    intro = null;
    window.setTimeout(() => node.remove(), 300);
  }

  /* ---------------------------------------------------------------------
     Pointer aura, sparks, transitions
     --------------------------------------------------------------------- */

  function initCursorAura() {
    if (!finePointer) return;
    const aura = document.createElement("div");
    aura.className = "cursor-aura";
    aura.setAttribute("aria-hidden", "true");
    document.body.append(aura);
    let x = window.innerWidth / 2;
    let y = window.innerHeight / 2;
    let px = x;
    let py = y;
    let visible = false;

    window.addEventListener("pointermove", (event) => {
      x = event.clientX;
      y = event.clientY;
      if (!visible) {
        aura.classList.add("is-visible");
        visible = true;
      }
    }, { passive: true });
    window.addEventListener("pointerleave", () => {
      aura.classList.remove("is-visible");
      visible = false;
    });
    const render = () => {
      px += (x - px) * 0.13;
      py += (y - py) * 0.13;
      aura.style.transform = `translate3d(${px}px, ${py}px, 0) translate(-50%, -50%)`;
      requestAnimationFrame(render);
    };
    render();
  }

  const sparkColors = ["#7c9cff", "#5eead4", "#b79cff", "#f3c77b"];

  function burst(x, y, count = 8) {
    if (!enabled) return;
    const wrap = document.createElement("span");
    wrap.className = "click-sparks";
    wrap.setAttribute("aria-hidden", "true");
    wrap.style.left = `${x}px`;
    wrap.style.top = `${y}px`;
    for (let index = 0; index < count; index += 1) {
      const dot = document.createElement("i");
      const angle = (Math.PI * 2 * index) / count + Math.random() * 0.5;
      const distance = 18 + Math.random() * 28;
      dot.style.setProperty("--dx", `${Math.cos(angle) * distance}px`);
      dot.style.setProperty("--dy", `${Math.sin(angle) * distance}px`);
      dot.style.setProperty("--size", `${2 + Math.random() * 3}px`);
      dot.style.setProperty("--spark", sparkColors[index % sparkColors.length]);
      wrap.append(dot);
    }
    document.body.append(wrap);
    window.setTimeout(() => wrap.remove(), 760);
  }

  function initSparks() {
    document.addEventListener("pointerdown", (event) => {
      if (!enabled || event.button !== 0) return;
      const interactive = event.target.closest(
        "button, a, .card, .format, .app__chip, summary, .docs-toc a",
      );
      if (!interactive) return;
      burst(event.clientX, event.clientY, interactive.classList.contains("btn--primary") ? 12 : 7);
    }, { passive: true });
  }

  function pageVeil() {
    let veil = document.querySelector(".page-veil");
    if (veil) return veil;
    veil = document.createElement("div");
    veil.className = "page-veil";
    veil.setAttribute("aria-hidden", "true");
    veil.innerHTML = '<img src="/assets/img/mark.svg" alt="" width="48" height="48"><span></span>';
    document.body.append(veil);
    return veil;
  }

  function initPageTransitions() {
    document.addEventListener("click", (event) => {
      if (!enabled || event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = event.target.closest("a[href]");
      if (!link) return;
      if (link.target && link.target !== "_self") return;
      if (link.hasAttribute("download")) return;
      const href = link.getAttribute("href");
      if (!href || href.startsWith("#") || /^(mailto:|tel:|javascript:)/i.test(href)) return;
      let url;
      try {
        url = new URL(href, window.location.href);
      } catch {
        return;
      }
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.hash) return;
      if (/\.[a-z0-9]+$/i.test(url.pathname) && !/\.html?$/i.test(url.pathname)) return;
      if (url.pathname === window.location.pathname && !url.hash) {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      const veil = pageVeil();
      veil.classList.add("is-active");
      window.setTimeout(() => {
        window.location.href = url.href;
      }, 360);
    });
    window.addEventListener("pageshow", () => {
      document.querySelector(".page-veil")?.classList.remove("is-active");
    });
  }

  /* ---------------------------------------------------------------------
     Scroll reveal, counters, tilt, magnet
     --------------------------------------------------------------------- */

  function initReveal() {
    const items = Array.from(document.querySelectorAll("[data-reveal]"));
    if (!items.length) return;
    items.forEach((item, index) => {
      item.classList.add("reveal");
      const delay = Number(item.dataset.revealDelay || 0);
      if (delay) item.style.transitionDelay = `${delay}ms`;
      if (item.dataset.reveal === "left") item.classList.add("reveal--left");
      if (item.dataset.reveal === "right") item.classList.add("reveal--right");
      if (item.dataset.reveal === "scale") item.classList.add("reveal--scale");
      item.style.setProperty("--reveal-order", String(index % 8));
    });
    if (!("IntersectionObserver" in window)) {
      items.forEach((item) => item.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    items.forEach((item) => observer.observe(item));
  }

  function initCounters() {
    const counters = Array.from(document.querySelectorAll("[data-count]"));
    if (!counters.length) return;
    const animate = (node) => {
      const target = Number(node.dataset.count || 0);
      const suffix = node.dataset.suffix || "";
      const duration = Math.max(450, Number(node.dataset.duration || 1100));
      const start = performance.now();
      const frame = (now) => {
        const progress = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - progress, 3);
        node.textContent = `${Math.round(target * eased)}${suffix}`;
        if (progress < 1) requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    };
    if (!("IntersectionObserver" in window)) {
      counters.forEach(animate);
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        animate(entry.target);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.4 });
    counters.forEach((counter) => observer.observe(counter));
  }

  function initTilt() {
    if (!finePointer) return;
    document.querySelectorAll("[data-tilt]").forEach((node) => {
      const strength = Number(node.dataset.tilt || 5);
      let frame = null;
      const reset = () => {
        node.classList.remove("is-tilting");
        node.style.setProperty("--tilt-x", "0deg");
        node.style.setProperty("--tilt-y", "0deg");
      };
      node.addEventListener("pointerenter", () => node.classList.add("is-tilting"));
      node.addEventListener("pointermove", (event) => {
        if (!enabled) return;
        if (frame) cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
          const rect = node.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width - 0.5;
          const y = (event.clientY - rect.top) / rect.height - 0.5;
          node.style.setProperty("--tilt-x", `${(-y * strength).toFixed(2)}deg`);
          node.style.setProperty("--tilt-y", `${(x * strength).toFixed(2)}deg`);
          node.style.setProperty("--spot-x", `${((x + 0.5) * 100).toFixed(1)}%`);
          node.style.setProperty("--spot-y", `${((y + 0.5) * 100).toFixed(1)}%`);
        });
      }, { passive: true });
      node.addEventListener("pointerleave", reset);
      node.addEventListener("blur", reset);
    });
  }

  function initMagnet() {
    if (!finePointer) return;
    const nodes = document.querySelectorAll(".btn--primary, .new-chat, .send, .download-btn");
    nodes.forEach((node) => {
      node.classList.add("is-magnetic");
      node.addEventListener("pointermove", (event) => {
        if (!enabled) return;
        const rect = node.getBoundingClientRect();
        const x = event.clientX - rect.left - rect.width / 2;
        const y = event.clientY - rect.top - rect.height / 2;
        node.style.setProperty("--mag-x", `${(x * 0.12).toFixed(1)}px`);
        node.style.setProperty("--mag-y", `${(y * 0.16).toFixed(1)}px`);
      }, { passive: true });
      node.addEventListener("pointerleave", () => {
        node.style.setProperty("--mag-x", "0px");
        node.style.setProperty("--mag-y", "0px");
      });
    });
  }

  function initToggles() {
    document.querySelectorAll("[data-motion-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        setMotion(!enabled);
        if (enabled) burst(button.getBoundingClientRect().left + 18, button.getBoundingClientRect().top + 18, 10);
      });
    });
    reduceMotion.addEventListener?.("change", (event) => {
      let stored = null;
      try {
        stored = window.localStorage.getItem(STORE_KEY);
      } catch {
        stored = null;
      }
      if (!stored) setMotion(!event.matches, { persist: false });
    });
  }

  function initProgress() {
    const bar = document.createElement("div");
    bar.className = "cosmic-progress";
    bar.setAttribute("aria-hidden", "true");
    bar.innerHTML = "<i></i>";
    document.body.append(bar);
    const fill = bar.firstElementChild;
    const scroller = document.querySelector("#scroll, .scroll");
    const source = scroller && getComputedStyle(scroller).overflowY !== "visible" ? scroller : window;
    const update = () => {
      const max =
        source === window
          ? document.documentElement.scrollHeight - window.innerHeight
          : source.scrollHeight - source.clientHeight;
      const top = source === window ? window.scrollY : source.scrollTop;
      const ratio = max > 0 ? Math.min(1, Math.max(0, top / max)) : 0;
      fill.style.transform = `scaleX(${ratio.toFixed(4)})`;
      bar.classList.toggle("is-visible", ratio > 0.015);
    };
    source.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update, { passive: true });
    update();
  }

  /* ---------------------------------------------------------------------
     Typewriter API
     --------------------------------------------------------------------- */

  function typewriter(element, options = {}) {
    const {
      words = [],
      typeSpeed = 62,
      eraseSpeed = 28,
      hold = 1800,
      startDelay = 300,
      loop = true,
      initial = "",
      onWord = null,
      erase = true,
    } = options;
    if (!element || !words.length) return { stop() {}, restart() {} };
    element.textContent = initial;
    let index = 0;
    let stopped = false;
    let timer = null;

    const wait = (ms) =>
      new Promise((resolve) => {
        timer = window.setTimeout(resolve, ms);
      });

    async function typeWord(word) {
      for (let position = initial && index === 0 ? initial.length : 0; position <= word.length; position += 1) {
        if (stopped) return false;
        while (!enabled) {
          if (stopped) return false;
          await wait(180);
        }
        element.textContent = word.slice(0, position);
        await wait(typeSpeed + Math.random() * 36);
      }
      return !stopped;
    }

    async function eraseWord(word) {
      for (let position = word.length; position >= 0; position -= 1) {
        if (stopped) return false;
        element.textContent = word.slice(0, position);
        await wait(eraseSpeed);
      }
      return !stopped;
    }

    async function run() {
      if (startDelay) await wait(startDelay);
      while (!stopped) {
        const word = words[index % words.length];
        const typed = await typeWord(word);
        if (!typed) return;
        onWord?.(word, index);
        if (!loop) return;
        await wait(hold);
        if (!erase) return;
        const erased = await eraseWord(word);
        if (!erased) return;
        await wait(240);
        index += 1;
      }
    }

    run();

    return {
      stop() {
        stopped = true;
        if (timer) window.clearTimeout(timer);
      },
      restart() {
        stopped = true;
        if (timer) window.clearTimeout(timer);
        stopped = false;
        index = 0;
        initial = "";
        run();
      },
      get word() {
        return words[index % words.length];
      },
    };
  }

  /* ---------------------------------------------------------------------
     Boot
     --------------------------------------------------------------------- */

  function init() {
    commitMotion();
    routeMotion();

    const host = document.querySelector(".ambient, .bg, .cosmos-host");
    if (host) {
      starfield = new Starfield(host);
    }

    initToggles();
    initSparks();
    initPageTransitions();
    initReveal();
    initCounters();
    initTilt();
    initMagnet();
    initProgress();
    if (finePointer && enabled) initCursorAura();
    if (enabled) showIntro();

    // Let pages start their own writing routines after the shared engine is ready.
    document.dispatchEvent(new CustomEvent("dreamai:ready", { detail: { motion: enabled } }));
  }

  function routeMotion() {
    if (enabled) return;
    // `animation-play-state` is a cheap, safe way to stop every decorative loop
    // while keeping focus/hover transitions responsive.
    document.querySelectorAll("[data-motion-decor]").forEach((node) => {
      node.classList.add("is-paused");
    });
  }

  window.DreamMotion = {
    get enabled() {
      return enabled;
    },
    set: setMotion,
    toggle: () => setMotion(!enabled),
    burst,
    typewriter,
    onChange(listener) {
      changeListeners.add(listener);
      return () => changeListeners.delete(listener);
    },
    sleep,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
