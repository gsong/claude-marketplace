#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8.0"]
# ///
"""Tests for lint-cowork-marks.py: which marks and links pass, and which fail."""

import subprocess
import sys
from pathlib import Path

import pytest

LINT = Path(__file__).parent / "lint-cowork-marks.py"


def lint(tmp_path: Path, files: dict[str, str]):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    result = subprocess.run(
        [sys.executable, LINT, tmp_path],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.returncode, result.stdout


@pytest.mark.parametrize(
    "mark",
    [
        "V",
        "V, measured",
        "V on two sites",
        "V, user report",
        "V: absence",
        "V, live 2026-10-16",
        "V, live 2026-10-16 to 2026-10-18",
        "V, live <date>",
        "I",
        "I, strong",
        "I: test it",
        "I that bodies are unavailable there",
        "V/I",
        "V, conflicting",
        "V for that build;\nI for other builds and rollouts",
    ],
)
def test_legal_marks_pass(tmp_path, mark):
    code, out = lint(tmp_path, {"a.md": f"Claim **[{mark}]** here.\n"})
    assert (code, out) == (0, "")


@pytest.mark.parametrize(
    "mark",
    ["V, live", "Verified", "V, live 2026-13-40", "V, live 2026-10-16 to", "X", "V, guess"],
)
def test_illegal_marks_fail_with_line(tmp_path, mark):
    code, out = lint(tmp_path, {"a.md": f"one\nClaim **[{mark}]** here.\n"})
    assert code == 1
    assert out.startswith(f"{tmp_path / 'a.md'}:2: invalid evidence mark")


def test_marks_in_code_are_skipped(tmp_path):
    text = "Use `**[Verified]**` or\n\n```\n**[V, live]**\n```\n"
    assert lint(tmp_path, {"a.md": text}) == (0, "")


def test_links_and_anchors_resolve(tmp_path):
    files = {
        "a.md": "# Top\n\n## Claude Code's browsers\n\n"
        "[x](b.md#within-one-run) [y](#claude-codes-browsers) [z](https://x.test/#nope)\n",
        "b.md": "## Within one run\n",
    }
    assert lint(tmp_path, files) == (0, "")


def test_broken_anchor_and_file_fail(tmp_path):
    files = {
        "a.md": "[x](b.md#missing)\n[y](#nowhere)\n[z](gone.md)\n",
        "b.md": "## Present\n",
    }
    code, out = lint(tmp_path, files)
    assert code == 1
    lines = out.splitlines()
    assert len(lines) == 3
    assert "a.md:1: broken anchor: #missing" in lines[0]
    assert "a.md:2: broken anchor: #nowhere" in lines[1]
    assert "a.md:3: broken link: gone.md" in lines[2]


def test_link_wrapped_across_lines_is_checked(tmp_path):
    code, out = lint(tmp_path, {"a.md": "[some\ntext](gone.md)\n"})
    assert code == 1
    assert "a.md:2: broken link" in out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
