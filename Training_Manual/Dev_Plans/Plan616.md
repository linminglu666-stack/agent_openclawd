# Plan616 CI/CD 与发布流程

## 目标
每次变更自动执行质量门。

## 代码（`.github/workflows/ci.yml`）
```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -U pytest ruff mypy
      - run: pytest -q
      - run: ruff check src tests
```

## 验收
- PR 自动触发 CI
