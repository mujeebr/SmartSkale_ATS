"""Abstract types for parsing raw resume files into structured text."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedDocument:
    """Immutable representation of a parsed document and its source filename."""

    filename: str
    text: str


class DocumentParser(ABC):
    """Contract for components capable of parsing resume file bytes."""

    @abstractmethod
    def parse(self, filename: str, data: bytes) -> ParsedDocument:
        """Parse raw bytes from a file into a `ParsedDocument`."""
