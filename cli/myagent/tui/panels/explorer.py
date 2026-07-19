"""File explorer panel for MyAgent TUI - compact tree view with Git indicators."""

import os
from pathlib import Path
from typing import Optional

from rich.text import Text
from rich.tree import Tree


class ExplorerPanel:
    """Collapsible file explorer with Git indicators.
    
    Shows project directory structure with git status markers.
    No borders - just a clean tree view.
    """

    GIT_INDICATORS = {
        "M": ("M", "bold yellow"),
        "A": ("A", "bold green"),
        "D": ("D", "bold red"),
        "?": ("?", "bold magenta"),
        "R": ("R", "bold blue"),
    }

    SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv",
        "venv", ".egg-info", "dist", "build", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", ".tox", ".nox",
        ".idea", ".vscode", ".git",
    }
    SKIP_EXTENSIONS = {".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe"}

    def __init__(self, workspace: Path = Path(".")):
        self.workspace = workspace.resolve()
        self.selected: Optional[str] = None
        self.collapsed: set[str] = set()
        self.git_status: dict[str, str] = {}
        self.visible = True

    def toggle_visibility(self):
        self.visible = not self.visible

    def refresh(self):
        """Clear cache so tree is rebuilt."""
        pass

    def refresh_git_status(self):
        """Scan git status for indicators."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5,
                cwd=self.workspace,
            )
            if result.returncode == 0:
                self.git_status = {}
                for line in result.stdout.splitlines():
                    if len(line) > 3:
                        indicator = line[:2].strip()
                        filepath = line[3:].strip()
                        self.git_status[filepath] = indicator
        except Exception:
            pass

    def _build_tree(self, path: Path, parent: Optional[Tree] = None, depth: int = 0) -> Optional[Tree]:
        """Build a Rich Tree representation of the directory."""
        if depth > 3:
            return parent

        if parent is None:
            label = Text(f" {self.workspace.name}/", "bold")
            tree = Tree(label, guide_style="dim")
            parent_node = tree
        else:
            node_label = self._file_label(path)
            parent_node = parent.add(node_label)

        try:
            entries = sorted(
                path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            return parent_node if parent is None else parent

        for entry in entries:
            if entry.name.startswith(".") and entry.name not in (".env", ".gitignore"):
                continue
            rel = str(entry.relative_to(self.workspace))
            if entry.is_dir():
                if entry.name in self.SKIP_DIRS:
                    continue
                if rel in self.collapsed:
                    # Show as collapsed (▶)
                    label = Text(f"▶ {entry.name}/", "dim")
                    self._add_leaf(parent_node, label, rel)
                else:
                    self._build_tree(entry, parent_node, depth + 1)
            else:
                if entry.suffix in self.SKIP_EXTENSIONS:
                    continue
                label = self._file_label(entry)
                self._add_leaf(parent_node, label, rel)

        return tree if parent is None else parent

    def _file_label(self, path: Path) -> Text:
        """Create a styled label for a file entry."""
        rel = str(path.relative_to(self.workspace)) if path != self.workspace else ""
        name = path.name

        if path.is_dir():
            if rel and rel in self.collapsed:
                label = Text(f"▶ {name}/", "dim")
            else:
                label = Text(f"  {name}/", "cyan")
        else:
            # Determine color by extension
            ext_color = {
                ".py": "green", ".ts": "blue", ".js": "yellow",
                ".tsx": "blue", ".jsx": "yellow", ".css": "magenta",
                ".html": "red", ".json": "dim", ".md": "dim white",
                ".toml": "dim", ".yaml": "dim", ".yml": "dim",
            }.get(path.suffix, "white")
            label = Text(f"  {name}", ext_color)

        # Apply git status indicator
        if rel:
            git_ind = self.git_status.get(rel) or self.git_status.get(str(path.name))
            if git_ind:
                indicator, style = self.GIT_INDICATORS.get(git_ind, ("?", "dim"))
                label = Text(f"  {indicator}  {name}", style)

        if rel == self.selected:
            label.stylize("bold reverse")

        return label

    def _add_leaf(self, parent: Tree, label: Text, rel_path: str):
        parent.add(label)

    def __rich__(self) -> Text:
        if not self.visible:
            return Text("")

        self.refresh_git_status()
        tree = self._build_tree(self.workspace)
        if tree is None:
            return Text("  (empty)")
        return tree
