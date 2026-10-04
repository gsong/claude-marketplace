#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check that the Clef server answers six known questions right on both models.

Run it on the Mac after setup and after each `brew upgrade ollama`.
It runs clef.py once per case and model, so it also checks the script's flags and image encoding.
A wrong answer is printed and the run goes on. A warm call over 30 s gets a warning, never a failure.

Exit codes: 0 every answer right, 1 a wrong answer, or clef.py's own exit code when clef.py fails.
clef.py's failure stops the run.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLEF = HERE / "clef.py"
MEDIA = HERE / "media"

MODELS = ("clef", "clef-flash")
SLOW_SECONDS = 30.0

EXIT_OK, EXIT_WRONG = 0, 1

# Each question's `expect` is the right answer. check.py strips it before the call.
CASES = [
    {
        "name": "sarcasm",
        "state": "Oh fantastic, the app logged me out for the fifth time today. Truly the highlight of my week.",
        "questions": {
            "sentiment": {
                "type": "choice",
                "instructions": "What is the customer's sentiment?",
                "criteria": {"positive": "Pleased", "neutral": "No clear feeling", "negative": "Unhappy or frustrated"},
                "expect": "negative",
            },
            "complaint": {"type": "noul", "instructions": "Is this a complaint?", "expect": True},
        },
    },
    {
        "name": "negated intent",
        "state": "I don't want to cancel my subscription, I just want to pause it for two months while I travel.",
        "questions": {
            "intent": {
                "type": "choice",
                "instructions": "What does the customer want?",
                "criteria": {
                    "cancel": "End the subscription",
                    "pause": "Temporarily suspend the subscription",
                    "upgrade": "Move to a higher plan",
                    "other": "Something else",
                },
                "expect": "pause",
            },
        },
    },
    {
        "name": "word problem",
        "state": "A store sells pens only in packs of 12 for $3.00 per pack. Maya needs 50 pens and must buy whole packs.",
        "questions": {
            "cost": {
                "type": "choice",
                "instructions": "How much does Maya spend?",
                "criteria": {"12.00": "$12.00", "12.50": "$12.50", "15.00": "$15.00", "18.00": "$18.00"},
                "expect": "15.00",
            },
        },
    },
    {
        "name": "receipt: clear",
        "state": "Review the attached receipt.",
        "images": ["receipt_clear.png"],
        "questions": {
            "total": {
                "type": "choice",
                "instructions": "What is the receipt total?",
                "criteria": {"42.17": "$42.17", "24.71": "$24.71", "47.12": "$47.12", "42.71": "$42.71"},
                "expect": "42.17",
            },
        },
    },
    {
        "name": "counting shapes",
        "state": "Look at the attached image.",
        "images": ["shapes.png"],
        "questions": {
            "red_circles": {
                "type": "choice",
                "instructions": "How many red circles are there?",
                "criteria": {"1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five"},
                "expect": "3",
            },
        },
    },
]


class ClefFailed(Exception):
    """clef.py exited with an error. Carries its stderr line and exit code."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def main() -> int:
    right = wrong = 0
    try:
        for model in MODELS:
            print(model)
            for index, case in enumerate(CASES):
                reply, seconds = ask(model, case)
                print(f"  {case['name']}: {_timing(seconds, cold=index == 0)}")
                answers = reply.get("answers")
                answers = answers if isinstance(answers, dict) else {}
                for qid, question in case["questions"].items():
                    ok, shown = judge(question, answers.get(qid))
                    if ok:
                        right += 1
                        print(f"    ok     {qid} = {shown}")
                    else:
                        wrong += 1
                        print(f"    WRONG  {qid} = {shown}, expected {_format(question['expect'])}")
    except ClefFailed as e:
        print(e, file=sys.stderr)
        return e.code
    print(f"{right} of {right + wrong} answers right")
    return EXIT_WRONG if wrong else EXIT_OK


def ask(model: str, case: dict) -> tuple[dict, float]:
    """Run clef.py on one case. Return its reply and the seconds the call took."""
    body = {
        "state": case["state"],
        "questions": {
            qid: {key: value for key, value in question.items() if key != "expect"}
            for qid, question in case["questions"].items()
        },
    }
    argv = [str(CLEF), "--model", model]
    for name in case.get("images", []):
        argv += ["--image", str(MEDIA / name)]
    # Keep the check's calls out of the developer's decision log.
    env = {key: value for key, value in os.environ.items() if key != "CLEF_LOG"}
    start = time.monotonic()
    result = subprocess.run(argv, input=json.dumps(body), capture_output=True, text=True, env=env, check=False)
    seconds = time.monotonic() - start
    if result.returncode != 0:
        message = result.stderr.strip() or f"clef: exited {result.returncode} with no error text"
        raise ClefFailed(message, result.returncode)
    return json.loads(result.stdout), seconds


def judge(question: dict, answer: object) -> tuple[bool, str]:
    """Return whether Clef's answer matches the expected one, and the answer as text."""
    if not isinstance(answer, dict):
        return False, "no answer"
    if question["type"] == "noul":
        value = answer.get("noul")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False, "no answer"
        # 0.5 is neither true nor false, so it never matches.
        verdict = None if value == 0.5 else value > 0.5
        return verdict == question["expect"], f"{_format(verdict)} ({value:.2f})"
    choice = answer.get("choice")
    if not isinstance(choice, str):
        return False, "no answer"
    probabilities = answer.get("probabilities")
    probability = probabilities.get(choice) if isinstance(probabilities, dict) else None
    shown = choice if not isinstance(probability, (int, float)) else f"{choice} ({probability:.2f})"
    return choice == question["expect"], shown


# ---------------------------------------------------------------------------
# Implementation details
# ---------------------------------------------------------------------------


def _timing(seconds, cold):
    text = f"{seconds:.1f} s"
    if cold:
        return f"{text}, cold"
    if seconds > SLOW_SECONDS:
        return f"{text}, warning: a warm call over {SLOW_SECONDS:g} s"
    return text


def _format(value):
    if value is None:
        return "undecided"
    return json.dumps(value) if isinstance(value, bool) else str(value)


if __name__ == "__main__":
    sys.exit(main())
