import logging
import os
from logging.handlers import RotatingFileHandler
import time

def setup_logger():
    """Configure logging system"""
    # Create logs directory
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Generate log filename with timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"agent_{timestamp}.log")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure file handler (with rotation)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create specific module loggers
    loggers = {
        'agent': logging.getLogger('agent'),
        'mcp': logging.getLogger('mcp'),
        'llm': logging.getLogger('llm'),
        'tools': logging.getLogger('tools')
    }
    
    # Configure each module logger
    for logger in loggers.values():
        logger.setLevel(logging.DEBUG)
        logger.propagate = True  # Allow logs to propagate to root logger
    
    return loggers

# Create logger instances
loggers = setup_logger()

# Export module loggers
agent_logger = loggers['agent']
mcp_logger = loggers['mcp']
llm_logger = loggers['llm']
tools_logger = loggers['tools'] 