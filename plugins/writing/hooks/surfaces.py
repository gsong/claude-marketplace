"""Which tools send text to a reader, and where in each payload that text sits.

Shared by send-lint.py and smart-quotes.py, so the two hooks agree on what a
Slack canvas or a Claude Doc actually says. SURFACES, at the bottom, is the one
place that maps a tool to its extractor, its voice profile, and whether a send
through it can be taken back. The extractors below it only find text. Judging
it is the caller's job.

Stdlib only: both callers run as `uv run --script` with no dependencies, and a
hook that has to resolve packages before it can answer is a hook that times out.
"""

import json
import re
import shlex
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Text:
    """One piece of outgoing prose. `label` says where it came from, so a report
    over several pieces can point at the right one."""

    label: str
    text: str
    html: bool = False


@dataclass
class Extract:
    texts: list[Text] = field(default_factory=list)
    # Names what the send lands on, for the bounce-once key. Empty on a soft
    # surface, where nothing is bounced.
    target: str = ""


@dataclass
class Surface:
    pattern: str
    profile: str
    # Hard means the send cannot be taken back once it lands.
    hard: bool
    extract: Callable[[dict, Path], Extract]


def surface_for(tool_name: str) -> Surface | None:
    for surface in SURFACES:
        if re.search(surface.pattern, tool_name):
            return surface
    return None


def published_paths(tool_input: dict, cwd: Path) -> list[Path]:
    """The local files an Artifact publish sends: `file_path` plus every source
    in `files`, resolved against `root` (else cwd). Missing files are dropped."""
    root = Path(tool_input["root"]) if tool_input.get("root") else cwd
    if not root.is_absolute():
        root = cwd / root

    sources: list[str] = []
    if tool_input.get("file_path"):
        sources.append(tool_input["file_path"])
    files = tool_input.get("files")
    if isinstance(files, dict):
        for value in files.values():
            if isinstance(value, str):
                sources.append(value)
            elif isinstance(value, dict) and value.get("from"):
                sources.append(value["from"])
    elif isinstance(files, list):
        for item in files:
            if isinstance(item, str):
                sources.append(item)
            elif isinstance(item, dict) and item.get("path"):
                sources.append(item["path"])

    paths = []
    for source in sources:
        path = Path(source).expanduser()
        if not path.is_absolute():
            path = root / path
        if path.is_file():
            paths.append(path)
    return paths


# --- extractors --------------------------------------------------------


def _slack_message(tool_input: dict, cwd: Path) -> Extract:
    target = f"{tool_input.get('channel_id') or ''}|{tool_input.get('thread_ts') or ''}"
    return Extract(_strings(("message", tool_input.get("message"))), target)


def _slack_canvas(tool_input: dict, cwd: Path) -> Extract:
    texts = _strings(("content", tool_input.get("content")))
    sections = tool_input.get("sections")
    if isinstance(sections, list):
        for index, section in enumerate(sections):
            if isinstance(section, dict) and section.get("edit_type") != "delete":
                texts += _strings((f"sections[{index}].content", section.get("content")))
    return Extract(texts)


def _gmail_draft(tool_input: dict, cwd: Path) -> Extract:
    # When both are set, `body` is the plain-text twin of `htmlBody`. Linting both
    # would report every finding twice.
    texts = _strings(("body", tool_input.get("body")))
    if not texts:
        texts = _strings(("htmlBody", tool_input.get("htmlBody")), html=True)
    return Extract(texts)


# Keys whose string values are prose the doc will show.
DOC_TEXT_KEYS = {"markdown", "text", "content", "body"}
# Keys whose values locate existing text rather than add new text. A `find`
# target quotes words already in the doc; they are not this send's to judge.
DOC_SKIP_KEYS = {"target", "ref"}


def _claude_docs(tool_input: dict, cwd: Path) -> Extract:
    texts: list[Text] = []
    payload = tool_input.get("payload")
    if isinstance(payload, str):
        # The schema allows a string payload, most likely the ops object sent
        # JSON-encoded. Read as prose, JSON's own quotes would look like text.
        try:
            decoded = json.loads(payload)
        except ValueError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            tool_input = {**tool_input, "payload": decoded}
        else:
            texts.extend(_strings(("$.payload", payload)))

    def walk(node, where: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in DOC_SKIP_KEYS:
                    continue
                if key in DOC_TEXT_KEYS and isinstance(value, str):
                    texts.extend(_strings((f"{where}.{key}", value)))
                else:
                    walk(value, f"{where}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{where}[{index}]")

    walk(tool_input, "$")
    return Extract(texts)


# A CSV or JSON upload is data. Its quotes and semicolons are syntax.
DRIVE_PROSE_TYPES = {"", "text/plain", "text/markdown", "text/x-markdown", "text/html"}


def _drive_file(tool_input: dict, cwd: Path) -> Extract:
    mime = str(tool_input.get("contentMimeType") or tool_input.get("mimeType") or "").lower()
    mime = mime.split(";")[0].strip()
    if mime not in DRIVE_PROSE_TYPES:
        return Extract()
    return Extract(_strings(("textContent", tool_input.get("textContent")), html=mime == "text/html"))


def _artifact(tool_input: dict, cwd: Path) -> Extract:
    if tool_input.get("action", "publish") != "publish" or tool_input.get("asset"):
        return Extract()
    texts = []
    for path in published_paths(tool_input, cwd):
        suffix = path.suffix.lower()
        if suffix not in {".md", ".markdown", ".html", ".htm"}:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        texts += _strings((str(path), body), html=suffix in {".html", ".htm"})
    return Extract(texts)


def _gh(tool_input: dict, cwd: Path) -> Extract:
    command = tool_input.get("command")
    if not isinstance(command, str) or "gh" not in command:
        return Extract()
    rest, heredocs = _split_heredocs(command)
    lexer = shlex.shlex(_split_lines(rest), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    tokens = list(lexer)

    texts: list[Text] = []
    target = ""
    for args in _gh_invocations(tokens):
        found = _gh_pr_issue(args, cwd) if args[0] in {"pr", "issue"} else _gh_api(args, cwd)
        if found is None:
            continue
        texts += found.texts
        target = target or found.target
    if not target:
        return Extract()

    # A heredoc feeds whichever gh call reads stdin or wraps it in $(cat ...).
    # There is almost always one gh call per command, so it gets them all.
    for index, body in enumerate(heredocs):
        texts += _json_or_raw(f"heredoc {index + 1}", body)
    return Extract(texts, target)


# --- gh parsing --------------------------------------------------------

GH_ACTIONS = {"pr": {"create", "comment", "review", "edit"}, "issue": {"create", "comment", "edit"}}
# pr and issue flags that take a value, so their value is not read as the PR number.
GH_VALUE_FLAGS = {
    "-t", "--title", "-B", "--base", "-H", "--head", "-l", "--label", "-a", "--assignee",
    "-r", "--reviewer", "-m", "--milestone", "-p", "--project", "-T", "--template",
    "--add-label", "--remove-label", "--add-assignee", "--remove-assignee",
    "--add-reviewer", "--remove-reviewer", "--add-project", "--remove-project", "--type",
}
GH_API_VALUE_FLAGS = {
    "-H", "--header", "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p", "--preview",
}
GH_API_PATH_SEGMENTS = {"comments", "reviews", "replies", "issues", "pulls"}
SHELL_OPERATORS = {"&&", "||", ";", "|", "&", "(", ")", ";;", "|&"}
COMMAND_PREFIXES = {"exec", "command", "then", "do", "else", "time", "env"}
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
REDIRECTS = {"<", ">", ">>", "2>", "&>", ">&", "2>&1"}
HEREDOC_PLACEHOLDER = "__WRITING_HEREDOC__"
HEREDOC_RE = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")


def _split_heredocs(command: str) -> tuple[str, list[str]]:
    """Pull heredoc bodies out of a command. shlex cannot parse them, and the
    body is exactly the text that is about to be sent. The operator is left as a
    placeholder so a `--body "$(cat <<EOF ...)"` value is known to be one."""
    lines = command.split("\n")
    kept, bodies = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        operators = HEREDOC_RE.findall(line)
        kept.append(HEREDOC_RE.sub(f" {HEREDOC_PLACEHOLDER} ", line))
        for dash, _, delimiter in operators:
            body = []
            while i < len(lines):
                candidate = lines[i]
                i += 1
                if (candidate.lstrip("\t") if dash else candidate) == delimiter:
                    break
                body.append(candidate)
            bodies.append("\n".join(body))
    return "\n".join(kept), bodies


def _split_lines(command: str) -> str:
    """Put a `;` after every unquoted newline. shlex reads a newline as plain
    whitespace, so `cd repo` on one line and `gh pr comment` on the next would
    lex as one command, with gh out of command position. The newline stays, so
    a `#` comment still ends where it did. A backslash continuation is left
    alone, and so is a newline inside quotes."""
    out, quote, i = [], "", 0
    while i < len(command):
        char = command[i]
        if char == "\\" and quote != "'":
            out.append(command[i : i + 2])
            i += 2
            continue
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "#" and (i == 0 or command[i - 1] in " \t\n;&|()"):
            # A comment may hold an apostrophe. It is not a quote.
            stop = command.find("\n", i)
            stop = len(command) if stop < 0 else stop
            out.append(command[i:stop])
            i = stop
            continue
        elif char == "\n":
            char = "\n; "
        out.append(char)
        i += 1
    return "".join(out)


def _gh_invocations(tokens: list[str]) -> list[list[str]]:
    """Every `gh ...` call in the token stream, cut at the next shell operator."""
    calls = []
    for index, token in enumerate(tokens):
        if token != "gh" and not token.endswith("/gh"):
            continue
        # `gh` must be in command position, so `grep gh pr` is not a send.
        before = tokens[index - 1] if index else ";"
        if before not in SHELL_OPERATORS | COMMAND_PREFIXES and not ASSIGNMENT_RE.match(before):
            continue
        args = []
        rest = iter(tokens[index + 1 :])
        for arg in rest:
            if arg in SHELL_OPERATORS:
                break
            # A redirect and its file are the shell's, not gh's.
            if arg in REDIRECTS:
                next(rest, None)
                continue
            if arg != HEREDOC_PLACEHOLDER:
                args.append(arg)
        if args and args[0] in {"pr", "issue", "api"}:
            calls.append(args)
    return calls


def _gh_pr_issue(args: list[str], cwd: Path) -> Extract | None:
    noun = args[0]
    if len(args) < 2 or args[1] not in GH_ACTIONS[noun]:
        return None
    texts: list[Text] = []
    repo, number = "", ""
    i = 2
    while i < len(args):
        arg = args[i]
        name, eq, inline = arg.partition("=") if arg.startswith("--") else (arg, "", "")
        value = inline if eq else (args[i + 1] if i + 1 < len(args) else "")
        step = 1 if eq else 2
        if name in {"-b", "--body"}:
            texts += _inline_body("--body", value)
            i += step
        elif name in {"-F", "--body-file"}:
            texts += _file_body(f"--body-file {value}", value, cwd)
            i += step
        elif name in {"-R", "--repo"}:
            repo = value
            i += step
        elif name in GH_VALUE_FLAGS:
            i += step
        elif arg.startswith("-"):
            i += 1
        else:
            number = number or _pr_number(arg)
            i += 1
    parts = ["gh", noun, args[1], repo, f"#{number}" if number else ""]
    return Extract(texts, " ".join(p for p in parts if p))


def _gh_api(args: list[str], cwd: Path) -> Extract | None:
    texts: list[Text] = []
    method, path = "", ""
    has_body = has_input = False
    i = 1
    while i < len(args):
        arg = args[i]
        name, eq, inline = arg.partition("=") if arg.startswith("--") else (arg, "", "")
        if not eq and name.startswith("-X") and len(name) > 2:
            name, eq, inline = "-X", "=", name[2:]
        value = inline if eq else (args[i + 1] if i + 1 < len(args) else "")
        step = 1 if eq else 2
        if name in {"-X", "--method"}:
            method = value.upper()
        elif name in {"-f", "--raw-field", "-F", "--field"}:
            key, _, field_value = value.partition("=")
            if key == "body" or key.endswith("[body]"):
                has_body = True
                typed = name in {"-F", "--field"}
                if typed and field_value.startswith("@"):
                    texts += _file_body(f"{key}=@", field_value[1:], cwd)
                else:
                    texts += _inline_body(f"{key}=", field_value)
        elif name == "--input":
            has_input = True
            if value != "-":
                texts += _json_file_bodies(f"--input {value}", value, cwd)
        elif name in GH_API_VALUE_FLAGS:
            pass
        elif arg.startswith("-"):
            step = 1
        else:
            path = path or arg
            step = 1
        i += step

    endpoint = path.split("?")[0].strip("/")
    if not GH_API_PATH_SEGMENTS & set(endpoint.split("/")):
        return None
    if method in {"GET", "DELETE", "HEAD"}:
        return None
    if method not in {"POST", "PATCH", "PUT"} and not has_body and not has_input:
        return None
    return Extract(texts, f"gh api {endpoint}")


def _pr_number(arg: str) -> str:
    match = re.search(r"/(?:pull|pulls|issues)/(\d+)", arg)
    if match:
        return match.group(1)
    return arg.lstrip("#")


def _inline_body(label: str, value: str) -> list[Text]:
    # `--body "$(cat <<EOF ...)"` carries a heredoc, which is read on its own.
    # Any other substitution is text the shell has not produced yet.
    if HEREDOC_PLACEHOLDER in value or value.lstrip().startswith("$("):
        return []
    return _strings((label, value))


def _file_body(label: str, value: str, cwd: Path) -> list[Text]:
    body = _read(value, cwd)
    return _strings((label, body)) if body is not None else []


def _json_file_bodies(label: str, value: str, cwd: Path) -> list[Text]:
    body = _read(value, cwd)
    if body is None:
        return []
    try:
        data = json.loads(body)
    except ValueError:
        return []
    return _body_strings(label, data)


def _json_or_raw(label: str, body: str) -> list[Text]:
    try:
        data = json.loads(body)
    except ValueError:
        return _strings((label, body))
    if isinstance(data, (dict, list)):
        return _body_strings(label, data)
    return _strings((label, body))


def _body_strings(label: str, data) -> list[Text]:
    """Every string under a key named `body`, at any depth. A review payload
    keeps its inline comments in `comments[].body`."""
    texts: list[Text] = []

    def walk(node, where: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "body" and isinstance(value, str):
                    texts.extend(_strings((f"{label} {where}.body", value)))
                else:
                    walk(value, f"{where}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{where}[{index}]")

    walk(data, "$")
    return texts


def _read(value: str, cwd: Path) -> str | None:
    if not value or value == "-":
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = cwd / path
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _strings(*pairs: tuple[str, object], html: bool = False) -> list[Text]:
    return [Text(label, value, html) for label, value in pairs if isinstance(value, str) and value.strip()]


# --- the table ---------------------------------------------------------
# Matched against tool_name with re.search, first hit wins. hooks.json decides
# which tools reach the hooks at all; this decides what each one says. A new
# row also needs both hooks.json matchers, the README hook table, and a sample
# tool name in tests/surfaces.test.mjs, which checks the matchers against it.

SURFACES = [
    Surface(r"__slack_(send_message|schedule_message)$", "comms", True, _slack_message),
    Surface(r"__slack_send_message_draft$", "comms", False, _slack_message),
    Surface(r"__slack_(create|update)_canvas$", "technical", False, _slack_canvas),
    Surface(r"Gmail__create_draft$", "comms", False, _gmail_draft),
    Surface(r"Claude_Docs__(create|batch|update)$", "technical", False, _claude_docs),
    Surface(r"Google_Drive__create_file$", "technical", False, _drive_file),
    Surface(r"^Artifact$", "technical", False, _artifact),
    Surface(r"^Bash$", "technical", True, _gh),
]
