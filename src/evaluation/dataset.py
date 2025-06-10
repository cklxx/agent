"""
评测数据集管理模块
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid

logger = logging.getLogger(__name__)


class TestCaseType(Enum):
    """测试用例类型"""

    CODE_GENERATION = "code_generation"  # 代码生成
    CODE_DEBUGGING = "code_debugging"  # 代码调试
    CODE_OPTIMIZATION = "code_optimization"  # 代码优化
    CODE_REVIEW = "code_review"  # 代码审查
    CODE_EXPLANATION = "code_explanation"  # 代码解释
    FILE_OPERATION = "file_operation"  # 文件操作
    PROJECT_SETUP = "project_setup"  # 项目搭建
    DEPENDENCY_MANAGEMENT = "dependency_mgmt"  # 依赖管理
    TESTING = "testing"  # 测试相关
    DOCUMENTATION = "documentation"  # 文档生成


class DifficultyLevel(Enum):
    """难度等级"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass
class TestCase:
    """测试用例数据结构"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    case_type: TestCaseType = TestCaseType.CODE_GENERATION
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM

    # 输入数据
    prompt: str = ""  # 用户输入的任务描述
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    files: Dict[str, str] = field(default_factory=dict)  # 相关文件内容

    # 期望输出
    expected_output: Dict[str, Any] = field(default_factory=dict)
    expected_files: Dict[str, str] = field(default_factory=dict)  # 期望生成的文件
    expected_commands: List[str] = field(default_factory=list)  # 期望执行的命令

    # 评估标准
    success_criteria: List[str] = field(default_factory=list)  # 成功标准
    evaluation_script: Optional[str] = None  # 自定义评估脚本

    # 元数据
    tags: List[str] = field(default_factory=list)
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "case_type": self.case_type.value,
            "difficulty": self.difficulty.value,
            "prompt": self.prompt,
            "context": self.context,
            "files": self.files,
            "expected_output": self.expected_output,
            "expected_files": self.expected_files,
            "expected_commands": self.expected_commands,
            "success_criteria": self.success_criteria,
            "evaluation_script": self.evaluation_script,
            "tags": self.tags,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        """从字典创建测试用例"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            case_type=TestCaseType(data.get("case_type", "code_generation")),
            difficulty=DifficultyLevel(data.get("difficulty", "medium")),
            prompt=data.get("prompt", ""),
            context=data.get("context", {}),
            files=data.get("files", {}),
            expected_output=data.get("expected_output", {}),
            expected_files=data.get("expected_files", {}),
            expected_commands=data.get("expected_commands", []),
            success_criteria=data.get("success_criteria", []),
            evaluation_script=data.get("evaluation_script"),
            tags=data.get("tags", []),
            author=data.get("author", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class EvaluationDataset:
    """评测数据集管理器"""

    def __init__(self, dataset_path: str = "benckmark/datasets"):
        """
        初始化数据集管理器

        Args:
            dataset_path: 数据集存储路径
        """
        self.dataset_path = Path(dataset_path)
        self.dataset_path.mkdir(parents=True, exist_ok=True)

        self.test_cases: Dict[str, TestCase] = {}
        self.metadata = {
            "name": "Code Agent Evaluation Dataset",
            "version": "1.0.0",
            "description": "代码智能体能力评测数据集",
            "created_at": datetime.now().isoformat(),
            "total_cases": 0,
            "case_types": {},
            "difficulty_distribution": {},
        }

        # 加载现有数据集
        self._load_dataset()

        logger.info(f"EvaluationDataset初始化完成，数据集路径: {dataset_path}")

    def _load_dataset(self):
        """加载数据集"""
        try:
            # 加载元数据
            metadata_file = self.dataset_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self.metadata.update(json.load(f))

            # 加载测试用例
            cases_dir = self.dataset_path / "cases"
            if cases_dir.exists():
                for case_file in cases_dir.glob("*.json"):
                    try:
                        with open(case_file, "r", encoding="utf-8") as f:
                            case_data = json.load(f)
                            test_case = TestCase.from_dict(case_data)
                            self.test_cases[test_case.id] = test_case
                    except Exception as e:
                        logger.error(f"加载测试用例失败 {case_file}: {e}")

            self._update_metadata()
            logger.info(f"加载了 {len(self.test_cases)} 个测试用例")

        except Exception as e:
            logger.error(f"加载数据集失败: {e}")

    def _save_dataset(self):
        """保存数据集"""
        try:
            # 保存元数据
            metadata_file = self.dataset_path / "metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)

            # 保存测试用例
            cases_dir = self.dataset_path / "cases"
            cases_dir.mkdir(exist_ok=True)

            for test_case in self.test_cases.values():
                case_file = cases_dir / f"{test_case.id}.json"
                with open(case_file, "w", encoding="utf-8") as f:
                    json.dump(test_case.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(f"保存了 {len(self.test_cases)} 个测试用例")

        except Exception as e:
            logger.error(f"保存数据集失败: {e}")

    def _update_metadata(self):
        """更新元数据统计"""
        self.metadata["total_cases"] = len(self.test_cases)
        self.metadata["updated_at"] = datetime.now().isoformat()

        # 统计用例类型分布
        case_types = {}
        difficulty_distribution = {}

        for test_case in self.test_cases.values():
            case_type = test_case.case_type.value
            difficulty = test_case.difficulty.value

            case_types[case_type] = case_types.get(case_type, 0) + 1
            difficulty_distribution[difficulty] = (
                difficulty_distribution.get(difficulty, 0) + 1
            )

        self.metadata["case_types"] = case_types
        self.metadata["difficulty_distribution"] = difficulty_distribution

    def add_test_case(self, test_case: TestCase) -> bool:
        """
        添加测试用例

        Args:
            test_case: 测试用例

        Returns:
            是否成功添加
        """
        try:
            test_case.updated_at = datetime.now().isoformat()
            self.test_cases[test_case.id] = test_case

            self._update_metadata()
            self._save_dataset()

            logger.info(f"添加测试用例: {test_case.name} ({test_case.id})")
            return True

        except Exception as e:
            logger.error(f"添加测试用例失败: {e}")
            return False

    def remove_test_case(self, case_id: str) -> bool:
        """
        删除测试用例

        Args:
            case_id: 测试用例ID

        Returns:
            是否成功删除
        """
        try:
            if case_id in self.test_cases:
                del self.test_cases[case_id]

                # 删除文件
                case_file = self.dataset_path / "cases" / f"{case_id}.json"
                if case_file.exists():
                    case_file.unlink()

                self._update_metadata()
                self._save_dataset()

                logger.info(f"删除测试用例: {case_id}")
                return True
            else:
                logger.warning(f"测试用例不存在: {case_id}")
                return False

        except Exception as e:
            logger.error(f"删除测试用例失败: {e}")
            return False

    def get_test_case(self, case_id: str) -> Optional[TestCase]:
        """获取测试用例"""
        return self.test_cases.get(case_id)

    def get_test_cases(
        self,
        case_type: Optional[TestCaseType] = None,
        difficulty: Optional[DifficultyLevel] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[TestCase]:
        """
        获取测试用例列表

        Args:
            case_type: 用例类型过滤
            difficulty: 难度级别过滤
            tags: 标签过滤
            limit: 结果数量限制

        Returns:
            测试用例列表
        """
        cases = list(self.test_cases.values())

        # 应用过滤器
        if case_type:
            cases = [case for case in cases if case.case_type == case_type]

        if difficulty:
            cases = [case for case in cases if case.difficulty == difficulty]

        if tags:
            tag_set = set(tags)
            cases = [case for case in cases if tag_set.intersection(set(case.tags))]

        # 按创建时间排序
        cases.sort(key=lambda x: x.created_at, reverse=True)

        # 应用数量限制
        if limit:
            cases = cases[:limit]

        return cases

    def create_sample_dataset(self):
        """创建示例数据集"""
        sample_cases = [
            TestCase(
                name="Python函数生成 - 计算斐波那契数列",
                description="生成一个计算斐波那契数列第n项的Python函数",
                case_type=TestCaseType.CODE_GENERATION,
                difficulty=DifficultyLevel.EASY,
                prompt="请写一个Python函数，计算斐波那契数列的第n项，要求使用递归实现",
                expected_output={"function_name": "fibonacci"},
                success_criteria=[
                    "函数名为fibonacci",
                    "使用递归实现",
                    "能正确计算斐波那契数列",
                    "包含必要的参数检查",
                ],
                tags=["python", "recursion", "fibonacci", "basic"],
            ),
            TestCase(
                name="代码Bug修复 - 数组越界",
                description="修复Python代码中的数组越界错误",
                case_type=TestCaseType.CODE_DEBUGGING,
                difficulty=DifficultyLevel.MEDIUM,
                prompt="以下代码存在数组越界错误，请修复:\n\ndef process_list(items):\n    result = []\n    for i in range(len(items) + 1):\n        result.append(items[i] * 2)\n    return result",
                context={"error_message": "IndexError: list index out of range"},
                expected_output={"bug_fixed": True},
                success_criteria=[
                    "修复数组越界错误",
                    "保持原有功能逻辑",
                    "代码能正常运行",
                ],
                tags=["python", "debugging", "array", "error_fix"],
            ),
            TestCase(
                name="文件操作 - 读取CSV并处理",
                description="读取CSV文件并进行数据处理",
                case_type=TestCaseType.FILE_OPERATION,
                difficulty=DifficultyLevel.MEDIUM,
                prompt="请写代码读取CSV文件'data.csv'，计算每列的平均值，并将结果保存到新的CSV文件",
                files={
                    "data.csv": "name,age,score\nAlice,25,85\nBob,30,92\nCharlie,28,78"
                },
                expected_files={"result.csv": "column,average\nage,27.67\nscore,85.0"},
                success_criteria=[
                    "正确读取CSV文件",
                    "计算数值列的平均值",
                    "保存结果到新文件",
                    "处理异常情况",
                ],
                tags=["python", "csv", "data_processing", "file_io"],
            ),
            TestCase(
                name="项目初始化 - Flask Web应用",
                description="创建一个基础的Flask Web应用项目结构",
                case_type=TestCaseType.PROJECT_SETUP,
                difficulty=DifficultyLevel.HARD,
                prompt="请创建一个Flask Web应用的基础项目结构，包含路由、模板和静态文件目录",
                expected_files={
                    "app.py": "Flask application entry point",
                    "requirements.txt": "Flask dependency",
                    "templates/index.html": "HTML template",
                    "static/style.css": "CSS styles",
                },
                expected_commands=["pip install flask"],
                success_criteria=[
                    "创建正确的项目结构",
                    "包含基础Flask应用",
                    "能够运行并响应请求",
                    "包含必要的依赖文件",
                ],
                tags=["python", "flask", "web", "project_setup"],
            ),
            TestCase(
                name="代码性能优化 - 循环优化",
                description="优化嵌套循环的性能",
                case_type=TestCaseType.CODE_OPTIMIZATION,
                difficulty=DifficultyLevel.EXPERT,
                prompt="优化以下代码的性能:\n\ndef find_duplicates(arr):\n    duplicates = []\n    for i in range(len(arr)):\n        for j in range(i+1, len(arr)):\n            if arr[i] == arr[j] and arr[i] not in duplicates:\n                duplicates.append(arr[i])\n    return duplicates",
                expected_output={"optimized": True, "time_complexity": "O(n)"},
                success_criteria=[
                    "显著提升时间复杂度",
                    "保持功能正确性",
                    "使用更高效的数据结构",
                    "提供性能分析说明",
                ],
                tags=["python", "optimization", "algorithm", "performance"],
            ),
        ]

        for case in sample_cases:
            case.author = "system"
            self.add_test_case(case)

        logger.info(f"创建了 {len(sample_cases)} 个示例测试用例")

    def export_dataset(self, export_path: str, format: str = "json") -> bool:
        """
        导出数据集

        Args:
            export_path: 导出路径
            format: 导出格式 (json, yaml)

        Returns:
            是否成功导出
        """
        try:
            export_data = {
                "metadata": self.metadata,
                "test_cases": [case.to_dict() for case in self.test_cases.values()],
            }

            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "json":
                with open(export_file, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            elif format.lower() == "yaml":
                import yaml

                with open(export_file, "w", encoding="utf-8") as f:
                    yaml.dump(
                        export_data, f, default_flow_style=False, allow_unicode=True
                    )
            else:
                raise ValueError(f"不支持的导出格式: {format}")

            logger.info(f"数据集已导出到: {export_path}")
            return True

        except Exception as e:
            logger.error(f"导出数据集失败: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据集统计信息"""
        return {
            "dataset_info": self.metadata,
            "total_cases": len(self.test_cases),
            "case_types": self.metadata.get("case_types", {}),
            "difficulty_distribution": self.metadata.get("difficulty_distribution", {}),
            "recent_cases": len(
                [
                    case
                    for case in self.test_cases.values()
                    if (datetime.now() - datetime.fromisoformat(case.created_at)).days
                    <= 7
                ]
            ),
        }
