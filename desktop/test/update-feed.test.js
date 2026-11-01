"use strict";

const assert = require("assert");
const { validateManifest } = require("../electron/update-feed");

const base = {
  version: "1.4.0",
  file: "DreamAI-Setup-1.4.0.exe",
  sha256: "a".repeat(64),
  size: 1024,
  notes: "test",
};

assert.strictEqual(validateManifest(base).version, "1.4.0");
assert.strictEqual(validateManifest({ ...base, version: "v1.4.0" }).version, "1.4.0");

// The file name is derived from the version, so a manifest cannot point one
// release at another release's installer.
assert.throws(() => validateManifest({ ...base, file: "DreamAI-Setup-1.3.0.exe" }), /名称无效/);
assert.throws(() => validateManifest({ ...base, file: "../../evil.exe" }), /名称无效/);

assert.throws(() => validateManifest({ ...base, version: "1.4.0-beta.1" }), /预发布/);
assert.throws(() => validateManifest({ ...base, version: "1.4" }), /版本号无效/);
assert.throws(() => validateManifest({ ...base, sha256: "nope" }), /校验值无效/);
assert.throws(() => validateManifest({ ...base, size: 0 }), /大小无效/);
assert.throws(() => validateManifest({ ...base, size: 2 ** 40 }), /大小无效/);

// A pending manifest announces a version without an installer; it must be
// recognisable and must not pretend to be installable.
const pending = validateManifest({ version: "1.4.0", file: "DreamAI-Setup-1.4.0.exe", pending: true });
assert.strictEqual(pending.pending, true);
assert.strictEqual(pending.sha256, "");
assert.strictEqual(pending.size, 0);

console.log("feed tests passed");
