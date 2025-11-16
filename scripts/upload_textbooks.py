#!/usr/bin/env python3
"""Compress and upload MedQuAD textbooks to Appwrite storage."""

from __future__ import annotations

import argparse
import os
import tarfile
import tempfile
from pathlib import Path

from rag.storage.appwrite_storage import AppwriteStorageClient

DEFAULT_SOURCE = Path("books/MedQuAD-master/textbooks")
DEFAULT_ARCHIVE_ID = os.getenv("APPWRITE_TEXTBOOK_ARCHIVE_ID", "medquad-textbooks")


def create_archive(source_dir: Path) -> Path:
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    temp_dir = Path(tempfile.gettempdir())
    archive_path = temp_dir / "medquad-textbooks.tar.gz"
    if archive_path.exists():
        archive_path.unlink()

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(source_dir, arcname=source_dir.name)
    return archive_path


def upload_archive(source_dir: Path, file_id: str) -> None:
    storage = AppwriteStorageClient()
    archive_path = create_archive(source_dir)
    storage.upload_file(file_id=file_id, source_path=archive_path, filename=archive_path.name)
    print(f"Uploaded {archive_path} to Appwrite as file ID '{file_id}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload MedQuAD textbooks directory to Appwrite storage.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Path to the textbooks directory")
    parser.add_argument(
        "--file-id",
        default=DEFAULT_ARCHIVE_ID,
        help="Appwrite file ID to use for the uploaded archive",
    )
    args = parser.parse_args()

    upload_archive(args.source, args.file_id)


if __name__ == "__main__":
    main()
