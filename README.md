# AgenticWorkflow

A modular, scalable, production-ready **Agentic AI Framework** that enables autonomous agents to plan, reason, execute tasks, use tools, collaborate with other agents, and continuously improve outcomes.

[![CI](https://github.com/connectmilind21/AgenticWorkflow/actions/workflows/ci.yml/badge.svg)](https://github.com/connectmilind21/AgenticWorkflow/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

---

## Features

### 🤖 Agent Layer
| Agent | Role |
|---|---|
| `PlannerAgent` | Decomposes goals into structured execution plans |
| `ResearchAgent` | Gathers and synthesizes information from multiple sources |
| `DataAnalysisAgent` | Analyzes data and generates actionable insights |
| `CodingAgent` | Generates, debugs, refactors, and tests code |
| `ReviewerAgent` | Reviews artifacts and provides structured feedback |
| `CriticAgent` | Provides adversarial critiques to improve quality |
| `ExecutionAgent` | Executes tasks using available tools |
| `CoordinatorAgent` | Orchestrates multi-agent workflows |

### 🧠 Memory Layer
- **ShortTermMemory** — Sliding window conversation history
- **LongTermMemory** — Persistent JSON/database-backed storage with full-text search
- **VectorStoreMemory** — Semantic search via ChromaDB or Pinecone embeddings

### 🛠 Tool Layer
- **WebSearchTool** — Tavily, Serper (Google), or mock search
- **FileOperationsTool** — Secure read/write/list/search within a base directory
- **DatabaseTool** — SQL query execution with injection protection
- **PythonExecTool** — Sandboxed Python snippet execution with AST validation
- **ShellTool** — Allowlist-restricted shell command execution

### ⚙️ Workflow Engine
- **SequentialWorkflow** — Ordered step execution with retries and error recovery
- **ParallelWorkflow** — Concurrent batch execution with dependency resolution
- **ConditionalWorkflow** — Runtime branching based on evaluated conditions
- **MultiAgentWorkflow** — Pipeline, debate, and voting collaboration modes

### 📊 Observability
- Structured JSON logging via `structlog`
- Distributed tracing with `AgentTracer` (spans, events, attributes)
- Metrics collection: counters, gauges, histograms with Prometheus export
- Token usage and cost tracking

### 🌐 REST API (FastAPI)
- `GET /health/` — Health, readiness, liveness probes
- `POST /api/v1/agents/run` — Run any agent
- `GET /api/v1/agents/` — List available agent types
- `POST /api/v1/workflows/run` — Run a workflow
- `GET /api/v1/metrics/` — Metrics summary
- `GET /api/v1/metrics/prometheus` — Prometheus-format metrics

---

## Repository Structure

```
AgenticWorkflow/
├── agents/              # Agent implementations
├── tools/               # Tool implementations
├── memory/              # Memory backends
├── workflows/           # Workflow engine
├── prompts/             # System prompt templates
├── evaluations/         # Benchmarking suite
├── examples/            # Example workflows
├── api/                 # FastAPI application
├── agentic_workflow/    # Core package (config, CLI)
├── observability/       # Tracing, logging, metrics
├── tests/               # Test suite (194 tests)
├── configs/             # Default YAML configuration
├── scripts/             # Utility scripts
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/connectmilind21/AgenticWorkflow.git
cd AgenticWorkflow

# Install with development dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Run an Agent (Python)

```python
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from tools.web_search import WebSearchTool

# Create a research agent with search capability
search = WebSearchTool(api_key="your_key", provider="tavily")
agent = ResearchAgent(tools=[search])

result = agent.run("Latest trends in autonomous AI agents 2024")
print(result.status)       # AgentStatus.SUCCESS
print(result.output["synthesis"])
```

### Run a Workflow (Python)

```python
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from workflows.base import WorkflowStep
from workflows.sequential import SequentialWorkflow

wf = SequentialWorkflow(name="research_pipeline")
wf.register_agent(PlannerAgent())
wf.register_agent(ResearchAgent())

wf.add_step(WorkflowStep(id="plan", name="Plan", agent_name="PlannerAgent", task="Plan research"))
wf.add_step(WorkflowStep(id="research", name="Research", agent_name="ResearchAgent",
                         task="Research AI trends", depends_on=["plan"]))

result = wf.execute(context={"task": "AI trends research"})
print(result.status)       # WorkflowStatus.SUCCESS
```

### CLI

```bash
# List available agents
agentic list-agents

# Run an agent
agentic run-agent planner "Build a data pipeline for stock analysis"

# Run a workflow
agentic run-workflow sequential "Research machine learning trends"

# Start the API server
agentic serve
```

### API Server

```bash
# With Docker Compose (recommended)
docker compose up

# Or directly
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

# Run a workflow via API
curl -X POST http://localhost:8080/api/v1/agents/run \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "planner", "task": "Research Python async patterns"}'
```

---

## Example Workflows

| Example | File |
|---|---|
| Stock Research Agent | `examples/stock_research_agent.py` |
| Financial Analysis Agent | `examples/financial_analysis_agent.py` |
| News Monitoring Agent | `examples/news_monitoring_agent.py` |
| Resume Review Agent | `examples/resume_review_agent.py` |

```bash
python examples/stock_research_agent.py
python scripts/run_examples.py  # Run all examples
```

---

## Configuration

Edit `configs/default.yaml` to configure agents, memory, tools, and workflows:

```yaml
llm:
  model: "gpt-4o"
  temperature: 0.1

tools:
  web_search:
    provider: "tavily"
    max_results: 10
  python_exec:
    sandbox: true
    timeout: 30
```

Or use environment variables — see `.env.example`.

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific module
pytest tests/test_agents.py -v
```

**194 tests** covering agents, tools, memory, workflows, observability, config, and API.

---

## Docker

```bash
# Build and start all services
docker compose up --build

# API only
docker build -t agentic-workflow .
docker run -p 8080:8080 agentic-workflow
```

Services: `api` (port 8080), `postgres` (5432), `redis` (6379), `chroma` (8000)

---

## Technology Stack

- **Python 3.12+**, FastAPI, Pydantic v2
- **LangGraph**, LangChain, OpenAI APIs
- **ChromaDB** (vector store), **PostgreSQL**, **Redis**
- **structlog** (logging), **Prometheus** (metrics)
- **pytest** (194 tests), **ruff** (linting)
- **Docker**, **GitHub Actions** (CI/CD)

---

## Adding a New Agent

1. Subclass `BaseAgent` in `agents/my_agent.py`
2. Implement the `run(task, context)` method
3. Register in `agents/__init__.py`
4. Add system prompt to `prompts/templates.py`
5. Write tests in `tests/test_agents.py`

```python
from agents.base import AgentResult, AgentStatus, BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(name="MyAgent", description="Does something useful", **kwargs)

    def run(self, task, context=None):
        # Your logic here
        return self._create_result(status=AgentStatus.SUCCESS, output={"result": "done"})
```

---

## License

MIT
