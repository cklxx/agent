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

logger = logging.getLogger(__name__)


class IntelligentWorkspaceAnalyzer:
    """智能工作区分析器"""

    def __init__(self, workspace_path: str, llm_type: str = "basic"):
        self.workspace_path = workspace_path
        self.state_manager = WorkspaceStateManager(workspace_path)
        self.llm = get_llm_by_type(llm_type)

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
            environment_info = await self._analyze_environment()

            # 生成文本格式的环境分析报告
            text_summary = self._generate_text_summary(
                project_structure, environment_info
            )

            analysis_result = {
                "project_structure": project_structure,
                "environment_info": environment_info,
                "text_summary": text_summary,  # 新增：文本格式摘要
                "success": True,
            }

            logger.info("环境分析完成")
            return analysis_result

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
        """分析项目结构"""
        workspace_path = Path(self.workspace_path)
        structure_info = {
            "total_files": 0,
            "total_directories": 0,
            "file_types": {},
            "config_files": [],
            "directories": [],
            "main_languages": [],
        }

        # 只扫描根目录和第一层子目录，避免扫描.venv等深层目录
        exclude_dirs = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
            ".pytest_cache",
            ".coverage",
            "temp",
        }

        # 扫描根目录的直接文件
        for item in workspace_path.iterdir():
            if item.is_file():
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
                structure_info["total_directories"] += 1
                structure_info["directories"].append(item.name)

                # 扫描第一层子目录的文件（不再深入）
                try:
                    for subitem in item.iterdir():
                        if subitem.is_file():
                            structure_info["total_files"] += 1
                            suffix = subitem.suffix.lower()
                            if suffix:
                                structure_info["file_types"][suffix] = (
                                    structure_info["file_types"].get(suffix, 0) + 1
                                )
                except (PermissionError, OSError):
                    # 跳过无法访问的目录
                    continue

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

    async def _analyze_environment(self) -> Dict[str, Any]:
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

        return env_info

    def _generate_text_summary(
        self, project_structure: Dict[str, Any], environment_info: Dict[str, Any]
    ) -> str:
        """生成环境分析结果的文本格式摘要"""
        try:
            # 提取关键信息
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

            # 构建文本摘要
            text_lines = []

            # === 项目概览 ===
            text_lines.append("=== 项目环境分析报告 ===")
            text_lines.append(f"分析时间: {timestamp}")
            text_lines.append(f"工作目录: {working_dir}")
            text_lines.append("")

            # === 项目结构 ===
            text_lines.append("=== 项目结构 ===")
            text_lines.append(f"项目类型: {project_type}")
            text_lines.append(f"总文件数: {total_files}")
            text_lines.append(f"总目录数: {total_dirs}")

            if main_languages:
                text_lines.append(f"主要编程语言: {', '.join(main_languages)}")

            # 文件类型分布
            if file_types:
                text_lines.append("")
                text_lines.append("文件类型分布:")
                for ext, count in sorted(
                    file_types.items(), key=lambda x: x[1], reverse=True
                )[:10]:
                    text_lines.append(f"  {ext}: {count}个文件")

            # 配置文件
            if config_files:
                text_lines.append("")
                text_lines.append(f"配置文件: {', '.join(config_files)}")

            # 主要目录
            if directories:
                text_lines.append("")
                text_lines.append(f"主要目录: {', '.join(directories[:10])}")
                if len(directories) > 10:
                    text_lines.append(f"  (还有{len(directories)-10}个其他目录)")

            text_lines.append("")

            # === 运行环境 ===
            text_lines.append("=== 运行环境 ===")
            text_lines.append(f"操作系统: {platform}")
            text_lines.append(
                f"Python版本: {python_version.split()[0] if python_version != 'Unknown' else 'Unknown'}"
            )

            # 虚拟环境
            if venv:
                text_lines.append(f"虚拟环境: {venv}")
            else:
                text_lines.append("虚拟环境: 未检测到")

            # 包管理器
            if package_managers:
                text_lines.append(f"包管理器: {', '.join(package_managers)}")
            else:
                text_lines.append("包管理器: 未检测到")

            # === 总结 ===
            text_lines.append("")
            text_lines.append("=== 环境总结 ===")
            if project_type != "Unknown":
                text_lines.append(f"这是一个{project_type}项目")
            if main_languages:
                text_lines.append(f"主要使用{main_languages[0]}进行开发")
            if total_files > 0:
                text_lines.append(f"项目规模：{total_files}个文件，{total_dirs}个目录")
            if venv:
                text_lines.append(f"开发环境：配置了{venv}虚拟环境")

            return "\n".join(text_lines)

        except Exception as e:
            logger.error(f"生成文本摘要失败: {e}")
            return f"无法生成文本摘要: {str(e)}"

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
