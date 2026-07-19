"""API endpoints for the Digital Twin intelligence system."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.intelligence.architecture_analyzer import ArchitectureAnalyzer
from backend.app.intelligence.dependency_graph import DependencyGraph
from backend.app.intelligence.impact_analysis import ImpactAnalysis
from backend.app.intelligence.project_graph import get_project_graph
from backend.app.intelligence.requirement_graph import RequirementGraph

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


@router.post("/refresh")
async def refresh_project_graph(workspace: str | None = None):
    """Refresh the project graph from the workspace."""
    graph = await get_project_graph(workspace or str(settings.workspace_path))
    snapshot = await graph.refresh()
    return {
        "status": "ok",
        "total_files": snapshot.total_files,
        "total_lines": snapshot.total_lines,
        "languages": snapshot.languages,
        "frameworks": snapshot.frameworks,
        "git_branch": snapshot.git_branch,
    }


@router.get("/graph")
async def get_graph(workspace: str | None = None):
    """Get the current project graph."""
    graph = await get_project_graph(workspace or str(settings.workspace_path))
    return graph.to_dict()


@router.get("/graph/query")
async def query_graph(
    q: str = Query(..., description="Search query"),
    workspace: str | None = None,
):
    """Search the project graph."""
    graph = await get_project_graph(workspace or str(settings.workspace_path))
    results = graph.query(q)
    return {
        "query": q,
        "results": [r.to_dict() for r in results],
        "count": len(results),
    }


@router.get("/dependencies")
async def get_dependencies(workspace: str | None = None):
    """Get the dependency graph."""
    graph = await get_project_graph(workspace or str(settings.workspace_path))
    dep_graph = DependencyGraph(graph.snapshot)
    dep_graph.build(graph.snapshot)
    return dep_graph.to_dict()


@router.get("/dependencies/{file_path:path}")
async def get_file_dependencies(
    file_path: str,
    workspace: str | None = None,
):
    """Get dependencies for a specific file."""
    graph = await get_project_graph(workspace or str(settings.workspace_path))
    dep_graph = DependencyGraph(graph.snapshot)
    dep_graph.build(graph.snapshot)

    deps = dep_graph.dependencies_of(file_path)
    dependents = dep_graph.dependents_of(file_path)
    transitive = dep_graph.transitive_dependents(file_path)

    return {
        "file": file_path,
        "dependencies": deps,
        "dependents": dependents,
        "transitive_dependents": list(transitive)[:20],
    }


@router.get("/architecture")
async def analyze_architecture(workspace: str | None = None):
    """Run full architecture analysis."""
    graph = await get_project_graph(workspace or str(settings.workspace_path))
    dep_graph = DependencyGraph(graph.snapshot)
    dep_graph.build(graph.snapshot)

    analyzer = ArchitectureAnalyzer()
    issues = analyzer.analyze(graph.snapshot, dep_graph)

    return {
        "summary": analyzer.summary(),
        "layers": dep_graph.layer_analysis(),
        "circular": dep_graph.circular_dependencies()[:10],
    }


@router.get("/impact/analyze")
async def analyze_impact(
    file_path: str = Query(..., description="File to analyze"),
    workspace: str | None = None,
):
    """Analyze the impact of changing a file."""
    graph = await get_project_graph(workspace or str(settings.workspace_path))
    dep_graph = DependencyGraph(graph.snapshot)
    dep_graph.build(graph.snapshot)

    analysis = ImpactAnalysis(graph.snapshot, dep_graph)
    return analysis.analyze_file_change(file_path)


@router.get("/impact/trace")
async def trace_requirement(
    requirement: str = Query(..., description="Requirement to trace"),
    workspace: str | None = None,
):
    """Trace a requirement through the architecture chain."""
    graph = await get_project_graph(workspace or str(settings.workspace_path))
    dep_graph = DependencyGraph(graph.snapshot)
    dep_graph.build(graph.snapshot)

    analysis = ImpactAnalysis(graph.snapshot, dep_graph)
    return analysis.trace_chain(requirement)


# Requirement Graph endpoints

@router.get("/requirements")
async def list_requirements(
    project_id: str = Query(...),
    status: str | None = None,
):
    """List requirements for a project."""
    rg = RequirementGraph()
    return await rg.list_requirements(project_id, status)


@router.get("/requirements/coverage")
async def requirement_coverage(
    project_id: str = Query(...),
):
    """Get requirement coverage statistics."""
    rg = RequirementGraph()
    return await rg.get_coverage(project_id)
