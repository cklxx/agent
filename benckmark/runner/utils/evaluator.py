#!/usr/bin/env python3
"""
代码评估器 - 对AI生成的代码进行多维度评分

功能:
- 功能完整性评估
- 代码质量分析
- 性能测试
- 安全性检查
- 最佳实践验证
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from .sandbox_manager import SandboxManager


@dataclass
class EvaluationResult:
    """评估结果数据类"""

    task_id: str
    total_score: float
    max_score: float
    dimension_scores: Dict[str, float]
    detailed_feedback: Dict[str, Any]
    execution_time: float
    success: bool
    error_message: Optional[str] = None


class CodeEvaluator:
    """代码评估器主类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化评估器"""
        self.config = config or self._get_default_config()
        self.sandbox = SandboxManager(self.config.get("sandbox", {}))

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认评估配置"""
        return {
            "weights": {
                "functionality": 0.4,
                "code_quality": 0.25,
                "performance": 0.15,
                "security": 0.1,
                "documentation": 0.1,
            },
            "thresholds": {
                "min_functionality_score": 60,
                "min_code_quality_score": 50,
                "max_execution_time": 30,
                "max_memory_mb": 500,
            },
            "sandbox": {
                "max_execution_time": 30,
                "max_memory_mb": 500,
                "blocked_imports": ["os.system", "subprocess", "exec", "eval"],
            },
        }

    async def evaluate_code(
        self, task_config: Dict[str, Any], generated_code: str
    ) -> EvaluationResult:
        """评估生成的代码"""
        start_time = time.time()

        try:
            # 提取任务信息
            task_id = task_config["id"]
            level = task_config["level"]
            evaluation_criteria = task_config["evaluation_criteria"]
            test_cases = task_config["test_cases"]

            # 初始化评估结果
            dimension_scores = {}
            detailed_feedback = {}

            # 1. 功能完整性评估
            functionality_result = await self._evaluate_functionality(
                generated_code, test_cases, task_config
            )
            dimension_scores["functionality"] = functionality_result["score"]
            detailed_feedback["functionality"] = functionality_result

            # 2. 代码质量评估
            quality_result = self._evaluate_code_quality(generated_code, task_config)
            dimension_scores["code_quality"] = quality_result["score"]
            detailed_feedback["code_quality"] = quality_result

            # 3. 性能评估
            performance_result = await self._evaluate_performance(
                generated_code, task_config
            )
            dimension_scores["performance"] = performance_result["score"]
            detailed_feedback["performance"] = performance_result

            # 4. 安全性评估
            security_result = self._evaluate_security(generated_code, task_config)
            dimension_scores["security"] = security_result["score"]
            detailed_feedback["security"] = security_result

            # 5. 文档质量评估
            documentation_result = self._evaluate_documentation(
                generated_code, task_config
            )
            dimension_scores["documentation"] = documentation_result["score"]
            detailed_feedback["documentation"] = documentation_result

            # 计算总分
            total_score = self._calculate_total_score(
                dimension_scores, evaluation_criteria
            )

            execution_time = time.time() - start_time

            return EvaluationResult(
                task_id=task_id,
                total_score=total_score,
                max_score=100.0,
                dimension_scores=dimension_scores,
                detailed_feedback=detailed_feedback,
                execution_time=execution_time,
                success=True,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return EvaluationResult(
                task_id=task_config.get("id", "unknown"),
                total_score=0.0,
                max_score=100.0,
                dimension_scores={},
                detailed_feedback={"error": str(e)},
                execution_time=execution_time,
                success=False,
                error_message=str(e),
            )

    async def _evaluate_functionality(
        self, code: str, test_cases: List[Dict[str, Any]], task_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估功能完整性"""
        result = {
            "score": 0.0,
            "passed_tests": 0,
            "total_tests": len(test_cases),
            "test_details": [],
            "issues": [],
        }

        if not test_cases:
            result["score"] = 50.0  # 没有测试用例时给予基础分
            result["issues"].append("没有提供测试用例")
            return result

        try:
            # 提取函数名（如果有）
            function_name = self._extract_function_name(code, task_config)

            if function_name:
                # 运行功能测试
                test_results = self.sandbox.run_functional_tests(
                    code, test_cases, function_name
                )

                result["passed_tests"] = test_results["passed"]
                result["total_tests"] = test_results["total"]
                result["test_details"] = test_results["details"]

                # 计算功能分数
                if test_results["total"] > 0:
                    pass_rate = test_results["passed"] / test_results["total"]
                    result["score"] = pass_rate * 100
                else:
                    result["score"] = 0.0
            else:
                # 如果无法识别函数，尝试直接执行代码
                exec_result = await self.sandbox.execute_python_code(code)
                if exec_result["success"]:
                    result["score"] = 70.0  # 代码能够执行给予基础分
                else:
                    result["score"] = 0.0
                    result["issues"].append(f"代码执行失败: {exec_result['stderr']}")

        except Exception as e:
            result["issues"].append(f"功能测试执行失败: {str(e)}")
            result["score"] = 0.0

        return result

    def _evaluate_code_quality(
        self, code: str, task_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估代码质量"""
        result = {
            "score": 0.0,
            "syntax_score": 0.0,
            "structure_score": 0.0,
            "style_score": 0.0,
            "complexity_score": 0.0,
            "issues": [],
        }

        try:
            # 使用沙箱进行代码质量分析
            quality_metrics = self.sandbox.analyze_code_quality(code)

            result["syntax_score"] = quality_metrics.get("syntax_score", 0)
            result["complexity_score"] = quality_metrics.get("complexity_score", 0)
            result["style_score"] = quality_metrics.get("style_score", 0)
            result["structure_score"] = quality_metrics.get("documentation_score", 0)

            # 计算综合代码质量分数
            scores = [
                result["syntax_score"],
                result["structure_score"],
                result["style_score"],
                result["complexity_score"],
            ]

            result["score"] = sum(scores) / len(scores)
            result["issues"] = quality_metrics.get("issues", [])

        except Exception as e:
            result["issues"].append(f"代码质量分析失败: {str(e)}")
            result["score"] = 0.0

        return result

    async def _evaluate_performance(
        self, code: str, task_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估性能"""
        result = {
            "score": 0.0,
            "execution_time": 0.0,
            "memory_usage": 0.0,
            "efficiency_score": 0.0,
            "issues": [],
        }

        try:
            # 执行性能测试
            start_time = time.time()
            exec_result = await self.sandbox.execute_python_code(code)
            execution_time = time.time() - start_time

            result["execution_time"] = execution_time

            # 根据难度级别设置性能标准
            level = task_config.get("level", "beginner")
            performance_thresholds = self._get_performance_thresholds(level)

            # 评估执行时间
            max_time = performance_thresholds["max_execution_time"]
            if execution_time <= max_time * 0.5:
                time_score = 100
            elif execution_time <= max_time:
                time_score = 100 - (execution_time / max_time) * 50
            else:
                time_score = 0
                result["issues"].append(
                    f"执行时间超出限制: {execution_time:.2f}s > {max_time}s"
                )

            result["efficiency_score"] = time_score
            result["score"] = time_score

            if not exec_result["success"]:
                result["score"] = 0.0
                result["issues"].append("代码执行失败")

        except Exception as e:
            result["issues"].append(f"性能测试失败: {str(e)}")
            result["score"] = 0.0

        return result

    def _evaluate_security(
        self, code: str, task_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估安全性"""
        result = {
            "score": 100.0,  # 从满分开始，发现问题扣分
            "security_issues": [],
            "vulnerability_count": 0,
        }

        try:
            # 检查安全性问题
            security_issues = self.sandbox.check_code_security(code)

            result["security_issues"] = security_issues
            result["vulnerability_count"] = len(security_issues)

            # 根据发现的安全问题扣分
            for issue in security_issues:
                if "禁止" in issue or "危险" in issue:
                    result["score"] -= 30  # 严重安全问题
                else:
                    result["score"] -= 10  # 一般安全问题

            result["score"] = max(0, result["score"])

        except Exception as e:
            result["security_issues"].append(f"安全检查失败: {str(e)}")
            result["score"] = 50.0  # 无法检查时给予中等分数

        return result

    def _evaluate_documentation(
        self, code: str, task_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估文档质量"""
        result = {
            "score": 0.0,
            "has_docstrings": False,
            "has_comments": False,
            "comment_ratio": 0.0,
            "readability_score": 0.0,
        }

        try:
            lines = code.split("\n")
            total_lines = len([line for line in lines if line.strip()])
            comment_lines = len(
                [line for line in lines if line.strip().startswith("#")]
            )

            # 检查文档字符串
            has_docstrings = '"""' in code or "'''" in code
            result["has_docstrings"] = has_docstrings

            # 检查注释
            has_comments = comment_lines > 0
            result["has_comments"] = has_comments

            # 计算注释比例
            comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
            result["comment_ratio"] = comment_ratio

            # 计算文档分数
            doc_score = 0
            if has_docstrings:
                doc_score += 50
            if has_comments:
                doc_score += 30
            if comment_ratio > 0.1:  # 注释比例超过10%
                doc_score += 20

            result["score"] = min(100, doc_score)
            result["readability_score"] = doc_score

        except Exception as e:
            result["score"] = 0.0

        return result

    def _extract_function_name(
        self, code: str, task_config: Dict[str, Any]
    ) -> Optional[str]:
        """从代码中提取主要函数名"""
        try:
            import ast

            tree = ast.parse(code)

            # 优先查找任务配置中指定的函数名
            input_spec = task_config.get("input_spec", {})
            if "function_name" in input_spec:
                return input_spec["function_name"]

            # 查找第一个函数定义
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name

            return None

        except Exception:
            return None

    def _get_performance_thresholds(self, level: str) -> Dict[str, float]:
        """根据难度级别获取性能阈值"""
        thresholds = {
            "beginner": {"max_execution_time": 10, "max_memory_mb": 100},
            "elementary": {"max_execution_time": 30, "max_memory_mb": 200},
            "intermediate": {"max_execution_time": 60, "max_memory_mb": 500},
            "advanced": {"max_execution_time": 120, "max_memory_mb": 1000},
            "expert": {"max_execution_time": 300, "max_memory_mb": 2000},
            "master": {"max_execution_time": 600, "max_memory_mb": 4000},
        }

        return thresholds.get(level, thresholds["beginner"])

    def _calculate_total_score(
        self, dimension_scores: Dict[str, float], evaluation_criteria: Dict[str, int]
    ) -> float:
        """计算总分"""
        total_score = 0.0
        total_weight = 0

        for dimension, weight in evaluation_criteria.items():
            if dimension in dimension_scores:
                score = dimension_scores[dimension]
                total_score += score * (weight / 100)
                total_weight += weight

        # 归一化到100分制
        if total_weight > 0:
            return (total_score / total_weight) * 100
        else:
            return 0.0

    def generate_feedback_report(self, evaluation_result: EvaluationResult) -> str:
        """生成详细的反馈报告"""
        report = []
        report.append(f"任务ID: {evaluation_result.task_id}")
        report.append(
            f"总分: {evaluation_result.total_score:.2f}/{evaluation_result.max_score}"
        )
        report.append(f"评估时间: {evaluation_result.execution_time:.2f}秒")
        report.append("=" * 50)

        # 各维度得分
        report.append("各维度得分:")
        for dimension, score in evaluation_result.dimension_scores.items():
            report.append(f"  {dimension}: {score:.2f}/100")

        report.append("\n详细反馈:")

        # 功能完整性反馈
        func_feedback = evaluation_result.detailed_feedback.get("functionality", {})
        if func_feedback:
            report.append(
                f"功能测试: {func_feedback.get('passed_tests', 0)}/{func_feedback.get('total_tests', 0)} 通过"
            )
            if func_feedback.get("issues"):
                report.append("功能问题:")
                for issue in func_feedback["issues"]:
                    report.append(f"  - {issue}")

        # 代码质量反馈
        quality_feedback = evaluation_result.detailed_feedback.get("code_quality", {})
        if quality_feedback:
            report.append(f"代码质量:")
            report.append(f"  语法分数: {quality_feedback.get('syntax_score', 0):.1f}")
            report.append(
                f"  结构分数: {quality_feedback.get('structure_score', 0):.1f}"
            )
            report.append(f"  风格分数: {quality_feedback.get('style_score', 0):.1f}")
            if quality_feedback.get("issues"):
                report.append("质量问题:")
                for issue in quality_feedback["issues"]:
                    report.append(f"  - {issue}")

        # 性能反馈
        perf_feedback = evaluation_result.detailed_feedback.get("performance", {})
        if perf_feedback:
            report.append(f"性能:")
            report.append(f"  执行时间: {perf_feedback.get('execution_time', 0):.3f}秒")
            if perf_feedback.get("issues"):
                report.append("性能问题:")
                for issue in perf_feedback["issues"]:
                    report.append(f"  - {issue}")

        # 安全性反馈
        security_feedback = evaluation_result.detailed_feedback.get("security", {})
        if security_feedback:
            vuln_count = security_feedback.get("vulnerability_count", 0)
            report.append(f"安全性: 发现{vuln_count}个安全问题")
            if security_feedback.get("security_issues"):
                for issue in security_feedback["security_issues"]:
                    report.append(f"  - {issue}")

        return "\n".join(report)


# 使用示例
if __name__ == "__main__":
    # 示例评估
    evaluator = CodeEvaluator()

    task_config = {
        "id": "test_task",
        "level": "beginner",
        "evaluation_criteria": {
            "functionality": 40,
            "code_quality": 25,
            "performance": 15,
            "security": 10,
            "documentation": 10,
        },
        "test_cases": [
            {"input": {"value": 0, "unit": "C"}, "expected": (32.0, "F")},
            {"input": {"value": 32, "unit": "F"}, "expected": (0.0, "C")},
        ],
        "input_spec": {"function_name": "temperature_converter"},
    }

    sample_code = '''
def temperature_converter(value, unit):
    """温度转换函数
    
    Args:
        value: 温度值
        unit: 单位 ('C' 或 'F')
    
    Returns:
        tuple: (转换后的温度值, 转换后的单位)
    """
    if unit == 'C':
        return round((value * 9/5) + 32, 1), 'F'
    elif unit == 'F':
        return round((value - 32) * 5/9, 1), 'C'
    else:
        raise ValueError("Invalid unit")
'''

    async def test_evaluation():
        result = await evaluator.evaluate_code(task_config, sample_code)
        print(evaluator.generate_feedback_report(result))

    asyncio.run(test_evaluation())
