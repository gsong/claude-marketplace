#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest>=8.0"]
# ///
"""Tests for check.py — it runs the real clef.py against a local stub server."""

import base64
import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("check", Path(__file__).parent / "check.py")
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

main = _mod.main
CASES = _mod.CASES
MEDIA = _mod.MEDIA

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _right(question):
    """The answer a server gives when it gets the question right."""
    expect = question["expect"]
    if question["type"] == "noul":
        return {"type": "noul", "noul": 0.97 if expect else 0.03}
    return {"type": "choice", "choice": expect, "probabilities": {expect: 0.9}, "confidence": 0.5}


class Stub:
    """A local Clef server that records each request and answers every question right,
    unless `answers` overrides a question id."""

    def __init__(self):
        self.answers, self.status = {}, 200
        self.requests = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                request = json.loads(self.rfile.read(length))
                stub.requests.append(request)
                if stub.status == 200:
                    reply = {"model": request["model"], "answers": stub._answer(request), "usage": {}}
                else:
                    reply = {"error": f"stub status {stub.status}"}
                payload = json.dumps(reply).encode()
                self.send_response(stub.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def _answer(self, request):
        expected = {qid: q for case in CASES for qid, q in case["questions"].items()}
        return {qid: self.answers.get(qid, _right(expected[qid])) for qid in request["questions"]}


@pytest.fixture(autouse=True)
def no_log(monkeypatch):
    monkeypatch.delenv("CLEF_LOG", raising=False)


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
def run(capsys):
    """Run check.py's main. Return (exit, stdout, stderr)."""

    def _run():
        code = main()
        out, err = capsys.readouterr()
        return code, out, err

    return _run


CALLS = len(CASES) * 2
ANSWERS = sum(len(case["questions"]) for case in CASES) * 2

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAllRight:
    def test_exits_0(self, stub, run):
        code, out, err = run()
        assert (code, err) == (0, "")
        assert out.endswith(f"{ANSWERS} of {ANSWERS} answers right\n")
        assert "WRONG" not in out

    def test_asks_each_case_on_both_models(self, stub, run):
        run()
        assert [r["model"] for r in stub.requests] == ["clef"] * len(CASES) + ["clef-flash"] * len(CASES)
        assert [r["state"] for r in stub.requests[: len(CASES)]] == [c["state"] for c in CASES]

    def test_sends_no_expected_answers(self, stub, run):
        run()
        for request in stub.requests:
            for question in request["questions"].values():
                assert "expect" not in question

    def test_sends_the_plugin_images(self, stub, run):
        run()
        sent = {r["state"]: r.get("images") for r in stub.requests[: len(CASES)]}
        for case in CASES:
            want = [base64.b64encode((MEDIA / name).read_bytes()).decode() for name in case.get("images", [])]
            assert sent[case["state"]] == (want or None)

    def test_writes_no_decision_log(self, stub, run, monkeypatch, tmp_path):
        log = tmp_path / "clef.jsonl"
        monkeypatch.setenv("CLEF_LOG", str(log))
        assert run()[0] == 0
        assert not log.exists()


class TestWrongAnswer:
    def test_choice_prints_and_goes_on(self, stub, run):
        stub.answers["intent"] = {"type": "choice", "choice": "cancel", "probabilities": {"cancel": 0.8}}
        code, out, _ = run()
        assert code == 1
        assert out.count("WRONG  intent = cancel (0.80), expected pause") == 2
        assert len(stub.requests) == CALLS
        assert out.endswith(f"{ANSWERS - 2} of {ANSWERS} answers right\n")

    def test_noul_false(self, stub, run):
        stub.answers["complaint"] = {"type": "noul", "noul": 0.2}
        code, out, _ = run()
        assert code == 1
        assert "WRONG  complaint = false (0.20), expected true" in out

    def test_noul_at_one_half_is_wrong(self, stub, run):
        stub.answers["complaint"] = {"type": "noul", "noul": 0.5}
        code, out, _ = run()
        assert code == 1
        assert "WRONG  complaint = undecided (0.50), expected true" in out

    def test_missing_answer(self, stub, run):
        stub.answers["cost"] = None
        code, out, _ = run()
        assert code == 1
        assert "WRONG  cost = no answer, expected 15.00" in out


class TestClefFails:
    @pytest.mark.parametrize("status, code", [(404, 3), (400, 2), (500, 1)])
    def test_stops_with_clef_exit_code(self, stub, run, status, code):
        stub.status = status
        got, out, err = run()
        assert got == code
        assert len(stub.requests) == 1
        assert err.startswith("clef: ")
        assert err.count("\n") == 1
        assert "answers right" not in out

    def test_noul_nan_stops_with_exit_1(self, stub, run):
        stub.answers["complaint"] = {"type": "noul", "noul": float("nan")}
        code, out, err = run()
        assert code == 1
        assert len(stub.requests) == 1
        assert err.endswith("but the reply is not JSON\n")
        assert "answers right" not in out

    def test_unreachable_exits_3(self, monkeypatch, run):
        monkeypatch.setenv("CLEF_URL", "http://127.0.0.1:9")
        code, _, err = run()
        assert code == 3
        assert "no answer from http://127.0.0.1:9 (URL from CLEF_URL)" in err


class TestSpeed:
    def test_warns_on_slow_warm_calls_only(self, stub, run, monkeypatch):
        monkeypatch.setattr(_mod, "SLOW_SECONDS", 0.0)
        code, out, _ = run()
        assert code == 0
        assert out.count(", cold\n") == 2
        assert out.count("warning: a warm call over 0 s") == CALLS - 2

    def test_no_warning_under_the_limit(self, stub, run):
        _, out, _ = run()
        assert "warning" not in out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
