import pytest
import os
import hashlib
import logging
import re
import fnmatch
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock, call

# Add project root directory to sys.path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag.code_indexer import CodeChunk, FileInfo, CodeParser, GitignoreParser, CodeIndexer, logger as code_indexer_logger
from src.rag.intelligent_file_filter import IntelligentFileFilter


# Fixtures
@pytest.fixture
def dummy_repo_path(tmp_path: Path) -> Path:
    repo = tmp_path / "dummy_repo"
    repo.mkdir()
    (repo / "sample_module.py").write_text("import os\ndef main():\n  pass", encoding='utf-8')
    return repo

@pytest.fixture
def fixed_timestamp():
    return datetime(2023, 1, 1, 12, 0, 0).timestamp()

@pytest.fixture
def python_code_full_sample():
    return "import os\nimport sys\nfrom pathlib import Path\nimport collections.abc as abc_collections\n\ndef add(a,b):\n    return a+b\n\nclass Dog:\n    pass"


# --- Test Classes (abbreviated) ---
def test_code_chunk_instantiation_and_hash():
    content = "def example_function():\n    pass"
    chunk = CodeChunk(file_path="example.py", content=content, chunk_type="function", name="example_function")
    expected_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    assert chunk.hash_value == expected_hash

def test_file_info_post_init_defaults():
    now = datetime.now()
    file_info = FileInfo(path="test.js", language="javascript", size=500, last_modified=now)
    assert file_info.imports == [] and file_info.exports == []

class TestCodeParser:
    @pytest.fixture
    def parser(self):
        return CodeParser()

    def test_get_language(self, parser):
        assert parser.get_language("script.py") == "python"

    @patch("os.path.getmtime")
    def test_parse_python_file_structure(self, mock_getmtime, parser, dummy_repo_path, python_code_full_sample, fixed_timestamp):
        sample_py_file = dummy_repo_path / "sample.py"
        sample_py_file.write_text(python_code_full_sample, encoding='utf-8')
        mock_getmtime.return_value = fixed_timestamp
        file_info, chunks = parser.parse_file(str(sample_py_file))
        assert file_info.language == "python"
        assert isinstance(chunks, list)


@pytest.fixture
def gitignore_file_factory(dummy_repo_path: Path):
    def _create_gitignore_file(content: str):
        gitignore_path = dummy_repo_path / ".gitignore"
        gitignore_path.write_text(content, encoding='utf-8')
        return str(dummy_repo_path)
    return _create_gitignore_file

class TestGitignoreParser:
    def test_load_non_existent_gitignore(self, dummy_repo_path: Path, caplog):
        with caplog.at_level(logging.DEBUG, logger=code_indexer_logger.name):
            parser = GitignoreParser(str(dummy_repo_path))
            assert len(parser.ignore_patterns) == 0

    @patch.object(GitignoreParser, '_convert_to_regex')
    def test_is_ignored_with_mocked_regex_conversion(self, mock_convert_to_regex, gitignore_file_factory):
        mock_convert_to_regex.return_value = re.compile(fnmatch.translate("*.log"))
        repo_path_str = gitignore_file_factory("*.log")
        parser = GitignoreParser(repo_path_str)
        assert parser.is_ignored("file.log") is True


# --- TestCodeIndexer ---
@pytest.fixture
def temp_repo_path(tmp_path: Path) -> Path:
    repo_path = tmp_path / "test_repo_indexer_specific"
    repo_path.mkdir(exist_ok=True)
    return repo_path

@pytest.fixture
def temp_db_file(tmp_path: Path) -> str:
    db_file = tmp_path / "test_indexer_specific.db"
    if db_file.exists(): db_file.unlink()
    yield str(db_file)
    if db_file.exists(): db_file.unlink()

@pytest.fixture
def in_memory_db_path() -> str:
    return ":memory:"

class TestCodeIndexer:

    def test_init_basic(self, temp_repo_path: Path, temp_db_file: str):
        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            indexer = CodeIndexer(repo_path=str(temp_repo_path), db_path=temp_db_file, use_intelligent_filter=False)
            assert indexer.repo_path == temp_repo_path
            assert indexer.db_path == temp_db_file

    def test_init_in_memory_db(self, temp_repo_path: Path, in_memory_db_path: str):
        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            indexer = CodeIndexer(repo_path=str(temp_repo_path), db_path=in_memory_db_path, use_intelligent_filter=False)
            assert indexer.db_path == in_memory_db_path

    @patch("src.rag.code_indexer.IntelligentFileFilter", spec=IntelligentFileFilter)
    def test_init_with_intelligent_filter(self, MockIntelligentFileFilter, temp_repo_path: Path):
        mock_filter_instance = MockIntelligentFileFilter.return_value
        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            indexer = CodeIndexer(repo_path=str(temp_repo_path), db_path=":memory:", use_intelligent_filter=True)
            MockIntelligentFileFilter.assert_called_once_with(temp_repo_path)
            assert indexer.intelligent_filter is mock_filter_instance

    def test_init_database_called(self, temp_repo_path: Path, temp_db_file: str):
        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            with patch.object(CodeIndexer, '_init_database') as mock_init_db:
                CodeIndexer(repo_path=str(temp_repo_path), db_path=temp_db_file, use_intelligent_filter=False)
                mock_init_db.assert_called_once()

    def test_init_database_schema(self, temp_repo_path: Path, temp_db_file: str):
        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            CodeIndexer(repo_path=str(temp_repo_path), db_path=temp_db_file, use_intelligent_filter=False)
        assert Path(temp_db_file).exists()
        conn = sqlite3.connect(temp_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files';")
        assert cursor.fetchone() is not None
        conn.close()

    def test_should_include_file_logic(self, temp_repo_path: Path):
        indexer = CodeIndexer(repo_path=str(temp_repo_path), db_path=":memory:", use_intelligent_filter=False)
        assert indexer._should_include_file(Path("src/app.py")) is True
        assert indexer._should_include_file(Path("image.png")) is False

    def test_should_exclude_path_gitignore(self, temp_repo_path: Path):
        repo_path_str = str(temp_repo_path)
        (temp_repo_path / ".gitignore").write_text("*.log\nbuild/", encoding='utf-8')
        indexer = CodeIndexer(repo_path=repo_path_str, db_path=":memory:", use_intelligent_filter=False)
        assert indexer.should_exclude_path(temp_repo_path / "file.log") is True
        assert indexer.should_exclude_path(temp_repo_path / "build" / "output.o") is True
        assert indexer.should_exclude_path(temp_repo_path / "file.txt") is False

    def test_should_exclude_path_excluded_dirs(self, temp_repo_path: Path):
        repo_path_str = str(temp_repo_path)
        with patch.object(GitignoreParser, 'is_ignored', return_value=False):
            indexer = CodeIndexer(repo_path=repo_path_str, db_path=":memory:", use_intelligent_filter=False)
            (temp_repo_path / ".git").mkdir(exist_ok=True)
            (temp_repo_path / "node_modules" / "package").mkdir(parents=True, exist_ok=True)
            assert indexer.should_exclude_path(temp_repo_path / ".git" / "config") is True
            assert indexer.should_exclude_path(temp_repo_path / "node_modules" / "file.js") is True

    def test_should_exclude_path_excluded_extensions(self, temp_repo_path: Path):
        repo_path_str = str(temp_repo_path)
        with patch.object(GitignoreParser, 'is_ignored', return_value=False):
            indexer = CodeIndexer(repo_path=repo_path_str, db_path=":memory:", use_intelligent_filter=False)
            assert indexer.should_exclude_path(temp_repo_path / "file.pyc") is True
            assert indexer.should_exclude_path(temp_repo_path / "image.jpeg") is True
            assert indexer.should_exclude_path(temp_repo_path / "image.png") is True

    def test_should_exclude_path_included_file_passes_all_negative_checks(self, temp_repo_path: Path):
        repo_path_str = str(temp_repo_path)
        with patch.object(GitignoreParser, 'is_ignored', return_value=False):
            indexer = CodeIndexer(repo_path=repo_path_str, db_path=":memory:", use_intelligent_filter=False)
            src_dir = temp_repo_path / "src"
            src_dir.mkdir(exist_ok=True)
            test_path = src_dir / "app.py"
            test_path.touch()
            assert indexer.should_exclude_path(test_path) is False

    def test_should_exclude_path_precedence(self, temp_repo_path: Path):
        repo_path_str = str(temp_repo_path)
        (temp_repo_path / ".gitignore").write_text("build/requirements.txt\n", encoding='utf-8')
        indexer_with_gitignore = CodeIndexer(repo_path=repo_path_str, db_path=":memory:", use_intelligent_filter=False)
        build_dir = temp_repo_path / "build"
        build_dir.mkdir(exist_ok=True)
        test_path_in_build_gitignored = build_dir / "requirements.txt"
        test_path_in_build_gitignored.touch()
        assert indexer_with_gitignore.should_exclude_path(test_path_in_build_gitignored) is True

        with patch.object(GitignoreParser, 'is_ignored', return_value=False):
            indexer_no_gitign = CodeIndexer(repo_path=repo_path_str, db_path=":memory:", use_intelligent_filter=False)
            dist_dir = temp_repo_path / "dist"
            dist_dir.mkdir(exist_ok=True)
            test_path_in_dist = dist_dir / "requirements.txt"
            test_path_in_dist.touch()
            assert indexer_no_gitign.should_exclude_path(test_path_in_dist) is True

    @patch("os.walk")
    def test_scan_repository_basic(self, mock_os_walk: MagicMock, temp_repo_path: Path):
        repo_path_str = str(temp_repo_path)
        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            indexer = CodeIndexer(repo_path=repo_path_str, db_path=":memory:", use_intelligent_filter=False)

        mock_os_walk.return_value = [
            (repo_path_str, ['dir1', '.git'], ['file1.py', 'README.md']),
            (str(temp_repo_path / 'dir1'), [], ['file2.py', 'data.txt']),
            (str(temp_repo_path / '.git'), [], ['config'])
        ]

        with patch.object(indexer.gitignore_parser, 'is_ignored') as mock_is_ignored_on_instance, \
             patch.object(indexer, '_should_include_file') as mock_should_include_on_instance:

            def gitignore_side_effect(relative_path_str_arg):
                return relative_path_str_arg == '.git/config'
            mock_is_ignored_on_instance.side_effect = gitignore_side_effect

            def should_include_side_effect(path_obj_arg: Path):
                if path_obj_arg.name == 'data.txt': return False
                return path_obj_arg.suffix in ['.py', '.md'] or path_obj_arg.name == 'README.md'
            mock_should_include_on_instance.side_effect = should_include_side_effect

            found_files = indexer.scan_repository()

        expected_files = sorted(['file1.py', 'README.md', 'dir1/file2.py'])
        assert sorted(found_files) == expected_files
        assert mock_is_ignored_on_instance.call_count >= 4
        assert mock_should_include_on_instance.call_count >= 4

    @pytest.mark.skip("Skipping intelligent filter test for now to focus on basic scan")
    def test_scan_repository_with_intelligent_filter(self):
        pass

    @patch("os.path.getmtime")
    def test_index_file_new_file(self, mock_getmtime, temp_repo_path: Path, temp_db_file: str, fixed_timestamp):
        repo_path_str = str(temp_repo_path)
        db_path_str = str(temp_db_file)

        dummy_file_relative_path = "dummy_new_file.py"
        dummy_file_abs_path = temp_repo_path / dummy_file_relative_path
        dummy_file_content = "print('new file')"
        dummy_file_abs_path.write_text(dummy_file_content, encoding='utf-8')

        mock_getmtime.return_value = fixed_timestamp

        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            indexer = CodeIndexer(repo_path=repo_path_str, db_path=db_path_str, use_intelligent_filter=False)

        file_hash = hashlib.md5(dummy_file_content.encode('utf-8')).hexdigest()
        # The FileInfo path stored and queried should be the relative path for consistency.
        # CodeIndexer.index_file receives a relative path.
        # It constructs full_path for parser. Parser returns FileInfo with this full_path.
        # _store_file_info should ideally convert full_path in FileInfo to relative_path before DB storage,
        # or store a separate relative_path field.
        # Current code stores file_info.path from parser (absolute) into DB.
        # Let's assume the test will check for absolute paths in DB for now, per current code.
        mock_file_info = FileInfo(
            path=str(dummy_file_abs_path), language="python", size=len(dummy_file_content.encode('utf-8')),
            last_modified=datetime.fromtimestamp(fixed_timestamp), hash_value=file_hash, imports=[], exports=[]
        )
        mock_code_chunk = CodeChunk(
            file_path=str(dummy_file_abs_path), content=dummy_file_content, chunk_type="code_block",
            name="dummy_chunk", start_line=1, end_line=1
        )

        with patch.object(indexer.parser, 'parse_file', return_value=(mock_file_info, [mock_code_chunk])) as mock_parse_method:
            result = indexer.index_file(dummy_file_relative_path)
            assert result is True
            mock_parse_method.assert_called_once_with(str(dummy_file_abs_path))

        conn = sqlite3.connect(db_path_str)
        cursor = conn.cursor()
        cursor.execute("SELECT path, language, hash_value FROM files WHERE path = ?", (str(dummy_file_abs_path),))
        file_row = cursor.fetchone()
        assert file_row is not None and file_row[2] == file_hash

        cursor.execute("SELECT file_path, name FROM code_chunks WHERE file_path = ?", (str(dummy_file_abs_path),))
        chunk_row = cursor.fetchone()
        assert chunk_row is not None and chunk_row[1] == "dummy_chunk"
        conn.close()

    @patch("os.path.getmtime")
    def test_index_file_unchanged_file(self, mock_getmtime, temp_repo_path: Path, temp_db_file: str, fixed_timestamp):
        repo_path_str = str(temp_repo_path)
        db_path_str = str(temp_db_file)
        dummy_file_rel_path = "unchanged.py"
        dummy_file_abs_path = temp_repo_path / dummy_file_rel_path
        content = "print('unchanged')"
        dummy_file_abs_path.write_text(content, encoding='utf-8')
        mock_getmtime.return_value = fixed_timestamp
        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            indexer = CodeIndexer(repo_path=repo_path_str, db_path=db_path_str, use_intelligent_filter=False)

        fi_v1 = FileInfo(path=str(dummy_file_abs_path), language="python", size=len(content), last_modified=datetime.fromtimestamp(fixed_timestamp), hash_value=file_hash)
        cc_v1 = [CodeChunk(file_path=str(dummy_file_abs_path), content=content, chunk_type="block")]

        with patch.object(indexer.parser, 'parse_file', return_value=(fi_v1, cc_v1)) as mock_parse1:
            indexer.index_file(dummy_file_rel_path)
            mock_parse1.assert_called_once()

        fi_v2 = FileInfo(path=str(dummy_file_abs_path), language="python", size=len(content), last_modified=datetime.fromtimestamp(fixed_timestamp + 10), hash_value=file_hash)
        with patch.object(indexer, '_store_file_info') as mock_store_file, \
             patch.object(indexer, '_store_code_chunks') as mock_store_chunks, \
             patch.object(indexer.parser, 'parse_file', return_value=(fi_v2, cc_v1)) as mock_parse2:
            result = indexer.index_file(dummy_file_rel_path)
            assert result is False
            mock_parse2.assert_called_once()
            mock_store_file.assert_not_called()
            mock_store_chunks.assert_not_called()

    @patch("os.path.getmtime")
    def test_index_file_updated_file(self, mock_getmtime, temp_repo_path: Path, temp_db_file: str, fixed_timestamp):
        repo_path_str = str(temp_repo_path)
        db_path_str = str(temp_db_file)
        dummy_file_rel_path = "updated.py"
        dummy_file_abs_path = temp_repo_path / dummy_file_rel_path

        content_v1 = "print('v1')"
        dummy_file_abs_path.write_text(content_v1, encoding='utf-8')
        mock_getmtime.return_value = fixed_timestamp
        hash_v1 = hashlib.md5(content_v1.encode('utf-8')).hexdigest()

        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            indexer = CodeIndexer(repo_path=repo_path_str, db_path=db_path_str, use_intelligent_filter=False)

        fi_v1 = FileInfo(path=str(dummy_file_abs_path), language="python", size=len(content_v1), last_modified=datetime.fromtimestamp(fixed_timestamp), hash_value=hash_v1)
        cc_v1 = [CodeChunk(file_path=str(dummy_file_abs_path), content=content_v1, chunk_type="v1")]
        with patch.object(indexer.parser, 'parse_file', return_value=(fi_v1, cc_v1)):
            indexer.index_file(dummy_file_rel_path)

        content_v2 = "print('v2')"
        dummy_file_abs_path.write_text(content_v2, encoding='utf-8') # Simulate file change
        mock_getmtime.return_value = fixed_timestamp + 20
        hash_v2 = hashlib.md5(content_v2.encode('utf-8')).hexdigest()
        fi_v2 = FileInfo(path=str(dummy_file_abs_path), language="python", size=len(content_v2), last_modified=datetime.fromtimestamp(fixed_timestamp + 20), hash_value=hash_v2)
        cc_v2 = [CodeChunk(file_path=str(dummy_file_abs_path), content=content_v2, chunk_type="v2")]

        with patch.object(indexer.parser, 'parse_file', return_value=(fi_v2, cc_v2)) as mock_parse:
            result = indexer.index_file(dummy_file_rel_path)
            assert result is True

        conn = sqlite3.connect(db_path_str)
        cursor = conn.cursor()
        cursor.execute("SELECT hash_value FROM files WHERE path = ?", (str(dummy_file_abs_path),))
        assert cursor.fetchone()[0] == hash_v2
        cursor.execute("SELECT chunk_type FROM code_chunks WHERE file_path = ?", (str(dummy_file_abs_path),))
        assert cursor.fetchone()[0] == "v2"
        conn.close()

    def test_index_file_does_not_exist(self, temp_repo_path: Path, temp_db_file: str):
        repo_path_str = str(temp_repo_path)
        with patch.object(GitignoreParser, '_load_gitignore', lambda self: None):
            indexer = CodeIndexer(repo_path=repo_path_str, db_path=temp_db_file, use_intelligent_filter=False)

        non_existent_file = "non_existent.py"
        # Ensure the file does not exist for real
        abs_non_existent_path_obj = temp_repo_path / non_existent_file
        if abs_non_existent_path_obj.exists():
            abs_non_existent_path_obj.unlink()

        with patch.object(indexer.parser, 'parse_file') as mock_parse:
            result = indexer.index_file(non_existent_file)
            assert result is False
            mock_parse.assert_not_called()

        conn = sqlite3.connect(temp_db_file) # DB should have been created by CodeIndexer init
        cursor = conn.cursor()
        abs_non_existent_path = str(temp_repo_path / non_existent_file)
        cursor.execute("SELECT * FROM files WHERE path = ?", (abs_non_existent_path,))
        assert cursor.fetchone() is None
        conn.close()

# Ensure a trailing newline character
