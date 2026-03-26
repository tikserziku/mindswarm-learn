"""Challenge tracker — learning progress management.

Tracks which challenges are completed, locked, or available.
Handles unlock logic based on dependency chain.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHALLENGES = [
    {
        "id": 1,
        "name": "First Blood",
        "title": "Claude SDK Integration",
        "course": "API Fundamentals",
        "lessons": "1-3",
        "description": "SDK wrapper with model fallback, add anthropic as LLM provider",
        "depends_on": [],
        "module": "claude_client",
    },
    {
        "id": 2,
        "name": "Agent Thinks",
        "title": "Policy Agent via Claude",
        "course": "Prompt Engineering",
        "lessons": "1-3",
        "description": "Policy agent sends prompts to Claude instead of hardcoded math",
        "depends_on": [1],
        "module": "policy_agent_llm",
    },
    {
        "id": 3,
        "name": "Stream It",
        "title": "Streaming + Multimodal",
        "course": "API Fundamentals",
        "lessons": "4-5",
        "description": "SSE streaming endpoint, token-by-token responses",
        "depends_on": [1],
        "module": "streaming",
    },
    {
        "id": 4,
        "name": "Prompt Lab",
        "title": "Dynamic Prompt Engineering",
        "course": "Prompt Engineering",
        "lessons": "4-6",
        "description": "Dynamic prompts with CoT, few-shot, versioning, A/B testing",
        "depends_on": [2],
        "module": "prompt_lab",
    },
    {
        "id": 5,
        "name": "Agent Hands",
        "title": "Real Claude tool_use",
        "course": "Tool Use",
        "lessons": "1-3",
        "description": "Replace if/else dispatch with Claude tool_use loop",
        "depends_on": [4],
        "module": "tool_schemas",
    },
    {
        "id": 6,
        "name": "Structured Minds",
        "title": "Structured Outputs + Chatbot",
        "course": "Tool Use",
        "lessons": "4-5",
        "description": "Support chatbot with tools for clients",
        "depends_on": [5],
        "module": "chatbot",
    },
    {
        "id": 7,
        "name": "Real World",
        "title": "Domain-Specific Prompts",
        "course": "Real World Prompting",
        "lessons": "all",
        "description": "Incident summaries, onboarding, diagnostics prompts",
        "depends_on": [5],
        "module": "domain_prompts",
    },
    {
        "id": 8,
        "name": "Trust but Verify",
        "title": "Code-Graded Evaluations",
        "course": "Prompt Evaluations",
        "lessons": "1-2",
        "description": "Test cases for each agent, pass rate tracking",
        "depends_on": [6],
        "module": "eval_runner",
    },
    {
        "id": 9,
        "name": "Judge the Judge",
        "title": "Model-Graded Evaluations",
        "course": "Prompt Evaluations",
        "lessons": "3-4",
        "description": "Claude evaluates Claude outputs for quality",
        "depends_on": [8],
        "module": "model_judge",
    },
    {
        "id": 10,
        "name": "The Gauntlet",
        "title": "promptfoo in CI",
        "course": "Prompt Evaluations",
        "lessons": "5",
        "description": "Automated prompt testing in CI pipeline",
        "depends_on": [9],
        "module": "promptfoo",
    },
    {
        "id": 11,
        "name": "Bots Learn",
        "title": "Prompt Optimization Loop",
        "course": "Synthesis",
        "lessons": "all",
        "description": "Self-improving prompts from audit logs",
        "depends_on": [10],
        "module": "prompt_optimizer",
    },
    {
        "id": 12,
        "name": "Dashboard",
        "title": "Progress + Intelligence Metrics",
        "course": "Meta",
        "lessons": "N/A",
        "description": "Visual progress tracker and bot intelligence dashboard",
        "depends_on": [11],
        "module": "dashboard",
    },
]


class ChallengeTracker:
    """Track learning progress through challenges."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.progress_file = self.data_dir / "learning_progress.json"
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.progress_file.exists():
            initial = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "challenges": {
                    str(c["id"]): {
                        "status": "available" if not c["depends_on"] else "locked",
                        "score": 0,
                        "started_at": None,
                        "completed_at": None,
                        "eval_results": [],
                    }
                    for c in CHALLENGES
                },
            }
            self._save(initial)

    def _load(self) -> dict[str, Any]:
        return json.loads(self.progress_file.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.progress_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_progress(self) -> dict[str, Any]:
        """Get full progress with challenge metadata."""
        data = self._load()
        result = []
        for c in CHALLENGES:
            cid = str(c["id"])
            state = data["challenges"].get(cid, {})
            result.append({
                **c,
                "status": state.get("status", "locked"),
                "score": state.get("score", 0),
                "started_at": state.get("started_at"),
                "completed_at": state.get("completed_at"),
            })
        return {
            "started_at": data.get("started_at"),
            "challenges": result,
            "completed": sum(
                1 for r in result if r["status"] == "completed"
            ),
            "total": len(CHALLENGES),
        }

    def start_challenge(self, challenge_id: int) -> dict[str, Any]:
        """Mark a challenge as in_progress."""
        data = self._load()
        cid = str(challenge_id)
        state = data["challenges"].get(cid)
        if not state:
            raise ValueError(f"Challenge {challenge_id} not found")
        if state["status"] == "locked":
            raise ValueError(f"Challenge {challenge_id} is locked. Complete dependencies first.")
        state["status"] = "in_progress"
        state["started_at"] = datetime.now(timezone.utc).isoformat()
        self._save(data)
        return state

    def complete_challenge(self, challenge_id: int, score: int = 100) -> dict[str, Any]:
        """Mark a challenge as completed and unlock dependents."""
        data = self._load()
        cid = str(challenge_id)
        state = data["challenges"].get(cid)
        if not state:
            raise ValueError(f"Challenge {challenge_id} not found")
        state["status"] = "completed"
        state["score"] = score
        state["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Unlock dependent challenges
        for c in CHALLENGES:
            dep_cid = str(c["id"])
            if challenge_id in c["depends_on"]:
                dep_state = data["challenges"].get(dep_cid, {})
                if dep_state.get("status") == "locked":
                    # Check if ALL dependencies are completed
                    all_deps_done = all(
                        data["challenges"].get(str(d), {}).get("status") == "completed"
                        for d in c["depends_on"]
                    )
                    if all_deps_done:
                        dep_state["status"] = "available"

        self._save(data)
        return state

    def record_eval(
        self, challenge_id: int, eval_name: str, passed: int, total: int,
    ) -> None:
        """Record evaluation results for a challenge."""
        data = self._load()
        cid = str(challenge_id)
        state = data["challenges"].get(cid)
        if state:
            state["eval_results"].append({
                "eval_name": eval_name,
                "passed": passed,
                "total": total,
                "score": round(passed / total * 100) if total > 0 else 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Update challenge score to latest eval
            if total > 0:
                state["score"] = round(passed / total * 100)
            self._save(data)
