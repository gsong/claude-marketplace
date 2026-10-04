#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Scan plugin hooks for network use and code fetches.

Run it through `mise run scan:hooks`. Pass a repo root to scan another tree.
Exits 1 and prints one `path:line: rule: text` line per finding. Lists each
file it scanned on stderr.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

# The path may follow a closing quote, as in "${CLAUDE_PLUGIN_ROOT}"/hooks/run.sh.
ROOT_REF = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?\"?(/[^\s\"';|&)]+)")
# After this, a command runs relative paths from the plugin root.
CD_ROOT = re.compile(r"\bcd\s+\"?\$\{?CLAUDE_PLUGIN_ROOT\}?\"?(?=[\s;&|]|$)")

JS_SUFFIXES = {".js", ".mjs", ".cjs", ".ts"}
CODE_SUFFIXES = {".sh", ".bash", ".zsh", ".py", ".pl", ".pm", ".rb"} | JS_SUFFIXES
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}

# A script path in a hook command, such as hooks/run.sh or /tmp/x.py.
SUFFIX = "|".join(sorted(s.lstrip(".") for s in CODE_SUFFIXES))
SCRIPT_REF = re.compile(
    rf"(?:^|(?<=[\s;&|(\"'=]))([^\s;&|()\"'=]*\.(?:{SUFFIX}))(?=[\"']?(?:[\s;&|)]|$))"
)

SHELL = r"(?:ba|z|k|da)?sh(?![\w.-])"
# An interpreter that reads its program from stdin: no arguments, or a lone -.
STDIN_INTERPRETER = r"(?:python[\d.]*|node|perl|ruby)(?=\s*(?:$|-(?:\s|$)|[|;&)]))"
PY_NET_MODULES = (
    r"(?:urllib3?|requests|httpx|aiohttp|socket|ssl|http\.(?:client|server)"
    r"|ftplib|smtplib|telnetlib|xmlrpc|websockets?)\b"
)

# A PEP 723 header that lists dependencies makes uv download them. The header is
# a comment, so it is checked apart from the rules below.
INLINE_DEPS = re.compile(r"^#\s*dependencies\s*=\s*\[(?!\s*\])")

# Each rule is a pattern for one line. One set covers every language, so a
# Python import inside a shell heredoc still counts.
RULES = {
    "network-tool": re.compile(
        r"\b(curl|wget|nc|ncat|netcat|socat|telnet|ssh|scp|sftp|ftp)(?![\w-])"
    ),
    # A pipe into a shell or interpreter, by name, by path or through env.
    "pipe-to-shell": re.compile(
        rf"""
        (?<!\|)\|(?!\|)\s*
        (?:sudo\s+(?:-\S+\s+)*)?
        (?:\S*/)?(?:env\s+(?:-\S+\s+)*)?
        (?:{SHELL}|{STDIN_INTERPRETER})
        """,
        re.VERBOSE,
    ),
    "shell-from-stream": re.compile(
        rf"(?:^|[\s;&|(])(?:source|\.|{SHELL}|eval)\s+<\(|\beval\s+[\"']?(?:\$\(|`)"
    ),
    "dev-tcp": re.compile(r"/dev/(?:tcp|udp)/"),
    "package-fetch": re.compile(
        r"""
        \b(?:uvx|npx|bunx|pnpx)\b
        | \bpnpm\s+(?:dlx|add|install|i)\b
        | \bnpm\s+(?:install|i|ci|add|exec|x)\b
        | \b(?:yarn|bun)\s+(?:add|install|dlx|x)\b
        | \b(?:pip3?|uv\s+pip|pipx|gem|cargo)\s+install\b
        | \bgo\s+(?:install|get)\b | \bgo\s+run\s+\S+@
        | \b(?:pipx|uv\s+tool)\s+run\b
        | \buv\s+run\b.*\s--with\b
        | \bgit\s+(?:clone|fetch|pull)\b
        """,
        re.VERBOSE,
    ),
    "network-module": re.compile(
        rf"""
        # Python, also inside python -c '...' or after a semicolon
        (?:^|[\s;'"])(?:from\s+|import\s+(?:[\w.]+\s*,\s*)*){PY_NET_MODULES}
        | \bfrom\s+http\s+import\s+[\w\s,()]*\b(?:client|server)\b
        | \b(?:__import__|import_module)\(\s*["']{PY_NET_MODULES}
        # JavaScript
        | (?:require\(\s*|from\s+|import\(\s*)["'](?:node:)?
          (?:https?|http2|net|dgram|tls|undici|axios|node-fetch|ws)["']
        | (?:(?<![\w.$])|(?<=globalThis\.)|(?<=window\.)|(?<=self\.))fetch\s*\(
        | \bnew\s+(?:WebSocket|XMLHttpRequest|EventSource)\b
        # Perl, also loaded with perl -M
        | (?:\b(?:use|require)\s+|(?:^|\s)-M)
          (?:LWP\b|HTTP::(?:Tiny|Request)\b|IO::Socket\b|Net::|Socket\b|Mojo::UserAgent\b)
        # Ruby
        | \brequire\s*\(?\s*["'](?:net/|open-uri|socket|httparty|faraday)
        """,
        re.VERBOSE,
    ),
}


class Finding(NamedTuple):
    path: Path
    rule: str
    text: str
    line: int | None = None

    def __str__(self) -> str:
        where = self.path if self.line is None else f"{self.path}:{self.line}"
        return f"{where}: {self.rule}: {self.text}"


def main(argv: list[str]) -> int:
    root = (Path(argv[1]) if len(argv) > 1 else Path(__file__).parent.parent).resolve()
    scans = [PluginScan(root, p).run() for p in sorted((root / "plugins").glob("*/"))]
    findings = [f for s in scans for f in s.findings]
    scanned = [p for s in scans for p in s.scanned]
    for path in scanned:
        print(f"scanned {path}", file=sys.stderr)
    for finding in findings:
        print(finding)
    print(f"{len(scanned)} files, {len(findings)} findings", file=sys.stderr)
    return 1 if findings else 0


@dataclass
class PluginScan:
    """One plugin's scan: its findings, and the files it read to find them."""

    root: Path
    plugin: Path
    findings: list[Finding] = field(default_factory=list)
    scanned: list[Path] = field(default_factory=list)

    def run(self) -> "PluginScan":
        # A hook script often runs others by a path built at run time, such as
        # "$bin_dir/tool.pl". So any code file whose name a command or a scanned
        # file mentions is scanned too. Files under skills/ are left to the skill
        # scan.
        candidates = [
            f
            for f in code_files(self.plugin)
            if "skills" not in f.relative_to(self.plugin).parts
        ]
        configs = self._configs()
        queue = []
        for source, config in configs:
            for hook in find_hooks(config):
                queue += self._check_hook(source, hook)
                command = hook.get("command")
                if isinstance(command, str):
                    queue += [f for f in candidates if mentions(command, f)]

        seen = set()
        while queue:
            path = queue.pop(0)
            if path in seen:
                continue
            seen.add(path)
            text = self._read(path)
            if text is None:
                continue
            self.findings += scan_text(self._rel(path), text)
            queue += [f for f in candidates if mentions(text, f)]
        self.scanned = list(dict.fromkeys(source for source, _ in configs))
        self.scanned += sorted(self._rel(p) for p in seen)
        return self

    def _configs(self) -> list[tuple[Path, object]]:
        """The hook configs: hooks/hooks.json, plus what plugin.json declares.

        plugin.json may hold a config inline, or name config files by path.
        """
        configs = []
        default = self.plugin / "hooks" / "hooks.json"
        if default.is_file():
            configs.append((default, self._load(default)))
        manifest = self.plugin / ".claude-plugin" / "plugin.json"
        declared = self._load(manifest).get("hooks") if manifest.is_file() else None
        refs = declared if isinstance(declared, list) else [declared]
        for ref in refs:
            if ref is None:
                continue
            if isinstance(ref, dict):
                configs.append((manifest, ref))
            elif not isinstance(ref, str):
                self._flag(manifest, "bad-hook-ref", json.dumps(ref))
            elif (path := self._resolve(ref, manifest)) and path != default.resolve():
                configs.append((path, self._load(path)))
        return [(self._rel(path), config) for path, config in configs]

    def _check_hook(self, source: Path, hook: dict) -> list[Path]:
        """Check one hook. Returns the plugin files its command runs."""
        if hook.get("type") == "http" or "url" in hook:
            self._flag(source, "http-hook", str(hook.get("url")))
        command = hook.get("command")
        if not isinstance(command, str):
            return []
        self.findings += [Finding(source, r, command) for r in matching_rules(command)]
        paths = [self._resolve(ref, source) for ref in ROOT_REF.findall(command)]
        # Any other script path runs from the user's project, outside the
        # plugin, unless the command first changes to the plugin root.
        rest = ROOT_REF.sub(" ", command)
        cd_root = CD_ROOT.search(rest)
        for match in SCRIPT_REF.finditer(rest):
            ref = match.group(1)
            after_cd = cd_root and cd_root.end() <= match.start()
            if after_cd and not ref.startswith(("/", "~", "$")):
                paths.append(self._resolve(ref, source))
            else:
                self._flag(source, "outside-plugin", ref)
        return [p for p in paths if p]

    def _resolve(self, ref: str, source: Path) -> Path | None:
        """The plugin file that ref names, or None after flagging a bad ref.

        A directory is not flagged, but has nothing to scan.
        """
        rel = ref.lstrip("/")
        path = (self.plugin / rel).resolve()
        if not path.is_relative_to(self.plugin):
            self._flag(source, "outside-plugin", rel)
        elif not path.exists():
            self._flag(source, "missing-file", rel)
        elif path.is_file():
            return path
        return None

    def _load(self, path: Path) -> dict:
        """A JSON file's object, or {} after flagging a file that will not parse."""
        text = self._read(path)
        if text is None:
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            self._flag(path, "bad-json", str(error))
            return {}
        return data if isinstance(data, dict) else {}

    def _read(self, path: Path) -> str | None:
        try:
            return path.read_text()
        except (OSError, UnicodeDecodeError) as error:
            self._flag(path, "unreadable-file", type(error).__name__)
            return None

    def _flag(self, path: Path, rule: str, text: str) -> None:
        self.findings.append(Finding(self._rel(path), rule, text))

    def _rel(self, path: Path) -> Path:
        return path.relative_to(self.root) if path.is_absolute() else path


def find_hooks(node) -> list[dict]:
    """Every hook in a hook config, at any depth. A hook is an object with a type."""
    if isinstance(node, dict):
        found = [node] if "type" in node else []
        return found + [h for v in node.values() for h in find_hooks(v)]
    if isinstance(node, list):
        return [h for v in node for h in find_hooks(v)]
    return []


def code_files(plugin: Path) -> list[Path]:
    """The plugin's files that can run: a known script type, or a shebang."""
    found = []
    for path in sorted(plugin.rglob("*")):
        if not path.is_file() or SKIP_DIRS & set(path.relative_to(plugin).parts):
            continue
        if path.suffix in CODE_SUFFIXES or has_shebang(path):
            found.append(path)
    return found


def has_shebang(path: Path) -> bool:
    with path.open("rb") as file:
        return file.read(2) == b"#!"


def mentions(text: str, path: Path) -> bool:
    """Whether text names the file, or imports it as a Python or Node module."""
    if re.search(rf"(?<![\w.-]){re.escape(path.name)}(?![\w.-])", text):
        return True
    stem = re.escape(path.stem)
    if path.suffix == ".py":
        # import helper, import a, helper, from helper import x,
        # from .helper import x, from pkg.helper import x, from . import helper
        pattern = rf"""
            ^[ \t]*(?:
              import[ \t]+[\w \t,.]*\b{stem}\b
            | from[ \t]+[\w.]*\b{stem}[ \t]+import\b
            | from[ \t]+[\w.]+[ \t]+import[ \t]+[\w \t,()]*\b{stem}\b
            )"""
        return bool(re.search(pattern, text, re.MULTILINE | re.VERBOSE))
    if path.suffix in JS_SUFFIXES:
        # require("./helper"), import x from "./helper", import("./helper")
        pattern = rf"""(?:require\(|from|import\(?)\s*["'](?:[^"']*/)?{stem}["']"""
        return bool(re.search(pattern, text))
    return False


def scan_text(rel: Path, text: str) -> list[Finding]:
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        if INLINE_DEPS.search(line):
            findings.append(Finding(rel, "package-fetch", line.strip(), number))
        # A whole-line comment runs nothing. A comment after code is still read.
        if line.lstrip().startswith(("#", "//")):
            continue
        findings += [
            Finding(rel, rule, line.strip(), number) for rule in matching_rules(line)
        ]
    return findings


def matching_rules(text: str) -> list[str]:
    return [rule for rule, pattern in RULES.items() if pattern.search(text)]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
