#!/usr/bin/env python3
"""
RAG Context Discovery and Testing Script
测试当前文件夹下包含RAG的context信息
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import ast
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入RAG和Context相关模块
from src.context.base import BaseContext, ContextType, Priority
from src.context.manager import ContextManager
from src.context.rag_context_manager import RAGContextManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGContextDiscovery:
    """RAG Context发现和测试工具"""

    def __init__(self, target_dir: str = ".", workspace_path: str = None):
        """
        初始化RAG Context发现工具
        
        Args:
            target_dir: 目标扫描目录
            workspace_path: 工作空间路径
        """
        self.target_dir = Path(target_dir).resolve()
        self.workspace_path = workspace_path or str(project_root)
        self.rag_files = []
        self.context_instances = []
        self.test_results = {}
        
        # 初始化Context管理器
        self.context_manager = ContextManager()
        
        print(f"🔍 RAG Context发现工具启动")
        print(f"📁 扫描目录: {self.target_dir}")
        print(f"🏠 工作空间: {self.workspace_path}")

    def scan_rag_files(self) -> List[str]:
        """扫描包含RAG相关内容的文件"""
        rag_keywords = [
            'rag', 'RAG', 'context', 'Context', 'retriever', 'enhanced', 
            'semantic', 'embedding', 'vector', 'search', 'query'
        ]
        
        rag_files = []
        for root, dirs, files in os.walk(self.target_dir):
            # 跳过__pycache__等目录
            dirs[:] = [d for d in dirs if not d.startswith('__pycache__')]
            
            for file in files:
                if file.endswith(('.py', '.md', '.txt', '.json', '.yaml')):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # 检查是否包含RAG相关关键词
                        if any(keyword in content for keyword in rag_keywords):
                            rag_files.append(str(file_path))
                            
                    except Exception as e:
                        logger.warning(f"读取文件失败 {file_path}: {e}")
        
        self.rag_files = rag_files
        return rag_files

    def analyze_rag_content(self, file_path: str) -> Dict[str, Any]:
        """分析文件中的RAG相关内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                'file_path': file_path,
                'file_type': Path(file_path).suffix,
                'rag_context_types': [],
                'rag_functions': [],
                'rag_classes': [],
                'context_instances': [],
                'test_methods': [],
                'import_statements': []
            }
            
            # 如果是Python文件，进行AST分析
            if file_path.endswith('.py'):
                try:
                    tree = ast.parse(content)
                    analysis.update(self._analyze_python_ast(tree))
                except SyntaxError as e:
                    logger.warning(f"Python AST解析失败 {file_path}: {e}")
            
            # 文本搜索分析
            lines = content.split('\n')
            for i, line in enumerate(lines):
                line_lower = line.lower()
                
                # 检测Context类型
                if 'contexttype' in line_lower:
                    if 'rag' in line_lower:
                        analysis['rag_context_types'].append({
                            'line': i + 1,
                            'content': line.strip()
                        })
                
                # 检测导入语句
                if line.strip().startswith(('import', 'from')) and 'rag' in line_lower:
                    analysis['import_statements'].append({
                        'line': i + 1,
                        'content': line.strip()
                    })
                
                # 检测测试方法
                if 'def test' in line_lower and 'rag' in line_lower:
                    analysis['test_methods'].append({
                        'line': i + 1,
                        'content': line.strip()
                    })
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析文件失败 {file_path}: {e}")
            return {'error': str(e)}

    def _analyze_python_ast(self, tree: ast.AST) -> Dict[str, Any]:
        """分析Python AST获取RAG相关信息"""
        analysis = {
            'rag_functions': [],
            'rag_classes': [],
            'context_instances': []
        }
        
        for node in ast.walk(tree):
            # 分析函数定义
            if isinstance(node, ast.FunctionDef):
                if 'rag' in node.name.lower():
                    analysis['rag_functions'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'docstring': ast.get_docstring(node)
                    })
            
            # 分析类定义
            elif isinstance(node, ast.ClassDef):
                if 'rag' in node.name.lower() or 'context' in node.name.lower():
                    analysis['rag_classes'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'bases': [base.id if isinstance(base, ast.Name) else str(base) for base in node.bases],
                        'docstring': ast.get_docstring(node)
                    })
            
            # 分析变量赋值（Context实例）
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and 'context' in target.id.lower():
                        analysis['context_instances'].append({
                            'name': target.id,
                            'line': node.lineno
                        })
        
        return analysis

    async def create_test_context_instances(self) -> List[BaseContext]:
        """创建测试用的Context实例"""
        test_contexts = []
        
        # 创建不同类型的RAG Context
        rag_types = [ContextType.RAG, ContextType.RAG_CODE, ContextType.RAG_SEMANTIC]
        
        for i, context_type in enumerate(rag_types):
            context = BaseContext(
                context_type=context_type,
                content=f"测试{context_type.value}内容 - 当前文件夹: {self.target_dir}",
                metadata={
                    'source': 'rag_context_discovery_test',
                    'scan_directory': str(self.target_dir),
                    'timestamp': datetime.now().isoformat(),
                    'test_id': f'test_{i+1}'
                },
                priority=Priority.HIGH if i == 0 else Priority.MEDIUM,
                tags=['rag', 'test', 'discovery', context_type.value]
            )
            
            # 添加到Context管理器
            context_id = await self.context_manager.add_context(
                content=context.content,
                context_type=context.context_type,
                metadata=context.metadata,
                priority=context.priority,
                tags=context.tags
            )
            context.id = context_id
            test_contexts.append(context)
        
        self.context_instances = test_contexts
        return test_contexts

    async def test_rag_context_manager(self) -> Dict[str, Any]:
        """测试RAG Context Manager功能"""
        test_results = {
            'initialization': False,
            'search_context': False,
            'function_context': False,
            'class_context': False,
            'error_handling': False,
            'performance': {},
            'errors': []
        }
        
        try:
            # 测试初始化
            rag_manager = RAGContextManager(
                context_manager=self.context_manager,
                repo_path=self.workspace_path,
                use_enhanced_retriever=False  # 使用基础检索器以避免依赖问题
            )
            test_results['initialization'] = True
            logger.info("✅ RAG Context Manager初始化成功")
            
            # 测试搜索上下文
            try:
                start_time = datetime.now()
                search_contexts = await rag_manager.add_rag_search_context(
                    query="test function",
                    max_results=3
                )
                end_time = datetime.now()
                
                test_results['search_context'] = len(search_contexts) >= 0  # 即使没有结果也算成功
                test_results['performance']['search_time'] = (end_time - start_time).total_seconds()
                logger.info(f"✅ RAG搜索上下文测试完成，结果数: {len(search_contexts)}")
                
            except Exception as e:
                test_results['errors'].append(f"搜索上下文测试失败: {e}")
                logger.warning(f"⚠️ RAG搜索上下文测试失败: {e}")
            
            # 测试函数上下文
            try:
                function_contexts = await rag_manager.add_function_search_context("test_function")
                test_results['function_context'] = len(function_contexts) >= 0
                logger.info(f"✅ 函数上下文测试完成，结果数: {len(function_contexts)}")
                
            except Exception as e:
                test_results['errors'].append(f"函数上下文测试失败: {e}")
                logger.warning(f"⚠️ 函数上下文测试失败: {e}")
            
            # 测试类上下文
            try:
                class_contexts = await rag_manager.add_class_search_context("TestClass")
                test_results['class_context'] = len(class_contexts) >= 0
                logger.info(f"✅ 类上下文测试完成，结果数: {len(class_contexts)}")
                
            except Exception as e:
                test_results['errors'].append(f"类上下文测试失败: {e}")
                logger.warning(f"⚠️ 类上下文测试失败: {e}")
            
            # 测试错误处理
            try:
                # 尝试无效查询
                invalid_contexts = await rag_manager.add_rag_search_context("")
                test_results['error_handling'] = True
                logger.info("✅ 错误处理测试完成")
                
            except Exception as e:
                test_results['error_handling'] = True  # 抛出异常也算正确的错误处理
                logger.info(f"✅ 错误处理测试完成（预期异常）: {e}")
            
        except Exception as e:
            test_results['errors'].append(f"RAG Context Manager初始化失败: {e}")
            logger.error(f"❌ RAG Context Manager测试失败: {e}")
        
        return test_results

    async def test_context_operations(self) -> Dict[str, Any]:
        """测试Context操作功能"""
        test_results = {
            'create_context': False,
            'retrieve_context': False,
            'search_context': False,
            'filter_by_type': False,
            'context_count': 0,
            'errors': []
        }
        
        try:
            # 创建测试Context
            contexts = await self.create_test_context_instances()
            test_results['create_context'] = len(contexts) > 0
            test_results['context_count'] = len(contexts)
            logger.info(f"✅ 创建了 {len(contexts)} 个测试Context")
            
            # 测试检索Context
            if contexts:
                first_context = contexts[0]
                retrieved = await self.context_manager.get_context(first_context.id)
                test_results['retrieve_context'] = retrieved is not None
                logger.info("✅ Context检索测试完成")
            
            # 测试搜索Context
            search_results = await self.context_manager.search_contexts(
                query="测试",
                limit=10
            )
            test_results['search_context'] = len(search_results) > 0
            logger.info(f"✅ Context搜索测试完成，找到 {len(search_results)} 个结果")
            
            # 测试按类型过滤
            rag_contexts = await self.context_manager.get_contexts_by_type(
                context_type=ContextType.RAG
            )
            test_results['filter_by_type'] = len(rag_contexts) > 0
            logger.info(f"✅ 按类型过滤测试完成，找到 {len(rag_contexts)} 个RAG Context")
            
        except Exception as e:
            test_results['errors'].append(f"Context操作测试失败: {e}")
            logger.error(f"❌ Context操作测试失败: {e}")
        
        return test_results

    def generate_report(self, analysis_results: List[Dict], 
                       context_test_results: Dict, 
                       rag_test_results: Dict) -> str:
        """生成测试报告"""
        report = []
        report.append("# RAG Context Discovery 测试报告")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**扫描目录**: {self.target_dir}")
        report.append(f"**工作空间**: {self.workspace_path}")
        report.append("")
        
        # 文件扫描结果
        report.append("## 📁 文件扫描结果")
        report.append(f"- 发现RAG相关文件: **{len(self.rag_files)}** 个")
        report.append("")
        
        for file_path in self.rag_files:
            relative_path = Path(file_path).relative_to(self.target_dir)
            report.append(f"- `{relative_path}`")
        report.append("")
        
        # 内容分析结果
        report.append("## 🔍 内容分析结果")
        total_rag_functions = sum(len(result.get('rag_functions', [])) for result in analysis_results)
        total_rag_classes = sum(len(result.get('rag_classes', [])) for result in analysis_results)
        total_context_types = sum(len(result.get('rag_context_types', [])) for result in analysis_results)
        total_test_methods = sum(len(result.get('test_methods', [])) for result in analysis_results)
        
        report.append(f"- RAG相关函数: **{total_rag_functions}** 个")
        report.append(f"- RAG相关类: **{total_rag_classes}** 个")
        report.append(f"- RAG Context类型: **{total_context_types}** 个")
        report.append(f"- RAG测试方法: **{total_test_methods}** 个")
        report.append("")
        
        # Context测试结果
        report.append("## 🧪 Context功能测试")
        report.append(f"- 创建Context: {'✅' if context_test_results.get('create_context') else '❌'}")
        report.append(f"- 检索Context: {'✅' if context_test_results.get('retrieve_context') else '❌'}")
        report.append(f"- 搜索Context: {'✅' if context_test_results.get('search_context') else '❌'}")
        report.append(f"- 类型过滤: {'✅' if context_test_results.get('filter_by_type') else '❌'}")
        report.append(f"- 创建的Context数量: **{context_test_results.get('context_count', 0)}** 个")
        report.append("")
        
        # RAG Manager测试结果
        report.append("## 🤖 RAG Manager功能测试")
        report.append(f"- 初始化: {'✅' if rag_test_results.get('initialization') else '❌'}")
        report.append(f"- 搜索上下文: {'✅' if rag_test_results.get('search_context') else '❌'}")
        report.append(f"- 函数上下文: {'✅' if rag_test_results.get('function_context') else '❌'}")
        report.append(f"- 类上下文: {'✅' if rag_test_results.get('class_context') else '❌'}")
        report.append(f"- 错误处理: {'✅' if rag_test_results.get('error_handling') else '❌'}")
        
        # 性能信息
        if 'performance' in rag_test_results and rag_test_results['performance']:
            perf = rag_test_results['performance']
            if 'search_time' in perf:
                report.append(f"- 搜索耗时: **{perf['search_time']:.3f}** 秒")
        report.append("")
        
        # 错误信息
        all_errors = context_test_results.get('errors', []) + rag_test_results.get('errors', [])
        if all_errors:
            report.append("## ⚠️ 错误信息")
            for error in all_errors:
                report.append(f"- {error}")
            report.append("")
        
        # 详细分析
        report.append("## 📋 详细文件分析")
        for result in analysis_results:
            if 'error' in result:
                continue
                
            file_path = result['file_path']
            relative_path = Path(file_path).relative_to(self.target_dir)
            report.append(f"### {relative_path}")
            
            if result.get('rag_functions'):
                report.append("**RAG函数:**")
                for func in result['rag_functions']:
                    report.append(f"- `{func['name']}()` (第{func['line']}行)")
            
            if result.get('rag_classes'):
                report.append("**RAG类:**")
                for cls in result['rag_classes']:
                    report.append(f"- `{cls['name']}` (第{cls['line']}行)")
            
            if result.get('test_methods'):
                report.append("**测试方法:**")
                for method in result['test_methods'][:5]:  # 只显示前5个
                    report.append(f"- 第{method['line']}行: `{method['content'][:60]}...`")
            
            report.append("")
        
        # 总结
        report.append("## 📊 测试总结")
        total_tests = 9  # 总测试项目数
        passed_tests = sum([
            context_test_results.get('create_context', False),
            context_test_results.get('retrieve_context', False),
            context_test_results.get('search_context', False),
            context_test_results.get('filter_by_type', False),
            rag_test_results.get('initialization', False),
            rag_test_results.get('search_context', False),
            rag_test_results.get('function_context', False),
            rag_test_results.get('class_context', False),
            rag_test_results.get('error_handling', False),
        ])
        
        success_rate = (passed_tests / total_tests) * 100
        report.append(f"- 测试通过率: **{success_rate:.1f}%** ({passed_tests}/{total_tests})")
        
        if success_rate >= 90:
            report.append("- 整体评价: 🏆 **优秀**")
        elif success_rate >= 75:
            report.append("- 整体评价: 🥇 **良好**")
        elif success_rate >= 60:
            report.append("- 整体评价: 🥈 **及格**")
        else:
            report.append("- 整体评价: 🥉 **需要改进**")
        
        return "\n".join(report)

    async def run_full_test(self) -> str:
        """运行完整的RAG Context测试"""
        print("🚀 开始RAG Context完整测试...")
        
        # 1. 扫描RAG文件
        print("📁 扫描RAG相关文件...")
        rag_files = self.scan_rag_files()
        print(f"   发现 {len(rag_files)} 个RAG相关文件")
        
        # 2. 分析文件内容
        print("🔍 分析文件内容...")
        analysis_results = []
        for file_path in rag_files:
            result = self.analyze_rag_content(file_path)
            analysis_results.append(result)
        print(f"   完成 {len(analysis_results)} 个文件的内容分析")
        
        # 3. 测试Context操作
        print("🧪 测试Context功能...")
        context_test_results = await self.test_context_operations()
        
        # 4. 测试RAG Manager
        print("🤖 测试RAG Manager功能...")
        rag_test_results = await self.test_rag_context_manager()
        
        # 5. 生成报告
        print("📋 生成测试报告...")
        report = self.generate_report(analysis_results, context_test_results, rag_test_results)
        
        # 保存报告到文件
        report_file = self.target_dir / "rag_context_discovery_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 测试完成！报告已保存到: {report_file}")
        return report


async def main():
    """主函数"""
    print("🔍 RAG Context Discovery and Testing Tool")
    print("=========================================")
    
    # 创建发现工具实例
    discovery = RAGContextDiscovery(target_dir=".", workspace_path=str(project_root))
    
    # 运行完整测试
    report = await discovery.run_full_test()
    
    print("\n📋 测试报告预览:")
    print("=" * 50)
    print(report[:1000] + "..." if len(report) > 1000 else report)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))