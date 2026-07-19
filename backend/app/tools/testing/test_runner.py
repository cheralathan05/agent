"""Test running tools using the verification runner singleton."""

from __future__ import annotations

from typing import Any

from backend.app.tools.base import BaseTool
from backend.app.verification.runner import verification_runner


class RunTestsTool(BaseTool):
    name = "run_tests"
    description = "Run tests in the workspace or a specific test file"
    input_schema = {"type": "object", "properties": {"test_path": {"type": "string", "default": ""}}, "required": []}
    risk_level = "safe"
    timeout = 120

    async def execute(self, test_path: str = "", **kwargs) -> dict[str, Any]:
        return await verification_runner.run_tests(
            test_path=test_path or None,
            workspace=kwargs.get("workspace"),
        )


class RunSpecificTestTool(BaseTool):
    name = "run_specific_test"
    description = "Run a specific test by name or path"
    input_schema = {"type": "object", "properties": {"test_name": {"type": "string"}, "test_file": {"type": "string", "default": ""}}, "required": ["test_name"]}
    risk_level = "safe"
    timeout = 60

    async def execute(self, test_name: str, test_file: str = "", **kwargs) -> dict[str, Any]:
        test_path = f"{test_file}::{test_name}" if test_file else test_name
        return await verification_runner.run_tests(
            test_path=test_path,
            workspace=kwargs.get("workspace"),
        )
