"""
RAG增强搜索工具 - 结合传统文件搜索和RAG检索结果
"""

import logging
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from langchain_core.tools import tool

# 导入传统搜索工具
from .file_system_tools import (
    glob_search as glob_search_raw,
    grep_search as grep_search_raw,
)

# 导入RAG相关模块
from ..rag.enhanced_retriever import EnhancedRAGRetriever
from ..rag.code_retriever import CodeRetriever
from ..context import RAGContextManager, ContextManager, ContextType

logger = logging.getLogger(__name__)


class RAGEnhancedSearchTools:
    """RAG增强搜索工具类"""

    def __init__(
        self,
        workspace: Optional[str] = None,
        use_enhanced_retriever: bool = True,
        enable_context_integration: bool = True,
    ):
        """
        初始化RAG增强搜索工具

        Args:
            workspace: 工作区路径
            use_enhanced_retriever: 是否使用增强检索器
            enable_context_integration: 是否启用上下文集成
        """
        self.workspace = workspace
        self.workspace_path = Path(workspace).resolve() if workspace else None
        self.use_enhanced_retriever = use_enhanced_retriever
        self.enable_context_integration = enable_context_integration

        # 初始化RAG检索器
        if workspace:
            if use_enhanced_retriever:
                self.rag_retriever = EnhancedRAGRetriever(
                    repo_path=workspace,
                    db_path="temp/rag_data/enhanced_rag",
                    use_intelligent_filter=True,
                )
            else:
                self.rag_retriever = CodeRetriever(
                    repo_path=workspace, db_path="temp/rag_data/code_index.db"
                )

            # 初始化上下文管理器
            if enable_context_integration:
                self.context_manager = ContextManager()
                self.rag_context_manager = RAGContextManager(
                    context_manager=self.context_manager,
                    repo_path=workspace,
                    use_enhanced_retriever=use_enhanced_retriever,
                )
        else:
            self.rag_retriever = None
            self.context_manager = None
            self.rag_context_manager = None

        logger.info(
            f"RAG增强搜索工具初始化完成: workspace={workspace}, enhanced={use_enhanced_retriever}"
        )

    def _resolve_workspace_path(self, file_path: str) -> str:
        """解析工作区路径"""
        if not self.workspace:
            return file_path

        # 如果已经是绝对路径，检查是否在workspace下
        if Path(file_path).is_absolute():
            # 确保路径在workspace下
            try:
                resolved_path = Path(file_path).resolve()
                if self.workspace_path and self.workspace_path in resolved_path.parents:
                    return str(resolved_path)
                else:
                    # 路径不在workspace下，使用workspace
                    logger.warning(f"路径 {file_path} 不在workspace {self.workspace} 下，使用workspace")
                    return self.workspace
            except Exception:
                return self.workspace

        # 相对路径，与工作区拼接
        return str(Path(self.workspace) / file_path)

    def _is_path_in_workspace(self, file_path: str) -> bool:
        """检查文件路径是否在workspace下"""
        if not self.workspace_path:
            return True  # 没有workspace限制
            
        try:
            resolved_path = Path(file_path).resolve()
            # 检查路径是否在workspace下或是workspace本身
            return (
                resolved_path == self.workspace_path or 
                self.workspace_path in resolved_path.parents
            )
        except Exception:
            return False

    def _filter_rag_results_by_workspace(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤RAG结果，只保留workspace下的文件"""
        if not self.workspace_path:
            return results
            
        filtered_results = []
        for result in results:
            file_path = result.get('file_path', '')
            
            # 如果file_path是相对路径，转换为绝对路径
            if not os.path.isabs(file_path) and self.workspace:
                file_path = str(Path(self.workspace) / file_path)
            
            # 检查是否在workspace下
            if self._is_path_in_workspace(file_path):
                # 更新为相对于workspace的路径（如果可能）
                try:
                    if self.workspace_path:
                        abs_path = Path(file_path).resolve()
                        if self.workspace_path in abs_path.parents or abs_path == self.workspace_path:
                            relative_path = abs_path.relative_to(self.workspace_path)
                            result['file_path'] = str(relative_path)
                except Exception:
                    pass  # 保持原始路径
                    
                filtered_results.append(result)
            else:
                logger.debug(f"过滤掉workspace外的文件: {file_path}")
                
        return filtered_results

    async def _get_rag_results(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """获取RAG检索结果，确保只返回workspace下的文件"""
        if not self.rag_retriever:
            return []

        try:
            # 在查询中明确workspace限制
            workspace_query = f"{query} in {self.workspace}" if self.workspace else query
            
            # 如果使用增强检索器
            if hasattr(self.rag_retriever, "hybrid_search"):
                retrieval_results = await self.rag_retriever.hybrid_search(
                    workspace_query, n_results=max_results * 2  # 获取更多结果用于过滤
                )
                results = []
                for result in retrieval_results:
                    doc = result.document
                    file_path = getattr(doc, "id", "unknown")
                    results.append({
                        "file_path": file_path,
                        "title": doc.title,
                        "content": doc.chunks[0].content if doc.chunks else "",
                        "similarity": result.combined_score,
                        "source": "rag_enhanced",
                        "url": getattr(doc, "url", ""),
                    })
            else:
                # 使用基础检索器
                documents = self.rag_retriever.query_relevant_documents(workspace_query)
                results = []
                for doc in documents:
                    file_path = getattr(doc, "id", "unknown")
                    results.append({
                        "file_path": file_path,
                        "title": doc.title,
                        "content": doc.chunks[0].content if doc.chunks else "",
                        "similarity": doc.chunks[0].similarity if doc.chunks else 0.0,
                        "source": "rag_basic",
                        "url": getattr(doc, "url", ""),
                    })

            # 过滤结果，确保只返回workspace下的文件
            filtered_results = self._filter_rag_results_by_workspace(results)
            
            # 限制最终结果数量
            return filtered_results[:max_results]

        except Exception as e:
            logger.error(f"RAG检索失败: {e}")
            return []

    def _format_combined_results(
        self, traditional_results: str, rag_results: List[Dict[str, Any]], query: str
    ) -> str:
        """格式化合并搜索结果"""
        output_parts = []

        # 传统搜索结果
        output_parts.append("## 🔍 传统文件系统搜索结果")
        if self.workspace:
            output_parts.append(f"搜索范围: {self.workspace}")
        output_parts.append(traditional_results)

        # RAG检索结果
        if rag_results:
            output_parts.append(f"\n## 🧠 RAG智能检索结果 (workspace: {self.workspace})")
            output_parts.append(f"基于查询 '{query}' 的语义搜索结果 (共{len(rag_results)}个结果):\n")

            for i, result in enumerate(rag_results, 1):
                output_parts.append(f"### {i}. {result['title']} (相关性: {result['similarity']:.3f})")
                output_parts.append(f"**文件路径**: {result['file_path']}")
                if result.get('url'):
                    output_parts.append(f"**URL**: {result['url']}")
                output_parts.append(f"**来源**: {result['source']}")
                
                # 显示代码片段预览
                content = result['content']
                if len(content) > 200:
                    content = content[:200] + "..."
                output_parts.append(f"**代码预览**:")
                output_parts.append("```")
                output_parts.append(content)
                output_parts.append("```")
                output_parts.append("")
        else:
            output_parts.append(f"\n## 🧠 RAG智能检索结果 (workspace: {self.workspace})")
            output_parts.append("未找到workspace内相关的代码片段")

        return "\n".join(output_parts)

    async def enhanced_glob_search(
        self, pattern: str, path: Optional[str] = None, include_rag: bool = True
    ) -> str:
        """
        增强的glob文件搜索，结合RAG检索结果

        Args:
            pattern: 文件模式 (如 *.py, **/*.js)
            path: 搜索路径
            include_rag: 是否包含RAG检索结果

        Returns:
            合并的搜索结果
        """
        # 执行传统glob搜索
        if path:
            resolved_path = self._resolve_workspace_path(path)
        else:
            resolved_path = self.workspace

        traditional_results = glob_search_raw.func(pattern, resolved_path)

        # 如果启用RAG且有检索器
        if include_rag and self.rag_retriever:
            # 将glob模式转换为查询字符串
            query = f"files matching {pattern}"
            rag_results = await self._get_rag_results(query, max_results=3)

            # 可选：添加到上下文
            if self.rag_context_manager:
                try:
                    await self.rag_context_manager.add_rag_search_context(
                        query=query, max_results=3, context_type=ContextType.RAG_CODE
                    )
                except Exception as e:
                    logger.warning(f"添加RAG上下文失败: {e}")

            return self._format_combined_results(traditional_results, rag_results, query)
        else:
            return traditional_results

    async def enhanced_grep_search(
        self,
        pattern: str,
        path: Optional[str] = None,
        include: Optional[str] = None,
        include_rag: bool = True,
    ) -> str:
        """
        增强的grep内容搜索，结合RAG检索结果

        Args:
            pattern: 搜索模式
            path: 搜索路径
            include: 文件过滤模式
            include_rag: 是否包含RAG检索结果

        Returns:
            合并的搜索结果
        """
        # 执行传统grep搜索
        if path:
            resolved_path = self._resolve_workspace_path(path)
        else:
            resolved_path = self.workspace

        traditional_results = grep_search_raw.func(pattern, resolved_path, include)

        # 如果启用RAG且有检索器
        if include_rag and self.rag_retriever:
            # 使用grep模式作为RAG查询
            query = pattern
            rag_results = await self._get_rag_results(query, max_results=5)

            # 可选：添加到上下文
            if self.rag_context_manager:
                try:
                    await self.rag_context_manager.add_rag_search_context(
                        query=query, max_results=5, context_type=ContextType.RAG_CODE
                    )
                except Exception as e:
                    logger.warning(f"添加RAG上下文失败: {e}")

            return self._format_combined_results(traditional_results, rag_results, query)
        else:
            return traditional_results

    async def semantic_code_search(self, query: str, max_results: int = 5) -> str:
        """
        纯语义代码搜索，严格限制在workspace下

        Args:
            query: 语义查询
            max_results: 最大结果数

        Returns:
            格式化的搜索结果
        """
        if not self.rag_retriever:
            workspace_info = f" (workspace: {self.workspace})" if self.workspace else ""
            return f"RAG检索器未初始化，无法执行语义搜索{workspace_info}"

        rag_results = await self._get_rag_results(query, max_results)

        if not rag_results:
            workspace_info = f" (workspace: {self.workspace})" if self.workspace else ""
            return f"未找到与查询 '{query}' 相关的代码片段{workspace_info}"

        # 格式化结果
        output_parts = [f"## 🧠 语义代码搜索结果 (workspace: {self.workspace})"]
        output_parts.append(f"查询: {query}")
        output_parts.append(f"找到 {len(rag_results)} 个相关代码片段\n")

        for i, result in enumerate(rag_results, 1):
            output_parts.append(f"### {i}. {result['title']} (相关性: {result['similarity']:.3f})")
            output_parts.append(f"**文件路径**: {result['file_path']}")
            if result.get('url'):
                output_parts.append(f"**URL**: {result['url']}")
            output_parts.append(f"**来源**: {result['source']}")
            
            # 显示完整代码片段
            output_parts.append("**代码内容**:")
            output_parts.append("```")
            output_parts.append(result['content'])
            output_parts.append("```")
            output_parts.append("")

        # 可选：添加到上下文
        if self.rag_context_manager:
            try:
                await self.rag_context_manager.add_rag_search_context(
                    query=query, max_results=max_results, context_type=ContextType.RAG_SEMANTIC
                )
            except Exception as e:
                logger.warning(f"添加RAG上下文失败: {e}")

        return "\n".join(output_parts)


# 全局工具实例（延迟初始化）
_global_rag_search_tools: Optional[RAGEnhancedSearchTools] = None


def get_rag_enhanced_search_tools(workspace: Optional[str] = None) -> RAGEnhancedSearchTools:
    """获取RAG增强搜索工具实例"""
    global _global_rag_search_tools
    
    if _global_rag_search_tools is None or _global_rag_search_tools.workspace != workspace:
        _global_rag_search_tools = RAGEnhancedSearchTools(workspace=workspace)
    
    return _global_rag_search_tools


# 工具函数装饰器版本
@tool
async def rag_enhanced_glob_search(
    pattern: str, path: Optional[str] = None, workspace: Optional[str] = None
) -> str:
    """
    RAG增强的文件模式搜索，结合传统glob搜索和智能代码检索。

    Args:
        pattern: 文件模式 (如 *.py, **/*.js)
        path: 搜索路径
        workspace: 工作区路径

    Returns:
        合并的搜索结果，包含传统搜索和RAG检索结果
    """
    tools = get_rag_enhanced_search_tools(workspace)
    return await tools.enhanced_glob_search(pattern, path)


@tool
async def rag_enhanced_grep_search(
    pattern: str,
    path: Optional[str] = None,
    include: Optional[str] = None,
    workspace: Optional[str] = None,
) -> str:
    """
    RAG增强的内容搜索，结合传统grep搜索和智能代码检索。

    Args:
        pattern: 搜索模式/正则表达式
        path: 搜索路径
        include: 文件过滤模式
        workspace: 工作区路径

    Returns:
        合并的搜索结果，包含传统搜索和RAG检索结果
    """
    tools = get_rag_enhanced_search_tools(workspace)
    return await tools.enhanced_grep_search(pattern, path, include)


@tool
async def semantic_code_search(
    query: str, max_results: int = 5, workspace: Optional[str] = None
) -> str:
    """
    纯语义代码搜索，基于代码语义理解检索相关代码片段。

    Args:
        query: 语义查询 (如 "数据库连接", "用户认证", "文件上传")
        max_results: 最大结果数量
        workspace: 工作区路径

    Returns:
        格式化的语义搜索结果
    """
    tools = get_rag_enhanced_search_tools(workspace)
    return await tools.semantic_code_search(query, max_results) 