"""Architecture Analyzer — detects drift, violations, and anti-patterns.

Detects:
- Duplicate services (same class/function defined in multiple places)
- Circular dependencies (delegates to DependencyGraph)
- Unused modules (no imports from other project files)
- Incorrect layering (controller imports from controller, etc.)
- High coupling / low cohesion
- Architecture rule violations
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from backend.app.intelligence.dependency_graph import DependencyGraph
from backend.app.intelligence.project_graph import ProjectSnapshot


class ArchitectureAnalyzer:
    """Analyzes project architecture for violations and anti-patterns."""

    def __init__(self, snapshot: ProjectSnapshot | None = None):
        self.snapshot = snapshot
        self._issues: list[dict[str, Any]] = []

    def analyze(self, snapshot: ProjectSnapshot, dep_graph: DependencyGraph) -> list[dict[str, Any]]:
        """Run all architecture checks and return a list of issues."""
        self.snapshot = snapshot
        self._issues = []

        self._check_duplicate_symbols()
        self._check_unused_modules(dep_graph)
        self._check_layering_violations(dep_graph)
        self._check_circular_dependencies(dep_graph)
        self._check_high_coupling()
        self._check_large_modules()

        return self._issues

    def _check_duplicate_symbols(self):
        """Detect classes/functions defined in multiple files."""
        if not self.snapshot:
            return
        class_locations: dict[str, list[str]] = {}
        func_locations: dict[str, list[str]] = {}

        for path, node in self.snapshot.files.items():
            for cls in node.classes:
                class_locations.setdefault(cls, []).append(path)
            for fn in node.functions:
                func_locations.setdefault(fn, []).append(path)

        # Report duplicates
        for cls, files in class_locations.items():
            if len(files) > 1:
                self._issues.append({
                    "type": "duplicate_symbol",
                    "severity": "warning",
                    "symbol": cls,
                    "kind": "class",
                    "files": files,
                    "message": f"Class '{cls}' defined in {len(files)} files: {', '.join(files)}",
                })

        for fn, files in func_locations.items():
            if len(files) > 1:
                self._issues.append({
                    "type": "duplicate_symbol",
                    "severity": "info",
                    "symbol": fn,
                    "kind": "function",
                    "files": files,
                    "message": f"Function '{fn}' defined in {len(files)} files: {', '.join(files)}",
                })

    def _check_unused_modules(self, dep_graph: DependencyGraph):
        """Detect files that no other project file imports."""
        if not self.snapshot:
            return
        for path in self.snapshot.files:
            # Skip test files, config files, and entry points
            pl = path.lower()
            if any(skip in pl for skip in ("test", "config", "settings", "__init__", "main")):
                continue
            # Check if anything depends on this module
            dependents = dep_graph.dependents_of(path)
            if not dependents:
                self._issues.append({
                    "type": "unused_module",
                    "severity": "info",
                    "file": path,
                    "message": f"Module '{path}' is not imported by any other project file",
                })

    def _check_layering_violations(self, dep_graph: DependencyGraph):
        """Detect violations of architectural layering."""
        layers = dep_graph.layer_analysis()
        layer_map: dict[str, list[str]] = {}
        for layer, files in layers.items():
            for f in files:
                layer_map[f] = layer

        # Define allowed dependency directions
        allowed_edges = {
            "controller": {"service", "model", "utility", "config"},
            "service": {"repository", "model", "utility", "config"},
            "repository": {"model", "utility", "config"},
            "model": {"utility", "config"},
            "utility": {"config"},
            "config": set(),
            "test": {"api", "controller", "service", "repository", "model", "utility", "config"},
        }

        for path, deps in dep_graph.iter_dependencies():
            source_layer = layer_map.get(path)
            if not source_layer or source_layer not in allowed_edges:
                continue
            allowed = allowed_edges[source_layer]
            for dep in deps:
                target_layer = layer_map.get(dep)
                if target_layer and target_layer not in allowed:
                    self._issues.append({
                        "type": "layering_violation",
                        "severity": "warning",
                        "file": path,
                        "depends_on": dep,
                        "message": f"'{path}' ({source_layer}) should not depend on '{dep}' ({target_layer})",
                    })

    def _check_circular_dependencies(self, dep_graph: DependencyGraph):
        """Report circular dependencies."""
        for cycle in dep_graph.circular_dependencies():
            self._issues.append({
                "type": "circular_dependency",
                "severity": "error",
                "cycle": cycle,
                "message": f"Circular dependency: {' → '.join(cycle)}",
            })

    def _check_high_coupling(self):
        """Detect modules with excessive dependencies (>10 imports)."""
        if not self.snapshot:
            return
        for path, node in self.snapshot.files.items():
            if len(node.imports) > 10:
                self._issues.append({
                    "type": "high_coupling",
                    "severity": "warning",
                    "file": path,
                    "import_count": len(node.imports),
                    "message": f"'{path}' has {len(node.imports)} imports (high coupling)",
                })

    def _check_large_modules(self):
        """Detect files that are excessively large (>500 lines)."""
        if not self.snapshot:
            return
        for path, node in self.snapshot.files.items():
            # Estimate lines from file size (rough heuristic)
            if node.language in ("Python", "JavaScript", "TypeScript", "Go", "Java", "C#", "C++"):
                # Check actual content
                try:
                    from pathlib import Path
                    from backend.app.config import settings
                    full = Path(settings.workspace_path) / path
                    if full.exists():
                        lines = len(full.read_text(encoding="utf-8", errors="ignore").splitlines())
                        if lines > 500:
                            self._issues.append({
                                "type": "large_module",
                                "severity": "info",
                                "file": path,
                                "lines": lines,
                                "message": f"'{path}' has {lines} lines (consider splitting)",
                            })
                except Exception:
                    pass

    def summary(self) -> dict[str, Any]:
        """Get a summary of architecture health."""
        by_severity = Counter(i["severity"] for i in self._issues)
        by_type = Counter(i["type"] for i in self._issues)
        return {
            "total_issues": len(self._issues),
            "by_severity": dict(by_severity),
            "by_type": dict(by_type),
            "health": "good" if len(self._issues) == 0 else "fair" if by_severity.get("error", 0) == 0 else "poor",
            "issues": self._issues,
        }
