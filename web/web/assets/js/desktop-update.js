/* ==========================================================================
   Dream AI — desktop update gate
   Every installed desktop app loads this live site, including releases that
   predate the native updater. A version mismatch opens a blocking update dialog
   on entry. "暂不更新" only dismisses the current view; every fresh entry
   checks again until the app is actually updated. Clients from 1.3.0 onward
   can install silently; older clients
   download the signed-manifest installer in the browser and install it once.
   ========================================================================== */
(() => {
  "use strict";

  const desktop = window.dreamDesktop;
  if (!desktop?.isDesktop) return;

  const gate = document.querySelector("#updateGate");
  const versionNode = document.querySelector("#updateVersion");
  const currentNode = document.querySelector("#updateCurrent");
  const notesNode = document.querySelector("#updateNotes");
  const hintNode = document.querySelector("#updateHint");
  const installButton = document.querySelector("#updateInstall");
  const laterButton = document.querySelector("#updateLater");
  const progress = document.querySelector("#updateProgress");
  const progressBar = document.querySelector("#updateBar");
  const progressText = document.querySelector("#updatePercent");
  if (!gate || !versionNode || !installButton) return;

  let manifest = null;
  let currentVersion = "";
  let unlisten = null;
  let busy = false;
  let lastFocused = null;
  let focusTrap = null;

  const parts = (value) => {
    const clean = String(value || "").trim().replace(/^v/i, "");
    return /^\d+\.\d+\.\d+$/.test(clean) ? clean.split(".").map(Number) : null;
  };

  const newer = (left, right) => {
    const a = parts(left);
    const b = parts(right);
    if (!a || !b) return false;
    for (let index = 0; index < 3; index += 1) {
      if (a[index] !== b[index]) return a[index] > b[index];
    }
    return false;
  };

  function reveal() {
    lastFocused = document.activeElement;
    gate.hidden = false;
    document.body.classList.add("update-gate-open");
    focusTrap = (event) => {
      if (!gate.contains(event.target)) installButton.focus({ preventScroll: true });
    };
    document.addEventListener("focusin", focusTrap);
    requestAnimationFrame(() => {
      gate.classList.add("is-visible");
      window.setTimeout(() => installButton.focus({ preventScroll: true }), 120);
    });
  }

  function hide() {
    gate.classList.remove("is-visible");
    document.body.classList.remove("update-gate-open");
    if (focusTrap) document.removeEventListener("focusin", focusTrap);
    focusTrap = null;
    window.setTimeout(() => {
      gate.hidden = true;
      lastFocused?.focus?.({ preventScroll: true });
    }, 280);
  }

  function setProgress(value, label) {
    progress.hidden = false;
    const percent = Math.max(0, Math.min(100, Math.round(value || 0)));
    progressBar.style.width = `${percent}%`;
    progressText.textContent = label || `${percent}%`;
  }

  function fail(message) {
    busy = false;
    installButton.disabled = false;
    laterButton.disabled = false;
    installButton.textContent = "重试更新";
    progress.hidden = false;
    progressBar.style.width = "100%";
    progressBar.classList.add("is-error");
    progressText.textContent = message || "更新失败，请稍后重试";
    hintNode.textContent = "更新失败。你可以稍后再试，或前往官网下载最新安装包。";
  }

  async function install() {
    if (!manifest || busy) return;
    busy = true;
    installButton.disabled = true;

    if (!desktop.update?.install) {
      // Older clients have no native installer bridge. Hand the verified
      // installer URL to the browser; the user runs it once. The next launch
      // of an outdated build will show this gate again.
      try {
        const url = new URL(
          `/downloads/${encodeURIComponent(manifest.file)}`,
          location.origin,
        ).href;
        laterButton.disabled = true;
        if (desktop.code?.openUrl) await desktop.code.openUrl(url);
        else window.open(url, "_blank", "noopener");
        installButton.textContent = "下载已开始";
        hintNode.textContent =
          "浏览器已开始下载安装包。运行安装包完成更新；下次进入若仍未更新，会再次提醒。";
        window.setTimeout(hide, 2000);
      } catch (error) {
        fail(error?.message || "无法打开下载页面");
      }
      return;
    }

    installButton.textContent = "正在更新…";
    laterButton.disabled = true;
    progress.hidden = false;
    progressBar.style.width = "0%";
    progressText.textContent = "连接更新通道…";
    hintNode.textContent = "下载完成前请保持应用打开。";
    unlisten?.();
    unlisten = desktop.update.onProgress((payload) => {
      if (!payload) return;
      if (payload.phase === "installing") {
        setProgress(100, "正在安装，应用即将重启");
        installButton.textContent = "正在重启…";
        hintNode.textContent = "安装器已启动，Dream AI 将自动重启。";
      } else {
        setProgress(payload.percent, `下载中 ${payload.percent || 0}%`);
        hintNode.textContent = `下载更新包 ${payload.percent || 0}% · 请保持应用打开`;
      }
    });

    try {
      await desktop.update.install({
        version: manifest.version,
        file: manifest.file,
        sha256: manifest.sha256,
        size: manifest.size,
      });
      hintNode.textContent = "安装器已启动，应用即将重启。";
    } catch (error) {
      fail(error?.message || "更新失败，请稍后重试");
    }
  }

  async function check() {
    try {
      currentVersion = await desktop.version?.();
      if (!currentVersion) return;
      const response = await fetch("/downloads/latest.json", { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      if (!newer(data.version, currentVersion)) return;

      const version = String(data.version || "");
      const file = String(data.file || "");
      const sha256 = String(data.sha256 || "");
      const size = Number(data.size) || 0;
      if (!parts(version)) return;
      if (file !== `DreamAI-Setup-${version}.exe`) return;
      if (!/^[a-f0-9]{64}$/i.test(sha256) || size <= 0) return;

      manifest = {
        version,
        file,
        sha256,
        size,
        notes: String(data.notes || "").trim(),
      };
      versionNode.textContent = `v${version}`;
      currentNode.textContent = `v${currentVersion}`;
      notesNode.textContent =
        manifest.notes || "更流畅的体验与若干细节修复，建议更新到最新版本。";

      const fallback = !desktop.update?.install;
      installButton.textContent = fallback ? "下载更新包" : "立即更新";
      hintNode.textContent = fallback
        ? "当前旧版需要手动运行一次安装包；安装最新版后，后续版本即可一键更新。暂不更新的话，下次进入仍会提醒。"
        : "更新包会校验 SHA-256 后静默安装，应用会自动重启。暂不更新的话，下次进入仍会提醒。";
      reveal();
    } catch {
      /* the update check must never block the chat */
    }
  }

  laterButton?.addEventListener("click", () => {
    // Deliberately no persistence: every fresh entry into an outdated client
    // must show this gate again until the app is actually updated.
    hide();
  });
  installButton.addEventListener("click", install);

  document.addEventListener("keydown", (event) => {
    if (gate.hidden || event.key !== "Escape") return;
    laterButton?.click();
  });

  window.setTimeout(check, 650);
})();
