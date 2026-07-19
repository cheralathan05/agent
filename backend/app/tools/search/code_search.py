"""Code and file search tools using ripgrep-style search."""

import os
import re
import subprocess
from pathlib import Path

from backend.app.tools.base import BaseTool
from backend.app.tools.utils import resolve_path


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Search for files matching a glob pattern"
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern (e.g., *.py, **/*.ts)"},
            "directory": {"type": "string", "description": "Directory to search, relative to workspace", "default": "."},
        },
        "required": ["pattern"],
    }
    risk_level = "safe"
    timeout = 15

    async def execute(self, pattern: str, directory: str = ".", **kwargs) -> dict:
        try:
            search_dir = resolve_path(directory, kwargs.get("workspace"))
            if not search_dir.exists():
                return {"success": False, "output": "", "error": f"Directory not found: {directory}"}

            from glob import iglob
            results = []
            for p in iglob(pattern, root_dir=search_dir, recursive=True):
                results.append(p)

            results.sort()
            return {
                "success": True,
                "output": "\n".join(results[:100]) if results else "No files found",
                "metadata": {"count": len(results), "truncated": len(results) > 100},
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Error searching files: {str(e)}"}


class SearchCodeTool(BaseTool):
    name = "search_code"
    description = "Search for code patterns in the project"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text to search for"},
            "directory": {"type": "string", "description": "Directory to search", "default": "."},
            "file_pattern": {"type": "string", "description": "Optional file pattern filter", "default": ""},
            "max_results": {"type": "integer", "description": "Max results to return", "default": 50},
        },
        "required": ["query"],
    }
    risk_level = "safe"
    timeout = 30

    async def execute(
        self,
        query: str,
        directory: str = ".",
        file_pattern: str = "",
        max_results: int = 50,
        **kwargs,
    ) -> dict:
        try:
            search_dir = resolve_path(directory, kwargs.get("workspace"))
            if not search_dir.exists():
                return {"success": False, "output": "", "error": f"Directory not found: {directory}"}

            results = []
            try:
                if os.name == "nt":
                    cmd = ["findstr", "/s", "/n", query, str(search_dir / "*")]
                else:
                    cmd = ["grep", "-r", "-n", query, str(search_dir)]
                    if file_pattern:
                        cmd.extend(["--include", file_pattern])
                    cmd.extend(["--exclude-dir=.git", "--exclude-dir=node_modules"])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                lines = [l for l in result.stdout.split("\n") if l.strip()][:max_results]
                results = lines
            except Exception:
                # Fallback to pure Python walk
                for r, _, files in os.walk(search_dir):
                    for f in files:
                        if f.startswith("."):
                            continue
                        fpath = Path(r) / f
                        try:
                            content = fpath.read_text(encoding="utf-8", errors="ignore")
                            for i, line in enumerate(content.split("\n"), 1):
                                if query.lower() in line.lower():
                                    rel = fpath.relative_to(search_dir)
                                    results.append(f"{rel}:{i}: {line.strip()[:200]}")
                                    if len(results) >= max_results:
                                        break
                        except Exception:
                            continue

            return {
                "success": True,
                "output": "\n".join(results[:max_results]) if results else f"No results for '{query}'",
                "metadata": {"count": len(results)},
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Error searching code: {str(e)}"}


class RegexSearchTool(BaseTool):
    name = "regex_search"
    description = "Search for patterns in files using regex"
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "directory": {"type": "string", "description": "Directory to search", "default": "."},
            "max_results": {"type": "integer", "description": "Max results", "default": 50},
        },
        "required": ["pattern"],
    }
    risk_level = "safe"
    timeout = 30

    async def execute(self, pattern: str, directory: str = ".", max_results: int = 50, **kwargs) -> dict:
        try:
            search_dir = resolve_path(directory, kwargs.get("workspace"))
            if not search_dir.exists():
                return {"success": False, "output": "", "error": f"Directory not found: {directory}"}

            results = []
            compiled = re.compile(pattern)

            for r, dirs, files in os.walk(search_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
                for f in files:
                    if f.startswith("."):
                        continue
                    fpath = Path(r) / f
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        for i, line in enumerate(content.split("\n"), 1):
                            if compiled.search(line):
                                rel = fpath.relative_to(search_dir)
                                results.append(f"{rel}:{i}: {line.strip()[:200]}")
                                if len(results) >= max_results:
                                    break
                    except Exception:
                        continue

            return {
                "success": True,
                "output": "\n".join(results[:max_results]) if results else "No matches for pattern",
                "metadata": {"count": len(results)},
            }
        except ValueError as e:
            return {"success": False, "output": "", "error": str(e)}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Error in regex search: {str(e)}"}
