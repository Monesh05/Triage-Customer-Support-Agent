# app/models/knowledge.py
# Purpose: SQLAlchemy ORM models for the Phase 6 Product RAG knowledge base (spec section 14).
#          `KnowledgeDocument` is one row per source document under clouddesk/data/knowledge/,
#          carrying the spec's required metadata fields (document_id, title, category, product,
#          version, source, updated_at). `KnowledgeChunk` is one row per chunk of a document's
#          body text, holding its pgvector embedding. Deliberately separate from
#          app.models.product.Product, which represents a CloudDesk SaaS catalog entity (a
#          plan-included feature), not long-form documentation — overloading it would conflate
#          two unrelated domain concepts.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

_EMBEDDING_DIMENSIONS: int = get_settings().embedding_dimensions


class KnowledgeDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One source document in the Product RAG knowledge base (spec section 14 metadata)."""

    __tablename__ = "knowledge_documents"

    document_id: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    # The document's own last-updated date (from its frontmatter), distinct from
    # TimestampMixin's `updated_at` (DB row bookkeeping, mutated by ingestion re-runs).
    source_updated_at: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One embedded chunk of a KnowledgeDocument's body text."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(_EMBEDDING_DIMENSIONS), nullable=False)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


Index("ix_knowledge_chunks_document_id", KnowledgeChunk.document_id)
