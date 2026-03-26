"""Challenge 8: Code-Graded Evaluations.

Course: Prompt Evaluations, Lessons 1-2
  - Lesson 1: Building evaluation sets
  - Lesson 2: Code-graded evaluation functions

Evaluates agent outputs against expected results using
deterministic checks (not LLM-based — that's Challenge 9).

Each eval set is a JSON file with test cases:
[
  {
    "name": "test case name",
    "input": { ... payload to agent ... },
    "expected": { ... expected output fields ... },
    "checks": ["field_match", "range_check", "contains"]
  }
]
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


# ─── Check functions ───

def check_field_match(actual: dict, expected: dict, field: str) -> bool:
    """Exact field value match."""
    return actual.get(field) == expected.get(field)


def check_field_exists(actual: dict, _expected: dict, field: str) -> bool:
    """Field exists and is not None."""
    return actual.get(field) is not None


def check_range(actual: dict, expected: dict, field: str) -> bool:
    """Value is within expected range [min, max]."""
    val = actual.get(field)
    exp = expected.get(field)
    if val is None or not isinstance(exp, list) or len(exp) != 2:
        return False
    return exp[0] <= val <= exp[1]


def check_contains(actual: dict, expected: dict, field: str) -> bool:
    """Actual field value contains expected substring."""
    val = str(actual.get(field, ""))
    exp = str(expected.get(field, ""))
    return exp.lower() in val.lower()


def check_in_set(actual: dict, expected: dict, field: str) -> bool:
    """Actual field value is in the expected set of values."""
    val = actual.get(field)
    exp = expected.get(field)
    if isinstance(exp, list):
        return val in exp
    return val == exp


CHECK_FUNCTIONS: dict[str, Callable] = {
    "field_match": check_field_match,
    "field_exists": check_field_exists,
    "range_check": check_range,
    "contains": check_contains,
    "in_set": check_in_set,
}


# ─── Eval Runner ───

class EvalResult:
    """Result of a single test case evaluation."""

    def __init__(self, name: str, passed: bool, details: dict[str, Any]) -> None:
        self.name = name
        self.passed = passed
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
        }


class EvalRunner:
    """Runs code-graded evaluations for agents.

    Usage:
        runner = EvalRunner(data_dir)
        report = runner.run("policy_evaluator")
        print(f"Passed: {report['passed']}/{report['total']}")
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.eval_sets_dir = Path(__file__).parent / "eval_sets"
        self.eval_sets_dir.mkdir(parents=True, exist_ok=True)
        self.results_file = data_dir / "eval_history.json"

    def run(
        self,
        agent_name: str,
        executor: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run all eval cases for an agent.

        If executor is None, uses a built-in executor for the agent type.
        executor takes an input dict and returns the agent's output dict.
        """
        eval_file = self.eval_sets_dir / f"{agent_name}.json"
        if not eval_file.exists():
            return {
                "agent": agent_name,
                "status": "no_eval_set",
                "message": f"No eval set found at {eval_file}",
            }

        cases = json.loads(eval_file.read_text(encoding="utf-8"))
        results: list[EvalResult] = []

        for case in cases:
            result = self._run_case(case, executor)
            results.append(result)

        report = self._build_report(agent_name, results)
        self._save_result(report)
        return report

    def _run_case(
        self,
        case: dict[str, Any],
        executor: Callable | None,
    ) -> EvalResult:
        """Run a single test case."""
        name = case.get("name", "unnamed")
        input_data = case.get("input", {})
        expected = case.get("expected", {})
        checks = case.get("checks", [])

        # Get actual output
        if executor:
            try:
                actual = executor(input_data)
            except Exception as e:
                return EvalResult(name, False, {"error": str(e)})
        else:
            # Without executor, we can only validate the expected format
            return EvalResult(name, True, {"skipped": "no executor provided"})

        # Run checks
        check_results = {}
        all_passed = True

        for check_spec in checks:
            if isinstance(check_spec, str):
                # Simple format: "field_match:decision"
                parts = check_spec.split(":")
                check_type = parts[0]
                check_field = parts[1] if len(parts) > 1 else ""
            elif isinstance(check_spec, dict):
                check_type = check_spec.get("type", "field_match")
                check_field = check_spec.get("field", "")
            else:
                continue

            check_fn = CHECK_FUNCTIONS.get(check_type)
            if not check_fn:
                check_results[check_spec] = {"status": "unknown_check", "passed": False}
                all_passed = False
                continue

            passed = check_fn(actual, expected, check_field)
            check_results[f"{check_type}:{check_field}"] = {
                "passed": passed,
                "actual": actual.get(check_field),
                "expected": expected.get(check_field),
            }
            if not passed:
                all_passed = False

        return EvalResult(name, all_passed, {
            "checks": check_results,
            "actual_output": actual,
        })

    def _build_report(
        self, agent_name: str, results: list[EvalResult],
    ) -> dict[str, Any]:
        """Build an evaluation report."""
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        return {
            "agent": agent_name,
            "status": "completed",
            "passed": passed,
            "total": total,
            "score": round(passed / total * 100) if total > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [r.to_dict() for r in results],
        }

    def _save_result(self, report: dict[str, Any]) -> None:
        """Save eval result to history."""
        history = []
        if self.results_file.exists():
            try:
                history = json.loads(self.results_file.read_text(encoding="utf-8"))
            except Exception:
                history = []

        history.append({
            "agent": report["agent"],
            "passed": report["passed"],
            "total": report["total"],
            "score": report["score"],
            "timestamp": report["timestamp"],
        })

        # Keep last 100 results
        history = history[-100:]
        self.results_file.write_text(
            json.dumps(history, indent=2), encoding="utf-8",
        )

    def list_eval_sets(self) -> list[dict[str, Any]]:
        """List available eval sets."""
        result = []
        for f in self.eval_sets_dir.glob("*.json"):
            cases = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "agent": f.stem,
                "case_count": len(cases),
                "file": str(f),
            })
        return result
