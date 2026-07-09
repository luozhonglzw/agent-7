"""PDF document type classifier.

Examines each page of a PDF to determine whether it is digitally
native (text layer present), scanned (image-only), hybrid, or
complex layout.  The classification result drives the parser
selection in :class:`~app.core.parsers.parser_factory.ParserFactory`.

The classifier is designed for speed (< 100 ms for typical documents)
and only reads structural metadata — it never performs OCR.

Usage::

    from app.core.parsers.pdf_classifier import PDFClassifier

    classifier = PDFClassifier()
    pdf_type, page_details = classifier.classify(Path("report.pdf"))
    print(pdf_type)  # PDFType.NATIVE
"""

import logging
from pathlib import Path

from app.core.parsers.base import PageClassification, PDFType

logger = logging.getLogger(__name__)


class PDFClassifier:
    """Classify a PDF into NATIVE / SCANNED / HYBRID / COMPLEX.

    Classification heuristics (per page):

    * **text_blocks**: Number of text extraction blocks.  A page with
      zero blocks is almost certainly scanned.
    * **text_ratio**: Fraction of the page area covered by text
      bounding boxes.  Very low ratio (< 0.02) on a non-blank page
      indicates an image-only scan.
    * **image_count**: Number of embedded images.  Pages with images
      but no text are likely scanned.

    Document-level decision:

    * 100 % scanned pages  → ``SCANNED``
    * 100 % native pages   → ``NATIVE``
    * > 30 % complex pages → ``COMPLEX``
    * otherwise            → ``HYBRID``
    """

    # Thresholds
    _TEXT_RATIO_SCANNED = 0.02   # Below this → scanned
    _TEXT_BLOCKS_SCANNED = 3     # Below this AND low ratio → scanned
    _COMPLEX_PAGE_THRESHOLD = 0.30  # > 30 % complex pages → COMPLEX

    def classify(
        self, file_path: Path
    ) -> tuple[PDFType, list[PageClassification]]:
        """Classify a PDF file.

        Args:
            file_path: Path to the PDF.

        Returns:
            Tuple of (document type, per-page classification list).

        Raises:
            ImportError: If PyMuPDF is not installed.
            FileNotFoundError: If the file does not exist.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF classification. "
                "Install with: pip install pymupdf"
            ) from exc

        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        doc = fitz.open(str(file_path))
        try:
            return self._classify_document(doc, file_path)
        finally:
            doc.close()

    def _classify_document(
        self, doc: object, file_path: Path
    ) -> tuple[PDFType, list[PageClassification]]:
        """Classify all pages in an open PyMuPDF document.

        Args:
            doc: Open PyMuPDF document.
            file_path: Source path (for logging).

        Returns:
            Tuple of (PDFType, list of PageClassification).
        """
        page_details: list[PageClassification] = []
        scanned_count = 0
        native_count = 0
        complex_count = 0
        total_pages = len(doc)

        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            pc = self._classify_page(page, page_num + 1)
            page_details.append(pc)

            if pc.page_type == "scanned":
                scanned_count += 1
            elif pc.page_type == "complex":
                complex_count += 1
            else:
                native_count += 1

        # Document-level decision
        if scanned_count == total_pages:
            pdf_type = PDFType.SCANNED
        elif native_count == total_pages:
            pdf_type = PDFType.NATIVE
        elif total_pages > 0 and complex_count / total_pages > self._COMPLEX_PAGE_THRESHOLD:
            pdf_type = PDFType.COMPLEX
        else:
            pdf_type = PDFType.HYBRID

        logger.info(
            "PDF classified %s: type=%s pages=%d native=%d scanned=%d complex=%d",
            file_path.name, pdf_type.value, total_pages,
            native_count, scanned_count, complex_count,
        )

        return pdf_type, page_details

    def _classify_page(self, page: object, page_number: int) -> PageClassification:
        """Classify a single page.

        Args:
            page: PyMuPDF page object.
            page_number: 1-based page number.

        Returns:
            PageClassification for this page.
        """
        import fitz

        page_rect = page.rect
        page_area = page_rect.width * page_rect.height

        # Count text blocks
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        text_blocks = [b for b in blocks if b.get("type") == 0]
        text_block_count = len(text_blocks)

        # Calculate text coverage ratio
        text_area = 0.0
        for block in text_blocks:
            bbox = block.get("bbox", (0, 0, 0, 0))
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if w > 0 and h > 0:
                text_area += w * h

        text_ratio = text_area / page_area if page_area > 0 else 0.0

        # Count images
        image_list = page.get_images(full=True)
        image_count = len(image_list)

        # Page-level classification
        if text_block_count <= self._TEXT_BLOCKS_SCANNED and text_ratio < self._TEXT_RATIO_SCANNED:
            if image_count > 0:
                page_type = "scanned"
                confidence = 0.9
            else:
                # Blank or near-blank page
                page_type = "native"
                confidence = 0.5
        elif text_block_count > 20 and image_count > 3:
            # Many text blocks + many images → complex layout
            page_type = "complex"
            confidence = 0.7
        else:
            page_type = "native"
            confidence = 0.85

        return PageClassification(
            page_number=page_number,
            text_blocks=text_block_count,
            text_ratio=round(text_ratio, 4),
            image_count=image_count,
            page_type=page_type,
            confidence=confidence,
        )
