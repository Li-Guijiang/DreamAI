"""Check that JavaScript selectors can find their nodes in the HTML.

A script that queries a missing id fails quietly: the guard clause returns and
the feature simply never runs. Static text often remains, so the page still
looks correct. This tool extracts literal id selectors from the site's own
scripts and verifies that some page declares each id.

Two exemptions are deliberate:

* ids created at runtime by a script are discovered from ``id="..."`` strings
  in JavaScript source;
* scripts that only run in the desktop shell may reference nodes injected by
  the native webview, which are declared in an allowlist with a reason.

Read-only. Exits non-zero when a selector cannot be resolved anywhere.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SITE = ROOT / "web" / "web"
SCRIPTS = SITE / "assets" / "js"

HTML_ID = re.compile(r'\bid="([^"]+)"')
JS_ID_LITERAL = re.compile(r'\bid="([^"]+)"')
GET_BY_ID = re.compile(r'getElementById\(["\']([^"\']+)["\']\)')
QUERY_ID = re.compile(r'querySelector(?:All)?\(["\']#([A-Za-z][\w-]*)["\']')

# Nodes the native desktop shell injects into the webview at runtime. Each
# entry must name the owner so the exemption stays reviewable.
DESKTOP_INJECTED = {
    "updateGate": "desktop native updater dialog",
    "updateVersion": "desktop native updater dialog",
    "updateCurrent": "desktop native updater dialog",
    "updateNotes": "desktop native updater dialog",
    "updateHint": "desktop native updater dialog",
    "updateInstall": "desktop native updater dialog",
    "updateLater": "desktop native updater dialog",
    "updateProgress": "desktop native updater dialog",
    "updateBar": "desktop native updater dialog",
    "updatePercent": "desktop native updater dialog",
}


def collect_ids(site: Path) -> set[str]:
    """Ids declared by pages or created by any script at runtime."""
    ids: set[str] = set()
    for page in site.glob("*.html"):
        ids |= set(HTML_ID.findall(page.read_text(encoding="utf-8")))
    scripts = site / "assets" / "js"
    if scripts.is_dir():
        for script in scripts.glob("*.js"):
            ids |= set(JS_ID_LITERAL.findall(script.read_text(encoding="utf-8")))
    return ids


def collect_refs(scripts: Path) -> dict[str, set[str]]:
    """Literal id selectors used by each script."""
    refs: dict[str, set[str]] = {}
    for script in sorted(scripts.glob("*.js")):
        text = script.read_text(encoding="utf-8")
        found = set(GET_BY_ID.findall(text)) | set(QUERY_ID.findall(text))
        if found:
            refs[script.name] = found
    return refs


def check(site: Path = SITE, extra: dict[str, str] | None = None) -> dict:
    scripts = site / "assets" / "js"
    declared = collect_ids(site)
    refs = collect_refs(scripts)
    allowed = dict(DESKTOP_INJECTED)
    if extra:
        allowed.update(extra)

    unresolved: list[str] = []
    by_script: dict[str, list[str]] = {}
    for name, ids in refs.items():
        missing = sorted(item for item in ids if item not in declared and item not in allowed)
        if missing:
            by_script[name] = missing
            for item in missing:
                unresolved.append(f"{name}: #{item}")

    constrained = sorted(
        name for ids in refs.values() for name in ids if name in allowed and name not in declared
    )
    return {
        "declaredIds": len(declared),
        "scripts": len(refs),
        "references": sum(len(value) for value in refs.values()),
        "unresolved": sorted(unresolved),
        "allowedInjected": constrained,
        "reasons": {name: allowed[name] for name in constrained},
        "ok": not unresolved,
    }


def _format(result: dict) -> str:
    lines = [
        f"dom refs: {result['references']} selectors across {result['scripts']} scripts, "
        f"{result['declaredIds']} ids declared"
    ]
    for item in result["unresolved"]:
        lines.append(f"  UNRESOLVED: {item}")
    for name in result["allowedInjected"]:
        lines.append(f"  injected (allowed): #{name} — {result['reasons'][name]}")
    lines.append("dom refs: OK" if result["ok"] else "dom refs: FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=SITE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(args.site)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
