import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call, mock_open

from src.rag.intelligent_file_filter import IntelligentFileFilter, FileRelevance, FileClassification
from src.llms.llm import BaseLLM # Assuming BaseLLM is the base class
from src.rag.code_indexer import GitignoreParser, CodeParser, CodeChunk, FileInfo, CodeIndexer
import re
import hashlib
import os # For os.path.getmtime mock
import sqlite3 # For mocking
import tempfile # For temporary repo path if needed
from datetime import datetime


# Mock LLM to prevent actual LLM instantiation during tests
@pytest.fixture(autouse=True)
def mock_llm_instantiation():
    with patch("src.rag.intelligent_file_filter.get_llm_by_type") as mock_get_llm:
        mock_llm_instance = MagicMock(spec=BaseLLM) # Use spec for better mocking
        mock_get_llm.return_value = mock_llm_instance
        yield mock_get_llm

@pytest.fixture
def file_filter():
    # The repo_path can be any string, as Path objects will handle it.
    # Actual file operations are mocked where necessary.
    return IntelligentFileFilter(repo_path="/test_repo")

class TestIntelligentFileFilterRuleBased:

    # Test cases for _is_virtual_env_file
    @pytest.mark.parametrize("path, expected", [
        (".venv/some_file", True),
        ("my_project/.env/bin/activate", True),
        ("node_modules/package/file.js", True),
        ("__pycache__/some.pyc", True), # __pycache__ is a venv pattern
        (".pytest_cache/testfile", True),
        ("src/main.py", False),
        ("docs/config.yaml", False),
        ("ENV/bin/python", True),
        ("build/output/file", True), # build is a venv pattern
        (".idea/project.xml", True), # .idea is a venv pattern
    ])
    def test_is_virtual_env_file(self, file_filter, path, expected):
        assert file_filter._is_virtual_env_file(path) == expected

    # Test cases for _is_third_party_file
    @pytest.mark.parametrize("path, expected", [
        ("lib/python3.9/site-packages/some_lib/file.py", True),
        (".venv/lib/python3.10/site-packages/another_lib/init.py", True),
        ("vendor/external/lib.go", True), # vendor is a venv pattern, but also implies third-party in some contexts. Let's assume venv_patterns are checked first.
                                        # The current patterns have 'vendor' in venv_patterns.
                                        # If a file is venv, it might not reach third_party checks if classify_file short-circuits.
                                        # These helper methods are tested independently here.
        ("src/my_code.py", False),
        ("include/header.h", True), # include is a third_party_pattern
        ("Scripts/activate.bat", True), # Scripts is a third_party_pattern (Windows venv)
    ])
    def test_is_third_party_file(self, file_filter, path, expected):
        assert file_filter._is_third_party_file(path) == expected

    # Test cases for _is_generated_file
    @pytest.mark.parametrize("path, expected", [
        ("file.pyc", True),
        ("output.pyo", True),
        ("native.pyd", True),
        ("library.so", True),
        ("archive.egg", True),
        ("package.whl", True),
        ("poetry.lock", True),
        ("package-lock.json", True),
        ("coverage.xml", True),
        (".coverage", True),
        ("app.log", True),
        ("temp_file.tmp", True),
        ("main.py", False),
        ("README.md", False),
    ])
    def test_is_generated_file(self, file_filter, path, expected):
        assert file_filter._is_generated_file(path) == expected

    # Test cases for _detect_file_type
    @pytest.mark.parametrize("path, expected_type", [
        ("main.py", "python"),
        ("script.js", "javascript"),
        ("style.css", "css"),
        ("README.md", "markdown"),
        ("config.yaml", "yaml"),
        ("config.yml", "yaml"),
        ("data.json", "json"),
        ("Cargo.toml", "toml"),
        ("index.html", "html"),
        ("run.sh", "shell"),
        ("Dockerfile", "other"), # No specific rule for Dockerfile, falls to 'other' based on suffix
        ("image.jpg", "other"),
        ("unknown_extension.xyz", "other"),
        ("no_extension_file", "other"),
    ])
    def test_detect_file_type(self, file_filter, path, expected_type):
        assert file_filter._detect_file_type(path) == expected_type

    # Test cases for _determine_relevance
    @pytest.mark.parametrize("path, file_type, size_kb, expected_relevance", [
        ("src/main.py", "python", 50, FileRelevance.HIGH), # high_relevance_patterns for .py
        ("README.md", "markdown", 10, FileRelevance.HIGH), # high_relevance_patterns for README
        ("LICENSE", "text", 2, FileRelevance.HIGH),       # high_relevance_patterns for LICENSE
        ("requirements.txt", "text", 1, FileRelevance.HIGH), # high_relevance_patterns for requirements.txt
        ("pyproject.toml", "toml", 1, FileRelevance.HIGH), # high_relevance_patterns for pyproject.toml
        ("package.json", "json", 3, FileRelevance.HIGH),   # high_relevance_patterns for package.json
        ("Dockerfile.dev", "other", 2, FileRelevance.HIGH), # high_relevance_patterns for Dockerfile*
        ("Makefile.ci", "other", 1, FileRelevance.HIGH),   # high_relevance_patterns for Makefile
        ("my_module/code.py", "python", 20, FileRelevance.HIGH), # .py is high
        ("my_docs/config.yaml", "yaml", 5, FileRelevance.MEDIUM), # Non-root yaml is medium by type
        ("assets/image.png", "other", 500, FileRelevance.MEDIUM), # Other type, medium size
        ("data/large_dataset.csv", "other", 2048, FileRelevance.LOW), # Large file is low
        ("scripts/myscript.pl", "other", 20, FileRelevance.MEDIUM), # 'other' type, not large
    ])
    def test_determine_relevance(self, file_filter, path, file_type, size_kb, expected_relevance):
        assert file_filter._determine_relevance(path, file_type, size_kb) == expected_relevance

    # Mock for Path.stat().st_size
    def mock_path_stat(size_kb):
        mock = MagicMock(spec=Path)
        mock.stat.return_value.st_size = size_kb * 1024
        # Need to make sure the mock is returned when Path(full_path_str) is called
        # This requires patching Path constructor or specific Path instances.
        # A simpler way for classify_file is to patch `(self.repo_path / file_path).stat`
        return mock

    @patch("pathlib.Path.exists") # Mock exists for full_path.exists()
    @patch("pathlib.Path.stat") # Mock stat for full_path.stat()
    def test_classify_file_python_core(self, mock_stat, mock_exists, file_filter):
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 10 * 1024 # 10KB

        # This mock setup assumes that when `self.repo_path / file_path` is called,
        # the resulting Path object uses the global mock_stat and mock_exists.
        # This is generally true if these methods are called on the Path instance.

        classification = file_filter.classify_file("src/app/main.py")

        assert classification.path == "src/app/main.py"
        assert classification.relevance == FileRelevance.HIGH
        assert classification.file_type == "python"
        assert not classification.is_virtual_env
        assert not classification.is_third_party
        assert not classification.is_generated
        assert classification.size_kb == 10.0
        assert "核心python代码文件" in classification.reason # Check reason

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_classify_file_venv_excluded(self, mock_stat, mock_exists, file_filter):
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 1 * 1024 # 1KB

        # Path that matches a venv pattern
        file_path = ".venv/lib/python3.9/site-packages/somepackage/module.py"
        classification = file_filter.classify_file(file_path)

        assert classification.path == file_path
        assert classification.relevance == FileRelevance.EXCLUDE
        assert classification.is_virtual_env  # This path matches venv patterns like ".venv" and "site-packages"
        # Depending on pattern order and specifics, is_third_party might also be true.
        # The key is that it's EXCLUDE.
        assert "虚拟环境文件" in classification.reason or "第三方库文件" in classification.reason

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_classify_file_generated_lock_file(self, mock_stat, mock_exists, file_filter):
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 50 * 1024 # 50KB

        classification = file_filter.classify_file("poetry.lock")
        assert classification.path == "poetry.lock"
        assert classification.relevance == FileRelevance.EXCLUDE # .lock files are generated
        assert classification.is_generated
        assert "生成文件" in classification.reason
        assert classification.file_type == "other" # .lock has no specific type mapping

    @patch("src.rag.intelligent_file_filter.IntelligentFileFilter.classify_file")
    def test_batch_classify_files(self, mock_classify_file, file_filter):
        file_paths = ["file1.py", "file2.md", "file3.log"]

        # Define what classify_file should return for each path
        mock_classify_file.side_effect = [
            FileClassification("file1.py", FileRelevance.HIGH, "Python", "python", 10),
            FileClassification("file2.md", FileRelevance.MEDIUM, "Markdown", "markdown", 5),
            FileClassification("file3.log", FileRelevance.EXCLUDE, "Log file", "other", 100, is_generated=True),
        ]

        results = file_filter.batch_classify_files(file_paths)

        assert len(results) == 3
        assert results[0].path == "file1.py"
        assert results[1].relevance == FileRelevance.MEDIUM
        assert results[2].is_generated

        # Ensure classify_file was called for each path
        mock_classify_file.assert_has_calls([
            call("file1.py"),
            call("file2.md"),
            call("file3.log"),
        ])

    @patch("src.rag.intelligent_file_filter.IntelligentFileFilter.batch_classify_files")
    def test_filter_files_for_indexing_logic(self, mock_batch_classify, file_filter):
        # Setup mock return value for batch_classify_files
        mock_batch_classify.return_value = [
            FileClassification("src/main.py", FileRelevance.HIGH, "Core python", "python", 10),
            FileClassification("README.md", FileRelevance.HIGH, "Readme", "markdown", 2),
            FileClassification("config/settings.yaml", FileRelevance.MEDIUM, "Config yaml", "yaml", 1),
            FileClassification("data/large.csv", FileRelevance.LOW, "Large data", "csv", 2000),
            FileClassification(".venv/bin/activate", FileRelevance.EXCLUDE, "Venv file", "shell", 1, is_virtual_env=True),
            FileClassification("docs/notes.txt", FileRelevance.MEDIUM, "Notes", "text", 5),
            FileClassification("build/app.exe", FileRelevance.EXCLUDE, "Build artifact", "other", 5000, is_generated=True)
        ]

        input_paths = ["src/main.py", "README.md", "config/settings.yaml", "data/large.csv",
                       ".venv/bin/activate", "docs/notes.txt", "build/app.exe"]

        files_to_index, stats = file_filter.filter_files_for_indexing(input_paths)

        # HIGH and MEDIUM relevance files should be indexed
        assert "src/main.py" in files_to_index
        assert "README.md" in files_to_index
        assert "config/settings.yaml" in files_to_index
        assert "docs/notes.txt" in files_to_index

        # LOW and EXCLUDE should not be indexed
        assert "data/large.csv" not in files_to_index
        assert ".venv/bin/activate" not in files_to_index
        assert "build/app.exe" not in files_to_index

        assert len(files_to_index) == 4

        assert stats["total_files"] == len(input_paths)
        assert stats["files_to_index"] == 4
        assert stats["high_relevance"] == 2
        assert stats["medium_relevance"] == 2 # settings.yaml and notes.txt
        assert stats["low_relevance"] == 1
        assert stats["excluded"] == 2
        assert stats["exclusion_breakdown"]["virtual_env"] == 1
        assert stats["exclusion_breakdown"]["generated"] == 1
        assert stats["exclusion_breakdown"]["third_party"] == 0 # None explicitly marked as only third_party in this set

    def test_get_exclusion_reason(self, file_filter):
        assert file_filter._get_exclusion_reason(True, False, False) == "虚拟环境文件"
        assert file_filter._get_exclusion_reason(False, True, False) == "第三方库文件"
        assert file_filter._get_exclusion_reason(False, False, True) == "生成文件"
        assert file_filter._get_exclusion_reason(True, True, False) == "虚拟环境文件、第三方库文件"
        assert file_filter._get_exclusion_reason(True, True, True) == "虚拟环境文件、第三方库文件、生成文件"

    def test_get_relevance_reason(self, file_filter):
        assert file_filter._get_relevance_reason(FileRelevance.HIGH, "python") == "核心python代码文件"
        assert file_filter._get_relevance_reason(FileRelevance.MEDIUM, "yaml") == "有用的yaml配置文件"
        assert file_filter._get_relevance_reason(FileRelevance.LOW, "text") == "可选的text文件"
        assert file_filter._get_relevance_reason(FileRelevance.EXCLUDE, "other") == "应该排除"


import asyncio # Make sure this import is added if not present

class TestIntelligentFileFilterLLM:

    @pytest.fixture
    def llm_file_filter(self, mock_llm_instantiation):
        filtr = IntelligentFileFilter(repo_path="/test_repo_llm")
        # Access the mocked LLM instance if needed for assertions
        filtr.llm = mock_llm_instantiation.return_value
        return filtr

    @patch("src.rag.intelligent_file_filter.IntelligentFileFilter.batch_classify_files")
    @pytest.mark.asyncio
    async def test_llm_classify_files_no_uncertain_files(self, mock_batch_classify, llm_file_filter):
        rule_classifications = [
            FileClassification("src/main.py", FileRelevance.HIGH, "Python", "python", 10),
            FileClassification(".venv/skip.py", FileRelevance.EXCLUDE, "Venv", "python", 1)
        ]
        mock_batch_classify.return_value = rule_classifications

        results = await llm_file_filter.llm_classify_files(["src/main.py", ".venv/skip.py"])

        assert results == rule_classifications
        llm_file_filter.llm.agenerate.assert_not_called()

    @patch("src.prompts.template.apply_prompt_template")
    @patch("src.rag.intelligent_file_filter.IntelligentFileFilter.batch_classify_files")
    @pytest.mark.asyncio
    async def test_llm_classify_files_with_uncertain_files(self, mock_batch_classify, mock_apply_prompt, llm_file_filter):
        uncertain_file_path = "docs/maybe.txt"
        rule_classifications = [
            FileClassification("src/main.py", FileRelevance.HIGH, "Python", "python", 10),
            FileClassification(uncertain_file_path, FileRelevance.MEDIUM, "Medium text", "text", 5),
            FileClassification("config.json", FileRelevance.HIGH, "Config", "json", 1)
        ]
        mock_batch_classify.return_value = rule_classifications

        mock_apply_prompt.return_value = "mocked_prompt_messages"

        llm_response_str = f"{uncertain_file_path}: high, important document"
        llm_file_filter.llm.agenerate.return_value = llm_response_str

        results = await llm_file_filter.llm_classify_files(
            ["src/main.py", uncertain_file_path, "config.json"],
            task_context="testing context"
        )

        mock_batch_classify.assert_called_once()
        mock_apply_prompt.assert_called_once()
        llm_file_filter.llm.agenerate.assert_called_once_with("mocked_prompt_messages")

        assert len(results) == 3
        classified_uncertain = next(r for r in results if r.path == uncertain_file_path)
        assert classified_uncertain.relevance == FileRelevance.HIGH
        assert "LLM分类" in classified_uncertain.reason
        assert "important document" in classified_uncertain.reason # Check if LLM reason is appended

        # Check original high relevance files are untouched
        assert next(r for r in results if r.path == "src/main.py").relevance == FileRelevance.HIGH
        assert next(r for r in results if r.path == "config.json").relevance == FileRelevance.HIGH

    def test_parse_llm_classification_response(self, llm_file_filter):
        llm_response = '''
        src/file1.py: high, core logic
        data/file2.csv: low, sample data only
        docs/guide.md: exclude, not relevant for indexing
        src/file3.js: medium, ui component
        non_existent_file.java: high, important class
        '''
        original_files = [
            FileClassification("src/file1.py", FileRelevance.MEDIUM, "py", "python", 10, file_hash="hash1"),
            FileClassification("data/file2.csv", FileRelevance.MEDIUM, "csv", "csv", 100, file_hash="hash2"),
            FileClassification("docs/guide.md", FileRelevance.MEDIUM, "md", "markdown", 20, file_hash="hash3"),
            FileClassification("src/not_in_llm.py", FileRelevance.MEDIUM, "py", "python", 5, file_hash="hash4"),
            FileClassification("src/file3.js", FileRelevance.LOW, "js", "javascript", 15, file_hash="hash5")
        ]

        parsed = llm_file_filter._parse_llm_classification_response(llm_response, original_files)

        assert len(parsed) == 5 # All original files should be present

        file1 = next(p for p in parsed if p.path == "src/file1.py")
        assert file1.relevance == FileRelevance.HIGH
        assert file1.reason == "LLM分类: high, core logic" # Reason should be updated
        assert file1.file_hash == "hash1" # Other fields retained

        file2 = next(p for p in parsed if p.path == "data/file2.csv")
        assert file2.relevance == FileRelevance.LOW
        assert file2.reason == "LLM分类: low, sample data only"
        assert file2.file_hash == "hash2"

        guide = next(p for p in parsed if p.path == "docs/guide.md")
        assert guide.relevance == FileRelevance.EXCLUDE
        assert guide.reason == "LLM分类: exclude, not relevant for indexing"
        assert guide.file_hash == "hash3"

        not_in_llm = next(p for p in parsed if p.path == "src/not_in_llm.py")
        assert not_in_llm.relevance == FileRelevance.MEDIUM # Unchanged
        assert not_in_llm.reason == "py" # Original reason retained
        assert not_in_llm.file_hash == "hash4"

        file3 = next(p for p in parsed if p.path == "src/file3.js")
        assert file3.relevance == FileRelevance.MEDIUM
        assert file3.reason == "LLM分类: medium, ui component"
        assert file3.file_hash == "hash5"

        # non_existent_file.java in LLM output but not in original_files should be ignored.

    @patch("src.rag.intelligent_file_filter.logger")
    @patch("src.prompts.template.apply_prompt_template")
    @patch("src.rag.intelligent_file_filter.IntelligentFileFilter.batch_classify_files")
    @pytest.mark.asyncio
    async def test_llm_classify_files_llm_agenerate_fails(self, mock_batch_classify, mock_apply_prompt, mock_logger, llm_file_filter):
        uncertain_file_path = "docs/maybe.txt"
        rule_classifications = [
            FileClassification(uncertain_file_path, FileRelevance.MEDIUM, "Medium text", "text", 5)
        ]
        mock_batch_classify.return_value = rule_classifications
        mock_apply_prompt.return_value = "prompt"

        llm_file_filter.llm.agenerate.side_effect = Exception("LLM API error")

        results = await llm_file_filter.llm_classify_files([uncertain_file_path])

        assert len(results) == 1
        assert results[0].path == uncertain_file_path
        assert results[0].relevance == FileRelevance.MEDIUM
        mock_logger.error.assert_called_once_with("LLM文件分类失败: LLM API error")

    @patch("src.rag.intelligent_file_filter.logger")
    @patch("src.prompts.template.apply_prompt_template")
    @patch("src.rag.intelligent_file_filter.IntelligentFileFilter.batch_classify_files")
    @pytest.mark.asyncio
    async def test_llm_classify_files_llm_returns_bad_response(self, mock_batch_classify, mock_apply_prompt, mock_logger, llm_file_filter):
        uncertain_file_path = "docs/another.txt"
        rule_classifications = [
            FileClassification(uncertain_file_path, FileRelevance.MEDIUM, "Medium text", "text", 5, file_hash="hash_another")
        ]
        mock_batch_classify.return_value = rule_classifications
        mock_apply_prompt.return_value = "prompt"

        llm_file_filter.llm.agenerate.return_value = "This is not a parsable response"

        results = await llm_file_filter.llm_classify_files([uncertain_file_path])

        assert len(results) == 1
        assert results[0].relevance == FileRelevance.MEDIUM
        assert results[0].reason == "Medium text" # Original reason retained
        assert results[0].file_hash == "hash_another" # Check other fields retained

        llm_file_filter.llm.agenerate.assert_called_once()

        # Check for the debug log from _parse_llm_classification_response
        # This relies on the logger being called with a specific message format.
        # We find the call that contains the unparsable line.
        found_log = False
        for call_args in mock_logger.debug.call_args_list:
            if "解析LLM响应行失败: This is not a parsable response" in call_args[0][0]:
                found_log = True
                break
        assert found_log, "Expected debug log for unparsable LLM response not found."

    def test_parse_llm_classification_response_empty_and_malformed_lines(self, llm_file_filter):
        llm_response = """
        src/app.py: high, main application

          src/utils.py : medium, utility functions
        tests/test_app.py:high, unit tests for app
        malformed_line_no_colon
        another_malformed: relevance_only
        config.json:low:too_many_colons
        """
        original_files = [
            FileClassification("src/app.py", FileRelevance.MEDIUM, "py", "python", 20),
            FileClassification("src/utils.py", FileRelevance.MEDIUM, "py", "python", 10),
            FileClassification("tests/test_app.py", FileRelevance.MEDIUM, "py", "python", 15),
            FileClassification("config.json", FileRelevance.HIGH, "json", "json", 2),
        ]

        with patch("src.rag.intelligent_file_filter.logger") as mock_logger:
            parsed = llm_file_filter._parse_llm_classification_response(llm_response, original_files)

            assert len(parsed) == 4

            app_py = next(f for f in parsed if f.path == "src/app.py")
            assert app_py.relevance == FileRelevance.HIGH
            assert app_py.reason == "LLM分类: high, main application"

            utils_py = next(f for f in parsed if f.path == "src/utils.py")
            assert utils_py.relevance == FileRelevance.MEDIUM # Path had spaces, should be stripped
            assert utils_py.reason == "LLM分类: medium, utility functions"

            test_app_py = next(f for f in parsed if f.path == "tests/test_app.py")
            assert test_app_py.relevance == FileRelevance.HIGH # Path had no spaces, relevance had no spaces
            assert test_app_py.reason == "LLM分类: high, unit tests for app"


            config_json = next(f for f in parsed if f.path == "config.json")
            assert config_json.relevance == FileRelevance.LOW # Parsed correctly despite extra colons in reason
            assert config_json.reason == "LLM分类: low:too_many_colons"


            # Check that errors were logged for malformed lines
            expected_log_messages = [
                "解析LLM响应行失败: malformed_line_no_colon",
                "解析LLM响应行失败: another_malformed: relevance_only"
            ]

            actual_log_messages = [call_args[0][0] for call_args in mock_logger.debug.call_args_list]
            for msg in expected_log_messages:
                assert any(msg in actual_msg for actual_msg in actual_log_messages)

    @patch("src.prompts.template.apply_prompt_template")
    @patch("src.rag.intelligent_file_filter.IntelligentFileFilter.batch_classify_files")
    @pytest.mark.asyncio
    async def test_llm_classify_files_uses_task_context(self, mock_batch_classify, mock_apply_prompt, llm_file_filter):
        uncertain_file_path = "docs/context_test.txt"
        rule_classifications = [
            FileClassification(uncertain_file_path, FileRelevance.MEDIUM, "Medium text", "text", 5)
        ]
        mock_batch_classify.return_value = rule_classifications
        mock_apply_prompt.return_value = "prompt_with_context"
        llm_file_filter.llm.agenerate.return_value = f"{uncertain_file_path}: high, relevant due to context"

        custom_context = "This is a special coding task."
        await llm_file_filter.llm_classify_files([uncertain_file_path], task_context=custom_context)

        # Verify apply_prompt_template was called with the task_context
        # The call is apply_prompt_template(template_name, variables)
        # We need to check the 'variables' dict passed to it.
        args, kwargs = mock_apply_prompt.call_args
        assert "task_context" in kwargs["variables"]
        assert kwargs["variables"]["task_context"] == custom_context
        llm_file_filter.llm.agenerate.assert_called_once_with("prompt_with_context")


class TestGitignoreParser:
    @patch("pathlib.Path.exists")
    def test_init_no_gitignore_file(self, mock_path_exists):
        mock_path_exists.return_value = False
        parser = GitignoreParser(repo_path="/fake_repo_no_gitignore")
        assert len(parser.ignore_patterns) == 0

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_gitignore_basic(self, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True # .gitignore exists
        gitignore_content = """
        # This is a comment
        *.log
        build/
        !important.log
        /docs_root_only/
        """
        mock_file_open.return_value.readlines.return_value = gitignore_content.splitlines()

        parser = GitignoreParser(repo_path="/fake_repo")

        # Expect 4 patterns (comment is skipped, empty lines are skipped)
        assert len(parser.ignore_patterns) == 4
        originals = [p["original"] for p in parser.ignore_patterns]
        assert "*.log" in originals
        assert "build/" in originals
        assert "!important.log" in originals
        assert "/docs_root_only/" in originals

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_gitignore_empty(self, mock_file_open, mock_path_exists):
        mock_path_exists.return_value = True
        mock_file_open.return_value.readlines.return_value = []
        parser = GitignoreParser(repo_path="/fake_repo_empty_gitignore")
        assert len(parser.ignore_patterns) == 0

    # Test _convert_to_regex indirectly via is_ignored, which is more practical.
    # Direct testing of regex strings can be brittle.

    def test_is_ignored_functionality(self):
        parser = GitignoreParser(repo_path="/test_repo") # repo_path doesn't matter here
        # Manually set patterns for testing
        # Based on how GitignoreParser processes them (stripping, etc.)
        # GitignoreParser._convert_to_regex is the key internal function
        parser.ignore_patterns = [
            parser._convert_to_regex("*.log"),          # Matches .log files
            parser._convert_to_regex("build/"),         # Matches files under build/ directory
            parser._convert_to_regex("!important.log"), # Negation
            parser._convert_to_regex("docs/*.md"),      # Specific md files in docs
            parser._convert_to_regex("!docs/keep.md"),  # Negation within a directory
            parser._convert_to_regex("/root_file.txt"), # Matches only at root
            parser._convert_to_regex("dir_pattern/"),   # Matches dir_pattern/ and its contents
            parser._convert_to_regex("**/temp/"),       # Matches temp directory anywhere
            parser._convert_to_regex("file?.txt")       # Matches fileA.txt, file1.txt etc.
        ]

        # Basic ignore
        assert parser.is_ignored("error.log") == True
        assert parser.is_ignored("src/error.log") == True

        # Directory ignore
        assert parser.is_ignored("build/app.exe") == True
        assert parser.is_ignored("build/subdir/file.c") == True

        # Negation
        assert parser.is_ignored("important.log") == False
        assert parser.is_ignored("src/important.log") == False # Negation applies to any matching path

        # Wildcard and specific directory
        assert parser.is_ignored("docs/guide.md") == True
        assert parser.is_ignored("docs/another.txt") == False
        assert parser.is_ignored("other/docs/guide.md") == True # *.md part is global if not anchored

        # Negation within directory
        assert parser.is_ignored("docs/keep.md") == False

        # Root file ignore
        assert parser.is_ignored("root_file.txt") == True
        assert parser.is_ignored("src/root_file.txt") == False

        # dir_pattern/
        assert parser.is_ignored("dir_pattern/some_file.txt") == True
        assert parser.is_ignored("dir_pattern/sub_dir/another_file.py") == True
        assert parser.is_ignored("other_dir_pattern/file.txt") == False

        # **/temp/
        assert parser.is_ignored("temp/file.txt") == True
        assert parser.is_ignored("src/temp/file.txt") == True
        assert parser.is_ignored("src/sub/temp/file.txt") == True

        # file?.txt
        assert parser.is_ignored("fileA.txt") == True
        assert parser.is_ignored("file1.txt") == True
        assert parser.is_ignored("fileLong.txt") == False

        # Not ignored
        assert parser.is_ignored("src/main.py") == False
        assert parser.is_ignored("README.md") == False


class TestCodeParser:
    @pytest.fixture
    def code_parser(self):
        return CodeParser()

    @pytest.mark.parametrize("filename, expected_lang", [
        ("test.py", "python"), ("script.js", "javascript"), ("style.css", "css"),
        ("index.html", "html"), ("README.md", "markdown"), ("config.yaml", "yaml"),
        ("main.c", "c"), ("service.go", "go"), ("App.java", "java"), ("lib.rs", "rust"),
        ("archive.zip", "binary"), ("image.jpg", "binary"), ("data.bin", "binary"),
        ("unknown.xyz", "text"), ("NO_EXTENSION", "text"), ("Makefile", "makefile"),
        ("Dockerfile", "dockerfile"), (".bashrc", "shell"), ("script.sh", "shell"),
        ("TEST.CPP", "cpp"), ("Test.Py", "python") # Case-insensitivity for extension
    ])
    def test_get_language(self, code_parser, filename, expected_lang):
        assert code_parser.get_language(filename) == expected_lang

    @patch("os.path.getmtime", return_value=1678886400.0) # Mock timestamp
    def test_parse_python_file_basic(self, mock_getmtime, code_parser):
        file_path = "example.py"
        content = """
import os
import sys

class MyClass:
    \"\"\"A simple class\"\"\"
    def __init__(self, name):
        self.name = name

    def method(self, x):
        \"\"\"A simple method\"\"\"
        return x * 2

def my_function(a, b):
    \"\"\"A test function\"\"\"
    # A comment inside function
    return a + b

# Global variable
global_var = 100
"""
        file_info, chunks = code_parser.parse_python_file(file_path, content)

        assert file_info.path == file_path
        assert file_info.language == "python"
        assert file_info.size == len(content)
        assert "os" in file_info.imports
        assert "sys" in file_info.imports
        assert "MyClass" in file_info.exports # Classes are exports
        assert "my_function" in file_info.exports # Functions are exports
        assert file_info.hash_value == hashlib.md5(content.encode()).hexdigest()
        assert file_info.last_modified == 1678886400.0

        assert len(chunks) == 2 # MyClass, my_function. __init__ and method are part of MyClass chunk.

        class_chunk = next(c for c in chunks if c.name == "MyClass")
        assert class_chunk.chunk_type == "class"
        assert class_chunk.name == "MyClass"
        assert "A simple class" in class_chunk.docstring
        assert "def __init__(self, name):" in class_chunk.content
        assert "def method(self, x):" in class_chunk.content
        assert class_chunk.start_line == 4 # Line numbers are 1-based
        assert class_chunk.end_line == 11

        func_chunk = next(c for c in chunks if c.name == "my_function")
        assert func_chunk.chunk_type == "function"
        assert func_chunk.name == "my_function"
        assert "A test function" in func_chunk.docstring
        assert func_chunk.start_line == 13
        assert func_chunk.end_line == 16
        assert "# A comment inside function" in func_chunk.content

    @patch("src.rag.code_indexer.logger")
    @patch("os.path.getmtime", return_value=1678886400.0)
    def test_parse_python_file_syntax_error(self, mock_getmtime, mock_logger, code_parser):
        file_path = "bad_syntax.py"
        content = "def my_func( : pass" # Invalid syntax

        file_info, chunks = code_parser.parse_python_file(file_path, content)

        assert file_info is not None
        assert file_info.path == file_path
        assert file_info.language == "python"
        assert file_info.size == len(content)
        assert file_info.hash_value == hashlib.md5(content.encode()).hexdigest()
        assert len(chunks) == 1 # Should produce one large chunk of the whole file
        assert chunks[0].content == content
        assert chunks[0].chunk_type == "code_block" # Fallback chunk type
        mock_logger.warning.assert_called_once()
        assert f"Syntax error parsing Python file: {file_path}" in mock_logger.warning.call_args[0][0]


    def test_split_file_into_chunks(self, code_parser):
        file_path = "large_file.txt"
        # Content with 10 lines, each line is "Line X\n" (7 chars) or "Line 10\n" (8 chars)
        # Total size = 6*7 + 3*7 + 8 = 42 + 21 + 8 = 71 bytes. Let's make it simpler.
        line_content = "This is a line of text.\n" # 25 bytes
        num_lines = 10
        content = line_content * num_lines # 250 bytes

        # Test with chunk_size smaller than total content
        chunks_small_size = code_parser._split_file_into_chunks(file_path, content, "text", chunk_size=100)
        assert len(chunks_small_size) == 3 # 250 / 100 = 2.5 -> 3 chunks
        assert chunks_small_size[0].content == line_content * 4 # 4 lines = 100 bytes
        assert chunks_small_size[0].start_line == 1
        assert chunks_small_size[0].end_line == 4
        assert chunks_small_size[1].content == line_content * 4 # Next 4 lines
        assert chunks_small_size[1].start_line == 5
        assert chunks_small_size[1].end_line == 8
        assert chunks_small_size[2].content == line_content * 2 # Remaining 2 lines
        assert chunks_small_size[2].start_line == 9
        assert chunks_small_size[2].end_line == 10

        # Test with chunk_size larger than total content
        chunks_large_size = code_parser._split_file_into_chunks(file_path, content, "text", chunk_size=500)
        assert len(chunks_large_size) == 1
        assert chunks_large_size[0].content == content
        assert chunks_large_size[0].start_line == 1
        assert chunks_large_size[0].end_line == 10

        # Test with content that doesn't end with newline
        content_no_final_newline = (line_content * 2).strip() # 2 lines, no final newline
        chunks_no_newline = code_parser._split_file_into_chunks(file_path, content_no_final_newline, "text", chunk_size=30)
        assert len(chunks_no_newline) == 2
        assert chunks_no_newline[0].content == line_content.strip() # First line
        assert chunks_no_newline[1].content == line_content.strip() # Second line

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.getmtime", return_value=1678886400.0)
    @patch.object(CodeParser, 'parse_python_file')
    def test_parse_file_python(self, mock_parse_python, mock_getmtime, mock_file_open, code_parser):
        file_path = "main.py"
        content = "print('hello')"
        mock_file_open.return_value.read.return_value = content

        # Let parse_python_file return dummy values
        dummy_file_info = FileInfo(path=file_path, language="python", size=len(content), hash_value="dummyhash")
        dummy_chunks = [CodeChunk(file_path=file_path, content=content, chunk_type="code_block", start_line=1, end_line=1)]
        mock_parse_python.return_value = (dummy_file_info, dummy_chunks)

        file_info, chunks = code_parser.parse_file(file_path)

        mock_file_open.assert_called_once_with(Path(file_path), 'r', encoding='utf-8', errors='ignore')
        mock_parse_python.assert_called_once_with(file_path, content)
        assert file_info == dummy_file_info
        assert chunks == dummy_chunks

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.getmtime", return_value=1678886400.0)
    @patch.object(CodeParser, '_split_file_into_chunks')
    def test_parse_file_non_python(self, mock_split_chunks, mock_getmtime, mock_file_open, code_parser):
        file_path = "README.md"
        content = "# Hello World"
        mock_file_open.return_value.read.return_value = content

        dummy_chunks = [CodeChunk(file_path=file_path, content=content, chunk_type="code_block", start_line=1, end_line=1)]
        mock_split_chunks.return_value = dummy_chunks

        file_info, chunks = code_parser.parse_file(file_path)

        mock_file_open.assert_called_once_with(Path(file_path), 'r', encoding='utf-8', errors='ignore')
        mock_split_chunks.assert_called_once_with(file_path, content, "markdown", chunk_size=500)

        assert file_info.path == file_path
        assert file_info.language == "markdown"
        assert file_info.size == len(content)
        assert file_info.hash_value == hashlib.md5(content.encode()).hexdigest()
        assert file_info.last_modified == 1678886400.0
        assert chunks == dummy_chunks

    @patch("src.rag.code_indexer.logger")
    @patch("os.path.getmtime", return_value=1678886400.0)
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_file_unicode_decode_error_fallback(self, mock_file_open, mock_getmtime, mock_logger, code_parser):
        file_path = "gbk_encoded.txt"
        gbk_content_bytes = "你好世界".encode('gbk') # Content that would fail utf-8

        # First attempt utf-8 (raises UnicodeDecodeError), then gbk
        mock_file_open.side_effect = [
            MagicMock(read=MagicMock(side_effect=UnicodeDecodeError('utf-8', b'', 0, 0, 'reason'))), # First open (utf-8)
            MagicMock(read=MagicMock(return_value=gbk_content_bytes.decode('gbk')))  # Second open (gbk)
        ]

        file_info, chunks = code_parser.parse_file(file_path)

        assert file_info is not None
        assert file_info.language == "text" # Assuming .txt
        assert file_info.size == len(gbk_content_bytes.decode('gbk')) # Size of successfully decoded content
        assert len(chunks) == 1
        assert chunks[0].content == "你好世界"

        mock_logger.warning.assert_called_once()
        assert f"Failed to decode {file_path} with UTF-8, trying GBK." in mock_logger.warning.call_args[0][0]

        # Check open calls: Path(file_path) for both attempts
        expected_calls = [
            call(Path(file_path), 'r', encoding='utf-8', errors='ignore'),
            call(Path(file_path), 'r', encoding='gbk', errors='ignore')
        ]
        mock_file_open.assert_has_calls(expected_calls)


    @patch("src.rag.code_indexer.logger")
    @patch("os.path.getmtime", return_value=1678886400.0)
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_file_unicode_decode_error_all_fail(self, mock_file_open, mock_getmtime, mock_logger, code_parser):
        file_path = "bad_encoding.txt"

        # Both UTF-8 and GBK attempts fail
        mock_file_open.side_effect = [
            MagicMock(read=MagicMock(side_effect=UnicodeDecodeError('utf-8', b'', 0, 0, 'reason'))),
            MagicMock(read=MagicMock(side_effect=UnicodeDecodeError('gbk', b'', 0, 0, 'reason')))
        ]

        file_info, chunks = code_parser.parse_file(file_path)

        assert file_info is None # Should return None, None on total failure
        assert chunks is None

        assert mock_logger.warning.call_count == 2 # One for utf-8, one for gbk
        assert f"Failed to decode {file_path} with UTF-8, trying GBK." in mock_logger.warning.call_args_list[0][0][0]
        assert f"Failed to decode {file_path} with GBK after UTF-8 failure." in mock_logger.warning.call_args_list[1][0][0]

    @patch("os.path.getmtime", return_value=1678886400.0)
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_file_binary_file(self, mock_file, mock_getmtime, code_parser):
        file_path = "image.jpg" # Identified as binary by get_language
        # For binary, parse_file should not attempt to read content for chunking
        # It should just create FileInfo.

        # mock_file shouldn't be called to .read() for binary files by parse_file's logic
        # CodeParser.get_language identifies it as binary, then parse_file skips reading.

        file_info, chunks = code_parser.parse_file(file_path)

        assert file_info.path == file_path
        assert file_info.language == "binary"
        assert file_info.size == 0 # Size is not determined if not read
        assert file_info.hash_value is None # Hash is not calculated if not read
        assert file_info.last_modified == 1678886400.0
        assert len(chunks) == 0

        mock_file.assert_not_called() # open().read() should not be called

    @patch("os.path.getmtime", return_value=1678886400.0) # Mock timestamp
    def test_parse_python_file_empty_content(self, mock_getmtime, code_parser):
        file_path = "empty.py"
        content = ""
        file_info, chunks = code_parser.parse_python_file(file_path, content)

        assert file_info.path == file_path
        assert file_info.language == "python"
        assert file_info.size == 0
        assert len(file_info.imports) == 0
        assert len(file_info.exports) == 0
        assert file_info.hash_value == hashlib.md5(b"").hexdigest()
        assert len(chunks) == 1 # parse_python_file creates a single chunk for empty/unparsable files
        assert chunks[0].content == ""
        assert chunks[0].chunk_type == "code_block"

    def test_split_file_into_chunks_empty_content(self, code_parser):
        file_path = "empty.txt"
        content = ""
        chunks = code_parser._split_file_into_chunks(file_path, content, "text", chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0].content == ""
        assert chunks[0].start_line == 1
        assert chunks[0].end_line == 1 # Or 0, depending on convention for empty. Current code: 1,1

    @patch("os.path.getmtime", return_value=1678886400.0) # Mock timestamp
    def test_parse_python_file_with_docstrings_only(self, mock_getmtime, code_parser):
        file_path = "docstring_only.py"
        content = """
\"\"\"Module docstring.\"\"\"

class MyClass:
    \"\"\"Class docstring only.\"\"\"
    pass

def my_function():
    \"\"\"Function docstring only.\"\"\"
    pass
"""
        file_info, chunks = code_parser.parse_python_file(file_path, content)

        assert file_info.path == file_path
        assert "MyClass" in file_info.exports
        assert "my_function" in file_info.exports
        assert len(chunks) == 2

        class_chunk = next(c for c in chunks if c.name == "MyClass")
        assert class_chunk.docstring.strip() == "Class docstring only."
        assert "pass" in class_chunk.content

        func_chunk = next(c for c in chunks if c.name == "my_function")
        assert func_chunk.docstring.strip() == "Function docstring only."
        assert "pass" in func_chunk.content

        # Module docstring is not captured as a separate chunk by current logic
        # but is part of the overall file content.
        # Exports should still be identified.

@pytest.fixture
def mock_db_cursor():
    cursor = MagicMock(spec=sqlite3.Cursor)
    cursor.fetchone.return_value = None # Default for SELECT
    cursor.fetchall.return_value = []   # Default for SELECT
    return cursor

@pytest.fixture
def mock_db_conn(mock_db_cursor):
    conn = MagicMock(spec=sqlite3.Connection)
    conn.cursor.return_value = mock_db_cursor
    return conn

@pytest.fixture
def mock_code_parser_instance():
    parser = MagicMock(spec=CodeParser)
    # Setup default return values if needed, e.g., for parse_file
    # Default: no info, no chunks. Path.exists() in index_file needs to be True for parse_file to be called.
    # So, ensure file_info has a path for the _is_file_updated check.
    mock_file_info = FileInfo(path="default.py", language="python", size=0, last_modified=datetime.now(), hash_value="defaulthash")
    parser.parse_file.return_value = (mock_file_info, [])
    return parser

@pytest.fixture
def mock_gitignore_parser_instance():
    parser = MagicMock(spec=GitignoreParser)
    parser.is_ignored.return_value = False # Default: not ignored
    return parser

@pytest.fixture
def mock_intelligent_file_filter_instance():
    filtr = MagicMock(spec=IntelligentFileFilter)
    filtr.filter_files_for_indexing.side_effect = lambda paths,task_context: (paths, {}) # Default: pass through (added task_context)
    async def default_llm_classify(paths, task_context): # ensure async def
        return [MagicMock(path=p, relevance=FileRelevance.HIGH) for p in paths]
    filtr.llm_classify_files.side_effect = default_llm_classify # Default: all high
    return filtr

@pytest.fixture
def code_indexer_fixture(mock_db_conn, mock_code_parser_instance, mock_gitignore_parser_instance, mock_intelligent_file_filter_instance):
    with patch("sqlite3.connect", return_value=mock_db_conn) as mock_connect, \
         patch("src.rag.code_indexer.CodeParser", return_value=mock_code_parser_instance) as mock_code_parser_cls, \
         patch("src.rag.code_indexer.GitignoreParser", return_value=mock_gitignore_parser_instance) as mock_gitignore_parser_cls, \
         patch("src.rag.code_indexer.IntelligentFileFilter", return_value=mock_intelligent_file_filter_instance) as mock_iff_cls, \
         patch("os.makedirs") as mock_makedirs:

        with tempfile.TemporaryDirectory() as tmpdir:
            # Make db_path a child of tmpdir to ensure it's cleaned up.
            db_path = Path(tmpdir) / "db" / "test.db"
            # os.makedirs in CodeIndexer creates db_path.parent if it doesn't exist.
            # We need to mock os.makedirs for db_path.parent specifically if it's different from repo_path.
            # The current mock_makedirs is general. Let's adjust it.

            # Simulate os.makedirs behavior for the db_path's parent directory
            def makedirs_side_effect(path, exist_ok=False):
                if str(path) == str(db_path.parent): # only mock for db_path.parent
                    return None
                raise FileNotFoundError # Or some other error for unexpected calls
            mock_makedirs.side_effect = makedirs_side_effect

            indexer = CodeIndexer(repo_path=tmpdir, db_path=str(db_path), use_intelligent_filter=True)

            yield indexer, {
                "db_conn": mock_db_conn, "db_cursor": mock_db_conn.cursor(),
                "connect": mock_connect, "makedirs": mock_makedirs, "db_path_parent": db_path.parent,
                "CodeParser_cls": mock_code_parser_cls, "GitignoreParser_cls": mock_gitignore_parser_cls,
                "IntelligentFileFilter_cls": mock_iff_cls,
                "code_parser_inst": mock_code_parser_instance,
                "gitignore_parser_inst": mock_gitignore_parser_instance,
                "intelligent_filter_inst": mock_intelligent_file_filter_instance,
                "repo_path": tmpdir, "db_path": str(db_path)
            }

class TestCodeIndexer:
    def test_init(self, code_indexer_fixture):
        indexer, mocks = code_indexer_fixture
        mocks["connect"].assert_called_once_with(mocks["db_path"])
        # Check that makedirs was called for the parent directory of the db_path
        mocks["makedirs"].assert_called_once_with(mocks["db_path_parent"], exist_ok=True)

        assert any("CREATE TABLE IF NOT EXISTS files" in call_args[0][0] for call_args in mocks["db_cursor"].execute.call_args_list)
        assert any("CREATE TABLE IF NOT EXISTS code_chunks" in call_args[0][0] for call_args in mocks["db_cursor"].execute.call_args_list)

        mocks["CodeParser_cls"].assert_called_once()
        mocks["GitignoreParser_cls"].assert_called_once_with(Path(indexer.repo_path)) # repo_path is Path obj in CodeIndexer
        mocks["IntelligentFileFilter_cls"].assert_called_once_with(Path(indexer.repo_path)) # same here

    def test_init_no_intelligent_filter(self, mock_db_conn):
         with patch("sqlite3.connect", return_value=mock_db_conn), \
              patch("src.rag.code_indexer.CodeParser"), \
              patch("src.rag.code_indexer.GitignoreParser"), \
              patch("src.rag.code_indexer.IntelligentFileFilter") as mock_iff_cls, \
              patch("os.makedirs"):
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test.db"
                CodeIndexer(repo_path=tmpdir, db_path=str(db_path), use_intelligent_filter=False)
                mock_iff_cls.assert_not_called()

    def test_should_include_file(self, code_indexer_fixture):
        indexer, _ = code_indexer_fixture
        # Test default include_extensions
        assert indexer._should_include_file(Path("main.py")) == True
        assert indexer._should_include_file(Path("script.js")) == True
        # Test include_config_files (names)
        assert indexer._should_include_file(Path("README.md")) == True
        assert indexer._should_include_file(Path("Dockerfile")) == True
        assert indexer._should_include_file(Path("Makefile")) == True
        # Test not included
        assert indexer._should_include_file(Path("image.png")) == False
        assert indexer._should_include_file(Path("custom_config")) == False
        assert indexer._should_include_file(Path("archive.zip")) == False # In default exclude_extensions

    def test_should_exclude_path(self, code_indexer_fixture):
        indexer, mocks = code_indexer_fixture
        repo_path_obj = Path(indexer.repo_path) # CodeIndexer uses Path objects internally

        mocks["gitignore_parser_inst"].is_ignored.return_value = True
        assert indexer.should_exclude_path(repo_path_obj / "ignored_by_git.txt") == True
        # GitignoreParser is called with relative path string
        mocks["gitignore_parser_inst"].is_ignored.assert_called_once_with(str(Path("ignored_by_git.txt")))
        mocks["gitignore_parser_inst"].is_ignored.reset_mock()

        mocks["gitignore_parser_inst"].is_ignored.return_value = False # Reset for other tests
        assert indexer.should_exclude_path(repo_path_obj / ".git" / "config") == True
        assert indexer.should_exclude_path(repo_path_obj / "node_modules" / "lib" / "file.js") == True
        assert indexer.should_exclude_path(repo_path_obj / "dist" / "bundle.js") == True # Common build output

        assert indexer.should_exclude_path(repo_path_obj / "file.exe") == True
        assert indexer.should_exclude_path(repo_path_obj / "archive.zip") == True

        assert indexer.should_exclude_path(repo_path_obj / "src" / "main.py") == False


    @patch("src.rag.code_indexer.logger") # Assuming logger is used in scan_repository
    @patch("os.walk")
    def test_scan_repository_basic_filtering(self, mock_os_walk, mock_logger, code_indexer_fixture):
        indexer, mocks = code_indexer_fixture
        indexer.use_intelligent_filter = False
        repo_path_str = str(indexer.repo_path)

        mock_os_walk.return_value = [
            (repo_path_str, ["src", ".git", "docs"], ["README.md", "file.exe", "config.json"]),
            (str(Path(repo_path_str) / "src"), [], ["main.py", "helper.pyc"]),
            (str(Path(repo_path_str) / ".git"), [], ["config"]),
            (str(Path(repo_path_str) / "docs"), ["images"], ["guide.md", "project.yaml"]),
            (str(Path(repo_path_str) / "docs" / "images"), [], ["logo.png"]),
        ]

        mocks["gitignore_parser_inst"].is_ignored.side_effect = lambda p: p == "docs/project.yaml" # Ignore one file

        files = indexer.scan_repository()

        # Expected files: README.md, config.json, src/main.py, docs/guide.md
        # Excluded: file.exe (ext), src/helper.pyc (ext), .git/* (dir), docs/project.yaml (gitignore), docs/images/* (ext)

        assert "README.md" in files
        assert "config.json" in files # Assumed to be in include_config_files
        assert str(Path("src") / "main.py") in files
        assert str(Path("docs") / "guide.md") in files # .md is in include_extensions

        assert "file.exe" not in files
        assert str(Path("src") / "helper.pyc") not in files
        assert str(Path(".git") / "config") not in files # .git dir itself is excluded
        assert str(Path("docs") / "project.yaml") not in files # Ignored by gitignore mock
        assert str(Path("docs") / "images" / "logo.png") not in files # .png is not in include_extensions

        # Check logging calls (example)
        assert mock_logger.info.called # Should log scan start/end
        # Could check for specific debug logs of excluded files if they are implemented
        # e.g. mock_logger.debug.assert_any_call(f"Excluding by extension: file.exe")


    @patch("src.rag.code_indexer.logger")
    @patch("os.walk")
    @pytest.mark.asyncio
    async def test_scan_repository_intelligent_flow(self, mock_os_walk, mock_logger, code_indexer_fixture):
        indexer, mocks = code_indexer_fixture
        indexer.use_intelligent_filter = True
        repo_path_str = str(indexer.repo_path)

        # Files that would be selected by basic scan before intelligent filter
        initial_scan_paths = [
            "README.md",
            str(Path("src") / "main.py"),
            "config.yaml" # Assuming .yaml is in include_extensions or include_config_files
        ]

        mock_os_walk.return_value = [
            (repo_path_str, ["src"], ["README.md", "config.yaml", "data.log"]), # data.log excluded by extension
            (str(Path(repo_path_str) / "src"), [], ["main.py", "temp.tmp"]), # temp.tmp excluded by extension
        ]
        mocks["gitignore_parser_inst"].is_ignored.return_value = False

        async def mock_llm_classify_side_effect(paths, task_context):
            # Ensure that paths passed to llm_classify_files are the ones from initial scan
            assert set(paths) == set(initial_scan_paths)
            classifications = []
            for p in paths:
                if p == "config.yaml":
                    classifications.append(FileClassification(path=p, relevance=FileRelevance.MEDIUM, reason="", file_type="yaml", size_kb=1))
                elif p == str(Path("src") / "main.py"):
                     classifications.append(FileClassification(path=p, relevance=FileRelevance.HIGH, reason="", file_type="python", size_kb=2))
                else: # README.md
                    classifications.append(FileClassification(path=p, relevance=FileRelevance.HIGH, reason="", file_type="markdown", size_kb=1))
            return classifications

        mocks["intelligent_filter_inst"].llm_classify_files.side_effect = mock_llm_classify_side_effect

        # The filter_files_for_indexing mock needs to be more realistic based on llm_classify_files output
        def mock_filter_for_indexing(paths, task_context): # The paths here are the initial scan result
            # This mock will be called by scan_repository_intelligent *before* llm_classify_files in the current CodeIndexer logic
            # So, it should return the files that are candidates for LLM classification
            # Let's assume all initial_scan_paths are candidates.
            return paths, {"total_files": len(paths)}

        mocks["intelligent_filter_inst"].filter_files_for_indexing.side_effect = mock_filter_for_indexing


        final_files_to_index = await indexer.scan_repository_intelligent(task_context="test_context")

        # filter_files_for_indexing is called first with all files from os.walk that pass basic checks
        # Then, its output (first element of tuple) is passed to llm_classify_files
        # Then, results of llm_classify_files are filtered by relevance

        # Check that filter_files_for_indexing was called correctly
        # Its input `paths` should be what os.walk yields after basic should_exclude/should_include checks
        # Its output becomes the input to llm_classify_files
        # This is a bit convoluted to test perfectly without knowing exact implementation details of scan_repository_intelligent
        # The current test setup implies scan_repository_intelligent calls filter_files_for_indexing, then llm_classify_files.
        # Let's refine this based on the typical flow:
        # 1. os.walk + basic filtering (should_exclude_path, _should_include_file) -> candidate_paths
        # 2. filter_files_for_indexing(candidate_paths) -> rule_based_to_index, stats (if not using LLM for all) OR all candidates if LLM is to re-evaluate.
        #    The provided mock for filter_files_for_indexing is a simple pass-through.
        # 3. llm_classify_files(output_from_filter_files_for_indexing) -> llm_classifications
        # 4. Final selection based on llm_classifications relevance.

        # With the provided mocks:
        # 1. os.walk -> README.md, config.yaml, src/main.py (data.log, temp.tmp excluded by ext)
        # 2. filter_files_for_indexing (mock) receives these 3, passes them all through.
        # 3. llm_classify_files (mock) receives these 3, classifies them as per its side_effect.
        # 4. Final selection based on relevance (HIGH, MEDIUM)

        mocks["intelligent_filter_inst"].filter_files_for_indexing.assert_called_once()
        # The argument to filter_files_for_indexing should be the set of files from os.walk after basic filtering
        args_filter, _ = mocks["intelligent_filter_inst"].filter_files_for_indexing.call_args
        assert set(args_filter[0]) == set(initial_scan_paths)

        mocks["intelligent_filter_inst"].llm_classify_files.assert_called_once()
        args_llm, kwargs_llm = mocks["intelligent_filter_inst"].llm_classify_files.call_args
        assert set(args_llm[0]) == set(initial_scan_paths) # Input to llm_classify is output of filter_files_for_indexing
        assert kwargs_llm["task_context"] == "test_context"

        assert set(final_files_to_index) == {"README.md", str(Path("src")/"main.py"), "config.yaml"} # All are HIGH or MEDIUM

    @patch("src.rag.code_indexer.logger")
    @patch("pathlib.Path.exists")
    def test_index_file_new_file(self, mock_path_exists, mock_logger, code_indexer_fixture):
        indexer, mocks = code_indexer_fixture
        file_path_str = "new_file.py"

        # Mock Path(self.repo_path / file_path).exists()
        # This is tricky because Path is used multiple times. Need to mock the specific instance or its methods.
        # Let's assume self.repo_path is a string in the test, and Path(self.repo_path) / file_path_str is used.
        # The Path object itself comes from indexer.repo_path which is a real temp path.
        # So (indexer.repo_path / file_path_str).exists() will actually check FS.
        # We need to ensure the mock for Path.exists is effective for the path being checked.
        # A more robust way is to mock the Path object that `indexer.repo_path / file_path_str` resolves to.
        # However, `mock_path_exists` is a global patch on `pathlib.Path.exists`.
        mock_path_exists.return_value = True # File exists on disk

        current_time = datetime.now()
        mock_file_info = FileInfo(path=file_path_str, language="python", size=100, last_modified=current_time, hash_value="newhash")
        mock_chunks = [CodeChunk(file_path=file_path_str, content="pass", chunk_type="code_block", start_line=1, end_line=1)]

        mocks["code_parser_inst"].parse_file.return_value = (mock_file_info, mock_chunks)

        # _is_file_updated: first checks DB (fetchone returns None for new file), then file system.
        mocks["db_cursor"].fetchone.return_value = None # Simulate new file (not in DB)

        result = indexer.index_file(file_path_str)
        assert result == True

        mocks["code_parser_inst"].parse_file.assert_called_once_with(Path(indexer.repo_path) / file_path_str)

        # _is_file_updated checks DB
        sql_check_file = "SELECT hash, last_modified FROM files WHERE path = ?"
        mocks["db_cursor"].execute.assert_any_call(sql_check_file, (file_path_str,))

        # _store_file_info call
        sql_insert_file = "INSERT OR REPLACE INTO files (path, language, size, hash, last_modified, summary, avg_chunk_size, num_chunks) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        mocks["db_cursor"].execute.assert_any_call(sql_insert_file,
            (file_path_str, "python", 100, "newhash", mock_file_info.last_modified_ts, None, 4, 1) # Assuming summary None, avg_chunk_size, num_chunks
        )

        # _store_code_chunks calls
        sql_delete_chunks = "DELETE FROM code_chunks WHERE file_path = ?"
        mocks["db_cursor"].execute.assert_any_call(sql_delete_chunks, (file_path_str,))
        sql_insert_chunk = "INSERT INTO code_chunks (file_path, chunk_id, content, start_line, end_line, chunk_type, name, docstring_summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        mocks["db_cursor"].execute.assert_any_call(sql_insert_chunk,
            (file_path_str, 0, "pass", 1, 1, "code_block", None, None) # Assuming chunk_id 0, name/docstring None
        )
        mocks["db_conn"].commit.assert_called()
        mock_logger.info.assert_any_call(f"Indexed new file: {file_path_str}")


    # TODO: Add more tests for TestCodeIndexer as outlined in the plan:
    # - test_index_file_unchanged_file, test_index_file_force_update,
    # - test_index_file_parse_failure, test_index_file_does_not_exist
    # - test_index_repository (force_reindex True/False)
    # - test_is_file_updated (DB interactions)
    # - test_store_file_info (DB interactions)
    # - test_store_code_chunks (DB interactions)
    # - test_clear_index (DB interactions)
    # - Tests for search_code, get_file_info, get_related_files, get_statistics (these will need more DB mock setup)

```
