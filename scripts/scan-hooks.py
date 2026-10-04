#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Scan plugin hooks for network use and shell downloads.

Run it through `mise run scan:hooks`. Pass a repo root to scan another tree.
Exits 1 and prints one `path:line: rule: text` line per finding. Lists each
file it scanned on stderr.
"""

import json
import re
import sys
from pathlib import Path

# The path may follow a closing quote, as in "${CLAUDE_PLUGIN_ROOT}"/hooks/run.sh.
ROOT_REF = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?\"?(/[^\s\"';|&)]+)")

CODE_SUFFIXES = {
    ".sh",
    ".bash",
    ".zsh",
    ".py",
    ".pl",
    ".pm",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".rb",
}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}

SHELL = r"(?:ba|z|k|da)?sh"

# A PEP 723 header that lists dependencies makes uv download them. The header is
# a comment, so it is checked apart from the rules below.
INLINE_DEPS = re.compile(r"^#\s*dependencies\s*=\s*\[(?!\s*\])")

# Each rule is a pattern for one line. One set covers every language, so a
# Python import inside a shell heredoc still counts.
RULES = {
    "network-tool": re.compile(
        r"\b(curl|wget|nc|ncat|netcat|socat|telnet|ssh|scp|sftp|ftp)\b"
    ),
    "pipe-to-shell": re.compile(rf"\|\s*(?:sudo\s+(?:-\S+\s+)*)?{SHELL}\b"),
    "shell-from-stream": re.compile(rf"(?:^|[\s;&|(])(?:source|\.|{SHELL}|eval)\s+<\("),
    "dev-tcp": re.compile(r"/dev/(?:tcp|udp)/"),
    "package-fetch": re.compile(
        r"""
        \b(?:uvx|npx|bunx|pnpx)\b
        | \bpnpm\s+dlx\b
        | \b(?:pip3?|uv\s+pip|pipx)\s+install\b
        | \b(?:pipx|uv\s+tool)\s+run\b
        | \buv\s+run\b.*\s--with\b
        | \bgit\s+(?:clone|fetch|pull)\b
        """,
        re.VERBOSE,
    ),
    "network-module": re.compile(
        r"""
        # Python, also inside python -c '...' or after a semicolon
        (?:^|[\s;'"])(?:from\s+|import\s+(?:[\w.]+\s*,\s*)*)
          (?:urllib3?|requests|httpx|aiohttp|socket|ssl|http\.client|ftplib|smtplib
            |telnetlib|xmlrpc|websockets?)\b
        # JavaScript
        | (?:require\(\s*|from\s+|import\(\s*)["'](?:node:)?
          (?:https?|http2|net|dgram|tls|undici|axios|node-fetch)["']
        | (?<![\w.$])fetch\s*\(
        # Perl, also loaded with perl -M
        | (?:\b(?:use|require)\s+|(?:^|\s)-M)
          (?:LWP\b|HTTP::(?:Tiny|Request)\b|IO::Socket\b|Net::|Socket\b|Mojo::UserAgent\b)
        # Ruby
        | \brequire\s*\(?\s*["'](?:net/|open-uri|socket|httparty|faraday)
        """,
        re.VERBOSE,
    ),
}


def main(argv: list[str]) -> int:
    root = (Path(argv[1]) if len(argv) > 1 else Path(__file__).parent.parent).resolve()
    findings = []
    scanned = []
    for plugin in sorted((root / "plugins").glob("*/")):
        found, read = scan_plugin(root, plugin)
        findings += found
        scanned += read
    for path in scanned:
        print(f"scanned {path}", file=sys.stderr)
    for finding in findings:
        print(finding)
    print(f"{len(scanned)} files, {len(findings)} findings", file=sys.stderr)
    return 1 if findings else 0


def scan_plugin(root: Path, plugin: Path) -> tuple[list[str], list[Path]]:
    """The plugin's findings, and the files it read to find them."""
    findings, configs = hook_configs(root, plugin)
    # A hook script often runs others by a path built at run time, such as
    # "$bin_dir/tool.pl". So any code file whose name a command or a scanned
    # file mentions is scanned too. Files under skills/ are left to the skill
    # scan.
    candidates = [
        f for f in code_files(plugin) if "skills" not in f.relative_to(plugin).parts
    ]
    queue = []
    for rel, config in configs:
        for hook in hooks(config):
            if hook.get("type") == "http" or "url" in hook:
                findings.append(f"{rel}: http-hook: {hook.get('url')}")
            command = hook.get("command")
            if not isinstance(command, str):
                continue
            findings += [
                f"{rel}: {rule}: {command}" for rule in matching_rules(command)
            ]
            for ref in ROOT_REF.findall(command):
                path, problem = plugin_file(plugin, ref)
                if problem:
                    findings.append(f"{rel}: {problem}: {ref.lstrip('/')}")
                else:
                    queue.append(path)
            queue += [f for f in candidates if mentions(command, f)]

    seen = set()
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        text = path.read_text()
        findings += scan_text(path.relative_to(root), text)
        queue += [f for f in candidates if mentions(text, f)]
    return findings, [rel for rel, _ in configs] + sorted(
        p.relative_to(root) for p in seen
    )


def hook_configs(
    root: Path, plugin: Path
) -> tuple[list[str], list[tuple[Path, object]]]:
    """The plugin's hook configs: hooks/hooks.json, plus what plugin.json declares.

    plugin.json may hold the config inline, or name config files by path.
    """
    findings = []
    configs = []
    default = plugin / "hooks" / "hooks.json"
    if default.is_file():
        configs.append((default.relative_to(root), json.loads(default.read_text())))
    manifest = plugin / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return findings, configs
    declared = json.loads(manifest.read_text()).get("hooks")
    if isinstance(declared, dict):
        configs.append((manifest.relative_to(root), declared))
        return findings, configs
    for ref in [declared] if isinstance(declared, str) else declared or []:
        path, problem = plugin_file(plugin, ref)
        if problem:
            findings.append(f"{manifest.relative_to(root)}: {problem}: {ref}")
        elif path != default.resolve():
            configs.append((path.relative_to(root), json.loads(path.read_text())))
    return findings, configs


def plugin_file(plugin: Path, ref: str) -> tuple[Path, str | None]:
    """Resolve a path relative to the plugin root. The second value names a problem."""
    path = (plugin / ref.lstrip("/")).resolve()
    if not path.is_relative_to(plugin):
        return path, "outside-plugin"
    if not path.is_file():
        return path, "missing-file"
    return path, None


def hooks(node) -> list[dict]:
    """Every hook in a hook config, at any depth. A hook is an object with a type."""
    if isinstance(node, dict):
        found = [node] if "type" in node else []
        return found + [h for v in node.values() for h in hooks(v)]
    if isinstance(node, list):
        return [h for v in node for h in hooks(v)]
    return []


def code_files(plugin: Path) -> list[Path]:
    """The plugin's files that can run: a known script type, or a shebang."""
    found = []
    for path in sorted(plugin.rglob("*")):
        if not path.is_file() or SKIP_DIRS & set(path.relative_to(plugin).parts):
            continue
        if path.suffix in CODE_SUFFIXES or path.read_bytes()[:2] == b"#!":
            found.append(path)
    return found


def mentions(text: str, path: Path) -> bool:
    """Whether text mentions the file by name, or imports it as a Python module."""
    name = re.escape(path.name)
    if re.search(rf"(?<![\w.-]){name}(?![\w.-])", text):
        return True
    module = re.escape(path.stem)
    return path.suffix == ".py" and bool(
        re.search(rf"^\s*(?:import|from)\s+{module}\b", text, re.MULTILINE)
    )


def scan_text(rel: Path, text: str) -> list[str]:
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        if INLINE_DEPS.search(line):
            findings.append(f"{rel}:{number}: package-fetch: {line.strip()}")
        # A whole-line comment runs nothing. A comment after code is still read.
        if line.lstrip().startswith(("#", "//")):
            continue
        findings += [
            f"{rel}:{number}: {rule}: {line.strip()}" for rule in matching_rules(line)
        ]
    return findings


def matching_rules(text: str) -> list[str]:
    return [rule for rule, pattern in RULES.items() if pattern.search(text)]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
