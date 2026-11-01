"use strict";

// dreamai:// links let the website ask the desktop app two questions that a
// browser cannot answer on its own: "is the app installed?" and "is a newer
// version available?". The app answers the first by sending the browser back to
// the download page with the version in the query string.

const ALLOWED_HOSTS = new Set(["liguijiang.com", "www.liguijiang.com"]);
const PROBE_PATH = "/download.html";

/**
 * Turn a dreamai:// URL into an intended action.
 *
 * @param {string} raw
 * @returns {{ action: "probe", returnUrl: string } | { action: "update" } | { action: "invalid", reason: string }}
 */
function parseDeepLink(raw) {
  let url;
  try {
    url = new URL(String(raw || ""));
  } catch {
    return { action: "invalid", reason: "unparsable" };
  }
  if (url.protocol !== "dreamai:") return { action: "invalid", reason: "scheme" };

  // dreamai://probe?return=… puts "probe" in the host; dreamai:probe?… puts it
  // in the path. Both forms are accepted so a link keeps working regardless of
  // how the browser normalises it.
  const name = (url.hostname || url.pathname.replace(/^\/+/, "")).toLowerCase();

  if (name === "probe") {
    const candidate = url.searchParams.get("return") || `https://liguijiang.com${PROBE_PATH}`;
    let target;
    try {
      target = new URL(candidate);
    } catch {
      return { action: "invalid", reason: "return" };
    }
    // The return address decides which page the user lands on, so it may only
    // point at our own site - otherwise a link could bounce them anywhere.
    if (target.protocol !== "https:" || !ALLOWED_HOSTS.has(target.hostname)) {
      return { action: "invalid", reason: "return-host" };
    }
    return { action: "probe", returnUrl: target.toString() };
  }

  if (name === "update") return { action: "update" };
  return { action: "invalid", reason: "unknown" };
}

/**
 * Build the URL the browser should be sent to after a probe.
 *
 * @param {string} returnUrl
 * @param {{ version: string, latest?: string | null }} info
 */
function probeRedirect(returnUrl, info) {
  const target = new URL(returnUrl);
  target.searchParams.set("dreamai", "1");
  target.searchParams.set("version", info.version);
  if (info.latest) target.searchParams.set("latest", info.latest);
  return target.toString();
}

/**
 * The first argument that looks like a deep link. Windows passes the URL as an
 * argv entry on a second launch; macOS uses the open-url event.
 *
 * @param {string[]} argv
 */
function findDeepLink(argv) {
  return (argv || []).find((arg) => typeof arg === "string" && arg.startsWith("dreamai://")) || null;
}

/** Everything the install registry would tell us, without reading the registry. */
function installedInfo(version) {
  return { installed: true, version: String(version || "") };
}

module.exports = {
  ALLOWED_HOSTS,
  PROBE_PATH,
  findDeepLink,
  installedInfo,
  parseDeepLink,
  probeRedirect,
};
