#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8.0"]
# ///
"""Tests for clef.py — request checks, exit codes, error shapes and the server URL order."""

import base64
import importlib.util
import io
import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("clef", Path(__file__).parent / "clef.py")
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
        self.requests = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                stub.requests.append((self.path, json.loads(self.rfile.read(length))))
                time.sleep(stub.delay)
                if stub.drop:
                    return
                payload = stub.reply.encode()
                self.send_response(stub.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload) + stub.extra_length))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def respond(self, status, reply, delay=0.0, extra_length=0, drop=False):
        """Set the reply. `extra_length` overstates Content-Length; `drop` closes with no reply."""
        self.status, self.delay, self.extra_length, self.drop = status, delay, extra_length, drop
        self.reply = reply if isinstance(reply, str) else json.dumps(reply)

    @property
    def sent(self):
        """The body of the only request the stub received."""
        assert len(self.requests) == 1
        return self.requests[0][1]


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

    @pytest.mark.parametrize("argv", [["--model", "gpt"], ["--timeout", "0"], ["--timeout", "soon"], ["--bogus"]])
    def test_bad_flags(self, stub, run, argv):
        code, _, err = run(_body(), *argv)
        assert code == 2
        _one_line(err)
        assert stub.requests == []

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

    def test_non_json_200_is_other_error(self, stub, run):
        stub.respond(200, "<html>proxy login</html>")
        code, out, err = run(_body())
        assert (code, out) == (1, "")
        assert _one_line(err) == f"clef: HTTP 200 from {stub.url}, but the reply is not JSON\n"

    def test_5xx_is_other_error(self, stub, run):
        stub.respond(500, {"error": "runner crashed"})
        code, out, err = run(_body())
        assert (code, out) == (1, "")
        assert _one_line(err) == "clef: HTTP 500: runner crashed\n"


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
