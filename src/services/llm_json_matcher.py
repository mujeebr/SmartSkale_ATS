"""Service-level matcher that asks an LLM for structured JSON output."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ..core.llm.base import LLMClient
from ..core.matching.base import ResumeMatcher
from ..core.matching.models import MatchResult


class LLMJsonResumeMatcher(ResumeMatcher):
    """Resume matcher implementation that delegates scoring to an LLM."""

    def __init__(self, llm: LLMClient) -> None:
        """Initialize the matcher with an injected LLM client."""
        self._llm = llm

    def evaluate(self, jd_text: str, resume_text: str) -> MatchResult:
        """Compare job description and resume text and return a `MatchResult`."""
        prompt = self._build_prompt(jd_text=jd_text, resume_text=resume_text)
        raw = self._llm.generate(prompt)
        payload = self._extract_json(raw)

        match_percentage = int(
            self._coerce_int(payload.get("match_percentage"), default=0)
        )
        summary = str(payload.get("summary") or "").strip() or "No summary returned."
        skills = self._coerce_skills(payload.get("skills"))
        recommendations = str(payload.get("recommendations") or "").strip()
        weaknesses = str(payload.get("weaknesses") or "").strip()

        match_percentage = max(0, min(100, match_percentage))

        return MatchResult(
            match_percentage=match_percentage,
            summary=summary,
            skills=skills,
            recommendations=recommendations,
            weaknesses=weaknesses,
        )

    def _build_prompt(self, jd_text: str, resume_text: str) -> str:
        """Construct the instruction prompt that asks the LLM to respond in JSON."""
        return f"""
You are an AI assistant that matches resumes to job descriptions.

Job Description:
{jd_text}

Resume:
{resume_text}

Tasks:
1. Provide a percentage match (0-100) of how well this resume fits the JD.
2. Provide a short summary of the candidate's profile (max 5 sentences).
3. Provide a list of the candidate's skills that are relevant to the JD.
4. Provide recommendations for the candidate to improve their chances of getting the job.
5. Provide weaknesses of the candidate that are not relevant to the JD.

Respond ONLY in JSON with keys: match_percentage, summary, skills, recommendations, weaknesses.
""".strip()

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Try to parse a JSON object from the LLM response."""
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return {}
            return json.loads(match.group(0))
        except Exception:
            return {}

    def _coerce_skills(self, value: Any) -> List[str]:
        """Normalise the `skills` field into a clean list of strings."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        # comma-separated string fallback
        return [s.strip() for s in str(value).split(",") if s.strip()]

    def _coerce_int(self, value: Any, default: int = 0) -> int:
        """Convert an arbitrary value to an integer, with a default on failure."""
        try:
            return int(float(str(value).strip()))
        except Exception:
            return default
