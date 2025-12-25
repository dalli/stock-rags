"""
PDF Parser for Stock Reports

Extracts text, metadata, and structure from financial PDF reports.
"""

import hashlib
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Optional

import pdfplumber
import pypdf
from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class PDFMetadata:
    """PDF document metadata"""

    filename: str
    file_hash: str
    page_count: int
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None


@dataclass
class PDFTable:
    """Extracted table from PDF"""

    page_number: int
    table_index: int
    data: list[list[str]]
    bbox: Optional[tuple[float, float, float, float]] = None


@dataclass
class PDFPage:
    """Single page content"""

    page_number: int
    text: str
    width: float
    height: float
    has_images: bool = False
    tables: list[PDFTable] = None

    def __post_init__(self):
        if self.tables is None:
            self.tables = []


@dataclass
class PDFDocument:
    """Complete parsed PDF document"""

    metadata: PDFMetadata
    pages: list[PDFPage]
    full_text: str
    tables: list[PDFTable] = None

    def __post_init__(self):
        if self.tables is None:
            self.tables = []


class PDFParser:
    """
    PDF parser for stock reports with metadata extraction.

    Features:
    - Text extraction with layout preservation
    - Metadata extraction from PDF properties
    - Page-by-page content structure
    - File hash calculation for deduplication
    """

    def __init__(self) -> None:
        pass

    def calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content for deduplication"""
        return hashlib.sha256(file_content).hexdigest()

    def parse_metadata(self, pdf: PdfReader, filename: str, file_hash: str) -> PDFMetadata:
        """Extract metadata from PDF document"""
        info = pdf.metadata or {}

        # Parse dates safely
        creation_date = None
        modification_date = None

        if info.get("/CreationDate"):
            try:
                creation_date = self._parse_pdf_date(info["/CreationDate"])
            except Exception:
                pass

        if info.get("/ModDate"):
            try:
                modification_date = self._parse_pdf_date(info["/ModDate"])
            except Exception:
                pass

        return PDFMetadata(
            filename=filename,
            file_hash=file_hash,
            page_count=len(pdf.pages),
            title=info.get("/Title"),
            author=info.get("/Author"),
            subject=info.get("/Subject"),
            creator=info.get("/Creator"),
            producer=info.get("/Producer"),
            creation_date=creation_date,
            modification_date=modification_date,
        )

    def _parse_pdf_date(self, date_str: str) -> datetime:
        """
        Parse PDF date format (D:YYYYMMDDHHmmSS)

        PDF date format: D:YYYYMMDDHHmmSSOHH'mm
        Example: D:20231225120000+09'00
        """
        if not date_str:
            return None

        # Remove 'D:' prefix if present
        if date_str.startswith("D:"):
            date_str = date_str[2:]

        # Take first 14 characters (YYYYMMDDHHmmSS)
        date_str = date_str[:14]

        try:
            return datetime.strptime(date_str, "%Y%m%d%H%M%S")
        except ValueError:
            # Try date only format
            return datetime.strptime(date_str[:8], "%Y%m%d")

    def extract_tables_from_page(self, pdf_path: Path, page_num: int) -> list[PDFTable]:
        """
        Extract tables from a specific page using pdfplumber

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)

        Returns:
            List of extracted tables
        """
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_num]
                extracted_tables = page.extract_tables()

                if extracted_tables:
                    for idx, table in enumerate(extracted_tables):
                        # Convert table to list of lists (clean empty cells)
                        cleaned_table = []
                        for row in table:
                            if row:
                                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                                # Only add non-empty rows
                                if any(cell for cell in cleaned_row):
                                    cleaned_table.append(cleaned_row)

                        if cleaned_table:
                            tables.append(
                                PDFTable(
                                    page_number=page_num + 1,  # 1-indexed
                                    table_index=idx,
                                    data=cleaned_table,
                                )
                            )
        except Exception as e:
            logger.warning(f"Failed to extract tables from page {page_num + 1}: {e}")

        return tables

    def extract_page_content(self, pdf_path: Path, page_num: int) -> PDFPage:
        """
        Extract content from a specific page using pdfplumber for better text extraction

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)

        Returns:
            PDFPage with extracted content
        """
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]

            # Extract text with layout preservation
            text = page.extract_text() or ""

            # Get page dimensions
            width = float(page.width)
            height = float(page.height)

            # Check for images
            has_images = len(page.images) > 0

            # Extract tables
            tables = self.extract_tables_from_page(pdf_path, page_num)

            return PDFPage(
                page_number=page_num + 1,  # 1-indexed for user display
                text=text,
                width=width,
                height=height,
                has_images=has_images,
                tables=tables,
            )

    def parse_file(self, file_path: Path) -> PDFDocument:
        """
        Parse PDF file from filesystem path

        Args:
            file_path: Path to PDF file

        Returns:
            PDFDocument with metadata and content
        """
        with open(file_path, "rb") as f:
            file_content = f.read()

        return self.parse_bytes(io.BytesIO(file_content), file_path.name)

    def parse_bytes(self, file_obj: BinaryIO, filename: str) -> PDFDocument:
        """
        Parse PDF from bytes stream (for uploaded files)

        Args:
            file_obj: Binary file-like object
            filename: Original filename

        Returns:
            PDFDocument with metadata and content
        """
        # Read file content for hashing
        file_content = file_obj.read()
        file_obj.seek(0)  # Reset for parsing

        # Calculate file hash
        file_hash = self.calculate_file_hash(file_content)

        # Parse with pypdf for metadata
        pdf_reader = PdfReader(io.BytesIO(file_content))
        metadata = self.parse_metadata(pdf_reader, filename, file_hash)

        # Save to temp file for pdfplumber (it works better with file paths)
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_content)
            tmp_path = Path(tmp_file.name)

        try:
            # Extract page-by-page content
            pages: list[PDFPage] = []
            all_tables: list[PDFTable] = []
            for page_num in range(metadata.page_count):
                page_content = self.extract_page_content(tmp_path, page_num)
                pages.append(page_content)
                all_tables.extend(page_content.tables)

            # Combine full text
            full_text = "\n\n".join(page.text for page in pages)

            return PDFDocument(metadata=metadata, pages=pages, full_text=full_text, tables=all_tables)

        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

    def chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list[dict[str, Any]]:
        """
        Split text into overlapping chunks for vector embedding

        Args:
            text: Full text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Overlap between consecutive chunks

        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text:
            return []

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending within last 100 chars
                last_period = text.rfind(".", start, end)
                last_newline = text.rfind("\n", start, end)
                break_point = max(last_period, last_newline)

                if break_point > start:
                    end = break_point + 1

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    {
                        "text": chunk_text,
                        "chunk_index": chunk_index,
                        "start_char": start,
                        "end_char": end,
                    }
                )
                chunk_index += 1

            # Move to next chunk with overlap
            start = end - overlap if end < len(text) else end

        return chunks

    def table_to_json(self, table: PDFTable) -> dict[str, Any]:
        """
        Convert table to JSON format

        Args:
            table: PDFTable object

        Returns:
            Dictionary with table data in JSON format
        """
        return {
            "page_number": table.page_number,
            "table_index": table.table_index,
            "rows": len(table.data),
            "columns": len(table.data[0]) if table.data else 0,
            "data": table.data,
        }

    def table_to_markdown(self, table: PDFTable) -> str:
        """
        Convert table to Markdown format

        Args:
            table: PDFTable object

        Returns:
            Markdown formatted table string
        """
        if not table.data:
            return ""

        markdown_lines = []
        for i, row in enumerate(table.data):
            # Clean and format cells
            formatted_row = [str(cell).replace("|", "\\|") if cell else "" for cell in row]
            markdown_lines.append("| " + " | ".join(formatted_row) + " |")

            # Add header separator after first row
            if i == 0:
                separator = "| " + " | ".join(["---"] * len(row)) + " |"
                markdown_lines.append(separator)

        return "\n".join(markdown_lines)


# Global parser instance
pdf_parser = PDFParser()
