import json
import logging
import os
import subprocess
from typing import Any, Dict
# Import local tool implementations if needed (e.g., WebCrawler)
try:
    from tools.crawler import WebCrawler
except ImportError:
    logging.warning("WebCrawler not available.")
    WebCrawler = None # Define a placeholder

# --- Local Tool Definitions ---
def get_local_tool_definitions():
    """Define and return local dummy tools definitions."""
    return [
        {
            "name": "add",
            "description": "Add two numbers together",
            "inputSchema": {
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"}
                },
                "required": ["a", "b"]
            }
        },
        {
            "name": "subtract",
            "description": "Subtract b from a",
            "inputSchema": {
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"}
                },
                "required": ["a", "b"]
            }
        },
        # WebCrawler tool schema
        {
            "name": "web_crawler",
            "description": "Crawl a website and extract content",
            "inputSchema": {
                "properties": {
                    "url": {"type": "string", "description": "Starting URL to crawl"},
                    "max_pages": {"type": "integer", "description": "Maximum number of pages to crawl", "default": 10}
                },
                "required": ["url"]
            }
        },
        {
            'name': 'get_project_info',
            'description': '获取项目信息，例如项目根目录。',
            'inputSchema': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        },
        {
            'name': 'get_file_info',
            'description': '获取指定文件的内容和基本信息。',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'target_file': {
                        'type': 'string',
                        'description': '目标文件的路径。'
                    }
                },
                'required': ['target_file']
            }
        },
        {
            'name': 'edit_file',
            'description': '编辑或创建文件。',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'target_file': {
                        'type': 'string',
                        'description': '要编辑或创建的目标文件的路径。'
                    },
                    'instructions': {
                        'type': 'string',
                        'description': '编辑文件的指令。'
                    },
                    'code_edit': {
                        'type': 'string',
                        'description': '要应用的精确代码修改。'
                    }
                },
                'required': ['target_file', 'instructions', 'code_edit']
            }
        },
        {
            'name': 'run_terminal_cmd',
            'description': '运行终端命令。包含命令禁止功能。',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'command': {
                        'type': 'string',
                        'description': '要执行的终端命令。'
                    },
                    'is_background': {
                        'type': 'boolean',
                        'description': '命令是否在后台运行。',
                        'default': False
                    }
                },
                'required': ['command']
            }
        }
    ]

# --- Local Tool Execution Functions ---
def call_local_tool(tool_name: str, arguments: Dict[str, Any]):
    """Execute a specific local dummy tool."""
    logging.info(f"🔧 Calling local dummy tool '{tool_name}' with parameters: {arguments}")

    if tool_name == "add":
        a = arguments.get("a")
        b = arguments.get("b")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a + b
        else:
            return f"Error: Invalid arguments for add tool. Expected numbers, got a={a}, b={b}"

    elif tool_name == "subtract":
        a = arguments.get("a")
        b = arguments.get("b")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a - b
        else:
            return f"Error: Invalid arguments for subtract tool. Expected numbers, got a={a}, b={b}"

    elif tool_name == "web_crawler":
        url = arguments.get("url")
        max_pages = arguments.get("max_pages", 10)
        try:
            max_pages = int(max_pages)
        except (ValueError, TypeError):
            logging.warning(f"Invalid max_pages value '{max_pages}', using default 10.")
            max_pages = 10

        if isinstance(url, str) and url and WebCrawler:
             return local_call_web_crawler(url, max_pages)
        elif not WebCrawler:
             return "Error: WebCrawler class not available. Check imports."
        else:
             return f"Error: Invalid arguments for web_crawler tool. Expected non-empty string for url, got {url}"

    elif tool_name == "get_project_info":
        logging.info("🔧 Executing tool 'get_project_info'")
        try:
            # 获取项目根目录
            project_root = os.getcwd()
            
            # 获取项目基本信息
            project_info = {
                "project_root": project_root,
                "files": [],
                "directories": [],
                "total_size": 0
            }
            
            # 要排除的目录
            excluded_dirs = {'.git', '.venv', 'venv', 'env', '__pycache__'}
            
            # 遍历项目目录
            for root, dirs, files in os.walk(project_root):
                # 排除特定目录
                dirs[:] = [d for d in dirs if d not in excluded_dirs]
                
                # 添加目录信息
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    project_info["directories"].append({
                        "name": dir_name,
                        "path": os.path.relpath(dir_path, project_root)
                    })
                
                # 添加文件信息
                for file_name in files:
                    # 跳过 .pyc 文件
                    if file_name.endswith('.pyc'):
                        continue
                        
                    file_path = os.path.join(root, file_name)
                    try:
                        file_size = os.path.getsize(file_path)
                        project_info["total_size"] += file_size
                        project_info["files"].append({
                            "name": file_name,
                            "path": os.path.relpath(file_path, project_root),
                            "size": file_size,
                            "extension": os.path.splitext(file_name)[1]
                        })
                    except OSError as e:
                        logging.warning(f"无法获取文件信息 {file_path}: {e}")
            
            return project_info
        except Exception as e:
            logging.error(f"获取项目信息时出错: {e}")
            return {"error": str(e)}

    elif tool_name == "get_file_info":
        file_path = arguments.get("target_file")
        if not isinstance(file_path, str) or not file_path:
            return "错误: 无效或缺少 'target_file' 参数"
            
        try:
            # 获取文件的绝对路径
            abs_path = os.path.abspath(file_path)
            
            # 检查文件是否存在
            if not os.path.exists(abs_path):
                return f"错误: 文件不存在 {abs_path}"
                
            # 获取文件信息
            file_info = {
                "path": abs_path,
                "relative_path": os.path.relpath(abs_path, os.getcwd()),
                "size": os.path.getsize(abs_path),
                "created": os.path.getctime(abs_path),
                "modified": os.path.getmtime(abs_path),
                "is_file": os.path.isfile(abs_path),
                "is_dir": os.path.isdir(abs_path),
                "extension": os.path.splitext(abs_path)[1]
            }
            
            # 如果是文件，读取内容
            if file_info["is_file"]:
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        file_info["content"] = f.read()
                except UnicodeDecodeError:
                    file_info["content"] = "<二进制文件>"
                except Exception as e:
                    file_info["content"] = f"<读取文件时出错: {str(e)}>"
            
            return file_info
        except Exception as e:
            return f"错误: 获取文件信息时出错 {file_path}: {str(e)}"

    elif tool_name == "edit_file":
        target_file = arguments.get("target_file")
        instructions = arguments.get("instructions")
        code_edit = arguments.get("code_edit")
        
        if not all(isinstance(x, str) and x for x in [target_file, instructions, code_edit]):
            return "错误: 缺少或无效的参数"
            
        try:
            # 获取文件的绝对路径
            abs_path = os.path.abspath(target_file)
            
            # 确保目标目录存在
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            # 如果文件存在，先读取原内容
            original_content = ""
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                except Exception as e:
                    return f"错误: 读取原文件时出错: {str(e)}"
            
            # 应用编辑
            try:
                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(code_edit)
            except Exception as e:
                return f"错误: 写入文件时出错: {str(e)}"
            
            return {
                "status": "success",
                "file": abs_path,
                "instructions": instructions,
                "original_size": len(original_content),
                "new_size": len(code_edit),
                "message": f"成功编辑文件 {abs_path}"
            }
        except Exception as e:
            return f"错误: 编辑文件时出错: {str(e)}"

    elif tool_name == "run_terminal_cmd":
        command = arguments.get("command")
        is_background = arguments.get("is_background", False)
        
        if not isinstance(command, str) or not command:
            return "错误: 缺少或无效的 'command' 参数"
            
        # 检查危险命令
        prohibited_commands = [
            "rm -rf", ":(){ :|:& };:", "mkfs", "dd if=",
            "> /dev/sd", "chmod -R 777", "chown -R root:root"
        ]
        if any(pc in command for pc in prohibited_commands):
            return f"错误: 命令 '{command}' 被禁止执行"
            
        try:
            if is_background:
                # 在后台运行命令
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                return {
                    "status": "success",
                    "pid": process.pid,
                    "message": f"命令已在后台启动，PID: {process.pid}"
                }
            else:
                # 同步运行命令
                process = subprocess.run(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                return {
                    "status": "success" if process.returncode == 0 else "error",
                    "return_code": process.returncode,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "message": f"命令执行{'成功' if process.returncode == 0 else '失败'}"
                }
        except Exception as e:
            return f"错误: 执行命令时出错: {str(e)}"

    else:
        return f"错误: 未知的工具 '{tool_name}'"

# Execute the WebCrawler tool locally (kept for now, can be moved/refactored later)
def local_call_web_crawler(url: str, max_pages: int = 10):
    """Execute the WebCrawler tool locally."""
    logging.info(f"🔧 Calling local tool 'web_crawler' with url={url}, max_pages={max_pages}")
    if not WebCrawler:
        return "Error: WebCrawler class not available."
    try:
        crawler = WebCrawler(base_url=url, max_pages=max_pages)
        results = crawler.crawl()
        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"❌ Error executing local web_crawler tool: {e}")
        return f"Error executing web_crawler: {e}" 