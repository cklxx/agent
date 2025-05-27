import logging
import os
from logging.handlers import RotatingFileHandler
import time

def setup_logger():
    """配置日志系统"""
    # 创建 logs 目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 生成日志文件名，包含时间戳
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"agent_{timestamp}.log")
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置文件处理器（按大小轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到根日志记录器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 创建特定模块的日志记录器
    loggers = {
        'agent': logging.getLogger('agent'),
        'mcp': logging.getLogger('mcp'),
        'llm': logging.getLogger('llm'),
        'tools': logging.getLogger('tools')
    }
    
    # 配置每个模块的日志记录器
    for logger in loggers.values():
        logger.setLevel(logging.DEBUG)
        logger.propagate = True  # 允许日志传播到根日志记录器
    
    return loggers

# 创建日志记录器实例
loggers = setup_logger()

# 导出各个模块的日志记录器
agent_logger = loggers['agent']
mcp_logger = loggers['mcp']
llm_logger = loggers['llm']
tools_logger = loggers['tools'] 