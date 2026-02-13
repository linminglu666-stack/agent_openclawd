from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class StorageType(Enum):
    LOCAL = "local"
    S3 = "s3"
    MINIO = "minio"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class FileInfo:
    name: str
    path: str
    size: int
    is_directory: bool
    modified_at: int
    content_type: Optional[str] = None
    checksum: Optional[str] = None


@dataclass(frozen=True)
class FileMetadata:
    file_id: str
    name: str
    path: str
    size: int
    content_type: str
    checksum: str
    created_at: int
    updated_at: int
    owner_id: str
    is_directory: bool
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UploadResult:
    file_id: str
    name: str
    path: str
    size: int
    content_type: str
    url: str


@dataclass(frozen=True)
class DownloadResult:
    content: bytes
    content_type: str
    filename: str
    size: int


class StorageProvider(Protocol):
    async def read(self, path: str) -> bytes:
        ...
    
    async def write(self, path: str, data: bytes) -> str:
        ...
    
    async def delete(self, path: str) -> bool:
        ...
    
    async def exists(self, path: str) -> bool:
        ...
    
    async def list(self, prefix: str) -> List[FileInfo]:
        ...
    
    async def move(self, src: str, dst: str) -> bool:
        ...
    
    async def copy(self, src: str, dst: str) -> bool:
        ...
    
    async def get_metadata(self, path: str) -> Optional[FileMetadata]:
        ...
    
    async def get_url(self, path: str, expires: int = 3600) -> str:
        ...
    
    async def create_directory(self, path: str) -> bool:
        ...
    
    async def delete_directory(self, path: str, force: bool = False) -> bool:
        ...


class BaseStorageProvider(ABC):
    def __init__(self, root_path: str):
        self._root_path = root_path.rstrip("/")
    
    def _normalize_path(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{self._root_path}/{path}" if path else self._root_path
    
    def _get_content_type(self, filename: str) -> str:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        content_types = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "ppt": "application/vnd.ms-powerpoint",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "txt": "text/plain",
            "csv": "text/csv",
            "json": "application/json",
            "xml": "application/xml",
            "zip": "application/zip",
            "tar": "application/x-tar",
            "gz": "application/gzip",
            "mp3": "audio/mpeg",
            "mp4": "video/mp4",
            "avi": "video/x-msvideo",
        }
        return content_types.get(ext, "application/octet-stream")
    
    def _compute_checksum(self, data: bytes) -> str:
        import hashlib
        return hashlib.sha256(data).hexdigest()
    
    def _generate_file_id(self) -> str:
        import uuid
        return str(uuid.uuid4())
