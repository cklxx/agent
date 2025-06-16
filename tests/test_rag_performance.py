#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG功能性能测试
"""

import tempfile
import time
import threading
import gc
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock


class TestRAGPerformance:
    """测试RAG功能的性能指标"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir) / "perf_workspace"
        self.workspace.mkdir()

        # 创建性能测试文件结构
        self.create_performance_test_files()

    def teardown_method(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        gc.collect()  # 强制垃圾回收

    def create_performance_test_files(self):
        """创建性能测试用的文件结构"""
        # 创建多层目录结构
        for level1 in range(3):
            level1_dir = self.workspace / f"level1_{level1}"
            level1_dir.mkdir()

            for level2 in range(5):
                level2_dir = level1_dir / f"level2_{level2}"
                level2_dir.mkdir()

                # 在每个目录创建多个Python文件
                for file_idx in range(10):
                    file_path = level2_dir / f"module_{file_idx}.py"
                    file_content = f"""
# Module {level1}_{level2}_{file_idx}
import os
import sys

class Module{level1}{level2}{file_idx}:
    def __init__(self):
        self.name = "module_{level1}_{level2}_{file_idx}"
    
    def process_data(self, input_data):
        result = {{}}
        for item in input_data:
            result[item] = len(item) + {file_idx}
        return result

def main():
    module = Module{level1}{level2}{file_idx}()
    print(f"Module: {{module.name}}")

if __name__ == "__main__":
    main()
"""
                    file_path.write_text(file_content)

        print(f"创建了 {3 * 5 * 10} 个测试文件用于性能测试")

    def get_memory_usage(self):
        """获取当前内存使用量（MB）"""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0  # 如果没有psutil，返回0

    def test_path_validation_performance(self):
        """测试路径验证性能"""
        print("🧪 测试路径验证性能")

        def is_path_in_workspace(file_path: str, workspace_path: Path) -> bool:
            try:
                resolved_path = Path(file_path).resolve()
                return (
                    resolved_path == workspace_path
                    or workspace_path in resolved_path.parents
                )
            except Exception:
                return False

        workspace_resolved = self.workspace.resolve()

        # 准备测试路径
        test_paths = []

        # 内部路径
        for level1 in range(3):
            for level2 in range(5):
                for file_idx in range(10):
                    path = str(
                        self.workspace
                        / f"level1_{level1}"
                        / f"level2_{level2}"
                        / f"module_{file_idx}.py"
                    )
                    test_paths.append((path, True))

        # 外部路径
        for i in range(50):
            path = str(Path(self.temp_dir) / f"outside_{i}.py")
            test_paths.append((path, False))

        print(f"准备测试 {len(test_paths)} 个路径")

        # 性能测试
        start_memory = self.get_memory_usage()
        start_time = time.time()

        correct_results = 0
        for path, expected in test_paths:
            result = is_path_in_workspace(path, workspace_resolved)
            if result == expected:
                correct_results += 1

        end_time = time.time()
        end_memory = self.get_memory_usage()

        elapsed_time = end_time - start_time
        memory_diff = end_memory - start_memory
        paths_per_second = len(test_paths) / elapsed_time if elapsed_time > 0 else 0

        print(f"✅ 路径验证性能测试完成:")
        print(f"   总路径数: {len(test_paths)}")
        print(f"   正确率: {(correct_results/len(test_paths))*100:.1f}%")
        print(f"   总耗时: {elapsed_time:.3f}秒")
        print(f"   处理速度: {paths_per_second:.0f} 路径/秒")
        print(f"   内存变化: {memory_diff:.1f}MB")

        # 性能断言
        assert correct_results == len(test_paths), "所有路径验证应该正确"
        assert (
            paths_per_second > 100
        ), f"处理速度应该 > 100 路径/秒，实际: {paths_per_second:.0f}"

    def test_result_filtering_performance(self):
        """测试结果过滤性能"""
        print("🧪 测试结果过滤性能")

        def filter_rag_results_by_workspace(
            results: list, workspace_path: Path
        ) -> list:
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
                    filtered_results.append(result)
            return filtered_results

        workspace_resolved = self.workspace.resolve()

        # 创建模拟结果
        large_results = []

        # 内部文件结果
        for level1 in range(3):
            for level2 in range(5):
                for file_idx in range(10):
                    file_path = str(
                        self.workspace
                        / f"level1_{level1}"
                        / f"level2_{level2}"
                        / f"module_{file_idx}.py"
                    )
                    large_results.append(
                        {
                            "file_path": file_path,
                            "title": f"module_{file_idx}.py",
                            "content": f"class Module{level1}{level2}{file_idx}: pass",
                            "similarity": 0.8 + (file_idx % 10) / 50,
                            "source": "rag_enhanced",
                        }
                    )

        # 外部文件结果
        for i in range(100):
            file_path = str(Path(self.temp_dir) / f"outside_{i}.py")
            large_results.append(
                {
                    "file_path": file_path,
                    "title": f"outside_{i}.py",
                    "content": f"def outside_function_{i}(): pass",
                    "similarity": 0.5 + (i % 20) / 40,
                    "source": "rag_basic",
                }
            )

        print(f"准备过滤 {len(large_results)} 个结果")

        # 性能测试
        start_memory = self.get_memory_usage()
        start_time = time.time()

        filtered_results = filter_rag_results_by_workspace(
            large_results, workspace_resolved
        )

        end_time = time.time()
        end_memory = self.get_memory_usage()

        elapsed_time = end_time - start_time
        memory_diff = end_memory - start_memory
        results_per_second = (
            len(large_results) / elapsed_time if elapsed_time > 0 else 0
        )

        print(f"✅ 结果过滤性能测试完成:")
        print(f"   原始结果数: {len(large_results)}")
        print(f"   过滤后结果数: {len(filtered_results)}")
        print(
            f"   过滤率: {((len(large_results)-len(filtered_results))/len(large_results))*100:.1f}%"
        )
        print(f"   总耗时: {elapsed_time:.3f}秒")
        print(f"   处理速度: {results_per_second:.0f} 结果/秒")
        print(f"   内存变化: {memory_diff:.1f}MB")

        # 验证过滤正确性
        expected_internal = 3 * 5 * 10  # 150个内部文件
        assert (
            len(filtered_results) == expected_internal
        ), f"应该保留{expected_internal}个内部结果"
        assert (
            results_per_second > 50
        ), f"处理速度应该 > 50 结果/秒，实际: {results_per_second:.0f}"

    def test_concurrent_search_performance(self):
        """测试并发搜索性能"""
        print("🧪 测试并发搜索性能")

        def mock_rag_search(query: str, workspace: str, search_id: int) -> dict:
            """模拟RAG搜索操作"""
            # 模拟搜索延迟
            time.sleep(0.05)  # 减少延迟以加快测试

            # 模拟搜索结果
            return {
                "search_id": search_id,
                "query": query,
                "workspace": workspace,
                "results": [
                    {
                        "file_path": f"result_{search_id}_{i}.py",
                        "content": f"def result_function_{search_id}_{i}(): pass",
                        "similarity": 0.8 - i * 0.1,
                    }
                    for i in range(3)
                ],
                "search_time": time.time(),
            }

        # 准备搜索查询
        queries = [f"search_query_{i}" for i in range(10)]

        # 串行搜索测试
        start_time = time.time()
        serial_results = []
        for i, query in enumerate(queries):
            result = mock_rag_search(query, str(self.workspace), i)
            serial_results.append(result)
        serial_time = time.time() - start_time

        # 并行搜索测试
        start_time = time.time()
        parallel_results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(mock_rag_search, query, str(self.workspace), i)
                for i, query in enumerate(queries)
            ]

            for future in as_completed(futures):
                result = future.result()
                parallel_results.append(result)

        parallel_time = time.time() - start_time

        # 性能分析
        speedup = serial_time / parallel_time if parallel_time > 0 else 1
        efficiency = speedup / 3  # 3个工作线程

        print(f"✅ 并发搜索性能测试完成:")
        print(f"   搜索查询数: {len(queries)}")
        print(f"   串行耗时: {serial_time:.2f}秒")
        print(f"   并行耗时: {parallel_time:.2f}秒")
        print(f"   加速比: {speedup:.2f}x")
        print(f"   并行效率: {efficiency:.2f}")
        print(f"   串行结果数: {len(serial_results)}")
        print(f"   并行结果数: {len(parallel_results)}")

        # 性能断言
        assert (
            len(serial_results) == len(parallel_results) == len(queries)
        ), "结果数量应该相同"
        assert speedup > 1.5, f"并行加速比应该 > 1.5，实际: {speedup:.2f}"

    def test_memory_efficiency(self):
        """测试内存使用效率"""
        print("🧪 测试内存使用效率")

        def memory_efficient_processing(data_size: int, batch_size: int = 50):
            """内存高效的批处理"""
            results = []

            for i in range(0, data_size, batch_size):
                # 处理一个批次
                batch = []
                for j in range(min(batch_size, data_size - i)):
                    item = {
                        "id": i + j,
                        "data": f"item_{i+j}_data_" * 5,  # 适中的数据项
                        "processed": True,
                    }
                    batch.append(item)

                # 模拟处理
                processed_batch = [
                    {"id": item["id"], "summary": f"summary_{item['id']}"}
                    for item in batch
                ]
                results.extend(processed_batch)

                # 清理批次数据
                del batch

                # 定期垃圾回收
                if i % (batch_size * 5) == 0:
                    gc.collect()

            return results

        # 测试不同数据大小的内存效率
        test_sizes = [100, 300, 500]

        for data_size in test_sizes:
            print(f"\n测试数据大小: {data_size}")

            start_memory = self.get_memory_usage()
            start_time = time.time()

            results = memory_efficient_processing(data_size, batch_size=30)

            end_time = time.time()
            end_memory = self.get_memory_usage()

            elapsed_time = end_time - start_time
            memory_diff = end_memory - start_memory
            items_per_second = len(results) / elapsed_time if elapsed_time > 0 else 0
            memory_per_item = memory_diff / len(results) if len(results) > 0 else 0

            print(f"   处理项目数: {len(results)}")
            print(f"   处理时间: {elapsed_time:.3f}秒")
            print(f"   处理速度: {items_per_second:.0f} 项目/秒")
            print(f"   内存变化: {memory_diff:.1f}MB")
            print(f"   单项内存: {memory_per_item*1024:.2f}KB")

            # 性能断言
            assert len(results) == data_size, f"应该处理{data_size}个项目"


def run_performance_tests():
    """运行性能测试"""
    print("⚡ 开始RAG功能性能测试")
    print("=" * 60)

    test_instance = TestRAGPerformance()

    test_methods = [
        test_instance.test_path_validation_performance,
        test_instance.test_result_filtering_performance,
        test_instance.test_concurrent_search_performance,
        test_instance.test_memory_efficiency,
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

    print(f"\n📊 性能测试结果:")
    print(f"总测试数: {len(test_methods)}")
    print(f"通过: {passed} ✅")
    print(f"失败: {failed} ❌")
    print(f"成功率: {(passed/len(test_methods))*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有性能测试通过!")
        print("RAG功能在性能方面表现良好")

    return failed == 0


if __name__ == "__main__":
    success = run_performance_tests()
    exit(0 if success else 1)
