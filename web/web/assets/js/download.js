(async () => {
  const byId = (id) => document.getElementById(id);
  const formatSize = (bytes) => {
    if (!bytes) return "约 90 MB";
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
  };

  try {
    const response = await fetch("/downloads/latest.json", { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    if (data.version) byId("dlVersion").textContent = `v${data.version}`;
    if (data.file) byId("downloadBtn").href = `/downloads/${data.file}`;
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
})();
