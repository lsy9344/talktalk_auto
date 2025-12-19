import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np

from talktalk_auto.docs_fetcher import fetch_doc
from talktalk_auto.openai_client import embed_texts


def chunk_paragraphs(paragraphs, chunk_size, overlap):
    chunks = []
    current = ""
    current_section = ""
    for para in paragraphs:
        if para.section:
            current_section = para.section
        if len(current) + len(para.text) + 1 > chunk_size and current:
            chunks.append((current_section, current.strip()))
            current = current[-overlap:] if overlap > 0 else ""
        current += (" " if current else "") + para.text
    if current.strip():
        chunks.append((current_section, current.strip()))
    return chunks


def normalize_embeddings(vectors):
    arr = np.array(vectors, dtype="float32")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError("S3 URI must start with s3://")
    path = uri[5:]
    bucket, _, key = path.partition("/")
    return bucket, key.rstrip("/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-ids", required=True, help="Comma-separated Google Doc IDs")
    parser.add_argument("--output-s3-uri", required=True, help="s3://bucket/prefix")
    parser.add_argument("--chunk-size", type=int, default=int(os.environ.get("CHUNK_SIZE", "800")))
    parser.add_argument("--chunk-overlap", type=int, default=int(os.environ.get("CHUNK_OVERLAP", "100")))
    args = parser.parse_args()

    doc_ids = [item.strip() for item in args.doc_ids.split(",") if item.strip()]
    if not doc_ids:
        raise ValueError("No doc IDs provided")

    chunk_texts = []
    metadata = []
    updated_at = datetime.now(timezone.utc).isoformat()

    for doc_id in doc_ids:
        doc = fetch_doc(doc_id)
        chunks = chunk_paragraphs(doc.paragraphs, args.chunk_size, args.chunk_overlap)
        for idx, (section, text) in enumerate(chunks):
            chunk_id = f"{doc_id}-{idx}"
            chunk_texts.append(text)
            metadata.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "doc_title": doc.title,
                    "section": section,
                    "updated_at": updated_at,
                    "text": text,
                }
            )

    embeddings = embed_texts(chunk_texts)
    vectors = normalize_embeddings(embeddings)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    temp_dir = Path("/tmp/talktalk_index")
    temp_dir.mkdir(parents=True, exist_ok=True)
    index_path = temp_dir / "index.faiss"
    meta_path = temp_dir / "metadata.jsonl"

    faiss.write_index(index, str(index_path))
    with meta_path.open("w", encoding="utf-8") as handle:
        for item in metadata:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    bucket, prefix = parse_s3_uri(args.output_s3_uri)
    import boto3

    s3 = boto3.client("s3")
    s3.upload_file(str(index_path), bucket, f"{prefix}/index.faiss")
    s3.upload_file(str(meta_path), bucket, f"{prefix}/metadata.jsonl")


if __name__ == "__main__":
    main()
