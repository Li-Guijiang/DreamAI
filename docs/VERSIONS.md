# 版本地图

项目同时发布四个带版本号的产物。它们**刻意不相等**：服务端修一个 bug
不需要重新打包安装器，桌面端发新版也不一定改动网页。文档的目标是说明
每个版本归属哪里，以及哪些关系必须成立。

`web/tools/check_versions.py` 是这份地图的可执行版本，在 CI 中运行。

## 1. 四个版本

| 产物 | 位置 | 当前值 | 谁变更它 |
|---|---|---|---|
| 服务端 / API | `web/app/config.py` → `VERSION` | 1.5.0 | 后端发布 |
| Service Worker 缓存 | `web/web/sw.js` → `CACHE` | 1.5.7 | 前端资源变更 |
| 桌面安装包 | `desktop/package.json`、`web/web/downloads/latest.json` | 1.3.0 | 桌面端发版 |
| CLI 包 | 根目录 `pyproject.toml` → `version` | 0.4.0 | Python 包发版 |

完整产品里程碑记录在 `web/web/changelog.html`，用 `vX.Y.Z` 标题展示。
它是面向用户的叙事，不与任一产物的构建号一一对应。

## 2. 必须成立的关系

1. **SW 缓存版本不得低于服务端版本**。浏览器仅在缓存名变化时安装新
   worker；若缓存名比服务端旧，访客会一直拿到上一次部署的页面。
2. **安装包清单版本必须等于桌面 package.json 版本**。二者不一致会让
   下载文件名、校验和与桌面应用自报版本互相矛盾。
3. **changelog 的最新条目不得低于服务端版本**。部署了新服务端却没有
   发布说明时，应补上条目而不是跳过检查。
4. 以上各值都必须是三段式语义版本（`X.Y.Z`），比较按数字而非字符串，
   因此 `1.10.0` 大于 `1.9.0`。

不要求相等的关系：服务端与安装包、CLI 与任一端、changelog 最新条目与
安装包构建号。

## 3. Service Worker 的预缓存版本

`sw.js` 的 `SHELL` 数组列出离线启动时预缓存的资源，其中 CSS/JS 带 `?v=`
版本。这些版本必须与页面实际引用的版本一致：

- 页面用 `app.css?v=2.1.0`，SW 却缓存 `app.css?v=2.0.8` 时，离线状态会
  加载旧样式，且在线时因为命中缓存也难以察觉。
- 修改任何预缓存资源的 `?v=` 后，必须同时提升 `CACHE` 名，否则已安装的
  worker 不会重新拉取列表。
- `web/tools/check_site.py` 的 `serviceWorkerPins` 检查会比对两者。

## 4. 发布顺序

1. 修改资源 → 更新对应页面的 `?v=`；
2. 同步更新 `sw.js` 中 `SHELL` 的版本，提升 `CACHE` 名；
3. 若涉及 API，更新 `VERSION` 与 changelog 条目；
4. 若发布桌面端，同时更新 `desktop/package.json` 与 `latest.json`
   （可用 `web/tools/make_downloads.py` 生成清单）；
5. 运行全部守卫工具与 `pytest`，确认版本地图与站点检查通过。

完整发布清单见 [RELEASE.md](./RELEASE.md)。
