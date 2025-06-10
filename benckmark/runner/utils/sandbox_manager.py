#!/usr/bin/env python3
"""
沙箱管理器 - 安全地执行和评估AI生成的代码

功能:
- 隔离代码执行环境
- 资源限制和监控
- 安全检查和验证
- 性能测试和分析
"""

import ast
import asyncio
import contextlib
import importlib.util
import io
import os
import psutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import threading
import resource

class SecurityViolationError(Exception):
    """安全检查违规异常"""
    pass

class ResourceLimitExceededError(Exception):
    """资源限制超出异常"""
    pass

class CodeExecutionTimeoutError(Exception):
    """代码执行超时异常"""
    pass

class SandboxManager:
    """代码执行沙箱管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化沙箱管理器"""
        self.config = config or self._get_default_config()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="benchmark_sandbox_"))
        self.blocked_imports = set(self.config.get("blocked_imports", []))
        self.allowed_extensions = set(self.config.get("allowed_file_extensions", []))
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "max_execution_time": 30,  # 秒
            "max_memory_mb": 500,
            "max_cpu_percent": 80,
            "blocked_imports": [
                "os.system", "subprocess", "exec", "eval", 
                "open", "__import__", "compile"
            ],
            "allowed_file_extensions": [
                ".py", ".js", ".html", ".css", ".json", ".yaml", ".md"
            ],
            "disable_network": True,
            "disable_file_system": False
        }
    
    def __enter__(self):
        """进入沙箱环境"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出沙箱环境，清理资源"""
        self.cleanup()
    
    def cleanup(self):
        """清理沙箱环境"""
        try:
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理沙箱环境失败: {e}")
    
    def check_code_security(self, code: str, language: str = "python") -> List[str]:
        """检查代码安全性"""
        security_issues = []
        
        if language == "python":
            security_issues.extend(self._check_python_security(code))
        elif language == "javascript":
            security_issues.extend(self._check_javascript_security(code))
        
        return security_issues
    
    def _check_python_security(self, code: str) -> List[str]:
        """检查Python代码安全性"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            class SecurityChecker(ast.NodeVisitor):
                def __init__(self):
                    self.issues = []
                
                def visit_Import(self, node):
                    for alias in node.names:
                        if alias.name in self.blocked_imports:
                            self.issues.append(f"禁止导入模块: {alias.name}")
                    self.generic_visit(node)
                
                def visit_ImportFrom(self, node):
                    if node.module and node.module in self.blocked_imports:
                        self.issues.append(f"禁止导入模块: {node.module}")
                    for alias in node.names:
                        full_name = f"{node.module}.{alias.name}" if node.module else alias.name
                        if full_name in self.blocked_imports:
                            self.issues.append(f"禁止导入: {full_name}")
                    self.generic_visit(node)
                
                def visit_Call(self, node):
                    # 检查危险函数调用
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ["eval", "exec", "compile", "__import__"]:
                            self.issues.append(f"禁止调用函数: {node.func.id}")
                    elif isinstance(node.func, ast.Attribute):
                        attr_name = node.func.attr
                        if attr_name in ["system", "popen", "spawn"]:
                            self.issues.append(f"禁止调用方法: {attr_name}")
                    self.generic_visit(node)
            
            checker = SecurityChecker()
            checker.visit(tree)
            issues.extend(checker.issues)
            
        except SyntaxError as e:
            issues.append(f"语法错误: {e}")
        
        return issues
    
    def _check_javascript_security(self, code: str) -> List[str]:
        """检查JavaScript代码安全性"""
        issues = []
        
        # 简单的关键词检查
        dangerous_patterns = [
            "eval(", "Function(", "setTimeout(", "setInterval(",
            "document.write", "innerHTML", "outerHTML",
            "exec", "spawn", "require("
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                issues.append(f"检测到危险模式: {pattern}")
        
        return issues
    
    async def execute_python_code(self, code: str, input_data: Any = None, 
                                 timeout: Optional[int] = None) -> Dict[str, Any]:
        """执行Python代码"""
        timeout = timeout or self.config["max_execution_time"]
        
        # 安全检查
        security_issues = self.check_code_security(code, "python")
        if security_issues:
            raise SecurityViolationError(f"安全检查失败: {security_issues}")
        
        # 创建执行环境
        exec_file = self.temp_dir / "exec_code.py"
        with open(exec_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 准备执行参数
        cmd = [sys.executable, str(exec_file)]
        env = os.environ.copy()
        
        if self.config.get("disable_network"):
            env["no_proxy"] = "*"
        
        # 执行代码
        start_time = time.time()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.temp_dir),
                env=env
            )
            
            # 监控资源使用
            monitor_task = asyncio.create_task(
                self._monitor_process_resources(process.pid, timeout)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise CodeExecutionTimeoutError(f"代码执行超时 ({timeout}秒)")
            finally:
                monitor_task.cancel()
            
            execution_time = time.time() - start_time
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "return_code": process.returncode,
                "execution_time": execution_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "execution_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def _monitor_process_resources(self, pid: int, timeout: int):
        """监控进程资源使用"""
        try:
            process = psutil.Process(pid)
            max_memory = self.config["max_memory_mb"] * 1024 * 1024  # 转换为字节
            max_cpu = self.config["max_cpu_percent"]
            
            check_interval = 0.1  # 检查间隔
            checks = 0
            max_checks = int(timeout / check_interval)
            
            while checks < max_checks:
                try:
                    if not process.is_running():
                        break
                    
                    # 检查内存使用
                    memory_info = process.memory_info()
                    if memory_info.rss > max_memory:
                        process.kill()
                        raise ResourceLimitExceededError(
                            f"内存使用超出限制: {memory_info.rss / 1024 / 1024:.1f}MB > {self.config['max_memory_mb']}MB"
                        )
                    
                    # 检查CPU使用
                    cpu_percent = process.cpu_percent(interval=None)
                    if cpu_percent > max_cpu:
                        process.kill()
                        raise ResourceLimitExceededError(
                            f"CPU使用超出限制: {cpu_percent:.1f}% > {max_cpu}%"
                        )
                    
                    await asyncio.sleep(check_interval)
                    checks += 1
                    
                except psutil.NoSuchProcess:
                    break
                    
        except asyncio.CancelledError:
            pass
    
    def validate_function_signature(self, code: str, expected_signature: str) -> bool:
        """验证函数签名是否符合要求"""
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 提取函数签名
                    args = [arg.arg for arg in node.args.args]
                    # 简单的签名匹配检查
                    if expected_signature in code:
                        return True
            
            return False
        except Exception:
            return False
    
    def run_functional_tests(self, code: str, test_cases: List[Dict[str, Any]], 
                           function_name: str) -> Dict[str, Any]:
        """运行功能测试"""
        results = {
            "passed": 0,
            "failed": 0,
            "total": len(test_cases),
            "details": []
        }
        
        # 创建测试模块
        test_module_code = f"""
{code}

import json
import sys

def run_test(test_case):
    try:
        input_data = test_case['input']
        expected = test_case['expected']
        
        # 调用被测试的函数
        if isinstance(input_data, dict):
            result = {function_name}(**input_data)
        else:
            result = {function_name}(input_data)
        
        # 比较结果
        success = result == expected
        
        return {{
            "success": success,
            "input": input_data,
            "expected": expected,
            "actual": result,
            "error": None
        }}
    except Exception as e:
        return {{
            "success": False,
            "input": input_data,
            "expected": expected,
            "actual": None,
            "error": str(e)
        }}

if __name__ == "__main__":
    test_case = json.loads(sys.argv[1])
    result = run_test(test_case)
    print(json.dumps(result))
"""
        
        for i, test_case in enumerate(test_cases):
            try:
                # 执行单个测试用例
                result = asyncio.run(self._run_single_test(test_module_code, test_case))
                
                if result.get("success"):
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                
                results["details"].append({
                    "test_case": i,
                    "result": result
                })
                
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "test_case": i,
                    "result": {
                        "success": False,
                        "error": str(e)
                    }
                })
        
        return results
    
    async def _run_single_test(self, test_code: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个测试用例"""
        import json
        
        # 写入测试代码
        test_file = self.temp_dir / f"test_{int(time.time() * 1000000)}.py"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        # 执行测试
        cmd = [sys.executable, str(test_file), json.dumps(test_case)]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.temp_dir)
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=10
            )
            
            if process.returncode == 0:
                return json.loads(stdout.decode('utf-8'))
            else:
                return {
                    "success": False,
                    "error": stderr.decode('utf-8', errors='ignore')
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # 清理测试文件
            try:
                test_file.unlink()
            except:
                pass
    
    def analyze_code_quality(self, code: str, language: str = "python") -> Dict[str, Any]:
        """分析代码质量"""
        quality_metrics = {
            "syntax_score": 0,
            "complexity_score": 0,
            "style_score": 0,
            "documentation_score": 0,
            "issues": []
        }
        
        if language == "python":
            quality_metrics.update(self._analyze_python_quality(code))
        elif language == "javascript":
            quality_metrics.update(self._analyze_javascript_quality(code))
        
        return quality_metrics
    
    def _analyze_python_quality(self, code: str) -> Dict[str, Any]:
        """分析Python代码质量"""
        metrics = {}
        
        try:
            # 语法检查
            ast.parse(code)
            metrics["syntax_score"] = 100
        except SyntaxError as e:
            metrics["syntax_score"] = 0
            metrics.setdefault("issues", []).append(f"语法错误: {e}")
        
        # 简单的复杂度分析
        try:
            tree = ast.parse(code)
            complexity = self._calculate_cyclomatic_complexity(tree)
            metrics["complexity_score"] = max(0, 100 - complexity * 5)
        except:
            metrics["complexity_score"] = 50
        
        # 代码风格检查（简化版）
        style_issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                style_issues.append(f"第{i}行过长 (>{100}字符)")
            if line.strip() and not line.startswith('#') and '  ' in line and not line.startswith('    '):
                style_issues.append(f"第{i}行缩进不规范")
        
        metrics["style_score"] = max(0, 100 - len(style_issues) * 10)
        metrics.setdefault("issues", []).extend(style_issues)
        
        # 文档检查
        doc_score = 0
        if '"""' in code or "'''" in code:
            doc_score += 50
        if 'def ' in code and ('"""' in code or "'''" in code):
            doc_score += 50
        
        metrics["documentation_score"] = doc_score
        
        return metrics
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """计算循环复杂度"""
        complexity = 1  # 基础复杂度
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _analyze_javascript_quality(self, code: str) -> Dict[str, Any]:
        """分析JavaScript代码质量（简化版）"""
        metrics = {
            "syntax_score": 80,  # 简化处理
            "complexity_score": 70,
            "style_score": 75,
            "documentation_score": 60,
            "issues": []
        }
        
        # 基本的语法和风格检查
        lines = code.split('\n')
        issues = []
        
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(f"第{i}行过长")
            if 'eval(' in line:
                issues.append(f"第{i}行使用了危险的eval函数")
        
        metrics["issues"] = issues
        return metrics

# 使用示例
if __name__ == "__main__":
    # 示例代码
    sample_code = '''
def temperature_converter(value, unit):
    """温度转换函数"""
    if unit == 'C':
        return round((value * 9/5) + 32, 1), 'F'
    elif unit == 'F':
        return round((value - 32) * 5/9, 1), 'C'
    else:
        raise ValueError("Invalid unit")
'''
    
    with SandboxManager() as sandbox:
        # 安全检查
        issues = sandbox.check_code_security(sample_code)
        print(f"安全检查结果: {issues}")
        
        # 代码质量分析
        quality = sandbox.analyze_code_quality(sample_code)
        print(f"代码质量分析: {quality}")
        
        # 功能测试
        test_cases = [
            {"input": {"value": 0, "unit": "C"}, "expected": (32.0, "F")},
            {"input": {"value": 32, "unit": "F"}, "expected": (0.0, "C")}
        ]
        
        test_results = sandbox.run_functional_tests(
            sample_code, test_cases, "temperature_converter"
        )
        print(f"测试结果: {test_results}") 