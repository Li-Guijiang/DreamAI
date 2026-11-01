"use strict";

const assert = require("assert");
const schedule = require("../electron/update-schedule");

// A constant random value removes the jitter, so the assertions are exact.
const middle = () => 0.5;

assert.strictEqual(schedule.withJitter(10_000, middle), 10_000);
assert.strictEqual(schedule.withJitter(10_000, () => 1), 11_000);
assert.strictEqual(schedule.withJitter(10_000, () => 0), 9_000);
assert.ok(schedule.withJitter(100, () => 0) >= 1000, "delay never collapses to zero");

assert.strictEqual(schedule.retryDelay(0, middle), schedule.INTERVAL);
assert.strictEqual(schedule.retryDelay(1, middle), 5 * 60_000);
assert.strictEqual(schedule.retryDelay(2, middle), 15 * 60_000);
assert.strictEqual(schedule.retryDelay(3, middle), 60 * 60_000);
assert.strictEqual(schedule.retryDelay(9, middle), 60 * 60_000, "retries cap at one hour");

assert.deepStrictEqual(schedule.planCheck({ online: true, now: 0, lastCheckAt: null }), {
  run: true,
  waitMs: 0,
  reason: "first",
});
assert.deepStrictEqual(schedule.planCheck({ online: false, now: 0, lastCheckAt: null }), {
  run: false,
  waitMs: 0,
  reason: "offline",
});
assert.deepStrictEqual(schedule.planCheck({ online: true, now: 1_000, lastCheckAt: 0, interval: 60_000 }), {
  run: false,
  waitMs: 59_000,
  reason: "not-due",
});
assert.strictEqual(schedule.planCheck({ online: true, now: 60_000, lastCheckAt: 0, interval: 60_000 }).run, true);

assert.strictEqual(schedule.isManifestFresh(Date.now()), true);
assert.strictEqual(schedule.isManifestFresh(Date.now() - schedule.MAX_MANIFEST_AGE - 1), false);
assert.strictEqual(schedule.isManifestFresh(undefined), false, "an unknown timestamp is never fresh");

console.log("schedule tests passed");
