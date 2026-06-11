from __future__ import annotations

import ast
import asyncio
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass


class CodeSandboxError(RuntimeError):
    """代码沙箱执行异常。"""


class CodeSafetyViolation(CodeSandboxError):
    """代码未通过静态安全检查。"""


@dataclass(slots=True)
class CodeExecutionResult:
    status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: int = 0


_FENCE_PATTERN = re.compile(r"```(?P<lang>[a-zA-Z0-9_+-]*)\s*\n(?P<code>[\s\S]*?)```")
_PYTHON_LANGS = {"", "py", "python", "python3"}
_IGNORED_LANGS = {"json", "mermaid", "markdown", "md", "text", "txt", "bash", "shell", "sh"}
_ALLOWED_IMPORTS = {
    "collections",
    "decimal",
    "fractions",
    "functools",
    "itertools",
    "math",
    "random",
    "statistics",
}
_BLOCKED_NAMES = {
    "breakpoint",
    "compile",
    "dir",
    "eval",
    "exec",
    "exit",
    "globals",
    "help",
    "input",
    "locals",
    "memoryview",
    "open",
    "quit",
    "vars",
    "__import__",
}
_BLOCKED_ATTRIBUTES = {
    "chmod",
    "chown",
    "exec",
    "execv",
    "execve",
    "fork",
    "kill",
    "load",
    "loads",
    "mkdir",
    "open",
    "popen",
    "remove",
    "removedirs",
    "rename",
    "replace",
    "rmdir",
    "rmtree",
    "spawn",
    "system",
    "unlink",
    "write",
    "writelines",
}
_SAFE_BUILTINS = (
    "ArithmeticError",
    "AssertionError",
    "Exception",
    "IndexError",
    "KeyError",
    "RuntimeError",
    "TypeError",
    "ValueError",
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "filter",
    "float",
    "format",
    "int",
    "isinstance",
    "len",
    "list",
    "map",
    "max",
    "min",
    "pow",
    "print",
    "range",
    "reversed",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
)
_RUNNER = f"""
import builtins
import sys
import traceback

ALLOWED_IMPORTS = {sorted(_ALLOWED_IMPORTS)!r}
SAFE_BUILTINS = {list(_SAFE_BUILTINS)!r}

def limited_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".", 1)[0]
    if root not in ALLOWED_IMPORTS:
        raise ImportError(f"不允许导入模块: {{name}}")
    return builtins.__import__(name, globals, locals, fromlist, level)

safe_builtins = {{name: getattr(builtins, name) for name in SAFE_BUILTINS}}
safe_builtins["__import__"] = limited_import
namespace = {{
    "__builtins__": safe_builtins,
    "__name__": "__eduagent_sandbox__",
}}
code = sys.stdin.read()

try:
    exec(compile(code, "<eduagent-code>", "exec"), namespace, namespace)
except BaseException as exc:
    traceback.print_exception(type(exc), exc, exc.__traceback__, limit=4)
    sys.exit(1)
"""


def extract_python_code(markdown: str, code_index: int = 0) -> str:
    """从 Markdown 资源中提取第 N 个 Python 代码块。"""
    candidates: list[str] = []
    for match in _FENCE_PATTERN.finditer(markdown):
        lang = match.group("lang").strip().lower()
        if lang in _PYTHON_LANGS:
            candidates.append(match.group("code").strip())
        elif not lang or lang not in _IGNORED_LANGS:
            candidates.append(match.group("code").strip())

    if not candidates:
        raise CodeSandboxError("未找到可运行的 Python 代码块")
    if code_index < 0 or code_index >= len(candidates):
        raise CodeSandboxError("代码块序号超出范围")

    code = candidates[code_index].strip()
    if not code:
        raise CodeSandboxError("代码块为空")
    return code


class _SafetyVisitor(ast.NodeVisitor):
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".", 1)[0]
            if root not in _ALLOWED_IMPORTS:
                raise CodeSafetyViolation(f"不允许导入模块: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".", 1)[0]
        if node.level != 0 or root not in _ALLOWED_IMPORTS:
            raise CodeSafetyViolation(f"不允许导入模块: {node.module or ''}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = self._call_name(node.func)
        if name in _BLOCKED_NAMES:
            raise CodeSafetyViolation(f"不允许调用函数: {name}")
        if isinstance(node.func, ast.Attribute) and node.func.attr in _BLOCKED_ATTRIBUTES:
            raise CodeSafetyViolation(f"不允许调用方法: {node.func.attr}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__"):
            raise CodeSafetyViolation("不允许访问双下划线属性")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("__") and node.id != "__name__":
            raise CodeSafetyViolation("不允许访问双下划线名称")
        self.generic_visit(node)

    def _call_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""


def validate_python_code(code: str, max_chars: int = 8000) -> None:
    if len(code) > max_chars:
        raise CodeSafetyViolation(f"代码过长，最多允许 {max_chars} 个字符")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise CodeSafetyViolation(f"Python 语法错误: {exc.msg}") from exc
    _SafetyVisitor().visit(tree)


async def execute_python_code(
    code: str,
    *,
    timeout_seconds: float = 3.0,
    max_output_chars: int = 12000,
) -> CodeExecutionResult:
    """在受限子进程中执行 Python 代码。"""
    started_at = time.perf_counter()
    try:
        validate_python_code(code)
    except CodeSafetyViolation as exc:
        return CodeExecutionResult(
            status="blocked",
            stderr=str(exc),
            duration_ms=_duration_ms(started_at),
        )

    with tempfile.TemporaryDirectory(prefix="eduagent-code-") as tmpdir:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-S",
            "-c",
            _RUNNER,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmpdir,
            env=_sandbox_env(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(code.encode("utf-8")),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            return CodeExecutionResult(
                status="timeout",
                stdout=_decode_and_truncate(stdout, max_output_chars),
                stderr=f"代码执行超时，已在 {timeout_seconds:.1f} 秒后停止",
                exit_code=process.returncode,
                duration_ms=_duration_ms(started_at),
            )

    return CodeExecutionResult(
        status="success" if process.returncode == 0 else "error",
        stdout=_decode_and_truncate(stdout, max_output_chars),
        stderr=_decode_and_truncate(stderr, max_output_chars),
        exit_code=process.returncode,
        duration_ms=_duration_ms(started_at),
    )


def _sandbox_env() -> dict[str, str]:
    env = {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    for key in ("SystemRoot", "WINDIR", "TEMP", "TMP"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _decode_and_truncate(data: bytes, max_chars: int) -> str:
    text = data.decode("utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n... [输出已截断]"


def _duration_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))
