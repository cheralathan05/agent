"""Project Graph — continuously updated representation of the project.

Tracks:
- Files & directories
- Languages & frameworks
- Classes, functions, APIs, database entities
- Dependencies & services
- Tests & configuration
- Git information

Updated incrementally when files change (cached via file hashes).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from backend.app.config import settings


# ----- Data Structures -----

@dataclass
class FileNode:
    """A file in the project with its metadata."""
    path: str
    language: str | None = None
    size: int = 0
    hash: str = ""
    last_modified: float = 0.0
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    apis: list[dict[str, Any]] = field(default_factory=list)
    database_models: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    config_keys: list[str] = field(default_factory=list)
    is_test: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProjectSnapshot:
    """Full snapshot of the project at a point in time."""
    files: dict[str, FileNode] = field(default_factory=dict)
    languages: dict[str, int] = field(default_factory=dict)
    frameworks: list[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    git_branch: str = ""
    git_commit: str = ""
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    services: list[str] = field(default_factory=list)


# ----- Language classifiers -----

LANGUAGE_BY_EXT: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "React JSX", ".tsx": "React TSX",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".java": "Java", ".kt": "Kotlin", ".swift": "Swift",
    ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".c": "C",
    ".h": "C/C++ Header", ".hpp": "C++ Header",
    ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".toml": "TOML", ".xml": "XML", ".md": "Markdown",
    ".sql": "SQL", ".sh": "Shell", ".bash": "Shell",
    ".css": "CSS", ".scss": "SCSS", ".html": "HTML",
}

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", ".eggs", "dist", "build", ".next", ".nuxt",
    "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".myagent", ".idea", ".vscode", ".svn",
}

IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", "*.pyc", "*.pyo", "*.so", "*.dll", "*.dylib",
}


# ----- Extraction helpers -----

_CLASS_PATTERN = re.compile(
    r'^\s*(?:public\s+|private\s+|protected\s+|abstract\s+|sealed\s+)?'
    r'(?:class|interface|trait|struct|enum)\s+(\w+)',
    re.MULTILINE,
)
_FUNC_PATTERN_PY = re.compile(
    r'^\s*(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE
)
_FUNC_PATTERN_JS = re.compile(
    r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(|'
    r'(\w+)\s*\([^)]*\)\s*{)', re.MULTILINE
)
_IMPORT_PATTERN_PY = re.compile(
    r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', re.MULTILINE
)
_IMPORT_PATTERN_JS = re.compile(
    r'(?:import\s+.*?from\s+[\'"]([^\'"]+)[\'"]|require\s*\([\'"]([^\'"]+)[\'"]\))',
    re.MULTILINE,
)
_API_PATTERN = re.compile(
    r'@(?:app|router|api)\.(?:get|post|put|patch|delete|options)\s*\([\'"]([^\'"]+)[\'"]',
    re.MULTILINE,
)
_MODEL_PATTERN = re.compile(
    r'class\s+(\w+)\s*\(.*?\b(?:Base|Model|DeclarativeBase|db\.Model)\b',
    re.MULTILINE,
)


def _file_hash(path: Path) -> str:
    """Compute a fast hash of file content."""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _extract_python_info(content: str) -> dict[str, Any]:
    """Extract Python-specific symbols from file content."""
    classes = [m.group(1) for m in _CLASS_PATTERN.finditer(content)]
    functions = [m.group(1) for m in _FUNC_PATTERN_PY.finditer(content)]
    imports = [m.group(1) or m.group(2) for m in _IMPORT_PATTERN_PY.finditer(content) if m.group(1) or m.group(2)]
    apis = [{"method": m.group(0).split(".")[-1].split("(")[0].upper(), "path": m.group(1)}
            for m in _API_PATTERN.finditer(content)]
    models = [m.group(1) for m in _MODEL_PATTERN.finditer(content)]
    return {"classes": classes, "functions": functions, "imports": imports, "apis": apis, "models": models}


def _extract_js_info(content: str, ext: str) -> dict[str, Any]:
    """Extract JS/TS-specific symbols."""
    classes = [m.group(1) for m in _CLASS_PATTERN.finditer(content)]
    functions = []
    for m in _FUNC_PATTERN_JS.finditer(content):
        functions.append(m.group(1) or m.group(2) or m.group(3))
    imports = [m.group(1) or m.group(2) for m in _IMPORT_PATTERN_JS.finditer(content) if m.group(1) or m.group(2)]
    apis = []
    for m in re.finditer(r'(?:router|app|api)\.(get|post|put|patch|delete)\([\'"]([^\'"]+)[\'"]', content):
        apis.append({"method": m.group(1).upper(), "path": m.group(2)})
    return {"classes": classes, "functions": functions, "imports": imports, "apis": apis, "models": []}


# ----- Main Project Graph -----

class ProjectGraph:
    """Maintains an incrementally updated representation of the project."""

    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or settings.workspace_path).resolve()
        self.snapshot = ProjectSnapshot()
        self._file_hashes: dict[str, str] = {}  # path -> md5 hash
        self._dirty = True

    async def refresh(self) -> ProjectSnapshot:
        """Full refresh of the project graph."""
        self.snapshot = ProjectSnapshot()
        self._file_hashes = {}

        # Scan all files
        for filepath in self._walk():
            rel_path = str(filepath.relative_to(self.workspace))
            ext = filepath.suffix.lower()
            lang = LANGUAGE_BY_EXT.get(ext, "Unknown")

            file_hash = _file_hash(filepath)
            self._file_hashes[rel_path] = file_hash
            stats = filepath.stat()

            node = FileNode(
                path=rel_path,
                language=lang,
                size=stats.st_size,
                hash=file_hash,
                last_modified=stats.st_mtime,
                is_test="test" in rel_path.lower(),
            )

            # Extract symbols based on language
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""

            if content:
                if ext == ".py":
                    info = _extract_python_info(content)
                elif ext in (".js", ".ts", ".jsx", ".tsx"):
                    info = _extract_js_info(content, ext)
                else:
                    info = {"classes": [], "functions": [], "imports": [], "apis": [], "models": []}

                node.classes = info["classes"]
                node.functions = info["functions"]
                node.imports = info["imports"]
                node.apis = info["apis"]
                node.database_models = info["models"]
                node.config_keys = self._extract_config_keys(rel_path, content)

                # Count lines
                self.snapshot.total_lines += content.count("\n") + 1

            self.snapshot.files[rel_path] = node

        # Aggregate language stats
        lang_counts: dict[str, int] = {}
        for node in self.snapshot.files.values():
            if node.language and node.language != "Unknown":
                lang_counts[node.language] = lang_counts.get(node.language, 0) + 1
        self.snapshot.languages = dict(
            sorted(lang_counts.items(), key=lambda x: -x[1])
        )

        self.snapshot.total_files = len(self.snapshot.files)

        # Detect frameworks
        self.snapshot.frameworks = self._detect_frameworks()

        # Detect services (files with classes)
        self.snapshot.services = [
            n.path for n in self.snapshot.files.values() if n.classes
        ]

        # Git info
        git_info = await self._get_git_info()
        self.snapshot.git_branch = git_info.get("branch", "")
        self.snapshot.git_commit = git_info.get("commit", "")

        # Dependencies (build from imports)
        self.snapshot.dependencies = self._build_dependency_map()

        self._dirty = False
        return self.snapshot

    async def incremental_update(self, changed_files: list[str]) -> list[str]:
        """Update only the files that have changed. Returns list of changed files."""
        updated = []
        for rel_path in changed_files:
            full = self.workspace / rel_path
            if not full.exists():
                # File was deleted
                self.snapshot.files.pop(rel_path, None)
                self._file_hashes.pop(rel_path, None)
                updated.append(rel_path)
                continue

            new_hash = _file_hash(full)
            old_hash = self._file_hashes.get(rel_path)
            if new_hash != old_hash:
                # File changed — re-scan it
                await self.refresh()  # Full refresh for simplicity
                return [rel_path]

        return updated

    def _walk(self) -> list[Path]:
        """Walk the workspace and return all relevant file paths."""
        files = []
        for path in self.workspace.rglob("*"):
            if not path.is_file():
                continue
            # Skip ignored directories
            if any(part in IGNORE_DIRS for part in path.relative_to(self.workspace).parts):
                continue
            # Skip ignored files
            if path.name in IGNORE_FILES or path.suffix in {".pyc", ".pyo", ".so", ".dll", ".dylib"}:
                continue
            files.append(path)
        return files

    def _detect_frameworks(self) -> list[str]:
        """Detect frameworks from project files."""
        frameworks = []
        root_files = {f.name for f in self.workspace.iterdir() if f.is_file()}
        root_lower = {f.lower() for f in root_files}

        if "package.json" in root_files:
            frameworks.append("Node.js")
            try:
                pkg = json.loads((self.workspace / "package.json").read_text(encoding="utf-8"))
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    frameworks.append("Next.js")
                if "react" in deps:
                    frameworks.append("React")
                if "vue" in deps:
                    frameworks.append("Vue.js")
                if "express" in deps:
                    frameworks.append("Express.js")
            except Exception:
                pass

        if "requirements.txt" in root_lower or "pyproject.toml" in root_lower:
            frameworks.append("Python")
        if "Cargo.toml" in root_lower:
            frameworks.append("Rust/Cargo")
        if "go.mod" in root_lower:
            frameworks.append("Go")
        if "Gemfile" in root_lower:
            frameworks.append("Ruby")
        if "pom.xml" in root_lower or "build.gradle" in root_lower:
            frameworks.append("Java")

        return frameworks

    def _extract_config_keys(self, path: str, content: str) -> list[str]:
        """Extract configuration keys from config files."""
        keys = []
        name = path.lower()
        if name.endswith((".env", ".ini", ".cfg")):
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith(("#", ";")) and "=" in line:
                    keys.append(line.split("=")[0].strip())
        elif name.endswith(".json"):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    keys = list(data.keys())[:20]
            except json.JSONDecodeError:
                pass
        elif name.endswith((".yaml", ".yml")):
            for line in content.splitlines():
                if ":" in line and not line.strip().startswith("#"):
                    key = line.split(":")[0].strip()
                    if key and not key.startswith("-"):
                        keys.append(key)
        return keys[:20]

    def _build_dependency_map(self) -> dict[str, list[str]]:
        """Build a map of module -> list of modules it imports."""
        deps: dict[str, list[str]] = {}
        for node in self.snapshot.files.values():
            if node.imports:
                deps[node.path] = list(set(node.imports))
        return deps

    async def _get_git_info(self) -> dict[str, str]:
        """Get current Git branch and latest commit."""
        try:
            branch_proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "--abbrev-ref", "HEAD",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=str(self.workspace),
            )
            stdout, _ = await branch_proc.communicate()
            branch = stdout.decode().strip() if stdout else ""

            commit_proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "--short", "HEAD",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=str(self.workspace),
            )
            stdout, _ = await commit_proc.communicate()
            commit = stdout.decode().strip() if stdout else ""

            return {"branch": branch, "commit": commit}
        except Exception:
            return {"branch": "", "commit": ""}

    def query(self, q: str) -> list[FileNode]:
        """Search the project graph for files matching a query."""
        ql = q.lower()
        results = []
        for node in self.snapshot.files.values():
            if ql in node.path.lower():
                results.append(node)
                continue
            for cls in node.classes:
                if ql in cls.lower():
                    results.append(node)
                    break
            for fn in node.functions:
                if ql in fn.lower():
                    results.append(node)
                    break
        return results[:20]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot to a dict."""
        return {
            "total_files": self.snapshot.total_files,
            "total_lines": self.snapshot.total_lines,
            "languages": self.snapshot.languages,
            "frameworks": self.snapshot.frameworks,
            "git_branch": self.snapshot.git_branch,
            "git_commit": self.snapshot.git_commit,
            "services_count": len(self.snapshot.services),
            "files": {p: n.to_dict() for p, n in self.snapshot.files.items()},
        }


# Global graph instance (lazy initialized)
_project_graph: ProjectGraph | None = None


async def get_project_graph(workspace: str | Path | None = None) -> ProjectGraph:
    """Get or create the project graph, refreshing if needed."""
    global _project_graph
    if _project_graph is None:
        _project_graph = ProjectGraph(workspace)
        await _project_graph.refresh()
    elif _project_graph._dirty:
        await _project_graph.refresh()
    return _project_graph
