"""
pdf_extractor.py — PDF text extraction wrapper.

Thin wrapper over vendor/pdf_extractor.py. Exposes the single
``extract_text`` function to the pipeline and enforces the error contract
(re-raise with file path).

Vendor source: adapted from
  scholar-agent/src/scholar_agent/engine/academic/image_extractor.py
"""

from vendor.pdf_extractor import extract_text, _clean_text

__all__ = ["extract_text", "_clean_text"]
