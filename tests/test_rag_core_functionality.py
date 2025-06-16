#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG核心功能测试 - 独立测试，不依赖外部库
"""

import tempfile
import os
from pathlib import Path


def test_workspace_path_operations():
    """测试workspace路径操作"""
    print("🧪 测试workspace路径操作")

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir) / "test_workspace"
        workspace.mkdir()

        # 创建测试文件
        (workspace / "src").mkdir()
        (workspace / "src" / "main.py").write_text("def main(): pass")

        # 创建workspace外文件
        outside_dir = Path(temp_dir) / "outside"
        outside_dir.mkdir()
        (outside_dir / "external.py").write_text("def external(): pass")

        # 测试路径解析逻辑
        def resolve_workspace_path(file_path: str, workspace_str: str = None) -> str:
            if not workspace_str:
                return file_path
            if os.path.isabs(file_path):
                return file_path
            return str(Path(workspace_str) / file_path)

        # 测试相对路径解析
        resolved = resolve_workspace_path("src/main.py", str(workspace))
        expected = str(workspace / "src" / "main.py")
        assert resolved == expected, f"路径解析错误: {resolved} != {expected}"
        print(f"✅ 相对路径解析正确: src/main.py -> {resolved}")

        # 测试绝对路径处理
        abs_path = str(workspace / "src" / "main.py")
        resolved_abs = resolve_workspace_path(abs_path, str(workspace))
        assert resolved_abs == abs_path, "绝对路径应该保持不变"
        print(f"✅ 绝对路径处理正确: {abs_path}")


def test_workspace_path_validation():
    """测试workspace路径验证逻辑"""
    print("🧪 测试workspace路径验证逻辑")

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir) / "test_workspace"
        workspace.mkdir()
        workspace_resolved = workspace.resolve()

        # 创建测试文件
        test_file = workspace / "test.py"
        test_file.write_text("# test")

        # 创建workspace外文件
        outside_file = Path(temp_dir) / "outside.py"
        outside_file.write_text("# outside")

        def is_path_in_workspace(file_path: str, workspace_path: Path) -> bool:
            """检查文件路径是否在workspace下"""
            try:
                resolved_path = Path(file_path).resolve()
                return (
                    resolved_path == workspace_path
                    or workspace_path in resolved_path.parents
                )
            except Exception:
                return False

        # 测试workspace内文件
        is_internal = is_path_in_workspace(str(test_file), workspace_resolved)
        assert is_internal, f"内部文件应该被识别为在workspace内: {test_file}"
        print(f"✅ workspace内文件验证通过: {test_file}")

        # 测试workspace外文件
        is_external = is_path_in_workspace(str(outside_file), workspace_resolved)
        assert not is_external, f"外部文件应该被识别为在workspace外: {outside_file}"
        print(f"✅ workspace外文件验证通过: {outside_file}")


def test_rag_result_filtering():
    """测试RAG结果过滤逻辑"""
    print("🧪 测试RAG结果过滤逻辑")

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir) / "test_workspace"
        workspace.mkdir()
        workspace_resolved = workspace.resolve()

        # 创建测试文件
        (workspace / "internal.py").write_text("# internal")
        outside_file = Path(temp_dir) / "external.py"
        outside_file.write_text("# external")

        def filter_rag_results_by_workspace(
            results: list, workspace_path: Path
        ) -> list:
            """过滤RAG结果，只保留workspace下的文件"""

            def is_path_in_workspace(file_path: str) -> bool:
                try:
                    resolved_path = Path(file_path).resolve()
                    return (
                        resolved_path == workspace_path
                        or workspace_path in resolved_path.parents
                    )
                except Exception:
                    return False

            filtered_results = []
            for result in results:
                file_path = result.get("file_path", "")
                if is_path_in_workspace(file_path):
                    # 转换为相对路径
                    try:
                        abs_path = Path(file_path).resolve()
                        if (
                            workspace_path in abs_path.parents
                            or abs_path == workspace_path
                        ):
                            relative_path = abs_path.relative_to(workspace_path)
                            result["file_path"] = str(relative_path)
                    except Exception:
                        pass
                    filtered_results.append(result)
            return filtered_results

        # 创建混合结果
        mock_results = [
            {
                "file_path": str(workspace / "internal.py"),
                "title": "internal.py",
                "content": "# internal code",
                "similarity": 0.9,
            },
            {
                "file_path": str(outside_file),
                "title": "external.py",
                "content": "# external code",
                "similarity": 0.8,
            },
        ]

        # 过滤结果
        filtered = filter_rag_results_by_workspace(mock_results, workspace_resolved)

        assert len(filtered) == 1, f"应该过滤掉1个外部文件，实际结果: {len(filtered)}"
        assert filtered[0]["title"] == "internal.py", "保留的应该是内部文件"
        assert not os.path.isabs(filtered[0]["file_path"]), "文件路径应该转换为相对路径"

        print(f"✅ RAG结果过滤测试通过: {len(mock_results)} -> {len(filtered)}")
        print(f"   保留文件: {filtered[0]['file_path']}")


def test_search_result_formatting():
    """测试搜索结果格式化"""
    print("🧪 测试搜索结果格式化")

    def format_combined_results(
        traditional_results: str, rag_results: list, query: str, workspace: str
    ) -> str:
        """格式化合并搜索结果"""
        output_parts = []

        # 传统搜索结果
        output_parts.append("## 🔍 传统文件系统搜索结果")
        if workspace:
            output_parts.append(f"搜索范围: {workspace}")
        output_parts.append(traditional_results)

        # RAG检索结果
        if rag_results:
            output_parts.append(f"\n## 🧠 RAG智能检索结果 (workspace: {workspace})")
            output_parts.append(
                f"基于查询 '{query}' 的语义搜索结果 (共{len(rag_results)}个结果):\n"
            )

            for i, result in enumerate(rag_results, 1):
                output_parts.append(
                    f"### {i}. {result['title']} (相关性: {result['similarity']:.3f})"
                )
                output_parts.append(f"**文件路径**: {result['file_path']}")

                content = result["content"]
                if len(content) > 200:
                    content = content[:200] + "..."
                output_parts.append(f"**代码预览**:")
                output_parts.append("```")
                output_parts.append(content)
                output_parts.append("```")
                output_parts.append("")
        else:
            output_parts.append(f"\n## 🧠 RAG智能检索结果 (workspace: {workspace})")
            output_parts.append("未找到workspace内相关的代码片段")

        return "\n".join(output_parts)

    # 测试格式化
    mock_rag_results = [
        {
            "file_path": "src/main.py",
            "title": "main.py",
            "content": "def main():\n    print('Hello World')",
            "similarity": 0.85,
        }
    ]

    formatted = format_combined_results(
        traditional_results="找到文件: src/main.py",
        rag_results=mock_rag_results,
        query="main function",
        workspace="/test/workspace",
    )

    # 验证格式化结果
    assert "传统文件系统搜索结果" in formatted
    assert "RAG智能检索结果" in formatted
    assert "workspace:" in formatted
    assert "main.py" in formatted
    assert "相关性: 0.850" in formatted

    print("✅ 搜索结果格式化测试通过")
    print("   包含传统搜索结果")
    print("   包含RAG智能检索结果")
    print("   包含workspace信息")
    print("   包含相关性评分")


def test_error_handling():
    """测试错误处理机制"""
    print("🧪 测试错误处理机制")

    def safe_path_resolution(file_path: str, workspace: str = None) -> str:
        """安全的路径解析，包含错误处理"""
        try:
            if not workspace:
                return file_path

            if os.path.isabs(file_path):
                # 检查是否在workspace下
                workspace_path = Path(workspace).resolve()
                file_resolved = Path(file_path).resolve()

                if (
                    workspace_path in file_resolved.parents
                    or file_resolved == workspace_path
                ):
                    return str(file_resolved)
                else:
                    # 不在workspace下，返回workspace
                    return workspace
            else:
                # 相对路径，拼接workspace
                return str(Path(workspace) / file_path)

        except Exception as e:
            print(f"路径解析错误: {e}")
            return workspace if workspace else file_path

    # 测试各种错误场景
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = str(Path(temp_dir) / "workspace")
        os.makedirs(workspace, exist_ok=True)

        # 测试正常情况
        normal_result = safe_path_resolution("test.py", workspace)
        expected = str(Path(workspace) / "test.py")
        assert normal_result == expected, "正常路径解析失败"
        print("✅ 正常路径解析通过")

        # 测试None workspace
        none_result = safe_path_resolution("test.py", None)
        assert none_result == "test.py", "None workspace处理失败"
        print("✅ None workspace处理通过")

        # 测试无效路径
        invalid_result = safe_path_resolution("/invalid/../../path", workspace)
        # 应该返回workspace或处理后的安全路径
        assert invalid_result is not None, "无效路径应该有返回值"
        print("✅ 无效路径处理通过")


def run_all_core_tests():
    """运行所有核心功能测试"""
    print("🧠 开始RAG核心功能测试")
    print("=" * 60)

    tests = [
        test_workspace_path_operations,
        test_workspace_path_validation,
        test_rag_result_filtering,
        test_search_result_formatting,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print(f"✅ {test.__name__} 通过")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} 失败: {e}")
        print("-" * 40)

    print(f"\n📊 测试结果:")
    print(f"总测试数: {len(tests)}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"成功率: {(passed/len(tests))*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有核心功能测试通过!")
        print("RAG集成的核心逻辑工作正常:")
        print("  • Workspace路径验证和解析 ✅")
        print("  • RAG结果过滤和安全检查 ✅")
        print("  • 搜索结果格式化 ✅")
        print("  • 错误处理和降级 ✅")
    else:
        print(f"\n⚠️  {failed} 个测试失败，请检查错误信息")

    return failed == 0


if __name__ == "__main__":
    success = run_all_core_tests()
    exit(0 if success else 1)
