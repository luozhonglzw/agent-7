"""Hybrid PDF parser — per-page routing.

Uses the :class:`~app.core.parsers.pdf_classifier.PDFClassifier`
to decide, for each page, whether to use direct text extraction
(native pages) or OCR (scanned pages).  This is the most common
scenario for real-world PDFs that mix digital and scanned content.

Usage::

    from app.core.parsers.pdf.hybrid_parser import HybridPDFParser

    parser = HybridPDFParser()
    doc = parser.parse(Path("mixed_report.pdf"))
"""

import logging
from pathlib import Path

from app.core.parsers.base import (
    ParsedDocument,
    ParsedPage,
    ParsedSection,
    ParserError,
    PDFType,
)
from app.core.parsers.pdf_classifier import PDFClassifier

logger = logging.getLogger(__name__)


class HybridPDFParser:
    """Parse hybrid PDFs by routing each page to the best strategy.

    Native pages are extracted via PyMuPDF; scanned pages are sent
    through PaddleOCR.  The results are merged into a single
    :class:`ParsedDocument`.
    """

    def __init__(self) -> None:
        self._classifier = PDFClassifier()

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a hybrid PDF.

        Args:
            file_path: Path to the hybrid PDF.

        Returns:
            Parsed document with mixed native/OCR content.

        Raises:
            ParserError: If required libraries are not installed.
        """
        try:
            import fitz
        except ImportError as exc:
            raise ParserError(
                detail="PyMuPDF is not installed",
                file_path=str(file_path),
            ) from exc

        # Classify pages
        pdf_type, page_classifications = self._classifier.classify(file_path)

        doc = fitz.open(str(file_path))
        pages: list[ParsedPage] = []
        sections: list[ParsedSection] = []
        full_text_parts: list[str] = []
        native_count = 0
        scanned_count = 0

        try:
            title = (doc.metadata or {}).get("title", "") or ""

            # Lazy-load OCR engine only if needed
            ocr_engine = None

            for pc in page_classifications:
                page_idx = pc.page_number - 1
                if page_idx >= len(doc):
                    continue

                if pc.page_type == "scanned":
                    # OCR this page
                    if ocr_engine is None:
                        ocr_engine = self._get_ocr_engine()
                    page_result = self._ocr_page(
                        doc, page_idx, ocr_engine, file_path.name
                    )
                    scanned_count += 1
                else:
                    # Direct text extraction
                    page_result = self._extract_native_page(
                        doc, page_idx, file_path.name
                    )
                    native_count += 1

                if page_result is not None:
                    pg, sects = page_result
                    pages.append(pg)
                    sections.extend(sects)
                    full_text_parts.append(pg.content)

            if not title:
                title = pages[0].heading or file_path.stem if pages else file_path.stem

        finally:
            doc.close()

        full_text = "\n\n".join(full_text_parts)

        logger.debug(
            "HybridPDFParser: %s — %d pages (native=%d scanned=%d), %d chars",
            file_path.name, len(pages), native_count, scanned_count, len(full_text),
        )

        return ParsedDocument(
            title=title,
            content=full_text,
            pages=pages,
            full_text=full_text,
            sections=sections,
            source_path=str(file_path),
            metadata={
                "type": PDFType.HYBRID.value,
                "parser": "HybridPDFParser",
                "pages": len(pages),
                "native_pages": native_count,
                "scanned_pages": scanned_count,
            },
        )

    def _extract_native_page(
        self, doc: object, page_idx: int, source: str
    ) -> tuple[ParsedPage, list[ParsedSection]] | None:
        """Extract text from a native page via PyMuPDF.

        Args:
            doc: Open PyMuPDF document.
            page_idx: 0-based page index.
            source: Source filename.

        Returns:
            Tuple of (ParsedPage, list of ParsedSection) or None.
        """
        import fitz

        page = doc.load_page(page_idx)
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        parts: list[str] = []
        sects: list[ParsedSection] = []

        for block in blocks:
            if block.get("type") != 0:
                continue
            bbox = block.get("bbox", (0, 0, 0, 0))
            for line in block.get("lines", []):
                span_texts = [s.get("text", "").strip() for s in line.get("spans", [])]
                span_texts = [t for t in span_texts if t]
                if span_texts:
                    line_text = " ".join(span_texts)
                    parts.append(line_text)
                    sects.append(
                        ParsedSection(
                            type="NarrativeText",
                            text=line_text,
                            page=page_idx + 1,
                            bbox=list(bbox),
                            confidence=1.0,
                        )
                    )

        text = " ".join(parts)
        if not text.strip():
            return None

        pg = ParsedPage(
            page_number=page_idx + 1,
            content=text,
            element_type="NarrativeText",
            source=source,
        )
        return pg, sects

    def _ocr_page(
        self, doc: object, page_idx: int, ocr_engine: object, source: str
    ) -> tuple[ParsedPage, list[ParsedSection]] | None:
        """OCR a scanned page.

        Args:
            doc: Open PyMuPDF document.
            page_idx: 0-based page index.
            ocr_engine: PaddleOCR instance.
            source: Source filename.

        Returns:
            Tuple of (ParsedPage, list of ParsedSection) or None.
        """
        import fitz
        from pdf2image import convert_from_path

        # Render single page to image
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(dpi=300)
        img = fitz.utils.pixmap_to_pil(pix) if hasattr(fitz.utils, "pixmap_to_pil") else None

        if img is None:
            # Fallback: save to temp and load
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            pix.save(tmp.name)
            from PIL import Image
            img = Image.open(tmp.name)

        results = ocr_engine.ocr(list(img) if hasattr(img, "__iter__") else img, cls=True)

        if not results or not results[0]:
            return None

        parts: list[str] = []
        sects: list[ParsedSection] = []

        _Y_TOLERANCE = 10
        lines = sorted(
            results[0],
            key=lambda l: (
                round((min(p[1] for p in l[0]) + max(p[1] for p in l[0])) / 2 / _Y_TOLERANCE) * _Y_TOLERANCE,
                min(p[0] for p in l[0]),
            ),
        )

        for line in lines:
            text = line[1][0].strip()
            conf = line[1][1]
            if not text:
                continue

            x_coords = [p[0] for p in line[0]]
            y_coords = [p[1] for p in line[0]]
            bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

            parts.append(text)
            sects.append(
                ParsedSection(
                    type="NarrativeText",
                    text=text,
                    page=page_idx + 1,
                    bbox=bbox,
                    confidence=conf,
                )
            )

        text = " ".join(parts)
        if not text.strip():
            return None

        pg = ParsedPage(
            page_number=page_idx + 1,
            content=text,
            element_type="NarrativeText",
            source=source,
        )
        return pg, sects

    @staticmethod
    def _get_ocr_engine():
        """Initialize PaddleOCR engine."""
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ParserError(
                detail="PaddleOCR is not installed",
            ) from exc
        return PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
