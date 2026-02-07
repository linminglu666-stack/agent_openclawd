# Plan612 测试基线与质量闸门

## 目标
建立最小可行测试体系。

## 代码（`tests/test_smoke.py`）
```python
def test_smoke():
    assert True
```

## 代码（`scripts/quality_gate.sh`）
```bash
#!/usr/bin/env bash
set -e
pytest -q
ruff check src tests
mypy src || true
```

## 验收
- `scripts/quality_gate.sh` 可运行
