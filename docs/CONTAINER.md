# Container image

<sub>[Back to the documentation index](./README.md)</sub>

Dream AI is published as a multi-architecture container image on the GitHub Container Registry. This page covers the image path, the tag scheme, what triggers a build, and how to check that the image you pulled matches the code you expect.

## 1. Image

```
ghcr.io/li-guijiang/dream-ai
```

The path is defined once, in the `IMAGE` variable at the top of
[`.github/workflows/publish-container.yml`](../.github/workflows/publish-container.yml), and the same string appears in the pull commands below. If the owner or the repository is ever renamed, change it in the workflow first.

## 2. Tags

| Tag | Moves when | Use it for |
|---|---|---|
| `latest` | every push to `main`, every `v*` tag, manual dispatch | "just give me the current main" |
| `edge` | every push to `main` | the same build as `latest`, named explicitly |
| `sha-<short>` | every push to `main` | pinning an exact commit |
| `1.4.0`, `1.4` | push of tag `v1.4.0` | a release you can reproduce later |

Images are built for `linux/amd64` and `linux/arm64`; Docker picks the right one automatically.

## 3. Triggers

| Event | Result |
|---|---|
| push to `main` | `latest`, `edge`, `sha-<short>` |
| push of a `v*` tag | semver tags, plus `latest` |
| manual dispatch | `latest` and an optional extra tag |

Before 2026-10-30 the workflow listened to `v*` tags only, so between two releases the published package kept describing older code than the repository. Every merge after `v0.4.0` had no effect on `latest`, which is exactly what "the package is not updating" looks like from the outside.

## 4. Pull and run

```bash
docker pull ghcr.io/li-guijiang/dream-ai:latest
docker run -it --rm ghcr.io/li-guijiang/dream-ai:latest
```

With a model backend:

```bash
docker run -it --rm \
  -e DREAMAI_API_KEY=your-key \
  -e DREAMAI_BASE_URL=https://api.deepseek.com/v1 \
  -e DREAMAI_MODEL=deepseek-chat \
  ghcr.io/li-guijiang/dream-ai:latest
```

Without `DREAMAI_API_KEY` the container starts in offline demo mode, which is expected and not an error.

## 5. Checking that the image is current

1. Open **Actions → Publish Container** and look at the newest run: it should be newer than the commit you care about.
2. Read the labels baked into the image:

   ```bash
   docker inspect ghcr.io/li-guijiang/dream-ai:latest \
     --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}'
   ```

   The value is the commit the image was built from. Compare it with `git log -1 --format=%H` in your checkout.
3. If the labels are missing, the image predates this workflow — rebuild by pushing to `main` or by running the workflow manually.

## 6. The legacy package in the sidebar

The repository's **Packages** section may list a second, older package whose name is the product's Chinese title rather than `dream-ai`. That package is not produced by the current workflow: it was published before the image path was standardised, and its name cannot be changed from git.

To remove it:

1. open the package page from the profile (**Your packages**), not from the repository sidebar;
2. **Package settings → Manage access / Delete package** — deleting requires typing the package name; versions can be deleted individually under **Versions**;
3. confirm the repository sidebar afterwards lists only `dream-ai`.

Nothing in the build depends on that package, so deleting it is safe. Keeping it would leave two entries that look like the same product with different ages.

## 7. Why a rebuild is not instant

A multi-arch build runs two platform builds plus a manifest merge, and the registry then has to propagate the new digest. Expect three to six minutes before `docker pull ...:latest` returns the new layers; `docker pull` caches aggressively, so add `--pull` if the old image is already local.
