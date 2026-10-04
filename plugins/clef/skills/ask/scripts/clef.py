#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Ask Clef questions with POST /v1/systemone and print the reply.

Stdin holds a JSON object with `state` and `questions`, in Cloudflare's shape.
Flags carry the model, images, a state file, the timeout and the caller's guess.
`--batch` makes one call per line of a JSONL file instead. `--ids` or `--lines` picks some of those lines.
When CLEF_LOG names a file, each call appends one JSON line to it, answered or failed.
A --batch line is one call.

Exit codes: 0 answered, 2 bad request, 3 no answer from the server, 1 any other error.
A --batch run that reaches its last line exits 0, even when some lines failed.
"""

import argparse
import base64
import http.client
import json
import math
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeGuard

MODELS = ("clef", "clef-flash")
DEFAULT_MODEL = "clef-flash"
DEFAULT_TIMEOUT = 120.0
MAX_TIMEOUT = 86400.0  # one day

DOCKER_HOST = "host.docker.internal"
DOCKER_URL = f"http://{DOCKER_HOST}:11434"
LOOPBACK_URL = "http://127.0.0.1:11434"
ENDPOINT = "/v1/systemone"
SETUP_FIXES = f"{Path(__file__).resolve().parent.parent / 'setup.md'}#fixes-for-exit-3"
PLUGIN_JSON = Path(__file__).resolve().parents[3] / ".claude-plugin" / "plugin.json"

MIN_QUESTIONS, MAX_QUESTIONS = 1, 64
QUESTION_ID = re.compile(r"[A-Za-z0-9_.-]{1,100}")
MIN_OPTIONS, MAX_OPTIONS = 2, 255
MIN_LEVELS, MAX_LEVELS = 2, 10
MAX_IMAGES = 4
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 8 * 1024 * 1024

STDIN_KEYS = {"state", "questions"}
# Stdin keys that a flag carries instead.
FLAG_FOR_KEY = {
    "model": "--model",
    "images": "--image",
    "image": "--image",
    "timeout": "--timeout",
    "state_file": "--state-file",
}
LINE_KEYS = {"state", "questions", "id", "images", "guess"}
# Flags that --batch refuses, and the line key that carries each instead.
LINE_KEY_FOR_FLAG = {"image": "images", "state_file": "state", "guess": "guess"}
# Keys that a batch result line sets itself. A reply's own value for one never reaches the line.
RESULT_KEYS = {"id", "line", "error", "exit"}
# Every CLEF_LOG record holds each key. A field the call never built is null.
RECORD_KEYS = (
    "time", "cwd", "session", "version", "model", "state", "state_chars", "images", "questions",
    "answers", "guess", "agree", "usage", "latency_s", "error", "exit",
)

EXIT_OK, EXIT_ERROR, EXIT_BAD_REQUEST, EXIT_NO_ANSWER = 0, 1, 2, 3

# The server is always local or on the Docker host, so no request goes through a proxy.
# An empty ProxyHandler drops the proxies that urllib reads from the environment and from macOS.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class ClefError(Exception):
    """A failure that ends the run with one stderr line and an exit code."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def main(argv: list[str] | None = None) -> int:
    """Run the call or batch. A failure prints one stderr line and logs the call it stopped."""
    log = _Log.from_env()
    log.start()  # A record for the flags, so a bad flag is logged. Each call then starts its own.
    try:
        args = _parse_args(argv)
        return run_batch(args, log) if args.batch is not None else run_one(args, log)
    except ClefError as e:
        message, code = f"clef: {e}", e.code
    except Exception as e:  # noqa: BLE001 - one line on stderr for any other error
        message, code = f"clef: {type(e).__name__}: {e}", EXIT_ERROR
    message = _one_line(message)
    print(message, file=sys.stderr)
    log.finish(message, code)
    return code


def run_one(args: argparse.Namespace, log: "_Log") -> int:
    """Ask one set of questions from stdin, print the server's reply unchanged, and log it.

    Each step notes what it read in the log's record, so a failure logs it too.
    """
    record = log.start()
    body = _load_object(sys.stdin.read(), "stdin")
    _note_input(record, args.model, body, args.image)
    record["guess"] = guess = _parse_guess(args.guess)
    body = read_body(args, body)
    # A --state-file state joins the body only now, so note the input a second time.
    _note_input(record, args.model, body, args.image)
    request = build_request(args.model, body, args.image)
    check_guess(guess, request["questions"])
    url, source = resolve_url()
    text, reply, latency = _timed_send(url, source, request, args.timeout)
    _note_reply(record, request, guess, reply, latency)
    sys.stdout.write(text)
    log.finish()
    return EXIT_OK


def run_batch(args: argparse.Namespace, log: "_Log") -> int:
    """Make one call per line of the --batch file and write one result line for each.

    Each line is one call with its own log record.
    A bad line, from a local check or a 4xx, gets an error line and the run goes on.
    Any other failure stops the run with that failure's exit code.
    A run that reaches its last line exits 0, even with bad lines.
    Claude Code shows a failed command's output only as an excerpt. A nonzero exit would hide answer lines.
    """
    for flag, key in LINE_KEY_FOR_FLAG.items():
        if getattr(args, flag) not in (None, []):
            name = "--" + flag.replace("_", "-")
            raise _bad(f"--batch and {name} do not mix; give each line its own `{key}`")
    text = _read_text(args.batch, "batch file")
    lines = list(_batch_lines(text))
    chosen = None
    if args.ids is not None:
        chosen = choose_lines(lines, args.ids.split())
    elif args.lines is not None:
        chosen = choose_line_numbers(text, args.lines.split())
    out = _open_out(args.out) if args.out else sys.stdout
    url, source = resolve_url()
    answered = failed = 0
    try:
        for number, line in lines:
            if chosen is not None and number not in chosen:
                continue
            ref = {"line": number}
            record = log.start()
            try:
                item = _load_object(line, "line")
                _note_input(record, args.model, item, item.get("images", []))
                record["guess"] = guess = item.get("guess", {})
                ref = _line_ref(item, number)
                _check_line(item)
                request = _make_request(args.model, item, item.get("images", []))
                check_guess(guess, request["questions"])
                _, reply, latency = _timed_send(url, source, request, args.timeout)
            except ClefError as e:
                if e.code != EXIT_BAD_REQUEST:
                    raise
                failed += 1
                message = _one_line(f"clef: {e}")
                _emit(out, {**ref, "error": message, "exit": e.code})
                log.finish(message, e.code)
                continue
            answered += 1
            _note_reply(record, request, guess, reply, latency)
            _emit(out, {**{k: v for k, v in reply.items() if k not in RESULT_KEYS}, **ref})
            log.finish()
    finally:
        if out is not sys.stdout:
            out.close()

    summary = f"{answered} answered, {failed} failed"
    if args.out:
        print(f"{summary} -> {args.out}")
    else:
        print(f"clef: {summary}", file=sys.stderr)
    return EXIT_OK


def choose_lines(lines: list[tuple[int, str]], ids: list[str]) -> set[int]:
    """Return the numbers of the batch lines that --ids names.

    A line matches by its `id`, read as a string. A line with no `id`, or a bad one, matches by its line number.
    That is the value its result line reports. A listed value that matches no line is a bad request.
    """
    if not ids:
        raise _bad("--ids lists no ids")
    wanted, chosen, found = set(ids), set(), set()
    for number, line in lines:
        key = _ids_key(line, number)
        if key in wanted:
            chosen.add(number)
            found.add(key)
    missing = [value for value in dict.fromkeys(ids) if value not in found]
    if missing:
        raise _bad(f"--ids {' '.join(missing)}: no batch line has that id or line number")
    return chosen


def choose_line_numbers(text: str, values: list[str]) -> set[int]:
    """Return the line numbers that --lines names, whether or not those lines have an `id`.

    A listed blank line runs nothing. A value that is not a line number of the file is a bad request.
    """
    if not values:
        raise _bad("--lines lists no line numbers")
    bad = [value for value in dict.fromkeys(values) if not re.fullmatch(r"[1-9][0-9]*", value)]
    if bad:
        raise _bad(f"--lines {' '.join(bad)}: not a line number")
    # The count that `grep -c ''` gives for `\n` or `\r\n` endings: a last line with no newline counts too.
    count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    # A value with more digits than the count is past the last line. Checking that first keeps
    # int() off a value over Python's integer digit limit.
    over = [
        value for value in dict.fromkeys(values) if len(value) > len(str(count)) or int(value) > count
    ]
    if over:
        raise _bad(f"--lines {' '.join(over)}: the batch file has {count} lines")
    return {int(value) for value in values}


def read_body(args: argparse.Namespace, body: dict) -> dict:
    """Check the stdin object's keys. Return it with the --state-file text as its `state` when that flag is given."""
    _check_stdin_keys(body)
    if args.state_file is not None:
        if "state" in body:
            raise _bad("give the state on stdin or with --state-file, not both")
        body["state"] = _read_text(args.state_file, "state file")
    return body


def build_request(model: str, body: dict, image_paths: list[str]) -> dict:
    """Return the request body from the checked stdin object and the flags, after Cloudflare's checks."""
    if "state" not in body:
        raise _bad("no state: put `state` on stdin or use --state-file")
    if "questions" not in body:
        raise _bad("no questions: put `questions` on stdin")
    return _make_request(model, body, image_paths)


def check_questions(questions: object) -> None:
    """Check the question count and each question against Cloudflare's schema."""
    if not isinstance(questions, dict):
        raise _bad("`questions` must be an object of question id to question")
    if not MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS:
        raise _bad(f"give {MIN_QUESTIONS}–{MAX_QUESTIONS} questions, not {len(questions)}")
    for qid, question in questions.items():
        _check_question(qid, question)


def check_guess(guess: object, questions: dict) -> None:
    """Check the caller's own answers against the questions they name."""
    if not isinstance(guess, dict):
        raise _bad("guess must be an object of question id to answer")
    for qid, value in guess.items():
        question = questions.get(qid)
        if question is None:
            raise _bad(f"guess {qid}: no such question")
        kind, criteria = question["type"], question.get("criteria")
        if kind == "noul" and not isinstance(value, bool):
            raise _bad(f"guess {qid}: give true or false for a noul question")
        if kind == "choice" and not (isinstance(value, str) and value in criteria):
            raise _bad(f"guess {qid}: give one of the question's option ids")
        if kind == "score" and not (_is_int(value) and 0 <= value < len(criteria)):
            raise _bad(f"guess {qid}: give a level index from 0 to {len(criteria) - 1}")


def encode_images(paths: list[str]) -> list[str]:
    """Return each image as raw base64, after the count, type and size checks."""
    if len(paths) > MAX_IMAGES:
        raise _bad(f"give at most {MAX_IMAGES} images, not {len(paths)}")
    encoded, total = [], 0
    for path in paths:
        data = _read_bytes(path)
        if _image_type(data) is None:
            raise _bad(f"image {path}: not PNG, JPEG or WebP")
        if len(data) > MAX_IMAGE_BYTES:
            raise _bad(f"image {path}: {len(data)} bytes, over the 4 MiB limit")
        total += len(data)
        encoded.append(base64.b64encode(data).decode("ascii"))
    if total > MAX_TOTAL_IMAGE_BYTES:
        raise _bad(f"images total {total} bytes, over the 8 MiB limit")
    return encoded


def resolve_url() -> tuple[str, str]:
    """Return the server URL and where it came from. The first that applies wins."""
    env = os.environ.get("CLEF_URL", "").strip()
    if env:
        return env.rstrip("/"), "CLEF_URL"
    try:
        socket.getaddrinfo(DOCKER_HOST, None)
    except OSError:
        return LOOPBACK_URL, "default"
    return DOCKER_URL, f"{DOCKER_HOST} resolves"


def send(url: str, source: str, request: dict, timeout: float) -> tuple[str, dict]:
    """POST the request and return the server's reply text, unchanged, and its JSON.

    A reply cut short, or bytes that are not HTTP, is no answer, like a refused connection.
    A reply that is not a JSON object with an `answers` object is an error,
    so a proxy's HTML page or a 200 error body never reads as an answer.
    A reply holding NaN or Infinity is not JSON, as _load_json reads it.
    """
    req = urllib.request.Request(
        url + ENDPOINT,
        data=json.dumps(request).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        message = f"HTTP {e.code}: {_error_text(_read_error_body(e))}"
        if e.code == 404:
            raise _no_answer(url, source, message) from e
        if 400 <= e.code < 500:
            raise ClefError(message, EXIT_BAD_REQUEST) from e
        raise ClefError(message, EXIT_ERROR) from e
    except OSError as e:  # URLError and TimeoutError included
        reason = e.reason if isinstance(e, urllib.error.URLError) else e
        if isinstance(reason, TimeoutError):
            raise _no_answer(url, source, f"no reply within {timeout:g}s") from e
        raise _no_answer(url, source, f"unreachable: {reason}") from e
    except http.client.IncompleteRead as e:
        raise _no_answer(url, source, f"broken reply: it stopped after {len(e.partial)} bytes") from e
    except http.client.HTTPException as e:  # BadStatusLine included
        raise _no_answer(url, source, f"broken reply: {type(e).__name__}: {_one_line(str(e))}") from e
    try:
        text = raw.decode("utf-8")
        reply = _load_json(text)
    except ValueError as e:  # UnicodeDecodeError, JSONDecodeError, a non-finite number, or an over-long integer
        raise ClefError(f"HTTP 200 from {url}, but the reply is not JSON", EXIT_ERROR) from e
    if not isinstance(reply, dict):
        raise ClefError(f"HTTP 200 from {url}, but the reply is not a JSON object", EXIT_ERROR)
    if not isinstance(reply.get("answers"), dict):
        raise ClefError(f"HTTP 200 from {url}, but the reply holds no answers", EXIT_ERROR)
    return text, reply


# ---------------------------------------------------------------------------
# Implementation details
# ---------------------------------------------------------------------------


class _Log:
    """Appends one JSON line per call to the CLEF_LOG file, and warns once if it cannot.

    `record` is the call in progress. Each step of the call fills in its fields,
    so a failed call logs every field it built before the failure.
    """

    def __init__(self, path):
        self.path, self.warned, self.record = path, False, None
        self._session = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip() or None
        self._version = _plugin_version() if path is not None else None

    @classmethod
    def from_env(cls):
        path = os.environ.get("CLEF_LOG", "").strip()
        return cls(os.path.expanduser(path) if path else None)

    def start(self):
        """Begin a new call's record, with every field null, and return it."""
        self.record = dict.fromkeys(RECORD_KEYS)
        return self.record

    def finish(self, error=None, code=None):
        """Log the call in progress once, with a failure's stderr line and exit code."""
        record, self.record = self.record, None
        if record is None or self.path is None:
            return
        self.write({
            **record,
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cwd": _cwd(),
            "session": self._session,
            "version": self._version,
            "error": error,
            "exit": code,
        })

    def write(self, record):
        # ASCII escapes, so a lone surrogate from a JSON escape cannot fail the encode.
        line = (json.dumps(record) + "\n").encode("ascii")
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line)
            finally:
                os.close(fd)
        except FileNotFoundError:
            self._warn(f"the CLEF_LOG folder {Path(self.path).parent} is missing, so no call is logged")
        except OSError as e:
            self._warn(f"cannot write CLEF_LOG {self.path} ({e.strerror}), so no call is logged")

    def _warn(self, message):
        if not self.warned:
            print(f"clef: warning: {message}", file=sys.stderr)
            self.warned = True


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ClefError(message, EXIT_BAD_REQUEST)


_EPILOG = """\
A guess is true or false for a noul question, an option id for choice,
or a level index for score. It changes nothing in the request.

A --batch line holds `state` and `questions`, and may hold `id` (string or
number), `images` (up to 4 paths) and `guess`. Each result line carries the
line's `id`, or "line": N. A bad line gets an error line with "exit": 2, and
the run goes on. Exit 3 or 1 stops the run.

A batch run that reaches its last line exits 0, even when some lines failed.
Find the failed lines by their `error` key. The stderr summary, or the --out
line, gives the counts: "N answered, M failed". A batch refused before any
line runs exits 2 and prints no result lines.

--ids 'A B 7' runs only the batch lines whose `id` is listed, or, for a
line with no `id` or a bad one, whose line number is. Other lines get no
result line.
A listed value that matches no line exits 2 before any call.

--lines '1 2 3' runs only the batch lines with these line numbers, whether
or not they have an `id`. It does not mix with --ids. A listed blank line
runs nothing. A value past the last line exits 2 before any call.

When CLEF_LOG names a file, each call appends one JSON line to it, answered
or failed. A --batch line is one call. A failed call's line holds its stderr
line in `error` and its exit code in `exit`, and null for each field it never
built. Each line also holds `session`, from CLAUDE_CODE_SESSION_ID, and the
plugin's `version`.

Exit codes: 0 answered, 2 bad request, 3 no answer from the server, 1 any other error.
"""


def _parse_args(argv):
    parser = _Parser(
        prog="clef.py",
        description="Ask Clef a set of questions from stdin and print the reply.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", choices=MODELS, default=DEFAULT_MODEL, help="default: clef-flash")
    parser.add_argument("--image", action="append", default=[], metavar="PATH", help="repeat for up to 4 images")
    parser.add_argument("--state-file", metavar="PATH", help="read the state from this file")
    parser.add_argument(
        "--timeout", type=_timeout_seconds, default=DEFAULT_TIMEOUT, metavar="N",
        help="seconds to wait for each reply (default: 120, at most 86400)",
    )
    parser.add_argument("--guess", metavar="JSON", help='your own answers, for the log: {"<question id>": <answer>}')
    parser.add_argument("--batch", metavar="IN.jsonl", help="make one call per line of this file")
    parser.add_argument("--out", metavar="OUT.jsonl", help="with --batch, write results here, not to stdout")
    parser.add_argument("--ids", metavar="'ID ...'", help="with --batch, run only the lines with these ids or line numbers")
    parser.add_argument("--lines", metavar="'N ...'", help="with --batch, run only the lines with these line numbers")
    args = parser.parse_args(argv)
    for flag in ("out", "ids", "lines"):
        if getattr(args, flag) is not None and args.batch is None:
            parser.error(f"--{flag} needs --batch")
    if args.ids is not None and args.lines is not None:
        parser.error("--ids and --lines do not mix")
    return args


def _timeout_seconds(text):
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text}") from None
    # float() takes "nan", which fails every comparison below.
    if math.isnan(value):
        raise argparse.ArgumentTypeError(f"not a number: {text}")
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be above 0: {text}")
    # A socket refuses a timeout much past 1e9 seconds, and Infinity, at send time.
    if value > MAX_TIMEOUT:
        raise argparse.ArgumentTypeError(f"must be at most {MAX_TIMEOUT:g}: {text}")
    return value


def _check_stdin_keys(body):
    for key in body:
        if key in STDIN_KEYS:
            continue
        if key in FLAG_FOR_KEY:
            raise _bad(f"stdin key `{key}` is not allowed; use {FLAG_FOR_KEY[key]}")
        raise _bad(f"stdin key `{key}` is not allowed; stdin takes only `state` and `questions`")


def _parse_guess(text):
    if text is None:
        return {}
    try:
        return _load_json(text)
    except ValueError as e:  # JSONDecodeError, a non-finite number, or an integer over Python's digit limit
        raise _bad(f"--guess is not JSON: {e}") from e


def _load_object(text, where):
    """Parse stdin or a batch line, which must be a JSON object."""
    try:
        value = _load_json(text)
    except ValueError as e:  # JSONDecodeError, a non-finite number, or an integer over Python's digit limit
        raise _bad(f"{where} is not JSON: {e}") from e
    if not isinstance(value, dict):
        raise _bad(f"{where} must be a JSON object with `state` and `questions`")
    return value


def _line_ref(item, number):
    """Return what a result line carries to name its input: the line's `id`, or its line number."""
    if "id" not in item:
        return {"line": number}
    value = item["id"]
    if not (isinstance(value, (str, float)) or _is_int(value)):
        raise _bad("`id` must be a string or number")
    return {"id": value}


def _batch_lines(text):
    """Yield the number and text of each batch line that is not blank."""
    for number, line in enumerate(text.split("\n"), 1):
        if line.strip():
            yield number, line


def _ids_key(line, number):
    """Return the value that --ids matches for a batch line: its `id` as a string, or its line number."""
    try:
        ref = _line_ref(_load_object(line, "line"), number)
    except ClefError:
        ref = {"line": number}
    return str(ref.get("id", number))


def _check_line(item):
    for key in item:
        if key not in LINE_KEYS:
            raise _bad(f"line key `{key}` is not allowed; a line takes only state, questions, id, images and guess")
    for key in ("state", "questions"):
        if key not in item:
            raise _bad(f"line has no `{key}`")
    images = item.get("images", [])
    if not isinstance(images, list) or not all(isinstance(path, str) for path in images):
        raise _bad("`images` must be a list of paths")


def _make_request(model, body, image_paths):
    check_questions(body["questions"])
    request = {"model": model, "state": body["state"], "questions": body["questions"]}
    if image_paths:
        request["images"] = encode_images(image_paths)
    return request


def _timed_send(url, source, request, timeout):
    """Send the request. Return the reply text, its JSON and the seconds it took."""
    start = time.monotonic()
    text, reply = send(url, source, request, timeout)
    return text, reply, time.monotonic() - start


def _load_json(text):
    """Parse JSON, refusing NaN and Infinity, so nothing clef.py prints, logs or sends holds one.

    json.loads takes them, and json.dumps writes them back out as invalid JSON.
    """
    return json.loads(text, parse_constant=_refuse_constant, parse_float=_finite_float)


def _refuse_constant(name):
    raise ValueError(f"{name} is not a JSON number")


def _finite_float(text):
    """Parse a float. `1e400` parses to Infinity, so it is refused too."""
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"{text} is out of a float's range")
    return value


def _open_out(path):
    try:
        return open(path, "w", encoding="utf-8")
    except OSError as e:
        raise _bad(f"cannot write --out file {path}: {e}") from e


def _emit(out, record):
    out.write(json.dumps(record) + "\n")
    out.flush()


def _note_input(record, model, body, image_paths):
    """Note a call's input in its log record, before any check of it. A missing key stays null."""
    state = body.get("state")
    record.update(
        model=model,
        state=state,
        state_chars=None if state is None else _state_chars(state),
        images=list(image_paths) if isinstance(image_paths, list) else image_paths,
        questions=body.get("questions"),
    )


def _note_reply(record, request, guess, reply, latency):
    answers = reply.get("answers")
    record.update(
        answers=answers,
        agree=_agreement(guess, request["questions"], answers),
        usage=reply.get("usage"),
        latency_s=round(latency, 3),
    )


def _state_chars(state):
    return len(state) if isinstance(state, str) else len(json.dumps(state, ensure_ascii=False))


def _cwd():
    """Return the working folder, or None when it was deleted, so logging cannot fail the run."""
    try:
        return os.getcwd()
    except OSError:
        return None


def _plugin_version():
    """Return the plugin's version from plugin.json, or None when it cannot be read."""
    try:
        version = json.loads(PLUGIN_JSON.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError, AttributeError):  # unreadable, not JSON, or not an object
        return None
    return version if isinstance(version, str) else None


def _agreement(guess, questions, answers):
    """Return, per guessed question, whether Clef's answer agrees. None when it cannot tell."""
    answers = answers if isinstance(answers, dict) else {}
    return {qid: _agrees(questions[qid]["type"], value, answers.get(qid)) for qid, value in guess.items()}


def _agrees(kind, guess, answer):
    value = answer.get(kind) if isinstance(answer, dict) else None
    if kind == "choice":
        return value == guess if isinstance(value, str) else None
    # An int skips math.isfinite and the + 0.5, which overflow past a float's range.
    if not (_is_int(value) or isinstance(value, float) and math.isfinite(value)):
        return None
    if kind == "noul":
        return None if value == 0.5 else (value > 0.5) == guess
    return (value if _is_int(value) else math.floor(value + 0.5)) == guess


def _is_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_question(qid, question):
    if not QUESTION_ID.fullmatch(qid):
        raise _bad(f"question id {qid!r}: use 1–100 letters, digits, '_', '.' or '-'")
    if not isinstance(question, dict):
        raise _bad(f"question {qid}: must be an object")
    kind = question.get("type")
    if kind not in ("noul", "choice", "score"):
        raise _bad(f"question {qid}: type must be noul, choice or score, not {kind!r}")
    if not _has_instructions(question.get("instructions")):
        raise _bad(f"question {qid}: needs non-empty `instructions`")

    criteria = question.get("criteria")
    if kind == "noul":
        if criteria is not None and not isinstance(criteria, dict):
            raise _bad(f"question {qid}: noul `criteria` must be an object")
        if criteria and not set(criteria) <= {"true", "false"}:
            raise _bad(f"question {qid}: noul `criteria` takes only `true` and `false`")
    elif kind == "choice":
        if not isinstance(criteria, dict):
            raise _bad(f"question {qid}: choice `criteria` must be an object of option id to description")
        if not MIN_OPTIONS <= len(criteria) <= MAX_OPTIONS:
            raise _bad(f"question {qid}: give {MIN_OPTIONS}–{MAX_OPTIONS} options, not {len(criteria)}")
        if "" in criteria:
            raise _bad(f"question {qid}: option ids must be non-empty")
    else:
        if not isinstance(criteria, list):
            raise _bad(f"question {qid}: score `criteria` must be a list of levels, lowest first")
        if not MIN_LEVELS <= len(criteria) <= MAX_LEVELS:
            raise _bad(f"question {qid}: give {MIN_LEVELS}–{MAX_LEVELS} levels, not {len(criteria)}")


def _has_instructions(value):
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, (dict, list)) and bool(value)


def _image_type(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _read_text(path, what):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise _bad(f"cannot read {what} {path}: {e}") from e


def _read_bytes(path):
    try:
        return Path(path).read_bytes()
    except OSError as e:
        raise _bad(f"cannot read image {path}: {e}") from e


def _read_error_body(error):
    """Return the error reply's body, or nothing when the read fails."""
    try:
        return error.read()
    except (OSError, http.client.HTTPException):
        return b""


def _error_text(raw):
    """Reduce Ollama's and the vendor's error bodies to one line."""
    text = raw.decode("utf-8", errors="replace")
    try:
        error = json.loads(text).get("error")
    except (ValueError, AttributeError):  # JSONDecodeError, or an integer over Python's digit limit
        error = None
    if isinstance(error, dict):
        error = error.get("message")
    if not isinstance(error, str) or not error.strip():
        error = text.strip() or "no error text"
    return _one_line(error)


def _one_line(text):
    """Collapse each run of whitespace to one space, so an exception's text cannot span stderr lines."""
    return " ".join(text.split())


def _bad(message):
    return ClefError(message, EXIT_BAD_REQUEST)


def _no_answer(url, source, reason):
    return ClefError(
        f"no answer from {url} (URL from {source}): {reason}. See {SETUP_FIXES}",
        EXIT_NO_ANSWER,
    )


if __name__ == "__main__":
    sys.exit(main())
