#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Lint the cowork:build skill: evidence marks and relative links.

Usage: lint-cowork-marks.py [DIR]   (default: plugins/cowork/skills/build)

Marks must fit the legend in SKILL.md "Freshness". Relative Markdown links must
point at a file that exists, and a #anchor must match a heading under GitHub's
slug rules. Prints path:line: message per failure and exits 1 if any.
"""

import re
import sys
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "plugins/cowork/skills/build"

DATE = r"(?:\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])|<date>)"
MARK_FORMS = [
    r"V",
    r"V, measured",
    r"V on two sites",
    r"V, user report",
    r"V: absence",
    rf"V, live {DATE}(?: to {DATE})?",
    r"V, conflicting",
    r"V/I",
    r"I",
    r"I[,:] [^\]]+",  # [I, strong], [I: test it]
    r"I (?:that|for|on|in|about|when|if) [^\]]+",  # [I that bodies are ...]
    r"V for [^;\]]+; I for [^\]]+",
]
MARK_RE = re.compile("|".join(f"(?:{p})" for p in MARK_FORMS))
MARK_FINDER = re.compile(r"\*\*\[(.*?)\]\*\*", re.DOTALL)
LINK_RE = re.compile(r"(?<!!)\[(?:[^\[\]])*?\]\(([^)\s]*)\)")


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else DEFAULT_DIR
    files = sorted(root.rglob("*.md"))
    if not files:
        print(f"{root}: no Markdown files found")
        return 1
    failures = []
    for path in files:
        failures += check_file(path)
    for f in failures:
        print(f)
    return 1 if failures else 0


def check_file(path):
    prose = blank_code(path.read_text())
    out = []
    for m in MARK_FINDER.finditer(prose):
        inner = " ".join(m.group(1).split())
        if not MARK_RE.fullmatch(inner):
            out.append(f"{path}:{line_of(prose, m.start())}: invalid evidence mark **[{inner}]**")
    for m in LINK_RE.finditer(prose):
        err = check_link(path, m.group(1))
        if err:
            out.append(f"{path}:{line_of(prose, m.start(1))}: {err}")
    return out


def check_link(path, target):
    if not target or re.match(r"[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
        return None  # http(s), mailto and the like
    file_part, _, anchor = target.partition("#")
    dest = (path.parent / file_part) if file_part else path
    if not dest.is_file():
        return f"broken link: {file_part} does not exist"
    if anchor and anchor not in anchors(dest):
        return f"broken anchor: #{anchor} matches no heading in {dest.name}"
    return None


def anchors(path):
    seen = {}
    result = set()
    for line in blank_code(path.read_text()).splitlines():
        h = re.match(r" {0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
        if not h:
            continue
        slug = slugify(h.group(1))
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        result.add(slug if n == 0 else f"{slug}-{n}")
    return result


def slugify(heading):
    heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # links keep text
    heading = heading.replace("`", "").replace("*", "")
    heading = re.sub(r"[^\w\- ]", "", heading.lower())
    return heading.replace(" ", "-")


def blank_code(text):
    """Replace fenced code and inline code spans with spaces, keeping newlines."""

    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))

    text = re.sub(r"^ {0,3}(`{3,}|~{3,}).*?^ {0,3}\1[`~]*[ \t]*$", blank, text, flags=re.DOTALL | re.MULTILINE)
    return re.sub(r"(`+)(?!`).+?(?<!`)\1(?!`)", blank, text, flags=re.DOTALL)


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
