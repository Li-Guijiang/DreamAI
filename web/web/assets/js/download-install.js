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
  const probe = byId("installProbe");
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

  /** The probe needs a user gesture: browsers block protocol launches otherwise. */
  function startProbe() {
    if (!probe) return;
    const target = `dreamai://probe?return=${encodeURIComponent(location.href)}`;
    let answered = false;
    const timer = window.setTimeout(() => {
      if (answered) return;
      probe.disabled = false;
      probe.textContent = "未检测到本机安装";
      showNote({
        title: "没有检测到本机安装",
        body: "可能是尚未安装，或浏览器拦截了打开应用的请求。可以直接下载安装包；安装后本页会自动识别。",
        open: false,
        redownload: false,
      });
    }, 2500);

    window.addEventListener(
      "pagehide",
      () => {
        answered = true;
        window.clearTimeout(timer);
      },
      { once: true },
    );

    probe.disabled = true;
    probe.textContent = "正在检测…";
    location.href = target;
  }

  async function loadManifest() {
    try {
      const response = await fetch("/downloads/latest.json", { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      manifest = data;
      if (data.version) byId("dlVersion").textContent = `v${data.version}`;

      if (data.pending) {
        // The manifest exists before the installer does. Say so instead of
        // handing out a link that 404s.
        downloadBtn.removeAttribute("href");
        downloadBtn.setAttribute("aria-disabled", "true");
        const label = downloadBtn.querySelector(".download-label");
        if (label) label.textContent = "安装包构建中";
        showNote({
          title: `v${data.version} 正在构建`,
          body: "这一版已发布，安装包还在上传。稍后刷新本页即可下载；已安装的用户可在应用内检查更新。",
          open: false,
          redownload: false,
        });
        return;
      }

      if (data.file) downloadBtn.href = `/downloads/${data.file}`;
      if (data.size) byId("dlSize").textContent = formatSize(data.size);
      if (data.date) byId("dlDate").textContent = data.date;
      if (data.sha256) byId("dlSha").textContent = data.sha256;

      const release = byId("releaseNote");
      if (release && data.version && data.notes) {
        byId("releaseTitle").textContent = `v${data.version} 更新公告`;
        byId("releaseNotes").textContent = data.notes;
        release.hidden = false;
      }
    } catch {
      /* keep static fallbacks */
    }
  }

  (async () => {
    await loadManifest();

    if (fromQuery()) return;

    const cached = readCache();
    if (cached && (!manifest?.version || cached.latest === manifest.version)) {
      applyInstalled(cached.version, cached.latest || manifest?.version || "");
      return;
    }

    if (probe) {
      probe.hidden = false;
      probe.addEventListener("click", startProbe);
    }
  })();
})();
