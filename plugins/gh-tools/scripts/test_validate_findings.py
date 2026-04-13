#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema>=4.20", "pytest>=8.0"]
# ///
"""Tests for validate-findings.py — schema validation, cross-field rules, and file collection."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Import the hyphenated module via importlib
_spec = importlib.util.spec_from_file_location(
    "validate_findings",
    Path(__file__).parent / "validate-findings.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

validate_file = _mod.validate_file
collect_files = _mod.collect_files
main = _mod.main

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SHA = "a" * 40


def _minimal_finding(**overrides):
    """Return a minimal valid finding dict, with optional overrides."""
    base = {
        "path": "src/foo.py",
        "line": 10,
        "body": "Something is wrong here.",
        "severity": "should-fix",
        "source_detail": [
            {"skill": "gs:gh-tools:review", "agent": "gh-review", "agent_label": "gh-review"}
        ],
    }
    base.update(overrides)
    return base


def _minimal_doc(**overrides):
    """Return a minimal valid top-level document dict."""
    base = {
        "source": "gh-review",
        "pr": 42,
        "repo": "owner/repo",
        "head_sha": VALID_SHA,
        "findings": [_minimal_finding()],
    }
    base.update(overrides)
    return base


def _write_json(tmp_path, data, name="findings.json"):
    """Write data as JSON to tmp_path/name and return the path."""
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# Schema validation — valid documents
# ---------------------------------------------------------------------------


class TestValidDocuments:
    def test_minimal_gh_review(self, tmp_path):
        p = _write_json(tmp_path, _minimal_doc())
        assert validate_file(p) == []

    def test_minimal_codex_source(self, tmp_path):
        p = _write_json(tmp_path, _minimal_doc(source="codex"))
        assert validate_file(p) == []

    def test_triage_source_with_input_sources(self, tmp_path):
        doc = _minimal_doc(source="triage", input_sources=["codex", "gh-review"])
        p = _write_json(tmp_path, doc)
        assert validate_file(p) == []

    def test_finding_with_all_optional_fields(self, tmp_path):
        finding = _minimal_finding(
            start_line=5,
            title="Title",
            recommendation="Do this instead.",
            confidence=80,
            source_severity="high",
            side="LEFT",
        )
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        assert validate_file(p) == []

    def test_unmappable_finding(self, tmp_path):
        finding = _minimal_finding(unmappable=True)
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        assert validate_file(p) == []

    def test_empty_findings_array(self, tmp_path):
        p = _write_json(tmp_path, _minimal_doc(findings=[]))
        assert validate_file(p) == []


# ---------------------------------------------------------------------------
# Schema validation — invalid documents
# ---------------------------------------------------------------------------


class TestInvalidDocuments:
    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json")
        errors = validate_file(p)
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

    @pytest.mark.parametrize("field", ["source", "pr", "repo", "head_sha", "findings"])
    def test_missing_required_top_level_field(self, tmp_path, field):
        doc = _minimal_doc()
        del doc[field]
        p = _write_json(tmp_path, doc)
        errors = validate_file(p)
        assert any(field in e for e in errors)

    def test_extra_top_level_property_rejected(self, tmp_path):
        doc = _minimal_doc(extra_field="nope")
        p = _write_json(tmp_path, doc)
        errors = validate_file(p)
        assert any("additional" in e.lower() or "extra_field" in e for e in errors)

    def test_invalid_repo_pattern(self, tmp_path):
        p = _write_json(tmp_path, _minimal_doc(repo="no-slash"))
        errors = validate_file(p)
        assert any("repo" in e for e in errors)

    def test_invalid_head_sha(self, tmp_path):
        p = _write_json(tmp_path, _minimal_doc(head_sha="short"))
        errors = validate_file(p)
        assert any("head_sha" in e for e in errors)

    def test_invalid_severity_enum(self, tmp_path):
        finding = _minimal_finding(severity="critical")
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        errors = validate_file(p)
        assert any("severity" in e for e in errors)

    def test_empty_source_detail_array(self, tmp_path):
        finding = _minimal_finding(source_detail=[])
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        errors = validate_file(p)
        assert any("source_detail" in e for e in errors)

    def test_extra_finding_property_rejected(self, tmp_path):
        finding = _minimal_finding(bogus="value")
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        errors = validate_file(p)
        assert any("additional" in e.lower() or "bogus" in e for e in errors)

    def test_pr_must_be_positive_integer(self, tmp_path):
        p = _write_json(tmp_path, _minimal_doc(pr=0))
        errors = validate_file(p)
        assert any("pr" in e for e in errors)

    def test_line_must_be_positive(self, tmp_path):
        finding = _minimal_finding(line=0)
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        errors = validate_file(p)
        assert any("line" in e for e in errors)

    def test_unmappable_must_be_true(self, tmp_path):
        finding = _minimal_finding(unmappable=False)
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        errors = validate_file(p)
        assert any("unmappable" in e for e in errors)


# ---------------------------------------------------------------------------
# Cross-field rules
# ---------------------------------------------------------------------------


class TestCrossFieldRules:
    def test_start_line_greater_than_line(self, tmp_path):
        finding = _minimal_finding(start_line=20, line=10)
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        errors = validate_file(p)
        assert any("start_line" in e and "line" in e for e in errors)

    def test_start_line_equal_to_line_is_ok(self, tmp_path):
        finding = _minimal_finding(start_line=10, line=10)
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        assert validate_file(p) == []

    def test_start_line_less_than_line_is_ok(self, tmp_path):
        finding = _minimal_finding(start_line=5, line=10)
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        assert validate_file(p) == []

    def test_side_right_rejected(self, tmp_path):
        finding = _minimal_finding(side="RIGHT")
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        errors = validate_file(p)
        assert any("RIGHT" in e for e in errors)

    def test_side_invalid_value_rejected(self, tmp_path):
        finding = _minimal_finding(side="BOTH")
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        errors = validate_file(p)
        assert any("BOTH" in e for e in errors)

    def test_side_left_accepted(self, tmp_path):
        finding = _minimal_finding(side="LEFT")
        p = _write_json(tmp_path, _minimal_doc(findings=[finding]))
        assert validate_file(p) == []

    def test_triage_without_input_sources(self, tmp_path):
        doc = _minimal_doc(source="triage")
        doc.pop("input_sources", None)
        p = _write_json(tmp_path, doc)
        errors = validate_file(p)
        assert any("input_sources" in e for e in errors)

    def test_non_triage_without_input_sources_is_ok(self, tmp_path):
        doc = _minimal_doc(source="gh-review")
        doc.pop("input_sources", None)
        p = _write_json(tmp_path, doc)
        assert validate_file(p) == []


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------


class TestCollectFiles:
    def test_single_file(self, tmp_path):
        p = _write_json(tmp_path, _minimal_doc(), name="a.json")
        assert collect_files([str(p)]) == [p]

    def test_directory_collects_sorted_json(self, tmp_path):
        b = _write_json(tmp_path, _minimal_doc(), name="b.json")
        a = _write_json(tmp_path, _minimal_doc(), name="a.json")
        result = collect_files([str(tmp_path)])
        assert result == [a, b]

    def test_directory_ignores_non_json(self, tmp_path):
        _write_json(tmp_path, _minimal_doc(), name="good.json")
        (tmp_path / "readme.txt").write_text("not json")
        result = collect_files([str(tmp_path)])
        assert len(result) == 1

    def test_nonexistent_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="nope"):
            collect_files([str(tmp_path / "nope")])

    def test_empty_directory(self, tmp_path):
        result = collect_files([str(tmp_path)])
        assert result == []


class TestMain:
    """Tests for the main() CLI entry point."""

    def test_no_args_exits_2(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["validate-findings.py"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_nonexistent_path_exits_2(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "argv", ["validate-findings.py", str(tmp_path / "nope")])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_empty_directory_exits_2(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "argv", ["validate-findings.py", str(tmp_path)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_valid_file_exits_0(self, monkeypatch, tmp_path):
        p = _write_json(tmp_path, _minimal_doc())
        monkeypatch.setattr(sys, "argv", ["validate-findings.py", str(p)])
        # main() returns None on success (no sys.exit call)
        main()

    def test_invalid_file_exits_1(self, monkeypatch, tmp_path):
        doc = _minimal_doc()
        del doc["source"]
        p = _write_json(tmp_path, doc)
        monkeypatch.setattr(sys, "argv", ["validate-findings.py", str(p)])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
