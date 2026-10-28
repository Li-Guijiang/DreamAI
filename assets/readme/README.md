# README image mirror

GitHub repository-relative images are served through
`raw.githubusercontent.com` (or a redirect to it). On several networks that host
times out or returns `502`, which leaves the README and docs banners blank even
though the files are valid. The live site is unaffected.

To keep the repository readable everywhere, the documentation images are
uploaded as **GitHub user attachments** and referenced by absolute URL in
Markdown. GitHub renders them through its own signed image host.

`attachments.json` is the source of truth:

- every documentation image URL must appear there;
- every entry records the original local source file and the transformation;
- `tests/test_web_assets.py` validates the manifest and every image reference.

## Replacing an image

1. Update the source image in the repository.
2. Produce the documented optimized variant (screenshots are 1400 px or
   1200 px wide JPEG, quality 82–84; the hero is a transparent 1000×340 PNG;
   banners stay animated GIF).
3. Upload it as a GitHub user attachment for `Li-Guijiang/DreamAI` with the
   repository's public visibility.
4. Add the new URL to `attachments.json`.
5. Replace the URL in the Markdown files (or keep the same Markdown URL and
   update the manifest if the URL itself did not change).
6. Run `pytest tests/test_web_assets.py`.

The full-resolution originals stay in `web/docs/` and `assets/brand/`; only
optimized copies are uploaded.

> These are ordinary images, not code. Upload only material intended for a
> public repository.
