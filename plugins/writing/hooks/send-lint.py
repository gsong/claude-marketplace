#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PreToolUse voice lint for text that leaves the machine: Slack, email drafts,
canvases, Claude Docs, Google Drive files, Artifacts, and GitHub comments sent
through `gh`. Reads the hook payload on stdin. Finds the outgoing text through
the table in surfaces.py, scans it with bin/voice-scan.pl against common.md plus
the surface's profile, and reports.

Two kinds of report, because a PreToolUse hook's additionalContext reaches
Claude only after the tool has run:

- Soft surfaces (drafts, canvases, docs, files) can be edited after they land,
  so the findings arrive as advisory context and the call goes through.
- Hard surfaces (a sent Slack message, a posted GitHub comment) cannot be taken
  back. Advice that arrives after the send is too late, so the first send with
  findings is denied, once. The retry to the same target within 30 minutes goes
  through whatever it says: the user's voice is theirs to keep, and a lint that
  can block a send forever gets switched off.

Any error exits 0 with no output. A broken lint must never block a send.
"""

import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True  # keep __pycache__ out of the plugin directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
import surfaces

BOUNCE_TTL_SECONDS = 30 * 60


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    if not isinstance(payload, dict):
        return
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input")
    surface = surfaces.surface_for(tool_name)
    if surface is None or not isinstance(tool_input, dict):
        return

    cwd = Path(payload.get("cwd") or ".")
    found = surface.extract(tool_input, cwd)
    if not found.texts:
        return

    rule_files = _rule_files(surface.profile)
    if not rule_files:
        return
    reports = [(text.label, _scan(rule_files, text)) for text in found.texts]
    reports = [(label, lines) for label, lines in reports if lines]

    bounce = _bounce_path(payload, tool_name, found.target) if surface.hard else None
    # Findings mean something only when a rule fired. A malformed rule file on
    # its own is the rules' problem, not this text's, and must not bounce a send.
    if not any(_is_finding(line) for _, lines in reports for line in lines):
        if bounce is not None:
            bounce.unlink(missing_ok=True)  # the retry came back clean
        return

    findings = _format(reports)
    where = found.target if tool_name == "Bash" else _short_name(tool_name)
    if bounce is None:
        _emit(
            {
                "hookEventName": "PreToolUse",
                "additionalContext": f'writing send-lint, profile "{surface.profile}", on {where}:\n\n'
                f"{findings}\n\n"
                "Advisory only. Fix what is a real violation in a follow-up edit if the surface allows it.",
            }
        )
        return

    if _fresh(bounce):
        bounce.unlink(missing_ok=True)
        return
    bounce.parent.mkdir(parents=True, exist_ok=True)
    bounce.write_text(f"{tool_name}\n{found.target}\n", encoding="utf-8")
    _emit(
        {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f'writing send-lint, profile "{surface.profile}", on {where}:\n\n'
            f"{findings}\n\n"
            "This send is bounced once so the findings arrive before the text goes out. "
            "Fix what is a real violation, or keep the text as is, and send again. "
            "The retry within 30 minutes goes through.",
        }
    )


# --- resolution (mirrors hooks/lib.sh) ---------------------------------


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(env) if env else Path(__file__).resolve().parent.parent


def _rules_dir() -> Path:
    env = os.environ.get("WRITING_LINE_RULES")
    if env:
        return Path(env)
    user = Path.home() / ".claude" / "writing-line" / "rules"
    if user.is_dir():
        return user
    return _plugin_root() / "defaults" / "rules"


def _state_dir() -> Path:
    env = os.environ.get("WRITING_LINE_STATE")
    return Path(env) if env else Path.home() / ".claude" / "state" / "writing-line"


def _bin_dir() -> Path:
    env = os.environ.get("WRITING_LINE_BIN")
    return Path(env) if env else _plugin_root() / "bin"


def _rule_files(profile: str) -> list[Path]:
    rules_dir = _rules_dir()
    rules = rules_dir / f"{profile}.md"
    if not rules.is_file():
        return []
    common = rules_dir / "common.md"
    # common.md first, so the profile file, parsed second, wins on maxwords.
    return ([common] if common.is_file() and common != rules else []) + [rules]


# --- scanning ----------------------------------------------------------


def _scan(rule_files: list[Path], text: surfaces.Text) -> list[str]:
    prose = _flatten_html(text.text) if text.html else text.text
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", prefix="writing-send-") as tmp:
        tmp.write(prose)
        tmp.flush()
        result = subprocess.run(
            [_perl(), str(_bin_dir() / "voice-scan.pl"), *map(str, rule_files), tmp.name],
            capture_output=True,
            check=False,
            text=True,
            timeout=20,
        )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _flatten_html(markup: str) -> str:
    """HTML is markup, not prose: flatten it with bin/html-prose.pl, the same
    converter the draft gate uses. If that fails (it needs HTML::Parser), strip
    tags here rather than scan CSS and attributes as sentences."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".html", prefix="writing-send-") as tmp:
        tmp.write(markup)
        tmp.flush()
        try:
            result = subprocess.run(
                [_perl(), str(_bin_dir() / "html-prose.pl"), tmp.name],
                capture_output=True,
                check=False,
                text=True,
                timeout=20,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except (OSError, subprocess.SubprocessError):
            pass
    return _strip_tags(markup)


def _strip_tags(markup: str) -> str:
    """Drop markup but keep every newline, so line numbers still point into the
    source. Cruder than html-prose.pl: a sentence the source wraps stays split."""

    def blank(match: re.Match) -> str:
        return "\n" * match.group(0).count("\n")

    text = re.sub(r"(?is)<(style|script|noscript|template)\b.*?</\1\s*>", blank, markup)
    text = re.sub(r"(?s)<!--.*?-->", blank, text)
    text = re.sub(r"(?s)<[^>]*>", lambda m: blank(m) or " ", text)
    return html.unescape(text)


def _perl() -> str:
    # /usr/bin/perl needs no login shell. Fall back to PATH where it is absent.
    return "/usr/bin/perl" if Path("/usr/bin/perl").exists() else "perl"


def _is_finding(line: str) -> bool:
    return not line.startswith("rule file malformed")


def _format(reports: list[tuple[str, list[str]]]) -> str:
    if len(reports) == 1:
        label, lines = reports[0]
        return f"[{label}]\n" + "\n".join(lines)
    return "\n\n".join(f"[{label}]\n" + "\n".join(lines) for label, lines in reports)


# --- bounce once -------------------------------------------------------


def _bounce_path(payload: dict, tool_name: str, target: str) -> Path:
    key = f"{payload.get('session_id') or ''}|{tool_name}|{target}"
    return _state_dir() / "bounces" / hashlib.sha256(key.encode("utf-8")).hexdigest()


def _fresh(path: Path) -> bool:
    try:
        return time.time() - path.stat().st_mtime < BOUNCE_TTL_SECONDS
    except OSError:
        return False


# --- output ------------------------------------------------------------


def _short_name(tool_name: str) -> str:
    return tool_name.rsplit("__", 1)[-1]


def _emit(hook_output: dict) -> None:
    json.dump({"hookSpecificOutput": hook_output}, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 -- a broken lint must never block a send
        sys.exit(0)
