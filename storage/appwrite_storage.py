import os
from pathlib import Path
from typing import Optional

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.input_file import InputFile
from appwrite.services.storage import Storage


class AppwriteStorageClient:
    """Lightweight helper around the Appwrite storage SDK."""

    def __init__(
        self,
        bucket_id: Optional[str] = None,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> None:
        self.bucket_id = bucket_id or os.getenv("APPWRITE_BUCKET_ID")
        self.api_key = api_key or os.getenv("APPWRITE_API_KEY")
        self.project_id = project_id or os.getenv("APPWRITE_PROJECT_ID")
        self.endpoint = endpoint or os.getenv("APPWRITE_ENDPOINT", "https://cloud.appwrite.io/v1")

        if not all([self.bucket_id, self.api_key, self.project_id]):
            raise RuntimeError("APPWRITE_BUCKET_ID, APPWRITE_API_KEY, and APPWRITE_PROJECT_ID must be set")

        self.client = Client()
        self.client.set_endpoint(self.endpoint)
        self.client.set_project(self.project_id)
        self.client.set_key(self.api_key)
        self.storage = Storage(self.client)

    def download_file(self, file_id: str, destination: Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = self.storage.get_file_download(self.bucket_id, file_id)
        except AppwriteException as exc:
            raise RuntimeError(f"Failed to download {file_id} from Appwrite: {exc}") from exc

        with destination.open("wb") as handle:
            handle.write(data)
        return destination

    def upload_file(self, file_id: str, source_path: Path, filename: Optional[str] = None) -> None:
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        try:
            # Delete existing object with the same ID to avoid conflicts
            self.storage.delete_file(self.bucket_id, file_id)
        except AppwriteException:
            pass  # Ignore missing file

        upload_file = InputFile.from_path(str(source_path))
        try:
            self.storage.create_file(self.bucket_id, file_id=file_id, file=upload_file)
        except AppwriteException as exc:
            raise RuntimeError(f"Failed to upload {source_path} to Appwrite: {exc}") from exc

    def file_metadata(self, file_id: str):
        try:
            return self.storage.get_file(self.bucket_id, file_id)
        except AppwriteException as exc:
            raise RuntimeError(f"Failed to read metadata for {file_id}: {exc}") from exc
