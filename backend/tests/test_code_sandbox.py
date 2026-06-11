from __future__ import annotations

import asyncio

from app.core.code_sandbox import (
    CodeSandboxError,
    execute_python_code,
    extract_python_code,
)


def test_extract_python_code_prefers_python_fence() -> None:
    content = """
说明文字

```json
{"not": "python"}
```

```python
print(sum(range(4)))
```
"""

    assert extract_python_code(content) == "print(sum(range(4)))"


def test_extract_python_code_reports_missing_block() -> None:
    try:
        extract_python_code("这里只有普通说明")
    except CodeSandboxError as exc:
        assert "未找到" in str(exc)
    else:
        raise AssertionError("expected CodeSandboxError")


def test_execute_python_code_returns_stdout() -> None:
    result = asyncio.run(execute_python_code("print(sum(range(4)))"))

    assert result.status == "success"
    assert result.stdout.strip() == "6"
    assert result.stderr == ""


def test_execute_python_code_blocks_unsafe_import() -> None:
    result = asyncio.run(execute_python_code("import os\nprint(os.getcwd())"))

    assert result.status == "blocked"
    assert "不允许导入模块" in result.stderr


def test_execute_python_code_stops_timeout() -> None:
    result = asyncio.run(
        execute_python_code("while True:\n    pass", timeout_seconds=0.2)
    )

    assert result.status == "timeout"
    assert "执行超时" in result.stderr
