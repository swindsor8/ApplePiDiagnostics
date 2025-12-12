#!/usr/bin/env python3
"""Extract README.md headings and content into a machine-readable JSON.

Produces `full-linux-gui/tools/readme_rules.json` summarizing sections.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
OUT = Path(__file__).resolve().parent / "readme_rules.json"


def parse_readme(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections = {}
    cur = None
    buf = []
    for ln in lines:
        if ln.strip().startswith("#"):
            if cur is not None:
                sections[cur] = "\n".join(buf).strip()
            # normalize heading (strip leading # and spaces)
            cur = ln.lstrip('#').strip()
            buf = []
        else:
            buf.append(ln)
    if cur is not None:
        sections[cur] = "\n".join(buf).strip()
    return sections


def main():
    if not README.exists():
        raise SystemExit(f"README not found at {README}")
    sections = parse_readme(README)
    summary = {
        "source": str(README),
        "sections": sections,
    }
    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == '__main__':
    main()
