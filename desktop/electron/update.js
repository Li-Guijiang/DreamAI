"use strict";

const crypto = require("crypto");
const fs = require("fs");
const https = require("https");
const path = require("path");
const { Transform, pipeline } = require("stream");
const { URL } = require("url");

const UPDATE_HOST = "liguijiang.com";
const MAX_BYTES = 512 * 1024 * 1024;
const MAX_REDIRECTS = 5;
const VERSION_RE = /^\d+\.\d+\.\d+$/;

function versionParts(value) {
  const clean = String(value || "").trim().replace(/^v/i, "");
  if (!VERSION_RE.test(clean)) return null;
  return clean.split(".").map(Number);
}

function compareVersions(left, right) {
  const a = versionParts(left);
  const b = versionParts(right);
  if (!a || !b) return 0;
  for (let index = 0; index < 3; index += 1) {
    if (a[index] !== b[index]) return a[index] > b[index] ? 1 : -1;
  }
  return 0;
}

function parseManifest(raw) {
  if (!raw || typeof raw !== "object") throw new Error("更新清单无效");
  const version = String(raw.version || "").trim();
  if (!VERSION_RE.test(version)) throw new Error("更新版本号无效");

  const expectedFile = `DreamAI-Setup-${version}.exe`;
  const file = path.basename(String(raw.file || expectedFile));
  if (file !== expectedFile) throw new Error("更新包名称无效");

  const sha256 = String(raw.sha256 || "").trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(sha256)) throw new Error("更新包校验值无效");

  const size = Number(raw.size);
  if (!Number.isSafeInteger(size) || size <= 0 || size > MAX_BYTES) {
    throw new Error("更新包大小无效");
  }

  const notes = String(raw.notes || "").trim().slice(0, 500);
  return { version, file, sha256, size, notes };
}

function updateUrl(manifest) {
  const url = new URL(`https://${UPDATE_HOST}/downloads/${encodeURIComponent(manifest.file)}`);
  if (url.protocol !== "https:" || url.hostname !== UPDATE_HOST) {
    throw new Error("更新地址无效");
  }
  return url;
}

function request(url, redirects = 0) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      {
        headers: {
          "User-Agent": "DreamAI-Desktop-Updater",
          Accept: "application/octet-stream",
        },
      },
      (res) => {
        const status = res.statusCode || 0;
        if (status >= 300 && status < 400 && res.headers.location) {
          res.resume();
          if (redirects >= MAX_REDIRECTS) {
            reject(new Error("更新地址重定向过多"));
            return;
          }
          let next;
          try {
            next = new URL(res.headers.location, url);
          } catch {
            reject(new Error("更新地址重定向无效"));
            return;
          }
          if (next.protocol !== "https:" || next.hostname !== UPDATE_HOST) {
            reject(new Error("更新地址重定向到了不受信任的域名"));
            return;
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

async function downloadInstaller(manifest, options) {
  const { destination, onProgress } = options;
  if (!destination) throw new Error("缺少更新包保存路径");
  await fs.promises.mkdir(path.dirname(destination), { recursive: true });
  const part = `${destination}.part`;
  const url = updateUrl(manifest);
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
      if (onProgress && (now - lastReport > 250 || received === manifest.size)) {
        lastReport = now;
        onProgress({
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
    const response = await request(url);
    await new Promise((resolve, reject) => {
      pipeline(response, meter, fs.createWriteStream(part), (error) => {
        if (error) reject(error);
        else resolve();
      });
    });
    if (received !== manifest.size) throw new Error("更新包大小校验失败");
    const digest = hash.digest("hex");
    if (digest !== manifest.sha256) throw new Error("更新包 SHA-256 校验失败");
    await fs.promises.rename(part, destination);
    return destination;
  } catch (error) {
    await fs.promises.rm(part, { force: true }).catch(() => {});
    throw error;
  }
}

module.exports = {
  compareVersions,
  downloadInstaller,
  parseManifest,
  updateUrl,
};
