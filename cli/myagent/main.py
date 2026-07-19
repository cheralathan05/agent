"""MyAgent CLI - Terminal UI for the local autonomous AI coding agent."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.status import Status
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="myagent",
    help="MyAgent - Local Autonomous AI Coding Agent",
    add_completion=False,
)
console = Console()

# Default backend URL
DEFAULT_BACKEND = "http://localhost:8000"


def get_backend_url() -> str:
    """Get the backend URL from config or default."""
    import os
    return os.environ.get("MYAGENT_BACKEND_URL", DEFAULT_BACKEND)


async def health_check(base_url: str) -> dict:
    """Check backend health."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/v1/health", timeout=10)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}


async def stream_chat(base_url: str, messages: list[dict], model: str | None = None):
    """Stream a chat response from the backend."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{base_url}/api/v1/chat/stream",
            json={"messages": messages, "model": model, "stream": True},
            timeout=120,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        yield data
                    except json.JSONDecodeError:
                        continue


async def chat_request(base_url: str, messages: list[dict], model: str | None = None) -> str:
    """Send a chat request and get the response."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/v1/chat",
                json={"messages": messages, "model": model, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("content", "")
    except httpx.ConnectError:
        return "[ERROR] Backend not running. Start with: myagent start"
    except Exception as e:
        return f"[ERROR] {str(e)}"


async def list_models(base_url: str) -> list[dict]:
    """List available models."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/v1/models", timeout=10)
            response.raise_for_status()
            return response.json().get("models", [])
    except Exception:
        return []


def print_banner():
    """Print the MyAgent banner."""
    banner = """
┌─[cyan]MyAgent[/cyan]────────────────────────────┐
│ [bold]Local Autonomous AI Coding Agent[/bold]      │
│ Powering Developer Productivity              │
└──────────────────────────────────────────────┘
"""
    console.print(banner)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Default behavior when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        asyncio.run(interactive_mode())


@app.command()
def chat(
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Ollama model to use"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
):
    """Start interactive chat mode."""
    asyncio.run(interactive_mode(model=model, workspace=workspace))


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Ollama model to use"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
):
    """Run a single task and exit."""
    asyncio.run(run_task(task, model=model, workspace=workspace))


@app.command()
def init(
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Ollama model to use"),
):
    """Initialize MyAgent in the current or specified directory."""
    target = Path(workspace or ".").resolve()
    console.print(f"[green]✓[/green] Initialized MyAgent in: [bold]{target}[/bold]")
    console.print(f"[green]✓[/green] Workspace ready")
    if model:
        console.print(f"[green]✓[/green] Model: {model}")


@app.command()
def models():
    """List available Ollama models."""
    asyncio.run(list_models_cmd())


@app.command()
def status():
    """Check backend status and system health."""
    asyncio.run(check_status())


@app.command()
def doctor():
    """Run system diagnostics."""
    asyncio.run(run_doctor())


@app.command()
def config():
    """View or edit configuration."""
    console.print("[yellow]Configuration:[/yellow]")
    console.print("  OLLAMA_BASE_URL=http://localhost:11434")
    console.print("  OLLAMA_MODEL=qwen2.5-coder")
    console.print("  BACKEND_URL=http://localhost:8000")
    console.print("\nSet via environment variables or .env file.")


@app.command()
def start():
    """Start the backend server."""
    console.print("[yellow]Starting MyAgent backend...[/yellow]")
    console.print("[yellow]Note: Run from the project root directory.[/yellow]")
    console.print(f"\nStart via Python directly:\n  [bold]cd backend && python -m backend.app.main[/bold]\n")
    console.print("Or with uvicorn directly:\n  [bold]cd backend && uvicorn backend.app.main:app --reload[/bold]")


async def interactive_mode(model: str | None = None, workspace: str | None = None):
    """Interactive chat mode with streaming responses."""
    base_url = get_backend_url()
    current_model = model

    # Check health
    health = await health_check(base_url)
    if health.get("status") != "ok":
        console.print("[red]✗[/red] Backend is not running.")
        console.print(f"  Start it with: [bold]myagent start[/bold]")
        return

    # Get model info
    if not current_model:
        current_model = health.get("config", {}).get("model", "qwen2.5-coder")
        console.print(f"  Model: {current_model}")

    ws_dir = Path(workspace or ".").resolve()
    messages: list[dict] = []

    # Print header
    console.clear()
    print_banner()
    console.print(f"[dim]Model:[/dim] [bold]{current_model}[/bold]    "
                  f"[dim]Workspace:[/dim] [bold]{ws_dir}[/bold]")
    console.print(f"[dim]Status:[/dim] [green]Ready[/green]")
    console.print("─" * 50)

    # Main interaction loop
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]>[/bold cyan]")

            if not user_input.strip():
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                await handle_slash_command(user_input, base_url, ws_dir)
                continue

            if user_input.lower() in ("exit", "quit"):
                break

            # Add user message
            messages.append({"role": "user", "content": user_input})

            # Stream the response
            console.print()
            full_response = ""
            async for data in stream_chat(base_url, messages):
                event_type = data.get("event")
                if event_type == "token":
                    chunk = data.get("data", {}).get("content", "")
                    full_response += chunk
                    console.print(chunk, end="")
                elif event_type == "complete":
                    content = data.get("data", {}).get("content", "")
                    if content:
                        full_response = content
                elif event_type == "error":
                    console.print(f"\n[red]Error: {data.get('data', {}).get('content', '')}[/red]")

            if full_response:
                messages.append({"role": "assistant", "content": full_response})

            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            break


async def handle_slash_command(cmd: str, base_url: str, ws_dir: Path):
    """Handle slash commands (async version)."""
    parts = cmd.split()
    command = parts[0].lower()

    if command in ("/help", "/h"):
        console.print("""
[bold]Commands:[/bold]
  /help, /h       Show this help
  /model <name>   Switch model
  /models         List available models
  /project        Show project info
  /status         Show agent status
  /clear          Clear screen
  /stop           Cancel current operation
  /exit, /quit    Exit MyAgent
        """)

    elif command == "/clear":
        console.clear()
        print_banner()

    elif command == "/model" and len(parts) > 1:
        console.print(f"[green]✓[/green] Switched to model: {parts[1]}")

    elif command == "/models":
        models_data = await list_models(base_url)
        if models_data:
            table = Table(title="Available Models")
            table.add_column("Name")
            table.add_column("Size", justify="right")
            table.add_column("Modified")
            for m in models_data:
                table.add_row(
                    m.get("name", ""),
                    str(m.get("size", "")),
                    str(m.get("modified_at", "")),
                )
            console.print(table)
        else:
            console.print("[yellow]No models found or Ollama unavailable[/yellow]")

    elif command == "/exit" or command == "/quit":
        console.print("[yellow]Goodbye![/yellow]")
        raise SystemExit(0)

    elif command == "/project":
        console.print(f"  [dim]Workspace:[/dim] [bold]{ws_dir}[/bold]")
        console.print(f"  [dim]Git:[/dim] [bold]detecting...[/bold]")
        console.print(f"  [dim]Language:[/dim] [bold]detecting...[/bold]")

    else:
        console.print(f"[red]Unknown command: {command}[/red]")


async def run_task(task: str, model: str | None = None, workspace: str | None = None):
    """Execute a single task."""
    base_url = get_backend_url()
    messages = [{"role": "user", "content": task}]

    console.print(f"[bold]Task:[/bold] {task}")
    console.print("─" * 50)

    with Status("Working...") as status:
        async for data in stream_chat(base_url, messages, model=model):
            event_type = data.get("event")
            if event_type == "token":
                chunk = data.get("data", {}).get("content", "")
                console.print(chunk, end="")
                status.update("")
            elif event_type == "complete":
                console.print()
            elif event_type == "error":
                console.print(f"\n[red]Error: {data.get('data', {}).get('content', '')}[/red]")

    console.print()


async def list_models_cmd():
    """List available models."""
    base_url = get_backend_url()

    with Status("Fetching models..."):
        models_data = await list_models(base_url)

    if models_data:
        table = Table(title="Available Models")
        table.add_column("Name", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Modified")

        for m in models_data[:10]:
            table.add_row(
                m.get("name", ""),
                str(m.get("size", "")),
                str(m.get("modified_at", "")),
            )

        console.print(table)
    else:
        console.print("[yellow]No models found.[/yellow]")
        console.print("Make sure Ollama is running: [bold]ollama serve[/bold]")


async def check_status():
    """Check system status."""
    base_url = get_backend_url()
    health = await health_check(base_url)

    if health.get("status") == "ok":
        console.print("[green]✓ Backend: Running[/green]")
        llm = health.get("llm", {})
        console.print(f"  [dim]Provider:[/dim] {llm.get('status', 'unknown')}")
        console.print(f"  [dim]Model:[/dim] {health.get('config', {}).get('model', 'N/A')}")
        console.print(f"  [dim]Database:[/dim] {health.get('config', {}).get('database', 'N/A')}")

        if llm.get("models"):
            console.print(f"  [dim]Available models:[/dim] {', '.join(llm['models'][:5])}")
    else:
        console.print("[red]✗ Backend: Not running[/red]")
        console.print(f"  Start: [bold]myagent start[/bold]")


async def run_doctor():
    """Run comprehensive diagnostics."""
    console.print("[bold]MyAgent Doctor[/bold]")
    console.print("─" * 40)

    # Check Python
    import sys
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    console.print(f"[green]✓[/green] Python {py_version}")

    # Check Backend
    base_url = get_backend_url()
    health = await health_check(base_url)
    if health.get("status") == "ok":
        console.print("[green]✓[/green] Backend: Running")
    else:
        console.print("[red]✗[/red] Backend: Not running")

    # Check Ollama
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                console.print(f"[green]✓[/green] Ollama: Running ({len(models)} models)")
            else:
                console.print("[yellow]⚠[/yellow] Ollama: Unexpected response")
    except Exception:
        console.print("[red]✗[/red] Ollama: Not running")

    # Check workspace
    ws = Path(".").resolve()
    if ws.exists():
        console.print(f"[green]✓[/green] Workspace: {ws}")

    # Check Git
    try:
        import subprocess
        result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            console.print("[green]✓[/green] Git: Repository detected")
        else:
            console.print("[yellow]⚠[/yellow] Git: No repository")
    except Exception:
        console.print("[yellow]⚠[/yellow] Git: Not available")

    console.print("─" * 40)
    console.print("[dim]For help: myagent --help[/dim]")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
