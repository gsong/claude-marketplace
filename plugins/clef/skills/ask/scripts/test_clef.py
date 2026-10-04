#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8.0"]
# ///
"""Tests for clef.py — request checks, exit codes, error shapes, the server URL order,
batch mode, `--guess` and the decision log."""

import base64
import importlib.util
import io
import json
import math
import os
import socket
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("clef", Path(__file__).parent / "clef.py")
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

main = _mod.main
resolve_url = _mod.resolve_url

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 16
MIB = 1024 * 1024
# More digits than json.loads takes (4,300 by default), so it raises a plain ValueError.
OVER_LONG_INT = "1" * 5000

ANSWER = {
    "model": "clef-flash",
    "answers": {"blue": {"type": "noul", "noul": 0.98}},
    "usage": {"input_tokens": 148, "output_tokens": 0},
}


def _noul(**overrides):
    base = {"type": "noul", "instructions": "Is the sky blue?"}
    base.update(overrides)
    return base


def _body(**overrides):
    base = {"state": "The sky is blue.", "questions": {"blue": _noul()}}
    base.update(overrides)
    return base


class Stub:
    """A local HTTP server that records each request and sends a set reply."""

    def __init__(self):
        self.status, self.reply, self.delay = 200, json.dumps(ANSWER), 0.0
        self.extra_length, self.drop = 0, False
        self.queue = []
        self.requests = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                stub.requests.append((self.path, json.loads(self.rfile.read(length))))
                time.sleep(stub.delay)
                if stub.drop:
                    return
                status, reply = stub.queue.pop(0) if stub.queue else (stub.status, stub.reply)
                payload = reply if isinstance(reply, bytes) else reply.encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload) + stub.extra_length))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # Join handler threads on close, so a delayed reply cannot write into a later test.
        self.server.daemon_threads = False
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def respond(self, status, reply, delay=0.0, extra_length=0, drop=False):
        """Set the reply. `extra_length` overstates Content-Length; `drop` closes with no reply."""
        self.status, self.delay, self.extra_length, self.drop = status, delay, extra_length, drop
        self.reply = reply if isinstance(reply, (str, bytes)) else json.dumps(reply)

    def respond_each(self, *replies):
        """Send these (status, reply) pairs in order, one per request, then the set reply."""
        self.queue = [(status, r if isinstance(r, str) else json.dumps(r)) for status, r in replies]

    @property
    def sent(self):
        """The body of the only request the stub received."""
        assert len(self.requests) == 1
        return self.requests[0][1]


@pytest.fixture(autouse=True)
def no_log(monkeypatch):
    """Keep a developer's own CLEF_LOG out of the tests."""
    monkeypatch.delenv("CLEF_LOG", raising=False)


@pytest.fixture
def log(monkeypatch, tmp_path):
    """Point CLEF_LOG at a file. Return a function that reads its records."""
    path = tmp_path / "logs" / "clef.jsonl"
    path.parent.mkdir()
    monkeypatch.setenv("CLEF_LOG", str(path))

    return lambda: _results(path) if path.exists() else []


@pytest.fixture
def stub(monkeypatch):
    s = Stub()
    thread = threading.Thread(target=s.server.serve_forever, args=(0.01,), daemon=True)
    thread.start()
    monkeypatch.setenv("CLEF_URL", s.url)
    yield s
    s.server.shutdown()
    s.server.server_close()


@pytest.fixture
def run(monkeypatch, capsys):
    """Run clef.py's main with the given stdin and flags. Return (exit, stdout, stderr)."""

    def _run(stdin, *argv):
        text = stdin if isinstance(stdin, str) else json.dumps(stdin)
        monkeypatch.setattr(sys, "stdin", io.StringIO(text))
        code = main(list(argv))
        out, err = capsys.readouterr()
        return code, out, err

    return _run


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


def _one_line(err):
    assert err.startswith("clef: ")
    assert err.count("\n") == 1
    return err


def _resolves(monkeypatch, docker):
    def fake_getaddrinfo(host, *args, **kwargs):
        if host == "host.docker.internal" and docker:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.65.254", 0))]
        raise socket.gaierror(8, "nodename nor servname provided, or not known")

    monkeypatch.setattr(_mod.socket, "getaddrinfo", fake_getaddrinfo)


# ---------------------------------------------------------------------------
# Exit 0 — answered
# ---------------------------------------------------------------------------


class TestAnswered:
    def test_prints_reply_unchanged(self, stub, run):
        stub.respond(200, '{"model":"clef-flash", "answers":{}, "usage":{}}')
        code, out, err = run(_body())
        assert (code, out, err) == (0, '{"model":"clef-flash", "answers":{}, "usage":{}}', "")

    def test_sends_cloudflare_request(self, stub, run):
        code, _, _ = run(_body())
        assert code == 0
        assert stub.requests[0][0] == "/v1/systemone"
        assert stub.sent == {"model": "clef-flash", **_body()}

    def test_sends_model_flag_unchanged(self, stub, run):
        run(_body(), "--model", "clef")
        assert stub.sent["model"] == "clef"

    def test_sends_no_ollama_fields(self, stub, run):
        run(_body())
        assert set(stub.sent) == {"model", "state", "questions"}

    def test_sends_json_state(self, stub, run):
        state = {"ticket": {"title": "Login fails", "priority": None}}
        run(_body(state=state))
        assert stub.sent["state"] == state

    def test_state_file_replaces_state(self, stub, run, tmp_path):
        path = _write(tmp_path, "state.txt", b"From a file.\n")
        code, _, _ = run({"questions": {"q": _noul()}}, "--state-file", path)
        assert code == 0
        assert stub.sent["state"] == "From a file.\n"

    def test_images_go_as_raw_base64(self, stub, run, tmp_path):
        paths = [_write(tmp_path, n, d) for n, d in [("a.png", PNG), ("b.jpg", JPEG), ("c.webp", WEBP)]]
        code, _, _ = run(_body(), *[arg for p in paths for arg in ("--image", p)])
        assert code == 0
        assert stub.sent["images"] == [base64.b64encode(d).decode() for d in (PNG, JPEG, WEBP)]

    def test_all_three_question_types(self, stub, run):
        questions = {
            "down": {"type": "noul", "instructions": "Is a service down?", "criteria": {"true": "Yes", "false": "No"}},
            "team": {"type": "choice", "instructions": "Which team?", "criteria": {"billing": "Payments", "tech": None}},
            "urgency": {"type": "score", "instructions": {"q": "How urgent?"}, "criteria": ["Can wait", "Today"]},
        }
        code, _, _ = run(_body(questions=questions))
        assert code == 0
        assert stub.sent["questions"] == questions

    def test_question_limits_inclusive(self, stub, run):
        questions: dict = {f"q{i}": _noul() for i in range(64)}
        questions["q0"] = {"type": "choice", "instructions": "x", "criteria": {str(i): None for i in range(255)}}
        questions["q1"] = {"type": "score", "instructions": "x", "criteria": list(range(10))}
        assert run(_body(questions=questions))[0] == 0

    def test_image_limits_inclusive(self, stub, run, tmp_path):
        big = PNG + b"\x00" * (4 * MIB - len(PNG))
        args = ["--image", _write(tmp_path, "a.png", big), "--image", _write(tmp_path, "b.png", big)]
        assert run(_body(), *args)[0] == 0


# ---------------------------------------------------------------------------
# Exit 2 — a local check failed; nothing is sent
# ---------------------------------------------------------------------------


class TestLocalChecks:
    @pytest.mark.parametrize(
        "stdin, message",
        [
            ("not json", "stdin is not JSON"),
            ("[1, 2]", "stdin must be a JSON object"),
            (OVER_LONG_INT, "stdin is not JSON"),
            (json.dumps(_body(state={"x": math.nan})), "stdin is not JSON: NaN is not a JSON number"),
            ('{"state": "x", "questions": {}, "n": 1e400}', "stdin is not JSON"),
            (_body(model="clef"), "use --model"),
            (_body(images=["x"]), "use --image"),
            (_body(timeout=5), "use --timeout"),
            (_body(keep_alive=0), "stdin takes only `state` and `questions`"),
            (_body(state_file="s.txt"), "use --state-file"),
            ({"questions": {"q": _noul()}}, "no state"),
            ({"state": "x"}, "no questions"),
            (_body(questions=[]), "must be an object"),
            (_body(questions={}), "give 1–64 questions, not 0"),
            (_body(questions={f"q{i}": _noul() for i in range(65)}), "give 1–64 questions, not 65"),
            (_body(questions={"bad id": _noul()}), "question id 'bad id'"),
            (_body(questions={"q\n": _noul()}), "question id 'q\\n'"),
            (_body(questions={"x" * 101: _noul()}), "question id"),
            (_body(questions={"q": "Is it?"}), "question q: must be an object"),
            (_body(questions={"q": _noul(type="bool")}), "type must be noul, choice or score"),
            (_body(questions={"q": {"type": "noul"}}), "needs non-empty `instructions`"),
            (_body(questions={"q": _noul(instructions="  ")}), "needs non-empty `instructions`"),
            (_body(questions={"q": _noul(criteria=["yes", "no"])}), "noul `criteria` must be an object"),
            (_body(questions={"q": _noul(criteria={"maybe": "z"})}), "takes only `true` and `false`"),
            (_body(questions={"q": _noul(type="choice")}), "choice `criteria` must be an object"),
            (_body(questions={"q": _noul(type="choice", criteria={"a": None})}), "give 2–255 options, not 1"),
            (
                _body(questions={"q": _noul(type="choice", criteria={str(i): None for i in range(256)})}),
                "give 2–255 options, not 256",
            ),
            (_body(questions={"q": _noul(type="choice", criteria={"": None, "b": None})}), "option ids"),
            (_body(questions={"q": _noul(type="score", criteria={"a": 1})}), "score `criteria` must be a list"),
            (_body(questions={"q": _noul(type="score", criteria=["low"])}), "give 2–10 levels, not 1"),
            (_body(questions={"q": _noul(type="score", criteria=list(range(11)))}), "give 2–10 levels, not 11"),
        ],
    )
    def test_bad_stdin(self, stub, run, stdin, message):
        code, out, err = run(stdin)
        assert (code, out) == (2, "")
        assert message in _one_line(err)
        assert stub.requests == []

    def test_state_on_stdin_and_state_file(self, stub, run, tmp_path):
        path = _write(tmp_path, "state.txt", b"x")
        code, _, err = run(_body(), "--state-file", path)
        assert code == 2
        assert "not both" in _one_line(err)
        assert stub.requests == []

    def test_missing_state_file(self, stub, run, tmp_path):
        code, _, err = run({"questions": {"q": _noul()}}, "--state-file", str(tmp_path / "missing.txt"))
        assert code == 2
        assert "cannot read state file" in _one_line(err)

    @pytest.mark.parametrize(
        "argv",
        [
            ["--model", "gpt"],
            ["--timeout", "0"],
            ["--timeout", "soon"],
            ["--timeout", "nan"],
            ["--timeout", "inf"],
            ["--timeout", "-inf"],
            ["--timeout", OVER_LONG_INT],
            ["--timeout", "86400.5"],
            ["--bogus"],
        ],
    )
    def test_bad_flags(self, stub, run, argv):
        code, _, err = run(_body(), *argv)
        assert code == 2
        _one_line(err)
        assert stub.requests == []

    def test_timeout_limit_inclusive(self, stub, run):
        assert run(_body(), "--timeout", "86400")[0] == 0

    def test_five_images(self, stub, run, tmp_path):
        path = _write(tmp_path, "a.png", PNG)
        code, _, err = run(_body(), *["--image", path] * 5)
        assert code == 2
        assert "at most 4 images" in _one_line(err)

    def test_image_not_png_jpeg_or_webp(self, stub, run, tmp_path):
        code, _, err = run(_body(), "--image", _write(tmp_path, "a.gif", b"GIF89a" + b"\x00" * 16))
        assert code == 2
        assert "not PNG, JPEG or WebP" in _one_line(err)

    def test_missing_image(self, stub, run, tmp_path):
        code, _, err = run(_body(), "--image", str(tmp_path / "missing.png"))
        assert code == 2
        assert "cannot read image" in _one_line(err)

    def test_image_over_4_mib(self, stub, run, tmp_path):
        path = _write(tmp_path, "a.png", PNG + b"\x00" * (4 * MIB - len(PNG) + 1))
        code, _, err = run(_body(), "--image", path)
        assert code == 2
        assert "over the 4 MiB limit" in _one_line(err)

    def test_images_over_8_mib_total(self, stub, run, tmp_path):
        path = _write(tmp_path, "a.png", PNG + b"\x00" * (3 * MIB))
        code, _, err = run(_body(), *["--image", path] * 3)
        assert code == 2
        assert "over the 8 MiB limit" in _one_line(err)
        assert stub.requests == []


# ---------------------------------------------------------------------------
# Server replies — exit 2, 3 and 1, and both error shapes
# ---------------------------------------------------------------------------


class TestServerErrors:
    @pytest.mark.parametrize(
        "reply",
        [
            {"error": "question \"q\": choice criteria\nmust be an object"},
            {"error": {"message": "question \"q\": choice criteria\nmust be an object"}},
        ],
        ids=["ollama-shape", "vendor-shape"],
    )
    def test_error_shapes_reduce_to_one_line(self, stub, run, reply):
        stub.respond(400, reply)
        code, out, err = run(_body())
        assert (code, out) == (2, "")
        assert _one_line(err) == 'clef: HTTP 400: question "q": choice criteria must be an object\n'

    def test_413_is_bad_request(self, stub, run):
        stub.respond(413, {"error": {"message": "request body too large"}})
        code, _, err = run(_body())
        assert code == 2
        assert "HTTP 413: request body too large" in _one_line(err)

    def test_error_body_not_json(self, stub, run):
        stub.respond(422, "plain text\nerror")
        code, _, err = run(_body())
        assert code == 2
        assert "HTTP 422: plain text error" in _one_line(err)

    @pytest.mark.parametrize("status, exit_code", [(400, 2), (404, 3)])
    def test_error_body_with_over_long_integer_keeps_its_exit_code(self, stub, run, status, exit_code):
        stub.respond(status, '{"error": "bad", "n": ' + OVER_LONG_INT + "}")
        code, out, err = run(_body())
        assert (code, out) == (exit_code, "")
        assert f'HTTP {status}: {{"error": "bad", "n": 111' in _one_line(err)

    def test_404_is_no_answer(self, stub, run):
        stub.respond(404, {"error": 'model "clef-flash" not found, try pulling it first'})
        code, out, err = run(_body())
        assert (code, out) == (3, "")
        line = _one_line(err)
        assert f"no answer from {stub.url} (URL from CLEF_URL)" in line
        assert 'HTTP 404: model "clef-flash" not found' in line
        assert "setup.md#fixes-for-exit-3" in line

    def test_timeout_is_no_answer(self, stub, run):
        stub.respond(200, ANSWER, delay=1.0)
        code, _, err = run(_body(), "--timeout", "0.2")
        assert code == 3
        line = _one_line(err)
        assert "no reply within 0.2s" in line
        assert "setup.md#fixes-for-exit-3" in line

    def test_unreachable_is_no_answer(self, run, monkeypatch):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        monkeypatch.setenv("CLEF_URL", url)
        code, _, err = run(_body())
        assert code == 3
        line = _one_line(err)
        assert f"no answer from {url} (URL from CLEF_URL): unreachable" in line
        assert "setup.md#fixes-for-exit-3" in line

    def test_404_with_unreadable_body_is_no_answer(self, stub, run):
        stub.respond(404, {"error": "x"}, extra_length=89)
        code, _, err = run(_body())
        assert code == 3
        line = _one_line(err)
        assert "HTTP 404: no error text" in line
        assert "setup.md#fixes-for-exit-3" in line

    def test_dropped_connection_is_no_answer(self, stub, run):
        stub.respond(200, ANSWER, drop=True)
        code, _, err = run(_body())
        assert code == 3
        assert f"no answer from {stub.url} (URL from CLEF_URL): unreachable" in _one_line(err)

    def test_connect_timeout_is_no_answer(self, run, monkeypatch):
        def connect_timeout(*args, **kwargs):
            raise _mod.urllib.error.URLError(TimeoutError("timed out"))

        monkeypatch.setenv("CLEF_URL", "http://10.255.255.1:11434")
        monkeypatch.setattr(_mod.urllib.request, "urlopen", connect_timeout)
        code, _, err = run(_body(), "--timeout", "5")
        assert code == 3
        assert "no reply within 5s" in _one_line(err)

    @pytest.mark.parametrize("body", ["<html>proxy login</html>", '{"n": ' + OVER_LONG_INT + "}", b'{"a": "\xff"}'])
    def test_non_json_200_is_other_error(self, stub, run, body):
        stub.respond(200, body)
        code, out, err = run(_body())
        assert (code, out) == (1, "")
        assert _one_line(err) == f"clef: HTTP 200 from {stub.url}, but the reply is not JSON\n"

    def test_json_200_not_an_object_is_other_error(self, stub, run):
        stub.respond(200, "[1, 2]")
        code, out, err = run(_body())
        assert (code, out) == (1, "")
        assert _one_line(err) == f"clef: HTTP 200 from {stub.url}, but the reply is not a JSON object\n"

    @pytest.mark.parametrize(
        "reply",
        [{"status": "ok"}, {"error": "model is loading"}, {"answers": None}, {"answers": [1]}],
    )
    def test_200_with_no_answers_is_other_error(self, stub, run, log, reply):
        stub.respond(200, reply)
        code, out, err = run(_body())
        assert (code, out) == (1, "")
        assert _one_line(err) == f"clef: HTTP 200 from {stub.url}, but the reply holds no answers\n"
        assert log() == []

    @pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e400"])
    def test_non_finite_number_in_200_is_not_json(self, stub, run, log, number):
        stub.respond(200, '{"answers": {"blue": {"type": "noul", "noul": ' + number + "}}}")
        code, out, err = run(_body())
        assert (code, out) == (1, "")
        assert _one_line(err) == f"clef: HTTP 200 from {stub.url}, but the reply is not JSON\n"
        assert log() == []

    def test_5xx_is_other_error(self, stub, run):
        stub.respond(500, {"error": "runner crashed"})
        code, out, err = run(_body())
        assert (code, out) == (1, "")
        assert _one_line(err) == "clef: HTTP 500: runner crashed\n"


# ---------------------------------------------------------------------------
# --guess and the decision log
# ---------------------------------------------------------------------------

# One question of each type, and the answers the live server gives in their shape.
MIXED_QUESTIONS = {
    "c": {"type": "noul", "instructions": "Is this a complaint?"},
    "t": {"type": "choice", "instructions": "Which team?", "criteria": {"shipping": "Delivery", "billing": "Payments"}},
    "u": {"type": "score", "instructions": "How urgent?", "criteria": ["Can wait", "This week", "Today"]},
}
MIXED_ANSWER = {
    "model": "clef-flash",
    "answers": {
        "c": {"type": "noul", "noul": 0.97},
        "t": {"type": "choice", "choice": "shipping", "probabilities": {"billing": 0.15, "shipping": 0.85},
              "confidence": 0.4},
        "u": {"type": "score", "score": 1.55, "legend": {"0": "Can wait", "1": "This week", "2": "Today"},
              "probabilities": {"0": 0.13, "1": 0.18, "2": 0.69}, "confidence": 0.23},
    },
    "usage": {"input_tokens": 290, "output_tokens": 0},
}


class TestDecisionLog:
    def test_nothing_logged_when_unset(self, stub, run, tmp_path):
        code, _, err = run(_body())
        assert (code, err) == (0, "")
        assert list(tmp_path.iterdir()) == []

    def test_one_line_per_call(self, stub, run, log, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = _write(tmp_path, "a.png", PNG)
        code, out, err = run(_body(), "--model", "clef", "--image", path)
        assert (code, out, err) == (0, json.dumps(ANSWER), "")
        [record] = log()
        assert set(record) == {
            "time", "cwd", "model", "state", "state_chars", "images", "questions",
            "answers", "guess", "agree", "usage", "latency_s",
        }
        datetime.fromisoformat(record["time"])
        assert record["cwd"] == os.getcwd()
        assert record["model"] == "clef"
        assert (record["state"], record["state_chars"]) == ("The sky is blue.", 16)
        assert record["images"] == [path]
        assert record["questions"] == _body()["questions"]
        assert record["answers"] == ANSWER["answers"]
        assert record["usage"] == ANSWER["usage"]
        assert (record["guess"], record["agree"]) == ({}, {})
        assert record["latency_s"] >= 0

    def test_json_state_counts_its_json(self, stub, run, log):
        state = {"ticket": "Login fails"}
        run(_body(state=state))
        [record] = log()
        assert record["state"] == state
        assert record["state_chars"] == len(json.dumps(state))

    def test_appends_with_mode_0600(self, stub, run, log):
        run(_body())
        run(_body())
        assert len(log()) == 2
        assert Path(os.environ["CLEF_LOG"]).stat().st_mode & 0o777 == 0o600

    def test_failed_call_not_logged(self, stub, run, log):
        stub.respond(400, {"error": "bad"})
        assert run(_body())[0] == 2
        assert log() == []

    def test_lone_surrogate_logs_and_keeps_exit_0(self, stub, run, log):
        code, out, err = run('{"state": "a\\ud800", "questions": {"blue": {"type": "noul", "instructions": "x"}}}')
        assert (code, out, err) == (0, json.dumps(ANSWER), "")
        assert log()[0]["state"] == "a\ud800"

    def test_missing_folder_warns_and_answers(self, stub, run, monkeypatch, tmp_path):
        monkeypatch.setenv("CLEF_LOG", str(tmp_path / "missing" / "clef.jsonl"))
        code, out, err = run(_body())
        assert (code, out) == (0, json.dumps(ANSWER))
        assert "clef: warning:" in _one_line(err)
        assert str(tmp_path / "missing") in err
        assert not (tmp_path / "missing").exists()


class TestGuess:
    def test_guess_goes_only_to_the_log(self, stub, run, log):
        stub.respond(200, MIXED_ANSWER)
        guess = {"c": True, "t": "billing", "u": 2}
        code, _, _ = run(_body(questions=MIXED_QUESTIONS), "--guess", json.dumps(guess))
        assert code == 0
        assert stub.sent == {"model": "clef-flash", **_body(questions=MIXED_QUESTIONS)}
        [record] = log()
        assert record["guess"] == guess
        assert record["agree"] == {"c": True, "t": False, "u": True}

    @pytest.mark.parametrize(
        "guess, agree",
        [
            ({"c": False}, {"c": False}),
            ({"t": "shipping"}, {"t": True}),
            ({"u": 1}, {"u": False}),
        ],
    )
    def test_agree_per_type(self, stub, run, log, guess, agree):
        stub.respond(200, MIXED_ANSWER)
        run(_body(questions=MIXED_QUESTIONS), "--guess", json.dumps(guess))
        assert log()[0]["agree"] == agree

    @pytest.mark.parametrize("value, agree", [(0.49, False), (0.5, None), (0.51, True)])
    def test_noul_agrees_on_the_same_side_of_half(self, stub, run, log, value, agree):
        stub.respond(200, {"answers": {"c": {"type": "noul", "noul": value}}, "usage": {}})
        run(_body(questions={"c": MIXED_QUESTIONS["c"]}), "--guess", '{"c": true}')
        assert log()[0]["agree"] == {"c": agree}

    def test_score_too_large_for_a_float_disagrees(self, stub, run, log):
        stub.respond(200, {"answers": {"u": {"type": "score", "score": 10**400}}, "usage": {}})
        code, _, err = run(_body(questions={"u": MIXED_QUESTIONS["u"]}), "--guess", '{"u": 1}')
        assert (code, err) == (0, "")
        assert log()[0]["agree"] == {"u": False}

    def test_missing_answer_agrees_with_nothing(self, stub, run, log):
        stub.respond(200, {"answers": {}, "usage": {}})
        run(_body(questions=MIXED_QUESTIONS), "--guess", '{"t": "shipping"}')
        assert log()[0]["agree"] == {"t": None}

    @pytest.mark.parametrize(
        "guess, message",
        [
            ("yes", "--guess is not JSON"),
            ('{"c": ' + OVER_LONG_INT + "}", "--guess is not JSON"),
            ('{"u": NaN}', "--guess is not JSON"),
            ("[true]", "guess must be an object"),
            ('{"nope": true}', "guess nope: no such question"),
            ('{"c": 1}', "guess c: give true or false"),
            ('{"t": "sales"}', "guess t: give one of the question's option ids"),
            ('{"u": 3}', "guess u: give a level index from 0 to 2"),
            ('{"u": -1}', "guess u: give a level index from 0 to 2"),
            ('{"u": true}', "guess u: give a level index from 0 to 2"),
            ('{"u": 1.0}', "guess u: give a level index from 0 to 2"),
        ],
    )
    def test_bad_guess(self, stub, run, guess, message):
        code, out, err = run(_body(questions=MIXED_QUESTIONS), "--guess", guess)
        assert (code, out) == (2, "")
        assert message in _one_line(err)
        assert stub.requests == []


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------


def _jsonl(tmp_path, *lines, name="in.jsonl"):
    """Write lines to a JSONL file. A str line goes as is; anything else as JSON."""
    path = tmp_path / name
    path.write_text("".join((l if isinstance(l, str) else json.dumps(l)) + "\n" for l in lines))
    return str(path)


def _results(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


class TestBatch:
    def test_one_call_per_line_to_out(self, stub, run, tmp_path):
        src = _jsonl(tmp_path, {"id": "a", **_body()}, {"id": 7, **_body(state="Two")}, _body(state="Three"))
        dst = str(tmp_path / "out.jsonl")
        code, out, err = run("", "--batch", src, "--out", dst, "--model", "clef")
        assert (code, out, err) == (0, f"3 answered, 0 failed -> {dst}\n", "")
        assert [r[1]["state"] for r in stub.requests] == ["The sky is blue.", "Two", "Three"]
        assert {r[1]["model"] for r in stub.requests} == {"clef"}
        assert _results(dst) == [{"id": "a", **ANSWER}, {"id": 7, **ANSWER}, {"line": 3, **ANSWER}]

    def test_results_to_stdout_and_summary_to_stderr(self, stub, run, tmp_path):
        code, out, err = run("", "--batch", _jsonl(tmp_path, _body(), _body()))
        assert code == 0
        assert [json.loads(l) for l in out.splitlines()] == [{"line": 1, **ANSWER}, {"line": 2, **ANSWER}]
        assert _one_line(err) == "clef: 2 answered, 0 failed\n"

    def test_ignores_stdin(self, stub, run, tmp_path):
        assert run("not json", "--batch", _jsonl(tmp_path, _body()))[0] == 0

    def test_blank_lines_skipped_but_counted(self, stub, run, tmp_path):
        code, out, _ = run("", "--batch", _jsonl(tmp_path, "", _body(), "  "))
        assert code == 0
        assert [json.loads(l)["line"] for l in out.splitlines()] == [2]

    def test_empty_batch(self, stub, run, tmp_path):
        code, out, err = run("", "--batch", _jsonl(tmp_path))
        assert (code, out, err) == (0, "", "clef: 0 answered, 0 failed\n")

    def test_images_per_line(self, stub, run, tmp_path):
        png, jpg = _write(tmp_path, "a.png", PNG), _write(tmp_path, "b.jpg", JPEG)
        code, _, _ = run("", "--batch", _jsonl(tmp_path, {**_body(), "images": [png, jpg]}, _body()))
        assert code == 0
        assert stub.requests[0][1]["images"] == [base64.b64encode(d).decode() for d in (PNG, JPEG)]
        assert "images" not in stub.requests[1][1]

    @pytest.mark.parametrize(
        "line, ref, message",
        [
            ("not json", {"line": 1}, "line is not JSON"),
            ("[1]", {"line": 1}, "line must be a JSON object"),
            ({**_body(), "id": True}, {"line": 1}, "`id` must be a string or number"),
            ({**_body(), "id": [1]}, {"line": 1}, "`id` must be a string or number"),
            (json.dumps({**_body(), "id": math.nan}), {"line": 1}, "line is not JSON: NaN is not a JSON number"),
            (json.dumps({**_body(), "id": math.inf}), {"line": 1}, "line is not JSON: Infinity is not a JSON number"),
            (json.dumps(_body(state={"x": -math.inf})), {"line": 1}, "line is not JSON"),
            ('{"id": 1e400}', {"line": 1}, "line is not JSON"),
            ('{"id": ' + OVER_LONG_INT + "}", {"line": 1}, "line is not JSON"),
            ({**_body(), "id": "x", "model": "clef"}, {"id": "x"}, "line key `model` is not allowed"),
            ({"id": "x", "questions": {"q": _noul()}}, {"id": "x"}, "line has no `state`"),
            ({"id": "x", "state": "s"}, {"id": "x"}, "line has no `questions`"),
            ({**_body(questions={}), "id": "x"}, {"id": "x"}, "give 1–64 questions, not 0"),
            ({**_body(), "id": "x", "images": "a.png"}, {"id": "x"}, "`images` must be a list of paths"),
            ({**_body(), "id": "x", "images": ["missing.png"]}, {"id": "x"}, "cannot read image"),
            ({**_body(), "id": "x", "guess": {"blue": "yes"}}, {"id": "x"}, "guess blue: give true or false"),
        ],
    )
    def test_bad_line_writes_its_error_and_goes_on(self, stub, run, tmp_path, line, ref, message):
        dst = str(tmp_path / "out.jsonl")
        code, out, err = run("", "--batch", _jsonl(tmp_path, line, _body()), "--out", dst)
        assert (code, out, err) == (0, f"1 answered, 1 failed -> {dst}\n", "")
        bad, good = _results(dst)
        assert set(bad) == {*ref, "error", "exit"}
        assert {k: bad[k] for k in ref} == ref
        assert bad["error"].startswith("clef: ") and message in bad["error"]
        assert bad["exit"] == 2
        assert good == {"line": 2, **ANSWER}
        assert len(stub.requests) == 1

    def test_every_line_failed_still_exits_0(self, stub, run, tmp_path):
        stub.respond(400, {"error": "question too long"})
        code, out, err = run("", "--batch", _jsonl(tmp_path, "not json", _body(questions={}), _body()))
        assert (code, err) == (0, "clef: 0 answered, 3 failed\n")
        assert [json.loads(l)["exit"] for l in out.splitlines()] == [2, 2, 2]
        assert len(stub.requests) == 1

    def test_every_line_failed_to_out_still_exits_0(self, stub, run, tmp_path):
        stub.respond(400, {"error": "question too long"})
        dst = str(tmp_path / "out.jsonl")
        code, out, err = run("", "--batch", _jsonl(tmp_path, "not json", _body()), "--out", dst)
        assert (code, out, err) == (0, f"0 answered, 2 failed -> {dst}\n", "")
        assert [r["exit"] for r in _results(dst)] == [2, 2]

    def test_huge_integer_id_is_carried(self, stub, run, tmp_path):
        code, out, _ = run("", "--batch", _jsonl(tmp_path, {**_body(), "id": 10**400}))
        assert code == 0
        assert json.loads(out) == {"id": 10**400, **ANSWER}

    def test_lone_surrogate_line_writes_its_error_and_goes_on(self, stub, run, tmp_path):
        bad = '{"id": "a\\udc80", "\\udc80x": 1, "state": "s", "questions": {"q": {"type": "noul", "instructions": "x"}}}'
        code, out, _ = run("", "--batch", _jsonl(tmp_path, bad, _body()))
        assert code == 0
        first, second = [json.loads(l) for l in out.splitlines()]
        assert (first["id"], first["exit"]) == ("a\udc80", 2)
        assert second == {"line": 2, **ANSWER}

    def test_reply_id_does_not_replace_the_line_id(self, stub, run, tmp_path):
        stub.respond(200, {"id": "srv-1", **ANSWER})
        _, out, _ = run("", "--batch", _jsonl(tmp_path, {"id": "mine", **_body()}))
        assert json.loads(out)["id"] == "mine"

    def test_reply_keys_that_name_a_line_never_reach_its_result(self, stub, run, tmp_path):
        stub.respond(200, {"id": "chatcmpl-9", "line": 99, "error": "x", "exit": 5, **ANSWER})
        code, out, _ = run("", "--batch", _jsonl(tmp_path, _body(), {"id": "b", **_body()}))
        assert code == 0
        assert [json.loads(l) for l in out.splitlines()] == [{"line": 1, **ANSWER}, {"id": "b", **ANSWER}]

    @pytest.mark.parametrize(
        "reply, message",
        [
            ('{"error": "model is loading"}', "the reply holds no answers"),
            ('{"answers": null}', "the reply holds no answers"),
            ('{"answers": [1]}', "the reply holds no answers"),
            ('{"answers": {"blue": {"type": "noul", "noul": NaN}}}', "the reply is not JSON"),
        ],
    )
    def test_200_with_no_good_answer_stops_with_exit_1(self, stub, run, tmp_path, log, reply, message):
        stub.respond_each((200, ANSWER), (200, reply))
        dst = str(tmp_path / "out.jsonl")
        code, out, err = run("", "--batch", _jsonl(tmp_path, _body(), _body(), _body()), "--out", dst)
        assert (code, out, err) == (1, "", f"clef: HTTP 200 from {stub.url}, but {message}\n")
        assert _results(dst) == [{"line": 1, **ANSWER}]
        assert len(log()) == 1
        assert len(stub.requests) == 2

    def test_4xx_line_writes_its_error_and_goes_on(self, stub, run, tmp_path):
        stub.respond_each((200, ANSWER), (400, {"error": "question too\nlong"}))
        dst = str(tmp_path / "out.jsonl")
        code, out, _ = run("", "--batch", _jsonl(tmp_path, _body(), {"id": "b", **_body()}, _body()), "--out", dst)
        assert (code, out) == (0, f"2 answered, 1 failed -> {dst}\n")
        assert _results(dst)[1] == {"id": "b", "error": "clef: HTTP 400: question too long", "exit": 2}

    def test_4xx_body_with_over_long_integer_writes_its_error_and_goes_on(self, stub, run, tmp_path):
        stub.respond_each((400, '{"n": ' + OVER_LONG_INT + "}"), (200, ANSWER))
        dst = str(tmp_path / "out.jsonl")
        code, out, _ = run("", "--batch", _jsonl(tmp_path, {"id": "a", **_body()}, _body()), "--out", dst)
        assert (code, out) == (0, f"1 answered, 1 failed -> {dst}\n")
        bad, good = _results(dst)
        assert (bad["id"], bad["exit"]) == ("a", 2)
        assert bad["error"].startswith('clef: HTTP 400: {"n": 111')
        assert good == {"line": 2, **ANSWER}

    def test_server_stopped_exits_3(self, run, tmp_path, monkeypatch):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        monkeypatch.setenv("CLEF_URL", f"http://127.0.0.1:{port}")
        dst = tmp_path / "out.jsonl"
        code, out, err = run("", "--batch", _jsonl(tmp_path, _body(), _body()), "--out", str(dst))
        assert (code, out) == (3, "")
        line = _one_line(err)
        assert f"no answer from http://127.0.0.1:{port} (URL from CLEF_URL): unreachable" in line
        assert "setup.md#fixes-for-exit-3" in line
        assert dst.read_text() == ""

    def test_exit_3_keeps_earlier_results(self, stub, run, tmp_path):
        stub.respond_each((200, ANSWER), (404, {"error": "model not found"}))
        dst = str(tmp_path / "out.jsonl")
        code, out, err = run("", "--batch", _jsonl(tmp_path, _body(), _body(), _body()), "--out", dst)
        assert (code, out) == (3, "")
        assert "HTTP 404: model not found" in _one_line(err)
        assert _results(dst) == [{"line": 1, **ANSWER}]
        assert len(stub.requests) == 2

    def test_5xx_stops_with_exit_1(self, stub, run, tmp_path):
        stub.respond_each((200, ANSWER), (500, {"error": "runner crashed"}))
        dst = str(tmp_path / "out.jsonl")
        code, out, err = run("", "--batch", _jsonl(tmp_path, _body(), _body(), _body()), "--out", dst)
        assert (code, out, err) == (1, "", "clef: HTTP 500: runner crashed\n")
        assert _results(dst) == [{"line": 1, **ANSWER}]

    def test_5xx_after_a_bad_line_stops_with_exit_1(self, stub, run, tmp_path):
        stub.respond(500, {"error": "runner crashed"})
        dst = str(tmp_path / "out.jsonl")
        code, out, err = run("", "--batch", _jsonl(tmp_path, _body(questions={}), _body(), _body()), "--out", dst)
        assert (code, out, err) == (1, "", "clef: HTTP 500: runner crashed\n")
        assert [r["exit"] for r in _results(dst)] == [2]
        assert len(stub.requests) == 1

    def test_each_answered_line_logged_with_its_guess(self, stub, run, tmp_path, log):
        stub.respond(200, MIXED_ANSWER)
        png = _write(tmp_path, "a.png", PNG)
        lines = [
            {**_body(questions=MIXED_QUESTIONS), "guess": {"t": "shipping"}, "images": [png]},
            {**_body(questions=MIXED_QUESTIONS), "guess": {"u": 0}},
            _body(questions={}),
        ]
        assert run("", "--batch", _jsonl(tmp_path, *lines))[0] == 0
        first, second = log()
        assert (first["guess"], first["agree"], first["images"]) == ({"t": "shipping"}, {"t": True}, [png])
        assert (second["guess"], second["agree"], second["images"]) == ({"u": 0}, {"u": False}, [])

    def test_missing_log_folder_warns_once(self, stub, run, tmp_path, monkeypatch):
        monkeypatch.setenv("CLEF_LOG", str(tmp_path / "missing" / "clef.jsonl"))
        dst = str(tmp_path / "out.jsonl")
        code, out, err = run("", "--batch", _jsonl(tmp_path, _body(), _body()), "--out", dst)
        assert (code, out) == (0, f"2 answered, 0 failed -> {dst}\n")
        assert "clef: warning:" in _one_line(err)

    @pytest.mark.parametrize(
        "argv, message",
        [
            (["--image", "a.png"], "--batch and --image do not mix"),
            (["--state-file", "s.txt"], "--batch and --state-file do not mix"),
            (["--guess", "{}"], "--batch and --guess do not mix"),
            (["--guess", ""], "--batch and --guess do not mix"),
            (["--state-file", ""], "--batch and --state-file do not mix"),
        ],
    )
    def test_batch_flag_conflicts(self, stub, run, tmp_path, argv, message):
        code, out, err = run("", "--batch", _jsonl(tmp_path, _body()), *argv)
        assert (code, out) == (2, "")
        assert message in _one_line(err)
        assert stub.requests == []

    def test_out_needs_batch(self, stub, run, tmp_path):
        code, _, err = run(_body(), "--out", str(tmp_path / "out.jsonl"))
        assert code == 2
        assert "--out needs --batch" in _one_line(err)
        assert stub.requests == []

    def test_ids_runs_only_the_lines_named(self, stub, run, tmp_path):
        src = _jsonl(
            tmp_path,
            {"id": "a", **_body(state="A")},
            {"id": 7, **_body(state="Seven")},
            _body(state="Line three"),
            {"id": "b", **_body(state="B")},
        )
        code, out, err = run("", "--batch", src, "--ids", "b 7 3", "--model", "clef")
        assert code == 0
        assert [r[1]["state"] for r in stub.requests] == ["Seven", "Line three", "B"]
        assert [json.loads(l) for l in out.splitlines()] == [
            {"id": 7, **ANSWER},
            {"line": 3, **ANSWER},
            {"id": "b", **ANSWER},
        ]
        assert _one_line(err) == "clef: 3 answered, 0 failed\n"

    def test_ids_skips_bad_lines_not_named(self, stub, run, tmp_path):
        code, out, err = run("", "--batch", _jsonl(tmp_path, "not json", {"id": "a", **_body()}), "--ids", "a")
        assert (code, err) == (0, "clef: 1 answered, 0 failed\n")
        assert json.loads(out) == {"id": "a", **ANSWER}

    def test_ids_names_a_bad_line_by_its_line_number(self, stub, run, tmp_path):
        code, out, _ = run("", "--batch", _jsonl(tmp_path, _body(), {**_body(), "id": True}), "--ids", "2")
        assert code == 0
        assert json.loads(out)["line"] == 2
        assert stub.requests == []

    @pytest.mark.parametrize(
        "ids, message",
        [
            # Line 1 has the id "a", line 2 is blank and line 3 has no id.
            ("a zz 9 zz", "--ids zz 9: no batch line has that id or line number"),
            ("1", "--ids 1: no batch line has that id or line number"),
            ("2", "--ids 2: no batch line has that id or line number"),
            ("", "--ids lists no ids"),
            ("  ", "--ids lists no ids"),
        ],
    )
    def test_ids_that_match_no_line_exit_2_before_any_call(self, stub, run, tmp_path, ids, message):
        dst = tmp_path / "out.jsonl"
        src = _jsonl(tmp_path, {"id": "a", **_body()}, "", _body())
        code, out, err = run("", "--batch", src, "--ids", ids, "--out", str(dst))
        assert (code, out, err) == (2, "", f"clef: {message}\n")
        assert stub.requests == []
        assert not dst.exists()

    def test_ids_needs_batch(self, stub, run):
        code, _, err = run(_body(), "--ids", "a")
        assert code == 2
        assert "--ids needs --batch" in _one_line(err)
        assert stub.requests == []

    def test_lines_runs_the_lines_at_those_numbers_even_with_an_id(self, stub, run, tmp_path):
        src = _jsonl(
            tmp_path,
            {"id": "a", **_body(state="A")},
            {"id": 7, **_body(state="Seven")},
            "",
            _body(state="Line four"),
        )
        code, out, err = run("", "--batch", src, "--lines", "4 3 1 4")
        assert code == 0
        assert [r[1]["state"] for r in stub.requests] == ["A", "Line four"]
        assert [json.loads(l) for l in out.splitlines()] == [{"id": "a", **ANSWER}, {"line": 4, **ANSWER}]
        assert _one_line(err) == "clef: 2 answered, 0 failed\n"

    def test_lines_runs_a_bad_line_and_exits_0(self, stub, run, tmp_path):
        src = _jsonl(tmp_path, _body(questions={}), _body(state="Two"), _body(state="Three"))
        code, out, err = run("", "--batch", src, "--lines", "1 2")
        assert (code, err) == (0, "clef: 1 answered, 1 failed\n")
        bad, good = [json.loads(l) for l in out.splitlines()]
        assert (bad["line"], bad["exit"]) == (1, 2)
        assert good == {"line": 2, **ANSWER}
        assert [r[1]["state"] for r in stub.requests] == ["Two"]

    def test_lines_counts_a_last_line_with_no_newline(self, stub, run, tmp_path):
        src = _write(tmp_path, "batch.jsonl", (json.dumps(_body()) + "\n" + json.dumps(_body(state="Two"))).encode())
        code, out, _ = run("", "--batch", src, "--lines", "2")
        assert code == 0
        assert json.loads(out) == {"line": 2, **ANSWER}

    @pytest.mark.parametrize(
        "lines, message",
        [
            # The file has 3 lines: line 2 is blank.
            ("1 4 9 4", "--lines 4 9: the batch file has 3 lines"),
            ("10", "--lines 10: the batch file has 3 lines"),
            pytest.param(OVER_LONG_INT, f"--lines {OVER_LONG_INT}: the batch file has 3 lines", id="over-long"),
            ("0", "--lines 0: not a line number"),
            ("1 x -2 01", "--lines x -2 01: not a line number"),
            ("", "--lines lists no line numbers"),
            ("  ", "--lines lists no line numbers"),
        ],
    )
    def test_lines_that_name_no_line_exit_2_before_any_call(self, stub, run, tmp_path, lines, message):
        dst = tmp_path / "out.jsonl"
        src = _jsonl(tmp_path, {"id": "a", **_body()}, "", _body())
        code, out, err = run("", "--batch", src, "--lines", lines, "--out", str(dst))
        assert (code, out, err) == (2, "", f"clef: {message}\n")
        assert stub.requests == []
        assert not dst.exists()

    def test_lines_needs_batch(self, stub, run):
        code, _, err = run(_body(), "--lines", "1")
        assert code == 2
        assert "--lines needs --batch" in _one_line(err)
        assert stub.requests == []

    def test_lines_and_ids_do_not_mix(self, stub, run, tmp_path):
        code, _, err = run("", "--batch", _jsonl(tmp_path, _body()), "--ids", "1", "--lines", "1")
        assert code == 2
        assert "--ids and --lines do not mix" in _one_line(err)
        assert stub.requests == []

    def test_missing_batch_file(self, stub, run, tmp_path):
        dst = tmp_path / "out.jsonl"
        code, out, err = run("", "--batch", str(tmp_path / "missing.jsonl"), "--out", str(dst))
        assert (code, out) == (2, "")
        assert "cannot read batch file" in _one_line(err)
        assert not dst.exists()

    def test_unwritable_out(self, stub, run, tmp_path):
        code, _, err = run("", "--batch", _jsonl(tmp_path, _body()), "--out", str(tmp_path / "no" / "out.jsonl"))
        assert code == 2
        assert "cannot write --out file" in _one_line(err)
        assert stub.requests == []


# ---------------------------------------------------------------------------
# Server URL order
# ---------------------------------------------------------------------------


class TestServerUrl:
    def test_clef_url_wins(self, monkeypatch):
        monkeypatch.setenv("CLEF_URL", "http://mac.local:11434/")
        _resolves(monkeypatch, docker=True)
        assert resolve_url() == ("http://mac.local:11434", "CLEF_URL")

    def test_docker_host_when_it_resolves(self, monkeypatch):
        monkeypatch.delenv("CLEF_URL", raising=False)
        _resolves(monkeypatch, docker=True)
        assert resolve_url() == ("http://host.docker.internal:11434", "host.docker.internal resolves")

    def test_loopback_otherwise(self, monkeypatch):
        monkeypatch.setenv("CLEF_URL", "  ")
        _resolves(monkeypatch, docker=False)
        assert resolve_url() == ("http://127.0.0.1:11434", "default")

    def test_error_line_names_the_docker_source(self, run, monkeypatch):
        monkeypatch.delenv("CLEF_URL", raising=False)
        _resolves(monkeypatch, docker=True)
        monkeypatch.setattr(_mod, "DOCKER_URL", "http://127.0.0.1:9")
        code, _, err = run(_body())
        assert code == 3
        assert "no answer from http://127.0.0.1:9 (URL from host.docker.internal resolves)" in _one_line(err)

    def test_error_line_names_the_default_source(self, run, monkeypatch):
        monkeypatch.delenv("CLEF_URL", raising=False)
        _resolves(monkeypatch, docker=False)
        monkeypatch.setattr(_mod, "LOOPBACK_URL", "http://127.0.0.1:9")
        code, _, err = run(_body())
        assert code == 3
        assert "no answer from http://127.0.0.1:9 (URL from default)" in _one_line(err)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
