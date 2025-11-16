"""Build a FAISS index from textbook chunks and optionally upload it to Appwrite."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from rag.storage.appwrite_storage import AppwriteStorageClient  # type: ignore
else:
    from .storage.appwrite_storage import AppwriteStorageClient

DEFAULT_SOURCE = Path("books/MedQuAD-master/textbooks/chunk")
DEFAULT_OUTPUT_DIR = Path("artifacts")
DEFAULT_INDEX_ID = os.getenv("APPWRITE_FAISS_INDEX_ID", "faiss-index")
DEFAULT_METADATA_ID = os.getenv("APPWRITE_FAISS_METADATA_ID", "faiss-metadata")


def load_chunks(source_dir: Path) -> List[dict]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Chunk directory not found: {source_dir}")

    documents: List[dict] = []
    for path in sorted(source_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                content = record.get("content")
                title = record.get("title")
                if not content:
                    continue
                documents.append({"title": title or "", "content": content})
    if not documents:
        raise RuntimeError(f"No documents parsed from {source_dir}")
    return documents


def build_index(documents: List[dict], model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    embedder = SentenceTransformer(model_name)
    embeddings = []
    for doc in documents:
        embedding = embedder.encode(doc["content"], normalize_embeddings=True)
        embeddings.append(embedding)
    vectors = np.asarray(embeddings, dtype="float32")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index, vectors.shape[1]


def write_artifacts(index, documents: List[dict], output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "faiss.index"
    metadata_path = output_dir / "metadata.jsonl"

    faiss.write_index(index, str(index_path))
    with metadata_path.open("w", encoding="utf-8") as handle:
        for doc in documents:
            handle.write(json.dumps(doc, ensure_ascii=False) + "\n")
    return index_path, metadata_path


def maybe_upload(index_path: Path, metadata_path: Path, upload: bool) -> None:
    if not upload:
        return
    storage = AppwriteStorageClient()
    storage.upload_file(DEFAULT_INDEX_ID, index_path)
    storage.upload_file(DEFAULT_METADATA_ID, metadata_path)
    print("Uploaded FAISS index + metadata to Appwrite")


def main():
    parser = argparse.ArgumentParser(description="Build FAISS index from textbook chunks")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Directory containing *.jsonl chunks")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for artifacts")
    parser.add_argument("--upload", action="store_true", help="Upload generated files to Appwrite")
    args = parser.parse_args()

    docs = load_chunks(args.source)
    index, _ = build_index(docs)
    index_path, metadata_path = write_artifacts(index, docs, args.output)
    maybe_upload(index_path, metadata_path, args.upload)
    print(f"Wrote index to {index_path} and metadata to {metadata_path}")


if __name__ == "__main__":
    main()
