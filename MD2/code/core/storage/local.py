from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .provider import (
    BaseStorageProvider,
    FileInfo,
    FileMetadata,
    StorageProvider,
)


class LocalStorage(BaseStorageProvider, StorageProvider):
    def __init__(
        self,
        root_path: str,
        create_if_missing: bool = True,
        max_file_size: int = 100 * 1024 * 1024,
    ):
        super().__init__(root_path)
        self._max_file_size = max_file_size
        self._metadata_cache: Dict[str, FileMetadata] = {}
        
        if create_if_missing:
            Path(self._root_path).mkdir(parents=True, exist_ok=True)
    
    async def read(self, path: str) -> bytes:
        full_path = self._normalize_path(path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(full_path, "rb") as f:
            return f.read()
    
    async def write(self, path: str, data: bytes) -> str:
        if len(data) > self._max_file_size:
            raise ValueError(f"File size exceeds maximum: {len(data)} > {self._max_file_size}")
        
        full_path = self._normalize_path(path)
        
        dir_path = os.path.dirname(full_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        with open(full_path, "wb") as f:
            f.write(data)
        
        return path
    
    async def delete(self, path: str) -> bool:
        full_path = self._normalize_path(path)
        
        if not os.path.exists(full_path):
            return False
        
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        
        if path in self._metadata_cache:
            del self._metadata_cache[path]
        
        return True
    
    async def exists(self, path: str) -> bool:
        full_path = self._normalize_path(path)
        return os.path.exists(full_path)
    
    async def list(self, prefix: str = "") -> List[FileInfo]:
        full_path = self._normalize_path(prefix)
        
        if not os.path.exists(full_path):
            return []
        
        items = []
        for entry in os.scandir(full_path):
            stat = entry.stat()
            items.append(FileInfo(
                name=entry.name,
                path=f"{prefix}/{entry.name}" if prefix else entry.name,
                size=stat.st_size if entry.is_file() else 0,
                is_directory=entry.is_dir(),
                modified_at=int(stat.st_mtime),
                content_type=self._get_content_type(entry.name) if entry.is_file() else None,
            ))
        
        return sorted(items, key=lambda x: (not x.is_directory, x.name.lower()))
    
    async def move(self, src: str, dst: str) -> bool:
        src_full = self._normalize_path(src)
        dst_full = self._normalize_path(dst)
        
        if not os.path.exists(src_full):
            return False
        
        dst_dir = os.path.dirname(dst_full)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)
        
        shutil.move(src_full, dst_full)
        
        if src in self._metadata_cache:
            metadata = self._metadata_cache.pop(src)
            self._metadata_cache[dst] = FileMetadata(
                file_id=metadata.file_id,
                name=os.path.basename(dst),
                path=dst,
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
        
        return True
    
    async def copy(self, src: str, dst: str) -> bool:
        src_full = self._normalize_path(src)
        dst_full = self._normalize_path(dst)
        
        if not os.path.exists(src_full):
            return False
        
        dst_dir = os.path.dirname(dst_full)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)
        
        if os.path.isdir(src_full):
            shutil.copytree(src_full, dst_full)
        else:
            shutil.copy2(src_full, dst_full)
        
        return True
    
    async def get_metadata(self, path: str) -> Optional[FileMetadata]:
        if path in self._metadata_cache:
            return self._metadata_cache[path]
        
        full_path = self._normalize_path(path)
        
        if not os.path.exists(full_path):
            return None
        
        stat = os.stat(full_path)
        is_dir = os.path.isdir(full_path)
        
        checksum = ""
        if not is_dir:
            with open(full_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
        
        metadata = FileMetadata(
            file_id=self._generate_file_id(),
            name=os.path.basename(path),
            path=path,
            size=stat.st_size if not is_dir else 0,
            content_type=self._get_content_type(path) if not is_dir else "directory",
            checksum=checksum,
            created_at=int(stat.st_ctime),
            updated_at=int(stat.st_mtime),
            owner_id="system",
            is_directory=is_dir,
            tags=[],
            metadata={},
        )
        
        self._metadata_cache[path] = metadata
        return metadata
    
    async def get_url(self, path: str, expires: int = 3600) -> str:
        return f"file://{self._normalize_path(path)}"
    
    async def create_directory(self, path: str) -> bool:
        full_path = self._normalize_path(path)
        os.makedirs(full_path, exist_ok=True)
        return True
    
    async def delete_directory(self, path: str, force: bool = False) -> bool:
        full_path = self._normalize_path(path)
        
        if not os.path.exists(full_path):
            return False
        
        if not os.path.isdir(full_path):
            return False
        
        if not force and os.listdir(full_path):
            raise ValueError(f"Directory not empty: {path}")
        
        shutil.rmtree(full_path)
        return True
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for root, dirs, files in os.walk(self._root_path):
            dir_count += len(dirs)
            file_count += len(files)
            for f in files:
                fp = os.path.join(root, f)
                total_size += os.path.getsize(fp)
        
        return {
            "total_size": total_size,
            "file_count": file_count,
            "directory_count": dir_count,
            "root_path": self._root_path,
        }
    
    async def get_tree(self, prefix: str = "", depth: int = 3) -> Dict[str, Any]:
        full_path = self._normalize_path(prefix)
        
        def build_tree(path: str, current_depth: int) -> Dict[str, Any]:
            if current_depth > depth:
                return {}
            
            result = {
                "name": os.path.basename(path) or "root",
                "path": path,
                "is_directory": True,
                "children": [],
            }
            
            try:
                for entry in os.scandir(path):
                    if entry.is_dir():
                        result["children"].append(build_tree(
                            entry.path,
                            current_depth + 1,
                        ))
                    else:
                        stat = entry.stat()
                        result["children"].append({
                            "name": entry.name,
                            "path": f"{path}/{entry.name}",
                            "is_directory": False,
                            "size": stat.st_size,
                            "modified_at": int(stat.st_mtime),
                        })
            except PermissionError:
                pass
            
            return result
        
        if not os.path.exists(full_path):
            return {}
        
        return build_tree(full_path, 0)
