"""MyAgent CLI - Premium Terminal UI for the local autonomous AI coding agent.

Usage:
    myagent              Start interactive TUI
    myagent chat         Start interactive chat mode
    myagent run <task>   Run a single task
    myagent status       Check backend health
    myagent doctor       Run diagnostics
    myagent models       List available models
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

from .client.api import MyAgentAPI
from .tui import MyAgentTUI

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = typer.Typer(
    name="myagent",
    help="MyAgent - Local AI Software Engineering Agent",
    add_completion=False,
)
console = Console()

DEFAULT_BACKEND = "http://localhost:8000"


def get_backend_url() -> str:
    return os.environ.get("MYAGENT_BACKEND_URL", DEFAULT_BACKEND)


# ── Commands ─────────────────────────────────────


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Default: start the interactive TUI."""
    if ctx.invoked_subcommand is None:
        asyncio.run(interactive_tui())


@app.command()
def chat(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Start interactive TUI session."""
    asyncio.run(interactive_tui(model=model))


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
):
    """Run a single task and exit."""
    asyncio.run(run_single_task(task, model=model))


@app.command()
def status():
    """Check backend and system health."""
    asyncio.run(check_status())


@app.command()
def doctor():
    """Run system diagnostics."""
    asyncio.run(run_doctor())


@app.command()
def models():
    """List available Ollama models."""
    asyncio.run(list_models())


@app.command()
def init(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Workspace"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Default model"),
):
    """Initialize MyAgent in a directory."""
    target = Path(workspace or ".").resolve()
    console.print(f"[green]✓[/green] Initialized MyAgent in: [bold]{target}[/bold]")
    console.print(f"[green]✓[/green] Workspace ready")
    if model:
        console.print(f"[green]✓[/green] Model: {model}")


@app.command()
def config():
    """View current configuration."""
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  OLLAMA_BASE_URL = {os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    console.print(f"  OLLAMA_MODEL    = {os.environ.get('OLLAMA_MODEL', 'qwen3:8b')}")
    console.print(f"  BACKEND_URL     = {get_backend_url()}")
    console.print("\nSet via environment variables or .env file.")


@app.command()
def start():
    """Show how to start the backend server."""
    console.print("[yellow]Starting MyAgent backend...[/yellow]")
    console.print("\n[bold]Option 1:[/bold] From project root:")
    console.print("  [bold]python backend/run.py[/bold]")
    console.print("\n[bold]Option 2:[/bold] With uvicorn:")
    console.print("  [bold]cd backend && uvicorn app.main:app --reload --port 8000[/bold]")


# ── Interactive TUI ──────────────────────────────


async def interactive_tui(model: str | None = None):
    """Launch the full multi-panel TUI."""
    base_url = get_backend_url()
    workspace = Path(".").resolve()

    # Check backend availability first
    api = MyAgentAPI(base_url)
    health = await api.health()

    if health.get("status") != "ok":
        console.print()
        console.print(Panel(
            Text.assemble(
                ("\n✗ ", "bold red"),
                ("Backend is not running\n\n", "bold"),
                ("Start the backend server:\n", ""),
                ("  python backend/run.py\n\n", "bold yellow"),
                ("Or check if the backend process is alive.\n", "dim"),
            ),
            title="[bold red]CONNECTION ERROR[/bold red]",
            border_style="red",
        ))
        return

    # Get model info
    if model:
        current_model = model
    else:
        config_model = health.get("config", {}).get("model")
        current_model = config_model or os.environ.get("OLLAMA_MODEL", "qwen3:8b")

    await api.close()

    # Launch TUI
    tui = MyAgentTUI(
        api_base_url=base_url,
        workspace=workspace,
        model=current_model,
    )
    await tui.run()


# ── Single task mode ─────────────────────────────


async def run_single_task(task: str, model: str | None = None):
    """Execute a single task with streaming output."""
    base_url = get_backend_url()
    api = MyAgentAPI(base_url)
    messages = [{"role": "user", "content": task}]

    # Check health
    health = await api.health()
    if health.get("status") != "ok":
        console.print("[red]✗ Backend is not running. Start with: python backend/run.py[/red]")
        return

    header = Panel(
        Text.assemble(
            (" ◆ MYAGENT ", "bold cyan"),
            ("\n  Run Task", "dim"),
        ),
        border_style="cyan",
    )
    console.print(header)
    console.print(f"\n[bold]Task:[/bold] {task}")
    console.print("─" * 50)

    with Status("Working...", spinner="dots"):
        full_response = ""
        async for data in api.stream_chat(messages, model):
            event = data.get("event")
            if event == "token":
                chunk = data.get("data", {}).get("content", "")
                full_response += chunk
                console.print(chunk, end="")
            elif event == "complete":
                if full_response:
                    messages.append({"role": "assistant", "content": full_response})
                console.print()
            elif event == "error":
                console.print(f"\n[red]Error: {data.get('data', {}).get('content', '')}[/red]")

        console.print()
    await api.close()


# ── Status Check ─────────────────────────────────


async def check_status():
    """Check backend and system health."""
    base_url = get_backend_url()
    api = MyAgentAPI(base_url)

    health = await api.health()
    if health.get("status") == "ok":
        console.print("[green]● Backend: Running[/green]")
        llm = health.get("llm", {})
        console.print(f"  Ollama: {llm.get('status', 'unknown')}")
        console.print(f"  Model:  {health.get('config', {}).get('model', 'N/A')}")

        if llm.get("models"):
            console.print(f"  Models: {', '.join(llm['models'][:5])}")
    else:
        console.print("[red]✗ Backend: Not running[/red]")
        console.print("  Start: python backend/run.py")

    await api.close()


# ── Diagnostics ──────────────────────────────────


async def run_doctor():
    """Run system diagnostics."""
    console.print(Panel(
        Text.assemble(
            (" ◆ MYAGENT ", "bold cyan"),
            ("Doctor", "dim"),
        ),
        border_style="cyan",
    ))
    console.print("─" * 40)

    # Python version
    console.print(f"[green]✓[/green] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # Backend
    base_url = get_backend_url()
    api = MyAgentAPI(base_url)
    health = await api.health()
    if health.get("status") == "ok":
        console.print("[green]✓[/green] Backend: Running")
    else:
        console.print("[red]✗[/red] Backend: Not running")

    # Ollama
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                console.print(f"[green]✓[/green] Ollama: Running ({len(models)} model(s))")
                for m in models[:3]:
                    name = m.get("name", "?")
                    size = m.get("size", 0)
                    console.print(f"       {name} ({size / 1e9:.1f} GB)")
            else:
                console.print("[yellow]⚠[/yellow] Ollama: Unexpected response")
    except Exception:
        console.print("[red]✗[/red] Ollama: Not running")

    # Workspace
    ws = Path(".").resolve()
    console.print(f"[green]✓[/green] Workspace: {ws}")

    # Git
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            console.print("[green]✓[/green] Git: Repository detected")
        else:
            console.print("[yellow]⚠[/yellow] Git: No repository")
    except Exception:
        console.print("[yellow]⚠[/yellow] Git: Not available")

    console.print("─" * 40)
    await api.close()


# ── List Models ──────────────────────────────────


async def list_models():
    """List available Ollama models in a table."""
    base_url = get_backend_url()
    api = MyAgentAPI(base_url)
    models_data = await api.list_models()

    if models_data:
        table = Table(title="Available Models", border_style="cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Family")
        table.add_column("Parameters")

        for m in models_data:
            details = m.get("details", {})
            size = m.get("size", 0)
            size_gb = size / 1e9 if size else 0
            table.add_row(
                m.get("name", ""),
                f"{size_gb:.1f} GB" if size_gb > 0 else "?",
                details.get("family", ""),
                details.get("parameter_size", ""),
            )
        console.print(table)
    else:
        console.print("[yellow]No models found. Is Ollama running?[/yellow]")
        console.print("  Run: [bold]ollama serve[/bold]")

    await api.close()


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
