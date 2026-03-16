"""Domain model objects used to represent matching results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class MatchResult:
    """Structured output for a resume–JD evaluation."""

    match_percentage: int
    summary: str
    skills: List[str]
    recommendations: str
    weaknesses: str
