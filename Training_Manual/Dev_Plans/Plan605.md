# Plan605 Search Adapter（免费链路）

## 目标
提供可替换搜索适配层。

## 代码（`src/search/adapter.py`）
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchAdapter:
    """Free-chain placeholder adapter.

    Integrate real adapters here:
    - SearXNG
    - Wikipedia API
    - RSS feeds
    """

    def search(self, query: str) -> list[SearchResult]:
        return [
            SearchResult(
                title="stub-result",
                url="https://example.com",
                snippet=f"query={query}",
            )
        ]
```

## 验收
- 统一返回 `title/url/snippet` 结构
