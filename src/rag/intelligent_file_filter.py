"""
Intelligent File Filter for RAG Indexing

This module provides smart file filtering capabilities to determine which files
should be indexed for RAG retrieval. It combines rule-based filtering with
LLM-based intelligent decisions to avoid indexing irrelevant files.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)


class FileRelevance(Enum):
    """文件相关性级别"""
    HIGH = "high"          # 核心项目代码，必须索引
    MEDIUM = "medium"      # 有用的配置或文档文件
    LOW = "low"           # 可选索引的文件
    EXCLUDE = "exclude"    # 应该排除的文件


@dataclass
class FileClassification:
    """文件分类结果"""
    path: str
    relevance: FileRelevance
    reason: str
    file_type: str
    size_kb: float
    is_virtual_env: bool = False
    is_third_party: bool = False
    is_generated: bool = False


class IntelligentFileFilter:
    """智能文件过滤器"""
    
    def __init__(self, repo_path: str, llm_type: str = "basic"):
        self.repo_path = Path(repo_path)
        self.llm = get_llm_by_type(llm_type)
        
        # 虚拟环境目录模式
        self.venv_patterns = {
            # Python 虚拟环境
            r"\.?venv",
            r"\.?env",
            r"ENV",
            r"virtualenv",
            r"\.virtualenv",
            r"__pycache__",
            r"\.pytest_cache",
            r"\.mypy_cache",
            r"\.tox",
            
            # Node.js
            r"node_modules",
            r"\.npm",
            r"\.yarn",
            r"\.pnpm",
            
            # 其他语言包管理器
            r"vendor",      # Go, PHP
            r"target",      # Rust, Java
            r"build",       # 通用构建目录
            r"dist",        # 分发目录
            r"out",         # 输出目录
            r"bin",         # 二进制目录
            r"obj",         # 对象文件目录
            
            # IDE和工具目录
            r"\.idea",
            r"\.vscode",
            r"\.vs",
            r"\.gradle",
            r"\.maven",
        }
        
        # 第三方库文件模式
        self.third_party_patterns = {
            # Python 包
            r"site-packages",
            r"dist-info",
            r"egg-info",
            
            # 静态依赖目录
            r"lib/python\d+\.\d+",
            r"lib64",
            r"include",
            r"Scripts",  # Windows 虚拟环境
            r"pyvenv\.cfg",
        }
        
        # 生成文件模式
        self.generated_patterns = {
            r".*\.pyc$",
            r".*\.pyo$",
            r".*\.pyd$",
            r".*\.so$",
            r".*\.dll$",
            r".*\.dylib$",
            r".*\.egg$",
            r".*\.whl$",
            r".*\.lock$",  # 锁定文件通常是生成的
            r".*-lock\.json$",
            r"coverage\.xml$",
            r"\.coverage$",
            r".*\.log$",
            r".*\.tmp$",
            r".*\.temp$",
        }
        
        # 高相关性文件模式
        self.high_relevance_patterns = {
            # 核心代码文件
            r".*\.py$",
            r".*\.js$",
            r".*\.ts$",
            r".*\.jsx$",
            r".*\.tsx$",
            r".*\.java$",
            r".*\.cpp?$",
            r".*\.h(pp)?$",
            r".*\.rs$",
            r".*\.go$",
            
            # 关键配置文件
            r"^[^/]*\.ya?ml$",  # 根目录的yaml文件
            r"^[^/]*\.json$",   # 根目录的json文件
            r"^[^/]*\.toml$",   # 根目录的toml文件
            r"^(README|LICENSE|CHANGELOG).*",
            r"^requirements.*\.txt$",
            r"^setup\.(py|cfg)$",
            r"^pyproject\.toml$",
            r"^Dockerfile.*",
            r"^Makefile$",
            r"^package\.json$",
        }
        
        logger.info(f"智能文件过滤器初始化完成：{repo_path}")
    
    def classify_file(self, file_path: str) -> FileClassification:
        """分类单个文件"""
        full_path = self.repo_path / file_path
        relative_path = file_path
        
        # 基本信息
        file_size = full_path.stat().st_size / 1024 if full_path.exists() else 0
        file_type = self._detect_file_type(relative_path)
        
        # 规则检查
        is_virtual_env = self._is_virtual_env_file(relative_path)
        is_third_party = self._is_third_party_file(relative_path)
        is_generated = self._is_generated_file(relative_path)
        
        # 确定相关性
        if is_virtual_env or is_third_party or is_generated:
            relevance = FileRelevance.EXCLUDE
            reason = self._get_exclusion_reason(is_virtual_env, is_third_party, is_generated)
        else:
            relevance = self._determine_relevance(relative_path, file_type, file_size)
            reason = self._get_relevance_reason(relevance, file_type)
        
        return FileClassification(
            path=relative_path,
            relevance=relevance,
            reason=reason,
            file_type=file_type,
            size_kb=file_size,
            is_virtual_env=is_virtual_env,
            is_third_party=is_third_party,
            is_generated=is_generated
        )
    
    def batch_classify_files(self, file_paths: List[str]) -> List[FileClassification]:
        """批量分类文件"""
        classifications = []
        
        for file_path in file_paths:
            try:
                classification = self.classify_file(file_path)
                classifications.append(classification)
            except Exception as e:
                logger.warning(f"分类文件失败 {file_path}: {e}")
                # 创建默认分类
                classifications.append(FileClassification(
                    path=file_path,
                    relevance=FileRelevance.EXCLUDE,
                    reason=f"分类失败: {str(e)}",
                    file_type="unknown",
                    size_kb=0
                ))
        
        return classifications
    
    async def llm_classify_files(self, file_paths: List[str], task_context: str = "") -> List[FileClassification]:
        """使用LLM智能分类文件"""
        try:
            # 首先进行规则分类
            rule_classifications = self.batch_classify_files(file_paths)
            
            # 对不确定的文件使用LLM分类
            uncertain_files = [
                c for c in rule_classifications 
                if c.relevance in [FileRelevance.MEDIUM, FileRelevance.LOW]
            ]
            
            if not uncertain_files or len(uncertain_files) > 50:  # 避免LLM调用过多文件
                return rule_classifications
            
            llm_classifications = await self._llm_classify_uncertain_files(uncertain_files, task_context)
            
            # 合并结果
            final_classifications = []
            llm_dict = {c.path: c for c in llm_classifications}
            
            for rule_class in rule_classifications:
                if rule_class.path in llm_dict:
                    final_classifications.append(llm_dict[rule_class.path])
                else:
                    final_classifications.append(rule_class)
            
            return final_classifications
            
        except Exception as e:
            logger.error(f"LLM文件分类失败: {e}")
            return self.batch_classify_files(file_paths)
    
    async def _llm_classify_uncertain_files(
        self, 
        uncertain_files: List[FileClassification],
        task_context: str
    ) -> List[FileClassification]:
        """使用LLM对不确定的文件进行分类"""
        
        # 构建文件信息
        file_info = []
        for f in uncertain_files[:20]:  # 限制数量
            file_info.append({
                "path": f.path,
                "type": f.file_type,
                "size_kb": f.size_kb,
                "current_relevance": f.relevance.value
            })
        
        # 构建LLM提示
        try:
            # 延迟导入避免循环导入
            from src.prompts.template import apply_prompt_template
            
            prompt_messages = apply_prompt_template("intelligent_file_classification", {
                "messages": [],  # 添加必需的messages字段
                "files": file_info,
                "task_context": task_context or "一般代码开发任务",
                "repo_path": str(self.repo_path)
            })
            
            response = await self.llm.agenerate(prompt_messages)
            
            # 解析LLM响应
            return self._parse_llm_classification_response(response, uncertain_files)
            
        except Exception as e:
            logger.warning(f"LLM分类失败，使用规则分类: {e}")
            return uncertain_files
    
    def _parse_llm_classification_response(
        self, 
        llm_response: str, 
        original_files: List[FileClassification]
    ) -> List[FileClassification]:
        """解析LLM分类响应"""
        # 简单的响应解析实现
        updated_files = []
        file_dict = {f.path: f for f in original_files}
        
        lines = llm_response.strip().split('\n')
        for line in lines:
            if ':' in line:
                try:
                    path_part = line.split(':')[0].strip()
                    relevance_part = line.split(':')[1].strip().lower()
                    
                    if path_part in file_dict:
                        original = file_dict[path_part]
                        
                        # 解析相关性
                        if 'high' in relevance_part or '高' in relevance_part:
                            new_relevance = FileRelevance.HIGH
                        elif 'exclude' in relevance_part or '排除' in relevance_part:
                            new_relevance = FileRelevance.EXCLUDE
                        elif 'low' in relevance_part or '低' in relevance_part:
                            new_relevance = FileRelevance.LOW
                        else:
                            new_relevance = FileRelevance.MEDIUM
                        
                        updated_files.append(FileClassification(
                            path=original.path,
                            relevance=new_relevance,
                            reason=f"LLM分类: {relevance_part}",
                            file_type=original.file_type,
                            size_kb=original.size_kb,
                            is_virtual_env=original.is_virtual_env,
                            is_third_party=original.is_third_party,
                            is_generated=original.is_generated
                        ))
                except Exception as e:
                    logger.debug(f"解析LLM响应行失败: {line}, {e}")
        
        # 对未处理的文件保留原分类
        processed_paths = {f.path for f in updated_files}
        for original in original_files:
            if original.path not in processed_paths:
                updated_files.append(original)
        
        return updated_files
    
    def _is_virtual_env_file(self, file_path: str) -> bool:
        """检查是否是虚拟环境文件"""
        path_lower = file_path.lower()
        
        for pattern in self.venv_patterns:
            if re.search(pattern, path_lower):
                return True
        
        return False
    
    def _is_third_party_file(self, file_path: str) -> bool:
        """检查是否是第三方库文件"""
        path_lower = file_path.lower()
        
        for pattern in self.third_party_patterns:
            if re.search(pattern, path_lower):
                return True
        
        return False
    
    def _is_generated_file(self, file_path: str) -> bool:
        """检查是否是生成文件"""
        for pattern in self.generated_patterns:
            if re.match(pattern, file_path):
                return True
        
        return False
    
    def _determine_relevance(self, file_path: str, file_type: str, file_size: float) -> FileRelevance:
        """基于规则确定文件相关性"""
        # 检查高相关性模式
        for pattern in self.high_relevance_patterns:
            if re.match(pattern, file_path):
                return FileRelevance.HIGH
        
        # 基于文件类型和大小判断
        if file_type in ["python", "javascript", "typescript", "java", "cpp", "rust", "go"]:
            return FileRelevance.HIGH
        elif file_type in ["yaml", "json", "toml", "markdown", "text"]:
            return FileRelevance.MEDIUM
        elif file_size > 1024:  # 大于1MB的文件降低优先级
            return FileRelevance.LOW
        else:
            return FileRelevance.MEDIUM
    
    def _detect_file_type(self, file_path: str) -> str:
        """检测文件类型"""
        suffix = Path(file_path).suffix.lower()
        
        type_mapping = {
            ".py": "python",
            ".js": "javascript", 
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp", ".c": "cpp", ".h": "cpp", ".hpp": "cpp",
            ".rs": "rust",
            ".go": "go",
            ".yaml": "yaml", ".yml": "yaml",
            ".json": "json",
            ".toml": "toml",
            ".md": "markdown",
            ".txt": "text",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".sh": "shell", ".bash": "shell",
        }
        
        return type_mapping.get(suffix, "other")
    
    def _get_exclusion_reason(self, is_venv: bool, is_third_party: bool, is_generated: bool) -> str:
        """获取排除原因"""
        reasons = []
        if is_venv:
            reasons.append("虚拟环境文件")
        if is_third_party:
            reasons.append("第三方库文件")
        if is_generated:
            reasons.append("生成文件")
        
        return "、".join(reasons)
    
    def _get_relevance_reason(self, relevance: FileRelevance, file_type: str) -> str:
        """获取相关性原因"""
        if relevance == FileRelevance.HIGH:
            return f"核心{file_type}代码文件"
        elif relevance == FileRelevance.MEDIUM:
            return f"有用的{file_type}配置文件"
        elif relevance == FileRelevance.LOW:
            return f"可选的{file_type}文件"
        else:
            return "应该排除"
    
    def filter_files_for_indexing(self, file_paths: List[str]) -> Tuple[List[str], Dict[str, Any]]:
        """过滤文件用于索引"""
        classifications = self.batch_classify_files(file_paths)
        
        # 分别收集不同相关性的文件
        high_relevance = []
        medium_relevance = []
        low_relevance = []
        excluded = []
        
        for c in classifications:
            if c.relevance == FileRelevance.HIGH:
                high_relevance.append(c.path)
            elif c.relevance == FileRelevance.MEDIUM:
                medium_relevance.append(c.path)
            elif c.relevance == FileRelevance.LOW:
                low_relevance.append(c.path)
            else:
                excluded.append(c.path)
        
        # 默认索引高和中等相关性的文件
        files_to_index = high_relevance + medium_relevance
        
        stats = {
            "total_files": len(file_paths),
            "files_to_index": len(files_to_index),
            "high_relevance": len(high_relevance),
            "medium_relevance": len(medium_relevance), 
            "low_relevance": len(low_relevance),
            "excluded": len(excluded),
            "exclusion_breakdown": self._get_exclusion_breakdown(classifications)
        }
        
        logger.info(f"文件过滤完成: {stats['files_to_index']}/{stats['total_files']} 文件将被索引")
        
        return files_to_index, stats
    
    def _get_exclusion_breakdown(self, classifications: List[FileClassification]) -> Dict[str, int]:
        """获取排除细分统计"""
        breakdown = {
            "virtual_env": 0,
            "third_party": 0,
            "generated": 0,
            "other": 0
        }
        
        for c in classifications:
            if c.relevance == FileRelevance.EXCLUDE:
                if c.is_virtual_env:
                    breakdown["virtual_env"] += 1
                elif c.is_third_party:
                    breakdown["third_party"] += 1
                elif c.is_generated:
                    breakdown["generated"] += 1
                else:
                    breakdown["other"] += 1
        
        return breakdown 