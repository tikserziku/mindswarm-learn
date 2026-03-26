"""Challenge 11: Prompt Optimization Loop.

Course: Synthesis of all courses
Reads audit logs + eval results → identifies failure patterns →
generates candidate prompt improvements → evaluates → promotes winners.

This is the self-improving loop that makes bots smarter over time.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PromptOptimizer:
    """Automated prompt optimization based on evaluation data.

    The optimization loop:
    1. Read eval history for an agent
    2. Identify underperforming areas
    3. Generate candidate prompt improvements (via Claude)
    4. Run evals on candidates
    5. Promote the best-performing version

    This closes the learning loop: build → evaluate → improve → repeat.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.audit_dir = self.data_dir / "agent_audit"
        self.history_file = self.data_dir / "eval_history.json"
        self.optimization_log = self.data_dir / "optimization_log.jsonl"

    def analyze(self, agent_name: str) -> dict[str, Any]:
        """Analyze an agent's performance and suggest improvements."""
        # Gather data
        eval_history = self._read_eval_history(agent_name)
        audit_data = self._read_audit_data(agent_name)

        if not eval_history:
            return {
                "agent": agent_name,
                "status": "insufficient_data",
                "message": "Run evaluations first to generate data for optimization.",
            }

        # Calculate metrics
        scores = [h.get("score", 0) for h in eval_history]
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0
        trend = self._calculate_trend(scores)

        # Identify failure patterns from audit
        failure_count = sum(
            1 for a in audit_data if a.get("status") == "failed"
        )
        common_errors = self._extract_common_errors(audit_data)

        analysis = {
            "agent": agent_name,
            "status": "analyzed",
            "metrics": {
                "eval_count": len(eval_history),
                "avg_score": round(avg_score, 1),
                "min_score": min_score,
                "max_score": max_score,
                "trend": trend,
            },
            "audit": {
                "total_calls": len(audit_data),
                "failures": failure_count,
                "failure_rate": round(failure_count / len(audit_data) * 100, 1) if audit_data else 0,
                "common_errors": common_errors[:5],
            },
            "recommendations": self._generate_recommendations(avg_score, trend, common_errors),
        }

        # Log the analysis
        self._log_optimization(agent_name, "analyze", analysis)
        return analysis

    def suggest_improvements(self, agent_name: str) -> dict[str, Any]:
        """Use Claude to suggest concrete prompt improvements."""
        analysis = self.analyze(agent_name)
        if analysis.get("status") != "analyzed":
            return analysis

        try:
            from .claude_client import get_claude_client
            from .prompt_lab import get_prompt_lab

            client = get_claude_client()
            lab = get_prompt_lab()
            current_prompt = lab.get_prompt(agent_name)

            response = client.ask(
                f"""You are a prompt engineering optimizer.
Analyze this agent's performance data and suggest specific prompt improvements.

<agent>{agent_name}</agent>

<performance>
{json.dumps(analysis['metrics'], indent=2)}
</performance>

<failures>
{json.dumps(analysis['audit'], indent=2)}
</failures>

<current_prompt>
{json.dumps(current_prompt, indent=2) if current_prompt else 'Using static .txt file'}
</current_prompt>

Generate 2-3 specific, actionable improvements.
For each improvement, explain WHAT to change, WHY, and the EXPECTED impact.

Return JSON:
{{
  "improvements": [
    {{
      "what": "...",
      "why": "...",
      "expected_impact": "+N% on <dimension>",
      "priority": "high|medium|low",
      "prompt_diff": "Add/change/remove: ..."
    }}
  ],
  "overall_assessment": "..."
}}""",
                system="You are an expert prompt engineer specializing in production AI systems.",
                preset="balanced",
            )

            content = response["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            suggestions = json.loads(content)
            suggestions["analysis"] = analysis["metrics"]
            suggestions["model"] = response["model"]

            self._log_optimization(agent_name, "suggest", suggestions)
            return suggestions

        except Exception as e:
            return {
                "agent": agent_name,
                "status": "error",
                "error": str(e),
                "fallback_recommendations": analysis.get("recommendations", []),
            }

    def _read_eval_history(self, agent_name: str) -> list[dict]:
        """Read evaluation history for an agent."""
        if not self.history_file.exists():
            return []
        history = json.loads(self.history_file.read_text(encoding="utf-8"))
        return [h for h in history if h.get("agent") == agent_name]

    def _read_audit_data(self, agent_name: str) -> list[dict]:
        """Read audit trail for an agent."""
        audit_file = self.audit_dir / "agent_tool_calls.jsonl"
        if not audit_file.exists():
            return []
        entries = []
        for line in audit_file.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("agent_name") == agent_name:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
        return entries[-100:]  # Last 100 entries

    def _calculate_trend(self, scores: list[float]) -> str:
        """Calculate score trend."""
        if len(scores) < 3:
            return "insufficient_data"
        recent = scores[-3:]
        older = scores[-6:-3] if len(scores) >= 6 else scores[:3]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        if avg_recent > avg_older + 5:
            return "improving"
        elif avg_recent < avg_older - 5:
            return "declining"
        return "stable"

    def _extract_common_errors(self, audit_data: list[dict]) -> list[str]:
        """Extract most common error messages."""
        errors: dict[str, int] = {}
        for entry in audit_data:
            error = entry.get("error")
            if error:
                key = error[:100]  # Truncate
                errors[key] = errors.get(key, 0) + 1
        return sorted(errors, key=errors.get, reverse=True)[:5]

    def _generate_recommendations(
        self, avg_score: float, trend: str, errors: list[str],
    ) -> list[str]:
        """Generate rule-based recommendations."""
        recs = []
        if avg_score < 50:
            recs.append("Score critically low — review prompt structure and examples")
        if avg_score < 80:
            recs.append("Add more few-shot examples to improve consistency")
        if trend == "declining":
            recs.append("Performance declining — check for prompt drift or data changes")
        if errors:
            recs.append(f"Address recurring errors: {errors[0][:50]}")
        if not recs:
            recs.append("Performance looks good — consider A/B testing prompt variants")
        return recs

    def _log_optimization(
        self, agent_name: str, action: str, data: dict[str, Any],
    ) -> None:
        """Append to optimization log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
            "action": action,
            "summary": {
                k: v for k, v in data.items()
                if k in ("status", "metrics", "overall_assessment")
            },
        }
        with open(self.optimization_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# Singleton
_optimizer: PromptOptimizer | None = None


def get_optimizer(data_dir: Path | None = None) -> PromptOptimizer:
    global _optimizer
    if _optimizer is None:
        if data_dir is None:
            raise ValueError("data_dir required")
        _optimizer = PromptOptimizer(data_dir)
    return _optimizer
