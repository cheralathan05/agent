"""Main agent loop implementing the central decision-execution-observe cycle."""

from __future__ import annotations

import json
import time
from typing import Any

from backend.app.agent.context import ContextBuilder
from backend.app.agent.orchestrator import orchestrator
from backend.app.agent.state import AgentState
from backend.app.config import settings
from backend.app.llm.ollama import OllamaProvider
from backend.app.schemas.agent import AgentDecision
from backend.app.security.secret_detector import secret_detector
from backend.app.tools.registry import registry

SYSTEM_PROMPT = """You are MyAgent, a local autonomous AI coding agent.

You have access to tools that let you read, search, write, and execute code.

Your goal is to help the user with their coding tasks.

You must respond with structured decisions in JSON format:
{
    "thought_summary": "Brief summary of your reasoning",
    "action": "plan | tool_call | ask_user | replan | finish | error",
    "arguments": {},
    "reason": "Why you chose this action",
    "risk": "safe | low | medium | high"
}

Available actions:
- plan: Create a multi-step plan for complex tasks
- tool_call: Execute a tool (requires tool_name in arguments)
- ask_user: Ask the user for clarification
- replan: Revise the current plan
- finish: Task complete
- error: Report an error

Always choose the most appropriate action based on the current state."""


class AgentLoop:
    """The central agent loop."""

    def __init__(self):
        self.provider = OllamaProvider()

    async def run(
        self,
        session_id: str,
        goal: str,
        model: str | None = None,
        workspace: str | None = None,
    ) -> str:
        """Run the agent loop for a given goal."""
        run_id = await orchestrator.create_run(
            session_id=session_id,
            goal=goal,
            model=model,
            workspace=workspace,
        )

        state = AgentState(run_id=run_id, goal=goal)
        context = ContextBuilder(max_tokens=settings.context_limit)

        context.add_section("Goal", goal, priority=1)
        context.add_section(
            "Tools Available",
            "\n".join(
                f"- {t['name']}: {t['description']}" for t in registry.list_tools()
            ),
            priority=9,
        )

        await orchestrator.update_run(run_id, {"status": "running"})

        try:
            while state.should_continue():
                if not state.increment_step():
                    break

                # Redact secrets from context before sending to LLM
                safe_context = context.build()
                if secret_detector.contains_secrets(safe_context):
                    safe_context = secret_detector.redact(safe_context)

                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": safe_context},
                ]

                decision = await self._get_decision(
                    messages=messages,
                    model=model or settings.ollama_model,
                )

                state.add_to_history({
                    "step": state.step_number,
                    "decision": decision.model_dump(),
                })

                if decision.action == "finish":
                    await orchestrator.update_run(
                        run_id,
                        {
                            "status": "completed",
                            "result": decision.thought_summary,
                            "current_step": state.step_number,
                        },
                    )
                    return run_id

                elif decision.action == "plan":
                    state.plan = decision.arguments.get("tasks", [])
                    context.add_section(
                        "Plan",
                        json.dumps(state.plan, indent=2),
                        priority=2,
                    )

                elif decision.action == "tool_call":
                    tool_name = decision.arguments.get("tool_name", "")
                    tool_args = decision.arguments.get("arguments", {})

                    if not tool_name:
                        context.add_section(
                            "Observation",
                            "No tool_name specified in tool_call",
                            priority=3,
                        )
                        continue

                    # Pass run_id and workspace through to permission check
                    tool_args["run_id"] = run_id
                    if workspace:
                        tool_args["workspace"] = workspace

                    start = time.time()
                    result = await registry.execute(tool_name, **tool_args)
                    duration = int((time.time() - start) * 1000)

                    observation = result.get("output", "") or result.get("error", "No output")

                    # Handle approval requirements — poll until resolved
                    if result.get("requires_approval"):
                        approval_id = result.get("approval_id")
                        from backend.app.security.permissions import permission_engine

                        await orchestrator.update_run(
                            run_id,
                            {
                                "status": "waiting_for_approval",
                                "current_step": state.step_number,
                                "approval_id": approval_id,
                            },
                        )

                        context.add_section(
                            "Pending Approval",
                            f"Tool '{tool_name}' requires approval to {result.get('error', 'proceed')} (id={approval_id})\n"
                            f"Use /allow {approval_id} or /deny {approval_id} in the CLI, "
                            f"or use the web UI to respond.",
                            priority=1,
                        )

                        # Poll for approval resolution
                        max_polls = 300  # 5 minutes at 1s intervals
                        for _ in range(max_polls):
                            await asyncio.sleep(1)
                            resolution = await permission_engine.resolve_approval(approval_id)
                            if resolution["status"] == "approved":
                                # Grant permission and retry
                                await permission_engine.grant_permission(
                                    tool_name, resolution.get("permission_type", "once")
                                )
                                start = time.time()
                                result = await registry.execute(tool_name, **tool_args)
                                duration = int((time.time() - start) * 1000)
                                observation = result.get("output", "") or result.get("error", "No output")
                                context.add_section(
                                    "Tool Result",
                                    f"Tool: {tool_name}\nDuration: {duration}ms\nSuccess: {result.get('success', False)}\n\n{observation[:2000]}",
                                    priority=3,
                                )
                                state.tool_failures += (0 if result.get("success", False) else 1)
                                await orchestrator.update_run(run_id, {"status": "running"})
                                break
                            elif resolution["status"] == "denied":
                                context.add_section(
                                    "Observation",
                                    f"Tool '{tool_name}' was denied by user. Skipping.",
                                    priority=3,
                                )
                                await orchestrator.update_run(run_id, {"status": "running"})
                                break
                        else:
                            # Approval timed out
                            context.add_section(
                                "Observation",
                                f"Tool '{tool_name}' approval timed out after 5 minutes. Skipping.",
                                priority=3,
                            )
                        # Continue to next iteration after handling approval
                        continue

                    context.add_section(
                        "Tool Result",
                        f"Tool: {tool_name}\nDuration: {duration}ms\nSuccess: {result.get('success', False)}\n\n{observation[:2000]}",
                        priority=3,
                    )

                    state.tool_failures += (0 if result.get("success", False) else 1)

                elif decision.action == "ask_user":
                    await orchestrator.update_run(
                        run_id,
                        {
                            "status": "waiting",
                            "current_step": state.step_number,
                        },
                    )
                    context.add_section(
                        "User Question",
                        decision.thought_summary,
                        priority=1,
                    )

                elif decision.action == "replan":
                    context.clear()
                    context.add_section("Goal", goal, priority=1)

                elif decision.action == "error":
                    await orchestrator.update_run(
                        run_id,
                        {
                            "status": "failed",
                            "error": decision.thought_summary,
                            "current_step": state.step_number,
                        },
                    )
                    return run_id

        except Exception as e:
            await orchestrator.update_run(
                run_id,
                {"status": "failed", "error": str(e)},
            )

        return run_id

    async def _get_decision(
        self,
        messages: list[dict[str, str]],
        model: str,
    ) -> AgentDecision:
        """Get a structured decision from the LLM."""
        result = await self.provider.chat(
            messages=messages,
            model=model,
            temperature=0.1,
        )

        content = result.get("content", "")

        if not content:
            return AgentDecision(
                thought_summary="Failed to get model response",
                action="error",
                arguments={},
                reason="Empty response from model",
                risk="low",
            )

        try:
            cleaned = self._extract_json(content)
            if cleaned:
                data = json.loads(cleaned)
                return AgentDecision(**data)
        except (json.JSONDecodeError, ValueError):
            pass

        return AgentDecision(
            thought_summary=content[:500],
            action="finish",
            arguments={"raw_response": content},
            reason="Model returned non-structured response",
            risk="low",
        )

    def _extract_json(self, content: str) -> str | None:
        """Extract JSON from model output."""
        import re

        json_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL
        )
        if json_match:
            return json_match.group(1).strip()

        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            return brace_match.group(0).strip()

        return None
