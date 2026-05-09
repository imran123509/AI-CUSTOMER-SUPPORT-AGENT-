"""RAG: ingestion, embedding, retrieval over ChromaDB.

All collections are namespaced as `org_{organization_id}` to enforce
multi-tenant isolation.
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from pathlib import Path
from typing import Iterable, List
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services import gemini_client

logger = get_logger(__name__)
settings = get_settings()

_chroma_client: chromadb.HttpClient | None = None


def _client() -> chromadb.HttpClient:
    global _chroma_client
    if _chroma_client is None:
        # parse host/port from URL
        from urllib.parse import urlparse

        u = urlparse(settings.chroma_http_url)
        _chroma_client = chromadb.HttpClient(
            host=u.hostname or "localhost",
            port=u.port or 8000,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def _collection_name(organization_id: UUID | str) -> str:
    return f"org_{str(organization_id).replace('-', '')}"


def _get_collection(organization_id: UUID | str):
    name = _collection_name(organization_id)
    return _client().get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


# ----------------------------- ingestion ------------------------------------
def chunk_text(text: str, *, chunk_size: int | None = None, overlap: int | None = None) -> List[str]:
    """Simple character-window chunker.  Replace with token-aware later."""
    chunk_size = chunk_size or settings.rag_chunk_size
    overlap = overlap or settings.rag_chunk_overlap
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def parse_file(path: str, mime_type: str, filename: str) -> str:
    """Extract text from supported file types."""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "pdf" or mime_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    if ext == "docx" or "wordprocessingml" in mime_type:
        import docx

        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    if ext in ("txt", "md"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    if ext == "csv":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            rows = ["\t".join(row) for row in reader]
        return "\n".join(rows)
    raise ValueError(f"Unsupported file type: {ext or mime_type}")


async def index_document(
    *,
    organization_id: UUID,
    document_id: UUID,
    document_name: str,
    text: str,
) -> List[tuple[str, str, int]]:
    """Chunk + embed + persist into Chroma. Returns [(chroma_id, content, tokens)]."""
    chunks = chunk_text(text)
    if not chunks:
        return []
    embeddings = await gemini_client.embed(chunks)
    collection = _get_collection(organization_id)
    ids: List[str] = []
    metadatas: List[dict] = []
    out: List[tuple[str, str, int]] = []
    for seq, (chunk, vec) in enumerate(zip(chunks, embeddings)):
        chroma_id = f"{document_id}:{seq}"
        ids.append(chroma_id)
        metadatas.append(
            {
                "document_id": str(document_id),
                "document_name": document_name,
                "seq": seq,
            }
        )
        out.append((chroma_id, chunk, len(chunk.split())))
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return out


async def remove_document(organization_id: UUID, document_id: UUID) -> None:
    collection = _get_collection(organization_id)
    collection.delete(where={"document_id": str(document_id)})


# ----------------------------- retrieval ------------------------------------
async def semantic_search(
    *,
    organization_id: UUID,
    query: str,
    top_k: int | None = None,
) -> List[dict]:
    if not query.strip():
        return []
    top_k = top_k or settings.rag_top_k
    embedding = (await gemini_client.embed([query]))[0]
    collection = _get_collection(organization_id)
    res = collection.query(query_embeddings=[embedding], n_results=top_k)
    out: List[dict] = []
    if not res or not res.get("ids"):
        return out
    ids = res["ids"][0]
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    distances = res.get("distances", [[0] * len(ids)])[0]
    for i, _id in enumerate(ids):
        out.append(
            {
                "chunk_id": _id,
                "document_id": metas[i].get("document_id"),
                "document_name": metas[i].get("document_name", "doc"),
                "score": 1.0 - float(distances[i]),
                "content": docs[i],
            }
        )
    return out


# ----------------------------- file utilities -------------------------------
def safe_save_upload(*, raw_bytes: bytes, original_name: str) -> tuple[str, str]:
    """Save an uploaded file under settings.upload_dir, returning (storage_path, sanitized_name)."""
    base_name = Path(original_name).name  # strip directory components
    if not base_name:
        raise ValueError("Empty filename")
    ext = Path(base_name).suffix.lower().lstrip(".")
    if ext not in settings.allowed_extension_set:
        raise ValueError(f"Disallowed extension: {ext}")
    if len(raw_bytes) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"File too large; max {settings.max_upload_mb} MB")

    os.makedirs(settings.upload_dir, exist_ok=True)
    safe = f"{uuid.uuid4().hex}_{base_name}"
    target = os.path.join(settings.upload_dir, safe)
    with open(target, "wb") as f:
        f.write(raw_bytes)
    return target, base_name


def iter_text_records(rows: Iterable[dict]) -> str:
    sio = io.StringIO()
    for r in rows:
        sio.write("\t".join(f"{k}={v}" for k, v in r.items()) + "\n")
    return sio.getvalue()
