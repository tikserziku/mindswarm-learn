"""Challenge 6: Structured Outputs + Support Chatbot.

Course: Tool Use, Lessons 4-5
  - Lesson 4: Complete workflow with structured outputs
  - Lesson 5: Multi-tool chatbot

The support chatbot is the first Claude-powered feature
exposed directly to end users. It can:
- Check environment status
- List installed/available powerups
- Explain platform policies
- Answer general questions about the platform
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .tool_schemas import SUPPORT_CHATBOT_TOOLS

logger = logging.getLogger(__name__)


class SupportChatbot:
    """Multi-tool support chatbot for SaaS clients.

    Uses Claude's tool_use to answer questions with real data
    from the platform's data files.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)

    def _read_json(self, filename: str) -> Any:
        """Read a JSON data file."""
        path = self.data_dir / filename
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig"))
        return []

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a chatbot tool and return the result as string.

        This is the tool_executor callback for ClaudeClient.tool_use_loop().
        """
        if tool_name == "get_environment_status":
            return self._get_env_status(tool_input.get("env_id", ""))

        elif tool_name == "list_installed_powerups":
            return self._list_installed(tool_input.get("env_id", ""))

        elif tool_name == "list_available_powerups":
            return self._list_catalog()

        elif tool_name == "explain_policy":
            return self._explain_policy(tool_input.get("action", ""))

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def _get_env_status(self, env_id: str) -> str:
        """Get environment status and details."""
        envs = self._read_json("environments.json")
        env = next((e for e in envs if e.get("id") == env_id), None)
        if not env:
            return json.dumps({"error": f"Environment {env_id} not found"})

        # Return safe subset (no secrets)
        safe_fields = [
            "id", "name", "status", "plan_tier", "region", "zone",
            "machine_type", "disk_size_gb", "external_ip",
            "created_at", "messenger_channel", "llm_provider",
        ]
        result = {k: env.get(k) for k in safe_fields if k in env}

        # Add installed powerup count
        installed = self._read_json("installed_powerups.json")
        result["installed_powerups_count"] = sum(
            1 for p in installed if p.get("environment_id") == env_id
        )
        return json.dumps(result, ensure_ascii=False)

    def _list_installed(self, env_id: str) -> str:
        """List installed powerups for an environment."""
        installed = self._read_json("installed_powerups.json")
        env_powerups = [
            {
                "powerup_id": p.get("powerup_id"),
                "installed_at": p.get("installed_at"),
                "status": p.get("status", "active"),
            }
            for p in installed
            if p.get("environment_id") == env_id
        ]
        if not env_powerups:
            return json.dumps({"message": "No powerups installed", "powerups": []})
        return json.dumps({"powerups": env_powerups}, ensure_ascii=False)

    def _list_catalog(self) -> str:
        """List available powerups from catalog."""
        catalog = self._read_json("powerups_catalog.json")
        if isinstance(catalog, dict):
            catalog = catalog.get("powerups", [])
        items = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "category": p.get("category"),
                "description": p.get("description", ""),
                "min_machine_type": p.get("min_machine_type", "e2-micro"),
                "min_disk_gb": p.get("min_disk_gb", 10),
            }
            for p in catalog
        ]
        return json.dumps({"catalog": items}, ensure_ascii=False)

    def _explain_policy(self, action: str) -> str:
        """Explain policy rules for an action."""
        rules = self._read_json("policy_rules.json")
        if isinstance(rules, dict):
            rules = rules.get("rules", [])

        relevant = [r for r in rules if r.get("action") == action or not action]
        tiers = self._read_json("plan_tiers.json")

        return json.dumps({
            "action": action or "all",
            "rules": relevant,
            "plan_tiers": tiers if isinstance(tiers, list) else [],
            "general_info": (
                "Risk scoring: free tier +15pts, pro +5pts, scale +0pts. "
                "Powerup tiers: basic +5, advanced +20, pro +35, ultra +50. "
                "Score <25 = low risk (auto-allow), "
                "<60 = medium (allow with monitoring), "
                ">=60 = high (requires manual review)."
            ),
        }, ensure_ascii=False)

    def chat(
        self,
        message: str,
        env_id: str | None = None,
        model: str = "haiku",
    ) -> dict[str, Any]:
        """Process a chat message using Claude with tools.

        This is the main entry point for the chatbot.
        Uses ClaudeClient.tool_use_loop() for multi-turn tool execution.
        """
        from .claude_client import get_claude_client
        from .prompt_lab import get_prompt_lab

        client = get_claude_client()

        # Get system prompt from Prompt Lab
        try:
            lab = get_prompt_lab()
            system, _ = lab.render("support_chatbot", {"message": message})
        except Exception:
            system = (
                "You are a helpful support assistant for the A2A Agent SaaS platform. "
                "Use the provided tools to look up real data. Be concise and friendly. "
                "Answer in the same language as the user."
            )

        # Add environment context if provided
        if env_id:
            system += f"\n\nThe user's environment ID is: {env_id}"

        response = client.tool_use_loop(
            user_message=message,
            tools=SUPPORT_CHATBOT_TOOLS,
            tool_executor=self.execute_tool,
            system=system,
            model=model,
            max_turns=5,
        )

        return {
            "reply": response["content"],
            "model": response["model"],
            "tools_used": [tc["name"] for tc in response.get("tool_calls", [])],
            "tokens": response.get("input_tokens", 0) + response.get("output_tokens", 0),
        }


# ─── Singleton ───

_instance: SupportChatbot | None = None


def get_chatbot(data_dir: Path | None = None) -> SupportChatbot:
    """Get or create the global SupportChatbot instance."""
    global _instance
    if _instance is None:
        if data_dir is None:
            raise ValueError("data_dir required for first init")
        _instance = SupportChatbot(data_dir)
    return _instance
