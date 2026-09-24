# app/rag/chunking.py
# Purpose: Simple paragraph-based chunking for Product RAG ingestion (spec section 14). This is
#          deliberately NOT a semantic/sentence-boundary-aware chunker — it splits body text on
#          blank lines into paragraphs, then greedily packs paragraphs into chunks up to
#          MAX_CHUNK_CHARS, carrying the last paragraph of each chunk forward into the next as a
#          one-paragraph overlap so a fact split across a chunk boundary is still retrievable
#          from either side. Pure function, no I/O, fully unit-testable without a database.
# Author: CloudDesk Team
# Date: 2026-09-24

MAX_CHUNK_CHARS: int = 900
MIN_CHUNK_CHARS: int = 40


def _split_paragraphs(text: str) -> list[str]:
    """Split on blank lines, dropping empty paragraphs and normalizing whitespace."""
    raw_paragraphs = text.replace("\r\n", "\n").split("\n\n")
    return [p.strip() for p in raw_paragraphs if p.strip()]


def chunk_text(content: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Chunk `content` into paragraph-aligned pieces of at most `max_chars` characters.

    Strategy: accumulate whole paragraphs into a chunk until the next paragraph would push it
    over `max_chars`, then start a new chunk. The last paragraph of each finished chunk is
    repeated as the first paragraph of the next chunk (a one-paragraph overlap), unless a
    single paragraph alone already exceeds `max_chars`, in which case it becomes its own chunk
    verbatim (never silently truncated).

    Returns an empty list for empty/whitespace-only content.
    """
    paragraphs = _split_paragraphs(content)
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        projected_len = current_len + len(paragraph) + (2 if current else 0)
        if current and projected_len > max_chars:
            chunks.append("\n\n".join(current))
            current = [current[-1], paragraph]
            current_len = len(current[-2]) + len(paragraph) + 2
        else:
            current.append(paragraph)
            current_len = projected_len
    if current:
        chunks.append("\n\n".join(current))

    return _merge_tiny_trailing_chunk(chunks)


def _merge_tiny_trailing_chunk(chunks: list[str]) -> list[str]:
    """Fold a too-small final chunk (e.g. just the carried-over overlap paragraph) into the
    previous one, so ingestion never stores a near-empty trailing chunk."""
    if len(chunks) < 2 or len(chunks[-1]) >= MIN_CHUNK_CHARS:
        return chunks
    merged = chunks[:-2] + [chunks[-2] + "\n\n" + chunks[-1]]
    return merged
