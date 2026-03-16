"""High-level orchestration service for resume–JD matching."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Sequence

from ..core.matching.base import ResumeMatcher
from ..core.parsing.base import DocumentParser, ParsedDocument


class ResumeMatchingService:
    """Coordinate document parsing and matching into a simple API."""

    def __init__(self, parser: DocumentParser, matcher: ResumeMatcher) -> None:
        """Create a service with the given parser and matcher implementations."""
        self._parser = parser
        self._matcher = matcher

    def match_text(self, jd_text: str, resume_text: str) -> Dict[str, Any]:
        """Evaluate a resume string against a job description string."""
        result = self._matcher.evaluate(jd_text=jd_text, resume_text=resume_text)
        return asdict(result)

    def match_files(
        self, jd_text: str, files: Sequence[tuple[str, bytes]]
    ) -> List[Dict[str, Any]]:
        """Evaluate one or more resume files against a job description string."""
        results: List[Dict[str, Any]] = []
        for filename, data in files:
            parsed: ParsedDocument = self._parser.parse(filename=filename, data=data)
            payload = self.match_text(jd_text=jd_text, resume_text=parsed.text)
            payload["filename"] = parsed.filename
            results.append(payload)
        return results
