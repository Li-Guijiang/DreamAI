"""Guard the static site's asset references.

Assets under /assets/ are served with a long cache lifetime and pinned by a
``?v=`` query string on every page. Two pages pinning different versions of the
same file means one of them silently renders with an old stylesheet. A link to
a missing file is worse: it works on the developer's machine and 404s in a
fresh deployment. Both are caught here, before publishing.

Read-only. Exits non-zero when the site would ship an inconsistent asset set.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

#: Local asset URLs, with an optional cache-busting version. External URLs,
#: anchors and page links are deliberately not matched here.
ASSET_URL = re.compile(r'(?:src|href)="(/(?:assets|vendor)/[^"?#]+)(?:\?v=([^"#]+))?"')
DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "web"


@dataclass(frozen=True)
class AssetRef:
    """One local asset reference found in one page."""

    page: str
    path: str
    version: str | None


def scan_assets(root: Path) -> list[AssetRef]:
    """Every local asset reference in the site's top-level HTML pages."""
    references: list[AssetRef] = []
    for page in sorted(root.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        for path, version in ASSET_URL.findall(text):
            references.append(AssetRef(page.name, path, version or None))
    return references


def missing_assets(references: list[AssetRef], root: Path) -> list[str]:
    """References whose file does not exist on disk."""
    return sorted(
        {
            f"{reference.page}: {reference.path}"
            for reference in references
            if not (root / reference.path.lstrip("/")).is_file()
        }
    )


def unversioned_assets(references: list[AssetRef]) -> list[str]:
    """Local assets without a cache-busting version."""
    return sorted(
        {
            f"{reference.page}: {reference.path}"
            for reference in references
            if reference.version is None
        }
    )


def version_conflicts(references: list[AssetRef]) -> list[str]:
    """Paths that different pages pin at different versions."""
    by_path: dict[str, set[str]] = defaultdict(set)
    for reference in references:
        by_path[reference.path].add(reference.version or "(none)")
    return sorted(
        f"{path}: {', '.join(sorted(versions))}"
        for path, versions in by_path.items()
        if len(versions) > 1
    )


def check(root: Path, strict: bool = False) -> dict:
    """Machine-readable result for one site root.

    ``strict`` promotes unversioned local assets to a failure. It is opt-in
    because favicons and inline SVGs are commonly served without a version.
    """
    references = scan_assets(root)
    issues = {
        "missing": missing_assets(references, root),
        "unversioned": unversioned_assets(references),
        "conflicts": version_conflicts(references),
    }
    return {
        "pages": len(list(root.glob("*.html"))),
        "references": len(references),
        "issues": issues,
        # An unversioned asset is a warning by default; --strict promotes it.
        "ok": not issues["missing"]
        and not issues["conflicts"]
        and not (strict and issues["unversioned"]),
    }


def _format(result: dict) -> str:
    lines = [f"assets: {result['references']} references across {result['pages']} pages"]
    for key, label in (
        ("missing", "MISSING"),
        ("conflicts", "VERSION CONFLICT"),
        ("unversioned", "unversioned (warning)"),
    ):
        for item in result["issues"][key]:
            lines.append(f"  {label}: {item}")
    lines.append("assets: OK" if result["ok"] else "assets: FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--strict", action="store_true", help="also fail on unversioned assets")
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"assets: site root not found: {args.root}", file=sys.stderr)
        return 2

    result = check(args.root, strict=args.strict)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
