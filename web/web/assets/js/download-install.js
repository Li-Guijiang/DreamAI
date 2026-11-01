/* ==========================================================================
   Dream AI — download page: "do I already have this?"
   The page cannot read the Windows registry, so it asks the app: a custom
   protocol (dreamai://probe) opens the app, which immediately sends the browser
   back here with ?dreamai=1&version=<installed>. Everything below either reads
   that answer or offers the probe.
   ========================================================================== */
(() => {
  "use strict";

  const CACHE_KEY = "dreamai.install.probe";
  const CACHE_TTL = 10 * 60 * 1000;

  const byId = (id) => document.getElementById(id);
  const note = byId("installNote");
  const probe = byId("installProbe"); // optional; the click handler works without it
  const downloadBtn = byId("downloadBtn");
  const formatSize = (bytes) => {
    if (!bytes) return "约 90 MB";
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
  };

  const parts = (value) => {
    const clean = String(value || "").trim().replace(/^v/i, "");
    return /^\d+\.\d+\.\d+$/.test(clean) ? clean.split(".").map(Number) : null;
  };

  const isOlder = (installed, latest) => {
    const a = parts(installed);
    const b = parts(latest);
    if (!a || !b) return false;
    for (let index = 0; index < 3; index += 1) {
      if (a[index] !== b[index]) return a[index] < b[index];
    }
    return false;
  };

  let manifest = null;

  function readCache() {
    try {
      const raw = JSON.parse(localStorage.getItem(CACHE_KEY) || "null");
      if (!raw || Date.now() - raw.at > CACHE_TTL) return null;
      if (!raw.version) return null;
      return raw;
    } catch {
      return null;
    }
  }

  function writeCache(version, latest) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ version, latest, at: Date.now() }));
    } catch {
      /* private mode: the probe simply runs again next visit */
    }
  }

  function showNote({ title, body, open, redownload }) {
    if (!note) return;
    byId("installNoteTitle").textContent = title;
    byId("installNoteBody").textContent = body;
    const openLink = byId("installNoteOpen");
    const againLink = byId("installNoteRedownload");
    openLink.hidden = !open;
    againLink.hidden = !redownload;
    if (redownload && manifest?.file) {
      againLink.href = `/downloads/${encodeURIComponent(manifest.file)}`;
    }
    note.hidden = false;
  }

  function applyInstalled(installedVersion, latestVersion) {
    // The visitor already knows the app is here; a second click on the download
    // means "give me the file", so stop probing.
    if (downloadBtn) downloadBtn.dataset.skipProbe = "1";
    const latest = latestVersion || manifest?.version || installedVersion;
    if (isOlder(installedVersion, latest)) {
      showNote({
        title: `本机已安装 Dream AI v${installedVersion}`,
        body: `可以更新到 v${latest}。在应用内点「立即更新」会自动下载并校验安装包；也可以直接下载安装包覆盖安装。`,
        open: true,
        redownload: true,
      });
      if (downloadBtn) {
        downloadBtn.classList.remove("btn--primary");
        downloadBtn.classList.add("btn--ghost");
        downloadBtn.querySelector(".download-label").textContent = "下载安装包覆盖安装";
      }
      return;
    }

    showNote({
      title: "本机已安装，无需继续安装",
      body: `检测到 Dream AI v${installedVersion}，已是最新版本。直接打开应用即可，不必再次下载。`,
      open: true,
      redownload: true,
    });
    if (downloadBtn) {
      downloadBtn.classList.remove("btn--primary");
      downloadBtn.classList.add("btn--ghost");
      const label = downloadBtn.querySelector(".download-label");
      if (label) label.textContent = "重新下载安装包";
    }
  }

  /** Read the answer the app appended when it bounced the browser back. */
  function fromQuery() {
    const params = new URLSearchParams(location.search);
    if (params.get("dreamai") !== "1") return false;
    const version = String(params.get("version") || "").trim();
    if (!parts(version)) return false;
    const latest = String(params.get("latest") || "").trim();
    writeCache(version, parts(latest) ? latest : "");
    applyInstalled(version, parts(latest) ? latest : "");
    // Drop the parameters so a reload does not replay a stale answer.
    params.delete("dreamai");
    params.delete("version");
    params.delete("latest");
    const query = params.toString();
    history.replaceState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
    return true;
  }

  /**
   * Ask the app whether it is installed. A protocol launch needs a user gesture,
   * so this is called from the download click rather than on load: if the app
   * answers, this page is replaced by the redirect and the download never starts;
   * if nothing answers within 1.2 s, the download proceeds as usual.
   */
  function probeThenDownload(href) {
    let answered = false;
    const go = () => {
      if (answered) return;
      answered = true;
      window.location.href = href;
    };
    const timer = window.setTimeout(go, 1200);
    window.addEventListener(
      "pagehide",
      () => {
        answered = true;
        window.clearTimeout(timer);
      },
      { once: true },
    );
    window.location.href = `dreamai://probe?return=${encodeURIComponent(location.href)}`;
  }

  /** The manifest is rendered by download.js; this script only reads the version. */
  async function readManifest() {
    try {
      const response = await fetch("/downloads/latest.json", { cache: "no-store" });
      if (!response.ok) return;
      manifest = await response.json();
    } catch {
      /* the page keeps its static values */
    }
  }

  (async () => {
    await readManifest();

    if (fromQuery()) return;

    const cached = readCache();
    if (cached && (!manifest?.version || cached.latest === manifest.version)) {
      applyInstalled(cached.version, cached.latest || manifest?.version || "");
      return;
    }

    // No visible control is added: the probe rides on the download click, so the
    // page keeps the layout it had before install detection existed.
    if (downloadBtn && !downloadBtn.dataset.probeBound) {
      downloadBtn.dataset.probeBound = "1";
      downloadBtn.addEventListener("click", (event) => {
        const href = downloadBtn.getAttribute("href");
        if (!href || downloadBtn.dataset.skipProbe === "1") return;
        event.preventDefault();
        probeThenDownload(href);
      });
    }
    if (probe) probe.hidden = true;
  })();
})();
