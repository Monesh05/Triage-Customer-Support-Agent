# app/rag/documents.py
# Purpose: Loads knowledge-base source documents from clouddesk/data/knowledge/ (spec section
#          14 metadata: document_id, title, category, product, version, source, updated_at).
#          Parses a minimal hand-rolled YAML-frontmatter block (`key: value` lines between two
#          `---` markers) rather than adding a PyYAML/python-frontmatter dependency, since the
#          frontmatter this project writes is intentionally simple flat key/value pairs.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger("clouddesk.rag.documents")

FRONTMATTER_DELIMITER: str = "---"
REQUIRED_FRONTMATTER_FIELDS: tuple[str, ...] = (
    "document_id",
    "title",
    "category",
    "product",
    "version",
    "source",
    "updated_at",
)


class DocumentParseError(Exception):
    """Raised when a knowledge-base source file is missing or malformed frontmatter."""


@dataclass(frozen=True)
class ParsedDocument:
    """A single knowledge-base source document, ready for chunking (spec section 14)."""

    document_id: str
    title: str
    category: str
    product: str
    version: str
    source: str
    updated_at: date
    content: str


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_frontmatter(raw_block: str) -> dict[str, str]:
    """Parse simple `key: value` lines into a dict. Raises DocumentParseError on a bad line."""
    fields: dict[str, str] = {}
    for line in raw_block.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            raise DocumentParseError(f"Malformed frontmatter line (no ':'): {line!r}")
        key, _, value = line.partition(":")
        fields[key.strip()] = _strip_quotes(value.strip())
    return fields


def _parse_markdown_file(path: Path) -> ParsedDocument:
    """Split a knowledge-base markdown file into frontmatter fields + body content."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        raise DocumentParseError(f"{path}: missing opening '---' frontmatter delimiter")
    try:
        closing_index = lines.index(FRONTMATTER_DELIMITER, 1)
    except ValueError as exc:
        raise DocumentParseError(f"{path}: missing closing '---' frontmatter delimiter") from exc

    fields = _parse_frontmatter("\n".join(lines[1:closing_index]))
    missing = [name for name in REQUIRED_FRONTMATTER_FIELDS if name not in fields]
    if missing:
        raise DocumentParseError(f"{path}: missing frontmatter fields {missing}")

    body = "\n".join(lines[closing_index + 1 :]).strip()
    if not body:
        raise DocumentParseError(f"{path}: document body is empty")

    try:
        updated_at = datetime.strptime(fields["updated_at"], "%Y-%m-%d").date()
    except ValueError as exc:
        raise DocumentParseError(f"{path}: updated_at must be YYYY-MM-DD") from exc

    return ParsedDocument(
        document_id=fields["document_id"],
        title=fields["title"],
        category=fields["category"],
        product=fields["product"],
        version=fields["version"],
        source=fields["source"],
        updated_at=updated_at,
        content=body,
    )


def load_knowledge_documents(knowledge_dir: Path) -> list[ParsedDocument]:
    """Load and parse every `*.md` file in `knowledge_dir` into a ParsedDocument.

    Raises:
        DocumentParseError: if any file is missing required frontmatter fields, or if two
            documents declare the same `document_id` (which would make ingestion ambiguous).
    """
    documents: list[ParsedDocument] = []
    seen_ids: set[str] = set()
    for path in sorted(knowledge_dir.glob("*.md")):
        document = _parse_markdown_file(path)
        if document.document_id in seen_ids:
            raise DocumentParseError(f"Duplicate document_id across files: {document.document_id!r}")
        seen_ids.add(document.document_id)
        documents.append(document)
    logger.info("loaded_knowledge_documents count=%d dir=%s", len(documents), knowledge_dir)
    return documents
