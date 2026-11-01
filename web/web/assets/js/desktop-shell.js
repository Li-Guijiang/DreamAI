/* Shared window chrome for pages loaded inside the frameless Electron shell.
   The main app has its own titlebar; docs, download and changelog use this. */
(() => {
  const desktop = window.dreamDesktop;
  const bridge = desktop?.window;
  if (!desktop || !bridge) return;

  const body = document.body;
  body.classList.add("desktop-app");

  const remove = (node) => {
    if (!node) return;
    const previous = node.previousElementSibling;
    node.remove();
    if (previous?.classList.contains("dot-sep")) previous.remove();
  };

  document
    .querySelectorAll('.download-btn, a[href="/download.html"]')
    .forEach(remove);

  let bar = document.getElementById("desktopTitlebar");
  if (!bar) {
    body.insertAdjacentHTML(
      "afterbegin",
      `<div class="desktop-titlebar" id="desktopTitlebar">
        <div class="dtb__brand">
          <img src="/assets/img/mark.svg" alt="" width="18" height="18">
          <strong>Dream AI</strong>
          <em>Desktop</em>
        </div>
        <div class="dtb__drag" id="dtbDrag"></div>
        <div class="dtb__status"><i></i><span>Desktop</span></div>
        <div class="dtb__controls">
          <button type="button" id="winMin" aria-label="最小化" title="最小化"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 6h8"/></svg></button>
          <button type="button" id="winMax" aria-label="最大化" title="最大化"><svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2.2" y="2.2" width="7.6" height="7.6" rx="1"/></svg></button>
          <button type="button" id="winClose" aria-label="关闭" title="关闭"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6"/></svg></button>
        </div>
      </div>`,
    );
    bar = document.getElementById("desktopTitlebar");
  }

  if (!bar) return;
  bar.hidden = false;

  const toggleMax = () => bridge.toggleMaximize?.();
  const syncMaximized = (value) => body.classList.toggle("is-maximized", Boolean(value));

  document.getElementById("winMin")?.addEventListener("click", () => bridge.minimize?.());
  document.getElementById("winMax")?.addEventListener("click", () => {
    toggleMax();
    bridge.isMaximized?.().then(syncMaximized).catch(() => {});
  });
  document.getElementById("winClose")?.addEventListener("click", () => bridge.close?.());
  document.getElementById("dtbDrag")?.addEventListener("dblclick", toggleMax);
  bridge.onMaximized?.(syncMaximized);
  bridge.isMaximized?.().then(syncMaximized).catch(() => {});
})();
