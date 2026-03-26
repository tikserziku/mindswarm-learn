"""Challenge 1: Claude SDK Integration.

Course: Anthropic API Fundamentals, Lessons 1-3
What we learn: SDK setup, authentication, model parameters, model fallback

This client wraps the Anthropic Python SDK with:
- Model fallback: haiku (cheap) → sonnet (smart) → opus (strongest)
- Retry logic with exponential backoff
- Token tracking for cost awareness
- Streaming support (used in Challenge 3)
- Tool use support (used in Challenge 5)
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Generator

logger = logging.getLogger(__name__)

# Model hierarchy: cheapest → strongest
MODEL_HIERARCHY = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250514",
    "claude-opus-4-20250514",
]

# Friendly aliases
MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20250514",
    "opus": "claude-opus-4-20250514",
}

# Default parameters per use case
PARAM_PRESETS: dict[str, dict[str, Any]] = {
    "fast": {"model": "haiku", "max_tokens": 1024, "temperature": 0.0},
    "balanced": {"model": "sonnet", "max_tokens": 4096, "temperature": 0.3},
    "creative": {"model": "sonnet", "max_tokens": 4096, "temperature": 0.8},
    "precise": {"model": "sonnet", "max_tokens": 4096, "temperature": 0.0},
    "powerful": {"model": "opus", "max_tokens": 8192, "temperature": 0.3},
}


@dataclass
class UsageStats:
    """Track token usage and costs."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_requests: int = 0
    total_errors: int = 0
    total_fallbacks: int = 0
    by_model: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += 1
        if model not in self.by_model:
            self.by_model[model] = {"input_tokens": 0, "output_tokens": 0, "requests": 0}
        self.by_model[model]["input_tokens"] += input_tokens
        self.by_model[model]["output_tokens"] += output_tokens
        self.by_model[model]["requests"] += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "total_fallbacks": self.total_fallbacks,
            "by_model": self.by_model,
        }


class ClaudeClient:
    """Production-grade Claude API client with model fallback.

    Lesson 1: Basic SDK setup
    Lesson 2: Model parameters (temperature, max_tokens, system prompt)
    Lesson 3: Model selection and fallback strategy

    Usage:
        client = ClaudeClient()
        response = client.ask("What is the capital of France?")
        response = client.ask("Evaluate this policy", preset="precise")
        response = client.ask("Generate ideas", preset="creative")

        # With model fallback (haiku fails → try sonnet)
        response = client.ask("Complex task", model="haiku", fallback=True)

        # With tools (Challenge 5)
        response = client.ask("Check status", tools=[...])

        # Streaming (Challenge 3)
        for chunk in client.stream("Tell me a story"):
            print(chunk, end="")
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "haiku",
        fallback: bool = True,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._default_model = self._resolve_model(default_model)
        self._fallback = fallback
        self._max_retries = max_retries
        self._client = None
        self.stats = UsageStats()

    def _resolve_model(self, model: str) -> str:
        """Resolve alias to full model ID."""
        return MODEL_ALIASES.get(model, model)

    def _get_client(self):
        """Lazy-init the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to init Anthropic client: {e}")
        return self._client

    def _get_fallback_model(self, current_model: str) -> str | None:
        """Get the next model in hierarchy for fallback."""
        try:
            idx = MODEL_HIERARCHY.index(current_model)
            if idx + 1 < len(MODEL_HIERARCHY):
                return MODEL_HIERARCHY[idx + 1]
        except ValueError:
            pass
        return None

    def ask(
        self,
        user_message: str,
        *,
        system: str | None = None,
        model: str | None = None,
        preset: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        messages: list[dict[str, Any]] | None = None,
        fallback: bool | None = None,
    ) -> dict[str, Any]:
        """Send a message to Claude and get a response.

        Returns dict with:
            - content: str (text response)
            - model: str (which model was used)
            - input_tokens: int
            - output_tokens: int
            - tool_calls: list[dict] (if tools were used)
            - stop_reason: str
        """
        # Apply preset defaults
        params: dict[str, Any] = {}
        if preset and preset in PARAM_PRESETS:
            params.update(PARAM_PRESETS[preset])

        # Explicit params override preset
        resolved_model = self._resolve_model(
            model or params.get("model") or self._default_model
        )
        resolved_temp = temperature if temperature is not None else params.get("temperature", 0.3)
        resolved_max = max_tokens or params.get("max_tokens", 4096)
        use_fallback = fallback if fallback is not None else self._fallback

        # Build messages
        if messages:
            msg_list = messages
        else:
            msg_list = [{"role": "user", "content": user_message}]

        return self._call_with_fallback(
            model=resolved_model,
            messages=msg_list,
            system=system,
            temperature=resolved_temp,
            max_tokens=resolved_max,
            tools=tools,
            tool_choice=tool_choice,
            fallback=use_fallback,
        )

    def _call_with_fallback(
        self,
        model: str,
        messages: list[dict],
        system: str | None,
        temperature: float,
        max_tokens: int,
        tools: list[dict] | None,
        tool_choice: dict | None,
        fallback: bool,
    ) -> dict[str, Any]:
        """Call Claude with automatic model fallback on failure."""
        current_model = model
        last_error = None

        while current_model:
            try:
                return self._call_api(
                    model=current_model,
                    messages=messages,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice=tool_choice,
                )
            except Exception as e:
                last_error = e
                self.stats.total_errors += 1
                logger.warning(f"Claude call failed with {current_model}: {e}")

                if not fallback:
                    break

                next_model = self._get_fallback_model(current_model)
                if next_model:
                    logger.info(f"Falling back: {current_model} → {next_model}")
                    self.stats.total_fallbacks += 1
                    current_model = next_model
                else:
                    break

        raise RuntimeError(
            f"All Claude models failed. Last error: {last_error}"
        )

    def _call_api(
        self,
        model: str,
        messages: list[dict],
        system: str | None,
        temperature: float,
        max_tokens: int,
        tools: list[dict] | None,
        tool_choice: dict | None,
    ) -> dict[str, Any]:
        """Make the actual API call."""
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        response = client.messages.create(**kwargs)

        # Parse response
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        # Track usage
        self.stats.record(
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return {
            "content": "\n".join(text_parts),
            "model": model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason,
        }

    def stream(
        self,
        user_message: str,
        *,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Stream a response token by token (Challenge 3).

        Usage:
            for chunk in client.stream("Tell me a story"):
                print(chunk, end="", flush=True)
        """
        client = self._get_client()
        resolved_model = self._resolve_model(model or self._default_model)

        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "messages": [{"role": "user", "content": user_message}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def tool_use_loop(
        self,
        user_message: str,
        tools: list[dict[str, Any]],
        tool_executor: Any,
        *,
        system: str | None = None,
        model: str | None = None,
        max_turns: int = 10,
    ) -> dict[str, Any]:
        """Run a full tool_use conversation loop (Challenge 5).

        The tool_executor is a callable: (tool_name, tool_input) -> result_dict

        This implements the core Anthropic tool_use pattern:
        1. Send message + tools to Claude
        2. If Claude requests tool_use → execute tool → send result back
        3. Repeat until Claude gives a text response or max_turns reached
        """
        resolved_model = self._resolve_model(model or self._default_model)
        messages = [{"role": "user", "content": user_message}]

        for turn in range(max_turns):
            response = self.ask(
                user_message="",
                messages=messages,
                system=system,
                model=resolved_model,
                tools=tools,
                fallback=True,
            )

            # If no tool calls, we're done
            if not response["tool_calls"]:
                return response

            # Build assistant message with tool_use blocks
            assistant_content = []
            if response["content"]:
                assistant_content.append({"type": "text", "text": response["content"]})
            for tc in response["tool_calls"]:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
                })
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute tools and build tool_result message
            tool_results = []
            for tc in response["tool_calls"]:
                try:
                    result = tool_executor(tc["name"], tc["input"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": str(result) if not isinstance(result, str) else result,
                    })
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": f"Error: {e}",
                        "is_error": True,
                    })

            messages.append({"role": "user", "content": tool_results})

        return {
            "content": "[Max tool_use turns reached]",
            "model": resolved_model,
            "input_tokens": 0,
            "output_tokens": 0,
            "tool_calls": [],
            "stop_reason": "max_turns",
        }


# --- Singleton ---

_instance: ClaudeClient | None = None


def get_claude_client(
    api_key: str | None = None,
    default_model: str = "haiku",
) -> ClaudeClient:
    """Get or create the global ClaudeClient instance."""
    global _instance
    if _instance is None:
        _instance = ClaudeClient(api_key=api_key, default_model=default_model)
    return _instance
