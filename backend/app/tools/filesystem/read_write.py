"""File read, write, and edit tools."""

from backend.app.tools.utils import resolve_path
from backend.app.config import settings
from backend.app.tools.base import BaseTool


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to workspace"},
            "max_size": {"type": "integer", "description": "Maximum bytes to read", "default": 100000},
        },
        "required": ["path"],
    }
    risk_level = "safe"
    timeout = 10

    async def execute(self, path: str, max_size: int = 100000, **kwargs) -> dict:
        try:
            filepath = resolve_path(path, kwargs.get("workspace"))
            if not filepath.exists():
                return {"success": False, "output": "", "error": f"File not found: {path}"}
            if not filepath.is_file():
                return {"success": False, "output": "", "error": f"Not a file: {path}"}

            size = filepath.stat().st_size
            if size > settings.max_file_size:
                return {
                    "success": False,
                    "output": "",
                    "error": f"File too large: {size} bytes (max {settings.max_file_size})",
                }

            content = filepath.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_size:
                content = content[:max_size] + f"\n... [truncated {len(content) - max_size} more chars]"

            return {
                "success": True,
                "output": content,
                "metadata": {"size": size, "lines": content.count("\n") + 1},
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Error reading file: {str(e)}"}


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to workspace"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    }
    risk_level = "medium"
    permission_requirement = "confirmation"
    timeout = 10

    async def execute(self, path: str, content: str, **kwargs) -> dict:
        try:
            filepath = resolve_path(path, kwargs.get("workspace"))
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "output": f"Written {len(content)} bytes to {path}",
                "metadata": {"size": len(content), "lines": content.count("\n") + 1},
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:            return {
                "success": False, "output": "", "error": f"Error writing file: {str(e)}"
            }


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "List the contents of a directory"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to workspace", "default": "."},
        },
        "required": [],
    }
    risk_level = "safe"
    timeout = 10

    async def execute(self, path: str = ".", **kwargs) -> dict:
        try:
            dirpath = resolve_path(path, kwargs.get("workspace"))
            if not dirpath.exists():
                return {"success": False, "output": "", "error": f"Directory not found: {path}"}
            if not dirpath.is_dir():
                return {"success": False, "output": "", "error": f"Not a directory: {path}"}

            items = []
            for entry in sorted(dirpath.iterdir(), key=lambda e: (not e.is_dir(), e.name)):
                items.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else 0,
                })

            return {
                "success": True,
                "output": "\n".join(
                    f"[{'DIR' if i['type'] == 'directory' else '   '}] {i['name']}"
                    for i in items
                ),
                "metadata": {"count": len(items), "items": items},
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Error listing directory: {str(e)}"}


class FileExistsTool(BaseTool):
    name = "file_exists"
    description = "Check if a file or directory exists"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to workspace"},
        },
        "required": ["path"],
    }
    risk_level = "safe"
    timeout = 5

    async def execute(self, path: str, **kwargs) -> dict:
        try:
            filepath = resolve_path(path, kwargs.get("workspace"))
            exists = filepath.exists()
            return {
                "success": True,
                "output": f"{'Exists' if exists else 'Does not exist'}: {path}",
                "metadata": {
                    "exists": exists,
                    "is_file": filepath.is_file() if exists else False,
                    "is_dir": filepath.is_dir() if exists else False,
                },
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
