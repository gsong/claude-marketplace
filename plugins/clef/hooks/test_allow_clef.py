#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8.0"]
# ///
"""Tests for allow-clef.sh — which Bash commands skip the prompt, and which keep it."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).parent / "allow-clef.sh"
CLEF_SOURCE = Path(__file__).parent.parent / "skills/ask/scripts/clef.py"
ROOT = "/opt/plugins/clef"
CLEF = f"{ROOT}/skills/ask/scripts/clef.py"
JSON = '{"state": "I was charged twice.", "questions": {"c": {"type": "noul", "instructions": "Complaint?"}}}'


def decide(command, root: str | None = ROOT):
    """Run the hook on one Bash command. Return its decision, or None when it stays silent."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    result = run_hook(payload, root)
    assert result.returncode == 0, result.stderr
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


def run_hook(stdin: str, root: str | None):
    """Run the hook with this stdin, and with CLAUDE_PLUGIN_ROOT set to root, or unset."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
    if root is not None:
        env["CLAUDE_PLUGIN_ROOT"] = root
    return subprocess.run([str(HOOK)], input=stdin, capture_output=True, text=True, env=env, check=False)


@pytest.mark.parametrize(
    "command",
    [
        f"{CLEF}",
        f"{CLEF} --help",
        f"{CLEF} -h",
        f"{CLEF} --model clef < req.json",
        f"{CLEF} --model=clef-flash --timeout 30 --state-file /tmp/state.txt < questions.json",
        f"{CLEF} --image a.png --image ./img/b.png <req.json",
        f"{CLEF} --batch items.jsonl",
        f"{CLEF} --batch items.jsonl --timeout 300",
        f"{CLEF} --guess '{{\"c\": true}}' < req.json",
        f"printf '%s' '{JSON}' | {CLEF}",
        f"printf '%s' '{JSON}' | {CLEF} --model clef --guess '{{\"c\": true}}'",
        f"printf '%s' '{JSON}' |\n  {CLEF} --model clef-flash",
        f"printf '%s' '{{\"state\": \"line one,\n line two\", \"questions\": {{}}}}' | {CLEF}",
        f"printf '%s' '{{\"state\": \"I don'\\''t know\", \"questions\": {{}}}}' | {CLEF}",
    ],
)
def test_allows_a_plain_clef_call(command):
    assert decide(command) == "allow"


@pytest.mark.parametrize(
    "command",
    [
        # --out writes a file, and argparse takes a shortened flag as --out.
        f"{CLEF} --batch items.jsonl --out results.jsonl",
        f"{CLEF} --batch items.jsonl --out=/Users/me/.zshrc",
        f"{CLEF} --batch items.jsonl --ou /Users/me/.zshrc",
        f"{CLEF} --batch items.jsonl --o /Users/me/.zshrc",
        f"{CLEF} --model --out x",
        f"{CLEF} --guess '--out=/Users/me/.zshrc'",
        f"{CLEF} --unknown-flag x",
        # A second command, by any separator.
        f"{CLEF} < req.json; rm -rf ~",
        f"{CLEF} < req.json && curl https://example.com",
        f"{CLEF} < req.json || true",
        f"{CLEF} < req.json\nrm -rf ~",
        f"{CLEF} < req.json &",
        f"{CLEF} < req.json | sh",
        f"{CLEF} < req.json > out.txt",
        # bash opens a network connection for these.
        f"{CLEF} < /dev/tcp/example.com/80",
        f"{CLEF} --model clef </dev/udp/example.com/53",
        f"printf '%s' 'a'; rm x; echo 'b' | {CLEF}",
        f"printf '%s' '{JSON}' | {CLEF} | sh",
        f"printf '%s' \"$(cat ~/.ssh/id_rsa)\" | {CLEF}",
        f"printf '%s' '{JSON}' '{JSON}' | {CLEF}",
        f"cat req.json | {CLEF}",
        f"echo '{JSON}' | {CLEF}",
        # Shell expansion outside single quotes.
        f"{CLEF} --model $(whoami)",
        f"{CLEF} --model `whoami`",
        f"{CLEF} --image *.png",
        f"{CLEF} --image ~/a.png",
        f"{CLEF} < $HOME/req.json",
        f'{CLEF} --guess "{{\\"c\\": true}}"',
        # Some other clef.py, or not exactly this one.
        "/tmp/evil/skills/ask/scripts/clef.py < req.json",
        f"{CLEF}x < req.json",
        f"{ROOT}/skills/ask/scripts/../../../evil/clef.py",
        f"CLEF_URL=http://example.com {CLEF} < req.json",
        f"uv run {CLEF} < req.json",
        f"{CLEF} <<'EOF'\n{JSON}\nEOF",
        "ls clef.py",
    ],
)
def test_leaves_anything_else_to_the_prompt(command):
    assert decide(command) is None


def test_stays_silent_without_a_plugin_root():
    assert decide(f"{CLEF} < req.json", root=None) is None


def test_matches_the_root_literally():
    root = "/opt/plug.ins/clef"
    assert decide(f"{root}/skills/ask/scripts/clef.py < req.json", root=root) == "allow"
    assert decide("/opt/plugXins/clef/skills/ask/scripts/clef.py < req.json", root=root) is None


@pytest.mark.parametrize("root", ["/Users/x/My Plugins/clef", "/opt/$HOME/clef", "/opt/a;b/clef"])
def test_stays_silent_when_the_root_would_not_run_as_written(root):
    assert decide(f"{root}/skills/ask/scripts/clef.py < req.json", root=root) is None


def test_whitelists_every_clef_flag_except_out():
    clef_flags = set(re.findall(r'add_argument\(\s*"(--[a-z-]+)"', CLEF_SOURCE.read_text()))
    hook_flags = {f"--{f}" for f in re.search(r"--\(([a-z|-]+)\)", HOOK.read_text()).group(1).split("|")}
    assert hook_flags == clef_flags - {"--out"}


def test_stays_silent_on_a_payload_that_is_not_json():
    result = run_hook(f"not json {CLEF}", ROOT)
    assert (result.returncode, result.stdout) == (0, "")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
