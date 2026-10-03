#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Ask Clef one set of questions with one POST /v1/systemone and print the reply.

Stdin holds a JSON object with `state` and `questions`, in Cloudflare's shape.
Flags carry the model, images, a state file and the timeout.

Exit codes: 0 answered, 2 bad request, 3 no answer from the server, 1 any other error.
"""

import argparse
import base64
import http.client
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODELS = ("clef", "clef-flash")
DEFAULT_MODEL = "clef-flash"
DEFAULT_TIMEOUT = 120.0

DOCKER_HOST = "host.docker.internal"
DOCKER_URL = f"http://{DOCKER_HOST}:11434"
LOOPBACK_URL = "http://127.0.0.1:11434"
ENDPOINT = "/v1/systemone"
SETUP_FIXES = f"{Path(__file__).resolve().parent.parent / 'setup.md'}#fixes-for-exit-3"

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

EXIT_OK, EXIT_ERROR, EXIT_BAD_REQUEST, EXIT_NO_ANSWER = 0, 1, 2, 3


class ClefError(Exception):
    """A failure that ends the run with one stderr line and an exit code."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
        request = build_request(args, sys.stdin.read())
        url, source = resolve_url()
        sys.stdout.write(send(url, source, request, args.timeout))
        return EXIT_OK
    except ClefError as e:
        print(f"clef: {e}", file=sys.stderr)
        return e.code
    except Exception as e:  # noqa: BLE001 - one line on stderr for any other error
        print(f"clef: {type(e).__name__}: {e}", file=sys.stderr)
        return EXIT_ERROR


def build_request(args: argparse.Namespace, stdin_text: str) -> dict:
    """Return the request body from stdin and flags, after Cloudflare's checks."""
    body = _parse_stdin(stdin_text)
    if args.state_file is not None:
        if "state" in body:
            raise _bad("give the state on stdin or with --state-file, not both")
        body["state"] = _read_text(args.state_file)
    if "state" not in body:
        raise _bad("no state: put `state` on stdin or use --state-file")
    if "questions" not in body:
        raise _bad("no questions: put `questions` on stdin")
    check_questions(body["questions"])

    request = {"model": args.model, "state": body["state"], "questions": body["questions"]}
    if args.image:
        request["images"] = encode_images(args.image)
    return request


def check_questions(questions: object) -> None:
    """Check the question count and each question against Cloudflare's schema."""
    if not isinstance(questions, dict):
        raise _bad("`questions` must be an object of question id to question")
    if not MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS:
        raise _bad(f"give {MIN_QUESTIONS}–{MAX_QUESTIONS} questions, not {len(questions)}")
    for qid, question in questions.items():
        _check_question(qid, question)


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


def send(url: str, source: str, request: dict, timeout: float) -> str:
    """POST the request and return the server's JSON reply text, unchanged.

    A reply that is not JSON is an error, so a proxy's HTML page never reads as an answer.
    """
    req = urllib.request.Request(
        url + ENDPOINT,
        data=json.dumps(request).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
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
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        raise ClefError(f"HTTP 200 from {url}, but the reply is not JSON", EXIT_ERROR) from e
    return text


# ---------------------------------------------------------------------------
# Implementation details
# ---------------------------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ClefError(message, EXIT_BAD_REQUEST)


def _parse_args(argv):
    parser = _Parser(prog="clef.py", description="Ask Clef one set of questions and print the reply.")
    parser.add_argument("--model", choices=MODELS, default=DEFAULT_MODEL)
    parser.add_argument("--image", action="append", default=[], metavar="PATH")
    parser.add_argument("--state-file", metavar="PATH")
    parser.add_argument("--timeout", type=_positive_float, default=DEFAULT_TIMEOUT, metavar="N")
    return parser.parse_args(argv)


def _positive_float(text):
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be above 0: {text}")
    return value


def _parse_stdin(text):
    try:
        body = json.loads(text)
    except json.JSONDecodeError as e:
        raise _bad(f"stdin is not JSON: {e}") from e
    if not isinstance(body, dict):
        raise _bad("stdin must be a JSON object with `state` and `questions`")
    for key in body:
        if key in STDIN_KEYS:
            continue
        if key in FLAG_FOR_KEY:
            raise _bad(f"stdin key `{key}` is not allowed; use {FLAG_FOR_KEY[key]}")
        raise _bad(f"stdin key `{key}` is not allowed; stdin takes only `state` and `questions`")
    return body


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


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise _bad(f"cannot read state file {path}: {e}") from e


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
    except (json.JSONDecodeError, AttributeError):
        error = None
    if isinstance(error, dict):
        error = error.get("message")
    if not isinstance(error, str) or not error.strip():
        error = text.strip() or "no error text"
    return " ".join(error.split())


def _bad(message):
    return ClefError(message, EXIT_BAD_REQUEST)


def _no_answer(url, source, reason):
    return ClefError(
        f"no answer from {url} (URL from {source}): {reason}. See {SETUP_FIXES}",
        EXIT_NO_ANSWER,
    )


if __name__ == "__main__":
    sys.exit(main())
