"""Impact Analysis — predicts the impact of modifications before execution.

Traces chains:
  Requirement → API → Controller → Service → Repository → Database Model → Tests

Analyzes risk (LOW/MEDIUM/HIGH) based on:
  - Number of files affected
  - Depth of dependency chain
  - Whether database models or public APIs change
"""

from __future__ import annotations

from typing import Any

from backend.app.intelligence.dependency_graph import DependencyGraph
from backend.app.intelligence.project_graph import ProjectSnapshot


class ImpactAnalysis:
    """Predicts the impact of proposed modifications."""

    def __init__(self, snapshot: ProjectSnapshot | None = None, dep_graph: DependencyGraph | None = None):
        self.snapshot = snapshot
        self.dep_graph = dep_graph

    def analyze_file_change(self, file_path: str) -> dict[str, Any]:
        """Analyze the impact of changing a specific file."""
        if not self.snapshot or not self.dep_graph:
            return {"error": "Project not loaded", "risk": "unknown"}

        # Find the file in the project
        if file_path not in self.snapshot.files:
            return {"error": f"File not found: {file_path}", "risk": "unknown"}

        node = self.snapshot.files[file_path]

        # Direct dependents: files that import this one
        direct_dependents = self.dep_graph.dependents_of(file_path)
        transitive_dependents = self.dep_graph.transitive_dependents(file_path)

        # Files that this file depends on
        dependencies = self.dep_graph.dependencies_of(file_path)

        # Check if this is a high-impact file
        is_model = bool(node.database_models)
        is_api = bool(node.apis)
        is_config = bool(node.config_keys)
        is_test = node.is_test

        # Risk assessment
        risk_factors = []
        if is_model:
            risk_factors.append("database model change")
        if is_api:
            risk_factors.append("API endpoint change")
        if len(transitive_dependents) > 10:
            risk_factors.append(f"affects {len(transitive_dependents)} files transitively")
        if is_config:
            risk_factors.append("configuration change")

        if is_model or len(transitive_dependents) > 20:
            risk = "high"
        elif len(transitive_dependents) > 5 or is_api or is_config:
            risk = "medium"
        elif is_test:
            risk = "low"
        else:
            risk = "low"

        return {
            "file": file_path,
            "risk": risk,
            "risk_factors": risk_factors,
            "symbols": {
                "classes": node.classes,
                "functions": node.functions,
                "apis": node.apis,
                "database_models": node.database_models,
            },
            "dependencies": {
                "direct": dependencies,
                "count": len(dependencies),
            },
            "dependents": {
                "direct": direct_dependents,
                "transitive": list(transitive_dependents),
                "total_direct": len(direct_dependents),
                "total_transitive": len(transitive_dependents),
            },
        }

    def analyze_symbol_change(self, symbol: str, kind: str = "class") -> dict[str, Any]:
        """Analyze the impact of changing a specific symbol (class or function)."""
        if not self.snapshot:
            return {"error": "Project not loaded"}

        # Find files containing this symbol
        affected_files = []
        for path, node in self.snapshot.files.items():
            if kind == "class" and symbol in node.classes:
                affected_files.append(path)
            elif kind == "function" and symbol in node.functions:
                affected_files.append(path)

        if not affected_files:
            return {"error": f"Symbol '{symbol}' not found", "risk": "unknown"}

        # Aggregate impact across all files containing the symbol
        all_dependents: set[str] = set()
        for f in affected_files:
            if self.dep_graph:
                all_dependents.update(self.dep_graph.transitive_dependents(f))

        return {
            "symbol": symbol,
            "kind": kind,
            "files_defined_in": affected_files,
            "total_affected_files": len(affected_files) + len(all_dependents),
            "transitive_dependents": list(all_dependents)[:20],
            "risk": "high" if len(all_dependents) > 5 else "medium",
        }

    def trace_chain(self, requirement: str) -> dict[str, Any]:
        """Trace a requirement through the architecture chain.
        
        Requirement → API → Controller → Service → Repository → Model → Tests
        """
        if not self.snapshot:
            return {"error": "Project not loaded"}

        rl = requirement.lower()
        chain: dict[str, list[str]] = {
            "requirement": [requirement],
            "api": [],
            "controller": [],
            "service": [],
            "repository": [],
            "model": [],
            "test": [],
        }

        for path, node in self.snapshot.files.items():
            pl = path.lower()

            if rl in pl or any(rl in cls.lower() for cls in node.classes):
                # Classify into chain
                if node.apis:
                    chain["api"].append(path)
                if any(x in pl for x in ("controller", "route", "endpoint")):
                    chain["controller"].append(path)
                if "service" in pl:
                    chain["service"].append(path)
                if any(x in pl for x in ("repo", "dao", "repository")):
                    chain["repository"].append(path)
                if node.database_models:
                    chain["model"].append(path)
                if "test" in pl:
                    chain["test"].append(path)

        # Remove empty layers
        chain = {k: v for k, v in chain.items() if v}

        return {
            "requirement": requirement,
            "chain": chain,
            "coverage": {
                "has_api": len(chain.get("api", [])) > 0,
                "has_controller": len(chain.get("controller", [])) > 0,
                "has_service": len(chain.get("service", [])) > 0,
                "has_model": len(chain.get("model", [])) > 0,
                "has_tests": len(chain.get("test", [])) > 0,
            },
            "missing_gaps": [
                layer for layer in ["api", "controller", "service", "model", "test"]
                if layer not in chain
            ],
        }
