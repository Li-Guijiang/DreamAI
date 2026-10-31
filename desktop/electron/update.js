"use strict";

/**
 * Small, dependency-free helpers used by the desktop updater and its tests.
 * electron-updater does the downloading; these functions only reason about
 * version strings and the `latest.yml` manifest we publish next to the
 * installer.
 */

function parseVersion(value) {
  const match = /^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?/.exec(String(value || "").trim());
  if (!match) return null;
  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3]),
    pre: match[4] || "",
  };
}

function compareVersions(a, b) {
  const left = parseVersion(a);
  const right = parseVersion(b);
  if (!left || !right) return 0;
  for (const key of ["major", "minor", "patch"]) {
    if (left[key] !== right[key]) return left[key] > right[key] ? 1 : -1;
  }
  if (left.pre === right.pre) return 0;
  if (!left.pre) return 1;
  if (!right.pre) return -1;
  return left.pre > right.pre ? 1 : -1;
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
