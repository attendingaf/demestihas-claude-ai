# Demestihas-AI

Custom AI agent with branched orchestration, dual-memory system, and commercial parity performance.

## 🚀 Features

- **Branched Orchestration** - Fast path for casual chat (<100ms latency)
- **Summary Buffer Memory** - 60-80% token usage reduction
- **Lightweight Router** - Intent classification with gpt-4o-mini
- **Dual Memory System** - FalkorDB knowledge graph + PostgreSQL conversations
- **Hybrid Execution** - Internal agents + external Arcade tools
- **Reflection Loop** - Judge LLM critique for low-confidence decisions
- **ReAct Pattern** - Iterative reasoning with tool observations

## 📋 Architecture

```
User Query → Pre-Router (Intent Classification)
              ├─ CASUAL_CHAT → Fast Path → Response (⚡ <100ms)
              └─ COMPLEX_TASK/KNOWLEDGE_QUERY → Full LangGraph
                  ├─ Reflection Loop (if confidence < 0.6)
                  ├─ Hybrid Executor (agents + tools)
                  ├─ ReAct Loop (iterative reasoning)
                  └─ Knowledge Consolidation → Response
```

## 🛠️ Tech Stack

- **Framework:** LangGraph, FastAPI
- **LLMs:** OpenAI (GPT-4, GPT-4o-mini)
- **Memory:** FalkorDB (graph), PostgreSQL (conversations), Qdrant (vectors)
- **Tools:** Arcade API integration
- **Deployment:** Docker, Docker Compose
- **UI:** Streamlit

## 🚦 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API key
- Python 3.10+

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/YOUR_USERNAME/demestihas-ai.git
   cd demestihas-ai
   ```

2. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start services:**

   ```bash
   docker-compose up -d
   ```

4. **Access the UI:**
   - Streamlit: <http://localhost:8501>
   - API: <http://localhost:8000>
   - Health check: <http://localhost:8000/health>

## 📦 Project Structure

```
demestihas-ai/
├── agent/                  # Main agent service
│   ├── main.py            # FastAPI app + LangGraph orchestrator
│   ├── statefulness_extensions.py  # Memory management
│   └── requirements.txt
├── streamlit/             # Streamlit UI
├── postgres/              # PostgreSQL init scripts
├── docker-compose.yml     # Service orchestration
└── .env                   # Environment variables (not committed)
```

## 📊 Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Casual Chat Latency | 3-5s | <100ms | **97% faster** |
| Token Usage (Long Conversations) | 5000+ | 1000-2000 | **60-80% reduction** |
| Intent Classification Accuracy | N/A | 95%+ | **New capability** |

## 🚀 Deployment

See [deployment_guide.md](deployment_guide.md) for VPS deployment instructions.

**Quick Deploy:**

```bash
./deploy.sh
```

## 🏷️ Releases

### v1.0 - Commercial Parity (Current)

- ✅ Branched orchestration with fast path
- ✅ Summary buffer memory
- ✅ Lightweight router with intent classification
- ✅ 97% latency reduction for casual chat
- ✅ 60-80% token usage reduction

---

**Built with ❤️ for intelligent, efficient AI interactions**
