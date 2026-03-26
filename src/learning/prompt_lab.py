"""Challenge 4: Prompt Lab — Dynamic Prompt Engineering.

Course: Prompt Engineering, Chapters 4-6
  - Ch4: Data/instruction separation (XML tags)
  - Ch5: Output formatting (structured responses)
  - Ch6: Chain-of-thought, few-shot examples

This module replaces static .txt prompt files with a dynamic system:
- Template variables: {context}, {rules}, {examples}
- Few-shot example injection from successful past interactions
- Chain-of-thought prefilling
- Prompt versioning and A/B testing
- XML-tag structured sections for data separation
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PromptVersion:
    """A single version of a prompt template."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.id = data.get("id", "v1")
        self.template = data.get("template", "")
        self.system = data.get("system", "")
        self.examples: list[dict[str, str]] = data.get("examples", [])
        self.chain_of_thought: bool = data.get("chain_of_thought", False)
        self.output_format: str = data.get("output_format", "")
        self.weight: float = data.get("weight", 1.0)  # For A/B testing
        self.created_at: str = data.get("created_at", "")
        self.eval_score: float = data.get("eval_score", 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "template": self.template,
            "system": self.system,
            "examples": self.examples,
            "chain_of_thought": self.chain_of_thought,
            "output_format": self.output_format,
            "weight": self.weight,
            "created_at": self.created_at,
            "eval_score": self.eval_score,
        }


class PromptDefinition:
    """A prompt with multiple versions for A/B testing."""

    def __init__(self, name: str, data: dict[str, Any]) -> None:
        self.name = name
        self.description = data.get("description", "")
        self.active_version = data.get("active_version", "v1")
        self.versions: dict[str, PromptVersion] = {
            v["id"]: PromptVersion(v)
            for v in data.get("versions", [])
        }

    def get_version(self, version_id: str | None = None) -> PromptVersion:
        """Get a specific version or the active one."""
        if version_id:
            return self.versions[version_id]
        return self.versions[self.active_version]

    def select_ab_version(self) -> PromptVersion:
        """Select a version based on A/B testing weights."""
        versions = list(self.versions.values())
        if len(versions) <= 1:
            return versions[0] if versions else self.get_version()
        weights = [v.weight for v in versions]
        return random.choices(versions, weights=weights, k=1)[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "active_version": self.active_version,
            "versions": [v.to_dict() for v in self.versions.values()],
        }


class PromptLab:
    """Dynamic prompt engineering system.

    Replaces static .txt files with versioned, templated prompts.

    Usage:
        lab = PromptLab(data_dir)
        system, user_msg = lab.render("policy_evaluator", {
            "action": "install_powerup",
            "environment": {"plan_tier": "free"},
            "rules": [...],
        })
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.library_file = self.data_dir / "prompt_library.json"
        self._prompts: dict[str, PromptDefinition] = {}
        self._load_library()

    def _load_library(self) -> None:
        """Load prompt library from JSON file."""
        if self.library_file.exists():
            data = json.loads(self.library_file.read_text(encoding="utf-8"))
            for name, pdata in data.get("prompts", {}).items():
                self._prompts[name] = PromptDefinition(name, pdata)

    def _save_library(self) -> None:
        """Save prompt library to JSON file."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "prompts": {
                name: p.to_dict() for name, p in self._prompts.items()
            },
        }
        self.library_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def render(
        self,
        prompt_name: str,
        context: dict[str, Any],
        *,
        version_id: str | None = None,
        ab_test: bool = False,
    ) -> tuple[str, str]:
        """Render a prompt with context variables.

        Returns (system_prompt, user_message).

        Prompt Engineering techniques applied:
        - Data separation via XML tags (Ch4)
        - Structured output format (Ch5)
        - Chain-of-thought instruction (Ch6)
        - Few-shot examples injection (Ch6)
        """
        prompt_def = self._prompts.get(prompt_name)
        if not prompt_def:
            # Fallback: load from static .txt file
            return self._render_legacy(prompt_name, context)

        # Select version
        if ab_test:
            version = prompt_def.select_ab_version()
        elif version_id:
            version = prompt_def.get_version(version_id)
        else:
            version = prompt_def.get_version()

        # Build system prompt
        system = version.system

        # Add chain-of-thought instruction
        if version.chain_of_thought:
            system += "\n\nBefore answering, think step by step inside <thinking> tags. Then give your final answer."

        # Add output format
        if version.output_format:
            system += f"\n\nOUTPUT FORMAT:\n{version.output_format}"

        # Build user message from template
        user_msg = version.template

        # Inject context variables using {variable} syntax
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in user_msg:
                if isinstance(value, (dict, list)):
                    user_msg = user_msg.replace(placeholder, json.dumps(value, indent=2, ensure_ascii=False))
                else:
                    user_msg = user_msg.replace(placeholder, str(value))

        # Inject few-shot examples
        if version.examples:
            examples_block = self._format_examples(version.examples)
            if "{examples}" in user_msg:
                user_msg = user_msg.replace("{examples}", examples_block)
            else:
                user_msg = f"{examples_block}\n\n{user_msg}"

        return system, user_msg

    def _format_examples(self, examples: list[dict[str, str]]) -> str:
        """Format few-shot examples with XML tags (Prompt Engineering Ch6)."""
        parts = ["<examples>"]
        for i, ex in enumerate(examples, 1):
            parts.append(f"<example index=\"{i}\">")
            if "input" in ex:
                parts.append(f"  <input>{ex['input']}</input>")
            if "output" in ex:
                parts.append(f"  <output>{ex['output']}</output>")
            parts.append("</example>")
        parts.append("</examples>")
        return "\n".join(parts)

    def _render_legacy(
        self, prompt_name: str, context: dict[str, Any],
    ) -> tuple[str, str]:
        """Fallback: render from static .txt file."""
        prompts_dir = Path(__file__).parent.parent / "orchestrator" / "prompts"
        txt_file = prompts_dir / f"{prompt_name}.txt"
        if txt_file.exists():
            system = txt_file.read_text(encoding="utf-8")
        else:
            system = f"You are a {prompt_name} agent."

        # Build basic user message from context
        user_msg = f"<context>\n{json.dumps(context, indent=2, ensure_ascii=False)}\n</context>"
        return system, user_msg

    # ─── CRUD for prompts ───

    def list_prompts(self) -> list[dict[str, Any]]:
        """List all prompt definitions."""
        return [
            {
                "name": p.name,
                "description": p.description,
                "active_version": p.active_version,
                "version_count": len(p.versions),
                "versions": list(p.versions.keys()),
            }
            for p in self._prompts.values()
        ]

    def get_prompt(self, name: str) -> dict[str, Any] | None:
        """Get a prompt definition by name."""
        p = self._prompts.get(name)
        return p.to_dict() if p else None

    def update_prompt(self, name: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create or update a prompt definition."""
        if name in self._prompts:
            prompt_def = self._prompts[name]
            if "description" in data:
                prompt_def.description = data["description"]
            if "active_version" in data:
                prompt_def.active_version = data["active_version"]
            if "versions" in data:
                for v in data["versions"]:
                    v.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                    prompt_def.versions[v["id"]] = PromptVersion(v)
        else:
            for v in data.get("versions", []):
                v.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            self._prompts[name] = PromptDefinition(name, data)

        self._save_library()
        return self._prompts[name].to_dict()

    def add_example(
        self, prompt_name: str, version_id: str,
        input_text: str, output_text: str,
    ) -> None:
        """Add a few-shot example to a prompt version."""
        prompt_def = self._prompts.get(prompt_name)
        if not prompt_def:
            raise ValueError(f"Prompt not found: {prompt_name}")
        version = prompt_def.get_version(version_id)
        version.examples.append({"input": input_text, "output": output_text})
        self._save_library()

    def record_eval_score(
        self, prompt_name: str, version_id: str, score: float,
    ) -> None:
        """Record eval score for a prompt version (for A/B test promotion)."""
        prompt_def = self._prompts.get(prompt_name)
        if prompt_def:
            version = prompt_def.get_version(version_id)
            version.eval_score = score
            self._save_library()

    def promote_best_version(self, prompt_name: str) -> str | None:
        """Promote the highest-scoring version to active."""
        prompt_def = self._prompts.get(prompt_name)
        if not prompt_def or not prompt_def.versions:
            return None
        best = max(prompt_def.versions.values(), key=lambda v: v.eval_score)
        prompt_def.active_version = best.id
        self._save_library()
        return best.id


# ─── Singleton ───

_instance: PromptLab | None = None


def get_prompt_lab(data_dir: Path | None = None) -> PromptLab:
    """Get or create the global PromptLab instance."""
    global _instance
    if _instance is None:
        if data_dir is None:
            raise ValueError("data_dir required for first init")
        _instance = PromptLab(data_dir)
    return _instance
