"""
评测指标计算模块
"""

import asyncio
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import ast
import json

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""

    ACCURACY = "accuracy"  # 准确率
    COMPLETENESS = "completeness"  # 完整性
    CORRECTNESS = "correctness"  # 正确性
    EFFICIENCY = "efficiency"  # 效率
    CODE_QUALITY = "code_quality"  # 代码质量
    SYNTAX_VALIDITY = "syntax_validity"  # 语法有效性
    EXECUTION_SUCCESS = "execution_success"  # 执行成功率
    OUTPUT_MATCH = "output_match"  # 输出匹配度
    FILE_GENERATION = "file_generation"  # 文件生成正确性
    COMMAND_EXECUTION = "command_execution"  # 命令执行正确性
    RESPONSE_TIME = "response_time"  # 响应时间
    TOKEN_USAGE = "token_usage"  # Token使用量


@dataclass
class MetricResult:
    """指标结果"""

    metric_type: MetricType
    score: float  # 0-1之间的分数
    max_score: float = 1.0  # 最大分数
    details: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""  # 评分说明

    @property
    def percentage(self) -> float:
        """百分比形式的分数"""
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metric_type": self.metric_type.value,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "details": self.details,
            "explanation": self.explanation,
        }


@dataclass
class EvaluationResult:
    """评测结果"""

    test_case_id: str
    test_case_name: str
    agent_response: Dict[str, Any]  # Agent的响应
    metrics: List[MetricResult] = field(default_factory=list)
    overall_score: float = 0.0  # 总体分数
    success: bool = False  # 是否成功
    execution_time: float = 0.0  # 执行时间（秒）
    error_message: Optional[str] = None  # 错误信息
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_metric(self, metric: MetricResult):
        """添加指标结果"""
        self.metrics.append(metric)
        self._calculate_overall_score()

    def _calculate_overall_score(self):
        """计算总体分数"""
        if not self.metrics:
            self.overall_score = 0.0
            return

        # 简单平均，也可以根据需要调整权重
        total_score = sum(metric.score for metric in self.metrics)
        self.overall_score = total_score / len(self.metrics)

        # 判断是否成功（总分超过60%）
        self.success = self.overall_score >= 0.6

    def get_metric_by_type(self, metric_type: MetricType) -> Optional[MetricResult]:
        """根据类型获取指标"""
        for metric in self.metrics:
            if metric.metric_type == metric_type:
                return metric
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "test_case_id": self.test_case_id,
            "test_case_name": self.test_case_name,
            "agent_response": self.agent_response,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "overall_score": self.overall_score,
            "success": self.success,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }


class EvaluationMetrics:
    """评测指标计算器"""

    def __init__(self):
        """初始化指标计算器"""
        self.temp_dir = Path(tempfile.gettempdir()) / "code_agent_eval"
        self.temp_dir.mkdir(exist_ok=True)
        logger.info("EvaluationMetrics初始化完成")

    async def evaluate_response(
        self,
        test_case,  # 避免循环导入
        agent_response: Dict[str, Any],
        execution_time: float = 0.0,
    ) -> EvaluationResult:
        """
        评估Agent响应

        Args:
            test_case: 测试用例
            agent_response: Agent响应
            execution_time: 执行时间

        Returns:
            评测结果
        """
        result = EvaluationResult(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            agent_response=agent_response,
            execution_time=execution_time,
        )

        try:
            # 根据测试用例类型选择相应的评测指标
            if test_case.case_type.value == "code_generation":
                await self._evaluate_code_generation(test_case, agent_response, result)
            elif test_case.case_type.value == "code_debugging":
                await self._evaluate_code_debugging(test_case, agent_response, result)
            elif test_case.case_type.value == "file_operation":
                await self._evaluate_file_operation(test_case, agent_response, result)
            elif test_case.case_type.value == "project_setup":
                await self._evaluate_project_setup(test_case, agent_response, result)
            else:
                # 通用评测
                await self._evaluate_general(test_case, agent_response, result)

            # 添加通用指标
            await self._add_common_metrics(test_case, agent_response, result)

        except Exception as e:
            logger.error(f"评测失败: {e}")
            result.error_message = str(e)

            # 添加失败指标
            for metric_type in [MetricType.ACCURACY, MetricType.CORRECTNESS]:
                result.add_metric(
                    MetricResult(
                        metric_type=metric_type, score=0.0, explanation=f"评测失败: {e}"
                    )
                )

        return result

    async def _evaluate_code_generation(
        self, test_case, agent_response: Dict[str, Any], result: EvaluationResult
    ):
        """评估代码生成任务"""
        # 语法有效性检查
        syntax_metric = await self._check_syntax_validity(agent_response)
        result.add_metric(syntax_metric)

        # 执行成功率检查
        execution_metric = await self._check_execution_success(
            agent_response, test_case
        )
        result.add_metric(execution_metric)

        # 输出匹配度检查
        if test_case.expected_output:
            output_metric = await self._check_output_match(
                agent_response, test_case.expected_output
            )
            result.add_metric(output_metric)

        # 代码质量检查
        quality_metric = await self._check_code_quality(agent_response)
        result.add_metric(quality_metric)

    async def _evaluate_code_debugging(
        self, test_case, agent_response: Dict[str, Any], result: EvaluationResult
    ):
        """评估代码调试任务"""
        # 语法有效性
        syntax_metric = await self._check_syntax_validity(agent_response)
        result.add_metric(syntax_metric)

        # 是否修复了Bug
        bug_fix_metric = await self._check_bug_fix(agent_response, test_case)
        result.add_metric(bug_fix_metric)

        # 执行成功率
        execution_metric = await self._check_execution_success(
            agent_response, test_case
        )
        result.add_metric(execution_metric)

    async def _evaluate_file_operation(
        self, test_case, agent_response: Dict[str, Any], result: EvaluationResult
    ):
        """评估文件操作任务"""
        # 文件生成正确性
        if test_case.expected_files:
            file_metric = await self._check_file_generation(
                agent_response, test_case.expected_files
            )
            result.add_metric(file_metric)

        # 执行成功率
        execution_metric = await self._check_execution_success(
            agent_response, test_case
        )
        result.add_metric(execution_metric)

    async def _evaluate_project_setup(
        self, test_case, agent_response: Dict[str, Any], result: EvaluationResult
    ):
        """评估项目搭建任务"""
        # 文件生成正确性
        if test_case.expected_files:
            file_metric = await self._check_file_generation(
                agent_response, test_case.expected_files
            )
            result.add_metric(file_metric)

        # 命令执行正确性
        if test_case.expected_commands:
            command_metric = await self._check_command_execution(
                agent_response, test_case.expected_commands
            )
            result.add_metric(command_metric)

        # 项目结构完整性
        structure_metric = await self._check_project_structure(
            agent_response, test_case
        )
        result.add_metric(structure_metric)

    async def _evaluate_general(
        self, test_case, agent_response: Dict[str, Any], result: EvaluationResult
    ):
        """通用评测"""
        # 响应完整性
        completeness_metric = await self._check_completeness(agent_response, test_case)
        result.add_metric(completeness_metric)

        # 响应准确性
        accuracy_metric = await self._check_accuracy(agent_response, test_case)
        result.add_metric(accuracy_metric)

    async def _add_common_metrics(
        self, test_case, agent_response: Dict[str, Any], result: EvaluationResult
    ):
        """添加通用指标"""
        # 响应时间指标
        time_metric = MetricResult(
            metric_type=MetricType.RESPONSE_TIME,
            score=min(
                1.0, max(0.0, (30.0 - result.execution_time) / 30.0)
            ),  # 30秒内得满分
            explanation=f"响应时间: {result.execution_time:.2f}秒",
        )
        result.add_metric(time_metric)

        # Token使用量指标（如果有的话）
        if "token_usage" in agent_response:
            token_usage = agent_response["token_usage"]
            token_metric = MetricResult(
                metric_type=MetricType.TOKEN_USAGE,
                score=min(
                    1.0, max(0.0, (5000 - token_usage) / 5000)
                ),  # 5000 token内得满分
                details={"token_usage": token_usage},
                explanation=f"Token使用量: {token_usage}",
            )
            result.add_metric(token_metric)

    async def _check_syntax_validity(
        self, agent_response: Dict[str, Any]
    ) -> MetricResult:
        """检查语法有效性"""
        try:
            # 提取代码
            code = self._extract_code_from_response(agent_response)
            if not code:
                return MetricResult(
                    metric_type=MetricType.SYNTAX_VALIDITY,
                    score=0.0,
                    explanation="未找到代码内容",
                )

            # 检查Python语法
            try:
                ast.parse(code)
                return MetricResult(
                    metric_type=MetricType.SYNTAX_VALIDITY,
                    score=1.0,
                    explanation="Python语法正确",
                )
            except SyntaxError as e:
                return MetricResult(
                    metric_type=MetricType.SYNTAX_VALIDITY,
                    score=0.0,
                    details={"syntax_error": str(e)},
                    explanation=f"语法错误: {e}",
                )

        except Exception as e:
            return MetricResult(
                metric_type=MetricType.SYNTAX_VALIDITY,
                score=0.0,
                explanation=f"语法检查失败: {e}",
            )

    async def _check_execution_success(
        self, agent_response: Dict[str, Any], test_case
    ) -> MetricResult:
        """检查执行成功率"""
        try:
            code = self._extract_code_from_response(agent_response)
            if not code:
                return MetricResult(
                    metric_type=MetricType.EXECUTION_SUCCESS,
                    score=0.0,
                    explanation="未找到可执行代码",
                )

            # 在临时文件中执行代码
            temp_file = self.temp_dir / f"test_{test_case.id}.py"

            # 准备测试环境
            full_code = self._prepare_test_environment(code, test_case)

            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(full_code)

            # 执行代码
            result = subprocess.run(
                ["python", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=30,  # 30秒超时
            )

            # 清理临时文件
            temp_file.unlink(missing_ok=True)

            if result.returncode == 0:
                return MetricResult(
                    metric_type=MetricType.EXECUTION_SUCCESS,
                    score=1.0,
                    details={"stdout": result.stdout[:500]},  # 限制输出长度
                    explanation="代码执行成功",
                )
            else:
                return MetricResult(
                    metric_type=MetricType.EXECUTION_SUCCESS,
                    score=0.0,
                    details={
                        "returncode": result.returncode,
                        "stderr": result.stderr[:500],
                    },
                    explanation=f"代码执行失败: {result.stderr[:100]}",
                )

        except subprocess.TimeoutExpired:
            return MetricResult(
                metric_type=MetricType.EXECUTION_SUCCESS,
                score=0.0,
                explanation="代码执行超时",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.EXECUTION_SUCCESS,
                score=0.0,
                explanation=f"执行检查失败: {e}",
            )

    def _extract_code_from_response(self, agent_response: Dict[str, Any]) -> str:
        """从响应中提取代码"""
        # 尝试从不同字段提取代码
        for key in ["code", "content", "response", "output"]:
            if key in agent_response:
                content = agent_response[key]
                if isinstance(content, str):
                    # 提取代码块
                    code_blocks = re.findall(
                        r"```(?:python)?\n?(.*?)\n?```", content, re.DOTALL
                    )
                    if code_blocks:
                        return code_blocks[0].strip()
                    return content

        # 从整个响应文本中提取
        response_text = str(agent_response)
        code_blocks = re.findall(
            r"```(?:python)?\n?(.*?)\n?```", response_text, re.DOTALL
        )
        if code_blocks:
            return code_blocks[0].strip()

        return ""

    def _prepare_test_environment(self, code: str, test_case) -> str:
        """准备测试环境代码"""
        # 添加必要的导入和测试数据
        environment_code = []

        # 添加常用导入
        environment_code.append("import sys")
        environment_code.append("import os")
        environment_code.append("import json")

        # 如果测试用例有文件数据，创建这些文件
        if hasattr(test_case, "files") and test_case.files:
            for file_path, file_content in test_case.files.items():
                environment_code.append(
                    f"""
with open('{file_path}', 'w', encoding='utf-8') as f:
    f.write('''{file_content}''')
"""
                )

        # 添加主要代码
        environment_code.append(code)

        # 添加简单的测试调用（如果是函数定义）
        if "def " in code:
            # 尝试提取函数名并调用
            func_matches = re.findall(r"def\s+(\w+)\s*\(", code)
            if func_matches:
                func_name = func_matches[0]
                environment_code.append(
                    f"""
# 简单测试调用
try:
    if '{func_name}' in locals():
        print(f"函数 {func_name} 定义成功")
except Exception as e:
    print(f"测试调用失败: {{e}}")
"""
                )

        return "\n".join(environment_code)

    async def _check_output_match(
        self, agent_response: Dict[str, Any], expected_output: Dict[str, Any]
    ) -> MetricResult:
        """检查输出匹配度"""
        try:
            matches = 0
            total = len(expected_output)

            for key, expected_value in expected_output.items():
                if key in agent_response:
                    actual_value = agent_response[key]
                    if str(actual_value).lower() == str(expected_value).lower():
                        matches += 1
                elif self._find_in_response_text(agent_response, str(expected_value)):
                    matches += 1

            score = matches / total if total > 0 else 1.0

            return MetricResult(
                metric_type=MetricType.OUTPUT_MATCH,
                score=score,
                details={
                    "matches": matches,
                    "total": total,
                    "expected": expected_output,
                },
                explanation=f"输出匹配: {matches}/{total}",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.OUTPUT_MATCH,
                score=0.0,
                explanation=f"输出匹配检查失败: {e}",
            )

    async def _check_code_quality(self, agent_response: Dict[str, Any]) -> MetricResult:
        """检查代码质量"""
        try:
            code = self._extract_code_from_response(agent_response)
            if not code:
                return MetricResult(
                    metric_type=MetricType.CODE_QUALITY,
                    score=0.0,
                    explanation="未找到代码内容",
                )

            quality_score = 0.0
            quality_details = {}

            # 检查注释
            comment_ratio = len(re.findall(r"#.*", code)) / max(
                len(code.split("\n")), 1
            )
            if comment_ratio > 0.1:
                quality_score += 0.3
                quality_details["has_comments"] = True

            # 检查函数定义
            if re.search(r"def\s+\w+\s*\(", code):
                quality_score += 0.3
                quality_details["has_functions"] = True

            # 检查错误处理
            if "try:" in code or "except" in code:
                quality_score += 0.2
                quality_details["has_error_handling"] = True

            # 检查变量命名
            if not re.search(r"\b[a-z]{1,2}\b", code):
                quality_score += 0.2
                quality_details["good_naming"] = True

            return MetricResult(
                metric_type=MetricType.CODE_QUALITY,
                score=min(1.0, quality_score),
                details=quality_details,
                explanation=f"代码质量评分: {quality_score:.2f}",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.CODE_QUALITY,
                score=0.0,
                explanation=f"代码质量检查失败: {e}",
            )

    async def _check_bug_fix(
        self, agent_response: Dict[str, Any], test_case
    ) -> MetricResult:
        """检查是否修复了Bug"""
        try:
            if self._extract_code_from_response(agent_response):
                original_code = test_case.prompt
                fixed_code = self._extract_code_from_response(agent_response)

                # 检查是否修复了越界错误
                if (
                    "range(len(items) + 1)" in original_code
                    and "range(len(items) + 1)" not in fixed_code
                ):
                    return MetricResult(
                        metric_type=MetricType.CORRECTNESS,
                        score=1.0,
                        explanation="成功修复数组越界错误",
                    )

                # 通用检查
                if fixed_code != original_code:
                    return MetricResult(
                        metric_type=MetricType.CORRECTNESS,
                        score=0.7,
                        explanation="代码有修改，可能修复了问题",
                    )

            return MetricResult(
                metric_type=MetricType.CORRECTNESS,
                score=0.0,
                explanation="未发现明显的Bug修复",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.CORRECTNESS,
                score=0.0,
                explanation=f"Bug修复检查失败: {e}",
            )

    async def _check_file_generation(
        self, agent_response: Dict[str, Any], expected_files: Dict[str, str]
    ) -> MetricResult:
        """检查文件生成正确性"""
        try:
            generated_files = agent_response.get("files", {})
            if not generated_files:
                generated_files = self._extract_files_from_response(agent_response)

            matches = 0
            total = len(expected_files)

            for file_path, expected_content in expected_files.items():
                if file_path in generated_files:
                    matches += 1
                else:
                    response_text = str(agent_response)
                    if file_path in response_text:
                        matches += 0.5

            score = matches / total if total > 0 else 1.0

            return MetricResult(
                metric_type=MetricType.FILE_GENERATION,
                score=score,
                details={
                    "expected_files": list(expected_files.keys()),
                    "generated_files": list(generated_files.keys()),
                    "matches": matches,
                    "total": total,
                },
                explanation=f"文件生成: {matches}/{total}",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.FILE_GENERATION,
                score=0.0,
                explanation=f"文件生成检查失败: {e}",
            )

    async def _check_command_execution(
        self, agent_response: Dict[str, Any], expected_commands: List[str]
    ) -> MetricResult:
        """检查命令执行正确性"""
        try:
            executed_commands = agent_response.get("commands", [])
            if not executed_commands:
                executed_commands = self._extract_commands_from_response(agent_response)

            matches = 0
            total = len(expected_commands)

            for expected_cmd in expected_commands:
                for executed_cmd in executed_commands:
                    if expected_cmd.lower() in executed_cmd.lower():
                        matches += 1
                        break

            score = matches / total if total > 0 else 1.0

            return MetricResult(
                metric_type=MetricType.COMMAND_EXECUTION,
                score=score,
                details={
                    "expected_commands": expected_commands,
                    "executed_commands": executed_commands,
                    "matches": matches,
                    "total": total,
                },
                explanation=f"命令执行: {matches}/{total}",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.COMMAND_EXECUTION,
                score=0.0,
                explanation=f"命令执行检查失败: {e}",
            )

    async def _check_project_structure(
        self, agent_response: Dict[str, Any], test_case
    ) -> MetricResult:
        """检查项目结构完整性"""
        try:
            response_text = str(agent_response)

            structure_score = 0.0
            structure_details = {}

            # 检查关键目录
            key_dirs = ["templates", "static", "src", "tests"]
            mentioned_dirs = sum(
                1 for dir_name in key_dirs if dir_name in response_text
            )
            if mentioned_dirs > 0:
                structure_score += 0.3
                structure_details["mentioned_directories"] = mentioned_dirs

            # 检查配置文件
            config_files = [
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
                "package.json",
            ]
            mentioned_configs = sum(
                1 for config in config_files if config in response_text
            )
            if mentioned_configs > 0:
                structure_score += 0.4
                structure_details["mentioned_configs"] = mentioned_configs

            # 检查主应用文件
            app_files = ["app.py", "main.py", "server.py", "index.js"]
            mentioned_apps = sum(1 for app in app_files if app in response_text)
            if mentioned_apps > 0:
                structure_score += 0.3
                structure_details["mentioned_apps"] = mentioned_apps

            return MetricResult(
                metric_type=MetricType.COMPLETENESS,
                score=min(1.0, structure_score),
                details=structure_details,
                explanation=f"项目结构完整性: {structure_score:.2f}",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.COMPLETENESS,
                score=0.0,
                explanation=f"项目结构检查失败: {e}",
            )

    async def _check_completeness(
        self, agent_response: Dict[str, Any], test_case
    ) -> MetricResult:
        """检查响应完整性"""
        try:
            completeness_score = 0.0

            response_text = str(agent_response)
            if len(response_text) > 100:
                completeness_score += 0.5

            success_criteria = getattr(test_case, "success_criteria", [])
            met_criteria = 0

            for criteria in success_criteria:
                if criteria.lower() in response_text.lower():
                    met_criteria += 1

            if success_criteria:
                criteria_score = met_criteria / len(success_criteria)
                completeness_score += 0.5 * criteria_score
            else:
                completeness_score += 0.5

            return MetricResult(
                metric_type=MetricType.COMPLETENESS,
                score=min(1.0, completeness_score),
                details={
                    "met_criteria": met_criteria,
                    "total_criteria": len(success_criteria),
                    "response_length": len(response_text),
                },
                explanation=f"完整性: 满足 {met_criteria}/{len(success_criteria)} 项标准",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.COMPLETENESS,
                score=0.0,
                explanation=f"完整性检查失败: {e}",
            )

    async def _check_accuracy(
        self, agent_response: Dict[str, Any], test_case
    ) -> MetricResult:
        """检查响应准确性"""
        try:
            prompt_keywords = re.findall(r"\b\w{4,}\b", test_case.prompt.lower())
            response_text = str(agent_response).lower()

            matched_keywords = sum(
                1 for keyword in prompt_keywords if keyword in response_text
            )
            total_keywords = len(prompt_keywords)

            accuracy_score = (
                matched_keywords / total_keywords if total_keywords > 0 else 1.0
            )

            return MetricResult(
                metric_type=MetricType.ACCURACY,
                score=min(1.0, accuracy_score),
                details={
                    "matched_keywords": matched_keywords,
                    "total_keywords": total_keywords,
                },
                explanation=f"准确性: 匹配 {matched_keywords}/{total_keywords} 个关键词",
            )
        except Exception as e:
            return MetricResult(
                metric_type=MetricType.ACCURACY,
                score=0.0,
                explanation=f"准确性检查失败: {e}",
            )

    def _extract_files_from_response(
        self, agent_response: Dict[str, Any]
    ) -> Dict[str, str]:
        """从响应中提取文件信息"""
        files = {}
        response_text = str(agent_response)

        file_patterns = [
            r"(\w+\.\w+):?\s*\n```[^`]*```",
            r'create\s+(?:file\s+)?[\'"]?([^\'"\s]+)[\'"]?',
            r'save\s+(?:to\s+)?[\'"]?([^\'"\s]+)[\'"]?',
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            for match in matches:
                if "." in match:
                    files[match] = "generated_content"

        return files

    def _extract_commands_from_response(
        self, agent_response: Dict[str, Any]
    ) -> List[str]:
        """从响应中提取命令"""
        commands = []
        response_text = str(agent_response)

        command_patterns = [
            r"pip install ([^\\n]+)",
            r"npm install ([^\\n]+)",
            r"python ([^\\n]+)",
            r'run[ning]*:?\s*[`\'"]?([^`\'"\\n]+)[`\'"]?',
        ]

        for pattern in command_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            commands.extend(matches)

        return commands

    def _find_in_response_text(
        self, agent_response: Dict[str, Any], search_text: str
    ) -> bool:
        """在响应文本中查找指定内容"""
        response_text = str(agent_response).lower()
        return search_text.lower() in response_text
