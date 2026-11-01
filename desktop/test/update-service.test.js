"use strict";

const assert = require("assert");
const { createUpdateService, STATE } = require("../electron/update-service");
const schedule = require("../electron/update-schedule");

function fakeTimers() {
  const calls = [];
  return {
    calls,
    setTimeout(fn, ms) {
      calls.push(ms);
      return calls.length;
    },
    clearTimeout() {},
  };
}

const okManifest = (version) => ({
  status: "ok",
  manifest: { version, file: `DreamAI-Setup-${version}.exe`, sha256: "a".repeat(64), size: 1024 },
  etag: `"${version}"`,
  checkedAt: Date.now(),
});

async function run() {
  // 1. Newer manifest -> available, next check armed on the normal interval.
  {
    const timers = fakeTimers();
    const service = createUpdateService({
      currentVersion: "1.4.0",
      timers,
      random: () => 0.5,
      fetchManifest: async () => okManifest("1.5.0"),
    });
    service.start();
    const state = await service.checkNow({ manual: true });
    assert.strictEqual(state.phase, STATE.AVAILABLE);
    assert.strictEqual(state.manifest.version, "1.5.0");
    assert.strictEqual(timers.calls[0], schedule.FIRST_DELAY, "first check waits for the window");
    assert.strictEqual(timers.calls.at(-1), schedule.INTERVAL);
  }

  // 2. Manifest older than the app -> up to date, never an offered downgrade.
  {
    const service = createUpdateService({
      currentVersion: "1.6.0",
      timers: fakeTimers(),
      random: () => 0.5,
      fetchManifest: async () => okManifest("1.5.0"),
    });
    const state = await service.checkNow({ manual: true });
    assert.strictEqual(state.phase, STATE.UP_TO_DATE);
  }

  // 3. 304 keeps the previous manifest and still evaluates the version.
  {
    let call = 0;
    const service = createUpdateService({
      currentVersion: "1.4.0",
      timers: fakeTimers(),
      random: () => 0.5,
      fetchManifest: async () => {
        call += 1;
        return call === 1 ? okManifest("1.5.0") : { status: "not-modified", checkedAt: Date.now() };
      },
    });
    await service.checkNow({ manual: true });
    const state = await service.checkNow({ manual: true });
    assert.strictEqual(call, 2);
    assert.strictEqual(state.phase, STATE.AVAILABLE, "a 304 must not lose the manifest");
  }

  // 4. Failure -> error state and the first retry step, not the full interval.
  {
    const timers = fakeTimers();
    const service = createUpdateService({
      currentVersion: "1.4.0",
      timers,
      random: () => 0.5,
      fetchManifest: async () => ({ status: "error", error: new Error("boom"), checkedAt: Date.now() }),
    });
    service.start();
    const state = await service.checkNow({ manual: true });
    assert.strictEqual(state.phase, STATE.ERROR);
    assert.strictEqual(state.lastError, "boom");
    assert.strictEqual(timers.calls.at(-1), schedule.RETRY_STEPS[0]);
  }

  // 5. Two manual checks in flight share one request.
  {
    let calls = 0;
    const service = createUpdateService({
      currentVersion: "1.4.0",
      timers: fakeTimers(),
      random: () => 0.5,
      fetchManifest: async () => {
        calls += 1;
        await new Promise((resolve) => setImmediate(resolve));
        return okManifest("1.5.0");
      },
    });
    await Promise.all([service.checkNow({ manual: true }), service.checkNow({ manual: true })]);
    assert.strictEqual(calls, 1, "concurrent checks must not duplicate the request");
  }

  // 6. Offline skips the request entirely.
  {
    let calls = 0;
    const service = createUpdateService({
      currentVersion: "1.4.0",
      timers: fakeTimers(),
      isOnline: () => false,
      fetchManifest: async () => {
        calls += 1;
        return okManifest("1.5.0");
      },
    });
    const state = await service.checkNow();
    assert.strictEqual(calls, 0);
    assert.strictEqual(state.phase, STATE.IDLE);
  }

  // 7. Reconnecting after a failure retries immediately.
  {
    let calls = 0;
    const service = createUpdateService({
      currentVersion: "1.4.0",
      timers: fakeTimers(),
      random: () => 0.5,
      fetchManifest: async () => {
        calls += 1;
        return calls === 1
          ? { status: "error", error: new Error("offline"), checkedAt: Date.now() }
          : okManifest("1.5.0");
      },
    });
    service.start();
    await service.checkNow({ manual: true });
    await service.handleOnline();
    assert.strictEqual(calls, 2);
    assert.strictEqual(service.getState().phase, STATE.AVAILABLE);
  }

  console.log("service tests passed");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
