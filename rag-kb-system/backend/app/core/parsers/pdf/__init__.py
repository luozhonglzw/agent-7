"""PDF-specific parsers for different document types.

Each parser is optimized for a particular PDF category:

* :class:`NativePDFParser`  — digital text extraction via PyMuPDF
* :class:`ScannedPDFParser` — OCR via PaddleOCR
* :class:`HybridPDFParser`  — per-page routing (native ↔ scanned)
* :class:`ComplexPDFParser` — deep layout analysis via Docling
"""

from app.core.parsers.pdf.native_parser import NativePDFParser
from app.core.parsers.pdf.scanned_parser import ScannedPDFParser
from app.core.parsers.pdf.hybrid_parser import HybridPDFParser
from app.core.parsers.pdf.complex_parser import ComplexPDFParser

__all__ = [
    "NativePDFParser",
    "ScannedPDFParser",
    "HybridPDFParser",
    "ComplexPDFParser",
]
