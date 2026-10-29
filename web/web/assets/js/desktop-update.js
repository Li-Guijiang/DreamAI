/* ==========================================================================
   Dream AI — desktop update channel
   The site is the update feed because every installed desktop app loads it,
   including versions released before this file existed. New clients get the
   one-click silent update; old clients get a browser fallback to the installer.
   ========================================================================== */
(() => {
  "use strict";

  const desktop = window.dreamDesktop;
  if (!desktop?.isDesktop) return;

  const toast = document.querySelector("#updateToast");
  const versionNode = document.querySelector("#updateVersion");
  const currentNode = document.querySelector("#updateCurrent");
  const notesNode = document.querySelector("#updateNotes");
  const installButton = document.querySelector("#updateInstall");
  const laterButton = document.querySelector("#updateLater");
  const progress = document.querySelector("#updateProgress");
  const progressBar = document.querySelector("#updateBar");
  const progressText = document.querySelector("#updatePercent");
  if (!toast || !versionNode || !installButton) return;

  let manifest = null;
  let currentVersion = "";
  let unlisten = null;
  let busy = false;

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

  const dismissKey = (version) => `dreamai.update.dismissed.${version}`;

  function reveal() {
    toast.hidden = false;
    requestAnimationFrame(() => toast.classList.add("is-visible"));
  }

  function hide() {
    toast.classList.remove("is-visible");
    window.setTimeout(() => {
      toast.hidden = true;
    }, 260);
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
    installButton.textContent = "重试更新";
    progress.hidden = false;
    progressBar.style.width = "100%";
    progressBar.classList.add("is-error");
    progressText.textContent = message || "更新失败，请稍后重试";
  }

  async function install() {
    if (!manifest || busy) return;
    busy = true;
    installButton.disabled = true;

    if (!desktop.update?.install) {
      // 1.2.x and older: no local installer bridge exists. Open the official
      // download page in the user's browser; the next release can update in place.
      const url = `${location.origin}/download.html?update=${encodeURIComponent(manifest.version)}`;
      if (desktop.code?.openUrl) await desktop.code.openUrl(url);
      else window.open(url, "_blank", "noopener");
      installButton.textContent = "已在浏览器打开";
      busy = false;
      return;
    }

    installButton.textContent = "正在更新…";
    progress.hidden = false;
    progressBar.style.width = "0%";
    progressText.textContent = "连接更新通道…";
    unlisten?.();
    unlisten = desktop.update.onProgress((payload) => {
      if (!payload) return;
      if (payload.phase === "installing") {
        setProgress(100, "正在安装，应用即将重启");
      } else {
        setProgress(payload.percent, `下载中 ${payload.percent || 0}%`);
      }
    });

    try {
      await desktop.update.install({
        version: manifest.version,
        file: manifest.file,
        sha256: manifest.sha256,
        size: manifest.size,
      });
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
      manifest = {
        version: String(data.version || ""),
        file: String(data.file || ""),
        sha256: String(data.sha256 || ""),
        size: Number(data.size) || 0,
        notes: String(data.notes || "").trim(),
      };
      if (!parts(manifest.version) || !manifest.file) return;
      if (sessionStorage.getItem(dismissKey(manifest.version))) return;

      versionNode.textContent = `v${manifest.version}`;
      currentNode.textContent = `v${currentVersion}`;
      const fallback = !desktop.update?.install;
      notesNode.textContent = `${manifest.notes || "更流畅的体验与若干细节修复，建议更新到最新版本。"}${
        fallback ? " 当前旧版需下载安装一次，之后的版本即可一键更新。" : ""
      }`;
      installButton.textContent = fallback ? "下载新版" : "立即更新";
      reveal();
    } catch {
      /* update checks must never disturb the chat */
    }
  }

  laterButton?.addEventListener("click", () => {
    if (manifest) sessionStorage.setItem(dismissKey(manifest.version), "1");
    hide();
  });
  installButton.addEventListener("click", install);

  window.setTimeout(check, 1600);
})();
