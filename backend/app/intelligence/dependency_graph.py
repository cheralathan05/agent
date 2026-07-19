"""Dependency Graph — tracks import relationships and detects circular dependencies.

Maps relationships:
  Module A → Module B (A imports B)
  Circular dependency detection via DFS
  Call graph of services → controllers → repositories
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.app.intelligence.project_graph import FileNode, ProjectSnapshot


class DependencyGraph:
    """Analyzes and tracks dependencies between project modules."""

    def __init__(self, snapshot: ProjectSnapshot | None = None):
        self.snapshot = snapshot
        self._adjacency: dict[str, list[str]] = {}  # module -> [dependencies]
        self._reverse: dict[str, list[str]] = {}  # module -> [dependents]
        self._circular: list[list[str]] = []

    def build(self, snapshot: ProjectSnapshot):
        """Build the dependency graph from a project snapshot."""
        self.snapshot = snapshot
        self._adjacency = {}
        self._reverse = defaultdict(list)
        self._circular = []

        for path, node in snapshot.files.items():
            deps = []
            for imp in node.imports:
                # Resolve import to a project file path
                resolved = self._resolve_import(imp, path)
                if resolved:
                    deps.append(resolved)
            self._adjacency[path] = deps
            for dep in deps:
                self._reverse[dep].append(path)

        # Detect circular dependencies
        self._circular = self._find_circular()

    def _resolve_import(self, imp: str, from_path: str) -> str | None:
        """Resolve an import statement to a project file path."""
        if not self.snapshot:
            return None

        # Convert Python/JS import to file path
        module_path = imp.replace(".", "/")

        # Try common extensions
        for ext in (".py", ".js", ".ts", ".jsx", ".tsx", ""):
            candidate = f"{module_path}{ext}"
            if candidate in self.snapshot.files:
                return candidate

        # Try __init__ variants
        for ext in ("/__init__.py", "/index.js", "/index.ts"):
            candidate = f"{module_path}{ext}"
            if candidate in self.snapshot.files:
                return candidate

        return None

    def _find_circular(self) -> list[list[str]]:
        """Detect circular dependencies using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in self._adjacency}
        parent: dict[str, str | None] = {}
        cycles: list[list[str]] = []

        def dfs(node: str):
            color[node] = GRAY
            for neighbor in self._adjacency.get(node, []):
                if neighbor not in color:
                    color[neighbor] = WHITE
                if color[neighbor] == GRAY:
                    # Found a cycle — trace it
                    cycle = [neighbor, node]
                    curr = node
                    while curr != neighbor and parent.get(curr):
                        curr = parent[curr]
                        if curr != neighbor:
                            cycle.append(curr)
                    cycle.reverse()
                    cycles.append(cycle)
                elif color[neighbor] == WHITE:
                    parent[neighbor] = node
                    dfs(neighbor)
            color[node] = BLACK

        for node in list(self._adjacency.keys()):
            if color.get(node) == WHITE:
                dfs(node)

        return cycles

    def dependencies_of(self, path: str) -> list[str]:
        """Get direct dependencies of a module."""
        return self._adjacency.get(path, [])

    def dependents_of(self, path: str) -> list[str]:
        """Get modules that depend on a given module (reverse dependencies)."""
        return self._reverse.get(path, [])

    def transitive_dependencies(self, path: str, max_depth: int = 5) -> set[str]:
        """Get all transitive dependencies (breadth-first)."""
        visited: set[str] = set()
        queue = [path]
        for _ in range(max_depth):
            if not queue:
                break
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for dep in self._adjacency.get(current, []):
                if dep not in visited:
                    queue.append(dep)
        visited.discard(path)
        return visited

    def transitive_dependents(self, path: str, max_depth: int = 5) -> set[str]:
        """Get all transitive dependents (breadth-first)."""
        visited: set[str] = set()
        queue = [path]
        for _ in range(max_depth):
            if not queue:
                break
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for dep in self._reverse.get(current, []):
                if dep not in visited:
                    queue.append(dep)
        visited.discard(path)
        return visited

    def has_circular(self) -> bool:
        """Check if the project has circular dependencies."""
        return len(self._circular) > 0

    def circular_dependencies(self) -> list[list[str]]:
        """Get list of circular dependency chains."""
        return self._circular

    def iter_dependencies(self):
        """Iterate over all (source, deps) pairs in the graph.
        
        Yields:
            (source_path, list_of_dependency_paths) tuples.
        """
        for source, deps in self._adjacency.items():
            yield source, deps

    def layer_analysis(self) -> dict[str, list[str]]:
        """Classify files into architectural layers."""
        layers: dict[str, list[str]] = {
            "api": [],
            "controller": [],
            "service": [],
            "repository": [],
            "model": [],
            "utility": [],
            "config": [],
            "test": [],
        }
        if not self.snapshot:
            return layers

        for path in self.snapshot.files:
            pl = path.lower()
            if "test" in pl:
                layers["test"].append(path)
            elif "api" in pl or "route" in pl or "controller" in pl:
                layers["controller"].append(path)
            elif "service" in pl:
                layers["service"].append(path)
            elif "repo" in pl or "dao" in pl:
                layers["repository"].append(path)
            elif "model" in pl or "entity" in pl:
                layers["model"].append(path)
            elif "config" in pl or "setting" in pl:
                layers["config"].append(path)
            elif "util" in pl or "helper" in pl or "common" in pl:
                layers["utility"].append(path)
            else:
                layers["api"].append(path)

        return layers

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for API responses."""
        return {
            "total_modules": len(self._adjacency),
            "circular_count": len(self._circular),
            "circular": self._circular[:10],
            "layers": {k: len(v) for k, v in self.layer_analysis().items()},
        }
