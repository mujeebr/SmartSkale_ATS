"""Abstract interface for components that score resumes against job descriptions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import MatchResult


class ResumeMatcher(ABC):
    """Strategy interface for computing a structured resume–JD match."""

    @abstractmethod
    def evaluate(self, jd_text: str, resume_text: str) -> MatchResult:
        """Produce a `MatchResult` for the given job description and resume text."""
