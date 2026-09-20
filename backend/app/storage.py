from io import BytesIO
from pathlib import Path
import re

from minio import Minio

from .config import settings


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^\w. -]", "_", name, flags=re.UNICODE) or "document"


class ObjectStorage:
    def __init__(self, client=None):
        self.client = client or Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(settings.minio_bucket):
            self.client.make_bucket(settings.minio_bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(settings.minio_bucket, key, BytesIO(data), len(data), content_type=content_type)

    def get(self, key: str) -> bytes:
        response = self.client.get_object(settings.minio_bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        self.client.remove_object(settings.minio_bucket, key)


object_storage = ObjectStorage()
