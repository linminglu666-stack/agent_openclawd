from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..storage.provider import (
    StorageProvider,
    FileInfo,
    FileMetadata,
)
from .output_router import OutputRouter, OutputContext, OutputTarget


@dataclass(frozen=True)
class ShareOptions:
    expire_in: Optional[int] = None
    password: Optional[str] = None
    max_downloads: Optional[int] = None


@dataclass(frozen=True)
class ShareInfo:
    share_id: str
    file_id: str
    file_name: str
    created_at: int
    expire_at: Optional[int]
    password: Optional[str]
    max_downloads: Optional[int]
    download_count: int = 0


@dataclass(frozen=True)
class SearchFilters:
    tags: Optional[List[str]] = None
    content_type: Optional[str] = None
    date_from: Optional[int] = None
    date_to: Optional[int] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None


@dataclass(frozen=True)
class VersionInfo:
    version_id: str
    file_id: str
    version_number: int
    created_at: int
    size: int
    checksum: str
    description: Optional[str] = None


class CloudDriveService:
    def __init__(
        self,
        storage: StorageProvider,
        output_router: Optional[OutputRouter] = None,
        max_versions: int = 10,
    ):
        self._storage = storage
        self._output_router = output_router or OutputRouter()
        self._max_versions = max_versions
        self._metadata_store: Dict[str, FileMetadata] = {}
        self._share_store: Dict[str, ShareInfo] = {}
        self._version_store: Dict[str, List[VersionInfo]] = {}
        self._file_index: Dict[str, List[str]] = {}
    
    async def save_output(
        self,
        content: bytes,
        filename: str,
        context: Optional[OutputContext] = None,
    ) -> FileMetadata:
        route = self._output_router.route(filename, context)
        
        if route.target == OutputTarget.CLOUDRIVE:
            return await self.upload(content, filename, route.path)
        elif route.target == OutputTarget.WORKSPACE:
            return await self._save_to_target(content, filename, "workspace")
        elif route.target == OutputTarget.DATASETS:
            return await self._save_to_target(content, filename, "datasets")
        elif route.target == OutputTarget.ANALYSIS:
            return await self._save_to_target(content, filename, "analysis")
        else:
            return await self.upload(content, filename, "/")
    
    async def _save_to_target(
        self,
        content: bytes,
        filename: str,
        target: str,
    ) -> FileMetadata:
        path = f"{target}/{filename}"
        return await self.upload(content, filename, path)
    
    async def upload(
        self,
        content: bytes,
        filename: str,
        path: str = "/",
        tags: Optional[List[str]] = None,
    ) -> FileMetadata:
        file_path = self._normalize_path(path, filename)
        
        file_id = await self._storage.write(file_path, content)
        
        checksum = self._compute_checksum(content)
        
        now = int(datetime.now(tz=timezone.utc).timestamp())
        metadata = FileMetadata(
            file_id=file_id or self._generate_id(),
            name=filename,
            path=file_path,
            size=len(content),
            content_type=self._detect_content_type(filename),
            checksum=checksum,
            created_at=now,
            updated_at=now,
            owner_id=self._get_current_user(),
            is_directory=False,
            tags=tags or [],
            metadata={},
        )
        
        self._metadata_store[metadata.file_id] = metadata
        
        await self._create_version(metadata.file_id, content, "Initial upload")
        
        self._index_file(metadata)
        
        return metadata
    
    async def download(self, file_id: str) -> bytes:
        metadata = await self.get_metadata(file_id)
        if not metadata:
            raise FileNotFoundError(f"File not found: {file_id}")
        
        return await self._storage.read(metadata.path)
    
    async def delete(self, file_id: str) -> bool:
        metadata = await self.get_metadata(file_id)
        if not metadata:
            return False
        
        result = await self._storage.delete(metadata.path)
        
        if result:
            del self._metadata_store[file_id]
            if file_id in self._version_store:
                del self._version_store[file_id]
        
        return result
    
    async def move(self, file_id: str, target_path: str) -> FileMetadata:
        metadata = await self.get_metadata(file_id)
        if not metadata:
            raise FileNotFoundError(f"File not found: {file_id}")
        
        new_path = self._normalize_path(target_path, metadata.name)
        await self._storage.move(metadata.path, new_path)
        
        updated = FileMetadata(
            file_id=metadata.file_id,
            name=metadata.name,
            path=new_path,
            size=metadata.size,
            content_type=metadata.content_type,
            checksum=metadata.checksum,
            created_at=metadata.created_at,
            updated_at=int(datetime.now(tz=timezone.utc).timestamp()),
            owner_id=metadata.owner_id,
            is_directory=metadata.is_directory,
            tags=metadata.tags,
            metadata=metadata.metadata,
        )
        
        self._metadata_store[file_id] = updated
        return updated
    
    async def rename(self, file_id: str, new_name: str) -> FileMetadata:
        metadata = await self.get_metadata(file_id)
        if not metadata:
            raise FileNotFoundError(f"File not found: {file_id}")
        
        parent_path = os.path.dirname(metadata.path)
        new_path = f"{parent_path}/{new_name}" if parent_path else new_name
        
        await self._storage.move(metadata.path, new_path)
        
        updated = FileMetadata(
            file_id=metadata.file_id,
            name=new_name,
            path=new_path,
            size=metadata.size,
            content_type=self._detect_content_type(new_name),
            checksum=metadata.checksum,
            created_at=metadata.created_at,
            updated_at=int(datetime.now(tz=timezone.utc).timestamp()),
            owner_id=metadata.owner_id,
            is_directory=metadata.is_directory,
            tags=metadata.tags,
            metadata=metadata.metadata,
        )
        
        self._metadata_store[file_id] = updated
        return updated
    
    async def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        return self._metadata_store.get(file_id)
    
    async def list_folder(
        self,
        folder_path: str = "/",
        page: int = 1,
        page_size: int = 50,
    ) -> List[FileInfo]:
        items = await self._storage.list(folder_path)
        
        start = (page - 1) * page_size
        end = start + page_size
        
        return items[start:end]
    
    async def create_folder(self, path: str, name: str) -> FileMetadata:
        full_path = self._normalize_path(path, name)
        await self._storage.create_directory(full_path)
        
        now = int(datetime.now(tz=timezone.utc).timestamp())
        metadata = FileMetadata(
            file_id=self._generate_id(),
            name=name,
            path=full_path,
            size=0,
            content_type="directory",
            checksum="",
            created_at=now,
            updated_at=now,
            owner_id=self._get_current_user(),
            is_directory=True,
            tags=[],
            metadata={},
        )
        
        self._metadata_store[metadata.file_id] = metadata
        return metadata
    
    async def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
    ) -> List[FileInfo]:
        results = []
        query_lower = query.lower()
        
        for file_id, metadata in self._metadata_store.items():
            if query_lower in metadata.name.lower():
                if self._matches_filters(metadata, filters):
                    results.append(FileInfo(
                        name=metadata.name,
                        path=metadata.path,
                        size=metadata.size,
                        is_directory=metadata.is_directory,
                        modified_at=metadata.updated_at,
                        content_type=metadata.content_type,
                        checksum=metadata.checksum,
                    ))
        
        return results
    
    def _matches_filters(
        self,
        metadata: FileMetadata,
        filters: Optional[SearchFilters],
    ) -> bool:
        if not filters:
            return True
        
        if filters.tags:
            if not any(tag in metadata.tags for tag in filters.tags):
                return False
        
        if filters.content_type:
            if not metadata.content_type.startswith(filters.content_type):
                return False
        
        if filters.date_from and metadata.updated_at < filters.date_from:
            return False
        
        if filters.date_to and metadata.updated_at > filters.date_to:
            return False
        
        if filters.min_size and metadata.size < filters.min_size:
            return False
        
        if filters.max_size and metadata.size > filters.max_size:
            return False
        
        return True
    
    async def create_share(
        self,
        file_id: str,
        options: ShareOptions,
    ) -> ShareInfo:
        metadata = await self.get_metadata(file_id)
        if not metadata:
            raise FileNotFoundError(f"File not found: {file_id}")
        
        now = int(datetime.now(tz=timezone.utc).timestamp())
        share = ShareInfo(
            share_id=self._generate_id(),
            file_id=file_id,
            file_name=metadata.name,
            created_at=now,
            expire_at=now + options.expire_in if options.expire_in else None,
            password=options.password,
            max_downloads=options.max_downloads,
            download_count=0,
        )
        
        self._share_store[share.share_id] = share
        return share
    
    async def get_share(self, share_id: str, password: Optional[str] = None) -> ShareInfo:
        share = self._share_store.get(share_id)
        if not share:
            raise ValueError(f"Share not found: {share_id}")
        
        now = int(datetime.now(tz=timezone.utc).timestamp())
        if share.expire_at and share.expire_at < now:
            raise ValueError("Share has expired")
        
        if share.password and share.password != password:
            raise ValueError("Invalid password")
        
        if share.max_downloads and share.download_count >= share.max_downloads:
            raise ValueError("Download limit reached")
        
        return share
    
    async def download_share(self, share_id: str, password: Optional[str] = None) -> bytes:
        share = await self.get_share(share_id, password)
        
        updated_share = ShareInfo(
            share_id=share.share_id,
            file_id=share.file_id,
            file_name=share.file_name,
            created_at=share.created_at,
            expire_at=share.expire_at,
            password=share.password,
            max_downloads=share.max_downloads,
            download_count=share.download_count + 1,
        )
        self._share_store[share_id] = updated_share
        
        return await self.download(share.file_id)
    
    async def list_versions(self, file_id: str) -> List[VersionInfo]:
        return self._version_store.get(file_id, [])
    
    async def _create_version(
        self,
        file_id: str,
        content: bytes,
        description: Optional[str] = None,
    ) -> VersionInfo:
        versions = self._version_store.get(file_id, [])
        
        version = VersionInfo(
            version_id=self._generate_id(),
            file_id=file_id,
            version_number=len(versions) + 1,
            created_at=int(datetime.now(tz=timezone.utc).timestamp()),
            size=len(content),
            checksum=self._compute_checksum(content),
            description=description,
        )
        
        versions.append(version)
        
        if len(versions) > self._max_versions:
            versions = versions[-self._max_versions:]
        
        self._version_store[file_id] = versions
        return version
    
    def _normalize_path(self, path: str, filename: str) -> str:
        path = path.rstrip("/")
        if path:
            return f"{path}/{filename}"
        return filename
    
    def _compute_checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()
    
    def _detect_content_type(self, filename: str) -> str:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        content_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "csv": "text/csv",
            "json": "application/json",
            "zip": "application/zip",
        }
        return content_types.get(ext, "application/octet-stream")
    
    def _generate_id(self) -> str:
        return str(uuid.uuid4())
    
    def _get_current_user(self) -> str:
        return "system"
    
    def _index_file(self, metadata: FileMetadata) -> None:
        for tag in metadata.tags:
            if tag not in self._file_index:
                self._file_index[tag] = []
            self._file_index[tag].append(metadata.file_id)
