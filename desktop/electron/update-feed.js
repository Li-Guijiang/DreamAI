"use strict";

// Fetches the release manifest and validates it. Kept separate from the
// installer download so a check costs one small HTTPS request and no disk writes.

const https = require("https");
const { URL } = require("url");
const semver = require("./semver");

const MANIFEST_URL = "https://liguijiang.com/downloads/latest.json";
const TIMEOUT_MS = 10_000;
const MAX_BYTES = 64 * 1024;
const MAX_REDIRECTS = 3;
const MAX_INSTALLER_BYTES = 512 * 1024 * 1024;

/**
 * Validate a manifest before anything trusts it.
 *
 * A `pending` manifest is a published version whose installer is still
 * uploading: it carries no size or hash, so it may be announced but never
 * installed from.
 *
 * @param {unknown} raw
 * @returns {{ version: string, file: string, size: number, sha256: string, notes: string, pending: boolean }}
 */
function validateManifest(raw) {
  if (!raw || typeof raw !== "object") throw new Error("更新清单无效");
  const version = semver.normalize(raw.version);
  if (!version) throw new Error("更新版本号无效");
  if (semver.isPrerelease(version)) throw new Error("更新版本号不能包含预发布标识");

  const expected = `DreamAI-Setup-${version}.exe`;
  const file = String(raw.file || expected).split("/").pop();
  if (file !== expected) throw new Error("更新包名称无效");

  if (raw.pending === true) {
    return { version, file, size: 0, sha256: "", notes: String(raw.notes || "").slice(0, 500), pending: true };
  }

  const sha256 = String(raw.sha256 || "").trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(sha256)) throw new Error("更新包校验值无效");

  const size = Number(raw.size);
  if (!Number.isSafeInteger(size) || size <= 0 || size > MAX_INSTALLER_BYTES) {
    throw new Error("更新包大小无效");
  }

  return { version, file, size, sha256, notes: String(raw.notes || "").slice(0, 500), pending: false };
}

/**
 * @param {{ etag?: string | null, url?: string, timeoutMs?: number }} [options]
 * @returns {Promise<{ status: "ok" | "not-modified" | "error", manifest?: object, etag?: string | null, checkedAt: number, error?: Error }>}
 */
function fetchManifest(options = {}) {
  const url = new URL(options.url || MANIFEST_URL);
  const timeoutMs = options.timeoutMs || TIMEOUT_MS;
  const checkedAt = Date.now();

  return new Promise((resolve) => {
    const fail = (error) => resolve({ status: "error", checkedAt, error });

    const request = https.get(
      url,
      {
        headers: {
          "User-Agent": "DreamAI-Desktop-Updater",
          Accept: "application/json",
          ...(options.etag ? { "If-None-Match": options.etag } : {}),
        },
      },
      (response) => {
        const status = response.statusCode || 0;

        if (status === 304) {
          response.resume();
          resolve({ status: "not-modified", checkedAt, etag: options.etag || null });
          return;
        }
        if (status >= 300 && status < 400 && response.headers.location) {
          response.resume();
          const redirects = (options._redirects || 0) + 1;
          if (redirects > MAX_REDIRECTS) return fail(new Error("更新清单重定向过多"));
          let next;
          try {
            next = new URL(response.headers.location, url);
          } catch {
            return fail(new Error("更新清单重定向无效"));
          }
          // Stay on the same origin: a manifest from elsewhere could point the
          // updater at a different installer host.
          if (next.protocol !== "https:" || next.hostname !== url.hostname) {
            return fail(new Error("更新清单重定向到了不受信任的域名"));
          }
          fetchManifest({ ...options, url: next.toString(), _redirects: redirects }).then(resolve, fail);
          return;
        }
        if (status !== 200) {
          response.resume();
          return fail(new Error(`更新清单不可用（HTTP ${status}）`));
        }

        const chunks = [];
        let received = 0;
        response.on("data", (chunk) => {
          received += chunk.length;
          if (received > MAX_BYTES) {
            response.destroy(new Error("更新清单超过大小限制"));
            return;
          }
          chunks.push(chunk);
        });
        response.on("end", () => {
          try {
            const manifest = validateManifest(JSON.parse(Buffer.concat(chunks).toString("utf8")));
            resolve({ status: "ok", manifest, etag: response.headers.etag || null, checkedAt });
          } catch (error) {
            fail(error);
          }
        });
        response.on("error", fail);
      },
    );

    request.setTimeout(timeoutMs, () => request.destroy(new Error("更新清单请求超时")));
    request.on("error", fail);
  });
}

module.exports = { MANIFEST_URL, MAX_BYTES, fetchManifest, validateManifest };
