#!/usr/bin/env python3
"""
RAG Context Scanner - 扫描和分析当前文件夹下的RAG相关内容
简化版本，专注于文件内容分析，避免复杂的模块导入
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict


class RAGContextScanner:
    """RAG Context内容扫描器"""

    def __init__(self, target_dir: str = "."):
        """
        初始化RAG Context扫描器

        Args:
            target_dir: 目标扫描目录
        """
        self.target_dir = Path(target_dir).resolve()
        self.scan_results = {}

        print(f"🔍 RAG Context扫描器启动")
        print(f"📁 扫描目录: {self.target_dir}")

    def scan_rag_files(self) -> Dict[str, Any]:
        """扫描包含RAG相关内容的文件"""
        rag_keywords = [
            "rag",
            "RAG",
            "context",
            "Context",
            "retriever",
            "enhanced",
            "semantic",
            "embedding",
            "vector",
            "search",
            "query",
            "ContextType",
            "RAG_CODE",
            "RAG_SEMANTIC",
            "rag_context",
        ]

        scan_results = {
            "files_scanned": 0,
            "rag_files": [],
            "file_analysis": {},
            "summary": {
                "total_rag_functions": 0,
                "total_rag_classes": 0,
                "total_context_types": 0,
                "total_test_methods": 0,
                "file_types": defaultdict(int),
            },
        }

        for root, dirs, files in os.walk(self.target_dir):
            # 跳过隐藏目录和缓存目录
            dirs[:] = [d for d in dirs if not d.startswith((".", "__pycache__"))]

            for file in files:
                if file.endswith((".py", ".md", ".txt", ".json", ".yaml", ".yml")):
                    scan_results["files_scanned"] += 1
                    file_path = Path(root) / file

                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # 检查是否包含RAG相关关键词
                        rag_keyword_matches = sum(
                            1 for keyword in rag_keywords if keyword in content
                        )

                        if rag_keyword_matches > 0:
                            scan_results["rag_files"].append(str(file_path))
                            analysis = self.analyze_file_content(file_path, content)
                            scan_results["file_analysis"][str(file_path)] = analysis

                            # 更新汇总统计
                            summary = scan_results["summary"]
                            summary["total_rag_functions"] += len(
                                analysis.get("rag_functions", [])
                            )
                            summary["total_rag_classes"] += len(
                                analysis.get("rag_classes", [])
                            )
                            summary["total_context_types"] += len(
                                analysis.get("rag_context_types", [])
                            )
                            summary["total_test_methods"] += len(
                                analysis.get("test_methods", [])
                            )
                            summary["file_types"][
                                analysis.get("file_type", "unknown")
                            ] += 1

                    except Exception as e:
                        print(f"⚠️ 读取文件失败 {file_path}: {e}")

        self.scan_results = scan_results
        return scan_results

    def analyze_file_content(self, file_path: Path, content: str) -> Dict[str, Any]:
        """分析文件内容中的RAG相关信息"""
        analysis = {
            "file_path": str(file_path),
            "file_type": file_path.suffix,
            "file_size": len(content),
            "line_count": len(content.split("\n")),
            "rag_context_types": [],
            "rag_functions": [],
            "rag_classes": [],
            "context_instances": [],
            "test_methods": [],
            "import_statements": [],
            "rag_keywords": [],
            "has_rag_manager": False,
            "has_context_manager": False,
        }

        # Python文件特殊处理
        if file_path.suffix == ".py":
            analysis.update(self.analyze_python_file(content))

        # 通用文本分析
        analysis.update(self.analyze_text_content(content))

        return analysis

    def analyze_python_file(self, content: str) -> Dict[str, Any]:
        """分析Python文件的AST结构"""
        analysis = {
            "rag_functions": [],
            "rag_classes": [],
            "context_instances": [],
            "imports": [],
        }

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # 分析导入语句
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if (
                            "rag" in alias.name.lower()
                            or "context" in alias.name.lower()
                        ):
                            analysis["imports"].append(
                                {
                                    "type": "import",
                                    "name": alias.name,
                                    "line": node.lineno,
                                }
                            )

                elif isinstance(node, ast.ImportFrom):
                    if node.module and (
                        "rag" in node.module.lower() or "context" in node.module.lower()
                    ):
                        for alias in node.names:
                            analysis["imports"].append(
                                {
                                    "type": "from_import",
                                    "module": node.module,
                                    "name": alias.name,
                                    "line": node.lineno,
                                }
                            )

                # 分析函数定义
                elif isinstance(node, ast.FunctionDef):
                    if any(
                        keyword in node.name.lower()
                        for keyword in ["rag", "context", "search", "retriev"]
                    ):
                        analysis["rag_functions"].append(
                            {
                                "name": node.name,
                                "line": node.lineno,
                                "args": [arg.arg for arg in node.args.args],
                                "is_async": isinstance(node, ast.AsyncFunctionDef),
                                "docstring": ast.get_docstring(node),
                                "is_test": node.name.startswith("test_"),
                            }
                        )

                # 分析类定义
                elif isinstance(node, ast.ClassDef):
                    if any(
                        keyword in node.name.lower()
                        for keyword in ["rag", "context", "retriev", "search"]
                    ):
                        analysis["rag_classes"].append(
                            {
                                "name": node.name,
                                "line": node.lineno,
                                "bases": [
                                    self._get_node_name(base) for base in node.bases
                                ],
                                "docstring": ast.get_docstring(node),
                                "methods": [
                                    method.name
                                    for method in node.body
                                    if isinstance(method, ast.FunctionDef)
                                ],
                            }
                        )

                # 分析变量赋值
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and any(
                            keyword in target.id.lower()
                            for keyword in ["context", "rag", "manager"]
                        ):
                            analysis["context_instances"].append(
                                {
                                    "name": target.id,
                                    "line": node.lineno,
                                    "type": (
                                        self._get_node_name(node.value)
                                        if hasattr(node.value, "id")
                                        else "unknown"
                                    ),
                                }
                            )

        except SyntaxError as e:
            analysis["parse_error"] = str(e)

        return analysis

    def analyze_text_content(self, content: str) -> Dict[str, Any]:
        """分析文本内容中的RAG相关信息"""
        analysis = {
            "rag_context_types": [],
            "test_methods": [],
            "import_statements": [],
            "rag_keywords": [],
            "has_rag_manager": False,
            "has_context_manager": False,
        }

        lines = content.split("\n")

        # RAG相关关键词
        rag_keywords = [
            "rag",
            "RAG",
            "context",
            "Context",
            "retriever",
            "enhanced",
            "semantic",
            "embedding",
            "vector",
            "search",
            "query",
        ]

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            line_stripped = line.strip()

            # 检测Context类型定义
            if "contexttype" in line_lower and "rag" in line_lower:
                analysis["rag_context_types"].append(
                    {"line": i, "content": line_stripped[:100]}  # 限制长度
                )

            # 检测导入语句
            if line_stripped.startswith(("import", "from")) and any(
                keyword in line_lower for keyword in ["rag", "context"]
            ):
                analysis["import_statements"].append(
                    {"line": i, "content": line_stripped}
                )

            # 检测测试方法
            if "def test" in line_lower and any(
                keyword in line_lower for keyword in ["rag", "context"]
            ):
                analysis["test_methods"].append(
                    {"line": i, "content": line_stripped[:80]}
                )

            # 检测特定类
            if "ragcontextmanager" in line_lower or "rag_context_manager" in line_lower:
                analysis["has_rag_manager"] = True

            if "contextmanager" in line_lower and "rag" not in line_lower:
                analysis["has_context_manager"] = True

            # 统计关键词出现
            for keyword in rag_keywords:
                if keyword in line:
                    analysis["rag_keywords"].append(
                        {
                            "keyword": keyword,
                            "line": i,
                            "context": (
                                line_stripped[:50] + "..."
                                if len(line_stripped) > 50
                                else line_stripped
                            ),
                        }
                    )

        return analysis

    def _get_node_name(self, node) -> str:
        """获取AST节点的名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_node_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_node_name(node.func)
        else:
            return str(type(node).__name__)

    def generate_context_report(self) -> str:
        """生成RAG Context分析报告"""
        if not self.scan_results:
            return "❌ 没有扫描结果，请先运行scan_rag_files()"

        results = self.scan_results
        report = []

        # 报告头部
        report.append("# RAG Context 扫描分析报告")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**扫描目录**: {self.target_dir}")
        report.append("")

        # 总体统计
        report.append("## 📊 总体统计")
        report.append(f"- 总扫描文件数: **{results['files_scanned']}**")
        report.append(f"- RAG相关文件数: **{len(results['rag_files'])}**")
        report.append(
            f"- RAG相关函数总数: **{results['summary']['total_rag_functions']}**"
        )
        report.append(f"- RAG相关类总数: **{results['summary']['total_rag_classes']}**")
        report.append(
            f"- Context类型定义: **{results['summary']['total_context_types']}**"
        )
        report.append(f"- 测试方法总数: **{results['summary']['total_test_methods']}**")
        report.append("")

        # 文件类型分布
        if results["summary"]["file_types"]:
            report.append("## 📁 文件类型分布")
            for file_type, count in results["summary"]["file_types"].items():
                report.append(f"- `{file_type}`: {count} 个文件")
            report.append("")

        # RAG文件列表
        report.append("## 📝 RAG相关文件列表")
        for file_path in results["rag_files"]:
            relative_path = Path(file_path).relative_to(self.target_dir)
            file_analysis = results["file_analysis"].get(file_path, {})

            # 文件基本信息
            size_kb = file_analysis.get("file_size", 0) // 1024
            line_count = file_analysis.get("line_count", 0)

            report.append(f"### `{relative_path}`")
            report.append(f"- 文件大小: {size_kb}KB, 行数: {line_count}")

            # RAG功能统计
            rag_functions = len(file_analysis.get("rag_functions", []))
            rag_classes = len(file_analysis.get("rag_classes", []))
            test_methods = len(file_analysis.get("test_methods", []))

            if rag_functions > 0 or rag_classes > 0 or test_methods > 0:
                report.append(
                    f"- RAG功能: {rag_functions} 个函数, {rag_classes} 个类, {test_methods} 个测试"
                )

            # 特殊标记
            if file_analysis.get("has_rag_manager"):
                report.append("- ✅ 包含RAG Manager")
            if file_analysis.get("has_context_manager"):
                report.append("- ✅ 包含Context Manager")

            report.append("")

        # 详细功能分析
        report.append("## 🔍 详细功能分析")

        for file_path, analysis in results["file_analysis"].items():
            relative_path = Path(file_path).relative_to(self.target_dir)

            if not (analysis.get("rag_functions") or analysis.get("rag_classes")):
                continue

            report.append(f"### {relative_path}")

            # RAG函数
            if analysis.get("rag_functions"):
                report.append("**RAG相关函数:**")
                for func in analysis["rag_functions"][:10]:  # 最多显示10个
                    async_mark = "async " if func.get("is_async") else ""
                    test_mark = " [测试]" if func.get("is_test") else ""
                    report.append(
                        f"- `{async_mark}{func['name']}()` (第{func['line']}行){test_mark}"
                    )

            # RAG类
            if analysis.get("rag_classes"):
                report.append("**RAG相关类:**")
                for cls in analysis["rag_classes"]:
                    method_count = len(cls.get("methods", []))
                    report.append(
                        f"- `{cls['name']}` (第{cls['line']}行, {method_count} 个方法)"
                    )

            # Context实例
            if analysis.get("context_instances"):
                report.append("**Context实例:**")
                for instance in analysis["context_instances"][:5]:
                    report.append(f"- `{instance['name']}` (第{instance['line']}行)")

            report.append("")

        # Context类型分析
        context_types_found = []
        for analysis in results["file_analysis"].values():
            context_types_found.extend(analysis.get("rag_context_types", []))

        if context_types_found:
            report.append("## 🏷️ Context类型定义")
            unique_types = {}
            for ct in context_types_found:
                key = ct["content"][:50]
                if key not in unique_types:
                    unique_types[key] = ct

            for ct in list(unique_types.values())[:10]:
                report.append(f"- 第{ct['line']}行: `{ct['content']}`")
            report.append("")

        # 总结评估
        report.append("## 📋 总结评估")

        total_files = len(results["rag_files"])
        has_managers = sum(
            1
            for analysis in results["file_analysis"].values()
            if analysis.get("has_rag_manager") or analysis.get("has_context_manager")
        )

        if total_files == 0:
            report.append("- 状态: ❌ 未发现RAG相关文件")
        elif total_files >= 10 and has_managers >= 2:
            report.append("- 状态: 🏆 RAG集成非常完善")
        elif total_files >= 5 and has_managers >= 1:
            report.append("- 状态: 🥇 RAG集成良好")
        elif total_files >= 2:
            report.append("- 状态: 🥈 RAG集成基础完备")
        else:
            report.append("- 状态: 🥉 RAG集成刚起步")

        report.append(
            f"- RAG文件覆盖率: {(total_files / max(results['files_scanned'], 1) * 100):.1f}%"
        )

        return "\n".join(report)

    def save_report(self, filename: str = "rag_context_scan_report.md") -> str:
        """保存报告到文件"""
        report = self.generate_context_report()
        report_path = self.target_dir / filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        return str(report_path)

    def run_scan(self) -> str:
        """运行完整的扫描和报告生成"""
        print("🚀 开始RAG Context扫描...")

        # 扫描文件
        print("📁 扫描RAG相关文件...")
        results = self.scan_rag_files()
        print(f"   发现 {len(results['rag_files'])} 个RAG相关文件")

        # 生成报告
        print("📋 生成扫描报告...")
        report = self.generate_context_report()

        # 保存报告
        report_path = self.save_report()
        print(f"✅ 扫描完成！报告已保存到: {report_path}")

        return report


def main():
    """主函数"""
    print("🔍 RAG Context Scanner")
    print("=" * 40)

    # 创建扫描器实例
    scanner = RAGContextScanner(target_dir=".")

    # 运行扫描
    report = scanner.run_scan()

    # 显示报告预览
    print("\n📋 扫描报告预览:")
    print("=" * 40)

    lines = report.split("\n")
    preview_lines = lines[:30]  # 显示前30行

    for line in preview_lines:
        print(line)

    if len(lines) > 30:
        print(f"\n... 还有 {len(lines) - 30} 行内容，请查看完整报告文件")

    return 0


if __name__ == "__main__":
    exit(main())
