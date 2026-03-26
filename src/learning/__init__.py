"""Learning by Building — Anthropic Courses → SaaS Features.

This module implements practical learning challenges that integrate
Anthropic's best practices directly into the SaaS platform.

Challenges:
  1. Claude SDK Integration (API Fundamentals)
  2. Policy Agent via Claude (Prompt Engineering)
  3. Streaming + Multimodal (API Fundamentals)
  4. Prompt Lab (Prompt Engineering)
  5. Real tool_use (Tool Use)
  6. Structured Outputs + Chatbot (Tool Use)
  7. Domain Prompts (Real World Prompting)
  8. Code-Graded Evals (Prompt Evaluations)
  9. Model-Graded Evals (Prompt Evaluations)
  10. promptfoo CI (Prompt Evaluations)
  11. Prompt Optimization Loop (Synthesis)
  12. Dashboard (Meta)
"""

from .claude_client import ClaudeClient, get_claude_client
from .tool_schemas import get_tools_for_agent

__all__ = ["ClaudeClient", "get_claude_client", "get_tools_for_agent"]
