#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8.0"]
# ///
"""Tests for scan-hooks.py — which plugin hooks fail the scan, and which pass."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCAN = Path(__file__).parent / "scan-hooks.py"
RUN = '"${CLAUDE_PLUGIN_ROOT}/hooks/run.sh"'


def hooks_json(*commands):
    """A hooks.json body that runs each command on UserPromptSubmit."""
    hooks = [{"type": "command", "command": c} for c in commands]
    return json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": hooks}]}})


def plugin(root: Path, files: dict[str, str], name="demo"):
    """Write a plugin's files under root/plugins/<name>/."""
    for rel, text in files.items():
        path = root / "plugins" / name / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def scan(root: Path):
    result = subprocess.run(
        [sys.executable, SCAN, root],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    return result


def test_passes_a_hook_with_no_network_use(tmp_path):
    plugin(tmp_path, {"hooks/hooks.json": hooks_json(RUN), "hooks/run.sh": "echo hi\n"})
    assert scan(tmp_path).returncode == 0


def test_fails_a_hook_script_that_calls_curl(tmp_path):
    plugin(
        tmp_path,
        {
            "hooks/hooks.json": hooks_json(RUN),
            "hooks/run.sh": "#!/bin/bash\nset -eu\ncurl -s https://example.com\n",
        },
    )
    result = scan(tmp_path)
    assert result.returncode == 1
    assert "plugins/demo/hooks/run.sh:3: network-tool:" in result.stdout


@pytest.mark.parametrize(
    "script, line, rule",
    [
        ("run.sh", 'printf "%s" "$code" | bash', "pipe-to-shell"),
        ("run.sh", 'base64 -d <<<"$x" | sudo sh -s', "pipe-to-shell"),
        ("run.sh", 'source <(cat "$f")', "shell-from-stream"),
        ("run.sh", 'bash <(cat "$f")', "shell-from-stream"),
        ("run.sh", "exec 3<>/dev/tcp/example.com/80", "dev-tcp"),
        ("run.py", "import urllib.request", "network-module"),
        ("run.py", "from http.client import HTTPSConnection", "network-module"),
        ("run.py", "import requests, socket", "network-module"),
        ("run.mjs", 'import https from "node:https";', "network-module"),
        ("run.mjs", 'const net = require("net");', "network-module"),
        ("run.mjs", "await fetch(url);", "network-module"),
        ("run.pl", "use LWP::UserAgent;", "network-module"),
        ("run.pl", "use IO::Socket::INET;", "network-module"),
        ("run.pl", "use HTTP::Tiny;", "network-module"),
    ],
)
def test_fails_a_hook_script_with_a_risky_line(tmp_path, script, line, rule):
    command = f'"${{CLAUDE_PLUGIN_ROOT}}/hooks/{script}"'
    plugin(
        tmp_path,
        {"hooks/hooks.json": hooks_json(command), f"hooks/{script}": f"{line}\n"},
    )
    result = scan(tmp_path)
    assert result.returncode == 1
    assert f"plugins/demo/hooks/{script}:1: {rule}: {line}" in result.stdout


@pytest.mark.parametrize(
    "line",
    [
        "sha=$(printf '%s' \"$f\" | shasum -a 256)",
        'out=$(sha256sum <<<"$f")',
        "use HTML::Parser ();",
        "from html.parser import HTMLParser",
        'printf \'%s\' "$payload" | "$here/lint.py"',
        'while read -r line; do :; done < <(jq -r . <<<"$p")',
        "# A redirect from /dev/tcp/HOST/PORT opens a connection.",
        "  # Never curl here.",
        "// fetch(url) would reach the network.",
    ],
)
def test_passes_a_line_that_only_looks_risky(tmp_path, line):
    plugin(tmp_path, {"hooks/hooks.json": hooks_json(RUN), "hooks/run.sh": f"{line}\n"})
    result = scan(tmp_path)
    assert (result.returncode, result.stdout) == (0, "")


@pytest.mark.parametrize(
    "mention, path",
    [
        ('source "$here/lib.sh"', "hooks/lib.sh"),
        ('"$(writing_bin_dir)/tool.pl" "$log"', "bin/tool.pl"),
        ("import helper", "hooks/helper.py"),
        ("from helper import run", "hooks/helper.py"),
    ],
)
def test_fails_a_file_the_hook_script_names(tmp_path, mention, path):
    plugin(
        tmp_path,
        {
            "hooks/hooks.json": hooks_json(RUN),
            "hooks/run.sh": f"{mention}\n",
            path: "echo ok\ncurl -s https://example.com\n",
        },
    )
    result = scan(tmp_path)
    assert result.returncode == 1
    assert f"plugins/demo/{path}:2: network-tool:" in result.stdout


def test_follows_names_through_several_files(tmp_path):
    plugin(
        tmp_path,
        {
            "hooks/hooks.json": hooks_json(RUN),
            "hooks/run.sh": 'exec "$here/a.sh"\n',
            "hooks/a.sh": 'exec "$here/run.sh" "$here/b.sh"\n',
            "hooks/b.sh": "wget https://example.com\n",
        },
    )
    result = scan(tmp_path)
    assert result.returncode == 1
    assert "plugins/demo/hooks/b.sh:1: network-tool:" in result.stdout


def test_ignores_a_file_no_hook_names(tmp_path):
    plugin(
        tmp_path,
        {
            "hooks/hooks.json": hooks_json(RUN),
            "hooks/run.sh": "echo hi\n",
            "hooks/test_run.py": "import socket\n",
            "bin/other.sh": "curl https://example.com\n",
        },
    )
    assert scan(tmp_path).returncode == 0


def test_leaves_a_named_skill_file_to_the_skill_scan(tmp_path):
    plugin(
        tmp_path,
        {
            "hooks/hooks.json": hooks_json(RUN),
            "hooks/run.sh": 'script="$CLAUDE_PLUGIN_ROOT/skills/ask/scripts/ask.py"\n',
            "skills/ask/scripts/ask.py": "import urllib.request\n",
        },
    )
    assert scan(tmp_path).returncode == 0


def test_ignores_a_named_file_that_is_not_code(tmp_path):
    plugin(
        tmp_path,
        {
            "hooks/hooks.json": hooks_json(RUN),
            "hooks/run.sh": 'rules="$dir/common.md"\n',
            "defaults/common.md": "Never tell the user to curl a URL.\n",
        },
    )
    assert scan(tmp_path).returncode == 0


def test_fails_a_command_whose_script_is_missing(tmp_path):
    plugin(tmp_path, {"hooks/hooks.json": hooks_json(RUN)})
    result = scan(tmp_path)
    assert result.returncode == 1
    assert "plugins/demo/hooks/hooks.json: missing-file: hooks/run.sh" in result.stdout


def test_fails_a_command_that_reaches_outside_the_plugin(tmp_path):
    command = '"${CLAUDE_PLUGIN_ROOT}/../other/run.sh"'
    plugin(tmp_path, {"hooks/hooks.json": hooks_json(command)})
    plugin(tmp_path, {"run.sh": "curl https://example.com\n"}, name="other")
    result = scan(tmp_path)
    assert result.returncode == 1
    assert (
        "plugins/demo/hooks/hooks.json: outside-plugin: ../other/run.sh"
        in result.stdout
    )


def test_fails_an_http_hook(tmp_path):
    hook = {"type": "http", "url": "https://example.com/hook"}
    config = {"hooks": {"Stop": [{"hooks": [hook]}]}}
    plugin(tmp_path, {"hooks/hooks.json": json.dumps(config)})
    result = scan(tmp_path)
    assert result.returncode == 1
    assert (
        "plugins/demo/hooks/hooks.json: http-hook: https://example.com/hook"
        in result.stdout
    )


def test_fails_a_hook_declared_inline_in_the_manifest(tmp_path):
    manifest = {
        "name": "demo",
        "hooks": json.loads(hooks_json("curl https://example.com")),
    }
    plugin(tmp_path, {".claude-plugin/plugin.json": json.dumps(manifest)})
    result = scan(tmp_path)
    assert result.returncode == 1
    assert (
        "plugins/demo/.claude-plugin/plugin.json: network-tool: curl" in result.stdout
    )


@pytest.mark.parametrize("ref", ["./config/extra.json", ["./config/extra.json"]])
def test_fails_a_hook_file_the_manifest_names(tmp_path, ref):
    plugin(
        tmp_path,
        {
            ".claude-plugin/plugin.json": json.dumps({"name": "demo", "hooks": ref}),
            "config/extra.json": hooks_json(RUN),
            "hooks/run.sh": "nc -l 4444\n",
        },
    )
    result = scan(tmp_path)
    assert result.returncode == 1
    assert "plugins/demo/hooks/run.sh:1: network-tool:" in result.stdout


def test_fails_an_inline_command_that_calls_wget(tmp_path):
    plugin(tmp_path, {"hooks/hooks.json": hooks_json("wget -qO- https://example.com")})
    result = scan(tmp_path)
    assert result.returncode == 1
    assert "plugins/demo/hooks/hooks.json: network-tool: wget -qO-" in result.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
