# MindSwarm Learn: Build AI Agents by Doing

> Stop reading docs. Start building. 12 hands-on challenges that turn Anthropic's courses into a working product.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Claude API](https://img.shields.io/badge/Claude-API-orange.svg)](https://docs.anthropic.com)

## What is this?

A practice-first learning platform where every lesson from [Anthropic's courses](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) becomes a real, working feature. No toy examples — you build production patterns from Challenge 1.

**12 challenges. 4 phases. 25 API endpoints. All runnable without an API key (graceful fallbacks).**

Built by [MindSwarm](https://mindswarm.dev) — Multi-Agent AI Platform.

---

## Why This Exists

| Traditional Course | MindSwarm Learn |
|---|---|
| Read about prompt engineering | Build a Prompt Lab with versioning & A/B tests |
| Watch a tool_use demo | Wire 17 tools across 5 agents |
| Study evaluation theory | Run code-graded + model-graded evals on your agents |
| "Now go apply this yourself" | Every lesson IS the application |

---

## Quick Start

```bash
git clone https://github.com/tikserziku/mindswarm-learn.git
cd mindswarm-learn
pip install -r requirements.txt

# Optional: set your API key (works without it too!)
export ANTHROPIC_API_KEY="sk-ant-..."

# Run
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8010 --reload
```

Open:
- **Dashboard**: http://localhost:8010/learn
- **Chat UI**: open `web/chat.html` in your browser

---

## The 12 Challenges

### Phase 1: Foundation
| # | Challenge | What You Build | Key Concept |
|---|-----------|---------------|-------------|
| 1 | **First Blood** | Claude SDK client with model fallback (haiku -> sonnet -> opus) | API basics, error handling |
| 2 | **Agent Thinks** | Policy agent powered by Claude with legacy fallback | Prompt engineering, XML tags |
| 3 | **Stream It** | SSE streaming endpoint + chat UI | Real-time responses, EventSource |

### Phase 2: Intelligence
| # | Challenge | What You Build | Key Concept |
|---|-----------|---------------|-------------|
| 4 | **Prompt Lab** | Dynamic prompts with versions, A/B tests, few-shot | Prompt management at scale |
| 5 | **Agent Hands** | 17 tool_use JSON schemas for 5 agents | Claude tool_use protocol |
| 6 | **Structured Minds** | Support chatbot with 4 real tools | Agentic tool loops |
| 7 | **Real World** | Incident summarizer, onboarding guide, diagnostics | Domain-specific prompts |

### Phase 3: Quality
| # | Challenge | What You Build | Key Concept |
|---|-----------|---------------|-------------|
| 8 | **Trust but Verify** | Code-graded evaluation engine (5 check types) | Automated testing for AI |
| 9 | **Judge the Judge** | Model-graded evals (Claude judges Claude, 5 dimensions) | LLM-as-judge pattern |
| 10 | **The Gauntlet** | promptfoo CI configuration | Continuous eval in CI/CD |

### Phase 4: Mastery
| # | Challenge | What You Build | Key Concept |
|---|-----------|---------------|-------------|
| 11 | **Bots Learn** | Prompt optimizer (audit logs -> AI suggestions) | Self-improving prompts |
| 12 | **Dashboard** | Learning progress tracker with HTML dashboard | Putting it all together |

---

## Architecture

```
mindswarm-learn/
├── src/
│   ├── learning/                # Core learning module (2,400+ lines)
│   │   ├── claude_client.py     # Ch1: SDK wrapper, fallback, presets, streaming
│   │   ├── challenges.py        # Progress tracker, unlock logic
│   │   ├── prompt_lab.py        # Ch4: Dynamic prompts, versioning, A/B
│   │   ├── tool_schemas.py      # Ch5: 17 tool schemas for 5 agents
│   │   ├── chatbot.py           # Ch6: Support bot with tool execution
│   │   ├── domain_prompts.py    # Ch7: Incident, onboarding, diagnostics
│   │   ├── prompt_optimizer.py  # Ch11: AI-powered prompt improvement
│   │   └── evaluations/
│   │       ├── eval_runner.py   # Ch8: Code-graded evals
│   │       ├── model_judge.py   # Ch9: Model-graded evals
│   │       └── eval_sets/       # Test case definitions
│   └── api/
│       └── main.py              # FastAPI server, 25 endpoints
├── data/
│   └── prompt_library.json      # 5 production prompts with versions
├── web/
│   └── chat.html                # Chat UI for streaming demo
├── tests/                       # Unit + integration tests
├── promptfooconfig.yaml         # Ch10: CI eval config
└── requirements.txt
```

---

## API Reference

<details>
<summary><strong>25 Endpoints (click to expand)</strong></summary>

### Learning Progress
- `GET /api/learning/progress` — All 12 challenges status
- `POST /api/learning/challenges/{id}/start` — Begin a challenge
- `POST /api/learning/challenges/{id}/complete?score=100` — Mark complete
- `GET /api/learning/claude/stats` — Token usage statistics
- `POST /api/learning/claude/test?message=hello` — Test Claude connection

### Chat (Challenge 3)
- `POST /api/chat/stream` — SSE streaming (`{message, system?, model?, temperature?}`)
- `POST /api/chat/vision` — Image analysis (`?message=...&image_url=...`)

### Prompt Lab (Challenge 4)
- `GET /api/prompts` — List all prompts
- `GET /api/prompts/{name}` — Get prompt by name
- `PUT /api/prompts/{name}` — Create/update prompt
- `POST /api/prompts/{name}/render` — Preview rendered prompt
- `POST /api/prompts/{name}/test` — Live test with Claude
- `POST /api/prompts/{name}/examples` — Add few-shot example

### Tools (Challenge 5)
- `GET /api/tools` — All agents and their tools
- `GET /api/tools/{agent}` — Tool schemas for specific agent

### Support Chat (Challenge 6)
- `POST /api/support/chat` — Chat with support bot (`{message, env_id?, model?}`)

### Domain Prompts (Challenge 7)
- `POST /api/incidents/summarize` — AI incident summary
- `POST /api/onboarding/guide` — Generate onboarding guide
- `POST /api/diagnostics/analyze` — AI system diagnostics

### Evaluations (Challenges 8-10)
- `GET /api/evals` — List eval sets
- `POST /api/evals/run/{agent}` — Run code-graded evals
- `GET /api/evals/history` — Evaluation history
- `POST /api/evals/judge` — Model-graded eval
- `POST /api/evals/judge/batch` — Batch model eval

### Optimizer (Challenge 11)
- `POST /api/prompts/optimize/{agent}` — AI prompt improvement suggestions

### Dashboard (Challenge 12)
- `GET /learn` — HTML progress dashboard

</details>

---

## Works Without an API Key

Every component has graceful degradation:

| Component | With Claude API | Without API Key |
|-----------|----------------|-----------------|
| Policy Agent | Claude-powered decisions | Rule-based math fallback |
| Domain Prompts | AI-generated summaries | Template-based output |
| Prompt Lab | Live testing with Claude | Render preview only |
| Evaluations | Full AI scoring | Code-graded checks only |

You can explore the entire codebase, run the server, and complete most challenges without spending a cent.

---

## How to Add Your Own

### New Eval Set
```json
// data/eval_sets/my_agent.json
[
  {
    "name": "test_basic_allow",
    "input": {"action": "read", "user_role": "admin"},
    "expected": {"decision": "allow"},
    "checks": ["field_match:decision"]
  }
]
```

### New Prompt
```bash
curl -X PUT http://localhost:8010/api/prompts/my_prompt \
  -H 'Content-Type: application/json' \
  -d '{"description": "My agent", "active_version": "v1", "versions": [...]}'
```

### New Tool Schema
Add to `src/learning/tool_schemas.py` and register in `get_tools_for_agent()`.

---

## Contributing

PRs welcome! Ideas:
- Add more eval sets for existing agents
- Create new domain prompt templates
- Build additional challenges (13+)
- Improve the dashboard UI
- Add more language support

---

## License

MIT License — use it however you want.

---

## Links

- **Website**: [mindswarm.dev](https://mindswarm.dev)
- **Blog**: [mindswarm.dev/blog](https://mindswarm.dev/blog)
- **Twitter**: [@MindSwarmAI](https://twitter.com/MindSwarmAI)

---

<p align="center">
  <strong>Built with MindSwarm</strong> — Multi-Agent AI Platform<br>
  <a href="https://mindswarm.dev">mindswarm.dev</a>
</p>
