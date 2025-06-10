#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

"""
RAG增强Code Agent独立演示
这是一个独立的demo文件，演示RAG和上下文增强代码生成的概念
不依赖项目代码，而是通过模拟来展示核心功能
"""

import asyncio
import json
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CodePattern:
    """代码模式数据结构"""

    name: str
    language: str
    pattern_type: str
    code_snippet: str
    description: str
    usage_count: int = 0


@dataclass
class ContextInfo:
    """上下文信息数据结构"""

    file_path: str
    function_name: str
    imports: List[str]
    dependencies: List[str]
    patterns: List[str]


class MockRAGDatabase:
    """模拟RAG数据库"""

    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.context_cache = {}

    def _initialize_patterns(self) -> List[CodePattern]:
        """初始化模拟代码模式"""
        return [
            CodePattern(
                name="http_client_pattern",
                language="python",
                pattern_type="client",
                code_snippet="""
class HTTPClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = await self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"HTTP GET failed: {e}")
            raise
                """,
                description="标准HTTP客户端模式，包含错误处理和超时设置",
            ),
            CodePattern(
                name="error_handler_pattern",
                language="python",
                pattern_type="error_handling",
                code_snippet="""
def handle_api_error(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPError as e:
            logger.error(f"API error in {func.__name__}: {e}")
            raise APIException(f"API call failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise
    return wrapper
                """,
                description="通用API错误处理装饰器模式",
            ),
            CodePattern(
                name="async_retry_pattern",
                language="python",
                pattern_type="retry_mechanism",
                code_snippet="""
async def retry_async(func, max_retries: int = 3, delay: float = 1.0):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(delay * (2 ** attempt))
    return None
                """,
                description="异步重试机制模式",
            ),
            CodePattern(
                name="config_manager_pattern",
                language="python",
                pattern_type="configuration",
                code_snippet="""
class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default=None):
        return self._config.get(key, default)
                """,
                description="配置管理器模式",
            ),
            CodePattern(
                name="logger_setup_pattern",
                language="python",
                pattern_type="logging",
                code_snippet="""
def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
                """,
                description="标准日志设置模式",
            ),
        ]

    def search_patterns(
        self, query: str, pattern_type: Optional[str] = None
    ) -> List[CodePattern]:
        """搜索相关代码模式"""
        results = []
        query_lower = query.lower()

        for pattern in self.patterns:
            # 简单的文本匹配
            if (
                query_lower in pattern.name.lower()
                or query_lower in pattern.description.lower()
                or query_lower in pattern.code_snippet.lower()
            ):

                if pattern_type is None or pattern.pattern_type == pattern_type:
                    pattern.usage_count += 1
                    results.append(pattern)

        # 按使用频率排序
        return sorted(results, key=lambda x: x.usage_count, reverse=True)

    def get_context_info(self, file_path: str) -> Optional[ContextInfo]:
        """获取文件上下文信息"""
        # 模拟上下文信息
        mock_contexts = {
            "client.py": ContextInfo(
                file_path="client.py",
                function_name="HTTPClient",
                imports=["requests", "asyncio", "logging"],
                dependencies=["requests", "aiohttp"],
                patterns=["http_client_pattern", "error_handler_pattern"],
            ),
            "utils.py": ContextInfo(
                file_path="utils.py",
                function_name="retry_async",
                imports=["asyncio", "functools"],
                dependencies=[],
                patterns=["async_retry_pattern", "error_handler_pattern"],
            ),
            "config.py": ContextInfo(
                file_path="config.py",
                function_name="ConfigManager",
                imports=["yaml", "pathlib"],
                dependencies=["pyyaml"],
                patterns=["config_manager_pattern", "logger_setup_pattern"],
            ),
        }

        return mock_contexts.get(file_path)


class MockRAGEnhancedCodeAgent:
    """模拟RAG增强代码代理"""

    def __init__(self):
        self.rag_db = MockRAGDatabase()
        self.context_history = []
        self.execution_stats = {
            "tasks_executed": 0,
            "rag_searches": 0,
            "patterns_used": 0,
            "context_hits": 0,
        }

    async def execute_task_with_rag(
        self, task: str, context_files: List[str] = None
    ) -> Dict[str, Any]:
        """执行RAG增强的任务"""
        print(f"🎯 执行任务: {task[:50]}...")

        # 模拟RAG检索
        relevant_patterns = self._retrieve_relevant_patterns(task)
        context_info = self._gather_context_info(context_files or [])

        # 模拟代码生成
        generated_code = await self._generate_code_with_rag(
            task, relevant_patterns, context_info
        )

        # 更新统计信息
        self.execution_stats["tasks_executed"] += 1
        self.execution_stats["rag_searches"] += 1
        self.execution_stats["patterns_used"] += len(relevant_patterns)
        self.execution_stats["context_hits"] += len(context_info)

        # 保存执行历史
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "patterns_used": [p.name for p in relevant_patterns],
            "context_files": context_files or [],
            "success": True,
        }
        self.context_history.append(execution_record)

        return {
            "success": True,
            "rag_enhanced": len(relevant_patterns) > 0,
            "context_used": len(context_info) > 0,
            "patterns_found": len(relevant_patterns),
            "context_files_analyzed": len(context_info),
            "generated_code": generated_code,
            "execution_stats": self.execution_stats.copy(),
        }

    def _retrieve_relevant_patterns(self, task: str) -> List[CodePattern]:
        """检索相关的代码模式"""
        # 模拟智能搜索
        search_terms = self._extract_search_terms(task)
        all_patterns = []

        for term in search_terms:
            patterns = self.rag_db.search_patterns(term)
            all_patterns.extend(patterns)

        # 去重并限制结果数量
        unique_patterns = {p.name: p for p in all_patterns}
        return list(unique_patterns.values())[:3]  # 返回前3个最相关的模式

    def _extract_search_terms(self, task: str) -> List[str]:
        """从任务描述中提取搜索词"""
        # 简单的关键词提取
        keywords = {
            "http": ["client", "request", "api"],
            "错误": ["error", "exception", "handling"],
            "重试": ["retry", "async"],
            "配置": ["config", "setting"],
            "日志": ["log", "logger"],
            "文档": ["documentation", "doc"],
            "测试": ["test", "unit"],
            "数据库": ["database", "db", "sql"],
        }

        task_lower = task.lower()
        search_terms = []

        for chinese_key, english_terms in keywords.items():
            if chinese_key in task_lower:
                search_terms.extend(english_terms)

        # 也直接使用任务中的英文单词
        words = task.split()
        for word in words:
            if word.isalpha() and len(word) > 3:
                search_terms.append(word.lower())

        return list(set(search_terms))

    def _gather_context_info(self, context_files: List[str]) -> List[ContextInfo]:
        """收集上下文信息"""
        context_info = []
        for file_path in context_files:
            info = self.rag_db.get_context_info(file_path)
            if info:
                context_info.append(info)
        return context_info

    async def _generate_code_with_rag(
        self, task: str, patterns: List[CodePattern], context_info: List[ContextInfo]
    ) -> str:
        """基于RAG和上下文生成代码"""
        # 模拟代码生成延迟
        await asyncio.sleep(0.5)

        # 构建代码模板
        code_parts = []

        # 添加imports（基于上下文）
        imports = set()
        for ctx in context_info:
            imports.update(ctx.imports)

        if imports:
            code_parts.append("# 导入依赖")
            for imp in sorted(imports):
                code_parts.append(f"import {imp}")
            code_parts.append("")

        # 基于模式生成代码
        if patterns:
            code_parts.append("# 基于RAG检索的代码模式生成")
            for pattern in patterns:
                code_parts.append(f"# 使用模式: {pattern.name}")
                code_parts.append(f"# 描述: {pattern.description}")
                code_parts.append(pattern.code_snippet.strip())
                code_parts.append("")

        # 添加任务特定的代码
        code_parts.append("# 任务特定实现")
        code_parts.append(self._generate_task_specific_code(task))

        return "\n".join(code_parts)

    def _generate_task_specific_code(self, task: str) -> str:
        """生成任务特定的代码"""
        # 简单的任务类型识别和代码生成
        if "http" in task.lower() or "客户端" in task:
            return '''
# HTTP客户端实现
class EnhancedHTTPClient(HTTPClient):
    """RAG增强的HTTP客户端"""
    
    def __init__(self, base_url: str, **kwargs):
        super().__init__(base_url, **kwargs)
        self.logger = setup_logger(__name__)
    
    @handle_api_error
    async def request_with_retry(self, method: str, endpoint: str, **kwargs):
        """带重试机制的请求方法"""
        async def _request():
            return await getattr(self.session, method.lower())(
                f"{self.base_url}/{endpoint.lstrip('/')}", **kwargs
            )
        
        return await retry_async(_request, max_retries=3)
            '''

        elif "配置" in task or "config" in task.lower():
            return '''
# 配置管理实现
class EnhancedConfigManager(ConfigManager):
    """RAG增强的配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        super().__init__(config_path)
        self.logger = setup_logger(__name__)
        self.logger.info(f"配置加载完成: {config_path}")
    
    def validate_config(self) -> bool:
        """验证配置完整性"""
        required_keys = ["database", "api", "logging"]
        for key in required_keys:
            if key not in self._config:
                self.logger.error(f"缺少必需配置项: {key}")
                return False
        return True
            '''

        else:
            return f'''
# 通用任务实现
class TaskImplementation:
    """基于RAG增强的任务实现"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.logger.info("任务实现初始化完成")
    
    async def execute(self):
        """执行任务: {task[:30]}..."""
        self.logger.info("开始执行任务")
        # TODO: 实现具体任务逻辑
        pass
            '''

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "total_tasks": self.execution_stats["tasks_executed"],
            "rag_usage": {
                "searches_performed": self.execution_stats["rag_searches"],
                "patterns_utilized": self.execution_stats["patterns_used"],
                "context_hits": self.execution_stats["context_hits"],
            },
            "pattern_effectiveness": {
                "most_used_patterns": self._get_most_used_patterns(),
                "pattern_success_rate": 0.95,  # 模拟成功率
            },
            "context_utilization": {
                "files_analyzed": len(
                    set(sum([r["context_files"] for r in self.context_history], []))
                ),
                "context_hit_rate": 0.80,  # 模拟命中率
            },
        }

    def _get_most_used_patterns(self) -> List[Dict[str, Any]]:
        """获取最常用的模式"""
        pattern_usage = {}
        for pattern in self.rag_db.patterns:
            if pattern.usage_count > 0:
                pattern_usage[pattern.name] = {
                    "usage_count": pattern.usage_count,
                    "description": pattern.description,
                }

        return sorted(
            pattern_usage.items(), key=lambda x: x[1]["usage_count"], reverse=True
        )[:5]


# 演示函数
async def demo_1_create_http_client():
    """演示1: 创建HTTP客户端 - RAG增强"""
    print("🔥 演示1: 创建HTTP客户端 - RAG模式检索")
    print("=" * 60)

    agent = MockRAGEnhancedCodeAgent()

    task = """
    创建一个HTTP客户端类，需要支持：
    1. GET、POST、PUT、DELETE方法
    2. 错误处理和重试机制
    3. 超时设置和请求头自定义
    4. 异步操作支持
    5. 日志记录功能
    """

    result = await agent.execute_task_with_rag(task, ["client.py", "utils.py"])

    print(f"\n📊 执行结果:")
    print(f"   ✅ 成功: {result['success']}")
    print(f"   🔍 RAG增强: {result['rag_enhanced']}")
    print(f"   📋 找到模式: {result['patterns_found']} 个")
    print(f"   📁 上下文文件: {result['context_files_analyzed']} 个")

    if result["patterns_found"] > 0:
        print(f"\n🎯 生成的代码片段:")
        print("```python")
        print(
            result["generated_code"][:500] + "..."
            if len(result["generated_code"]) > 500
            else result["generated_code"]
        )
        print("```")

    return result


async def demo_2_refactor_with_context():
    """演示2: 基于上下文的代码重构"""
    print("\n🔧 演示2: 上下文感知重构")
    print("=" * 60)

    agent = MockRAGEnhancedCodeAgent()

    task = """
    重构现有代码，优化目标：
    1. 提高代码可读性
    2. 优化错误处理
    3. 增强类型注解
    4. 改进日志记录
    5. 保持代码一致性
    """

    result = await agent.execute_task_with_rag(
        task, ["client.py", "utils.py", "config.py"]
    )

    print(f"\n📊 重构结果:")
    print(f"   ✅ 成功: {result['success']}")
    print(f"   🧠 上下文使用: {result['context_used']}")
    print(f"   📋 模式匹配: {result['patterns_found']} 个")

    # 显示重构建议
    print(f"\n💡 重构建议:")
    print("   • 使用装饰器模式处理错误")
    print("   • 实现异步重试机制")
    print("   • 统一日志记录格式")
    print("   • 添加配置验证逻辑")

    return result


async def demo_3_intelligent_debugging():
    """演示3: 智能调试和修复"""
    print("\n🐛 演示3: 智能调试 - 模式识别修复")
    print("=" * 60)

    agent = MockRAGEnhancedCodeAgent()

    task = """
    分析代码问题并提供修复建议：
    1. 检查常见bug模式
    2. 验证错误处理完整性
    3. 检查资源泄漏
    4. 异步代码正确性
    5. 性能优化建议
    """

    result = await agent.execute_task_with_rag(task, ["client.py", "utils.py"])

    print(f"\n📊 调试结果:")
    print(f"   ✅ 成功: {result['success']}")
    print(f"   🔍 RAG增强: {result['rag_enhanced']}")

    # 模拟调试发现
    print(f"\n🔍 发现的问题:")
    print("   • 缺少连接池管理")
    print("   • 异常处理不够细化")
    print("   • 日志级别配置不当")
    print("   • 重试逻辑可能导致阻塞")

    print(f"\n🛠️ 修复建议:")
    print("   • 使用连接池管理HTTP连接")
    print("   • 实现分层异常处理")
    print("   • 配置结构化日志")
    print("   • 添加重试熔断机制")

    return result


async def demo_4_documentation_generation():
    """演示4: 智能文档生成"""
    print("\n📚 演示4: 智能文档生成 - 代码分析驱动")
    print("=" * 60)

    agent = MockRAGEnhancedCodeAgent()

    task = """
    基于代码分析生成文档：
    1. API接口文档
    2. 使用示例
    3. 配置说明
    4. 最佳实践
    5. 故障排除指南
    """

    result = await agent.execute_task_with_rag(task, ["client.py", "config.py"])

    print(f"\n📊 文档生成结果:")
    print(f"   ✅ 成功: {result['success']}")
    print(f"   📋 分析文件: {result['context_files_analyzed']} 个")

    # 模拟生成的文档结构
    print(f"\n📖 生成的文档结构:")
    print("   📄 API参考文档")
    print("   📄 快速开始指南")
    print("   📄 配置参考")
    print("   📄 最佳实践")
    print("   📄 故障排除")
    print("   📄 代码示例")

    return result


async def demo_5_performance_optimization():
    """演示5: 性能优化建议"""
    print("\n⚡ 演示5: 性能优化 - RAG驱动分析")
    print("=" * 60)

    agent = MockRAGEnhancedCodeAgent()

    task = """
    分析性能瓶颈并提供优化建议：
    1. 内存使用优化
    2. I/O操作优化
    3. 并发性能改进
    4. 缓存策略优化
    5. 数据库查询优化
    """

    result = await agent.execute_task_with_rag(
        task, ["client.py", "utils.py", "config.py"]
    )

    print(f"\n📊 性能分析结果:")
    print(f"   ✅ 成功: {result['success']}")
    print(f"   🔍 RAG增强: {result['rag_enhanced']}")

    # 模拟性能分析结果
    print(f"\n📈 性能优化建议:")
    print("   • 🚀 使用连接池减少连接开销")
    print("   • 💾 实现智能缓存机制")
    print("   • ⚡ 优化异步并发处理")
    print("   • 🗃️ 批量处理减少I/O次数")
    print("   • 📊 添加性能监控指标")

    # 模拟性能指标
    print(f"\n📊 预期性能提升:")
    print("   • 响应时间: 减少 40%")
    print("   • 内存使用: 减少 25%")
    print("   • 并发处理: 提升 60%")
    print("   • 缓存命中率: 85%+")

    return result


async def demonstrate_rag_capabilities():
    """演示RAG能力概览"""
    print("\n🚀 RAG增强Code Agent能力演示")
    print("=" * 80)

    agent = MockRAGEnhancedCodeAgent()

    print("🔧 核心RAG功能:")
    print("   • 🔍 语义代码搜索 - 基于相似性检索代码模式")
    print("   • 🧠 上下文感知 - 利用历史执行和文件上下文")
    print("   • 📚 模式识别 - 自动识别和应用最佳实践")
    print("   • 🎯 智能生成 - 基于RAG的上下文感知代码生成")
    print("   • 📊 质量保证 - 模式一致性和架构合规性检查")

    print(f"\n📋 支持的任务类型:")
    print("   • 🏗️ 新功能开发")
    print("   • 🔧 代码重构优化")
    print("   • 🐛 智能调试修复")
    print("   • 📚 文档自动生成")
    print("   • ⚡ 性能优化分析")
    print("   • 🧪 测试代码生成")
    print("   • 🔐 安全漏洞检测")

    print(f"\n📊 RAG增强效果:")
    print("   • 📈 代码质量提升: 95%+")
    print("   • ⚡ 开发效率提升: 60%+")
    print("   • 🎯 模式一致性: 90%+")
    print("   • 🔍 上下文利用率: 80%+")
    print("   • 🛡️ 错误减少率: 70%+")

    # 显示模拟的RAG数据库统计
    patterns = agent.rag_db.patterns
    print(f"\n🗃️ RAG知识库统计:")
    print(f"   • 代码模式: {len(patterns)} 个")
    print(f"   • 支持语言: Python, JavaScript, TypeScript")
    print(f"   • 模式类型: {len(set(p.pattern_type for p in patterns))} 种")
    print(f"   • 知识库大小: ~2.5MB (模拟)")


async def main():
    """主演示函数"""
    print("🎯 RAG增强Code Agent独立演示")
    print("这是一个独立的demo，展示RAG和上下文增强的核心概念")
    print("=" * 80)

    try:
        # 显示RAG能力概览
        await demonstrate_rag_capabilities()

        # 可选的演示示例
        demos = [
            ("创建HTTP客户端", demo_1_create_http_client),
            ("上下文感知重构", demo_2_refactor_with_context),
            ("智能调试修复", demo_3_intelligent_debugging),
            ("智能文档生成", demo_4_documentation_generation),
            ("性能优化分析", demo_5_performance_optimization),
        ]

        print(f"\n📋 可用演示:")
        for i, (name, _) in enumerate(demos, 1):
            print(f"   {i}. {name}")

        print(f"\n💬 请选择要运行的演示 (1-{len(demos)})，或按回车查看所有演示:")

        try:
            choice = input().strip()
            if choice and choice.isdigit():
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(demos):
                    name, demo_func = demos[choice_idx]
                    print(f"\n🚀 运行演示: {name}")
                    result = await demo_func()

                    if result.get("success"):
                        print(f"\n✅ 演示 '{name}' 执行成功!")
                    else:
                        print(f"\n❌ 演示 '{name}' 执行失败")
                else:
                    print("❌ 无效的选择")
            else:
                # 运行所有演示
                print(f"\n🎬 运行所有演示...")
                agent = MockRAGEnhancedCodeAgent()

                for name, demo_func in demos:
                    print(f"\n{'='*20} {name} {'='*20}")
                    result = await demo_func()
                    await asyncio.sleep(1)  # 添加延迟以便观察

                # 显示最终统计
                print(f"\n📊 演示完成统计:")
                summary = agent.get_execution_summary()
                print(f"   • 总任务数: {summary['total_tasks']}")
                print(f"   • RAG搜索: {summary['rag_usage']['searches_performed']} 次")
                print(f"   • 使用模式: {summary['rag_usage']['patterns_utilized']} 个")
                print(f"   • 上下文命中: {summary['rag_usage']['context_hits']} 次")
                print(
                    f"   • 模式成功率: {summary['pattern_effectiveness']['pattern_success_rate']*100:.1f}%"
                )
                print(
                    f"   • 上下文命中率: {summary['context_utilization']['context_hit_rate']*100:.1f}%"
                )

        except KeyboardInterrupt:
            print("\n👋 用户中断演示")
            return

        print(f"\n🎉 RAG增强Code Agent演示完成!")
        print("💡 这个demo展示了RAG和上下文如何增强代码生成的核心概念")
        print("💡 实际实现中，RAG会检索真实的代码库和模式数据")

    except Exception as e:
        print(f"❌ 演示执行失败: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🔧 启动RAG增强Code Agent独立演示...")
    asyncio.run(main())
