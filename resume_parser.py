"""Compatibility wrapper that exposes a simple text-extraction function."""

from __future__ import annotations

from src.container import get_document_parser


def extract_text(file) -> str:
    """Extract plain text from a file-like object using the shared parser."""
    filename = getattr(file, "name", "document.txt")

    if hasattr(file, "getvalue"):
        data = file.getvalue()
    else:
        data = file.read()

    parser = get_document_parser()
    return parser.parse(filename=filename, data=data).text
