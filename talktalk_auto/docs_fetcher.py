from __future__ import annotations

from dataclasses import dataclass

from googleapiclient.discovery import build

from .google_auth import get_google_credentials


_DOCS_SERVICE = None


@dataclass
class DocParagraph:
    section: str
    text: str


@dataclass
class DocContent:
    doc_id: str
    title: str
    paragraphs: list[DocParagraph]


def _get_service():
    global _DOCS_SERVICE
    if _DOCS_SERVICE is None:
        creds = get_google_credentials()
        _DOCS_SERVICE = build("docs", "v1", credentials=creds, cache_discovery=False)
    return _DOCS_SERVICE


def fetch_doc(doc_id: str) -> DocContent:
    service = _get_service()
    doc = service.documents().get(documentId=doc_id).execute()
    title = doc.get("title", "")
    content = doc.get("body", {}).get("content", [])

    paragraphs: list[DocParagraph] = []
    current_section = ""
    for block in content:
        paragraph = block.get("paragraph")
        if not paragraph:
            continue
        elements = paragraph.get("elements", [])
        text_parts = []
        for elem in elements:
            text_run = elem.get("textRun")
            if not text_run:
                continue
            text_parts.append(text_run.get("content", ""))
        text = "".join(text_parts).strip()
        if not text:
            continue
        style = paragraph.get("paragraphStyle", {})
        named_style = style.get("namedStyleType", "")
        if named_style.startswith("HEADING"):
            current_section = text
            continue
        paragraphs.append(DocParagraph(section=current_section, text=text))

    return DocContent(doc_id=doc_id, title=title, paragraphs=paragraphs)
