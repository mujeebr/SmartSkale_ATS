"""Backwards-compatible helper that exposes a simple evaluation function."""

from __future__ import annotations

from src.container import get_resume_matching_service


def evaluate_resume(jd_text: str, resume_text: str) -> dict:
    """Public API used by older code to score a single resume."""
    svc = get_resume_matching_service()
    return svc.match_text(jd_text=jd_text, resume_text=resume_text)
