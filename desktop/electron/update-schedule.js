"use strict";

// When to look for a new version. Pure functions only, so the policy can be
// tested without a clock, a network, or an Electron instance.

const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;

const FIRST_DELAY = 15 * 1000;      // let the window paint first
const INTERVAL = 6 * HOUR;          // steady-state cadence
const JITTER_RATIO = 0.1;           // +/-10 %
const RETRY_STEPS = [5 * MINUTE, 15 * MINUTE, 60 * MINUTE];
const MAX_MANIFEST_AGE = 24 * HOUR; // usable for display, never for installing

/**
 * Spread a delay by +/-10 %. Without it, every client that started at the same
 * time would hit the manifest in the same second after a release.
 *
 * @param {number} delayMs
 * @param {() => number} [random] injectable for tests
 */
function withJitter(delayMs, random = Math.random) {
  const factor = 1 + (random() * 2 - 1) * JITTER_RATIO;
  return Math.max(1000, Math.round(delayMs * factor));
}

/**
 * Delay before the next attempt.
 *
 * @param {number} attempt 0 after a successful check, 1..n for consecutive failures
 */
function retryDelay(attempt, random = Math.random) {
  if (attempt <= 0) return withJitter(INTERVAL, random);
  const step = RETRY_STEPS[Math.min(attempt, RETRY_STEPS.length) - 1];
  return withJitter(step, random);
}

/**
 * Decide whether a check should run at all, and for how long to postpone it.
 *
 * @param {{ online: boolean, now: number, lastCheckAt: number | null, interval?: number }} state
 * @returns {{ run: boolean, waitMs: number, reason: string }}
 */
function planCheck(state) {
  const interval = state.interval ?? INTERVAL;
  if (!state.online) return { run: false, waitMs: 0, reason: "offline" };
  if (state.lastCheckAt == null) return { run: true, waitMs: 0, reason: "first" };
  const elapsed = state.now - state.lastCheckAt;
  if (elapsed >= interval) return { run: true, waitMs: 0, reason: "due" };
  return { run: false, waitMs: interval - elapsed, reason: "not-due" };
}

/**
 * A cached manifest may be shown to the user ("last checked …") but must never
 * be used to install: the hash could describe a file that no longer exists.
 */
function isManifestFresh(fetchedAt, now = Date.now()) {
  if (!Number.isFinite(fetchedAt)) return false;
  return now - fetchedAt <= MAX_MANIFEST_AGE;
}

module.exports = {
  FIRST_DELAY,
  INTERVAL,
  MAX_MANIFEST_AGE,
  RETRY_STEPS,
  isManifestFresh,
  planCheck,
  retryDelay,
  withJitter,
};
