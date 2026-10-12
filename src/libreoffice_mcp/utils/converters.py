# converters.py - Format detection and document-type classification helpers.
from __future__ import annotations

from pathlib import Path

# Map of extension -> canonical document kind used for routing tools.
DOCX = "docx"
ODT = "odt"
PPTX = "pptx"

DOCUMENT_TYPES = {DOCX: {".docx"}, ODT: {".odt"}, PPTX: {".pptx"}}

# Writer-centric extensions that are converted to .docx for editing.
_WRITER_EXTENSIONS = {".odt", ".doc", ".rtf", ".txt", ".html"}


def detect_extension(path: str | Path) -> str:
    """Return the lowercase file extension including the dot (e.g. '.odt')."""
    return Path(path).suffix.lower()


def document_kind(path: str | Path) -> str | None:
    """Return the canonical doc kind ('docx' | 'odt' | 'pptx') or None.

    Unknown/legacy extensions map to None; callers decide conversion.
    """
    ext = detect_extension(path)
    for kind, extensions in DOCUMENT_TYPES.items():
        if ext in extensions:
            return kind
    return None


def is_writer_file(path: str | Path) -> bool:
    """True if the file is a Writer doc (native or conversion-friendly)."""
    return detect_extension(path) in _WRITER_EXTENSIONS


def is_presentation_file(path: str | Path) -> bool:
    """True if the file is a presentation (.pptx or legacy .ppt)."""
    return detect_extension(path) in {".pptx", ".ppt"}


def needs_conversion_to_editable(path: str | Path) -> str | None:
    """Return the .docx target extension if this file needs conversion first.

    Editing tools operate on .docx/.-pptx natively. Legacy or interchange
    formats (.odt, .doc, .rtf, .txt, .ppt) must be converted by LibreOffice
    before python-docx/python-pptx can touch them.
    """
    ext = detect_extension(path)
    if ext in {".docx", ".pptx"}:
        return None
    if ext in {".odt", ".doc", ".rtf", ".txt", ".html"}:
        return "docx"  # Writer-family -> edit as .docx
    if ext == ".ppt":
        return "pptx"  # legacy presentation -> edit as .pptx
    return None