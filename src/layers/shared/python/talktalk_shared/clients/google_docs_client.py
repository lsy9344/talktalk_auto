"""Google Docs API client with circuit breaker and retry logic"""
import json
from typing import Any, Dict, List, Optional, cast

from google.oauth2 import service_account  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from talktalk_shared.config import get_google_sa_json
from talktalk_shared.models.kb_chunk import DocumentSection
from talktalk_shared.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)
from talktalk_shared.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDocsClient:
    """Google Docs API client"""

    SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

    def __init__(self) -> None:
        """Initialize Google Docs API client with service account credentials"""
        self.circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                timeout_seconds=60,
                success_threshold=1,
            )
        )
        self._service: Optional[Any] = None

    def _get_service(self) -> Any:
        """
        Get or create Google Docs API service

        Returns:
            Google Docs API service instance
        """
        if self._service is None:
            # Get service account credentials from SSM Parameter Store
            sa_json_str = get_google_sa_json()
            sa_dict = json.loads(sa_json_str)

            credentials = service_account.Credentials.from_service_account_info(
                sa_dict, scopes=self.SCOPES
            )

            self._service = build("docs", "v1", credentials=credentials)
            logger.info("Google Docs API service initialized")

        return self._service

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Get Google Docs document

        Args:
            doc_id: Google Docs document ID

        Returns:
            Document dict containing:
            - documentId: str
            - title: str
            - body: dict - Document content
            - revisionId: str - Revision ID for change detection

        Raises:
            HttpError: If API call fails
        """
        if not self.circuit_breaker.allow_request():
            logger.error("Circuit breaker is open - request blocked", extra={"doc_id": doc_id})
            raise CircuitBreakerOpenError("Google Docs API circuit breaker is open")

        try:
            service = self._get_service()
            doc = cast(Dict[str, Any], service.documents().get(documentId=doc_id).execute())
        except HttpError as e:
            self.circuit_breaker.record_failure()
            logger.error(
                "Failed to fetch document from Google Docs API",
                extra={"doc_id": doc_id, "error": str(e)},
            )
            raise
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(
                "Unexpected error fetching document from Google Docs API",
                extra={"doc_id": doc_id, "error": str(e), "error_type": type(e).__name__},
            )
            raise

        self.circuit_breaker.record_success()
        logger.info(
            "Fetched document",
            extra={
                "doc_id": doc_id,
                "title": doc.get("title"),
                "revision_id": doc.get("revisionId"),
            },
        )
        return doc

    def get_document_text(self, doc_id: str) -> str:
        """
        Get document text content

        Args:
            doc_id: Google Docs document ID

        Returns:
            Plain text extracted from document

        Reference: Story 3.2 AC4 - Extract document text for chunking/embedding
        """
        doc = self.get_document(doc_id)
        return self.extract_text_from_document(doc)

    def extract_text_from_document(self, doc: Dict[str, Any]) -> str:
        """Extract plain text from a Google Docs document dict.

        This avoids extra API calls when the caller already has the document response.
        """
        text_parts: List[str] = []
        body = doc.get("body", {})

        def extract_text_from_element(element: Dict[str, Any]) -> None:
            """Recursively extract text from document element."""
            if "paragraph" in element:
                paragraph = element["paragraph"]
                for elem in paragraph.get("elements", []):
                    text_run = elem.get("textRun")
                    if text_run:
                        content = text_run.get("content", "")
                        text_parts.append(content)

            elif "table" in element:
                table = element["table"]
                for row in table.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        for content in cell.get("content", []):
                            extract_text_from_element(content)

        for content in body.get("content", []):
            extract_text_from_element(content)

        full_text = "".join(text_parts).strip()
        logger.info(
            "Extracted text from document",
            extra={"doc_id": doc.get("documentId"), "text_length": len(full_text)},
        )

        return full_text

    def get_revision_id(self, doc_id: str) -> str:
        """
        Get document revision ID for change detection

        Args:
            doc_id: Google Docs document ID

        Returns:
            Revision ID string

        Reference: Story 3.2 AC3 - Change detection using revisionId
        """
        doc = self.get_document(doc_id)
        revision_id_raw = doc.get("revisionId")
        revision_id = revision_id_raw if isinstance(revision_id_raw, str) else ""

        if not revision_id:
            logger.warning(f"No revisionId found for document: {doc_id}")

        return revision_id

    def get_modified_time(self, doc_id: str) -> Optional[str]:
        """
        Get document modified time

        Args:
            doc_id: Google Docs document ID

        Returns:
            Modified time (ISO 8601 format) or None if not available

        Reference: Story 3.3 Task 1.3 - Extract modifiedTime for updated_at
        """
        doc = self.get_document(doc_id)
        modified_time: object = doc.get("modifiedTime")
        if isinstance(modified_time, str) and modified_time:
            return modified_time
        return None

    def get_document_sections(self, doc_id: str) -> List[DocumentSection]:
        """
        Extract document sections based on headings

        Args:
            doc_id: Google Docs document ID

        Returns:
            List of DocumentSection objects with section_path, text, and heading_level

        Reference: Story 3.3 AC1 - Section-based chunking with heading hierarchy
        """
        doc = self.get_document(doc_id)
        return self.extract_sections_from_document(doc)

    def extract_sections_from_document(self, doc: Dict[str, Any]) -> List[DocumentSection]:
        """Extract sections from a Google Docs document dict.

        This avoids extra API calls when the caller already has the document response.
        """
        body = doc.get("body", {})
        content = body.get("content", [])

        sections: List[DocumentSection] = []
        current_headings: List[str] = []  # Stack of current heading hierarchy
        current_text_parts: List[str] = []
        current_heading_level = 0

        def flush_current_section() -> None:
            """Flush accumulated text as a section"""
            if current_text_parts:
                section_path = " > ".join(current_headings) if current_headings else "(문서 본문)"
                section_text = "".join(current_text_parts).strip()

                if section_text:
                    sections.append(
                        DocumentSection(
                            section_path=section_path,
                            text=section_text,
                            heading_level=current_heading_level,
                        )
                    )
                current_text_parts.clear()

        def extract_text_from_paragraph(paragraph: Dict[str, Any]) -> str:
            """Extract text from a paragraph element"""
            text_parts = []
            for elem in paragraph.get("elements", []):
                text_run = elem.get("textRun")
                if text_run:
                    text_parts.append(text_run.get("content", ""))
            return "".join(text_parts)

        def get_heading_level(paragraph_style: Dict[str, Any]) -> int:
            """Get heading level from paragraph style (1-6), or 0 if not a heading"""
            named_style_type = paragraph_style.get("namedStyleType", "")
            if named_style_type.startswith("HEADING_"):
                try:
                    return int(named_style_type.replace("HEADING_", ""))
                except ValueError:
                    return 0
            return 0

        for element in content:
            if "paragraph" in element:
                paragraph = element["paragraph"]
                paragraph_style = paragraph.get("paragraphStyle", {})
                heading_level = get_heading_level(paragraph_style)
                text = extract_text_from_paragraph(paragraph)

                if heading_level > 0:
                    # This is a heading - flush previous section
                    flush_current_section()

                    # Update heading stack
                    heading_text = text.strip()
                    if heading_text:
                        # Pop headings at same or lower levels
                        while (
                            current_headings
                            and len(current_headings) >= heading_level
                        ):
                            current_headings.pop()

                        # Add new heading
                        current_headings.append(heading_text)
                        current_heading_level = heading_level
                else:
                    # Regular paragraph - accumulate text
                    current_text_parts.append(text)

            elif "table" in element:
                # Extract table content as text
                table = element["table"]
                for row in table.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        for cell_content in cell.get("content", []):
                            if "paragraph" in cell_content:
                                text = extract_text_from_paragraph(
                                    cell_content["paragraph"]
                                )
                                current_text_parts.append(text)

        # Flush final section
        flush_current_section()

        # Fallback: If no sections found, treat entire document as one section
        if not sections:
            full_text = self.extract_text_from_document(doc)
            if full_text:
                sections.append(
                    DocumentSection(
                        section_path="(문서 전체)",
                        text=full_text,
                        heading_level=0,
                    )
                )

        logger.info(
            "Extracted sections from document",
            extra={"doc_id": doc.get("documentId"), "section_count": len(sections)},
        )

        return sections
