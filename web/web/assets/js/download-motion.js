/* ==========================================================================
   Dream AI — download page stories
   ========================================================================== */
(() => {
  "use strict";

  const dream = window.DreamMotion;
  if (!dream) return;

  const titleNode = document.querySelector("#downloadTyped");
  const downloadButton = document.querySelector("#downloadBtn");
  const downloadLabel = downloadButton?.querySelector(".download-label");
  const titleWords = ["装进电脑。", "变成作品。", "带在身边。", "写进现实。"];
  let titleWriter = null;
  let resetTimer = null;

  function startTitle() {
    if (!titleNode) return;
    titleWriter?.stop();
    if (!dream.enabled) {
      titleNode.textContent = titleWords[0];
      return;
    }
    titleWriter = dream.typewriter(titleNode, {
      words: titleWords,
      initial: "",
      typeSpeed: 105,
      eraseSpeed: 42,
      hold: 3200,
      startDelay: document.querySelector(".dream-intro") ? 1150 : 500,
      loop: true,
    });
  }

  function initDownloadFeedback() {
    if (!downloadButton) return;
    downloadButton.addEventListener("click", () => {
      if (!downloadLabel) return;
      downloadButton.classList.add("is-downloading");
      downloadLabel.textContent = "正在准备下载…";
      window.clearTimeout(resetTimer);
      resetTimer = window.setTimeout(() => {
        downloadButton.classList.remove("is-downloading");
        downloadLabel.textContent = "再次下载 Windows 版";
      }, 5200);
    });
  }

  function init() {
    startTitle();
    initDownloadFeedback();

    document.addEventListener("dreamai:motion", (event) => {
      if (event.detail.enabled) {
        startTitle();
      } else {
        titleWriter?.stop();
        if (titleNode) titleNode.textContent = titleWords[0];
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
