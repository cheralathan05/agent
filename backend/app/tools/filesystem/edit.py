"""File editing tools for targeted modifications."""

from backend.app.tools.utils import resolve_path
from backend.app.tools.base import BaseTool


class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Apply an exact string replacement in a file"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to workspace"},
            "old_string": {"type": "string", "description": "Exact string to replace"},
            "new_string": {"type": "string", "description": "Replacement string"},
        },
        "required": ["path", "old_string", "new_string"],
    }
    risk_level = "medium"
    permission_requirement = "confirmation"
    timeout = 10

    async def execute(self, path: str, old_string: str, new_string: str, **kwargs) -> dict:
        try:
            filepath = resolve_path(path, kwargs.get("workspace"))
            if not filepath.exists() or not filepath.is_file():
                return {"success": False, "output": "", "error": f"File not found: {path}"}

            content = filepath.read_text(encoding="utf-8")
            
            if old_string not in content:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Could not find the specified content in {path}. The content may have changed.",
                }

            count = content.count(old_string)
            if count > 1:
                # If multiple occurrences, do first replacement only (targeted)
                new_content = content.replace(old_string, new_string, 1)
            else:
                new_content = content.replace(old_string, new_string)

            lines_added = new_string.count("\n") - old_string.count("\n")
            
            filepath.write_text(new_content, encoding="utf-8")

            return {
                "success": True,
                "output": f"Applied edit to {path} ({count} occurrence{'s' if count > 1 else ''})",
                "metadata": {
                    "lines_added": max(lines_added, 0),
                    "lines_removed": max(-lines_added, 0),
                    "occurrences": count,
                },
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Error editing file: {str(e)}"}


class CreateFileTool(BaseTool):
    name = "create_file"
    description = "Create a new file with content"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to workspace"},
            "content": {"type": "string", "description": "File content"},
        },
        "required": ["path", "content"],
    }
    risk_level = "low"
    permission_requirement = "confirmation"
    timeout = 10

    async def execute(self, path: str, content: str, **kwargs) -> dict:
        try:
            filepath = resolve_path(path, kwargs.get("workspace"))
            if filepath.exists():
                return {"success": False, "output": "", "error": f"File already exists: {path}"}

            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "output": f"Created {path} ({len(content)} bytes)",
                "metadata": {"size": len(content), "lines": content.count("\n") + 1},
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Error creating file: {str(e)}"}


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Delete a file"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to workspace"},
        },
        "required": ["path"],
    }
    risk_level = "high"
    permission_requirement = "confirmation"
    timeout = 10

    async def execute(self, path: str, **kwargs) -> dict:
        try:
            filepath = resolve_path(path, kwargs.get("workspace"))
            if not filepath.exists():
                return {"success": False, "output": "", "error": f"File not found: {path}"}
            if filepath.is_dir():
                return {"success": False, "output": "", "error": f"Is a directory: {path}"}

            filepath.unlink()
            return {"success": True, "output": f"Deleted {path}"}
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Error deleting file: {str(e)}"}
