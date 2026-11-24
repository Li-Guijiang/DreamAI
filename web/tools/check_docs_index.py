"""Keep the documentation indexes aligned with the files on disk.

Every ADR gets a row in ``docs/adr/README.md`` and every top-level document a
row in ``docs/README.md``. Forgetting the row does not break a build, so it
happens quietly and stays broken until somebody notices. This tool turns the
convention into a CI check.

Read-only. Exits non-zero when an index is missing an entry or points at a
file that does not exist.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DOCS = ROOT / "docs"
ADR = DOCS / "adr"
INDEX = DOCS / "README.md"
ADR_INDEX = ADR / "README.md"
LOCAL_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
ADR_FILE = re.compile(r"^\d{4}-.+\.md$")


def links_in(text: str) -> list[str]:
    """Local markdown targets referenced from one index page."""
    return [
        target
        for target in LOCAL_LINK.findall(text)
        if not target.startswith(("http://", "https://", "#", "mailto:"))
    ]


def check_adr_index(root: Path = ROOT) -> dict:
    adr = root / "docs" / "adr"
    index = adr / "README.md"
    if not index.is_file():
        return {"missing": [], "broken": [], "gaps": [], "duplicates": [], "files": 0, "ok": False}
    listed = {
        Path(target).name
        for target in links_in(index.read_text(encoding="utf-8"))
        if target.endswith(".md")
    }
    files = {p.name for p in adr.glob("*.md") if ADR_FILE.match(p.name)}
    numbers = sorted(int(name[:4]) for name in files)
    gaps = sorted(set(range(1, max(numbers) + 1)) - set(numbers)) if numbers else []
    duplicates = sorted(number for number in set(numbers) if numbers.count(number) > 1)
    return {
        "files": len(files),
        "missing": sorted(files - listed),
        "broken": sorted(target for target in listed if not (adr / target).is_file()),
        "gaps": gaps,
        "duplicates": duplicates,
        "ok": not (files - listed)
        and not any(not (adr / target).is_file() for target in listed)
        and not gaps
        and not duplicates,
    }


def check_docs_index(root: Path = ROOT) -> dict:
    docs = root / "docs"
    index = docs / "README.md"
    if not index.is_file():
        return {"missing": [], "broken": [], "files": 0, "ok": False}
    listed = {
        Path(target).name
        for target in links_in(index.read_text(encoding="utf-8"))
        if target.endswith(".md") and target.startswith("./")
    }
    files = {p.name for p in docs.glob("*.md") if p.name != "README.md"}
    # ADRs are linked through their own index rather than the document map.
    files.discard("adr")
    return {
        "files": len(files),
        "missing": sorted(files - listed),
        "broken": sorted(target for target in listed if not (docs / target).is_file()),
        "ok": not (files - listed) and not any(not (docs / target).is_file() for target in listed),
    }


def check(root: Path = ROOT) -> dict:
    adr = check_adr_index(root)
    docs = check_docs_index(root)
    return {
        "adr": adr,
        "docs": docs,
        "ok": adr["ok"] and docs["ok"],
    }


def _format(result: dict) -> str:
    lines = [f"docs index: {result['adr']['files']} ADRs, {result['docs']['files']} documents"]
    for group, key in (("adr", "ADR"), ("docs", "DOC")):
        for name in result[group]["missing"]:
            lines.append(f"  NOT INDEXED ({key}): {name}")
        for name in result[group]["broken"]:
            lines.append(f"  BROKEN LINK ({key}): {name}")
    for number in result["adr"]["gaps"]:
        lines.append(f"  ADR GAP: {number:04d}")
    for number in result["adr"]["duplicates"]:
        lines.append(f"  DUPLICATE ADR: {number:04d}")
    lines.append("docs index: OK" if result["ok"] else "docs index: FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
