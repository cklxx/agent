# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development Setup
```bash
# Environment setup (preferred method)
uv sync                          # Install all dependencies
./bootstrap.sh --dev             # Start both backend and frontend in dev mode
./bootstrap.sh                   # Start in production mode

# Manual setup
make install-dev                 # Install Python dev dependencies
cd web && pnpm install          # Install frontend dependencies
```

### Backend Development
```bash
# Running the application
uv run main.py --interactive     # Interactive research mode with built-in questions
uv run main.py "Your query"      # Direct query execution
uv run server.py                 # Start FastAPI backend server
make serve                       # Start with auto-reload

# Development tools
make format                      # Format code with Black (88 char line length)
make lint                        # Check code formatting
make test                        # Run pytest tests
make coverage                    # Run tests with coverage report
uv run pytest tests/test_specific.py  # Run specific test file

# LangGraph development
make langgraph-dev               # Start LangGraph development server for debugging
```

### Frontend Development (web/ directory)
```bash
pnpm dev                         # Start Next.js development server
pnpm build                       # Build for production
pnpm typecheck                   # TypeScript type checking
pnpm lint                        # ESLint checking
pnpm format:write                # Prettier code formatting
```

### Testing Infrastructure
```bash
# Comprehensive testing script with Chinese interface
./scripts/test_tools.sh --all           # Run all tool tests
./scripts/test_tools.sh --quick         # Quick basic tests
./scripts/test_tools.sh --bash          # Test bash tools specifically
./scripts/test_tools.sh --file-edit     # Test file editing tools
./scripts/test_tools.sh --workspace --verbose  # Workspace tests with details

# Individual test commands
uv run pytest tests/test_rag_*.py       # RAG system tests
uv run pytest tests/test_optimized_tools.py  # Optimized tools tests
uv run pytest tests/integration/        # Integration tests
```

## Architecture Overview

### Core System Design
DeepTool is a multi-agent AI system built on **LangGraph** state-based workflows with the following key architectural patterns:

**1. LangGraph State Machine Architecture**
- All agents extend `MessagesState` with custom state fields (locale, resources, observations, etc.)
- State flows through nodes: `coordinator → background_investigator → planner → researcher/coder → reporter`
- Memory persistence using `MemorySaver` for conversation continuity
- Command-based agent transitions using LangGraph's `Command` pattern

**2. Multi-Agent Coordination**
- **Coordinator**: Entry point, routes to appropriate agents based on task analysis
- **Background Investigator**: Performs initial context gathering before planning
- **Planner**: Creates structured research plans with human-in-the-loop feedback
- **Researcher**: Executes web search and information gathering
- **Coder**: Handles code analysis, generation, and RAG-enhanced operations
- **Reporter**: Synthesizes findings into final reports

**3. Hybrid RAG System** 
- Triple retrieval strategy: Vector + Keyword + AST-based code search
- SQLite-based storage with ChromaDB vector store
- Intelligent file filtering using LLM-driven relevance detection
- Enhanced retriever in `src/rag/enhanced_retriever.py` with configurable weights

### Tool System Architecture

**Optimized Tool Pipeline**
- **Middleware Layer**: `src/tools/middleware.py` provides caching, metrics, and async wrappers
- **Unified Interface**: `src/tools/unified_tools.py` standardizes tool interactions
- **Async Support**: `src/tools/async_tools.py` enables concurrent tool execution
- Tool categories: File operations, system commands, web search, RAG-enhanced tools

### Configuration Management

**Multi-Level Configuration**
- `conf.yaml`: LLM providers, model configurations, service endpoints
- `.env`: API keys and sensitive credentials (never committed)
- `src/config/`: Centralized configuration loading with validation
- Runtime parameters: locale, max iterations, debug mode, auto-execution flags

### Data Flow Patterns

**Research Workflow**
1. User input → Coordinator (task classification)
2. Background Investigation (optional context gathering)
3. Planning → Human feedback loop (plan review/modification)
4. Execution → Agent dispatch based on task type
5. Reporting → Multi-format output generation

**Code Agent Workflow**
- RAG-enhanced context retrieval from existing codebase
- Pattern recognition for consistent code generation
- Workspace-aware file operations with gitignore support
- AST-based code parsing and semantic search

### Key Integration Points

**LLM Integration**
- LiteLLM for multi-provider support (OpenAI, Anthropic, local models)
- Configurable model selection per agent type
- Retry mechanisms and error handling

**External Services**
- Search engines: Tavily (recommended), Brave, DuckDuckGo, Arxiv
- Optional: RAGFlow, Volcengine TTS, LangSmith tracing
- MCP (Model Context Protocol) for extensible tool integration

**Web UI Integration**
- FastAPI backend with SSE (Server-Sent Events) for real-time updates
- Next.js frontend with React 19 and TypeScript
- Real-time workflow visualization via LangGraph Studio

### Development Patterns

**State Management**
- All agents receive and return `State` objects with messages, resources, and metadata
- Use `Command(update={"field": value}, goto="next_node")` for state transitions
- Preserve conversation history and context across agent handoffs

**Error Handling**
- Structured exception handling with retry mechanisms for LLM calls
- Graceful degradation when optional services are unavailable
- Comprehensive logging with configurable levels

**Testing Strategy**
- Unit tests for individual tools and agents
- Integration tests for complete workflows
- Mock external API calls to ensure reliable testing
- Coverage requirement: minimum 25%

## Important Notes

- **Python Version**: Requires Python 3.12+ for latest language features
- **Package Management**: Prefer `uv` over pip for faster dependency resolution
- **Development Mode**: Use `./bootstrap.sh --dev` for full-stack development
- **Memory**: LangGraph workflows use in-memory checkpointing (future: SQLite/PostgreSQL)
- **Security**: Never commit API keys; use `.env` files excluded from git
- **Performance**: Background processing and caching implemented for long-running tasks