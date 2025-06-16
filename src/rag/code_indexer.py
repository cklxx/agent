"""
代码索引器 - 专门用于索引代码仓库的RAG组件
"""

import os
import ast
import hashlib
import sqlite3
import logging
import fnmatch
import re
from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from .intelligent_file_filter import IntelligentFileFilter, FileRelevance

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """代码块数据结构"""

    file_path: str
    content: str
    chunk_type: str  # function, class, method, import, other
    name: Optional[str] = None  # 函数名、类名等
    start_line: int = 0
    end_line: int = 0
    docstring: Optional[str] = None
    dependencies: List[str] = None
    hash_value: str = ""

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if not self.hash_value:
            self.hash_value = hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class FileInfo:
    """文件信息数据结构"""

    path: str
    language: str
    size: int
    last_modified: datetime
    encoding: str = "utf-8"
    imports: List[str] = None
    exports: List[str] = None
    hash_value: str = ""

    def __post_init__(self):
        if self.imports is None:
            self.imports = []
        if self.exports is None:
            self.exports = []


class CodeParser:
    """代码解析器"""

    def __init__(self):
        self.supported_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".clj": "clojure",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".md": "markdown",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".sql": "sql",
            ".sh": "shell",
            ".bash": "shell",
            ".zsh": "shell",
        }

    def get_language(self, file_path: str) -> str:
        """根据文件扩展名判断语言类型"""
        ext = Path(file_path).suffix.lower()
        return self.supported_extensions.get(ext, "text")

    def parse_python_file(
        self, file_path: str, content: str
    ) -> Tuple[FileInfo, List[CodeChunk]]:
        """解析Python文件"""
        chunks = []
        imports = []
        exports = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # 解析函数和类
            for node in tree.body: # Iterate over top-level nodes only
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunk = self._extract_function_chunk(file_path, content, node)
                    chunks.append(chunk)
                    exports.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    chunk = self._extract_class_chunk(file_path, content, node)
                    chunks.append(chunk)
                    exports.append(node.name)

        except SyntaxError as e:
            logger.warning(f"Syntax error parsing file {file_path}: {e}")

        file_info = FileInfo(
            path=file_path,
            language="python",
            size=len(content),
            last_modified=datetime.fromtimestamp(os.path.getmtime(file_path)),
            imports=imports,
            exports=exports,
            hash_value=hashlib.md5(content.encode()).hexdigest(),
        )

        return file_info, chunks

    def _extract_function_chunk(
        self, file_path: str, content: str, node: ast.FunctionDef
    ) -> CodeChunk:
        """提取函数代码块"""
        lines = content.split("\n")
        start_line = node.lineno
        end_line = node.end_lineno or start_line

        func_content = "\n".join(lines[start_line - 1 : end_line])

        # 提取文档字符串
        docstring = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value

        return CodeChunk(
            file_path=file_path,
            content=func_content,
            chunk_type="function",
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            docstring=docstring,
        )

    def _extract_class_chunk(
        self, file_path: str, content: str, node: ast.ClassDef
    ) -> CodeChunk:
        """提取类代码块"""
        lines = content.split("\n")
        start_line = node.lineno
        end_line = node.end_lineno or start_line

        class_content = "\n".join(lines[start_line - 1 : end_line])

        # 提取文档字符串
        docstring = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value

        return CodeChunk(
            file_path=file_path,
            content=class_content,
            chunk_type="class",
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            docstring=docstring,
        )

    def parse_file(self, file_path: str) -> Tuple[FileInfo, List[CodeChunk]]:
        """解析文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
            except:
                logger.warning(f"Unable to read file {file_path}")
                return None, []

        language = self.get_language(file_path)

        if language == "python":
            return self.parse_python_file(file_path, content)
        else:
            # 对于其他类型的文件，做简单的块分割
            chunks = self._split_file_into_chunks(file_path, content, language)
            file_info = FileInfo(
                path=file_path,
                language=language,
                size=len(content),
                last_modified=datetime.fromtimestamp(os.path.getmtime(file_path)),
                hash_value=hashlib.md5(content.encode()).hexdigest(),
            )
            return file_info, chunks

    def _split_file_into_chunks(
        self, file_path: str, content: str, language: str, chunk_size: int = 500
    ) -> List[CodeChunk]:
        """将文件分割成代码块"""
        chunks = []
        lines = content.split("\n")

        current_chunk = []
        current_size = 0
        start_line = 1

        for i, line in enumerate(lines, 1):
            current_chunk.append(line)
            current_size += len(line)

            if current_size >= chunk_size or i == len(lines):
                chunk_content = "\n".join(current_chunk)
                chunk = CodeChunk(
                    file_path=file_path,
                    content=chunk_content,
                    chunk_type="code_block",
                    start_line=start_line,
                    end_line=i,
                )
                chunks.append(chunk)

                current_chunk = []
                current_size = 0
                start_line = i + 1

        return chunks


class GitignoreParser:
    """解析.gitignore文件的工具类"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.ignore_patterns = []
        self._load_gitignore()

    def _load_gitignore(self):
        """加载.gitignore文件"""
        gitignore_path = self.repo_path / ".gitignore"
        if not gitignore_path.exists():
            logger.debug("No .gitignore file found")
            return

        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith("#"):
                    continue

                # 处理否定模式 (以!开头)
                negate = line.startswith("!")
                if negate:
                    line = line[1:]

                # 转换为正则表达式模式
                pattern = self._convert_to_regex(line)
                self.ignore_patterns.append(
                    {"pattern": pattern, "negate": negate, "original": line}
                )

        except Exception as e:
            logger.warning(f"Failed to parse .gitignore file: {e}")

    def _convert_to_regex(self, pattern: str) -> re.Pattern:
        """
        将gitignore模式转换为正则表达式。
        Simplified version primarily relying on fnmatch.translate for robustness.
        """
        # Handle negation prefix, but apply it after converting the main pattern
        # The is_ignored method handles the negation logic based on rule order.
        # Here, we just convert the pattern part.

        # fnmatch.translate converts a standard glob pattern to a regex pattern.
        # Gitignore patterns are similar to globs, but with some specific behaviors
        # like `**` and how `/` is handled.

        # Direct use of fnmatch.translate might not handle all gitignore nuances perfectly,
        # especially regarding directory matching ("pattern/") or "**".
        # However, for many common cases, it's a good starting point.

        # Let's adjust common gitignore specifics before fnmatch.
        # 1. `**` is like `*` in fnmatch but can cross multiple directory levels.
        #    `fnmatch` doesn't have a direct equivalent for `**` that means "zero or more directories".
        #    A simple `pattern.replace('**', '*')` might be too simplistic.
        #    If `**` is present, `fnmatch` might not be enough.
        #    The original code had: pattern = pattern.replace("**", r".*")
        #    Let's try to retain that for `**` as it's a common requirement.

        # 2. Trailing slash "pattern/" means it's a directory.
        #    fnmatch doesn't specifically handle this; the regex from fnmatch needs to ensure it matches a dir.
        #    `dir/` should match `dir/file` and `dir/subdir/file`.
        #    `fnmatch.translate("dir/")` -> `dir/\\Z` (matches literal "dir/")
        #    We need it to match `dir/` and `dir/*`.
        #    So, if `pattern.endswith('/')`, we can translate `pattern + '*'` and also check exact match for `pattern[:-1]`.
        #    This gets complicated.

        # 3. Leading slash "/pattern" anchors to the repo root.
        #    fnmatch doesn't know about repo root. The regex from fnmatch needs `^`.

        # Simplification: Use fnmatch.translate and make small adjustments if possible.
        # This might break some of the more complex behaviors the original tried to handle.

        is_dir_pattern = pattern.endswith('/')
        if is_dir_pattern:
            pattern = pattern[:-1] # Remove trailing slash for now, will adjust regex suffix

        is_anchored_at_start = pattern.startswith('/')
        if is_anchored_at_start:
            pattern = pattern[1:] # Remove leading slash, will add ^ to regex

        # Convert common wildcards. Gitignore's `*` doesn't cross dir boundaries by default.
        # `fnmatch`'s `*` also doesn't cross dir boundaries.
        # `**` is the tricky one. If present, simple fnmatch is not enough.
        # For now, let's assume `**` is not in the simplified patterns for this attempt,
        # or rely on its original handling if it was more robust.
        # The original code replaced `**` with `.*`.

        # Let's try a version that uses the original complex replacements for wildcards,
        # but simplifies the anchoring and suffix logic.

        original_pattern_for_fallback = pattern # This is now pattern without leading/trailing slashes
                                                # This is not correct, fallback should use original.
                                                # Let's keep original_pattern_for_fallback as the true original.

        # Re-fetch true original for fallback
        # No, _convert_to_regex receives pattern without !.
        # The parameter 'pattern' IS the original pattern string (without !)

        temp_pattern = pattern # Use this for manipulation

        # Handle `**` specifically because fnmatch doesn't support it well for "any dir level"
        # Replace `**` with a placeholder that fnmatch won't mess up, then convert to `.*`.
        # This means we are partially doing custom regex.
        if "**" in temp_pattern:
            # A common strategy is to split by **, translate parts, then join with .*
            # For simplicity here, if ** is present, we might fall back to a more direct regex construction
            # or accept fnmatch's limitations for it.
            # The original code did: temp_pattern = temp_pattern.replace("**", r".*")
            # Let's stick to that for ** as it's a known translation.
            temp_pattern = temp_pattern.replace("**", r".*") # Greedy, could be r".*?"

        # Now translate the (potentially **-modified) pattern using fnmatch
        regex_str = fnmatch.translate(temp_pattern)
        # fnmatch.translate adds `\Z` at the end. We might want to adjust this.
        # e.g., fnmatch.translate("*.log") -> '.*\\.log\\Z'
        # e.g., fnmatch.translate("build") -> 'build\\Z'
        # e.g., fnmatch.translate("foo/.*/bar") (if ** became .*) -> 'foo\\/.\\*\\/bar\\Z' (escapes are tricky)

        if is_anchored_at_start:
            # fnmatch adds \A for beginning of string by default. If we removed leading /, ensure it means root.
            # If regex_str starts with \A, replace with ^. Otherwise, prepend ^.
            if regex_str.startswith(r'\A'):
                 regex_str = '^' + regex_str[2:]
            else: # Should not happen if fnmatch.translate always adds \A
                 regex_str = '^' + regex_str
        else:
            # If not anchored to root, it can appear after any '/' or at the start.
            # fnmatch regex usually anchors at start (\A). We need to allow prefix.
            # This makes it behave like `(?:^|/)pattern`.
            # A simple way: if it starts with `\A`, replace with `(?:^|/)?` - no, this is not quite right.
            # The regex `(?:^|/)` + (pattern part of fnmatch output) is better.
            # fnmatch output: \A<pattern_re>\Z
            # We want: (?:^|/)<pattern_re>($|/) (roughly)
            if regex_str.startswith(r'\A'):
                main_pattern_part = regex_str[2:-2] # Remove \A and \Z (e.g., 'file\\.txt')
            else: # Should not happen with fnmatch.translate
                main_pattern_part = regex_str[:-2] if regex_str.endswith(r'\Z') else regex_str

            # If original pattern had no slashes (e.g., "file.txt", "*.log"), it should match anywhere.
            if "/" not in pattern: # 'pattern' here is original pattern stripped of start/end slashes
                regex_str = r"(?:^|.*/)" + main_pattern_part
            else: # Original pattern had slashes (e.g., "foo/bar")
                regex_str = r"(?:^|/)" + main_pattern_part


        if is_dir_pattern:
            # Pattern was "dir/", fnmatch made it for "dir". Should match "dir/anything" or "dir" if it's a dir.
            # Current regex_str is like (?:^|.*/)dir or (?:^|/)dir
            # We want it to match if path is "dir" or "dir/foo".
            # So, (?:^|.*/)dir($|/.*) or (?:^|/)dir($|/.*)
            regex_str += r"($|/.*)"
        else:
            # Pattern was "file", fnmatch made it for "file". Should match "file" or "file/" if it's a dir.
            # Current regex_str is like (?:^|.*/)file or (?:^|/)file
            # We want it to match if path is "file" or "file/foo" (if file is a dir component)
            regex_str += r"($|/)"


        # This simplified version might not be perfect, but aims for common cases.
        try:
            return re.compile(regex_str)
        except re.error:
            logger.warning(f"Simplified regex '{regex_str}' from '{pattern}' failed, using basic fnmatch.")
            # Fallback to the most basic fnmatch translation of the original pattern
            return re.compile(fnmatch.translate(original_pattern_for_fallback))

    def is_ignored(self, file_path: str) -> bool:
        """检查文件是否应该被忽略"""
        relative_path = str(Path(file_path).as_posix())

        ignored = False
        for rule in self.ignore_patterns:
            if rule["pattern"].match(relative_path):
                if rule["negate"]:
                    ignored = False
                else:
                    ignored = True

        return ignored


class CodeIndexer:
    """代码索引器"""

    def __init__(
        self,
        repo_path: str,
        db_path: str = "temp/rag_data/code_index.db",
        use_intelligent_filter: bool = True,
    ):
        self.repo_path = Path(repo_path)
        self.db_path = db_path
        self.parser = CodeParser()
        self.gitignore_parser = GitignoreParser(repo_path)

        # 智能文件过滤器
        self.use_intelligent_filter = use_intelligent_filter
        if use_intelligent_filter:
            self.intelligent_filter = IntelligentFileFilter(self.repo_path) # Use self.repo_path (Path object)
        else:
            self.intelligent_filter = None

        # 只索引有用的代码文件和配置文件
        self.include_extensions = {
            # 编程语言文件
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".cs",
            ".go",
            ".rs",
            ".php",
            ".rb",
            ".swift",
            ".kt",
            ".scala",
            ".clj",
            ".html",
            ".css",
            ".scss",
            ".sass",
            ".less",
            ".sql",
            ".sh",
            ".bash",
            ".zsh",
            ".fish",
            ".ps1",
            ".bat",
            ".cmd",
            # 配置和文档文件
            ".yaml",
            ".yml",
            ".json",
            ".toml",
            ".ini",
            ".cfg",
            ".xml",
            ".md",
            ".rst",
            ".txt",
            ".dockerfile",
            ".dockerignore",
            ".gitignore",
            ".gitattributes",
            # 项目配置文件
            ".lock",
            ".gradle",
            ".maven",
            ".npm",
            ".yarn",
        }

        # 有用的配置文件名 (不考虑扩展名)
        self.include_config_files = {
            "Dockerfile",
            "Makefile",
            "CMakeLists.txt",
            "requirements.txt",
            "setup.py",
            "setup.cfg",
            "pyproject.toml",
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pom.xml",
            "build.gradle",
            "gradle.properties",
            "Gemfile",
            "Gemfile.lock",
            "Rakefile",
            "Cargo.toml",
            "Cargo.lock",
            "go.mod",
            "go.sum",
            ".env.example",
            "conf.yaml.example",
            "config.example",
            ".editorconfig",
            ".eslintrc",
            ".prettierrc",
            "tsconfig.json",
            "webpack.config.js",
            "LICENSE",
            "README",
        }

        # 增强的排除目录 - 包含更多虚拟环境和第三方库目录
        self.exclude_dirs = {
            # 版本控制
            ".git",
            ".svn",
            ".hg",
            # Python 虚拟环境和缓存
            ".venv",
            "venv",
            "env",
            "ENV",
            "virtualenv",
            ".virtualenv",
            "__pycache__",
            ".pytest_cache",
            ".coverage",
            ".tox",
            ".mypy_cache",
            "site-packages",
            "dist-info",
            "egg-info",
            # Node.js
            "node_modules",
            ".npm",
            ".yarn",
            ".pnpm",
            # 其他语言包管理器
            "vendor",  # Go, PHP, Ruby
            "target",  # Rust, Java, Maven
            "build",
            "dist",
            "out",
            "bin",
            "obj",  # 构建输出
            # IDE和工具
            ".idea",
            ".vscode",
            ".vs",
            ".gradle",
            ".maven",
            # 临时和缓存目录
            "temp",
            "tmp",
            "cache",
            ".cache",
            "log",
            "logs",
            ".logs",
            ".sass-cache",
            ".next",
            ".nuxt",
            ".parcel-cache",
            # 文档生成
            "_site",
            "_build",
            "docs/_build",
        }

        # 明确排除的文件扩展名 (二进制文件等)
        self.exclude_extensions = {
            # 二进制和可执行文件
            ".pyc",
            ".pyo",
            ".pyd",
            ".so",
            ".dll",
            ".dylib",
            ".exe",
            ".o",
            ".obj",
            ".lib",
            ".a",
            ".jar",
            ".war",
            ".ear",
            # 压缩文件
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".xz",
            ".7z",
            ".rar",
            # 图像和媒体
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".bmp",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            # 字体
            ".ttf",
            ".otf",
            ".woff",
            ".woff2",
            ".eot",
            # 其他二进制
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".db",
            ".sqlite",
            ".sqlite3",
        }

        # 确保数据库目录存在 (除非是内存数据库)
        if self.db_path != ":memory:":
            db_dir = os.path.dirname(self.db_path)
            if db_dir: # Ensure dirname is not empty (e.g. if db_path is just a filename)
                os.makedirs(db_dir, exist_ok=True)

        self._init_database()

        logger.info(
            f"CodeIndexer initialized: repo={repo_path}, intelligent_filter={use_intelligent_filter}"
        )

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建文件表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                language TEXT,
                size INTEGER,
                last_modified TIMESTAMP,
                hash_value TEXT,
                imports TEXT,
                exports TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 创建代码块表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS code_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                content TEXT,
                chunk_type TEXT,
                name TEXT,
                start_line INTEGER,
                end_line INTEGER,
                docstring TEXT,
                dependencies TEXT,
                hash_value TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_path) REFERENCES files (path)
            )
        """
        )

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files (path)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON code_chunks (file_path)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_name ON code_chunks (name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_type ON code_chunks (chunk_type)"
        )

        conn.commit()
        conn.close()

    def should_exclude_path(self, path: Path) -> bool:
        """判断是否应该排除路径"""
        logger.debug(f"[TEMP_DEBUG] should_exclude_path: Evaluating path: {path}, name: {path.name}, suffix: {path.suffix}")
        # 检查gitignore规则
        relative_path = str(path.relative_to(self.repo_path))
        if self.gitignore_parser.is_ignored(relative_path):
            logger.debug(f"[TEMP_DEBUG] should_exclude_path: Ignored by gitignore: {path}")
            return True

        # 检查目录 (relative to repo root)
        # Convert path to be relative to repo_path before checking its parts against exclude_dirs
        try:
            path_relative_to_repo = path.relative_to(self.repo_path)
            for part in path_relative_to_repo.parts:
                # We only want to check the actual components, not '.' (current dir) if path itself is repo_path
                if part != '.' and part in self.exclude_dirs: # Check part != '.' for robustness
                    logger.debug(f"[TEMP_DEBUG] should_exclude_path: Ignored by exclude_dirs ('{part}'): {path} (relative: {path_relative_to_repo})")
                    return True
        except ValueError:
            # This can happen if 'path' is not under 'self.repo_path'.
            # For example, if path is an absolute system path elsewhere.
            # In such cases, direct dir exclusion might not apply or needs careful thought.
            # For now, if it's not relative, we don't apply this specific dir exclusion.
            # Alternatively, one might want to check absolute path.parts if path is outside repo_path.
            # Given the context, exclusion usually applies to files *within* the repo.
            logger.debug(f"[TEMP_DEBUG] should_exclude_path: Path {path} is not relative to repo {self.repo_path}, skipping exclude_dirs check on parts.")
            pass


        # 检查文件扩展名排除列表
        if path.suffix.lower() in self.exclude_extensions:
            logger.debug(f"[TEMP_DEBUG] should_exclude_path: Ignored by exclude_extensions ('{path.suffix.lower()}'): {path}")
            return True

        # 检查是否是我们想要索引的文件
        #检查是否是我们想要索引的文件
        should_include = self._should_include_file(path)
        if should_include:
            return False # Not excluded
        else:
            return True  # Excluded because it's not an included file

    def _should_include_file(self, path: Path) -> bool:
        """判断文件是否应该被索引"""
        file_name = path.name
        file_suffix = path.suffix.lower()

        # 检查配置文件名
        if file_name in self.include_config_files:
            return True

        # 检查文件名模式 (如 .env, .env.local 等)
        for config_file_pattern in self.include_config_files:
            if file_name.startswith(config_file_pattern):
                return True

        # 检查扩展名
        if file_suffix and file_suffix in self.include_extensions:
            return True

        # 没有扩展名的文件，检查是否是常见的配置文件
        if not file_suffix and file_name.lower() in {
            "dockerfile",
            "makefile",
            "rakefile",
            "gruntfile",
            "gulpfile",
        }:
            return True

        return False

    def scan_repository(self) -> List[str]:
        """扫描仓库获取所有代码文件"""
        files = []
        total_files = 0
        excluded_by_gitignore = 0
        excluded_by_dir = 0
        excluded_by_extension = 0
        excluded_by_type = 0

        # 首先获取所有可能的文件
        candidate_files = []

        for root, dirs, filenames in os.walk(self.repo_path):
            # 排除目录
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            excluded_dirs = set(original_dirs) - set(dirs)
            if excluded_dirs:
                logger.debug(f"Excluded directories: {excluded_dirs}")

            for filename in filenames:
                total_files += 1
                file_path = Path(root) / filename
                relative_path = str(file_path.relative_to(self.repo_path))

                # 检查gitignore规则
                if self.gitignore_parser.is_ignored(relative_path):
                    excluded_by_gitignore += 1
                    logger.debug(f"Excluded by gitignore: {relative_path}")
                    continue

                # 检查目录排除
                excluded_by_dir_check = False
                for part in file_path.parts:
                    if part in self.exclude_dirs:
                        excluded_by_dir += 1
                        excluded_by_dir_check = True
                        break
                if excluded_by_dir_check:
                    continue

                # 检查文件扩展名排除列表
                if file_path.suffix.lower() in self.exclude_extensions:
                    excluded_by_extension += 1
                    logger.debug(f"Excluded by extension: {relative_path}")
                    continue

                # 基本文件类型检查
                if not self._should_include_file(file_path):
                    excluded_by_type += 1
                    logger.debug(f"Excluded by file type: {relative_path}")
                    continue

                candidate_files.append(relative_path)

        # 使用智能过滤器进一步过滤
        if self.use_intelligent_filter and self.intelligent_filter:
            logger.info(f"使用智能过滤器处理 {len(candidate_files)} 个候选文件...")
            try:
                final_files, filter_stats = (
                    self.intelligent_filter.filter_files_for_indexing(candidate_files)
                )
                files = final_files

                # 更新统计信息
                intelligent_excluded = len(candidate_files) - len(final_files)
                logger.info(f"智能过滤器统计: {filter_stats}")

            except Exception as e:
                logger.warning(f"智能过滤器失败，使用基础过滤: {e}")
                files = candidate_files
        else:
            files = candidate_files

        logger.info(
            f"Repository scan completed: {total_files} total files, {len(files)} files selected for indexing"
        )
        logger.info(
            f"Exclusion stats: gitignore({excluded_by_gitignore}), directory({excluded_by_dir}), extension({excluded_by_extension}), type({excluded_by_type})"
        )

        if self.use_intelligent_filter:
            logger.info(f"Final file selection: {len(files)} files will be indexed")

        return files

    async def scan_repository_intelligent(self, task_context: str = "") -> List[str]:
        """使用LLM智能扫描仓库文件"""
        # 首先进行基础扫描获取候选文件
        candidate_files = []
        total_files = 0

        for root, dirs, filenames in os.walk(self.repo_path):
            # 排除明显不需要的目录
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for filename in filenames:
                total_files += 1
                file_path = Path(root) / filename
                relative_path = str(file_path.relative_to(self.repo_path))

                # 基础过滤：gitignore、扩展名等
                if self.gitignore_parser.is_ignored(relative_path):
                    continue
                if file_path.suffix.lower() in self.exclude_extensions:
                    continue

                candidate_files.append(relative_path)

        logger.info(
            f"基础扫描完成: {total_files} 个文件，{len(candidate_files)} 个候选文件"
        )

        # 使用智能过滤器和LLM进行智能分类
        if self.use_intelligent_filter and self.intelligent_filter:
            try:
                logger.info(f"开始LLM智能文件分类，任务上下文: {task_context}")
                classifications = await self.intelligent_filter.llm_classify_files(
                    candidate_files, task_context
                )

                # 收集高优先级和中等优先级的文件
                final_files = [
                    c.path
                    for c in classifications
                    if c.relevance in [FileRelevance.HIGH, FileRelevance.MEDIUM]
                ]

                # 统计信息
                stats = {
                    "total_scanned": total_files,
                    "candidates": len(candidate_files),
                    "final_selected": len(final_files),
                    "high_relevance": len(
                        [
                            c
                            for c in classifications
                            if c.relevance == FileRelevance.HIGH
                        ]
                    ),
                    "medium_relevance": len(
                        [
                            c
                            for c in classifications
                            if c.relevance == FileRelevance.MEDIUM
                        ]
                    ),
                    "low_relevance": len(
                        [c for c in classifications if c.relevance == FileRelevance.LOW]
                    ),
                    "excluded": len(
                        [
                            c
                            for c in classifications
                            if c.relevance == FileRelevance.EXCLUDE
                        ]
                    ),
                }

                logger.info(f"LLM智能扫描完成: {stats}")
                return final_files

            except Exception as e:
                logger.error(f"LLM智能扫描失败，回退到基础扫描: {e}")
                return self.scan_repository()
        else:
            return self.scan_repository()

    def index_repository(self, force_reindex: bool = False) -> Dict[str, int]:
        """索引整个仓库"""
        logger.info(f"Starting repository indexing: {self.repo_path}")

        files = self.scan_repository()
        stats = {
            "total_files": len(files),
            "indexed_files": 0,
            "skipped_files": 0,
            "failed_files": 0,
        }

        # 如果强制重新索引，清理现有数据
        if force_reindex:
            logger.info("强制重新索引，清理现有数据...")
            self._clear_index()

        for file_path in files:
            try:
                if self.index_file(file_path, force_update=force_reindex):
                    stats["indexed_files"] += 1
                else:
                    stats["skipped_files"] += 1
            except Exception as e:
                logger.error(f"Failed to index file {file_path}: {e}")
                stats["failed_files"] += 1

        logger.info(f"Indexing completed: {stats}")
        return stats

    def _clear_index(self):
        """清理索引数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM code_chunks")
        cursor.execute("DELETE FROM files")
        conn.commit()
        conn.close()
        logger.info("索引数据已清理")

    def index_file(self, file_path: str, force_update: bool = False) -> bool:
        """索引单个文件"""
        full_path = self.repo_path / file_path

        if not full_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return False

        try:
            file_info, chunks = self.parser.parse_file(str(full_path))
            if not file_info:
                return False

            # 检查文件是否已更新
            if force_update or self._is_file_updated(file_info):
                self._store_file_info(file_info)
                self._store_code_chunks(chunks)
                logger.debug(f"Indexed file: {file_path}")
                return True
            else:
                logger.debug(f"File unchanged, skipping: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to index file {file_path}: {e}")
            return False

    def _is_file_updated(self, file_info: FileInfo) -> bool:
        """检查文件是否需要更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT hash_value FROM files WHERE path = ?", (file_info.path,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return True  # 新文件

        return result[0] != file_info.hash_value  # 检查哈希值

    def _store_file_info(self, file_info: FileInfo):
        """存储文件信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO files 
            (path, language, size, last_modified, hash_value, imports, exports)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                file_info.path,
                file_info.language,
                file_info.size,
                file_info.last_modified,
                file_info.hash_value,
                ",".join(file_info.imports),
                ",".join(file_info.exports),
            ),
        )

        conn.commit()
        conn.close()

    def _store_code_chunks(self, chunks: List[CodeChunk]):
        """存储代码块"""
        if not chunks:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 删除该文件的旧代码块
        cursor.execute(
            "DELETE FROM code_chunks WHERE file_path = ?", (chunks[0].file_path,)
        )

        # 插入新代码块
        for chunk in chunks:
            cursor.execute(
                """
                INSERT INTO code_chunks 
                (file_path, content, chunk_type, name, start_line, end_line, docstring, dependencies, hash_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    chunk.file_path,
                    chunk.content,
                    chunk.chunk_type,
                    chunk.name,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.docstring,
                    ",".join(chunk.dependencies),
                    chunk.hash_value,
                ),
            )

        conn.commit()
        conn.close()

    def search_code(
        self,
        query: str,
        file_type: Optional[str] = None,
        chunk_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """搜索代码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 构建查询条件
        conditions = []
        params = []

        # 文本搜索
        conditions.append("(content LIKE ? OR name LIKE ? OR docstring LIKE ?)")
        search_term = f"%{query}%"
        params.extend([search_term, search_term, search_term])

        # 文件类型过滤
        if file_type:
            conditions.append(
                "EXISTS (SELECT 1 FROM files WHERE files.path = code_chunks.file_path AND files.language = ?)"
            )
            params.append(file_type)

        # 块类型过滤
        if chunk_type:
            conditions.append("chunk_type = ?")
            params.append(chunk_type)

        where_clause = " AND ".join(conditions)

        query_sql = f"""
            SELECT 
                cc.file_path, cc.content, cc.chunk_type, cc.name,
                cc.start_line, cc.end_line, cc.docstring,
                f.language
            FROM code_chunks cc
            LEFT JOIN files f ON cc.file_path = f.path
            WHERE {where_clause}
            ORDER BY 
                CASE 
                    WHEN cc.name LIKE ? THEN 1
                    WHEN cc.docstring LIKE ? THEN 2
                    ELSE 3
                END,
                cc.file_path, cc.start_line
            LIMIT ?
        """

        params.extend([f"%{query}%", f"%{query}%", limit])

        cursor.execute(query_sql, params)
        results = cursor.fetchall()
        conn.close()

        # 格式化结果
        formatted_results = []
        for row in results:
            result = {
                "file_path": row[0],
                "content": row[1],
                "chunk_type": row[2],
                "name": row[3],
                "start_line": row[4],
                "end_line": row[5],
                "docstring": row[6],
                "language": row[7],
            }
            formatted_results.append(result)

        return formatted_results

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT path, language, size, last_modified, imports, exports
            FROM files WHERE path = ?
        """,
            (file_path,),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "path": result[0],
                "language": result[1],
                "size": result[2],
                "last_modified": result[3],
                "imports": result[4].split(",") if result[4] else [],
                "exports": result[5].split(",") if result[5] else [],
            }

        return None

    def get_related_files(self, file_path: str) -> List[str]:
        """获取相关文件"""
        file_info = self.get_file_info(file_path)
        if not file_info:
            return []

        related_files = set()

        # 基于导入关系查找相关文件
        for import_name in file_info["imports"]:
            related_files.update(self._find_files_by_export(import_name))

        # 基于导出关系查找相关文件
        for export_name in file_info["exports"]:
            related_files.update(self._find_files_by_import(export_name))

        # 移除自身
        related_files.discard(file_path)

        return list(related_files)

    def _find_files_by_export(self, export_name: str) -> List[str]:
        """根据导出名称查找文件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT path FROM files 
            WHERE exports LIKE ?
        """,
            (f"%{export_name}%",),
        )

        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

    def _find_files_by_import(self, import_name: str) -> List[str]:
        """根据导入名称查找文件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT path FROM files 
            WHERE imports LIKE ?
        """,
            (f"%{import_name}%",),
        )

        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 文件统计
        cursor.execute("SELECT COUNT(*) FROM files")
        total_files = cursor.fetchone()[0]

        cursor.execute("SELECT language, COUNT(*) FROM files GROUP BY language")
        files_by_language = dict(cursor.fetchall())

        # 代码块统计
        cursor.execute("SELECT COUNT(*) FROM code_chunks")
        total_chunks = cursor.fetchone()[0]

        cursor.execute(
            "SELECT chunk_type, COUNT(*) FROM code_chunks GROUP BY chunk_type"
        )
        chunks_by_type = dict(cursor.fetchall())

        conn.close()

        return {
            "total_files": total_files,
            "total_chunks": total_chunks,
            "files_by_language": files_by_language,
            "chunks_by_type": chunks_by_type,
        }
