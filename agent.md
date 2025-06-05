# Agent Development Guide

本文档为 **DeepTool** 项目的 Code Agent 开发指南，提供项目架构、API 接口、工具函数等详细信息。

## 项目概述

**DeepTool** 是一个基于 LangGraph 的智能 Agent 系统，支持多种工具集成和工作流管理。

### 核心特性
- 🔧 **多工具集成**: 搜索、地图、TTS、Python REPL、爬虫等
- 🌐 **Web 界面**: Node.js + React 前端
- 📊 **工作流管理**: 基于 LangGraph 的状态图
- 🔍 **智能搜索**: 支持多种搜索引擎 (Tavily, Brave, DuckDuckGo)
- 🗺️ **地图服务**: 集成高德地图 API
- 🎤 **语音合成**: TTS 支持

## 项目架构

```
agent/
├── src/                    # 核心代码
│   ├── agents/            # Agent 定义
│   ├── config/            # 配置管理
│   ├── crawler/           # 爬虫模块
│   ├── graph/             # LangGraph 工作流
│   ├── llms/              # LLM 集成
│   ├── podcast/           # 播客功能
│   ├── prompts/           # Prompt 模板
│   ├── prose/             # 文本处理
│   ├── ppt/               # PPT 生成
│   ├── rag/               # RAG 检索
│   ├── server/            # 服务端
│   ├── tools/             # 工具函数
│   ├── utils/             # 工具类
│   └── workflow.py        # 主工作流
├── web/                   # 前端代码
├── docs/                  # 文档
├── examples/              # 示例代码
├── tests/                 # 测试
├── main.py               # 入口文件
├── server.py             # Web 服务器
├── conf.yaml             # 配置文件
└── pyproject.toml        # Python 项目配置
```

## 环境要求

- **Python**: 3.12+
- **Node.js**: 22+
- **依赖管理**: uv (推荐)
- **包管理器**: pnpm

## 核心模块

### 1. 工具模块 (`src/tools/`)

#### 搜索工具 (`search.py`)
```python
# 主要函数
search_web(query: str) -> str
search_web_with_sources(query: str) -> Dict
```

#### 地图工具 (`maps.py`)
```python
# 位置搜索
search_location(keyword: str) -> List[Location]
search_location_in_city(keyword: str, city: str) -> List[Location]

# 路线规划
get_route(origin: str, destination: str, mode: str = "driving") -> Route

# 周边搜索
get_nearby_places(location: str, radius: int = 1000, types: Optional[str] = None) -> List[Location]
```

#### TTS 工具 (`tts.py`)
```python
# 语音合成
text_to_speech(text: str, voice: str = "default") -> bytes
```

#### Python REPL (`python_repl.py`)
```python
# 代码执行
execute_python_code(code: str) -> str
```

#### 爬虫工具 (`crawl.py`)
```python
# 网页抓取
crawl_url(url: str) -> str
```

### 2. 图形工作流 (`src/graph/`)

#### 节点类型 (`nodes.py`)
- `PlannerNode`: 规划节点
- `DecideToolNode`: 工具决策节点
- `ExecuteToolNode`: 工具执行节点
- `ResponseNode`: 响应生成节点

#### 状态类型 (`types.py`)
```python
class AgentState(TypedDict):
    user_input: str
    plan: str
    tool_calls: List[ToolCall]
    response: str
    iteration: int
```

### 3. LLM 集成 (`src/llms/`)

支持多种 LLM 提供商：
- OpenAI
- Anthropic
- 本地模型
- 其他 LiteLLM 支持的提供商

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
```

#### Web 服务器 (`server.py`)
```python
# 启动服务
uvicorn server:app --host 0.0.0.0 --port 8000

# API 端点
POST /chat - 聊天接口
GET /health - 健康检查
```

## 配置管理

### 环境变量 (`.env`)
```bash
# LLM API Keys
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# 搜索引擎
TAVILY_API_KEY=your_key
BRAVE_SEARCH_API_KEY=your_key

# 地图服务
AMAP_MAPS_API_KEY=your_key

# TTS 服务
VOLCENGINE_ACCESS_KEY=your_key
VOLCENGINE_SECRET_KEY=your_key
```

### 配置文件 (`conf.yaml`)
```yaml
llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.1

search:
  default_engine: "tavily"
  max_results: 5

maps:
  provider: "amap"
  default_radius: 1000
```

## 开发指南

### 添加新工具

1. 在 `src/tools/` 创建新的工具文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `src/tools/__init__.py` 中注册工具
4. 更新配置文件

```python
from langchain_core.tools import tool

@tool
def your_new_tool(param: str) -> str:
    """工具描述"""
    # 实现逻辑
    return result
```

### 添加新节点

1. 在 `src/graph/nodes.py` 中定义新节点
2. 继承 `BaseNode` 类
3. 实现 `process` 方法
4. 在 `builder.py` 中注册节点

```python
class YourNewNode(BaseNode):
    def process(self, state: AgentState) -> AgentState:
        # 处理逻辑
        return state
```

### 自定义 Prompt

1. 在 `src/prompts/template.py` 中添加新模板
2. 使用 Jinja2 语法
3. 在节点中引用模板

```python
YOUR_PROMPT = """
{{ user_input }}
请根据以上输入进行处理...
"""
```

## 调试和日志

### 启用调试模式
```python
from src.workflow import enable_debug_logging
enable_debug_logging()
```

### 日志级别
- `INFO`: 基本信息
- `DEBUG`: 详细调试信息
- `ERROR`: 错误信息

### 常用调试技巧
1. 使用 `--debug` 参数启动
2. 检查 `logs/` 目录下的日志文件
3. 使用 `print()` 在节点中输出状态信息

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

### 测试结构
```
tests/
├── test_tools.py      # 工具测试
├── test_graph.py      # 图形工作流测试
├── test_config.py     # 配置测试
└── conftest.py        # 测试配置
```

## 部署

### 使用 Docker
```bash
# 构建镜像
docker build -t agent .

# 运行容器
docker run -p 8000:8000 agent
```

### 使用 Docker Compose
```bash
docker-compose up -d
```

## 常见问题

### Q: 如何添加新的 LLM 提供商？
A: 在 `src/llms/` 中添加新的提供商集成，使用 LiteLLM 统一接口。

### Q: 如何自定义工作流？
A: 修改 `src/graph/builder.py` 中的图形构建逻辑，添加或删除节点和边。

### Q: 如何处理工具调用错误？
A: 在工具函数中使用 try-catch 处理异常，返回错误信息给 Agent。

### Q: 如何优化响应速度？
A: 1) 使用更快的 LLM 模型；2) 减少不必要的工具调用；3) 启用缓存机制。

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

### 代码规范
- 使用 Black 格式化代码
- 添加类型注解
- 编写文档字符串
- 遵循 PEP 8 规范

## 相关资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 文档](https://python.langchain.com/)
- [项目 GitHub](https://github.com/bytedance/agent)

## 代码示例

### 完整的工具开发示例

#### 1. 创建天气查询工具 (`src/tools/weather.py`)
```python
import requests
from typing import Dict, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class WeatherInfo(BaseModel):
    """天气信息模型"""
    temperature: float = Field(..., description="温度 (摄氏度)")
    description: str = Field(..., description="天气描述")
    humidity: int = Field(..., description="湿度百分比")
    city: str = Field(..., description="城市名称")

@tool
def get_weather(city: str, api_key: Optional[str] = None) -> WeatherInfo:
    """获取指定城市的天气信息
    
    Args:
        city: 城市名称 (如: "北京", "上海", "深圳")
        api_key: OpenWeatherMap API key (可选，从环境变量获取)
    
    Returns:
        WeatherInfo: 包含温度、天气描述等信息的对象
        
    Examples:
        - get_weather("北京") - 获取北京天气
        - get_weather("Shanghai") - 获取上海天气
    """
    import os
    
    if not api_key:
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            raise ValueError("需要设置 OPENWEATHER_API_KEY 环境变量")
    
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",  # 使用摄氏度
        "lang": "zh_cn"     # 中文描述
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        return WeatherInfo(
            temperature=data["main"]["temp"],
            description=data["weather"][0]["description"],
            humidity=data["main"]["humidity"],
            city=data["name"]
        )
    except requests.RequestException as e:
        raise Exception(f"获取天气数据失败: {e}")
    except KeyError as e:
        raise Exception(f"天气数据格式错误: {e}")
```

#### 2. 注册新工具 (`src/tools/__init__.py`)
```python
from .weather import get_weather

__all__ = [
    # ... 现有工具 ...
    "get_weather",
]
```

#### 3. 创建自定义节点 (`src/graph/custom_nodes.py`)
```python
import logging
from typing import Dict, Any
from src.graph.types import AgentState
from src.prompts.template import render_template

logger = logging.getLogger(__name__)

class WeatherAnalysisNode:
    """天气分析节点 - 提供天气建议"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def process(self, state: AgentState) -> AgentState:
        """分析天气数据并提供建议"""
        logger.info("开始天气分析...")
        
        # 获取工具调用结果中的天气数据
        weather_data = self._extract_weather_data(state)
        if not weather_data:
            return state
        
        # 生成天气建议
        advice_prompt = render_template("weather_advice.md", {
            "weather_data": weather_data,
            "user_query": state.get("user_input", "")
        })
        
        try:
            advice = self.llm.invoke(advice_prompt)
            
            # 更新状态
            state["weather_advice"] = advice.content
            logger.info("天气建议生成完成")
            
        except Exception as e:
            logger.error(f"生成天气建议失败: {e}")
            state["weather_advice"] = "抱歉，无法生成天气建议"
        
        return state
    
    def _extract_weather_data(self, state: AgentState) -> Dict[str, Any]:
        """从状态中提取天气数据"""
        tool_results = state.get("tool_results", [])
        for result in tool_results:
            if result.get("tool") == "get_weather":
                return result.get("result", {})
        return {}
```

#### 4. 创建自定义 Prompt 模板 (`src/prompts/weather_advice.md`)
```markdown
# 天气建议分析

## 当前天气信息
- **城市**: {{ weather_data.city }}
- **温度**: {{ weather_data.temperature }}°C
- **天气**: {{ weather_data.description }}
- **湿度**: {{ weather_data.humidity }}%

## 用户查询
{{ user_query }}

## 请提供建议

请根据当前天气情况，为用户提供以下方面的建议：

1. **穿衣建议**: 根据温度和天气状况推荐合适的着装
2. **出行建议**: 是否适合外出，需要注意什么
3. **健康建议**: 基于天气给出健康相关的提醒
4. **活动建议**: 推荐适合当前天气的活动

请用友好、实用的语言回答，让建议既专业又贴心。
```

### 工作流集成示例

#### 1. 扩展工作流 (`src/graph/enhanced_builder.py`)
```python
from langgraph.graph import StateGraph, END
from src.graph.types import AgentState
from src.graph.nodes import PlannerNode, DecideToolNode, ExecuteToolNode, ResponseNode
from src.graph.custom_nodes import WeatherAnalysisNode

def build_enhanced_graph(llm, tools):
    """构建增强版工作流图"""
    
    # 创建节点
    planner = PlannerNode(llm)
    decide_tool = DecideToolNode(llm, tools)
    execute_tool = ExecuteToolNode(tools)
    weather_analysis = WeatherAnalysisNode(llm)
    response = ResponseNode(llm)
    
    # 构建状态图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("planner", planner.process)
    workflow.add_node("decide_tool", decide_tool.process)
    workflow.add_node("execute_tool", execute_tool.process)
    workflow.add_node("weather_analysis", weather_analysis.process)
    workflow.add_node("response", response.process)
    
    # 设置入口点
    workflow.set_entry_point("planner")
    
    # 添加边（控制流）
    workflow.add_edge("planner", "decide_tool")
    
    # 条件边：根据工具类型决定后续流程
    def should_analyze_weather(state):
        tool_calls = state.get("tool_calls", [])
        for call in tool_calls:
            if call.get("tool") == "get_weather":
                return "weather_analysis"
        return "response"
    
    workflow.add_conditional_edges(
        "execute_tool",
        should_analyze_weather,
        {
            "weather_analysis": "weather_analysis",
            "response": "response"
        }
    )
    
    workflow.add_edge("weather_analysis", "response")
    workflow.add_edge("response", END)
    
    return workflow.compile()
```

### 最佳实践

#### 1. 错误处理模式
```python
from functools import wraps
import logging

def handle_tool_errors(func):
    """工具错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"工具 {func.__name__} 执行失败: {e}")
            return f"抱歉，{func.__name__} 工具暂时不可用: {str(e)}"
    return wrapper

@tool
@handle_tool_errors
def robust_search(query: str) -> str:
    """带错误处理的搜索工具"""
    # 实现搜索逻辑
    pass
```

#### 2. 配置管理模式
```python
from dataclasses import dataclass
from typing import Optional
import yaml

@dataclass
class ToolConfig:
    """工具配置类"""
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    base_url: Optional[str] = None

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "conf.yaml"):
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}
    
    def get_tool_config(self, tool_name: str) -> ToolConfig:
        """获取特定工具的配置"""
        tool_config = self._config.get("tools", {}).get(tool_name, {})
        return ToolConfig(**tool_config)
```

#### 3. 缓存模式
```python
from functools import lru_cache
import hashlib
import json
import time

class ToolCache:
    """工具结果缓存"""
    
    def __init__(self, ttl: int = 3600):  # 1小时过期
        self.cache = {}
        self.ttl = ttl
    
    def get_cache_key(self, tool_name: str, **kwargs) -> str:
        """生成缓存键"""
        data = {"tool": tool_name, "args": kwargs}
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()
    
    def get(self, key: str):
        """获取缓存"""
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value):
        """设置缓存"""
        self.cache[key] = (value, time.time())

# 全局缓存实例
tool_cache = ToolCache()

def cached_tool(func):
    """工具缓存装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = tool_cache.get_cache_key(func.__name__, **kwargs)
        
        # 尝试从缓存获取
        cached_result = tool_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # 执行工具函数
        result = func(*args, **kwargs)
        
        # 缓存结果
        tool_cache.set(cache_key, result)
        
        return result
    
    return wrapper
```

#### 4. 异步工具模式
```python
import asyncio
from typing import List
from langchain_core.tools import tool

@tool
async def async_batch_search(queries: List[str]) -> List[str]:
    """异步批量搜索工具"""
    
    async def single_search(query: str) -> str:
        # 模拟异步搜索
        await asyncio.sleep(1)
        return f"搜索结果: {query}"
    
    # 并发执行所有搜索
    tasks = [single_search(query) for query in queries]
    results = await asyncio.gather(*tasks)
    
    return results

# 在工作流中使用异步工具
async def async_execute_tool(state: AgentState) -> AgentState:
    """异步执行工具"""
    tool_calls = state.get("tool_calls", [])
    
    for call in tool_calls:
        if call["tool"] == "async_batch_search":
            result = await async_batch_search.ainvoke(call["args"])
            state["tool_results"] = state.get("tool_results", []) + [result]
    
    return state
```

---

*本文档持续更新，如有问题请提交 Issue 或 PR。* 