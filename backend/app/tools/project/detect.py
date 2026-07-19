"""Project detection tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.config import settings
from backend.app.tools.base import BaseTool


def detect_project_language(workspace: Path) -> str | None:
    """Detect the primary programming language of a project."""
    files = list(workspace.rglob("*"))
    extensions: dict[str, int] = {}
    for f in files:
        if f.is_file() and not f.name.startswith("."):
            ext = f.suffix.lower()
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1

    ext_map = {
        ".py": "Python",
        ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React JSX", ".tsx": "React TypeScript",
        ".go": "Go", ".rs": "Rust",
        ".java": "Java", ".kt": "Kotlin",
        ".rb": "Ruby", ".php": "PHP",
        ".swift": "Swift", ".c": "C", ".h": "C",
        ".cpp": "C++", ".hpp": "C++",
        ".cs": "C#", ".fs": "F#",
        ".scala": "Scala", ".ex": "Elixir",
        ".exs": "Elixir", ".erl": "Erlang",
    }

    best_lang = None
    best_count = 0
    for ext, count in extensions.items():
        lang = ext_map.get(ext)
        if lang and count > best_count:
            best_count = count
            best_lang = lang

    return best_lang


def detect_framework(workspace: Path) -> str | None:
    """Detect the framework used by the project."""
    files = {f.name for f in workspace.iterdir() if f.is_file()}

    frameworks = {
        "package.json": "Node.js",
        "requirements.txt": "Python",
        "pyproject.toml": "Python",
        "Cargo.toml": "Rust",
        "go.mod": "Go",
        "Gemfile": "Ruby",
        "composer.json": "PHP",
        "pom.xml": "Java/Maven",
        "build.gradle": "Java/Gradle",
        "CMakeLists.txt": "CMake",
        "Makefile": "Make",
    }

    for file_name, framework in frameworks.items():
        if file_name in files:
            return framework

    # Check for specific framework indicators
    if "package.json" in files:
        import json
        try:
            pkg = json.loads((workspace / "package.json").read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                return "Next.js"
            if "react" in deps:
                return "React"
            if "vue" in deps:
                return "Vue.js"
            if "express" in deps:
                return "Express.js"
            if "fastify" in deps:
                return "Fastify"
        except Exception:
            pass

    return None


class DetectLanguageTool(BaseTool):
    name = "detect_language"
    description = "Detect the primary programming language of the project"
    input_schema = {"type": "object", "properties": {}, "required": []}
    risk_level = "safe"
    timeout = 15

    async def execute(self, **kwargs) -> dict[str, Any]:
        ws = Path(kwargs.get("workspace") or settings.workspace_path).resolve()
        lang = detect_project_language(ws)
        return {"success": True, "output": lang or "Unknown", "metadata": {"language": lang}}


class DetectFrameworkTool(BaseTool):
    name = "detect_framework"
    description = "Detect the framework used by the project"
    input_schema = {"type": "object", "properties": {}, "required": []}
    risk_level = "safe"
    timeout = 15

    async def execute(self, **kwargs) -> dict[str, Any]:
        ws = Path(kwargs.get("workspace") or settings.workspace_path).resolve()
        framework = detect_framework(ws)
        return {"success": True, "output": framework or "Unknown", "metadata": {"framework": framework}}


class BuildProjectMapTool(BaseTool):
    name = "build_project_map"
    description = "Build a map of the project structure"
    input_schema = {
        "type": "object",
        "properties": {
            "max_depth": {"type": "integer", "description": "Max directory depth", "default": 3},
        },
        "required": [],
    }
    risk_level = "safe"
    timeout = 15

    async def execute(self, max_depth: int = 3, **kwargs) -> dict[str, Any]:
        ws = Path(kwargs.get("workspace") or settings.workspace_path).resolve()
        lines = []
        skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".myagent"}
        skip_extensions = {".pyc", ".pyo", ".o", ".obj", ".dll", ".so", ".dylib"}

        for path in sorted(ws.rglob("*")):
            # Skip ignored directories
            if any(part in skip_dirs for part in path.parts):
                continue
            # Skip binary/generated file types
            if path.suffix.lower() in skip_extensions:
                continue
            depth = len(path.relative_to(ws).parts)
            if depth > max_depth:
                continue
            indent = "  " * depth
            marker = "📁" if path.is_dir() else "📄"
            lines.append(f"{indent}{marker} {path.name}")

        return {
            "success": True,
            "output": "\n".join(lines) if lines else "No files found",
            "metadata": {"depth": max_depth, "file_count": len(lines)},
        }
