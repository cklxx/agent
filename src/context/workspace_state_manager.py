"""
工作区状态管理器 - 跟踪agent在工作区的运行状态
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceAnalysis:
    """工作区分析结果"""
    workspace_hash: str
    analysis_time: datetime
    project_structure: Dict[str, Any]
    environment_info: Dict[str, Any]
    indexed_files_count: int
    rag_status: str  # "indexed", "partial", "none"
    analysis_summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于JSON序列化"""
        result = asdict(self)
        result['analysis_time'] = self.analysis_time.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkspaceAnalysis':
        """从字典创建实例"""
        data['analysis_time'] = datetime.fromisoformat(data['analysis_time'])
        return cls(**data)


class WorkspaceStateManager:
    """工作区状态管理器"""
    
    def __init__(self, workspace_path: str, state_file: str = "temp/workspace_state.json"):
        self.workspace_path = Path(workspace_path)
        self.state_file = Path(state_file)
        
        # 确保状态文件目录存在
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成工作区唯一标识符
        self.workspace_hash = self._generate_workspace_hash()
        
        # 加载已有状态
        self.state_data = self._load_state()
        
        logger.info(f"工作区状态管理器初始化：{workspace_path} (hash: {self.workspace_hash[:8]})")
    
    def _generate_workspace_hash(self) -> str:
        """生成工作区唯一标识符"""
        workspace_str = str(self.workspace_path.resolve())
        return hashlib.md5(workspace_str.encode('utf-8')).hexdigest()
    
    def _load_state(self) -> Dict[str, Any]:
        """加载状态数据"""
        if not self.state_file.exists():
            return {
                "workspaces": {},
                "last_updated": datetime.now().isoformat()
            }
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"无法加载状态文件，使用默认状态: {e}")
            return {
                "workspaces": {},
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_state(self):
        """保存状态数据"""
        try:
            self.state_data["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")
    
    def is_first_run(self, force_check: bool = False) -> bool:
        """
        检查是否是当前工作区的首次运行
        
        Args:
            force_check: 是否强制检查（忽略缓存）
            
        Returns:
            True如果是首次运行，False如果已经分析过
        """
        workspace_data = self.state_data["workspaces"].get(self.workspace_hash)
        
        if not workspace_data:
            logger.info("工作区首次运行，需要进行环境探测和RAG索引")
            return True
        
        # 检查最后分析时间是否过期（7天）
        last_analysis = datetime.fromisoformat(workspace_data.get("last_analysis", "1970-01-01T00:00:00"))
        if datetime.now() - last_analysis > timedelta(days=7):
            logger.info("工作区分析已过期，需要重新分析")
            return True
        
        # 检查RAG状态
        rag_status = workspace_data.get("rag_status", "none")
        if rag_status == "none":
            logger.info("RAG索引不存在，需要构建")
            return True
        
        if force_check:
            logger.info("强制检查模式，将重新分析")
            return True
        
        logger.info("工作区已分析过，跳过环境探测")
        return False
    
    def get_analysis_history(self) -> List[WorkspaceAnalysis]:
        """获取工作区分析历史"""
        workspace_data = self.state_data["workspaces"].get(self.workspace_hash, {})
        analyses_data = workspace_data.get("analyses", [])
        
        analyses = []
        for analysis_data in analyses_data:
            try:
                analysis = WorkspaceAnalysis.from_dict(analysis_data)
                analyses.append(analysis)
            except Exception as e:
                logger.warning(f"解析分析历史失败: {e}")
        
        return analyses
    
    def save_analysis(self, analysis: WorkspaceAnalysis):
        """保存工作区分析结果"""
        if self.workspace_hash not in self.state_data["workspaces"]:
            self.state_data["workspaces"][self.workspace_hash] = {
                "workspace_path": str(self.workspace_path),
                "first_analysis": datetime.now().isoformat(),
                "analyses": []
            }
        
        workspace_data = self.state_data["workspaces"][self.workspace_hash]
        workspace_data["last_analysis"] = analysis.analysis_time.isoformat()
        workspace_data["rag_status"] = analysis.rag_status
        workspace_data["indexed_files_count"] = analysis.indexed_files_count
        
        # 保存分析历史（最多保留10个）
        workspace_data["analyses"].append(analysis.to_dict())
        workspace_data["analyses"] = workspace_data["analyses"][-10:]
        
        self._save_state()
        logger.info(f"工作区分析结果已保存: {analysis.rag_status}")
    
    def get_workspace_summary(self) -> Dict[str, Any]:
        """获取工作区状态摘要"""
        workspace_data = self.state_data["workspaces"].get(self.workspace_hash)
        
        if not workspace_data:
            return {
                "workspace_hash": self.workspace_hash,
                "workspace_path": str(self.workspace_path),
                "is_first_run": True,
                "rag_status": "none",
                "indexed_files_count": 0,
                "last_analysis": None,
                "analyses_count": 0
            }
        
        return {
            "workspace_hash": self.workspace_hash,
            "workspace_path": str(self.workspace_path),
            "is_first_run": self.is_first_run(),
            "rag_status": workspace_data.get("rag_status", "none"),
            "indexed_files_count": workspace_data.get("indexed_files_count", 0),
            "last_analysis": workspace_data.get("last_analysis"),
            "analyses_count": len(workspace_data.get("analyses", []))
        }
    
    def should_perform_rag_indexing(self, llm_decision: Optional[bool] = None) -> bool:
        """
        智能判断是否应该执行RAG索引
        
        Args:
            llm_decision: LLM的决策结果（可选）
            
        Returns:
            是否应该执行RAG索引
        """
        # 首次运行，默认需要索引
        if self.is_first_run():
            return True
        
        # 如果LLM明确决定，遵循其决策
        if llm_decision is not None:
            logger.info(f"遵循LLM决策：{'执行' if llm_decision else '跳过'}RAG索引")
            return llm_decision
        
        # 检查现有RAG状态
        workspace_data = self.state_data["workspaces"].get(self.workspace_hash, {})
        rag_status = workspace_data.get("rag_status", "none")
        
        if rag_status == "none":
            logger.info("RAG索引不存在，需要构建")
            return True
        elif rag_status == "partial":
            logger.info("RAG索引不完整，建议重新构建")
            return True
        else:
            logger.info("RAG索引存在且完整，跳过构建")
            return False
    
    def should_perform_environment_analysis(self, llm_decision: Optional[bool] = None) -> bool:
        """
        智能判断是否应该执行环境分析
        
        Args:
            llm_decision: LLM的决策结果（可选）
            
        Returns:
            是否应该执行环境分析
        """
        # 首次运行，默认需要分析
        if self.is_first_run():
            return True
        
        # 如果LLM明确决定，遵循其决策
        if llm_decision is not None:
            logger.info(f"遵循LLM决策：{'执行' if llm_decision else '跳过'}环境分析")
            return llm_decision
        
        # 检查最后分析时间
        workspace_data = self.state_data["workspaces"].get(self.workspace_hash, {})
        last_analysis = workspace_data.get("last_analysis")
        
        if not last_analysis:
            logger.info("无环境分析历史，需要分析")
            return True
        
        last_time = datetime.fromisoformat(last_analysis)
        if datetime.now() - last_time > timedelta(days=7):
            logger.info("环境分析已过期，需要重新分析")
            return True
        
        logger.info("环境分析较新，跳过分析")
        return False
    
    def mark_indexing_complete(self, indexed_files_count: int, status: str = "indexed"):
        """标记索引构建完成"""
        if self.workspace_hash not in self.state_data["workspaces"]:
            self.state_data["workspaces"][self.workspace_hash] = {
                "workspace_path": str(self.workspace_path),
                "first_analysis": datetime.now().isoformat(),
                "analyses": []
            }
        
        workspace_data = self.state_data["workspaces"][self.workspace_hash]
        workspace_data["rag_status"] = status
        workspace_data["indexed_files_count"] = indexed_files_count
        workspace_data["last_indexing"] = datetime.now().isoformat()
        
        self._save_state()
        logger.info(f"RAG索引状态已更新: {status}, 文件数: {indexed_files_count}")
    
    def get_context_for_llm(self) -> Dict[str, Any]:
        """获取供LLM判断的上下文信息"""
        summary = self.get_workspace_summary()
        analyses = self.get_analysis_history()
        
        # 构建上下文信息
        context = {
            "workspace_status": summary,
            "analysis_history": [
                {
                    "time": analysis.analysis_time.isoformat(),
                    "files_count": analysis.indexed_files_count,
                    "rag_status": analysis.rag_status,
                    "summary": analysis.analysis_summary
                }
                for analysis in analyses[-3:]  # 最近3次分析
            ],
            "recommendations": self._generate_recommendations(summary, analyses)
        }
        
        return context
    
    def _generate_recommendations(self, summary: Dict[str, Any], analyses: List[WorkspaceAnalysis]) -> List[str]:
        """生成智能建议"""
        recommendations = []
        
        if summary["is_first_run"]:
            recommendations.append("建议执行完整的环境分析和RAG索引，为后续任务提供最佳上下文")
        elif summary["rag_status"] == "none":
            recommendations.append("未发现RAG索引，建议构建以提升代码理解能力")
        elif summary["rag_status"] == "partial":
            recommendations.append("RAG索引不完整，建议重新构建以获得完整的代码知识库")
        else:
            recommendations.append("RAG索引完整，可直接使用现有知识库")
        
        # 基于分析历史的建议
        if len(analyses) > 2:
            recent_analyses = analyses[-2:]
            if all(a.rag_status == "indexed" for a in recent_analyses):
                recommendations.append("最近的分析表明索引状态良好，可以专注于任务执行")
        
        return recommendations 