"""
智能工作区分析器 - 集成LLM决策的工作区状态管理
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .workspace_state_manager import WorkspaceStateManager, WorkspaceAnalysis
from ..llms.llm import get_llm_by_type
from ..prompts import apply_prompt_template
from ..rag.code_indexer import GitignoreParser

logger = logging.getLogger(__name__)


class IntelligentWorkspaceAnalyzer:
    """智能工作区分析器"""

    def __init__(self, workspace_path: str, llm_type: str = "basic"):
        self.workspace_path = workspace_path
        self.state_manager = WorkspaceStateManager(workspace_path)
        self.llm = get_llm_by_type(llm_type)
        # 集成 GitignoreParser 以支持 .gitignore 文件
        self.gitignore_parser = GitignoreParser(workspace_path)

        logger.info(f"智能工作区分析器初始化完成：{workspace_path}")

    async def should_perform_analysis(
        self, task_description: str
    ) -> Tuple[bool, bool, Dict[str, Any]]:
        """
        智能决策是否需要执行环境分析和RAG索引

        Args:
            task_description: 用户任务描述

        Returns:
            (should_analyze_env, should_build_rag, decision_context)
        """
        # 获取工作区状态上下文
        workspace_context = self.state_manager.get_context_for_llm()

        # 如果是首次运行，直接执行分析
        if workspace_context["workspace_status"]["is_first_run"]:
            logger.info("首次运行，直接执行完整分析")
            return (
                True,
                True,
                {
                    "decision_type": "first_run",
                    "reasoning": "首次在此工作区运行，需要完整的环境探测和RAG索引构建",
                    "workspace_context": workspace_context,
                },
            )

        # 使用LLM进行智能决策
        try:
            decision_result = await self._llm_decide_analysis(
                task_description, workspace_context
            )

            should_analyze_env = decision_result.get("analyze_environment", False)
            should_build_rag = decision_result.get("build_rag_index", False)

            logger.info(
                f"LLM决策结果: 环境分析={should_analyze_env}, RAG索引={should_build_rag}"
            )

            return (
                should_analyze_env,
                should_build_rag,
                {
                    "decision_type": "llm_decision",
                    "reasoning": decision_result.get("reasoning", "LLM智能决策"),
                    "confidence": decision_result.get("confidence", 0.5),
                    "workspace_context": workspace_context,
                    "llm_response": decision_result,
                },
            )

        except Exception as e:
            logger.error(f"LLM决策失败，使用默认策略: {e}")

            # 回退到基于规则的决策
            should_analyze_env = (
                self.state_manager.should_perform_environment_analysis()
            )
            should_build_rag = self.state_manager.should_perform_rag_indexing()

            return (
                should_analyze_env,
                should_build_rag,
                {
                    "decision_type": "fallback_rules",
                    "reasoning": "LLM决策失败，使用基于规则的默认策略",
                    "workspace_context": workspace_context,
                    "error": str(e),
                },
            )

    async def _llm_decide_analysis(
        self, task_description: str, workspace_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用LLM进行智能决策"""

        # 构建决策提示
        decision_prompt = apply_prompt_template(
            "intelligent_workspace_decision",
            {
                "task_description": task_description,
                "workspace_status": workspace_context["workspace_status"],
                "analysis_history": workspace_context["analysis_history"],
                "recommendations": workspace_context["recommendations"],
                "current_time": datetime.now().isoformat(),
            },
        )

        # 调用LLM进行决策
        messages = [
            {"role": "system", "content": decision_prompt[0]["content"]},
            {
                "role": "user",
                "content": (
                    f"任务描述：{task_description}\n\n请根据上述工作区状态信息，智能决策是否需要执行环境分析和RAG索引构建。"
                ),
            },
        ]

        response = await self.llm.agenerate(messages)

        # 解析LLM响应
        return self._parse_llm_decision(response)

    def _parse_llm_decision(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM的决策响应"""
        try:
            # 简单的响应解析（可以根据需要改进）
            response_lower = llm_response.lower()

            # 检测环境分析决策
            analyze_env = any(
                keyword in response_lower
                for keyword in [
                    "需要环境分析",
                    "执行环境分析",
                    "环境探测",
                    "analyze environment",
                    "environment analysis",
                ]
            )

            # 检测RAG索引决策
            build_rag = any(
                keyword in response_lower
                for keyword in [
                    "需要rag索引",
                    "构建索引",
                    "建立索引",
                    "build rag",
                    "rag index",
                    "code index",
                ]
            )

            # 检测跳过信号
            skip_signals = ["跳过", "不需要", "skip", "no need", "unnecessary"]
            if any(signal in response_lower for signal in skip_signals):
                if "环境" in response_lower or "environment" in response_lower:
                    analyze_env = False
                if (
                    "rag" in response_lower
                    or "索引" in response_lower
                    or "index" in response_lower
                ):
                    build_rag = False

            # 提取置信度（简单估算）
            confidence = (
                0.8
                if ("建议" in response_lower or "recommend" in response_lower)
                else 0.6
            )

            return {
                "analyze_environment": analyze_env,
                "build_rag_index": build_rag,
                "reasoning": llm_response.strip(),
                "confidence": confidence,
            }

        except Exception as e:
            logger.warning(f"解析LLM决策响应失败: {e}")
            return {
                "analyze_environment": False,
                "build_rag_index": False,
                "reasoning": f"解析失败: {str(e)}",
                "confidence": 0.0,
            }

    async def perform_environment_analysis(self) -> Dict[str, Any]:
        """执行环境分析"""
        logger.info("开始执行环境分析...")

        try:
            # 分析项目结构
            project_structure = await self._analyze_project_structure()

            # 分析环境信息
            environment_info = await self._analyze_environment(project_structure)

            # 生成文本格式的环境分析报告
            text_summary = self._generate_text_summary(
                project_structure, environment_info
            )

            logger.info("环境分析完成")
            return {
                "project_structure": project_structure,
                "environment_info": environment_info,
                "text_summary": text_summary,  # 新增：文本格式摘要
                "success": True,
            }

        except Exception as e:
            logger.error(f"环境分析失败: {e}")
            return {
                "project_structure": {},
                "environment_info": {},
                "text_summary": f"环境分析失败: {str(e)}",
                "success": False,
                "error": str(e),
            }

    async def _analyze_project_structure(self) -> Dict[str, Any]:
        """分析项目结构，支持 .gitignore 规则"""
        workspace_path = Path(self.workspace_path)
        structure_info = {
            "total_files": 0,
            "total_directories": 0,
            "file_types": {},
            "config_files": [],
            "directories": [],
            "directory_structure": {},  # 新增：详细的目录结构
            "main_languages": [],
            "gitignore_excluded_count": 0,  # 新增：被 gitignore 排除的文件数量
        }

        # 基础排除目录（用于性能优化，避免扫描明显无用的目录）
        exclude_dirs = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".coverage",
        }

        # 扫描根目录的直接文件
        for item in workspace_path.iterdir():
            if item.is_file():
                # 检查是否被 .gitignore 排除
                relative_path = str(item.relative_to(workspace_path))
                if self.gitignore_parser.is_ignored(relative_path):
                    structure_info["gitignore_excluded_count"] += 1
                    logger.debug(f"文件被 .gitignore 排除: {relative_path}")
                    continue

                structure_info["total_files"] += 1

                # 统计文件类型
                suffix = item.suffix.lower()
                if suffix:
                    structure_info["file_types"][suffix] = (
                        structure_info["file_types"].get(suffix, 0) + 1
                    )

                # 识别配置文件
                if item.name in [
                    "package.json",
                    "requirements.txt",
                    "pyproject.toml",
                    "Cargo.toml",
                    "go.mod",
                    "conf.yaml",
                    "docker-compose.yml",
                    "Dockerfile",
                    "Makefile",
                ]:
                    structure_info["config_files"].append(item.name)

            elif item.is_dir() and item.name not in exclude_dirs:
                # 检查目录是否被 .gitignore 排除
                relative_dir_path = str(item.relative_to(workspace_path))
                if self.gitignore_parser.is_ignored(relative_dir_path):
                    logger.debug(f"目录被 .gitignore 排除: {relative_dir_path}")
                    continue

                structure_info["total_directories"] += 1
                structure_info["directories"].append(item.name)

                # 初始化当前目录结构
                current_dir_structure = {"files": [], "subdirectories": {}}

                # 扫描第一层和第二层子目录的文件
                try:
                    for subitem in item.iterdir():
                        if subitem.is_file():
                            # 检查子文件是否被 .gitignore 排除
                            relative_subfile_path = str(subitem.relative_to(workspace_path))
                            if self.gitignore_parser.is_ignored(relative_subfile_path):
                                structure_info["gitignore_excluded_count"] += 1
                                continue

                            structure_info["total_files"] += 1
                            current_dir_structure["files"].append(subitem.name)
                            suffix = subitem.suffix.lower()
                            if suffix:
                                structure_info["file_types"][suffix] = (
                                    structure_info["file_types"].get(suffix, 0) + 1
                                )
                        elif subitem.is_dir() and subitem.name not in exclude_dirs:
                            # 检查子目录是否被 .gitignore 排除
                            relative_subdir_path = str(subitem.relative_to(workspace_path))
                            if self.gitignore_parser.is_ignored(relative_subdir_path):
                                continue
                            # 初始化子目录结构
                            subdir_structure = {"files": []}

                            # 扫描第二层子目录的文件
                            try:
                                for subsubitem in subitem.iterdir():
                                    if subsubitem.is_file():
                                        # 检查深层文件是否被 .gitignore 排除
                                        relative_deep_path = str(subsubitem.relative_to(workspace_path))
                                        if self.gitignore_parser.is_ignored(relative_deep_path):
                                            structure_info["gitignore_excluded_count"] += 1
                                            continue

                                        structure_info["total_files"] += 1
                                        subdir_structure["files"].append(
                                            subsubitem.name
                                        )
                                        suffix = subsubitem.suffix.lower()
                                        if suffix:
                                            structure_info["file_types"][suffix] = (
                                                structure_info["file_types"].get(
                                                    suffix, 0
                                                )
                                                + 1
                                            )
                            except (PermissionError, OSError):
                                # 跳过无法访问的第二层目录
                                continue

                            current_dir_structure["subdirectories"][
                                subitem.name
                            ] = subdir_structure
                except (PermissionError, OSError):
                    # 跳过无法访问的目录
                    continue

                # 保存当前目录的详细结构
                structure_info["directory_structure"][item.name] = current_dir_structure

        # 确定主要语言
        common_extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C",
        }

        for ext, count in sorted(
            structure_info["file_types"].items(), key=lambda x: x[1], reverse=True
        ):
            if ext in common_extensions:
                structure_info["main_languages"].append(common_extensions[ext])
            if len(structure_info["main_languages"]) >= 3:
                break

        # 推断项目类型
        if "package.json" in structure_info["config_files"]:
            structure_info["project_type"] = "Node.js"
        elif (
            "requirements.txt" in structure_info["config_files"]
            or "pyproject.toml" in structure_info["config_files"]
        ):
            structure_info["project_type"] = "Python"
        elif "Cargo.toml" in structure_info["config_files"]:
            structure_info["project_type"] = "Rust"
        elif "go.mod" in structure_info["config_files"]:
            structure_info["project_type"] = "Go"

        return structure_info

    async def _analyze_environment(
        self, project_structure: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """分析环境信息"""
        import platform
        import sys

        env_info = {
            "platform": platform.system(),
            "python_version": sys.version,
            "working_directory": self.workspace_path,  # 使用用户指定的工作目录
            "workspace_path": self.workspace_path,
            "timestamp": datetime.now().isoformat(),
        }

        # 检查常见的环境配置
        workspace_path = Path(self.workspace_path)

        # 检查虚拟环境
        venv_indicators = [".venv", "venv", "env", "virtualenv"]
        for indicator in venv_indicators:
            if (workspace_path / indicator).exists():
                env_info["virtual_environment"] = indicator
                break
        else:
            env_info["virtual_environment"] = None

        # 检查包管理器文件
        package_files = {
            "requirements.txt": "pip",
            "pyproject.toml": "pip/poetry/setuptools",
            "package.json": "npm/yarn",
            "Cargo.toml": "cargo",
            "go.mod": "go modules",
        }

        env_info["package_managers"] = []
        for file_name, manager in package_files.items():
            if (workspace_path / file_name).exists():
                env_info["package_managers"].append(manager)

        # 添加项目结构信息到环境信息中
        if project_structure:
            env_info["project_structure"] = {
                "total_files": project_structure.get("total_files", 0),
                "total_directories": project_structure.get("total_directories", 0),
                "directories": project_structure.get("directories", []),
                "directory_structure": project_structure.get("directory_structure", {}),
                "main_languages": project_structure.get("main_languages", []),
                "project_type": project_structure.get("project_type", "Unknown"),
                "config_files": project_structure.get("config_files", []),
                "file_types": project_structure.get("file_types", {}),
            }

        return env_info

    def _generate_text_summary(
        self, project_structure: Dict[str, Any], environment_info: Dict[str, Any]
    ) -> str:
        """Generate environment analysis summary in English Markdown format"""
        try:
            # Extract key information
            total_files = project_structure.get("total_files", 0)
            total_dirs = project_structure.get("total_directories", 0)
            file_types = project_structure.get("file_types", {})
            config_files = project_structure.get("config_files", [])
            directories = project_structure.get("directories", [])
            main_languages = project_structure.get("main_languages", [])
            project_type = project_structure.get("project_type", "Unknown")

            platform = environment_info.get("platform", "Unknown")
            python_version = environment_info.get("python_version", "Unknown")
            working_dir = environment_info.get("working_directory", "Unknown")
            venv = environment_info.get("virtual_environment")
            package_managers = environment_info.get("package_managers", [])
            timestamp = environment_info.get("timestamp", "Unknown")

            # Build Markdown summary
            md_lines = []

            # === Project Overview ===
            md_lines.append("# Project Environment Analysis Report")
            md_lines.append("")
            md_lines.append(f"**Analysis Time:** {timestamp}")
            md_lines.append(f"**Working Directory:** `{working_dir}`")
            md_lines.append("")

            # === Project Structure ===
            md_lines.append("## 📁 Project Structure")
            md_lines.append("")
            md_lines.append(f"- **Project Type:** {project_type}")
            md_lines.append(f"- **Total Files:** {total_files}")
            md_lines.append(f"- **Total Directories:** {total_dirs}")

            if main_languages:
                md_lines.append(f"- **Primary Languages:** {', '.join(main_languages)}")

            # File type distribution
            if file_types:
                md_lines.append("")
                md_lines.append("### File Type Distribution")
                md_lines.append("")
                md_lines.append("| Extension | File Count |")
                md_lines.append("|-----------|------------|")
                for ext, count in sorted(
                    file_types.items(), key=lambda x: x[1], reverse=True
                )[:10]:
                    md_lines.append(f"| `{ext}` | {count} |")

            # Configuration files
            if config_files:
                md_lines.append("")
                md_lines.append("### Configuration Files")
                md_lines.append("")
                for config_file in config_files:
                    md_lines.append(f"- `{config_file}`")

            # Main directories
            if directories:
                md_lines.append("")
                md_lines.append("### Main Directories")
                md_lines.append("")
                for directory in directories[:10]:
                    md_lines.append(f"- `{directory}/`")
                if len(directories) > 10:
                    md_lines.append(
                        f"- *...and {len(directories)-10} more directories*"
                    )

            # Detailed directory structure
            directory_structure = project_structure.get("directory_structure", {})
            if directory_structure:
                md_lines.append("")
                md_lines.append("### Directory Structure Details")
                md_lines.append("")

                # 遍历主要目录
                for dir_name, dir_info in list(directory_structure.items())[
                    :5
                ]:  # 只显示前5个目录
                    md_lines.append(f"#### `{dir_name}/`")

                    # 显示直接文件
                    files = dir_info.get("files", [])
                    if files:
                        md_lines.append(
                            f"- **Files ({len(files)})**: {', '.join([f'`{f}`' for f in files[:8]])}"
                        )
                        if len(files) > 8:
                            md_lines.append(f"  *(+{len(files)-8} more files)*")

                    # 显示子目录
                    subdirs = dir_info.get("subdirectories", {})
                    if subdirs:
                        md_lines.append(f"- **Subdirectories ({len(subdirs)})**:")
                        for subdir_name, subdir_info in list(subdirs.items())[
                            :3
                        ]:  # 只显示前3个子目录
                            subdir_files = subdir_info.get("files", [])
                            if subdir_files:
                                md_lines.append(
                                    f"  - `{subdir_name}/` ({len(subdir_files)} files)"
                                )
                            else:
                                md_lines.append(f"  - `{subdir_name}/`")
                        if len(subdirs) > 3:
                            md_lines.append(
                                f"  *(+{len(subdirs)-3} more subdirectories)*"
                            )

                    md_lines.append("")

                if len(directory_structure) > 5:
                    md_lines.append(
                        f"*...and {len(directory_structure)-5} more directories*"
                    )
                    md_lines.append("")

            md_lines.append("")

            # === Runtime Environment ===
            md_lines.append("## 🔧 Runtime Environment")
            md_lines.append("")
            md_lines.append(f"- **Operating System:** {platform}")
            md_lines.append(
                f"- **Python Version:** {python_version.split()[0] if python_version != 'Unknown' else 'Unknown'}"
            )

            # Virtual environment
            if venv:
                md_lines.append(f"- **Virtual Environment:** `{venv}`")
            else:
                md_lines.append("- **Virtual Environment:** Not detected")

            # Package managers
            if package_managers:
                md_lines.append(
                    f"- **Package Managers:** {', '.join(package_managers)}"
                )
            else:
                md_lines.append("- **Package Managers:** Not detected")

            # === Summary ===
            md_lines.append("")
            md_lines.append("## 📋 Environment Summary")
            md_lines.append("")

            if project_type != "Unknown":
                md_lines.append(f"- **{project_type}** project")
            if main_languages:
                md_lines.append(f"- **{main_languages[0]}** development")
            if total_files > 0:
                md_lines.append(
                    f"- **{total_files}** files, **{total_dirs}** directories"
                )
            if venv:
                md_lines.append(f"- **{venv}** virtual environment")

            return "\n".join(md_lines)

        except Exception as e:
            logger.error(f"Failed to generate text summary: {e}")
            return f"# Error\n\nUnable to generate text summary: {str(e)}"

    def save_analysis_result(
        self,
        project_structure: Dict[str, Any],
        environment_info: Dict[str, Any],
        indexed_files_count: int,
        rag_status: str,
    ) -> WorkspaceAnalysis:
        """保存分析结果"""

        # 生成分析摘要
        main_languages = project_structure.get("main_languages", [])
        project_type = project_structure.get("project_type", "unknown")
        total_files = project_structure.get("total_files", 0)

        summary = (
            f"{project_type}项目，主要语言：{', '.join(main_languages[:2])}，"
            f"共{total_files}个文件，索引{indexed_files_count}个，RAG状态：{rag_status}"
        )

        analysis = WorkspaceAnalysis(
            workspace_hash=self.state_manager.workspace_hash,
            analysis_time=datetime.now(),
            project_structure=project_structure,
            environment_info=environment_info,
            indexed_files_count=indexed_files_count,
            rag_status=rag_status,
            analysis_summary=summary,
        )

        self.state_manager.save_analysis(analysis)
        logger.info(f"分析结果已保存: {summary}")

        return analysis

    def get_workspace_context_for_retrieval(self) -> Optional[Dict[str, Any]]:
        """获取可用于检索的工作区上下文信息"""
        try:
            summary = self.state_manager.get_workspace_summary()
            analyses = self.state_manager.get_analysis_history()

            if not analyses:
                logger.info("无可用的工作区分析历史")
                return None

            latest_analysis = analyses[-1]

            context = {
                "workspace_summary": summary,
                "latest_analysis": {
                    "project_structure": latest_analysis.project_structure,
                    "environment_info": latest_analysis.environment_info,
                    "analysis_summary": latest_analysis.analysis_summary,
                    "rag_status": latest_analysis.rag_status,
                    "indexed_files_count": latest_analysis.indexed_files_count,
                },
                "is_context_available": True,
                "context_age_days": (
                    (datetime.now() - latest_analysis.analysis_time).days
                ),
            }

            logger.info(f"工作区上下文可用，分析时间：{latest_analysis.analysis_time}")
            return context

        except Exception as e:
            logger.error(f"获取工作区上下文失败: {e}")
            return None
