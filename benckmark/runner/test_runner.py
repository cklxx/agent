#!/usr/bin/env python3
"""
AI Agent 编程能力测试集合 - 主测试运行器

功能:
- 管理和执行各级别编程任务测试
- 提供多维度评估和评分
- 生成详细的测试报告
- 支持并行执行和沙箱隔离
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml
from dataclasses import dataclass, asdict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestTask:
    """测试任务数据结构"""
    id: str
    level: str
    domain: str
    title: str
    description: str
    input_spec: Dict[str, Any]
    output_spec: Dict[str, Any]
    evaluation_criteria: Dict[str, Any]
    test_cases: List[Dict[str, Any]]
    time_limit: int = 300  # 5分钟默认超时

@dataclass
class TestResult:
    """测试结果数据结构"""
    task_id: str
    success: bool
    score: float
    max_score: float
    execution_time: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    generated_code: Optional[str] = None

class BenchmarkTestRunner:
    """Benchmark测试运行器主类"""
    
    def __init__(self, config_path: str = "config/test_config.yaml"):
        """初始化测试运行器"""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.base_dir = Path(__file__).parent
        self.sandbox_dir = self.base_dir / "sandbox"
        self.reports_dir = self.base_dir / "reports"
        
        # 确保目录存在
        self.sandbox_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        self.test_tasks: Dict[str, TestTask] = {}
        self.test_results: List[TestResult] = []
        
    def _load_config(self) -> Dict[str, Any]:
        """加载测试配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件 {self.config_path} 不存在，使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "levels": ["beginner", "elementary", "intermediate", "advanced", "expert", "master"],
            "domains": ["web_development", "mobile_app", "algorithms", "devops", "data_science"],
            "timeout": 300,
            "parallel_tasks": 3,
            "sandbox_enabled": True,
            "output_formats": ["json", "html"],
            "evaluation": {
                "beginner": {
                    "functionality": 40,
                    "code_structure": 25,
                    "readability": 20,
                    "edge_cases": 15
                },
                "elementary": {
                    "functionality": 35,
                    "code_quality": 25,
                    "user_experience": 20,
                    "error_handling": 20
                },
                "intermediate": {
                    "functionality": 30,
                    "architecture": 25,
                    "performance": 20,
                    "security": 15,
                    "testing": 10
                },
                "advanced": {
                    "functionality": 25,
                    "architecture": 25,
                    "performance": 20,
                    "security": 15,
                    "maintainability": 15
                },
                "expert": {
                    "innovation": 30,
                    "architecture": 25,
                    "performance": 20,
                    "complexity": 15,
                    "knowledge": 10
                },
                "master": {
                    "innovation": 35,
                    "architecture": 25,
                    "integration": 20,
                    "efficiency": 15,
                    "impact": 5
                }
            }
        }
    
    def load_test_tasks(self, level: Optional[str] = None, domain: Optional[str] = None):
        """加载测试任务"""
        levels_to_load = [level] if level and level != "all" else self.config["levels"]
        domains_to_load = [domain] if domain and domain != "all" else self.config["domains"]
        
        for level_name in levels_to_load:
            level_dir = self.base_dir / "levels" / level_name
            if level_dir.exists():
                self._load_tasks_from_directory(level_dir, level_name)
        
        for domain_name in domains_to_load:
            domain_dir = self.base_dir / "domains" / domain_name
            if domain_dir.exists():
                self._load_tasks_from_directory(domain_dir, None, domain_name)
    
    def _load_tasks_from_directory(self, directory: Path, level: Optional[str] = None, 
                                  domain: Optional[str] = None):
        """从目录加载任务"""
        for task_file in directory.glob("*.yaml"):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_data = yaml.safe_load(f)
                
                task = TestTask(
                    id=task_data["id"],
                    level=level or task_data.get("level", "unknown"),
                    domain=domain or task_data.get("domain", "unknown"),
                    title=task_data["title"],
                    description=task_data["description"],
                    input_spec=task_data["input_spec"],
                    output_spec=task_data["output_spec"],
                    evaluation_criteria=task_data["evaluation_criteria"],
                    test_cases=task_data["test_cases"],
                    time_limit=task_data.get("time_limit", 300)
                )
                
                self.test_tasks[task.id] = task
                logger.info(f"加载任务: {task.id} - {task.title}")
                
            except Exception as e:
                logger.error(f"加载任务文件 {task_file} 失败: {e}")
    
    async def run_single_task(self, task: TestTask) -> TestResult:
        """运行单个测试任务"""
        logger.info(f"开始执行任务: {task.id} - {task.title}")
        start_time = time.time()
        
        try:
            # 创建任务特定的沙箱环境
            task_sandbox = self.sandbox_dir / f"task_{task.id}_{int(start_time)}"
            task_sandbox.mkdir(exist_ok=True)
            
            # 这里应该调用实际的AI Agent进行代码生成
            # 暂时使用模拟的代码生成
            generated_code = await self._simulate_code_generation(task)
            
            # 执行功能测试
            test_results = await self._run_functional_tests(task, generated_code, task_sandbox)
            
            # 评估代码质量
            quality_score = self._evaluate_code_quality(task, generated_code)
            
            # 计算总分
            total_score, max_score, details = self._calculate_score(task, test_results, quality_score)
            
            execution_time = time.time() - start_time
            
            result = TestResult(
                task_id=task.id,
                success=True,
                score=total_score,
                max_score=max_score,
                execution_time=execution_time,
                details=details,
                generated_code=generated_code
            )
            
            logger.info(f"任务完成: {task.id}, 得分: {total_score:.2f}/{max_score}")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"任务执行失败: {task.id}, 错误: {e}")
            
            return TestResult(
                task_id=task.id,
                success=False,
                score=0.0,
                max_score=100.0,
                execution_time=execution_time,
                details={"error": str(e)},
                error_message=str(e)
            )
    
    async def _simulate_code_generation(self, task: TestTask) -> str:
        """模拟AI Agent代码生成（实际实现中应该调用真实的AI Agent）"""
        await asyncio.sleep(1)  # 模拟生成时间
        
        # 根据任务类型返回不同的示例代码
        if task.domain == "algorithms":
            return """
def temperature_converter(value, unit):
    if unit == 'C':
        return round((value * 9/5) + 32, 1), 'F'
    elif unit == 'F':
        return round((value - 32) * 5/9, 1), 'C'
    else:
        raise ValueError("Invalid unit")
"""
        elif task.domain == "web_development":
            return """
<!DOCTYPE html>
<html>
<head>
    <title>Personal Resume</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .section { margin-bottom: 20px; }
        h1, h2 { color: #333; }
    </style>
</head>
<body>
    <h1 id="name">John Doe</h1>
    <div class="section">
        <h2>Contact</h2>
        <p id="email">john@example.com</p>
        <p id="phone">123-456-7890</p>
    </div>
    <div class="section">
        <h2>Education</h2>
        <p id="education">Computer Science Degree</p>
    </div>
</body>
</html>
"""
        else:
            return "# 示例代码\nprint('Hello, World!')"
    
    async def _run_functional_tests(self, task: TestTask, code: str, sandbox_dir: Path) -> Dict[str, Any]:
        """运行功能测试"""
        test_results = {
            "passed": 0,
            "failed": 0,
            "total": len(task.test_cases),
            "details": []
        }
        
        for i, test_case in enumerate(task.test_cases):
            try:
                # 这里应该实际执行代码和测试用例
                # 暂时模拟测试结果
                passed = i % 3 != 0  # 模拟部分测试通过
                
                test_results["details"].append({
                    "test_case": i,
                    "passed": passed,
                    "input": test_case.get("input", {}),
                    "expected": test_case.get("expected", {}),
                    "actual": "模拟输出"
                })
                
                if passed:
                    test_results["passed"] += 1
                else:
                    test_results["failed"] += 1
                    
            except Exception as e:
                test_results["failed"] += 1
                test_results["details"].append({
                    "test_case": i,
                    "passed": False,
                    "error": str(e)
                })
        
        return test_results
    
    def _evaluate_code_quality(self, task: TestTask, code: str) -> Dict[str, float]:
        """评估代码质量"""
        # 这里应该实现实际的代码质量评估
        # 暂时返回模拟分数
        return {
            "syntax": 85.0,
            "structure": 80.0,
            "readability": 75.0,
            "best_practices": 70.0
        }
    
    def _calculate_score(self, task: TestTask, test_results: Dict[str, Any], 
                        quality_scores: Dict[str, float]) -> tuple[float, float, Dict[str, Any]]:
        """计算任务总分"""
        criteria = self.config["evaluation"].get(task.level, self.config["evaluation"]["beginner"])
        
        # 功能性得分
        functionality_score = (test_results["passed"] / test_results["total"]) * 100 if test_results["total"] > 0 else 0
        
        # 代码质量得分
        quality_score = sum(quality_scores.values()) / len(quality_scores)
        
        # 加权计算总分
        total_score = 0
        max_score = 100
        details = {}
        
        # 根据评估标准计算分数
        for criterion, weight in criteria.items():
            if criterion == "functionality":
                score = functionality_score * (weight / 100)
            else:
                score = quality_score * (weight / 100)
            
            total_score += score
            details[criterion] = {
                "score": score,
                "weight": weight,
                "max_score": weight
            }
        
        details["test_results"] = test_results
        details["quality_scores"] = quality_scores
        
        return total_score, max_score, details
    
    async def run_tests(self, level: Optional[str] = None, domain: Optional[str] = None) -> List[TestResult]:
        """运行测试"""
        logger.info("开始执行Benchmark测试")
        
        # 加载测试任务
        self.load_test_tasks(level, domain)
        
        if not self.test_tasks:
            logger.warning("没有找到要执行的测试任务")
            return []
        
        logger.info(f"找到 {len(self.test_tasks)} 个测试任务")
        
        # 并行执行任务
        semaphore = asyncio.Semaphore(self.config.get("parallel_tasks", 3))
        
        async def run_with_semaphore(task):
            async with semaphore:
                return await self.run_single_task(task)
        
        tasks = [run_with_semaphore(task) for task in self.test_tasks.values()]
        self.test_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        valid_results = []
        for result in self.test_results:
            if isinstance(result, Exception):
                logger.error(f"任务执行异常: {result}")
            else:
                valid_results.append(result)
        
        self.test_results = valid_results
        logger.info(f"测试完成，共执行 {len(self.test_results)} 个任务")
        
        return self.test_results
    
    def generate_report(self, output_format: str = "json") -> str:
        """生成测试报告"""
        if not self.test_results:
            logger.warning("没有测试结果可以生成报告")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == "json":
            return self._generate_json_report(timestamp)
        elif output_format == "html":
            return self._generate_html_report(timestamp)
        else:
            logger.error(f"不支持的报告格式: {output_format}")
            return ""
    
    def _generate_json_report(self, timestamp: str) -> str:
        """生成JSON格式报告"""
        report_data = {
            "timestamp": timestamp,
            "summary": self._get_summary_stats(),
            "results": [asdict(result) for result in self.test_results],
            "config": self.config
        }
        
        report_file = self.reports_dir / f"benchmark_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON报告已生成: {report_file}")
        return str(report_file)
    
    def _generate_html_report(self, timestamp: str) -> str:
        """生成HTML格式报告"""
        # 这里应该生成详细的HTML报告
        # 暂时生成简单的HTML
        summary = self._get_summary_stats()
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent Benchmark Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .summary {{ background: #f5f5f5; padding: 20px; margin-bottom: 20px; }}
        .result {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; }}
        .success {{ border-left: 5px solid #4CAF50; }}
        .failure {{ border-left: 5px solid #f44336; }}
    </style>
</head>
<body>
    <h1>AI Agent Benchmark Test Report</h1>
    <div class="summary">
        <h2>测试总结</h2>
        <p>总任务数: {summary['total_tasks']}</p>
        <p>成功任务: {summary['successful_tasks']}</p>
        <p>失败任务: {summary['failed_tasks']}</p>
        <p>平均分数: {summary['average_score']:.2f}</p>
        <p>总执行时间: {summary['total_time']:.2f}秒</p>
    </div>
    
    <h2>详细结果</h2>
"""
        
        for result in self.test_results:
            status_class = "success" if result.success else "failure"
            html_content += f"""
    <div class="result {status_class}">
        <h3>任务: {result.task_id}</h3>
        <p>状态: {'成功' if result.success else '失败'}</p>
        <p>分数: {result.score:.2f}/{result.max_score}</p>
        <p>执行时间: {result.execution_time:.2f}秒</p>
        {f'<p>错误: {result.error_message}</p>' if result.error_message else ''}
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        report_file = self.reports_dir / f"benchmark_report_{timestamp}.html"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML报告已生成: {report_file}")
        return str(report_file)
    
    def _get_summary_stats(self) -> Dict[str, Any]:
        """获取汇总统计信息"""
        if not self.test_results:
            return {}
        
        successful_tasks = sum(1 for r in self.test_results if r.success)
        total_score = sum(r.score for r in self.test_results)
        total_max_score = sum(r.max_score for r in self.test_results)
        total_time = sum(r.execution_time for r in self.test_results)
        
        return {
            "total_tasks": len(self.test_results),
            "successful_tasks": successful_tasks,
            "failed_tasks": len(self.test_results) - successful_tasks,
            "average_score": total_score / len(self.test_results) if self.test_results else 0,
            "total_score": total_score,
            "total_max_score": total_max_score,
            "total_time": total_time,
            "success_rate": successful_tasks / len(self.test_results) * 100 if self.test_results else 0
        }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI Agent编程能力测试集合")
    parser.add_argument("--level", choices=["beginner", "elementary", "intermediate", 
                                          "advanced", "expert", "master", "all"], 
                       default="all", help="指定测试难度级别")
    parser.add_argument("--domain", choices=["web_development", "mobile_app", "algorithms", 
                                           "devops", "data_science", "all"], 
                       default="all", help="指定测试技术领域")
    parser.add_argument("--output", choices=["json", "html"], default="json", 
                       help="输出报告格式")
    parser.add_argument("--config", default="config/test_config.yaml", 
                       help="配置文件路径")
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = BenchmarkTestRunner(args.config)
    
    try:
        # 运行测试
        results = asyncio.run(runner.run_tests(args.level, args.domain))
        
        # 生成报告
        report_file = runner.generate_report(args.output)
        
        # 打印摘要
        summary = runner._get_summary_stats()
        print(f"\n{'='*50}")
        print("测试完成！")
        print(f"总任务数: {summary.get('total_tasks', 0)}")
        print(f"成功任务: {summary.get('successful_tasks', 0)}")
        print(f"成功率: {summary.get('success_rate', 0):.1f}%")
        print(f"平均分数: {summary.get('average_score', 0):.2f}")
        print(f"报告文件: {report_file}")
        print(f"{'='*50}")
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 