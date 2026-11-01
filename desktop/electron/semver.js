"use strict";

// Semantic version handling for the desktop updater.
//
// The manifest publishes plain `major.minor.patch`, but comparing versions by
// string is how "1.10.0" ends up older than "1.9.0" and how a prerelease slips
// past a release. Everything goes through these functions instead.

const PATTERN = /^(\d{1,6})\.(\d{1,6})\.(\d{1,6})(?:-([0-9A-Za-z.-]{1,32}))?$/;

/**
 * Parse a version string into its numeric parts and an optional prerelease tag.
 * A leading `v` is accepted so tags and manifests can disagree about it.
 *
 * @param {unknown} value
 * @returns {{ major: number, minor: number, patch: number, prerelease: string | null, raw: string } | null}
 */
function parse(value) {
  const text = String(value ?? "").trim().replace(/^v/i, "");
  const match = PATTERN.exec(text);
  if (!match) return null;
  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3]),
    prerelease: match[4] || null,
    raw: text,
  };
}

function normalize(value) {
  const parsed = parse(value);
  return parsed ? parsed.raw : null;
}

function isPrerelease(value) {
  const parsed = parse(value);
  return Boolean(parsed && parsed.prerelease);
}

/**
 * Compare two prerelease strings the way SemVer 2.0.0 does: dot-separated
 * identifiers, numeric ones compared as numbers and ranked below alphanumeric
 * ones, and a version without a prerelease always wins.
 */
function comparePrerelease(left, right) {
  if (!left && !right) return 0;
  if (!left) return 1;
  if (!right) return -1;

  const a = left.split(".");
  const b = right.split(".");
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    const one = a[index];
    const two = b[index];
    if (one === undefined) return -1;
    if (two === undefined) return 1;
    const oneNumeric = /^\d+$/.test(one);
    const twoNumeric = /^\d+$/.test(two);
    if (oneNumeric && twoNumeric) {
      const diff = Number(one) - Number(two);
      if (diff !== 0) return diff > 0 ? 1 : -1;
      continue;
    }
    if (oneNumeric !== twoNumeric) return oneNumeric ? -1 : 1;
    if (one !== two) return one > two ? 1 : -1;
  }
  return 0;
}

/**
 * @returns {-1|0|1} 1 when `left` is newer than `right`.
 */
function compare(left, right) {
  const a = parse(left);
  const b = parse(right);
  if (!a || !b) return 0;
  for (const key of ["major", "minor", "patch"]) {
    if (a[key] !== b[key]) return a[key] > b[key] ? 1 : -1;
  }
  return comparePrerelease(a.prerelease, b.prerelease);
}

function isNewer(candidate, current) {
  return compare(candidate, current) > 0;
}

module.exports = { compare, isNewer, isPrerelease, normalize, parse };
