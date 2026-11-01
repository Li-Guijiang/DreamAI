"use strict";

// Owns the update state machine and the timers. Everything is injected so the
// whole thing can be exercised with a fake clock and a fake feed.

const { EventEmitter } = require("events");
const schedule = require("./update-schedule");
const feed = require("./update-feed");
const semver = require("./semver");

const STATE = Object.freeze({
  IDLE: "idle",
  CHECKING: "checking",
  AVAILABLE: "available",
  UP_TO_DATE: "up-to-date",
  ERROR: "error",
});

/**
 * @param {{
 *   currentVersion: string,
 *   fetchManifest?: typeof feed.fetchManifest,
 *   isOnline?: () => boolean,
 *   timers?: { setTimeout: Function, clearTimeout: Function },
 *   now?: () => number,
 *   random?: () => number,
 *   firstDelayMs?: number,
 *   intervalMs?: number,
 * }} options
 */
function createUpdateService(options) {
  const fetchManifest = options.fetchManifest || feed.fetchManifest;
  const isOnline = options.isOnline || (() => true);
  const timers = options.timers || { setTimeout, clearTimeout };
  const now = options.now || (() => Date.now());
  const random = options.random || Math.random;
  const firstDelay = options.firstDelayMs ?? schedule.FIRST_DELAY;
  const interval = options.intervalMs ?? schedule.INTERVAL;

  const emitter = new EventEmitter();
  const state = {
    phase: STATE.IDLE,
    currentVersion: options.currentVersion,
    manifest: null,
    etag: null,
    lastCheckAt: null,
    lastError: null,
  };

  let timer = null;
  let attempt = 0;
  let inFlight = null;
  let stopped = true;

  function snapshot() {
    return { ...state, manifest: state.manifest ? { ...state.manifest } : null };
  }

  function publish(extra) {
    const payload = { ...snapshot(), ...extra };
    emitter.emit("state", payload);
    return payload;
  }

  function arm(delayMs) {
    if (stopped) return;
    if (timer) timers.clearTimeout(timer);
    timer = timers.setTimeout(() => {
      timer = null;
      checkNow({ manual: false }).catch(() => {});
    }, delayMs);
  }

  /**
   * Run one check. Resolves with the state snapshot; never rejects, because the
   * caller is usually a timer that has nothing useful to do with an exception.
   */
  async function checkNow({ manual = false } = {}) {
    if (inFlight) return inFlight;

    const plan = schedule.planCheck({
      online: isOnline(),
      now: now(),
      lastCheckAt: manual ? null : state.lastCheckAt,
      interval,
    });
    if (!plan.run && !manual) {
      arm(plan.waitMs);
      return publish({ reason: plan.reason });
    }

    state.phase = STATE.CHECKING;
    state.lastError = null;
    publish({ reason: manual ? "manual" : plan.reason });

    inFlight = (async () => {
      const result = await fetchManifest({ etag: state.etag });
      state.lastCheckAt = now();

      if (result.status === "error") {
        attempt += 1;
        state.phase = STATE.ERROR;
        state.lastError = result.error ? result.error.message : "更新检查失败";
        publish();
        arm(schedule.retryDelay(attempt, random));
        return snapshot();
      }

      attempt = 0;
      if (result.status === "ok") {
        state.manifest = result.manifest;
        state.etag = result.etag || null;
      }

      if (!state.manifest) {
        state.phase = STATE.ERROR;
        state.lastError = "更新清单缺失";
        arm(schedule.retryDelay(1, random));
        publish();
        return snapshot();
      }

      // Never offer a downgrade, even if the manifest is older than the app
      // (a rollback that was published by mistake, for example).
      const available = semver.isNewer(state.manifest.version, state.currentVersion);
      state.phase = available ? STATE.AVAILABLE : STATE.UP_TO_DATE;
      publish();
      arm(schedule.retryDelay(0, random));
      return snapshot();
    })();

    try {
      return await inFlight;
    } finally {
      inFlight = null;
    }
  }

  function start() {
    if (!stopped) return snapshot();
    stopped = false;
    arm(schedule.withJitter(firstDelay, random));
    return snapshot();
  }

  function stop() {
    stopped = true;
    if (timer) {
      timers.clearTimeout(timer);
      timer = null;
    }
    return snapshot();
  }

  /**
   * Called when the OS reports the network is back. A reconnect is an explicit
   * signal, so it forces the check instead of waiting for the interval to
   * elapse - otherwise "retry when online" would do nothing for six hours.
   */
  function handleOnline() {
    if (stopped) return snapshot();
    if (state.phase === STATE.ERROR) return checkNow({ manual: true });
    return snapshot();
  }

  return {
    checkNow,
    getState: snapshot,
    handleOnline,
    off: (event, listener) => emitter.off(event, listener),
    on: (event, listener) => emitter.on(event, listener),
    start,
    stop,
    STATE,
  };
}

module.exports = { STATE, createUpdateService };
