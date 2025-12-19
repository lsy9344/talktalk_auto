from __future__ import annotations

import numpy as np

from .index_store import load_index_bundle
from .models import RagChunk, RagResult
from .openai_client import embed_texts
from .settings import get_settings


def _normalize_vector(vec: list[float]) -> np.ndarray:
    arr = np.array(vec, dtype="float32")
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr
    return arr / norm


def _search(bundle, query_vec: np.ndarray, top_k: int) -> list[RagChunk]:
    if bundle is None:
        return []
    scores, indices = bundle.index.search(query_vec.reshape(1, -1), top_k)
    results: list[RagChunk] = []
    for score, idx in zip(scores[0].tolist(), indices[0].tolist()):
        if idx < 0:
            continue
        if idx >= len(bundle.metadata):
            continue
        meta = bundle.metadata[idx]
        results.append(
            RagChunk(
                chunk_id=str(meta.get("chunk_id", idx)),
                doc_id=str(meta.get("doc_id", "")),
                doc_title=str(meta.get("doc_title", "")),
                section=str(meta.get("section", "")),
                updated_at=str(meta.get("updated_at", "")),
                text=str(meta.get("text", "")),
                score=float(score),
            )
        )
    return results


def retrieve(query: str, channel_index_uri: str, channel_index_version: str | None) -> RagResult:
    settings = get_settings()
    embeddings = embed_texts([query])
    query_vec = _normalize_vector(embeddings[0])

    channel_bundle = load_index_bundle(channel_index_uri, channel_index_version)
    common_bundle = load_index_bundle(settings.common_index_s3_uri, "common")

    top_k = max(1, settings.max_context_chunks)
    channel_results = _search(channel_bundle, query_vec, top_k)
    common_results = _search(common_bundle, query_vec, top_k)

    combined = sorted(channel_results + common_results, key=lambda c: c.score, reverse=True)
    combined = combined[: top_k]

    if not combined:
        return RagResult(chunks=[], top1=0.0, topk_avg=0.0)

    top1 = combined[0].score
    topk_avg = sum(chunk.score for chunk in combined) / len(combined)
    return RagResult(chunks=combined, top1=top1, topk_avg=topk_avg)


def build_context(chunks: list[RagChunk]) -> str:
    lines: list[str] = []
    for chunk in chunks:
        lines.append(
            "[" + chunk.chunk_id + "] "
            + f"doc_title={chunk.doc_title} "
            + f"section={chunk.section} "
            + f"updated_at={chunk.updated_at} "
            + f"text={chunk.text}"
        )
    return "\n".join(lines)


def summarize_sources(chunks: list[RagChunk]) -> str:
    items = []
    for chunk in chunks:
        items.append(f"{chunk.doc_title}:{chunk.section}:{chunk.chunk_id}")
    return "; ".join(items)


def chunks_to_citations(chunks: list[RagChunk]) -> list[dict]:
    return [
        {
            "doc_id": chunk.doc_id,
            "doc_title": chunk.doc_title,
            "section": chunk.section,
            "chunk_id": chunk.chunk_id,
        }
        for chunk in chunks
    ]
