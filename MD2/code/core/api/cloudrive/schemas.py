from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FileListRequest:
    folder_id: Optional[str] = None
    folder_path: str = "/"
    page: int = 1
    page_size: int = 50
    sort_by: str = "name"
    sort_order: str = "asc"


@dataclass(frozen=True)
class FileListResponse:
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_more: bool


@dataclass(frozen=True)
class UploadRequest:
    filename: str
    content: bytes
    path: str = "/"
    tags: List[str] = field(default_factory=list)
    overwrite: bool = False


@dataclass(frozen=True)
class UploadResponse:
    file_id: str
    name: str
    path: str
    size: int
    content_type: str
    url: str
    created_at: int


@dataclass(frozen=True)
class SearchRequest:
    query: str
    tags: Optional[List[str]] = None
    content_type: Optional[str] = None
    date_from: Optional[int] = None
    date_to: Optional[int] = None
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True)
class SearchResponse:
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class ShareCreateRequest:
    file_id: str
    expire_in: Optional[int] = None
    password: Optional[str] = None
    max_downloads: Optional[int] = None


@dataclass(frozen=True)
class ShareCreateResponse:
    share_id: str
    share_url: str
    expire_at: Optional[int]
    file_name: str


@dataclass(frozen=True)
class FolderCreateRequest:
    name: str
    parent_id: Optional[str] = None
    parent_path: str = "/"


@dataclass(frozen=True)
class FolderCreateResponse:
    folder_id: str
    name: str
    path: str


@dataclass(frozen=True)
class MoveRequest:
    file_id: str
    target_folder_id: Optional[str] = None
    target_path: Optional[str] = None


@dataclass(frozen=True)
class RenameRequest:
    file_id: str
    new_name: str


@dataclass(frozen=True)
class BatchDeleteRequest:
    file_ids: List[str]


@dataclass(frozen=True)
class BatchDeleteResponse:
    success: List[str]
    failed: List[Dict[str, str]]


@dataclass(frozen=True)
class StorageStats:
    total_size: int
    file_count: int
    directory_count: int
    used_percentage: float
    quota: int


@dataclass(frozen=True)
class TreeNode:
    id: str
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    children: Optional[List["TreeNode"]] = None


@dataclass(frozen=True)
class RecentFile:
    file_id: str
    name: str
    path: str
    size: int
    content_type: str
    modified_at: int
    thumbnail_url: Optional[str] = None


@dataclass(frozen=True)
class BreadcrumbItem:
    id: Optional[str]
    name: str
    path: str
