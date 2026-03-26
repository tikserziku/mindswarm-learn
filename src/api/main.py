"""MindSwarm Learn — API Server.

25 endpoints covering all 12 learning challenges.
Run: uvicorn src.api.main:app --host 0.0.0.0 --port 8010 --reload
"""

import json
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
WEB_DIR = BASE_DIR / "web"

# Ensure data dir exists
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="MindSwarm Learn",
    description="Learn to build AI agents by doing — 12 challenges from Anthropic's courses",
    version="1.0.0",
)

# --- Learning imports (lazy to handle missing deps gracefully) ---

def _get_client():
    from src.learning import get_claude_client
    return get_claude_client()

def _get_challenges():
    from src.learning.challenges import ChallengeTracker
    return ChallengeTracker(str(DATA_DIR))

def _get_prompt_lab():
    from src.learning.prompt_lab import get_prompt_lab
    return get_prompt_lab(str(DATA_DIR))

def _get_chatbot():
    from src.learning.chatbot import SupportChatbot
    return SupportChatbot(str(DATA_DIR))

def _get_eval_runner():
    from src.learning.evaluations.eval_runner import EvalRunner
    return EvalRunner(str(DATA_DIR))

def _get_model_judge():
    from src.learning.evaluations.model_judge import ModelJudge
    return ModelJudge()

def _get_optimizer():
    from src.learning.prompt_optimizer import PromptOptimizer
    return PromptOptimizer(str(DATA_DIR))


# ============================================================
# Learning Progress (Challenges 1-12)
# ============================================================

@app.get("/api/learning/progress")
async def learning_progress():
    """Get progress for all 12 challenges."""
    tracker = _get_challenges()
    return tracker.get_progress()

@app.post("/api/learning/challenges/{challenge_id}/start")
async def start_challenge(challenge_id: int):
    """Start a challenge."""
    tracker = _get_challenges()
    return tracker.start_challenge(challenge_id)

@app.post("/api/learning/challenges/{challenge_id}/complete")
async def complete_challenge(challenge_id: int, score: int = 100):
    """Complete a challenge with a score."""
    tracker = _get_challenges()
    return tracker.complete_challenge(challenge_id, score)

@app.get("/api/learning/claude/stats")
async def claude_stats():
    """Get Claude API usage statistics."""
    client = _get_client()
    return client.stats.to_dict()

@app.post("/api/learning/claude/test")
async def claude_test(message: str = "Hello, Claude!"):
    """Test Claude connection."""
    client = _get_client()
    result = client.ask(message, preset="fast")
    return result


# ============================================================
# Chat — Challenge 3: Streaming
# ============================================================

@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    """SSE streaming chat endpoint."""
    body = await request.json()
    message = body.get("message", "")
    system = body.get("system")
    model = body.get("model", "sonnet")
    temperature = body.get("temperature", 0.3)

    client = _get_client()

    async def event_generator():
        for chunk in client.stream(message, model=model, system=system, temperature=temperature):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/chat/vision")
async def chat_vision(message: str = "What do you see?", image_url: str = ""):
    """Multimodal vision endpoint."""
    client = _get_client()
    content = [{"type": "text", "text": message}]
    if image_url:
        content.insert(0, {"type": "image", "source": {"type": "url", "url": image_url}})
    result = client.ask(content, preset="balanced")
    return result


# ============================================================
# Prompt Lab — Challenge 4
# ============================================================

@app.get("/api/prompts")
async def list_prompts():
    """List all prompts in the library."""
    lab = _get_prompt_lab()
    return lab.list_prompts()

@app.get("/api/prompts/{name}")
async def get_prompt(name: str):
    """Get a specific prompt by name."""
    lab = _get_prompt_lab()
    return lab.get_prompt(name)

@app.put("/api/prompts/{name}")
async def update_prompt(name: str, request: Request):
    """Create or update a prompt."""
    body = await request.json()
    lab = _get_prompt_lab()
    return lab.save_prompt(name, body)

@app.post("/api/prompts/{name}/render")
async def render_prompt(name: str, request: Request):
    """Preview: render a prompt with context variables."""
    body = await request.json()
    lab = _get_prompt_lab()
    system, user_msg = lab.render(name, body)
    return {"system": system, "user_message": user_msg}

@app.post("/api/prompts/{name}/test")
async def test_prompt(name: str, request: Request):
    """Live test: render + send to Claude."""
    body = await request.json()
    lab = _get_prompt_lab()
    system, user_msg = lab.render(name, body)
    client = _get_client()
    result = client.ask(user_msg, system=system, preset="balanced")
    return result

@app.post("/api/prompts/{name}/examples")
async def add_example(name: str, request: Request):
    """Add a few-shot example to a prompt."""
    body = await request.json()
    lab = _get_prompt_lab()
    return lab.add_example(name, body)


# ============================================================
# Tool Schemas — Challenge 5
# ============================================================

@app.get("/api/tools")
async def list_tools():
    """List all agents and their tool schemas."""
    from src.learning.tool_schemas import get_tools_for_agent, AGENT_TOOL_MAP
    return {name: get_tools_for_agent(name) for name in AGENT_TOOL_MAP}

@app.get("/api/tools/{agent_name}")
async def get_agent_tools(agent_name: str):
    """Get tool schemas for a specific agent."""
    from src.learning.tool_schemas import get_tools_for_agent
    tools = get_tools_for_agent(agent_name)
    if not tools:
        return JSONResponse({"error": f"Agent '{agent_name}' not found"}, status_code=404)
    return tools


# ============================================================
# Support Chatbot — Challenge 6
# ============================================================

@app.post("/api/support/chat")
async def support_chat(request: Request):
    """Chat with the AI support bot (uses tool_use loop)."""
    body = await request.json()
    message = body.get("message", "")
    env_id = body.get("env_id", "env-001")
    model = body.get("model", "sonnet")
    chatbot = _get_chatbot()
    return chatbot.chat(message, env_id=env_id, model=model)


# ============================================================
# Domain Prompts — Challenge 7
# ============================================================

@app.post("/api/incidents/summarize")
async def summarize_incidents(request: Request):
    """AI-powered incident summary."""
    body = await request.json()
    from src.learning.domain_prompts import IncidentSummarizer
    summarizer = IncidentSummarizer()
    return summarizer.summarize(body.get("events", []))

@app.post("/api/onboarding/guide")
async def onboarding_guide(request: Request):
    """Generate personalized onboarding guide."""
    body = await request.json()
    from src.learning.domain_prompts import OnboardingGuide
    guide = OnboardingGuide()
    return guide.generate(
        user_type=body.get("user_type", "developer"),
        platform=body.get("platform", "saas"),
        messenger=body.get("messenger", "telegram"),
        llm_provider=body.get("llm_provider", "anthropic"),
    )

@app.post("/api/diagnostics/analyze")
async def diagnostics_analyze(request: Request):
    """AI system diagnostics."""
    body = await request.json()
    from src.learning.domain_prompts import DiagnosticsAgent
    agent = DiagnosticsAgent()
    return agent.analyze(body.get("metrics", {}))


# ============================================================
# Evaluations — Challenges 8-9
# ============================================================

@app.get("/api/evals")
async def list_evals():
    """List available eval sets."""
    runner = _get_eval_runner()
    return runner.list_eval_sets()

@app.post("/api/evals/run/{agent_name}")
async def run_evals(agent_name: str):
    """Run code-graded evaluations for an agent."""
    runner = _get_eval_runner()
    return runner.run(agent_name)

@app.get("/api/evals/history")
async def eval_history():
    """Get evaluation history."""
    history_path = DATA_DIR / "eval_history.json"
    if history_path.exists():
        return json.loads(history_path.read_text())
    return []

@app.post("/api/evals/judge")
async def model_judge(request: Request):
    """Model-graded evaluation (Claude judges Claude)."""
    body = await request.json()
    judge = _get_model_judge()
    return judge.evaluate(
        prompt=body.get("prompt", ""),
        response=body.get("response", ""),
        dimensions=body.get("dimensions"),
    )

@app.post("/api/evals/judge/batch")
async def model_judge_batch(request: Request):
    """Batch model-graded evaluation."""
    body = await request.json()
    judge = _get_model_judge()
    results = []
    for case in body.get("test_cases", []):
        result = judge.evaluate(
            prompt=case.get("prompt", ""),
            response=case.get("response", ""),
        )
        results.append(result)
    return {"results": results, "total": len(results)}

@app.get("/api/evals/promptfoo-config")
async def promptfoo_config():
    """Get promptfoo CI configuration."""
    config_path = BASE_DIR / "promptfooconfig.yaml"
    if config_path.exists():
        return {"config": config_path.read_text()}
    return {"error": "promptfoo config not found"}


# ============================================================
# Prompt Optimizer — Challenge 11
# ============================================================

@app.post("/api/prompts/optimize/{agent_name}")
async def optimize_prompt(agent_name: str):
    """AI-powered prompt improvement suggestions."""
    optimizer = _get_optimizer()
    return optimizer.suggest_improvements(agent_name)


# ============================================================
# Dashboard — Challenge 12
# ============================================================

@app.get("/learn", response_class=HTMLResponse)
async def learning_dashboard():
    """HTML learning progress dashboard."""
    tracker = _get_challenges()
    progress = tracker.get_progress()

    challenges_html = ""
    for ch in progress.get("challenges", []):
        status_class = ch.get("status", "locked")
        status_icon = {"completed": "&#10003;", "in_progress": "&#9654;", "available": "&#9711;", "locked": "&#128274;"}.get(status_class, "?")
        score = f" — {ch.get('score', 0)}%" if ch.get("score") else ""
        challenges_html += f"""
        <div class="challenge {status_class}">
            <span class="icon">{status_icon}</span>
            <div>
                <strong>Challenge {ch.get('id', '?')}: {ch.get('name', '')}</strong>{score}
                <p>{ch.get('description', '')}</p>
            </div>
        </div>"""

    completed = sum(1 for ch in progress.get("challenges", []) if ch.get("status") == "completed")
    total = len(progress.get("challenges", []))
    pct = int(completed / total * 100) if total else 0

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindSwarm Learn — Dashboard</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; background: #fafaf9; color: #1a1814; }}
  h1 {{ font-size: 28px; margin-bottom: 8px; }}
  .progress {{ background: #e5e3de; border-radius: 12px; height: 24px; margin: 16px 0 32px; overflow: hidden; }}
  .progress-bar {{ background: #E8A019; height: 100%; border-radius: 12px; transition: width 0.3s; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; color: white; }}
  .challenge {{ display: flex; gap: 12px; padding: 16px; margin: 8px 0; background: white; border: 1px solid #e5e3de; border-radius: 12px; align-items: flex-start; }}
  .challenge.completed {{ border-color: #16a34a; background: #f0fdf4; }}
  .challenge.in_progress {{ border-color: #E8A019; background: #fef3e0; }}
  .icon {{ font-size: 20px; min-width: 28px; text-align: center; }}
  p {{ margin: 4px 0 0; font-size: 14px; color: #6b6760; }}
  a {{ color: #E8A019; }}
  .footer {{ margin-top: 40px; text-align: center; font-size: 13px; color: #6b6760; }}
</style>
</head><body>
<h1>MindSwarm Learn</h1>
<p>{completed}/{total} challenges completed</p>
<div class="progress"><div class="progress-bar" style="width: {pct}%">{pct}%</div></div>
{challenges_html}
<div class="footer">
  <a href="https://mindswarm.dev">mindswarm.dev</a> &middot;
  <a href="https://github.com/tikserziku/mindswarm-learn">GitHub</a> &middot;
  <a href="/api/learning/progress">API</a>
</div>
</body></html>"""


# ============================================================
# Root
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "MindSwarm Learn",
        "version": "1.0.0",
        "description": "Learn to build AI agents by doing",
        "dashboard": "/learn",
        "docs": "/docs",
        "website": "https://mindswarm.dev",
    }
