"use strict";

const assert = require("assert");
const { compareVersions, parseManifest, updateUrl } = require("../electron/update");

assert.strictEqual(compareVersions("1.3.0", "1.2.9"), 1);
assert.strictEqual(compareVersions("v1.2.0", "1.2.0"), 0);
assert.strictEqual(compareVersions("1.2.0", "1.3.0"), -1);
assert.strictEqual(compareVersions("bad", "1.2.0"), 0);

const manifest = parseManifest({
  version: "1.3.0",
  file: "DreamAI-Setup-1.3.0.exe",
  sha256: "a".repeat(64),
  size: 1024,
  notes: "test",
});
assert.strictEqual(manifest.version, "1.3.0");
assert.strictEqual(updateUrl(manifest).href, "https://liguijiang.com/downloads/DreamAI-Setup-1.3.0.exe");

assert.throws(() => parseManifest({ ...manifest, file: "../evil.exe" }), /更新包名称无效/);
assert.throws(() => parseManifest({ ...manifest, file: "other.exe" }), /更新包名称无效/);
assert.throws(() => parseManifest({ ...manifest, sha256: "nope" }), /校验值无效/);
assert.throws(() => parseManifest({ ...manifest, size: 0 }), /大小无效/);

console.log("update tests passed");
