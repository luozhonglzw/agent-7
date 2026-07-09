"""Scanned PDF parser using pdf2image + PaddleOCR.

Converts each page to a 300 DPI image, runs OCR, and restores
reading order by sorting text blocks by y-coordinate then x-coordinate.

Usage::

    from app.core.parsers.pdf.scanned_parser import ScannedPDFParser

    parser = ScannedPDFParser()
    doc = parser.parse(Path("scanned_contract.pdf"))
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

logger = logging.getLogger(__name__)


class ScannedPDFParser:
    """OCR-based parser for scanned PDFs.

    Pipeline: PDF → images (pdf2image 300dpi) → OCR (PaddleOCR) →
    sort by y/x coordinates → build sections.
    """

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a scanned PDF with OCR.

        Args:
            file_path: Path to the scanned PDF.

        Returns:
            Parsed document with OCR-extracted text.

        Raises:
            ParserError: If pdf2image or PaddleOCR are not installed.
        """
        images = self._pdf_to_images(file_path)
        ocr_engine = self._get_ocr_engine()

        pages: list[ParsedPage] = []
        sections: list[ParsedSection] = []
        full_text_parts: list[str] = []

        for page_idx, img in enumerate(images):
            page_num = page_idx + 1
            ocr_results = ocr_engine.ocr(img, cls=True)

            # Sort by y-coordinate (top to bottom), then x (left to right)
            sorted_blocks = self._sort_reading_order(ocr_results)

            page_parts: list[str] = []
            for block in sorted_blocks:
                text = block["text"].strip()
                if not text:
                    continue

                page_parts.append(text)
                sections.append(
                    ParsedSection(
                        type="NarrativeText",
                        level=0,
                        text=text,
                        page=page_num,
                        bbox=block.get("bbox"),
                        confidence=block.get("confidence", 0.0),
                    )
                )

            page_text = " ".join(page_parts)
            if page_text.strip():
                pages.append(
                    ParsedPage(
                        page_number=page_num,
                        content=page_text,
                        element_type="NarrativeText",
                        source=file_path.name,
                    )
                )
                full_text_parts.append(page_text)

        full_text = "\n\n".join(full_text_parts)
        title = pages[0].content[:80] if pages else file_path.stem

        # Update first section as Title if on page 1
        if sections and sections[0].page == 1:
            sections[0].type = "Title"
            sections[0].level = 1

        logger.debug(
            "ScannedPDFParser: %s — %d pages, %d chars, avg_conf=%.2f",
            file_path.name, len(pages), len(full_text),
            sum(s.confidence for s in sections) / max(len(sections), 1),
        )

        return ParsedDocument(
            title=title,
            content=full_text,
            pages=pages,
            full_text=full_text,
            sections=sections,
            source_path=str(file_path),
            metadata={
                "type": PDFType.SCANNED.value,
                "parser": "ScannedPDFParser",
                "pages": len(pages),
                "native_pages": 0,
                "scanned_pages": len(pages),
            },
        )

    @staticmethod
    def _pdf_to_images(file_path: Path) -> list:
        """Convert PDF pages to PIL images at 300 DPI.

        Args:
            file_path: Path to the PDF.

        Returns:
            List of PIL Image objects, one per page.

        Raises:
            ParserError: If pdf2image is not installed.
        """
        try:
            from pdf2image import convert_from_path
        except ImportError as exc:
            raise ParserError(
                detail="pdf2image is not installed. Install with: pip install pdf2image",
                file_path=str(file_path),
            ) from exc

        try:
            images = convert_from_path(str(file_path), dpi=300)
        except Exception as exc:
            raise ParserError(
                detail=f"pdf2image conversion failed: {exc}",
                file_path=str(file_path),
            ) from exc

        logger.debug("Converted %d pages to images: %s", len(images), file_path.name)
        return images

    @staticmethod
    def _get_ocr_engine():
        """Initialize PaddleOCR engine.

        Returns:
            PaddleOCR instance.

        Raises:
            ParserError: If PaddleOCR is not installed.
        """
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ParserError(
                detail=(
                    "PaddleOCR is not installed. Install with: "
                    "pip install paddlepaddle paddleocr"
                ),
            ) from exc

        return PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

    @staticmethod
    def _sort_reading_order(ocr_results: list) -> list[dict]:
        """Sort OCR results in natural reading order.

        Groups blocks by approximate y-coordinate (within 10px tolerance)
        then sorts left-to-right within each group.

        Args:
            ocr_results: Raw PaddleOCR output.

        Returns:
            Sorted list of block dicts with text, bbox, confidence.
        """
        if not ocr_results or not ocr_results[0]:
            return []

        blocks: list[dict] = []
        for line in ocr_results[0]:
            bbox_points = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = line[1][0]
            confidence = line[1][1]

            # Convert 4-point bbox to [x0, y0, x1, y1]
            x_coords = [p[0] for p in bbox_points]
            y_coords = [p[1] for p in bbox_points]
            bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

            blocks.append({
                "text": text,
                "bbox": bbox,
                "confidence": confidence,
                "y_center": (bbox[1] + bbox[3]) / 2,
                "x_left": bbox[0],
            })

        # Sort by y-coordinate with tolerance, then x
        _Y_TOLERANCE = 10
        blocks.sort(
            key=lambda b: (
                round(b["y_center"] / _Y_TOLERANCE) * _Y_TOLERANCE,
                b["x_left"],
            )
        )

        return blocks
