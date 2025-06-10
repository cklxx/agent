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
            for node in ast.walk(tree):
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
        """将gitignore模式转换为正则表达式"""
        # 处理特殊字符
        pattern = pattern.replace(".", r"\.")
        pattern = pattern.replace("+", r"\+")
        pattern = pattern.replace("?", r".")
        pattern = pattern.replace("*", r"[^/]*")
        pattern = pattern.replace("**", r".*")

        # 处理目录匹配
        if pattern.endswith("/"):
            pattern = pattern[:-1] + r"(?:/.*)?"

        # 处理根路径匹配
        if pattern.startswith("/"):
            pattern = "^" + pattern[1:]
        else:
            pattern = r"(?:^|/)" + pattern

        pattern += r"(?:/.*)?$"

        try:
            return re.compile(pattern)
        except re.error:
            # 如果正则表达式无效，使用简单的fnmatch
            return re.compile(fnmatch.translate(pattern))

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

    def __init__(self, repo_path: str, db_path: str = "temp/rag_data/code_index.db"):
        self.repo_path = Path(repo_path)
        self.db_path = db_path
        self.parser = CodeParser()
        self.gitignore_parser = GitignoreParser(repo_path)

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

        # 排除的目录 (这些目录通常包含生成文件或缓存)
        self.exclude_dirs = {
            ".git",
            ".svn",
            ".hg",
            ".venv",
            "venv",
            "env",
            "ENV",
            "__pycache__",
            ".pytest_cache",
            ".coverage",
            ".tox",
            ".mypy_cache",
            "node_modules",
            ".npm",
            ".yarn",
            "dist",
            "build",
            "target",
            "out",
            "bin",
            "obj",
            ".gradle",
            ".maven",
            ".idea",
            ".vscode",
            ".vs",
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
        }

        # 明确排除的文件扩展名 (二进制文件等)
        self.exclude_extensions = {
            # 二进制和可执行文件
            ".pyc",
            ".pyo",
            ".pyd",
            ".so",
            ".dll",
            ".exe",
            ".bin",
            ".class",
            ".jar",
            ".war",
            ".ear",
            ".o",
            ".obj",
            ".lib",
            ".a",
            # 媒体文件
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".ico",
            ".svg",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".mp3",
            ".wav",
            ".ogg",
            ".flac",
            ".aac",
            # 压缩文件
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".xz",
            ".rar",
            ".7z",
            # 其他二进制文件
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
        }

        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        # 确保数据库目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
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
        # 检查gitignore规则
        relative_path = str(path.relative_to(self.repo_path))
        if self.gitignore_parser.is_ignored(relative_path):
            return True

        # 检查目录
        for part in path.parts:
            if part in self.exclude_dirs:
                return True

        # 检查文件扩展名排除列表
        if path.suffix.lower() in self.exclude_extensions:
            return True

        # 检查是否是我们想要索引的文件
        return not self._should_include_file(path)

    def _should_include_file(self, path: Path) -> bool:
        """判断文件是否应该被索引"""
        file_name = path.name
        file_suffix = path.suffix.lower()

        # 检查配置文件名
        if file_name in self.include_config_files:
            return True

        # 检查文件名模式 (如 .env, .env.local 等)
        for config_file in self.include_config_files:
            if file_name.startswith(config_file):
                return True

        # 检查扩展名
        if file_suffix in self.include_extensions:
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

                # 检查是否是我们想要索引的文件
                if not self._should_include_file(file_path):
                    excluded_by_type += 1
                    logger.debug(f"Excluded by file type: {relative_path}")
                    continue

                files.append(relative_path)

        logger.info(
            f"Repository scan completed: {total_files} total files, {len(files)} included files"
        )
        logger.info(
            f"Exclusion stats: gitignore({excluded_by_gitignore}), directory({excluded_by_dir}), extension({excluded_by_extension}), type({excluded_by_type})"
        )
        return files

    def index_file(self, file_path: str) -> bool:
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
            if self._is_file_updated(file_info):
                self._store_file_info(file_info)
                self._store_code_chunks(chunks)
                logger.info(f"Indexed file: {file_path}")
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

    def index_repository(self) -> Dict[str, int]:
        """索引整个仓库"""
        logger.info(f"Starting repository indexing: {self.repo_path}")

        files = self.scan_repository()
        stats = {
            "total_files": len(files),
            "indexed_files": 0,
            "skipped_files": 0,
            "failed_files": 0,
        }

        for file_path in files:
            try:
                if self.index_file(file_path):
                    stats["indexed_files"] += 1
                else:
                    stats["skipped_files"] += 1
            except Exception as e:
                logger.error(f"Failed to index file {file_path}: {e}")
                stats["failed_files"] += 1

        logger.info(f"Indexing completed: {stats}")
        return stats

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
