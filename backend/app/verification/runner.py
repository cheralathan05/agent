"""Verification runner for validating code changes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.config import settings
from backend.app.database.models.verification_result import VerificationResult
from backend.app.database.session import SessionLocal
from backend.app.tools.utils import run_cmd_async


class VerificationRunner:
    """Runs verification checks on code changes."""

    async def verify_syntax(self, file_path: str, workspace: str | None = None) -> dict[str, Any]:
        """Check syntax of a file."""
        ws = Path(workspace or settings.workspace_path).resolve()
        full_path = ws / file_path

        if not full_path.exists():
            return {"status": "skipped", "reason": "File does not exist"}

        ext = full_path.suffix.lower()
        try:
            if ext == ".py":
                result = await run_cmd_async(
                    ["python", "-m", "py_compile", str(full_path)],
                    timeout=15,
                )
                return {
                    "status": "passed" if result.get("success") else "failed",
                    "details": result.get("stderr") if not result.get("success") else None,
                }
            elif ext in (".js", ".ts", ".jsx", ".tsx"):
                result = await run_cmd_async(
                    ["node", "--check", str(full_path)],
                    timeout=15,
                )
                return {
                    "status": "passed" if result.get("success") else "failed",
                    "details": result.get("stderr") if not result.get("success") else None,
                }
            elif ext in (".json",):
                import json
                try:
                    json.loads(full_path.read_text(encoding="utf-8"))
                    return {"status": "passed", "details": None}
                except json.JSONDecodeError as e:
                    return {"status": "failed", "details": str(e)}
            else:
                return {"status": "skipped", "reason": f"No syntax checker for {ext}"}
        except FileNotFoundError:
            return {"status": "skipped", "reason": "Syntax checker not found"}

    async def run_tests(
        self,
        test_path: str | None = None,
        workspace: str | None = None,
    ) -> dict[str, Any]:
        """Run tests in the workspace."""
        ws = Path(workspace or settings.workspace_path).resolve()
        cmd = ["python", "-m", "pytest", "-x", "--timeout=60", "-q"]
        if test_path:
            cmd.append(str(ws / test_path))

        result = await run_cmd_async(cmd, cwd=str(ws), timeout=120)
        output = result.get("stdout", "") + result.get("stderr", "")
        passed = result.get("success", False) and "failed" not in output.lower()

        return {
            "status": "passed" if passed else "failed",
            "details": output[:2000],
            "exit_code": result.get("exit_code", -1),
        }

    async def save_result(
        self,
        run_id: str,
        verification_type: str,
        status: str,
        target: str | None = None,
        details: str | None = None,
    ) -> str:
        """Save a verification result to the database."""
        db = SessionLocal()
        try:
            result = VerificationResult(
                run_id=run_id,
                verification_type=verification_type,
                status=status,
                target=target,
                details=details,
            )
            db.add(result)
            db.commit()
            return result.id
        finally:
            db.close()


# Global verification runner
verification_runner = VerificationRunner()
