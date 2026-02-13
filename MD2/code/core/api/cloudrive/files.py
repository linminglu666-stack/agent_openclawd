from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..cloudrive import (
    CloudDriveService,
    OutputRouter,
    OutputContext,
    SearchFilters,
    ShareOptions,
)
from ..storage import LocalStorage
from .schemas import (
    FileListRequest,
    FileListResponse,
    UploadRequest,
    UploadResponse,
    SearchRequest,
    SearchResponse,
    ShareCreateRequest,
    ShareCreateResponse,
    FolderCreateRequest,
    FolderCreateResponse,
    MoveRequest,
    RenameRequest,
    BatchDeleteRequest,
    BatchDeleteResponse,
    StorageStats,
    TreeNode,
    RecentFile,
    BreadcrumbItem,
)


class CloudDriveAPI:
    def __init__(
        self,
        storage_root: str = "./cloudrive",
        workspace_root: str = "./workspace",
    ):
        self._cloudrive_storage = LocalStorage(storage_root)
        self._workspace_storage = LocalStorage(workspace_root)
        self._output_router = OutputRouter()
        self._service = CloudDriveService(
            storage=self._cloudrive_storage,
            output_router=self._output_router,
        )
        self._recent_files: List[RecentFile] = []
    
    async def list_files(self, request: FileListRequest) -> FileListResponse:
        items = await self._service.list_folder(
            folder_path=request.folder_path,
            page=request.page,
            page_size=request.page_size,
        )
        
        total = len(items)
        
        result_items = [
            {
                "id": item.name,
                "name": item.name,
                "path": item.path,
                "size": item.size,
                "is_directory": item.is_directory,
                "modified_at": item.modified_at,
                "content_type": item.content_type,
            }
            for item in items
        ]
        
        if request.sort_by == "name":
            result_items.sort(
                key=lambda x: x["name"].lower(),
                reverse=request.sort_order == "desc",
            )
        elif request.sort_by == "size":
            result_items.sort(
                key=lambda x: x["size"],
                reverse=request.sort_order == "desc",
            )
        elif request.sort_by == "modified_at":
            result_items.sort(
                key=lambda x: x["modified_at"],
                reverse=request.sort_order == "desc",
            )
        
        return FileListResponse(
            items=result_items,
            total=total,
            page=request.page,
            page_size=request.page_size,
            has_more=total > request.page * request.page_size,
        )
    
    async def upload_file(self, request: UploadRequest) -> UploadResponse:
        context = OutputContext(
            task_type="general",
            metadata={"user_upload": True},
        )
        
        metadata = await self._service.save_output(
            content=request.content,
            filename=request.filename,
            context=context,
        )
        
        recent = RecentFile(
            file_id=metadata.file_id,
            name=metadata.name,
            path=metadata.path,
            size=metadata.size,
            content_type=metadata.content_type,
            modified_at=metadata.updated_at,
        )
        self._recent_files.insert(0, recent)
        self._recent_files = self._recent_files[:50]
        
        return UploadResponse(
            file_id=metadata.file_id,
            name=metadata.name,
            path=metadata.path,
            size=metadata.size,
            content_type=metadata.content_type,
            url=f"/api/v1/cloudrive/files/{metadata.file_id}/download",
            created_at=metadata.created_at,
        )
    
    async def download_file(self, file_id: str) -> Dict[str, Any]:
        content = await self._service.download(file_id)
        metadata = await self._service.get_metadata(file_id)
        
        return {
            "content": content,
            "filename": metadata.name if metadata else file_id,
            "content_type": metadata.content_type if metadata else "application/octet-stream",
            "size": len(content),
        }
    
    async def delete_file(self, file_id: str) -> bool:
        return await self._service.delete(file_id)
    
    async def search_files(self, request: SearchRequest) -> SearchResponse:
        filters = SearchFilters(
            tags=request.tags,
            content_type=request.content_type,
            date_from=request.date_from,
            date_to=request.date_to,
        )
        
        items = await self._service.search(request.query, filters)
        
        total = len(items)
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        page_items = items[start:end]
        
        return SearchResponse(
            items=[
                {
                    "id": item.name,
                    "name": item.name,
                    "path": item.path,
                    "size": item.size,
                    "is_directory": item.is_directory,
                    "modified_at": item.modified_at,
                    "content_type": item.content_type,
                }
                for item in page_items
            ],
            total=total,
            page=request.page,
            page_size=request.page_size,
        )
    
    async def create_folder(self, request: FolderCreateRequest) -> FolderCreateResponse:
        metadata = await self._service.create_folder(
            path=request.parent_path,
            name=request.name,
        )
        
        return FolderCreateResponse(
            folder_id=metadata.file_id,
            name=metadata.name,
            path=metadata.path,
        )
    
    async def move_file(self, request: MoveRequest) -> Dict[str, Any]:
        target_path = request.target_path or "/"
        metadata = await self._service.move(request.file_id, target_path)
        
        return {
            "success": True,
            "new_path": metadata.path,
        }
    
    async def rename_file(self, request: RenameRequest) -> Dict[str, Any]:
        metadata = await self._service.rename(request.file_id, request.new_name)
        
        return {
            "success": True,
            "new_name": metadata.name,
            "new_path": metadata.path,
        }
    
    async def batch_delete(self, request: BatchDeleteRequest) -> BatchDeleteResponse:
        success = []
        failed = []
        
        for file_id in request.file_ids:
            try:
                result = await self._service.delete(file_id)
                if result:
                    success.append(file_id)
                else:
                    failed.append({"file_id": file_id, "error": "Delete failed"})
            except Exception as e:
                failed.append({"file_id": file_id, "error": str(e)})
        
        return BatchDeleteResponse(success=success, failed=failed)
    
    async def create_share(self, request: ShareCreateRequest) -> ShareCreateResponse:
        options = ShareOptions(
            expire_in=request.expire_in,
            password=request.password,
            max_downloads=request.max_downloads,
        )
        
        share = await self._service.create_share(request.file_id, options)
        
        return ShareCreateResponse(
            share_id=share.share_id,
            share_url=f"/s/{share.share_id}",
            expire_at=share.expire_at,
            file_name=share.file_name,
        )
    
    async def get_share(self, share_id: str, password: Optional[str] = None) -> Dict[str, Any]:
        share = await self._service.get_share(share_id, password)
        metadata = await self._service.get_metadata(share.file_id)
        
        return {
            "share_id": share.share_id,
            "file_name": share.file_name,
            "file_size": metadata.size if metadata else 0,
            "expire_at": share.expire_at,
            "download_url": f"/api/v1/cloudrive/shares/{share_id}/download",
        }
    
    async def download_share(self, share_id: str, password: Optional[str] = None) -> Dict[str, Any]:
        content = await self._service.download_share(share_id, password)
        share = await self._service.get_share(share_id, password)
        
        return {
            "content": content,
            "filename": share.file_name,
            "content_type": "application/octet-stream",
            "size": len(content),
        }
    
    async def get_storage_stats(self) -> StorageStats:
        stats = await self._cloudrive_storage.get_storage_stats()
        quota = 10 * 1024 * 1024 * 1024
        
        return StorageStats(
            total_size=stats["total_size"],
            file_count=stats["file_count"],
            directory_count=stats["directory_count"],
            used_percentage=stats["total_size"] / quota * 100 if quota > 0 else 0,
            quota=quota,
        )
    
    async def get_folder_tree(self, root_path: str = "/", depth: int = 3) -> List[TreeNode]:
        tree = await self._cloudrive_storage.get_tree(root_path, depth)
        
        def convert_node(node: Dict[str, Any]) -> TreeNode:
            children = None
            if node.get("children"):
                children = [convert_node(c) for c in node["children"]]
            
            return TreeNode(
                id=node.get("path", ""),
                name=node.get("name", ""),
                path=node.get("path", ""),
                is_directory=node.get("is_directory", True),
                size=node.get("size"),
                children=children,
            )
        
        if tree:
            return [convert_node(tree)]
        return []
    
    async def get_recent_files(self, limit: int = 20) -> List[RecentFile]:
        return self._recent_files[:limit]
    
    async def get_breadcrumbs(self, path: str) -> List[BreadcrumbItem]:
        parts = path.strip("/").split("/")
        breadcrumbs = [BreadcrumbItem(id=None, name="Root", path="/")]
        
        current_path = ""
        for part in parts:
            if part:
                current_path = f"{current_path}/{part}"
                breadcrumbs.append(BreadcrumbItem(
                    id=None,
                    name=part,
                    path=current_path,
                ))
        
        return breadcrumbs
    
    async def get_file_versions(self, file_id: str) -> List[Dict[str, Any]]:
        versions = await self._service.list_versions(file_id)
        
        return [
            {
                "version_id": v.version_id,
                "version_number": v.version_number,
                "created_at": v.created_at,
                "size": v.size,
                "description": v.description,
            }
            for v in versions
        ]
