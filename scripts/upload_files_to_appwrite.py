#!/usr/bin/env python3
"""Compress and upload any directory to Appwrite storage."""

from __future__ import annotations

import argparse
import os
import tarfile
import tempfile
from pathlib import Path

try:
    from storage.appwrite_storage import AppwriteStorageClient
except ModuleNotFoundError:
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[1]))
    from storage.appwrite_storage import AppwriteStorageClient  # type: ignore

DEFAULT_SOURCE = Path("textbooks")
DEFAULT_ARCHIVE_ID = os.getenv("APPWRITE_TEXTBOOK_ARCHIVE_ID", "medquad-textbooks")


def create_archive(source_dir: Path, archive_name: str) -> Path:
    source_dir = source_dir.resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    temp_dir = Path(tempfile.gettempdir())
    archive_path = temp_dir / archive_name
    if archive_path.exists():
        archive_path.unlink()

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(source_dir, arcname=source_dir.name)
    return archive_path


def upload_archive(source_dir: Path, file_id: str) -> None:
    storage = AppwriteStorageClient()
    archive_name = f"{file_id}.tar.gz"
    archive_path = create_archive(source_dir, archive_name)
    storage.upload_file(file_id=file_id, source_path=archive_path)
    print(f"Uploaded {archive_path} to Appwrite as file ID '{file_id}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive a directory as tar.gz and upload it to Appwrite storage.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Path to the directory you want to upload")
    parser.add_argument(
        "--file-id",
        default=DEFAULT_ARCHIVE_ID,
        help="Appwrite file ID to use for the uploaded archive",
    )
    args = parser.parse_args()

    upload_archive(args.source, args.file_id)


if __name__ == "__main__":
    main()
