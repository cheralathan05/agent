"""Agent-callable tools that expose the Digital Twin to the agent loop."""

from __future__ import annotations

from typing import Any

from backend.app.config import settings
from backend.app.intelligence.architecture_analyzer import ArchitectureAnalyzer
from backend.app.intelligence.dependency_graph import DependencyGraph
from backend.app.intelligence.impact_analysis import ImpactAnalysis
from backend.app.intelligence.project_graph import get_project_graph
from backend.app.tools.base import BaseTool


class QueryProjectGraphTool(BaseTool):
    name = "query_project_graph"
    description = "Search the project graph for files, classes, or functions matching a query"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term (file name, class name, function name)"},
        },
        "required": ["query"],
    }
    risk_level = "safe"
    timeout = 15

    async def execute(self, query: str, **kwargs) -> dict[str, Any]:
        """Search the project graph for matching files."""
        ws = kwargs.get("workspace") or str(settings.workspace_path)
        graph = await get_project_graph(ws)
        results = graph.query(query)
        return {
            "success": True,
            "output": "\n---\n".join(
                f"File: {r.path}\n  Language: {r.language}\n  Classes: {', '.join(r.classes) or 'none'}\n  Functions: {', '.join(r.functions[:5]) or 'none'}\n  APIs: {len(r.apis)} endpoint(s)"
                for r in results
            ) if results else f"No results for '{query}'",
            "metadata": {
                "count": len(results),
                "total_files": graph.snapshot.total_files,
                "languages": list(graph.snapshot.languages.keys()),
                "frameworks": graph.snapshot.frameworks,
                "git_branch": graph.snapshot.git_branch,
            },
        }


class AnalyzeDependenciesTool(BaseTool):
    name = "analyze_dependencies"
    description = "Analyze dependencies for a specific file"
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "File path relative to workspace"},
        },
        "required": ["file_path"],
    }
    risk_level = "safe"
    timeout = 15

    async def execute(self, file_path: str, **kwargs) -> dict[str, Any]:
        """Analyze dependencies for a file."""
        ws = kwargs.get("workspace") or str(settings.workspace_path)
        graph = await get_project_graph(ws)
        dep_graph = DependencyGraph(graph.snapshot)
        dep_graph.build(graph.snapshot)

        deps = dep_graph.dependencies_of(file_path)
        dependents = dep_graph.dependents_of(file_path)
        transitive = dep_graph.transitive_dependents(file_path)
        has_cycles = dep_graph.has_circular()

        return {
            "success": True,
            "output": f"Dependencies for {file_path}:\n"
                      f"  Direct imports: {len(deps)}\n"
                      f"  Direct dependents: {len(dependents)}\n"
                      f"  Transitive dependents: {len(transitive)}\n"
                      f"  Circular deps: {'Yes' if has_cycles else 'No'}"
                      + ("\n  Files that depend on this: " + ", ".join(dependents[:10]) if dependents else ""),
            "metadata": {
                "direct_dependencies": deps,
                "direct_dependents": dependents,
                "transitive_dependents": list(transitive)[:20],
                "has_circular": has_cycles,
            },
        }


class AnalyzeArchitectureTool(BaseTool):
    name = "analyze_architecture"
    description = "Analyze project architecture for violations, duplicate symbols, and layering issues"
    input_schema = {"type": "object", "properties": {}, "required": []}
    risk_level = "safe"
    timeout = 30

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Run full architecture analysis on the project."""
        ws = kwargs.get("workspace") or str(settings.workspace_path)
        graph = await get_project_graph(ws)
        dep_graph = DependencyGraph(graph.snapshot)
        dep_graph.build(graph.snapshot)

        analyzer = ArchitectureAnalyzer()
        issues = analyzer.analyze(graph.snapshot, dep_graph)
        summary = analyzer.summary()

        return {
            "success": True,
            "output": f"Architecture Analysis:\n"
                      f"  Health: {summary['health']}\n"
                      f"  Total issues: {summary['total_issues']}\n"
                      f"  By severity: {summary['by_severity']}\n"
                      f"  By type: {summary['by_type']}\n"
                      + ("\nTop issues:\n" + "\n".join(
                          f"  [{i['severity']}] {i['message'][:100]}"
                          for i in issues[:5]
                      ) if issues else "\n  No issues found."),
            "metadata": summary,
        }


class AnalyzeImpactTool(BaseTool):
    name = "analyze_impact"
    description = "Analyze the potential impact of modifying a file, including risk assessment"
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "File path relative to workspace"},
        },
        "required": ["file_path"],
    }
    risk_level = "safe"
    timeout = 15

    async def execute(self, file_path: str, **kwargs) -> dict[str, Any]:
        """Analyze impact of changing a file."""
        ws = kwargs.get("workspace") or str(settings.workspace_path)
        graph = await get_project_graph(ws)
        dep_graph = DependencyGraph(graph.snapshot)
        dep_graph.build(graph.snapshot)

        analysis = ImpactAnalysis(graph.snapshot, dep_graph)
        result = analysis.analyze_file_change(file_path)

        if "error" in result:
            return {"success": False, "output": result["error"], "metadata": {}}

        return {
            "success": True,
            "output": f"Impact Analysis for {file_path}:\n"
                      f"  Risk: {result['risk'].upper()}\n"
                      f"  Risk factors: {', '.join(result.get('risk_factors', [])) or 'none'}\n"
                      f"  Symbols: {len(result['symbols']['classes'])} classes, {len(result['symbols']['functions'])} functions, {len(result['symbols']['apis'])} APIs\n"
                      f"  Direct dependents: {result['dependents']['total_direct']} files\n"
                      f"  Transitive dependents: {result['dependents']['total_transitive']} files",
            "metadata": result,
        }
