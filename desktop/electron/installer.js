"use strict";

// Downloads an installer, verifies it against the manifest, and starts it.
// Everything here is async with streams: the main process must stay responsive
// while a 120 MB file moves through it.

const crypto = require("crypto");
const fs = require("fs");
const https = require("https");
const path = require("path");
const { Transform, pipeline } = require("stream");
const { URL } = require("url");

const DOWNLOAD_BASE = "https://liguijiang.com/downloads/";
const MAX_BYTES = 512 * 1024 * 1024;
const MAX_REDIRECTS = 5;

function installerUrl(manifest) {
  const url = new URL(manifest.file, DOWNLOAD_BASE);
  if (url.protocol !== "https:" || url.hostname !== "liguijiang.com") {
    throw new Error("更新地址无效");
  }
  return url;
}

function request(url, redirects = 0) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      { headers: { "User-Agent": "DreamAI-Desktop-Updater", Accept: "application/octet-stream" } },
      (res) => {
        const status = res.statusCode || 0;
        if (status >= 300 && status < 400 && res.headers.location) {
          res.resume();
          if (redirects >= MAX_REDIRECTS) return reject(new Error("更新地址重定向过多"));
          const next = new URL(res.headers.location, url);
          if (next.protocol !== "https:" || next.hostname !== "liguijiang.com") {
            return reject(new Error("更新地址重定向到了不受信任的域名"));
          }
          request(next, redirects + 1).then(resolve, reject);
          return;
        }
        if (status !== 200) {
          res.resume();
          reject(new Error(`下载更新失败（HTTP ${status}）`));
          return;
        }
        resolve(res);
      },
    );
    req.setTimeout(30_000, () => req.destroy(new Error("下载更新超时")));
    req.on("error", reject);
  });
}

/**
 * Download to `destination`, hashing as it writes. The partial file is removed
 * on any failure so a retry never resumes from a corrupt prefix.
 *
 * @param {{ version: string, file: string, size: number, sha256: string }} manifest
 * @param {{ destination: string, onProgress?: (payload: object) => void }} options
 */
async function downloadInstaller(manifest, options) {
  if (!options.destination) throw new Error("缺少更新包保存路径");
  if (!manifest.size || manifest.size > MAX_BYTES) throw new Error("更新包大小无效");
  if (!manifest.sha256) throw new Error("更新包尚未就绪");

  await fs.promises.mkdir(path.dirname(options.destination), { recursive: true });
  const part = `${options.destination}.part`;
  const hash = crypto.createHash("sha256");
  let received = 0;
  let lastReport = 0;

  const meter = new Transform({
    transform(chunk, _encoding, callback) {
      hash.update(chunk);
      received += chunk.length;
      if (received > MAX_BYTES) {
        callback(new Error("更新包超过大小限制"));
        return;
      }
      const now = Date.now();
      if (options.onProgress && (now - lastReport > 250 || received === manifest.size)) {
        lastReport = now;
        options.onProgress({
          phase: "download",
          received,
          total: manifest.size,
          percent: Math.min(100, Math.round((received / manifest.size) * 100)),
        });
      }
      callback(null, chunk);
    },
  });

  try {
    const response = await request(installerUrl(manifest));
    await new Promise((resolve, reject) => {
      pipeline(response, meter, fs.createWriteStream(part), (error) => (error ? reject(error) : resolve()));
    });
    if (received !== manifest.size) throw new Error("更新包大小校验失败");
    if (hash.digest("hex") !== manifest.sha256) throw new Error("更新包 SHA-256 校验失败");
    await fs.promises.rename(part, options.destination);
    return options.destination;
  } catch (error) {
    await fs.promises.rm(part, { force: true }).catch(() => {});
    throw error;
  }
}

module.exports = { DOWNLOAD_BASE, downloadInstaller, installerUrl };
