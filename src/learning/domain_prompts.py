"""Challenge 7: Domain-Specific Prompts — Real World Prompting.

Course: Real World Prompting
  - Customer support patterns
  - Call/incident summarization
  - Medical domain adaptation → DevOps domain

Three domain prompt systems:
1. Incident Summarizer — AI summaries of VM/infra incidents
2. Onboarding Guide — Step-by-step client onboarding
3. Diagnostics Agent — Analyzes errors instead of random reactor thoughts
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IncidentSummarizer:
    """Generate AI summaries of infrastructure incidents.

    Replaces generic timeline events with intelligent analysis.
    """

    SYSTEM_PROMPT = """You are an incident analysis specialist for a cloud VM management platform.
You summarize infrastructure incidents concisely and helpfully.

RULES:
- Lead with impact: what broke, who is affected
- Include root cause if identifiable
- Suggest remediation steps
- Use severity levels: INFO, WARNING, ERROR, CRITICAL
- Keep summaries under 3 sentences
- Be specific: include VM names, error codes, timestamps"""

    def summarize(
        self,
        events: list[dict[str, Any]],
        env_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Summarize a list of events into an incident report."""
        try:
            from .claude_client import get_claude_client
            client = get_claude_client()
        except Exception:
            return self._fallback_summary(events)

        context = json.dumps(events[:20], indent=2, ensure_ascii=False)
        env_info = ""
        if env_data:
            env_info = f"\n<environment>\n{json.dumps(env_data, indent=2)}\n</environment>"

        user_msg = f"""<task>Summarize these infrastructure events into a brief incident report.</task>

<events>
{context}
</events>
{env_info}

Return JSON:
{{
  "severity": "INFO|WARNING|ERROR|CRITICAL",
  "summary": "...",
  "impact": "...",
  "root_cause": "...",
  "remediation": ["step1", "step2"],
  "affected_components": ["component1"]
}}"""

        try:
            response = client.ask(user_msg, system=self.SYSTEM_PROMPT, preset="fast")
            content = response["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(content)
        except Exception:
            return self._fallback_summary(events)

    def _fallback_summary(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Non-AI fallback summary."""
        error_count = sum(1 for e in events if "error" in str(e).lower())
        return {
            "severity": "ERROR" if error_count > 0 else "INFO",
            "summary": f"{len(events)} events, {error_count} errors detected",
            "impact": "Unknown — AI summary unavailable",
            "root_cause": "Requires investigation",
            "remediation": ["Check logs manually"],
            "affected_components": [],
        }


class OnboardingGuide:
    """AI-powered client onboarding guidance.

    Generates step-by-step instructions tailored to the client's
    plan tier and requirements.
    """

    SYSTEM_PROMPT = """You are an onboarding specialist for the A2A Agent SaaS platform.
You guide new clients through setting up their AI assistant.

PLATFORM OVERVIEW:
- Clients get a GCP VM with a Telegram bot connected to an LLM
- Plans: free (e2-micro, 30GB), pro (e2-small, 50GB), scale (n1-standard-2, 100GB)
- Supported LLM providers: moonshot (Kimi), openai, gemini, anthropic (Claude)
- Supported messengers: telegram, whatsapp_cloud, multi

RULES:
- Adapt language and complexity to the client's experience level
- Provide exact API calls or UI steps
- Warn about common pitfalls
- Be encouraging and supportive"""

    def generate_guide(
        self,
        plan_tier: str = "free",
        messenger: str = "telegram",
        llm_provider: str = "moonshot",
        language: str = "en",
    ) -> dict[str, Any]:
        """Generate a personalized onboarding guide."""
        try:
            from .claude_client import get_claude_client
            client = get_claude_client()
        except Exception:
            return self._fallback_guide(plan_tier, messenger, llm_provider)

        user_msg = f"""Generate a step-by-step onboarding guide for a new client.

<client_setup>
  <plan_tier>{plan_tier}</plan_tier>
  <messenger>{messenger}</messenger>
  <llm_provider>{llm_provider}</llm_provider>
  <language>{language}</language>
</client_setup>

Return JSON:
{{
  "title": "...",
  "estimated_time_minutes": N,
  "steps": [
    {{"step": 1, "title": "...", "description": "...", "action": "..."}}
  ],
  "prerequisites": ["..."],
  "common_pitfalls": ["..."]
}}"""

        try:
            response = client.ask(user_msg, system=self.SYSTEM_PROMPT, preset="balanced")
            content = response["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(content)
        except Exception:
            return self._fallback_guide(plan_tier, messenger, llm_provider)

    def _fallback_guide(
        self, plan_tier: str, messenger: str, llm_provider: str,
    ) -> dict[str, Any]:
        return {
            "title": f"Onboarding: {plan_tier} plan with {messenger}",
            "estimated_time_minutes": 15,
            "steps": [
                {"step": 1, "title": "Create environment", "description": "POST /environments", "action": "api_call"},
                {"step": 2, "title": "Configure bot token", "description": f"Set up {messenger} bot", "action": "manual"},
                {"step": 3, "title": "Set LLM provider", "description": f"Configure {llm_provider}", "action": "api_call"},
                {"step": 4, "title": "Test bot", "description": "Send a test message", "action": "manual"},
            ],
            "prerequisites": [f"{messenger} bot token", f"{llm_provider} API key"],
            "common_pitfalls": ["Forgetting to set webhook URL", "Using wrong API key format"],
        }


class DiagnosticsAgent:
    """AI-powered diagnostics that replaces reactor's random thoughts.

    Analyzes actual system state instead of generating random ideas.
    """

    SYSTEM_PROMPT = """You are a DevOps diagnostics specialist.
You analyze system metrics and events to identify issues and suggest fixes.

RULES:
- Focus on actionable insights, not generic advice
- Prioritize by severity
- Include specific commands or API calls for fixes
- Never suggest destructive operations without warning
- Keep analysis under 5 bullet points"""

    def diagnose(
        self,
        events: list[dict[str, Any]],
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze system state and generate diagnostics."""
        try:
            from .claude_client import get_claude_client
            client = get_claude_client()
        except Exception:
            return self._fallback_diagnostics(events)

        user_msg = f"""<task>Analyze these recent system events and provide diagnostics.</task>

<events>
{json.dumps(events[:15], indent=2, ensure_ascii=False)}
</events>

<metrics>
{json.dumps(metrics or {}, indent=2)}
</metrics>

Return JSON:
{{
  "health": "healthy|degraded|critical",
  "issues": [
    {{"severity": "low|medium|high|critical", "description": "...", "fix": "..."}}
  ],
  "recommendations": ["..."],
  "next_check_minutes": N
}}"""

        try:
            response = client.ask(user_msg, system=self.SYSTEM_PROMPT, preset="fast")
            content = response["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(content)
        except Exception:
            return self._fallback_diagnostics(events)

    def _fallback_diagnostics(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        error_events = [e for e in events if "error" in str(e).lower()]
        health = "critical" if len(error_events) > 3 else "degraded" if error_events else "healthy"
        return {
            "health": health,
            "issues": [{"severity": "medium", "description": f"{len(error_events)} errors detected", "fix": "Check logs"}] if error_events else [],
            "recommendations": ["Review recent events manually"],
            "next_check_minutes": 5,
        }


# ─── Convenience instances ───

incident_summarizer = IncidentSummarizer()
onboarding_guide = OnboardingGuide()
diagnostics_agent = DiagnosticsAgent()
