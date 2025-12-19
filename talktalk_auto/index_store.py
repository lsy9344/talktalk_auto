from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import faiss

from .aws_clients import s3_client
from .settings import get_settings


INDEX_FILE_NAME = "index.faiss"
METADATA_FILE_NAME = "metadata.jsonl"


@dataclass
class IndexBundle:
    index: faiss.Index
    metadata: list[dict]
    loaded_at: datetime


_CACHE: dict[str, IndexBundle] = {}


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")
    path = uri[5:]
    bucket, _, key = path.partition("/")
    return bucket, key.rstrip("/")


def _local_dir_for_uri(uri: str) -> Path:
    digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()[:16]
    base = Path("/tmp/talktalk_auto") / digest
    base.mkdir(parents=True, exist_ok=True)
    return base


def load_index_bundle(uri: str, version: str | None = None) -> IndexBundle | None:
    if not uri:
        return None
    settings = get_settings()
    cache_key = f"{uri}:{version or ''}"
    bundle = _CACHE.get(cache_key)
    now = datetime.now(timezone.utc)
    if bundle and bundle.loaded_at + timedelta(seconds=settings.index_cache_ttl_seconds) > now:
        return bundle

    bucket, prefix = _parse_s3_uri(uri)
    local_dir = _local_dir_for_uri(cache_key)
    index_path = local_dir / INDEX_FILE_NAME
    meta_path = local_dir / METADATA_FILE_NAME

    s3 = s3_client()
    s3.download_file(bucket, f"{prefix}/{INDEX_FILE_NAME}", str(index_path))
    s3.download_file(bucket, f"{prefix}/{METADATA_FILE_NAME}", str(meta_path))

    index = faiss.read_index(str(index_path))
    metadata: list[dict] = []
    with meta_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            metadata.append(json.loads(line))

    bundle = IndexBundle(index=index, metadata=metadata, loaded_at=now)
    _CACHE[cache_key] = bundle
    return bundle
