# Agent Development Guide

本文档为 **DeepTool** 项目的 Code Agent 开发指南，提供项目架构、API 接口、工具函数等详细信息。

## 项目概述

**DeepTool** 是一个基于 LangGraph 的智能 Agent 系统，专注于自动化研究和代码分析。该项目起源于开源，回馈开源社区。
本系统采用模块化的多智能体架构，通过明确定义的组件和交互流程，实现复杂任务的自动化处理。

### 核心特性
- 🔧 **多工具集成**: 搜索、地图、TTS、Python REPL、爬虫、文件操作、终端执行等
- 🌐 **Web 界面**: Next.js + React 现代化前端界面
- 📊 **工作流管理**: 基于 LangGraph 的多agent状态图系统
- 🔍 **智能搜索**: 支持多种搜索引擎 (Tavily, Brave, DuckDuckGo, Arxiv)
- 🗺️ **地图服务**: 集成高德地图 API
- 🎤 **语音合成**: TTS 支持 (火山引擎)
- 🤖 **多模型支持**: 通过 LiteLLM 集成多种 LLM 提供商
- 🔗 **MCP 集成**: 无缝集成 Model Context Protocol
- 🧠 **人机协作**: 支持交互式研究计划修改
- 📝 **内容创建**: 播客脚本生成、PPT自动创建
- 📃 **RAG 集成**: 支持 RAGFlow 集成进行文档检索. 详细的RAG子系统描述见 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#rag-subsystem-srcrag-srccontextcode_rag_adapterpy).

## 项目架构

DeepTool 的核心架构基于 LangGraph 构建，实现了一个多智能体 (Multi-Agent) 系统。该系统通过一系列专门的智能体（节点）和它们之间的状态转移（边）来协同完成复杂任务，如自动化研究和代码分析。

主要组件包括：
- **入口点**: `main.py` (CLI) 和 `server.py` (Web API)。
- **工作流编排**: `src/workflow.py` 使用 LangGraph 的 `graph.astream`。
- **图构建**: `src/graph/builder.py` 中的 `build_graph()` 定义了核心的图结构。
- **核心智能体节点** (定义于 `src.graph.nodes.py`): 包括协调器 (Coordinator)、规划器 (Planner)、研究团队 (ResearchTeam)、编码器 (Coder) 和报告器 (Reporter) 等。
- **Agent 实现**: 位于 `src/agents/`，包括基础代码 Agent 和 RAG 增强的代码 Agent。
- **RAG 子系统**: 位于 `src/rag/`，提供代码索引和检索能力。
- **工具系统**: 位于 `src/tools/`，提供多样化的工具供 Agent 使用。

更详细的系统架构、组件说明和数据流图，请参阅 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)。

### 代码库结构

```
agent/
├── src/                    # 核心代码
│   ├── agents/            # Agent 定义 (包含code_agent)
│   ├── config/            # 配置管理和日志配置
│   ├── crawler/           # 爬虫模块
│   ├── graph/             # LangGraph 工作流
│   │   ├── nodes.py       # 节点定义
│   │   ├── types.py       # 状态类型
│   │   └── builder.py     # 图形构建器
│   ├── llms/              # LLM 集成
│   ├── podcast/           # 播客功能
│   ├── prompts/           # Prompt 模板
│   ├── prose/             # 文本处理
│   ├── ppt/               # PPT 生成
│   ├── rag/               # RAG 检索
│   ├── server/            # 服务端
│   ├── tools/             # 工具函数集合
│   │   ├── search.py      # 搜索工具
│   │   ├── maps.py        # 地图工具
│   │   ├── tts.py         # TTS工具
│   │   ├── python_repl.py # Python执行
│   │   ├── crawl.py       # 网页抓取
│   │   ├── file_reader.py # 文件读取
│   │   ├── file_writer.py # 文件写入
│   │   ├── terminal_executor.py # 终端命令执行
│   │   └── retriever.py   # 检索工具
│   ├── utils/             # 工具类
│   ├── workflow.py        # 主工作流
│   └── code_agent_workflow.py # 代码Agent专用工作流
├── web/                   # Next.js前端代码
│   ├── src/               # 前端源代码
│   ├── public/            # 静态资源
│   ├── package.json       # Node.js依赖
│   └── Dockerfile         # 前端Docker配置
├── docs/                  # 文档
├── examples/              # 示例代码
├── tests/                 # 测试
├── scripts/               # 脚本文件
├── assets/                # 资源文件
├── main.py               # 控制台入口文件
├── server.py             # Web API服务器
├── conf.yaml             # 主配置文件
├── conf.yaml.example     # 配置示例
├── pyproject.toml        # Python项目配置
├── uv.lock               # uv依赖锁定文件
├── docker-compose.yml    # Docker Compose配置
├── langgraph.json        # LangGraph配置
├── mcp.json              # MCP服务器配置
├── bootstrap.sh          # Linux/macOS启动脚本
├── bootstrap.bat         # Windows启动脚本
└── Dockerfile            # Docker配置

```

## 环境要求

- **Python**: 3.12+
- **Node.js**: 22+
- **依赖管理**: uv (推荐)
- **包管理器**: pnpm

## 核心模块详解

### 1. 工具模块 (`src/tools/`)

项目包含丰富的工具集合，支持多种操作场景：

#### 搜索工具 (`search.py`)
```python
# 主要函数
get_web_search_tool() -> Tool  # 获取配置化的搜索工具
```
支持的搜索引擎：
- **Tavily** (默认): AI应用专用搜索API
- **DuckDuckGo**: 隐私友好的搜索引擎
- **Brave Search**: 具有高级功能的隐私搜索
- **Arxiv**: 学术论文搜索

#### 地图工具 (`maps.py`)
```python
# 位置搜索
search_location(keyword: str) -> List[Location]

# 路线规划  
get_route(origin: str, destination: str, mode: str = "driving") -> Route

# 周边搜索
get_nearby_places(location: str, radius: int = 1000, types: Optional[str] = None) -> List[Location]
```

#### 文件操作工具
**文件读取** (`file_reader.py`):
```python
read_file(file_path: str) -> str
read_file_lines(file_path: str, start_line: int, end_line: int) -> str  
get_file_info(file_path: str) -> Dict
```

**文件写入** (`file_writer.py`):
```python
write_file(file_path: str, content: str) -> str
append_to_file(file_path: str, content: str) -> str
create_new_file(file_path: str, content: str) -> str
generate_file_diff(file_path: str, new_content: str) -> str
```

#### 终端执行工具 (`terminal_executor.py`)
```python
execute_terminal_command(command: str) -> str
get_current_directory() -> str
list_directory_contents(path: str = ".") -> str
execute_command_background(command: str) -> str
get_background_tasks_status() -> str
terminate_background_task(task_id: str) -> str
test_service_command(command: str, expected_patterns: List[str]) -> str
```

#### Python REPL (`python_repl.py`)
```python
python_repl_tool(code: str) -> str  # 执行Python代码
```

#### 网页爬虫 (`crawl.py`)
```python
crawl_tool(url: str) -> str  # 网页内容抓取
```

#### TTS 语音合成 (`tts.py`)
```python
class VolcengineTTS:
    def generate_speech(text: str, voice: str = "default") -> bytes
```

#### 检索工具 (`retriever.py`)
```python
get_retriever_tool() -> Tool  # 获取RAG检索工具
```

### 2. 图形工作流 (`src/graph/`)

#### 状态类型 (`types.py`)
```python
class AgentState(TypedDict):
    messages: List[Dict]
    auto_accepted_plan: bool
    enable_background_investigation: bool
    # 其他状态字段...
```

#### 节点定义 (`nodes.py`)
包含多种节点类型用于不同的处理阶段，支持复杂的工作流编排。

#### 图形构建 (`builder.py`)
```python
def build_graph() -> CompiledGraph:
    """构建主要的LangGraph工作流"""
```

### 3. 代码Agent工作流 (`src/code_agent_workflow.py` 和 `src/rag_enhanced_code_agent_workflow.py`)

专门用于处理编程任务的高级工作流。这些工作流编排了 `CodeTaskPlanner`, `RAGEnhancedCodeTaskPlanner`, 和相应的代码执行 Agent。
详细信息请参阅 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#agent-implementations-srcagents) 中的 Agent 实现部分。

```python
# class CodeAgentWorkflow: ... # (Details in src/code_agent_workflow.py)
# class RAGEnhancedCodeAgentWorkflow: ... # (Details in src/rag_enhanced_code_agent_workflow.py)

# 示例调用方式：
# result = await run_code_agent_workflow("创建一个Python Web应用", max_iterations=5)
# result = await run_rag_enhanced_code_agent_workflow("分析并优化指定代码文件", repo_path=".")
```

### 4. LLM 集成 (`src/llms/`)

通过 LiteLLM 支持多种模型提供商。系统对LLM进行了分类（如 'reasoning', 'basic'），以便根据任务需求选择合适的模型。
详细信息请参阅 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#llm-integration-srcllms)。
- OpenAI, Anthropic, DeepSeek, Google Gemini, 本地模型, OpenRouter 等。

### 5. 配置管理 (`src/config/`, `.env`, `conf.yaml`)

系统配置通过 `.env` 文件（API密钥和环境特定设置）、`conf.yaml`（LLM模型和服务URL）以及 `src/config/configuration.py`（加载和提供配置访问）进行管理。
详细信息请参阅 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#configuration-env-confyaml-srconfig)。

## API 接口

### 主要入口点

#### 命令行接口 (`main.py`)
```bash
# 交互模式
python main.py --interactive

# 直接查询
python main.py "你的问题"

# 调试模式
python main.py --debug "你的问题"

# 自定义参数
python main.py --max-plan-iterations 2 --max-step-num 5 "复杂任务"

# 禁用背景调研
python main.py --no-background-investigation "你的问题"
```

#### Web 服务器 (`server.py`)
```python
# 启动服务
uvicorn server:app --host 0.0.0.0 --port 8000

# API 端点
POST /chat - 聊天接口
GET /health - 健康检查
```

#### Web UI 启动
```bash
# 开发模式（同时启动后端和前端）
./bootstrap.sh -d

# Windows
bootstrap.bat -d
```

### 代码Agent接口
```python
from src.code_agent_workflow import run_code_agent_workflow

# 异步执行代码任务
result = await run_code_agent_workflow("创建一个Python Web应用", max_iterations=5)
```

## 配置管理

### 环境变量配置示例
```bash
# LLM API Keys
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# 搜索引擎配置
SEARCH_API=tavily  # tavily, duckduckgo, brave_search, arxiv
TAVILY_API_KEY=your_key
BRAVE_SEARCH_API_KEY=your_key

# 地图服务
AMAP_MAPS_API_KEY=your_key

# TTS 服务 (火山引擎)
VOLCENGINE_ACCESS_KEY=your_key
VOLCENGINE_SECRET_KEY=your_key

# RAG集成
RAG_PROVIDER=ragflow
RAGFLOW_API_URL=http://localhost:9388
RAGFLOW_API_KEY=ragflow-xxx
RAGFLOW_RETRIEVAL_SIZE=10
```

### 主配置文件 (`conf.yaml`)
```yaml
# 基础模型配置
BASIC_MODEL:
  base_url: https://openrouter.ai/api/v1
  model: "deepseek/deepseek-chat-v3-0324:free"
  api_key: your_api_key

# 推理模型配置  
REASONING_MODEL:
  base_url: https://openrouter.ai/api/v1
  model: "deepseek/deepseek-chat-v3-0324:free"
  api_key: your_api_key

# 视觉模型配置
VISION_MODEL:
  base_url: https://openrouter.ai/api/v1
  model: "google/gemini-2.5-flash-preview-05-20:thinking"
  api_key: your_api_key

# 图像生成模型
IMAGE_GEN_MODEL:
  base_url: https://openrouter.ai/api/v1
  model: "google/gemini-2.5-flash-preview-05-20:image-generation"
  api_key: your_api_key

# 地图API配置
AMAP_MAPS_API_KEY: "your_amap_key"
```

### MCP 服务器配置 (`mcp.json`)
```json
{
  "servers": {
    "mcp-github-trending": {
      "transport": "stdio",
      "command": "uvx",
      "args": ["mcp-github-trending"]
    }
  }
}
```

## 项目依赖

### Python 核心依赖 (`pyproject.toml`)
```toml
dependencies = [
    "httpx>=0.28.1",
    "langchain-community>=0.3.19", 
    "langchain-experimental>=0.3.4",
    "langchain-openai>=0.3.8",
    "langgraph>=0.3.5",
    "readabilipy>=0.3.0",
    "python-dotenv>=1.0.1",
    "fastapi>=0.110.0",
    "uvicorn>=0.27.1",
    "sse-starlette>=1.6.5",
    "pandas>=2.2.3",
    "numpy>=2.2.3", 
    "litellm>=1.63.11",
    "json-repair>=0.7.0",
    "jinja2>=3.1.3",
    "duckduckgo-search>=8.0.0",
    "inquirerpy>=0.3.4",
    "arxiv>=2.2.0",
    "mcp>=1.6.0",
    "langchain-mcp-adapters>=0.0.9",
    "tenacity>=9.0.0",
    "nest-asyncio>=1.6.0",
]
```

### 前端依赖 (`web/package.json`)
基于 Next.js 14+ 的现代化 React 应用，支持：
- TypeScript
- Tailwind CSS
- Notion-like 块编辑器 (tiptap)
- 实时通信

## 开发指南

### 快速开始

1. **环境设置**
```bash
# 克隆项目
git clone https://github.com/cklxx/agent
cd agent

# 安装Python依赖
uv sync

# 配置环境变量
cp .env.example .env
cp conf.yaml.example conf.yaml
# 编辑 .env 和 conf.yaml 添加你的API密钥

# 安装前端依赖（可选）
cd web
pnpm install
```

2. **运行项目**
```bash
# 控制台模式
uv run main.py --interactive

# Web模式 
./bootstrap.sh -d
```

### 添加新工具

1. 在 `src/tools/` 创建新的工具文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `src/tools/__init__.py` 中注册工具

```python
from langchain_core.tools import tool

@tool
def your_new_tool(param: str) -> str:
    """工具描述
    
    Args:
        param: 参数描述
        
    Returns:
        返回值描述
        
    Examples:
        - your_new_tool("example") - 使用示例
    """
    # 实现逻辑
    return result
```

### 自定义工作流

修改 `src/graph/builder.py` 或创建新的工作流文件来定制流程逻辑。

### 日志和调试

#### 日志模式
- **简化模式** (默认): 清晰的输出，专注于LLM规划和执行进度
- **调试模式**: 详细的调试信息用于开发和故障排除

```bash
# 启用调试模式
uv run main.py --debug "你的问题"
```

## 测试

### 运行测试
```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_tools.py

# 生成覆盖率报告
uv run pytest --cov=src
```

## 部署

### Docker 部署
```bash
# 构建镜像
docker build -t deeptool .

# 运行容器
docker run -p 8000:8000 deeptool

# 使用 Docker Compose
docker-compose up -d
```

## 高级功能

### MCP 集成
支持 Model Context Protocol，可以扩展私有域访问、知识图谱、网页浏览等能力。

### RAG 集成
通过 RAGFlow 集成，支持在输入中提及文件进行文档检索。RAG子系统的详细架构和组件（如`CodeIndexer`, `CodeRetriever`, `CodeRAGAdapter`）在 [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#rag-subsystem-srcrag-srccontextcode_rag_adapterpy) 中有详细描述。

### 人机协作
支持交互式修改研究计划，可使用自然语言调整AI的执行策略。这是通过 `HumanFeedback` 节点在主工作流中实现的。

### 多模态支持
支持视觉模型和图像生成，可处理图像输入并生成图像内容。

## 常见问题

### Q: 如何配置不同的LLM提供商？
A: 在 `conf.yaml` 中配置不同的模型。系统通过 LiteLLM 支持大多数主流提供商，并按用途（如 'reasoning', 'basic'）对模型进行分类。详情请见 [LLM Integration in SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#llm-integration-srcllms)。

### Q: 如何添加新的搜索引擎？
A: 在 `.env` 中设置 `SEARCH_API` 变量。支持的引擎包括 Tavily, DuckDuckGo, Brave Search, 和 Arxiv。工具的集成方式概述于 [Tool System in SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#tool-system-srctools)。

### Q: 如何自定义代码执行流程？
A: 代码执行流程由 `src/code_agent_workflow.py` 和 `src/rag_enhanced_code_agent_workflow.py` 中的工作流类管理。这些工作流通常包含规划、实现和验证等阶段。更广泛的工作流结构见 [Main Workflow in SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#main-workflow-srcworkflowpy-and-srcgraphbuilderpy)。

### Q: Web UI 如何与后端通信？
A: 前端 (`web/` 目录下的 Next.js 应用) 通过 API 调用与 `server.py` 托管的 FastAPI 后端进行通信。详情请见 [Web Interface in SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md#web-interface-web)。

## 贡献指南

1. Fork 项目仓库
2. 创建功能分支
3. 提交更改 (遵循代码规范)
4. 发起 Pull Request

### 代码规范
- 使用 Black 格式化代码
- 添加完整的类型注解
- 编写详细的文档字符串
- 遵循 PEP 8 规范
- 为新功能添加测试

## 相关资源

- [项目 GitHub](https://github.com/cklxx/agent
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 文档](https://python.langchain.com/)
- [LiteLLM 文档](https://docs.litellm.ai/)
- [System Architecture Document](SYSTEM_ARCHITECTURE.md)
- [Configuration Guide](configuration_guide.md)
- [Logging Guide](logging_guide.md)

---

*本文档基于实际项目结构持续更新，如有问题请提交 Issue 或 PR。* 