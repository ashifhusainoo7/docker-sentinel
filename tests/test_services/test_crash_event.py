import pytest

from src.schemas.crash_event import CrashAnalysis


def test_crash_analysis_schema():
    analysis = CrashAnalysis(
        restart_likely_fixes=True,
        root_cause="Out of memory — container exceeded 512MB limit",
        severity="high",
        category="oom",
        suggestions=["Increase memory limit to 1GB", "Check for memory leaks"],
        confidence=0.92,
    )
    assert analysis.restart_likely_fixes is True
    assert analysis.severity == "high"
    assert len(analysis.suggestions) == 2


def test_crash_analysis_validation():
    with pytest.raises(Exception):
        CrashAnalysis()  # Missing required fields
