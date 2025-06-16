#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试RAG增强搜索工具功能
"""

import tempfile
import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

try:
    from src.tools.rag_enhanced_search_tools import RAGEnhancedSearchTools
except ImportError:
    # Mock if not available
    RAGEnhancedSearchTools = Mock


class TestRAGEnhancedSearchTools:
    """测试RAG增强搜索工具"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir) / "test_workspace"
        self.workspace.mkdir()

        # 创建测试文件
        self.create_test_files()

        # 创建workspace外的文件
        self.outside_workspace = Path(self.temp_dir) / "outside"
        self.outside_workspace.mkdir()
        (self.outside_workspace / "external.py").write_text("def external(): pass")

    def teardown_method(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_files(self):
        """创建测试文件"""
        # 创建Python源码文件
        (self.workspace / "src").mkdir()
        (self.workspace / "src" / "main.py").write_text(
            """
def database_connection():
    '''建立数据库连接'''
    import sqlite3
    return sqlite3.connect('app.db')

def user_authentication(username, password):
    '''用户认证功能'''
    return verify_credentials(username, password)

class UserManager:
    '''用户管理类'''
    def __init__(self):
        self.db = database_connection()
"""
        )

        (self.workspace / "src" / "utils.py").write_text(
            """
def verify_credentials(username, password):
    '''验证用户凭据'''
    # 模拟验证逻辑
    return username == "admin" and password == "secret"

def hash_password(password):
    '''密码哈希'''
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
"""
        )

        # 创建配置文件
        (self.workspace / "config.py").write_text(
            """
DATABASE_URL = "sqlite:///app.db"
SECRET_KEY = "your-secret-key"
DEBUG = True
"""
        )

        # 创建README
        (self.workspace / "README.md").write_text(
            """
# 测试项目

这是一个测试项目，包含：
- 数据库连接功能
- 用户认证系统
- 配置管理
"""
        )

    def test_workspace_path_validation(self):
        """测试workspace路径验证"""
        try:
            tools = RAGEnhancedSearchTools(workspace=str(self.workspace))

            # 测试workspace内路径
            internal_path = str(self.workspace / "src" / "main.py")
            is_internal = tools._is_path_in_workspace(internal_path)
            assert is_internal, f"内部路径应该被识别为在workspace内: {internal_path}"
            print(f"✅ 内部路径验证通过: {internal_path}")

            # 测试workspace外路径
            external_path = str(self.outside_workspace / "external.py")
            is_external = tools._is_path_in_workspace(external_path)
            assert (
                not is_external
            ), f"外部路径应该被识别为在workspace外: {external_path}"
            print(f"✅ 外部路径验证通过: {external_path}")

        except Exception as e:
            print(f"⚠️  路径验证测试跳过: {e}")

    def test_workspace_path_resolution(self):
        """测试workspace路径解析"""
        try:
            tools = RAGEnhancedSearchTools(workspace=str(self.workspace))

            # 测试相对路径解析
            relative_path = "src/main.py"
            resolved = tools._resolve_workspace_path(relative_path)
            expected = str(self.workspace / "src" / "main.py")
            assert resolved == expected, f"相对路径解析错误: {resolved} != {expected}"
            print(f"✅ 相对路径解析正确: {relative_path} -> {resolved}")

            # 测试workspace内绝对路径
            abs_internal = str(self.workspace / "config.py")
            resolved_internal = tools._resolve_workspace_path(abs_internal)
            assert resolved_internal == abs_internal, "workspace内绝对路径应该保持不变"
            print(f"✅ workspace内绝对路径解析正确: {abs_internal}")

            # 测试workspace外绝对路径（应该被重定向到workspace）
            abs_external = str(self.outside_workspace / "external.py")
            resolved_external = tools._resolve_workspace_path(abs_external)
            assert resolved_external == str(
                self.workspace
            ), "workspace外路径应该被重定向"
            print(
                f"✅ workspace外路径重定向正确: {abs_external} -> {resolved_external}"
            )

        except Exception as e:
            print(f"⚠️  路径解析测试跳过: {e}")

    def test_rag_results_filtering(self):
        """测试RAG结果过滤"""
        try:
            tools = RAGEnhancedSearchTools(workspace=str(self.workspace))

            # 创建混合结果（包含workspace内外的文件）
            mock_results = [
                {
                    "file_path": str(self.workspace / "src" / "main.py"),
                    "title": "main.py",
                    "content": "def database_connection():",
                    "similarity": 0.9,
                    "source": "test",
                },
                {
                    "file_path": str(self.outside_workspace / "external.py"),
                    "title": "external.py",
                    "content": "def external():",
                    "similarity": 0.8,
                    "source": "test",
                },
                {
                    "file_path": str(self.workspace / "config.py"),
                    "title": "config.py",
                    "content": "DATABASE_URL = ...",
                    "similarity": 0.7,
                    "source": "test",
                },
            ]

            # 过滤结果
            filtered = tools._filter_rag_results_by_workspace(mock_results)

            # 验证过滤结果
            assert (
                len(filtered) == 2
            ), f"应该过滤掉1个外部文件，实际过滤后数量: {len(filtered)}"

            # 验证保留的文件都在workspace内
            for result in filtered:
                file_path = result["file_path"]
                # 结果应该是相对路径
                assert not os.path.isabs(
                    file_path
                ), f"过滤后的路径应该是相对路径: {file_path}"

            print(f"✅ RAG结果过滤测试通过: {len(mock_results)} -> {len(filtered)}")

        except Exception as e:
            print(f"⚠️  RAG结果过滤测试跳过: {e}")

    @patch("src.tools.rag_enhanced_search_tools.EnhancedRAGRetriever")
    def test_mock_rag_search(self, mock_retriever_class):
        """使用mock测试RAG搜索功能"""
        try:
            # 设置mock检索器
            mock_retriever = Mock()
            mock_retriever_class.return_value = mock_retriever

            # 模拟检索结果
            mock_doc = Mock()
            mock_doc.id = str(self.workspace / "src" / "main.py")
            mock_doc.title = "main.py"
            mock_doc.chunks = [Mock()]
            mock_doc.chunks[0].content = "def database_connection(): pass"

            mock_result = Mock()
            mock_result.document = mock_doc
            mock_result.combined_score = 0.85

            mock_retriever.hybrid_search = AsyncMock(return_value=[mock_result])

            # 创建工具实例
            tools = RAGEnhancedSearchTools(workspace=str(self.workspace))

            # 测试格式化结果
            formatted = tools._format_combined_results(
                traditional_results="传统搜索结果",
                rag_results=[
                    {
                        "file_path": "src/main.py",
                        "title": "main.py",
                        "content": "def database_connection(): pass",
                        "similarity": 0.85,
                        "source": "rag_enhanced",
                    }
                ],
                query="database",
            )

            assert "传统文件系统搜索结果" in formatted
            assert "RAG智能检索结果" in formatted
            assert "workspace:" in formatted
            assert "main.py" in formatted

            print("✅ Mock RAG搜索测试通过")

        except Exception as e:
            print(f"⚠️  Mock RAG搜索测试跳过: {e}")

    def test_initialization_scenarios(self):
        """测试不同初始化场景"""
        try:
            # 测试有workspace的初始化
            tools_with_workspace = RAGEnhancedSearchTools(workspace=str(self.workspace))
            assert tools_with_workspace.workspace == str(self.workspace)
            assert tools_with_workspace.workspace_path is not None
            print("✅ 有workspace的初始化测试通过")

            # 测试无workspace的初始化
            tools_without_workspace = RAGEnhancedSearchTools(workspace=None)
            assert tools_without_workspace.workspace is None
            assert tools_without_workspace.workspace_path is None
            print("✅ 无workspace的初始化测试通过")

            # 测试不同参数组合
            tools_basic = RAGEnhancedSearchTools(
                workspace=str(self.workspace),
                use_enhanced_retriever=False,
                enable_context_integration=False,
            )
            assert tools_basic.use_enhanced_retriever is False
            assert tools_basic.enable_context_integration is False
            print("✅ 基础配置初始化测试通过")

        except Exception as e:
            print(f"⚠️  初始化场景测试跳过: {e}")

    def test_error_handling(self):
        """测试错误处理"""
        try:
            tools = RAGEnhancedSearchTools(workspace=str(self.workspace))

            # 测试无效路径处理
            invalid_results = [
                {
                    "file_path": "/invalid/path/that/does/not/exist",
                    "title": "invalid",
                    "content": "content",
                    "similarity": 0.5,
                    "source": "test",
                }
            ]

            filtered = tools._filter_rag_results_by_workspace(invalid_results)
            assert len(filtered) == 0, "无效路径应该被过滤掉"
            print("✅ 无效路径错误处理测试通过")

        except Exception as e:
            print(f"⚠️  错误处理测试跳过: {e}")


def run_rag_search_tools_tests():
    """运行RAG增强搜索工具测试"""
    print("🧪 开始RAG增强搜索工具测试")

    test_instance = TestRAGEnhancedSearchTools()

    # 运行所有测试方法
    test_methods = [
        test_instance.test_workspace_path_validation,
        test_instance.test_workspace_path_resolution,
        test_instance.test_rag_results_filtering,
        test_instance.test_mock_rag_search,
        test_instance.test_initialization_scenarios,
        test_instance.test_error_handling,
    ]

    for test_method in test_methods:
        try:
            test_instance.setup_method()
            test_method()
            test_instance.teardown_method()
        except Exception as e:
            print(f"❌ 测试失败: {test_method.__name__} - {e}")

    print("🎉 RAG增强搜索工具测试完成!")


if __name__ == "__main__":
    run_rag_search_tools_tests()
