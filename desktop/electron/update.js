"use strict";

/**
 * Small, dependency-free helpers used by the desktop updater and its tests:
 * version ordering and parsing of the `latest.yml` manifest published next to
 * the installer.
 *
 * Ordering lives in ./semver.js so the schedule, the service and the renderer
 * fallback all agree; these wrappers keep the call sites readable.
 */

const semver = require("./semver");

function parseVersion(value) {
  const parsed = semver.parse(value);
  if (!parsed) return null;
  return {
    major: parsed.major,
    minor: parsed.minor,
    patch: parsed.patch,
    pre: parsed.prerelease || "",
  };
}

function compareVersions(a, b) {
  return semver.compare(a, b);
}

function isNewerVersion(latest, current) {
  return compareVersions(latest, current) > 0;
}

function parseLatestYml(text) {
  const source = String(text || "");
  const pick = (key) => {
    const match = new RegExp(`^${key}:\\s*(.+)$`, "m").exec(source);
    return match ? match[1].trim().replace(/^["']|["']$/g, "") : "";
  };
  return {
    version: pick("version"),
    path: pick("path"),
    sha512: pick("sha512"),
    releaseDate: pick("releaseDate"),
  };
}

module.exports = { compareVersions, isNewerVersion, parseLatestYml, parseVersion };
