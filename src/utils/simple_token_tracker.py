"""
简化版Token统计工具

提供基本的session管理和消费记录功能，用户可以手动添加token使用情况。

使用示例：
    tracker = SimpleTokenTracker()

    # 开启session
    tracker.start_session("测试对话")

    # 用户手动添加消费记录
    tracker.add_usage(input_tokens=100, output_tokens=50, cost=0.001, model="gpt-4o-mini")
    tracker.add_usage(input_tokens=200, output_tokens=80, cost=0.002, model="gpt-4o-mini")

    # 查看当前统计
    report = tracker.get_current_report()
    print(f"总费用: ${report['total_cost']:.6f}")

    # 结束session
    tracker.end_session()

    # 获取最终报告
    final_report = tracker.get_session_report("测试对话")
"""

import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class UsageRecord:
    """单次使用记录"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


class SimpleTokenTracker:
    """简化版Token统计器"""

    def __init__(self):
        """初始化统计器"""
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.current_session: Optional[str] = None
        self._session_start_time: Optional[float] = None

    def start_session(self, session_name: str) -> None:
        """
        开启新的统计session

        Args:
            session_name: session名称
        """
        if self.current_session:
            print(f"警告: 当前session '{self.current_session}' 尚未结束，将自动结束")
            self.end_session()

        self.current_session = session_name
        self._session_start_time = time.time()

        # 初始化session数据
        self.sessions[session_name] = {
            "session_name": session_name,
            "start_time": datetime.now().isoformat(),
            "end_time": "",
            "duration_seconds": 0.0,
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "records": [],
            "model_breakdown": {},
        }

        print(f"✅ Session '{session_name}' 已开启")

    def add_usage(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        model: str = "unknown",
    ) -> None:
        """
        添加token使用记录

        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            cost: 费用
            model: 模型名称
        """
        if not self.current_session:
            raise ValueError("没有活跃的session，请先调用 start_session()")

        # 创建使用记录
        record = UsageRecord(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            model=model,
        )

        # 更新当前session统计
        session_data = self.sessions[self.current_session]
        session_data["total_calls"] += 1
        session_data["total_input_tokens"] += input_tokens
        session_data["total_output_tokens"] += output_tokens
        session_data["total_tokens"] += record.total_tokens
        session_data["total_cost"] += cost
        session_data["records"].append(asdict(record))

        # 更新模型分类统计
        if model not in session_data["model_breakdown"]:
            session_data["model_breakdown"][model] = {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
            }

        model_stats = session_data["model_breakdown"][model]
        model_stats["calls"] += 1
        model_stats["input_tokens"] += input_tokens
        model_stats["output_tokens"] += output_tokens
        model_stats["total_tokens"] += record.total_tokens
        model_stats["cost"] += cost

        print(
            f"📊 已添加使用记录: {input_tokens}+{output_tokens}={record.total_tokens} tokens, ${cost:.6f} ({model})"
        )

    def get_current_report(self) -> Dict[str, Any]:
        """
        获取当前session的统计报告

        Returns:
            当前session的统计数据
        """
        if not self.current_session:
            return {"error": "没有活跃的session"}

        session_data = self.sessions[self.current_session].copy()

        # 计算当前持续时间
        if self._session_start_time:
            session_data["current_duration_seconds"] = (
                time.time() - self._session_start_time
            )

        return session_data

    def end_session(self) -> Optional[Dict[str, Any]]:
        """
        结束当前session

        Returns:
            结束的session统计报告
        """
        if not self.current_session:
            print("警告: 没有活跃的session")
            return None

        # 更新结束时间和持续时间
        session_data = self.sessions[self.current_session]
        session_data["end_time"] = datetime.now().isoformat()

        if self._session_start_time:
            session_data["duration_seconds"] = time.time() - self._session_start_time

        ended_session = self.current_session
        report = session_data.copy()

        # 清理当前session状态
        self.current_session = None
        self._session_start_time = None

        print(f"✅ Session '{ended_session}' 已结束")
        print(
            f"📊 总计: {report['total_calls']}次调用, {report['total_tokens']:,} tokens, ${report['total_cost']:.6f}"
        )

        return report

    def get_session_report(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定session的报告

        Args:
            session_name: session名称

        Returns:
            session统计报告，如果不存在则返回None
        """
        return self.sessions.get(session_name)

    def list_sessions(self) -> List[str]:
        """
        列出所有session名称

        Returns:
            session名称列表
        """
        return list(self.sessions.keys())

    def print_session_summary(self, session_name: Optional[str] = None) -> None:
        """
        打印session统计摘要

        Args:
            session_name: session名称，如果不指定则打印当前session
        """
        if session_name is None:
            if not self.current_session:
                print("没有指定session且无活跃session")
                return
            session_name = self.current_session
            data = self.get_current_report()
        else:
            data = self.get_session_report(session_name)
            if not data:
                print(f"Session '{session_name}' 不存在")
                return

        print(f"\n=== Session '{session_name}' 统计摘要 ===")
        print(f"调用次数: {data['total_calls']}")
        print(
            f"总Token: {data['total_tokens']:,} (输入: {data['total_input_tokens']:,}, 输出: {data['total_output_tokens']:,})"
        )
        print(f"总费用: ${data['total_cost']:.6f}")

        if data.get("duration_seconds", 0) > 0:
            print(f"持续时间: {data['duration_seconds']:.2f} 秒")
        elif data.get("current_duration_seconds", 0) > 0:
            print(f"当前持续时间: {data['current_duration_seconds']:.2f} 秒")

        if data["model_breakdown"]:
            print("\n模型使用分布:")
            for model, stats in data["model_breakdown"].items():
                print(
                    f"  {model}: {stats['calls']}次, {stats['total_tokens']:,} tokens, ${stats['cost']:.6f}"
                )

    def export_session(self, session_name: str, file_path: str) -> bool:
        """
        导出session数据到JSON文件

        Args:
            session_name: session名称
            file_path: 导出文件路径

        Returns:
            是否成功导出
        """
        session_data = self.get_session_report(session_name)
        if not session_data:
            print(f"Session '{session_name}' 不存在")
            return False

        try:
            export_data = {
                "export_time": datetime.now().isoformat(),
                "session": session_data,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Session '{session_name}' 已导出到: {file_path}")
            return True

        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return False

    def export_all_sessions(self, file_path: str) -> bool:
        """
        导出所有session数据到JSON文件

        Args:
            file_path: 导出文件路径

        Returns:
            是否成功导出
        """
        try:
            export_data = {
                "export_time": datetime.now().isoformat(),
                "sessions": self.sessions,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 所有sessions已导出到: {file_path}")
            return True

        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return False

    def clear_session(self, session_name: str) -> bool:
        """
        删除指定session

        Args:
            session_name: session名称

        Returns:
            是否成功删除
        """
        if session_name not in self.sessions:
            print(f"Session '{session_name}' 不存在")
            return False

        if self.current_session == session_name:
            self.current_session = None
            self._session_start_time = None

        del self.sessions[session_name]
        print(f"✅ Session '{session_name}' 已删除")
        return True

    def clear_all_sessions(self) -> None:
        """清除所有session数据"""
        self.sessions.clear()
        self.current_session = None
        self._session_start_time = None
        print("✅ 所有sessions已清除")


# 便捷函数
def create_tracker() -> SimpleTokenTracker:
    """
    创建新的token统计器

    Returns:
        SimpleTokenTracker实例
    """
    return SimpleTokenTracker()


# 全局实例（可选使用）
_global_tracker = None


def get_global_tracker() -> SimpleTokenTracker:
    """
    获取全局token统计器实例

    Returns:
        全局SimpleTokenTracker实例
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = SimpleTokenTracker()
    return _global_tracker
