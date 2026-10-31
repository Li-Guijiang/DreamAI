"use strict";

const assert = require("assert");
const { compareVersions, isNewerVersion, parseLatestYml, parseVersion } = require("../electron/update");

assert.deepStrictEqual(parseVersion("v1.2.3"), { major: 1, minor: 2, patch: 3, pre: "" });
assert.strictEqual(parseVersion("nope"), null);
assert.strictEqual(compareVersions("1.2.0", "1.1.9"), 1);
assert.strictEqual(compareVersions("1.2.0", "1.2.0"), 0);
assert.strictEqual(compareVersions("1.2.0-beta", "1.2.0"), -1);
assert.strictEqual(isNewerVersion("1.3.0", "1.2.0"), true);
assert.strictEqual(isNewerVersion("1.2.0", "1.2.0"), false);

const manifest = parseLatestYml(`
version: 1.3.0
files:
  - url: DreamAI-Setup-1.3.0.exe
    sha512: abc
path: DreamAI-Setup-1.3.0.exe
sha512: abcdef
releaseDate: '2026-10-31T00:00:00.000Z'
`);
assert.strictEqual(manifest.version, "1.3.0");
assert.strictEqual(manifest.path, "DreamAI-Setup-1.3.0.exe");
assert.strictEqual(manifest.sha512, "abcdef");

console.log("update helpers ok");
