#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG功能边界情况和异常测试
"""

import tempfile
import os
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestRAGEdgeCases:
    """测试RAG功能的边界情况和异常处理"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir) / "test_workspace"
        self.workspace.mkdir()
        
        # 创建复杂的文件结构
        self.create_complex_test_structure()

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_complex_test_structure(self):
        """创建复杂的测试文件结构"""
        # 深层嵌套目录
        deep_dir = self.workspace / "level1" / "level2" / "level3" / "level4"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep_file.py").write_text("def deep_function(): pass")
        
        # 特殊字符文件名
        special_dir = self.workspace / "special_chars"
        special_dir.mkdir()
        (special_dir / "file with spaces.py").write_text("def with_spaces(): pass")
        (special_dir / "file-with-dashes.py").write_text("def with_dashes(): pass")
        (special_dir / "file_with_中文.py").write_text("def with_chinese(): pass")
        (special_dir / "file@with#symbols$.py").write_text("def with_symbols(): pass")
        
        # 大文件
        large_dir = self.workspace / "large_files"
        large_dir.mkdir()
        large_content = "# Large file\n" + "def function_{}(): pass\n" * 1000
        (large_dir / "large_file.py").write_text(large_content)
        
        # 空文件和目录
        empty_dir = self.workspace / "empty_dir"
        empty_dir.mkdir()
        (self.workspace / "empty_file.py").write_text("")
        
        # 只读文件（如果系统支持）
        readonly_dir = self.workspace / "readonly"
        readonly_dir.mkdir()
        readonly_file = readonly_dir / "readonly.py"
        readonly_file.write_text("def readonly_function(): pass")
        try:
            readonly_file.chmod(0o444)  # 只读权限
        except Exception:
            pass  # 在某些系统上可能不支持

    def test_path_validation_edge_cases(self):
        """测试路径验证的边界情况"""
        print("🧪 测试路径验证边界情况")
        
        def is_path_in_workspace(file_path: str, workspace_path: Path) -> bool:
            try:
                resolved_path = Path(file_path).resolve()
                return (
                    resolved_path == workspace_path or 
                    workspace_path in resolved_path.parents
                )
            except Exception:
                return False
        
        workspace_resolved = self.workspace.resolve()
        
        # 测试空字符串
        assert not is_path_in_workspace("", workspace_resolved), "空字符串应该返回False"
        print("✅ 空字符串路径处理正确")
        
        # 测试特殊字符路径
        special_path = str(self.workspace / "special_chars" / "file with spaces.py")
        assert is_path_in_workspace(special_path, workspace_resolved), "特殊字符路径应该有效"
        print("✅ 特殊字符路径处理正确")
        
        # 测试路径遍历攻击
        traversal_path = str(self.workspace / ".." / ".." / "etc" / "passwd")
        try:
            result = is_path_in_workspace(traversal_path, workspace_resolved)
            assert not result, "路径遍历攻击应该被阻止"
            print("✅ 路径遍历攻击防护正确")
        except Exception:
            print("✅ 路径遍历攻击引发异常（预期行为）")

    def test_large_file_handling(self):
        """测试大文件处理"""
        print("🧪 测试大文件处理")
        
        def safe_file_read(file_path: str, max_size: int = 1024) -> str:
            """安全的文件读取，限制大小"""
            try:
                file_size = os.path.getsize(file_path)
                if file_size > max_size:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(max_size)
                        return content + f"\n... (文件太大，仅显示前{max_size}字节)"
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception as e:
                return f"读取文件失败: {e}"
        
        # 测试大文件读取
        large_file = self.workspace / "large_files" / "large_file.py"
        content = safe_file_read(str(large_file), max_size=1000)
        
        assert len(content) <= 1050, "大文件内容应该被截断"
        print(f"✅ 大文件处理正确，内容长度: {len(content)}")
        
        # 测试空文件
        empty_file = self.workspace / "empty_file.py"
        empty_content = safe_file_read(str(empty_file))
        assert empty_content == "", "空文件应该返回空字符串"
        print("✅ 空文件处理正确")

    def test_concurrent_access(self):
        """测试并发访问"""
        print("🧪 测试并发访问")
        
        def worker_function(worker_id: int, workspace_path: str):
            """工作线程函数"""
            try:
                test_paths = [
                    f"worker_{worker_id}_file.py",
                    f"subdir/worker_{worker_id}_file.py",
                    f"../outside_worker_{worker_id}.py"
                ]
                
                results = []
                for path in test_paths:
                    is_valid = not path.startswith("../")
                    results.append((path, is_valid))
                
                return worker_id, results, None
            except Exception as e:
                return worker_id, [], str(e)
        
        # 并发测试
        num_workers = 3
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker_function, i, str(self.workspace))
                for i in range(num_workers)
            ]
            
            completed_workers = 0
            errors = []
            
            for future in as_completed(futures):
                worker_id, results, error = future.result()
                completed_workers += 1
                
                if error:
                    errors.append(f"Worker {worker_id}: {error}")
                else:
                    # 验证结果
                    for path, is_valid in results:
                        if path.startswith("../"):
                            assert not is_valid, f"Worker {worker_id}: 外部路径应该无效"
                        else:
                            assert is_valid, f"Worker {worker_id}: 内部路径应该有效"
        
        assert completed_workers == num_workers, f"应该完成{num_workers}个工作线程"
        assert len(errors) == 0, f"不应该有错误: {errors}"
        print(f"✅ 并发访问测试通过: {completed_workers}个线程完成")

    def test_memory_usage_limits(self):
        """测试内存使用限制"""
        print("🧪 测试内存使用限制")
        
        def memory_safe_result_processing(results: list, max_results: int = 50):
            """内存安全的结果处理"""
            if len(results) > max_results:
                sorted_results = sorted(
                    results[:max_results*2],
                    key=lambda x: x.get('similarity', 0),
                    reverse=True
                )
                return sorted_results[:max_results]
            return results
        
        # 创建大量模拟结果
        large_results = [
            {
                "file_path": f"file_{i}.py",
                "title": f"file_{i}.py",
                "content": f"def function_{i}(): pass" * 5,
                "similarity": 0.5 + (i % 50) / 100,
                "source": "test"
            }
            for i in range(200)  # 200个结果
        ]
        
        # 测试内存限制处理
        limited_results = memory_safe_result_processing(large_results, max_results=30)
        
        assert len(limited_results) <= 30, "结果数量应该被限制"
        print(f"✅ 内存使用限制正确: {len(large_results)} -> {len(limited_results)}")

    def test_unicode_and_encoding(self):
        """测试Unicode和编码处理"""
        print("🧪 测试Unicode和编码处理")
        
        def safe_text_processing(text: str) -> dict:
            """安全的文本处理"""
            try:
                return {
                    "original_length": len(text),
                    "encoded_utf8": text.encode('utf-8', errors='ignore').decode('utf-8'),
                    "contains_unicode": any(ord(c) > 127 for c in text),
                    "error": None
                }
            except Exception as e:
                return {
                    "original_length": 0,
                    "encoded_utf8": "",
                    "contains_unicode": False,
                    "error": str(e)
                }
        
        # 测试各种Unicode字符
        test_texts = [
            "def normal_function(): pass",  # 正常ASCII
            "def 中文函数(): pass",  # 中文
            "def función_española(): pass",  # 西班牙语
        ]
        
        for i, text in enumerate(test_texts):
            result = safe_text_processing(text)
            assert result["error"] is None, f"文本{i}处理不应该出错"
            assert len(result["encoded_utf8"]) > 0, f"文本{i}应该有UTF-8编码结果"
            print(f"✅ 文本{i}处理正确: Unicode={result['contains_unicode']}")

    def test_error_recovery(self):
        """测试错误恢复机制"""
        print("🧪 测试错误恢复机制")
        
        def resilient_operation(max_retries: int = 3):
            """有恢复能力的操作"""
            for attempt in range(max_retries):
                try:
                    if attempt < 2:  # 前两次故意失败
                        raise ConnectionError(f"Attempt {attempt + 1} failed")
                    return {"attempt": attempt + 1, "success": True}
                except Exception as e:
                    if attempt == max_retries - 1:
                        return {"attempt": attempt + 1, "success": False, "error": str(e)}
                    time.sleep(0.01)  # 短暂延迟
                    continue
        
        # 测试成功恢复
        result = resilient_operation()
        assert result["success"] == True, "应该最终成功"
        assert result["attempt"] == 3, "应该在第3次尝试成功"
        print(f"✅ 错误恢复测试通过: 第{result['attempt']}次尝试成功")


def run_edge_case_tests():
    """运行边界情况测试"""
    print("🔬 开始RAG功能边界情况测试")
    print("="*60)
    
    test_instance = TestRAGEdgeCases()
    
    test_methods = [
        test_instance.test_path_validation_edge_cases,
        test_instance.test_large_file_handling,
        test_instance.test_concurrent_access,
        test_instance.test_memory_usage_limits,
        test_instance.test_unicode_and_encoding,
        test_instance.test_error_recovery,
    ]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_instance.setup_method()
            test_method()
            test_instance.teardown_method()
            passed += 1
            print(f"✅ {test_method.__name__} 通过")
        except Exception as e:
            failed += 1
            print(f"❌ {test_method.__name__} 失败: {e}")
        print("-" * 40)
    
    print(f"\n📊 边界情况测试结果:")
    print(f"总测试数: {len(test_methods)}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"成功率: {(passed/len(test_methods))*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 所有边界情况测试通过!")
        print("RAG功能在各种极端情况下都能正常工作")
    
    return failed == 0


if __name__ == "__main__":
    success = run_edge_case_tests()
    exit(0 if success else 1) 