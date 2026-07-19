"""Path policy - validates file paths for workspace isolation."""

from __future__ import annotations

from pathlib import Path


class PathPolicy:
    """Validates paths against workspace boundaries."""

    # File extensions that should never be read or sent to LLM
    SENSITIVE_EXTENSIONS = {
        ".env", ".env.local", ".env.production",
        ".pem", ".key", ".cert", ".p12", ".pfx",
        ".keystore", ".jks",
        ".htpasswd", ".htaccess",
        ".gitconfig", ".netrc",
        "id_rsa", "id_dsa", "id_ecdsa",
    }

    # Directory names to skip
    IGNORED_DIRECTORIES = {
        ".git", "node_modules", "__pycache__", ".venv",
        "venv", ".tox", ".eggs", "dist", "build",
        ".next", ".nuxt", "coverage", ".nyc_output",
        ".sass-cache", ".mypy_cache", ".pytest_cache",
        ".ruff_cache", ".hypothesis",
    }

    # File extensions that should be scanned for secrets
    SECRET_SCAN_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
        ".rs", ".rb", ".php", ".sh", ".bash", ".zsh",
        ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
        ".env", ".env.*", ".terraform.*",
    }

    def __init__(self, workspace_root: str | Path | None = None):
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()

    def is_path_allowed(self, path: str | Path) -> bool:
        """Check if a path is within the allowed workspace."""
        try:
            resolved = (self.workspace_root / path).resolve()
            return str(resolved).startswith(str(self.workspace_root))
        except (ValueError, OSError):
            return False

    def is_file_allowed(self, filepath: str | Path) -> bool:
        """Check if a file can be read/edited."""
        filepath = Path(filepath)
        # Check extension-based restrictions
        ext = filepath.suffix.lower() if filepath.suffix else f".{filepath.name}"
        if ext in self.SENSITIVE_EXTENSIONS or filepath.name in self.SENSITIVE_EXTENSIONS:
            return False
        return self.is_path_allowed(filepath)

    def should_scan_for_secrets(self, filepath: str | Path) -> bool:
        """Check if a file should be scanned for secrets."""
        filepath = Path(filepath)
        ext = filepath.suffix.lower()
        name = filepath.name.lower()
        return ext in self.SECRET_SCAN_EXTENSIONS or name.startswith(".env")


# Global path policy
path_policy = PathPolicy()
