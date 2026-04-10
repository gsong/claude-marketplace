#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4.20"]
# ///
"""Validate findings JSON files against the common review findings schema."""

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

FINDINGS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["source", "pr", "repo", "head_sha", "findings"],
    "additionalProperties": False,
    "properties": {
        "source": {"type": "string", "minLength": 1},
        "pr": {"type": "integer", "minimum": 1},
        "repo": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
        "head_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
        "input_sources": {"type": "array", "items": {"type": "string"}},
        "findings": {"type": "array", "items": {"$ref": "#/$defs/finding"}},
    },
    "$defs": {
        "finding": {
            "type": "object",
            "required": ["path", "line", "body", "severity", "source_detail"],
            "additionalProperties": False,
            "properties": {
                "path": {"type": "string", "minLength": 1},
                "line": {"type": "integer", "minimum": 1},
                "start_line": {"type": "integer", "minimum": 1},
                "body": {"type": "string", "minLength": 1, "maxLength": 65536},
                "severity": {"type": "string", "enum": ["must-fix", "should-fix", "nit"]},
                "source_severity": {"type": "string"},
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "title": {"type": "string"},
                "recommendation": {"type": "string"},
                "side": {"type": "string", "enum": ["LEFT"]},
                "source_detail": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"$ref": "#/$defs/source_detail_entry"},
                },
            },
        },
        "source_detail_entry": {
            "type": "object",
            "required": ["skill", "agent", "agent_label"],
            "additionalProperties": False,
            "properties": {
                "skill": {"type": "string", "minLength": 1},
                "agent": {"type": "string", "minLength": 1},
                "agent_label": {"type": "string", "minLength": 1},
            },
        },
    },
}

validator = Draft202012Validator(FINDINGS_SCHEMA)


def validate_file(path: Path) -> list[str]:
    """Validate a single findings JSON file. Returns list of error messages."""
    errors: list[str] = []

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    # JSON Schema validation — collect all errors
    for error in validator.iter_errors(data):
        json_path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[{json_path}] {error.message}")

    # Cross-field: start_line <= line
    if isinstance(data.get("findings"), list):
        for i, finding in enumerate(data["findings"]):
            if (
                isinstance(finding, dict)
                and "start_line" in finding
                and "line" in finding
                and isinstance(finding["start_line"], int)
                and isinstance(finding["line"], int)
                and finding["start_line"] > finding["line"]
            ):
                errors.append(
                    f"[findings.{i}] start_line ({finding['start_line']}) "
                    f"must be <= line ({finding['line']})"
                )

    # Cross-field: triage requires input_sources
    if data.get("source") == "triage" and "input_sources" not in data:
        errors.append(
            '[root] source is "triage" but required field "input_sources" is missing'
        )

    return errors


def collect_files(args: list[str]) -> list[Path]:
    """Resolve CLI args to a list of JSON file paths."""
    files: list[Path] = []
    for arg in args:
        p = Path(arg)
        if p.is_dir():
            files.extend(sorted(p.glob("*.json")))
        elif p.is_file():
            files.append(p)
        else:
            raise FileNotFoundError(f"path not found: {arg}")
    return files


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: validate-findings.py <file-or-dir> [...]", file=sys.stderr)
        sys.exit(2)

    try:
        files = collect_files(sys.argv[1:])
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    if not files:
        print("Error: no JSON files found in the given paths", file=sys.stderr)
        sys.exit(2)

    any_errors = False
    for path in files:
        errors = validate_file(path)
        if errors:
            any_errors = True
            print(f"\n{path}:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)

    if any_errors:
        sys.exit(1)

    print(f"OK: {len(files)} file(s) validated successfully.")


if __name__ == "__main__":
    main()
