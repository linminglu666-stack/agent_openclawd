from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from protocols.interfaces import IModule
from utils.logger import get_logger


@dataclass
class Route:
    path: str
    method: str
    handler: Callable
    auth_required: bool = True
    roles: List[str] = field(default_factory=list)


@dataclass
class APIResponse:
    status_code: int
    body: Any
    headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "body": self.body,
            "headers": self.headers,
        }


class APIRouter(IModule):
    def __init__(self):
        self._routes: Dict[str, Dict[str, Route]] = {}
        self._middleware: List[Callable] = []
        self._initialized = False
        self._logger = get_logger("api.router")

    @property
    def name(self) -> str:
        return "api_router"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        self._initialized = True
        self._logger.info("API router initialized")
        return True

    async def shutdown(self) -> bool:
        self._initialized = False
        self._logger.info("API router shutdown")
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "component": self.name,
            "initialized": self._initialized,
            "routes": sum(len(methods) for methods in self._routes.values()),
        }

    async def execute(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command == "route":
            response = await self.handle_request(
                args.get("path", ""),
                args.get("method", "GET"),
                args.get("body", {}),
                args.get("headers", {}),
                args.get("user", {}),
            )
            return response.to_dict()
        elif command == "list":
            return {"routes": self.list_routes()}
        else:
            return {"error": f"Unknown command: {command}"}

    def route(self, path: str, method: str = "GET", auth_required: bool = True, roles: Optional[List[str]] = None) -> Callable:
        def decorator(handler: Callable) -> Callable:
            self.add_route(Route(
                path=path,
                method=method.upper(),
                handler=handler,
                auth_required=auth_required,
                roles=roles or [],
            ))
            return handler
        return decorator

    def add_route(self, route: Route) -> None:
        if route.path not in self._routes:
            self._routes[route.path] = {}
        self._routes[route.path][route.method] = route
        self._logger.debug("Route added", path=route.path, method=route.method)

    def add_middleware(self, middleware: Callable) -> None:
        self._middleware.append(middleware)

    async def handle_request(
        self,
        path: str,
        method: str,
        body: Dict[str, Any],
        headers: Dict[str, str],
        user: Dict[str, Any],
    ) -> APIResponse:
        for middleware in self._middleware:
            try:
                result = await middleware(path, method, body, headers, user) if asyncio.iscoroutinefunction(middleware) else middleware(path, method, body, headers, user)
                if result:
                    return result
            except Exception as e:
                self._logger.error("Middleware error", path=path, error=str(e))
                return APIResponse(500, {"error": "middleware_error"})

        path_routes = self._routes.get(path)
        if not path_routes:
            return APIResponse(404, {"error": "not_found"})

        route = path_routes.get(method.upper())
        if not route:
            return APIResponse(405, {"error": "method_not_allowed"})

        if route.auth_required and not user:
            return APIResponse(401, {"error": "unauthorized"})

        if route.roles:
            user_roles = set(user.get("roles", []))
            if not any(role in user_roles for role in route.roles):
                return APIResponse(403, {"error": "forbidden"})

        try:
            result = route.handler(body, headers, user)
            if hasattr(result, "__await__"):
                result = await result

            if isinstance(result, APIResponse):
                return result
            elif isinstance(result, dict):
                return APIResponse(200, result)
            else:
                return APIResponse(200, {"data": result})

        except Exception as e:
            self._logger.error("Handler error", path=path, method=method, error=str(e))
            return APIResponse(500, {"error": str(e)})

    def list_routes(self) -> List[Dict[str, Any]]:
        routes = []
        for path, methods in self._routes.items():
            for method, route in methods.items():
                routes.append({
                    "path": path,
                    "method": method,
                    "auth_required": route.auth_required,
                    "roles": route.roles,
                })
        return routes

    def get_openapi_spec(self) -> Dict[str, Any]:
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "OpenClaw-X API",
                "version": "1.0.0",
            },
            "paths": {
                path: {
                    method.lower(): {
                        "summary": f"{method} {path}",
                        "responses": {
                            "200": {"description": "Success"},
                            "401": {"description": "Unauthorized"},
                            "403": {"description": "Forbidden"},
                            "404": {"description": "Not Found"},
                        },
                    }
                    for method, route in methods.items()
                }
                for path, methods in self._routes.items()
            },
        }


import asyncio
