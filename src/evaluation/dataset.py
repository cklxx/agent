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


@dataclass
class TestCaseType(Enum):
    """Test case types"""

    CODE_GENERATION = "code_generation"  # Code generation tasks
    CODE_DEBUG = "code_debug"  # Code debugging tasks
    FILE_OPERATION = "file_operation"  # File operation tasks
    PROJECT_SETUP = "project_setup"  # Project setup tasks
    CODE_OPTIMIZATION = "code_optimization"  # Code optimization tasks


@dataclass
class DifficultyLevel(Enum):
    """Difficulty levels"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class TestCase:
    """Test case data structure"""

    id: str
    name: str
    type: TestCaseType
    difficulty: DifficultyLevel
    description: str
    prompt: str = ""  # User input task description
    context: Dict[str, Any] = field(default_factory=dict)  # Context information
    files: Dict[str, str] = field(default_factory=dict)  # Related file content

    # Expected results
    expected_output: str = ""  # Expected output
    expected_files: Dict[str, str] = field(
        default_factory=dict
    )  # Expected generated files
    expected_commands: List[str] = field(
        default_factory=list
    )  # Expected executed commands

    # Evaluation criteria
    success_criteria: List[str] = field(default_factory=list)  # Success criteria
    time_limit: int = 600  # Time limit (seconds)
    memory_limit: int = 512  # Memory limit (MB)

    # Metadata
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        result = asdict(self)
        # Convert enum values to strings
        result["type"] = self.type.value
        result["difficulty"] = self.difficulty.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        """Create test case from dictionary"""
        # Convert string values to enums
        if "type" in data:
            data["type"] = TestCaseType(data["type"])
        if "difficulty" in data:
            data["difficulty"] = DifficultyLevel(data["difficulty"])

        return cls(**data)


class EvaluationDataset:
    """Evaluation dataset manager"""

    def __init__(self, dataset_path: str = "evaluation/dataset"):
        self.dataset_path = Path(dataset_path)
        self.dataset_path.mkdir(parents=True, exist_ok=True)

        self.test_cases: List[TestCase] = []
        self.metadata: Dict[str, Any] = {
            "name": "Agent Evaluation Dataset",
            "version": "1.0.0",
            "description": "Code agent capability evaluation dataset",
            "created_at": datetime.now().isoformat(),
            "total_cases": 0,
            "cases_by_type": {},
            "cases_by_difficulty": {},
        }

        logger.info(
            f"EvaluationDataset initialization completed, dataset path: {dataset_path}"
        )

    def load_dataset(self) -> None:
        """Load dataset"""
        try:
            # Load test cases
            cases_dir = self.dataset_path / "cases"
            if cases_dir.exists():
                for case_file in cases_dir.glob("*.json"):
                    try:
                        with open(case_file, "r", encoding="utf-8") as f:
                            case_data = json.load(f)
                            test_case = TestCase.from_dict(case_data)
                            self.test_cases.append(test_case)
                    except Exception as e:
                        logger.error(f"Failed to load test case {case_file}: {e}")

            # Load metadata
            metadata_file = self.dataset_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self.metadata.update(json.load(f))

            logger.info(f"Loaded {len(self.test_cases)} test cases")

        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")

    def save_dataset(self) -> None:
        """Save dataset"""
        try:
            # Save test cases
            cases_dir = self.dataset_path / "cases"
            cases_dir.mkdir(exist_ok=True)

            for test_case in self.test_cases:
                case_file = cases_dir / f"{test_case.id}.json"
                with open(case_file, "w", encoding="utf-8") as f:
                    json.dump(test_case.to_dict(), f, indent=2, ensure_ascii=False)

            # Update and save metadata
            self._update_metadata()
            metadata_file = self.dataset_path / "metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.test_cases)} test cases")

        except Exception as e:
            logger.error(f"Failed to save dataset: {e}")

    def _update_metadata(self) -> None:
        """Update metadata statistics"""
        self.metadata["total_cases"] = len(self.test_cases)
        self.metadata["updated_at"] = datetime.now().isoformat()

        # Statistics by type
        type_counts = {}
        for case in self.test_cases:
            case_type = case.type.value
            type_counts[case_type] = type_counts.get(case_type, 0) + 1
        self.metadata["cases_by_type"] = type_counts

        # Statistics by difficulty
        difficulty_counts = {}
        for case in self.test_cases:
            difficulty = case.difficulty.value
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        self.metadata["cases_by_difficulty"] = difficulty_counts

    def add_test_case(self, test_case: TestCase) -> None:
        """Add test case"""
        try:
            # Check if ID already exists
            existing_ids = {case.id for case in self.test_cases}
            if test_case.id in existing_ids:
                # Generate new ID
                base_id = test_case.id
                counter = 1
                while f"{base_id}_{counter}" in existing_ids:
                    counter += 1
                test_case.id = f"{base_id}_{counter}"

            # Set timestamps
            current_time = datetime.now().isoformat()
            if not test_case.created_at:
                test_case.created_at = current_time
            test_case.updated_at = current_time

            self.test_cases.append(test_case)
            logger.info(f"Added test case: {test_case.name} ({test_case.id})")

        except Exception as e:
            logger.error(f"Failed to add test case: {e}")

    def remove_test_case(self, case_id: str) -> bool:
        """Remove test case"""
        try:
            original_count = len(self.test_cases)
            self.test_cases = [case for case in self.test_cases if case.id != case_id]

            if len(self.test_cases) < original_count:
                logger.info(f"Removed test case: {case_id}")

                # Remove case file
                case_file = self.dataset_path / "cases" / f"{case_id}.json"
                if case_file.exists():
                    case_file.unlink()

                return True
            else:
                logger.warning(f"Test case does not exist: {case_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to remove test case: {e}")
            return False

    def get_test_case(self, case_id: str) -> Optional[TestCase]:
        """Get test case"""
        for case in self.test_cases:
            if case.id == case_id:
                return case
        return None

    def get_test_cases_by_type(self, case_type: TestCaseType) -> List[TestCase]:
        """Get test cases by type"""
        return [case for case in self.test_cases if case.type == case_type]

    def get_test_cases_by_difficulty(
        self, difficulty: DifficultyLevel
    ) -> List[TestCase]:
        """Get test cases by difficulty"""
        return [case for case in self.test_cases if case.difficulty == difficulty]

    def filter_test_cases(
        self,
        case_type: Optional[TestCaseType] = None,
        difficulty: Optional[DifficultyLevel] = None,
        tags: Optional[List[str]] = None,
    ) -> List[TestCase]:
        """Filter test cases"""
        filtered_cases = self.test_cases

        if case_type:
            filtered_cases = [case for case in filtered_cases if case.type == case_type]

        if difficulty:
            filtered_cases = [
                case for case in filtered_cases if case.difficulty == difficulty
            ]

        if tags:
            filtered_cases = [
                case for case in filtered_cases if any(tag in case.tags for tag in tags)
            ]

        return filtered_cases

    def create_sample_dataset(self) -> None:
        """Create sample dataset"""
        sample_cases = [
            TestCase(
                id="fibonacci_recursive",
                name="Fibonacci Sequence Generation - Recursive Implementation",
                type=TestCaseType.CODE_GENERATION,
                difficulty=DifficultyLevel.EASY,
                description="Generate a Python function to calculate the nth item of Fibonacci sequence",
                prompt="Please write a Python function to calculate the nth item of Fibonacci sequence, using recursive implementation",
                success_criteria=[
                    "Function name is fibonacci",
                    "Uses recursive implementation",
                    "Can correctly calculate Fibonacci sequence",
                    "Includes necessary parameter checking",
                ],
                tags=["python", "algorithm", "recursion"],
            ),
            TestCase(
                id="array_bounds_fix",
                name="Code Bug Fix - Array Bounds",
                type=TestCaseType.CODE_DEBUG,
                difficulty=DifficultyLevel.MEDIUM,
                description="Fix array bounds error in Python code",
                prompt="The following code has array bounds error, please fix:\n\ndef process_list(items):\n    result = []\n    for i in range(len(items) + 1):\n        result.append(items[i] * 2)\n    return result",
                success_criteria=[
                    "Fix array bounds error",
                    "Maintain original functionality logic",
                    "Code runs normally",
                ],
                tags=["python", "debug", "array"],
            ),
            TestCase(
                id="csv_processing",
                name="File Operation - Read CSV and Process",
                type=TestCaseType.FILE_OPERATION,
                difficulty=DifficultyLevel.MEDIUM,
                description="Read CSV file and perform data processing",
                prompt="Please write code to read CSV file 'data.csv', calculate average value of each column, and save results to new CSV file",
                expected_files={
                    "data.csv": "name,age,score\nAlice,25,85\nBob,30,92\nCharlie,35,78",
                },
                success_criteria=[
                    "Correctly read CSV file",
                    "Calculate average of numeric columns",
                    "Save results to new file",
                    "Handle exception cases",
                ],
                tags=["python", "csv", "data_processing"],
            ),
            TestCase(
                id="flask_project_init",
                name="Project Initialization - Flask Web Application",
                type=TestCaseType.PROJECT_SETUP,
                difficulty=DifficultyLevel.HARD,
                description="Create basic Flask web application project structure",
                prompt="Please create basic Flask web application project structure, including routes, templates and static file directories",
                expected_files={
                    "app.py": "",
                    "templates/index.html": "",
                    "static/style.css": "",
                    "requirements.txt": "",
                },
                success_criteria=[
                    "Create correct project structure",
                    "Include basic Flask application",
                    "Can run and respond to requests",
                    "Include necessary dependency files",
                ],
                tags=["python", "flask", "web", "project_setup"],
            ),
            TestCase(
                id="loop_optimization",
                name="Code Performance Optimization - Loop Optimization",
                type=TestCaseType.CODE_OPTIMIZATION,
                difficulty=DifficultyLevel.HARD,
                description="Optimize nested loop performance",
                prompt="Optimize the performance of the following code:\n\ndef find_duplicates(arr):\n    duplicates = []\n    for i in range(len(arr)):\n        for j in range(i+1, len(arr)):\n            if arr[i] == arr[j] and arr[i] not in duplicates:\n                duplicates.append(arr[i])\n    return duplicates",
                success_criteria=[
                    "Significantly improve time complexity",
                    "Maintain functional correctness",
                    "Use more efficient data structures",
                    "Provide performance analysis explanation",
                ],
                tags=["python", "optimization", "algorithm", "performance"],
            ),
        ]

        for case in sample_cases:
            self.add_test_case(case)

        logger.info(f"Created {len(sample_cases)} sample test cases")

    def export_dataset(self, export_path: str, format: str = "json") -> None:
        """Export dataset"""
        try:
            export_path = Path(export_path)

            if format == "json":
                # Export as JSON format
                dataset_data = {
                    "metadata": self.metadata,
                    "test_cases": [case.to_dict() for case in self.test_cases],
                }

                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(dataset_data, f, indent=2, ensure_ascii=False)

            elif format == "csv":
                # Export as CSV format (simplified)
                import pandas as pd

                cases_data = []
                for case in self.test_cases:
                    case_dict = case.to_dict()
                    # Flatten complex fields
                    case_dict["tags"] = ",".join(case_dict.get("tags", []))
                    case_dict["success_criteria"] = ",".join(
                        case_dict.get("success_criteria", [])
                    )
                    cases_data.append(case_dict)

                df = pd.DataFrame(cases_data)
                df.to_csv(export_path, index=False, encoding="utf-8")

            else:
                raise ValueError(f"Unsupported export format: {format}")

            logger.info(f"Dataset exported to: {export_path}")

        except Exception as e:
            logger.error(f"Failed to export dataset: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics"""
        return {
            "total_cases": len(self.test_cases),
            "cases_by_type": self.metadata.get("cases_by_type", {}),
            "cases_by_difficulty": self.metadata.get("cases_by_difficulty", {}),
            "tags": list(set(tag for case in self.test_cases for tag in case.tags)),
            "avg_success_criteria": (
                sum(len(case.success_criteria) for case in self.test_cases)
                / len(self.test_cases)
                if self.test_cases
                else 0
            ),
        }
