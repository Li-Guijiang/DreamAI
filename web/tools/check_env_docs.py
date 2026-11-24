"""Keep the server configuration reference in sync with the code.

Adding an environment variable to ``config.py`` is easy; remembering to
document it is not. This tool fails when a variable read by the server is
absent from ``docs/CONFIGURATION.md``. Variables that belong to other
components are allowed only in the document's final "out of scope" section,
so they cannot be mistaken for server settings.

Read-only. Exits non-zero when the reference is incomplete or misleading.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "web" / "app" / "config.py"
DOCUMENT = ROOT / "docs" / "CONFIGURATION.md"
ENV_NAME = re.compile(r"DREAMAI_[A-Z0-9_]+")
ENV_DEFAULT = re.compile(
    r'_env(?:_int|_float)?\(\s*"(DREAMAI_[A-Z0-9_]+)"\s*,\s*'
    r"([0-9]+(?:\.[0-9]+)?(?:\s*\*\s*[0-9]+(?:\.[0-9]+)?)*)"
)
DOC_DEFAULT = re.compile(
    r"^\|\s*`(DREAMAI_[A-Z0-9_]+)`\s*\|\s*`?([0-9]+(?:\.[0-9]+)?)`?\s*(?:秒)?\s*\|",
    re.M,
)
OUT_OF_SCOPE = "## 9. 不属于本文的变量"


def check(config: Path = CONFIG, document: Path = DOCUMENT) -> dict:
    """Compare the variables in code with the ones described in the document."""
    if not config.is_file() or not document.is_file():
        return {
            "config": str(config),
            "document": str(document),
            "variables": 0,
            "missing": ["configuration files not found"],
            "defaultDrift": [],
            "misplaced": [],
            "ok": False,
        }

    code_names = set(ENV_NAME.findall(config.read_text(encoding="utf-8")))
    text = document.read_text(encoding="utf-8")
    main_text, separator, out_of_scope_text = text.partition(OUT_OF_SCOPE)
    documented = set(ENV_NAME.findall(text))
    before = set(ENV_NAME.findall(main_text))
    after = set(ENV_NAME.findall(out_of_scope_text)) if separator else set()

    missing = sorted(code_names - documented)

    # Numeric defaults must match too. Descriptive cells ("empty", "built-in
    # prompt", a URL name) are deliberately left out of this comparison.
    def numeric(expression: str) -> float:
        # Only digits and multiplication signs reach this function via the
        # regex above; no general expression evaluation is involved.
        result = 1.0
        for factor in expression.split("*"):
            result *= float(factor.strip())
        return result

    code_defaults = {
        name: numeric(value)
        for name, value in ENV_DEFAULT.findall(config.read_text(encoding="utf-8"))
    }
    doc_defaults = {name: float(value) for name, value in DOC_DEFAULT.findall(main_text)}
    drifted = sorted(
        f"{name}: code={code_defaults[name]:g}, docs={doc_defaults[name]:g}"
        for name in code_defaults.keys() & doc_defaults.keys()
        if code_defaults[name] != doc_defaults[name]
    )
    # A name listed before the boundary looks like a server setting but has no
    # counterpart in config.py. The boundary section exists for those names.
    misplaced = sorted(before - code_names)
    # A code variable mentioned only in the out-of-scope section is confusing.
    misplaced += sorted((code_names & after) - before)

    return {
        "config": str(config),
        "document": str(document),
        "variables": len(code_names),
        "documented": len(documented),
        "outOfScope": len(after),
        "missing": missing,
        "defaultDrift": drifted,
        "misplaced": sorted(set(misplaced)),
        "ok": not missing and not misplaced and not drifted,
    }


def _format(result: dict) -> str:
    lines = [
        f"env docs: {result['variables']} server variables, "
        f"{result['documented']} documented, {result['outOfScope']} out of scope"
    ]
    for name in result["missing"]:
        lines.append(f"  UNDOCUMENTED: {name}")
    for item in result["defaultDrift"]:
        lines.append(f"  DEFAULT DRIFT: {item}")
    for name in result["misplaced"]:
        lines.append(f"  OUT OF PLACE: {name}")
    lines.append("env docs: OK" if result["ok"] else "env docs: FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--document", type=Path, default=DOCUMENT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = check(args.config, args.document)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
