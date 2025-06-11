"""
代码检索器 - 基于代码索引器的RAG检索实现
"""

import os
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from .retriever import Retriever, Resource, Document, Chunk
from .code_indexer import CodeIndexer

logger = logging.getLogger(__name__)


class CodeResource(Resource):
    """代码资源"""

    def __init__(self, file_path: str, language: str, description: str = ""):
        super().__init__(
            uri=f"file://{file_path}",
            title=Path(file_path).name,
            description=description or f"{language} 代码文件",
        )
        self.file_path = file_path
        self.language = language


class CodeRetriever(Retriever):
    """代码检索器"""

    def __init__(self, repo_path: str, db_path: str = "temp/rag_data/code_index.db"):
        self.repo_path = repo_path
        self.indexer = CodeIndexer(repo_path, db_path)
        self._ensure_indexed()

    def _ensure_indexed(self):
        """确保仓库已被索引"""
        stats = self.indexer.get_statistics()
        if stats["total_files"] == 0:
            logger.info("Repository not indexed yet, starting indexing...")
            self.indexer.index_repository()
        else:
            logger.info(f"Index exists, contains {stats['total_files']} files")

    def list_resources(self, query: str | None = None) -> List[Resource]:
        """列出代码资源"""
        # 获取所有已索引的文件
        stats = self.indexer.get_statistics()
        resources = []

        # 根据语言类型创建资源
        for language, count in stats["files_by_language"].items():
            description = f"{language} 代码文件 ({count} 个文件)"
            resource = Resource(
                uri=f"language://{language}",
                title=f"{language.upper()} 代码",
                description=description,
            )
            resources.append(resource)

        # 如果有查询，可以返回更具体的文件资源
        if query:
            search_results = self.indexer.search_code(query, limit=20)
            file_paths = list(set(result["file_path"] for result in search_results))

            for file_path in file_paths:
                file_info = self.indexer.get_file_info(file_path)
                if file_info:
                    resource = CodeResource(
                        file_path=file_path, language=file_info["language"]
                    )
                    resources.append(resource)

        return resources

    def query_relevant_documents(
        self, query: str, resources: List[Resource] = []
    ) -> List[Document]:
        """查询相关的代码文档"""
        documents = []

        # 解析资源过滤条件
        language_filter = None
        specific_files = []

        for resource in resources:
            if resource.uri.startswith("language://"):
                language_filter = resource.uri.replace("language://", "")
            elif resource.uri.startswith("file://"):
                file_path = resource.uri.replace("file://", "")
                specific_files.append(file_path)

        # 执行搜索
        search_results = self.indexer.search_code(
            query=query, file_type=language_filter, limit=50
        )

        # 如果指定了特定文件，进行过滤
        if specific_files:
            search_results = [
                result
                for result in search_results
                if result["file_path"] in specific_files
            ]

        # 按文件分组结果
        files_dict = {}
        for result in search_results:
            file_path = result["file_path"]
            if file_path not in files_dict:
                files_dict[file_path] = {
                    "chunks": [],
                    "language": result["language"],
                    "file_info": self.indexer.get_file_info(file_path),
                }

            # 计算相关性得分
            similarity = self._calculate_similarity(query, result)

            chunk = Chunk(content=result["content"], similarity=similarity)
            files_dict[file_path]["chunks"].append(chunk)

        # 创建文档对象
        for file_path, file_data in files_dict.items():
            # 按相关性排序块
            file_data["chunks"].sort(key=lambda x: x.similarity, reverse=True)

            # 创建文档标题
            title = f"{Path(file_path).name} ({file_data['language']})"

            document = Document(
                id=file_path,
                url=f"file://{file_path}",
                title=title,
                chunks=file_data["chunks"][:10],  # 限制每个文件最多10个块
            )
            documents.append(document)

        # 按最高相关性排序文档
        documents.sort(
            key=lambda doc: (
                max(chunk.similarity for chunk in doc.chunks) if doc.chunks else 0
            ),
            reverse=True,
        )

        return documents[:10]  # 返回最相关的10个文档

    def _calculate_similarity(self, query: str, result: Dict[str, Any]) -> float:
        """计算相关性得分"""
        score = 0.0
        query_lower = query.lower()

        # 名称匹配得分最高
        if result["name"] and query_lower in result["name"].lower():
            score += 1.0

        # 文档字符串匹配
        if result["docstring"] and query_lower in result["docstring"].lower():
            score += 0.8

        # 内容匹配
        if query_lower in result["content"].lower():
            score += 0.6

        # 文件路径匹配
        if query_lower in result["file_path"].lower():
            score += 0.4

        # 根据块类型调整得分
        if result["chunk_type"] in ["function", "class", "method"]:
            score += 0.2

        return min(score, 1.0)  # 限制最高得分为1.0

    def search_by_function_name(self, function_name: str) -> List[Document]:
        """根据函数名搜索"""
        search_results = self.indexer.search_code(
            query=function_name, chunk_type="function", limit=20
        )

        documents = []
        for result in search_results:
            # 只返回名称完全匹配的结果
            if result["name"] and result["name"].lower() == function_name.lower():
                chunk = Chunk(content=result["content"], similarity=1.0)

                document = Document(
                    id=f"{result['file_path']}:{result['name']}",
                    url=f"file://{result['file_path']}#L{result['start_line']}",
                    title=f"{result['name']} - {Path(result['file_path']).name}",
                    chunks=[chunk],
                )
                documents.append(document)

        return documents

    def search_by_class_name(self, class_name: str) -> List[Document]:
        """根据类名搜索"""
        search_results = self.indexer.search_code(
            query=class_name, chunk_type="class", limit=20
        )

        documents = []
        for result in search_results:
            # 只返回名称完全匹配的结果
            if result["name"] and result["name"].lower() == class_name.lower():
                chunk = Chunk(content=result["content"], similarity=1.0)

                document = Document(
                    id=f"{result['file_path']}:{result['name']}",
                    url=f"file://{result['file_path']}#L{result['start_line']}",
                    title=f"{result['name']} - {Path(result['file_path']).name}",
                    chunks=[chunk],
                )
                documents.append(document)

        return documents

    def get_file_context(self, file_path: str) -> Optional[Document]:
        """获取完整的文件上下文"""
        file_info = self.indexer.get_file_info(file_path)
        if not file_info:
            return None

        # 获取文件的所有代码块
        search_results = self.indexer.search_code(
            query="", limit=1000  # 空查询获取所有块
        )

        file_chunks = [
            result for result in search_results if result["file_path"] == file_path
        ]

        chunks = []
        for result in file_chunks:
            chunk = Chunk(content=result["content"], similarity=1.0)
            chunks.append(chunk)

        # 按行号排序
        try:
            chunks.sort(
                key=lambda c: (
                    int(c.content.split("\n")[0].split(":")[0])
                    if ":" in c.content.split("\n")[0]
                    else 0
                )
            )
        except:
            pass  # 如果排序失败，保持原始顺序

        document = Document(
            id=file_path,
            url=f"file://{file_path}",
            title=Path(file_path).name,
            chunks=chunks,
        )

        return document

    def get_related_files(self, file_path: str) -> List[Document]:
        """获取相关文件"""
        related_paths = self.indexer.get_related_files(file_path)
        documents = []

        for path in related_paths:
            file_info = self.indexer.get_file_info(path)
            if file_info:
                # 获取文件的主要代码块
                search_results = self.indexer.search_code(query="", limit=5)

                file_chunks = [
                    result for result in search_results if result["file_path"] == path
                ]

                chunks = []
                for result in file_chunks[:3]:  # 只取前3个块
                    chunk = Chunk(content=result["content"], similarity=0.8)
                    chunks.append(chunk)

                document = Document(
                    id=path,
                    url=f"file://{path}",
                    title=f"{Path(path).name} ({file_info['language']})",
                    chunks=chunks,
                )
                documents.append(document)

        return documents

    def reindex_repository(self) -> Dict[str, int]:
        """重新索引仓库"""
        return self.indexer.index_repository()

    def get_indexer_statistics(self) -> Dict[str, Any]:
        """获取索引器统计信息"""
        return self.indexer.get_statistics()

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息 - 与get_indexer_statistics保持一致"""
        return self.indexer.get_statistics()
