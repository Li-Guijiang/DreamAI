"use strict";

const assert = require("assert");
const protocol = require("../electron/protocol");

// 1. A probe with no return target lands on the download page.
assert.deepStrictEqual(protocol.parseDeepLink("dreamai://probe"), {
  action: "probe",
  returnUrl: "https://liguijiang.com/download.html",
});

// 2. A probe keeps the page the visitor came from.
assert.deepStrictEqual(
  protocol.parseDeepLink("dreamai://probe?return=https%3A%2F%2Fliguijiang.com%2Fdownload.html%3Futm%3Dmail"),
  { action: "probe", returnUrl: "https://liguijiang.com/download.html?utm=mail" },
);

// 3. Anywhere else is refused: a link must not bounce the user off-site.
assert.strictEqual(protocol.parseDeepLink("dreamai://probe?return=https://evil.example/x").action, "invalid");
assert.strictEqual(protocol.parseDeepLink("dreamai://probe?return=http://liguijiang.com/download.html").action, "invalid");

// 4. The path form some browsers produce works too.
assert.strictEqual(protocol.parseDeepLink("dreamai:probe").action, "probe");

// 5. Update and unknown links.
assert.deepStrictEqual(protocol.parseDeepLink("dreamai://update"), { action: "update" });
assert.strictEqual(protocol.parseDeepLink("dreamai://something").action, "invalid");
assert.strictEqual(protocol.parseDeepLink("not a url").action, "invalid");
assert.strictEqual(protocol.parseDeepLink("https://liguijiang.com").action, "invalid");

// 6. Windows passes the URL as an argv entry; findDeepLink picks it out.
assert.strictEqual(
  protocol.findDeepLink(["Dream AI.exe", "--url=http://x", "dreamai://probe"]),
  "dreamai://probe",
);
assert.strictEqual(protocol.findDeepLink(["Dream AI.exe"]), null);

// 7. The redirect keeps the original query and adds the answer.
const redirect = protocol.probeRedirect("https://liguijiang.com/download.html?utm=mail", {
  version: "1.4.0",
  latest: "1.5.0",
});
const parsed = new URL(redirect);
assert.strictEqual(parsed.searchParams.get("utm"), "mail");
assert.strictEqual(parsed.searchParams.get("dreamai"), "1");
assert.strictEqual(parsed.searchParams.get("version"), "1.4.0");
assert.strictEqual(parsed.searchParams.get("latest"), "1.5.0");

console.log("protocol tests passed");
