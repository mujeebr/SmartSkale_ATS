"""Simple dependency container for wiring core services and infrastructure."""

from __future__ import annotations

from functools import lru_cache

from .core.llm.base import LLMClient
from .core.matching.base import ResumeMatcher
from .core.parsing.base import DocumentParser
from .infrastructure.llm.openai_client import OpenAIChatCompletionsClient
from .infrastructure.parsing.document_parser import DefaultDocumentParser
from .services.llm_json_matcher import LLMJsonResumeMatcher
from .services.resume_matcher import ResumeMatchingService


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """Return a singleton OpenAI-based LLM client."""
    return OpenAIChatCompletionsClient(model="gpt-4o-mini")


@lru_cache(maxsize=1)
def get_document_parser() -> DocumentParser:
    """Return a singleton document parser for PDF/DOCX/TXT content."""
    return DefaultDocumentParser()


@lru_cache(maxsize=1)
def get_resume_matcher() -> ResumeMatcher:
    """Return a singleton matcher that delegates scoring to the LLM."""
    return LLMJsonResumeMatcher(llm=get_llm_client())


@lru_cache(maxsize=1)
def get_resume_matching_service() -> ResumeMatchingService:
    """Return a singleton high-level service used by APIs and UI."""
    return ResumeMatchingService(
        parser=get_document_parser(), matcher=get_resume_matcher()
    )
