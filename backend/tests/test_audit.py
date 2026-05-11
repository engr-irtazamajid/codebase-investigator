"""Tests for audit JSON parsing and verdict normalisation."""
import json

import pytest

from app.services.audit import _parse_audit_json


class TestParseAuditJson:
    def _make_json(self, **overrides) -> str:
        base = {
            "trust_score": 8,
            "verdict": "reliable",
            "flags": [],
            "summary": "The answer is well-grounded.",
        }
        base.update(overrides)
        return json.dumps(base)

    def test_valid_json_parses_correctly(self):
        result = _parse_audit_json(self._make_json())
        assert result.trust_score == 8
        assert result.verdict == "reliable"
        assert result.flags == []
        assert "well-grounded" in result.summary

    def test_flags_parsed(self):
        payload = self._make_json(
            flags=[
                {"type": "overconfident", "description": "No citation for claim", "severity": "medium"}
            ]
        )
        result = _parse_audit_json(payload)
        assert len(result.flags) == 1
        assert result.flags[0].type == "overconfident"
        assert result.flags[0].severity == "medium"

    def test_trust_score_clamped_to_zero(self):
        result = _parse_audit_json(self._make_json(trust_score=-5))
        assert result.trust_score == 0

    def test_trust_score_clamped_to_ten(self):
        result = _parse_audit_json(self._make_json(trust_score=99))
        assert result.trust_score == 10

    def test_unknown_verdict_normalised_to_caution(self):
        result = _parse_audit_json(self._make_json(verdict="unknown_value"))
        assert result.verdict == "caution"

    def test_json_embedded_in_markdown_fences(self):
        raw = "```json\n" + self._make_json(trust_score=7, verdict="caution") + "\n```"
        result = _parse_audit_json(raw)
        assert result.trust_score == 7
        assert result.verdict == "caution"

    def test_json_with_leading_text(self):
        raw = "Here is my audit:\n\n" + self._make_json(verdict="unreliable")
        result = _parse_audit_json(raw)
        assert result.verdict == "unreliable"

    def test_no_json_raises_value_error(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            _parse_audit_json("This is just plain text with no JSON.")

    def test_all_verdict_values_accepted(self):
        for verdict in ("reliable", "caution", "unreliable"):
            result = _parse_audit_json(self._make_json(verdict=verdict))
            assert result.verdict == verdict
