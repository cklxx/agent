# Project Agent

## Introduction

This project is a tool-calling agent built with the PocketFlow framework, integrating local dummy tools and external MCP (Model Context Protocol) servers. It can be invoked via the command line, and soon, via an API and a simple web interface.

## Development Setup

### Prerequisites

*   Python 3.10+
*   uv (for Python environment and package management)
*   Git
*   Node.js and npm/npx

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository_url>
    cd <project_directory>
    ```

2.  Create a virtual environment and install dependencies using uv:
    ```bash
    uv venv
    uv sync
    ```
    This will set up a `.venv` directory with all necessary packages.

3.  Install Node.js dependencies and Playwright browsers:
    ```bash
    npm install
    npx playwright install
    ```

### Configuration

#### 1. LLM Configuration (`conf.yaml`)

*   Copy the example configuration file:
    ```bash
    cp conf.yaml.example conf.yaml
    cp .env.example .env
    ```
*   Edit `conf.yaml` to set your LLM API key and base URL.
    ```yaml
    # Example conf.yaml structure
    BASIC_MODEL:
      base_url: <your_llm_api_base_url> # e.g., https://ark.cn-beijing.volces.com/api/v3
      model: "<your_model_name>"       # e.g., "doubao-1-5-pro-32k-250115"
      api_key: <your_llm_api_key>
    ```
    Replace placeholders with your actual credentials and model details.

#### 2. MCP Server Configuration (`mcp.json`)

*   This file configures external tools accessible via the Model Context Protocol.
*   Copy the example configuration file:
    ```bash
    cp mcp.json.example mcp.json
    ```
*   Edit `mcp.json` to define the MCP servers you want to use.
    ```json
    // Example mcp.json structure
    {
      "mcpServers": {
        "amap-maps": { // Example: A map service
          "command": "npx",
          "args": ["-y", "@amap/amap-maps-mcp-server"],
          "env": {
            "AMAP_MAPS_API_KEY": "YOUR_AMAP_API_KEY" // Replace with your actual key
          }
        },
        "tavily-mcp": { // Example: Tavily search
          "command": "npx",
          "args": ["-y", "tavily-mcp@0.1.2"],
          "env": {
            "TAVILY_API_KEY": "YOUR_TAVILY_API_KEY" // Replace with your actual key
          }
        }
        // Add other MCP servers as needed
      }
    }
    ```
    *   Update `command` and `args` for each server as per its documentation.
    *   Crucially, set any required API keys or environment variables under the `env` object for each server. For instance, replace `"YOUR_AMAP_API_KEY"` and `"YOUR_TAVILY_API_KEY"` with your actual API keys.
    *   If an MCP server does not require environment variables, you can omit the `env` field or leave it as an empty object `{}`.

### Running the Project

You can run the agent in two main ways:

#### 1. Using Startup Scripts (Recommended)

These scripts handle virtual environment activation and then start the application.

*   **For Linux/macOS:**
    ```bash
    ./run.sh
    ```
    (If you get a permission error, run `chmod +x run.sh` first.)

*   **For Windows:**
    ```bash
    .\run.bat
    ```

Currently, these scripts run `python main.py` for command-line interaction. This will be updated as the API server is developed.

#### 2. Manual Execution

1.  Activate the virtual environment:
    *   Linux/macOS: `source .venv/bin/activate`
    *   Windows: `.venv\Scripts\activate.bat`

2.  Run the main application:
    ```bash
    python main.py
    ```

### Testing

项目提供了两种一键测试脚本，用于运行测试用例：

#### Python测试脚本 (跨平台)

```bash
# 运行所有测试
python run_tests.py

# 只运行 Flow 测试
python run_tests.py flow

# 只运行 API 服务器测试
python run_tests.py api

# 显示详细输出
python run_tests.py -v
```

#### Bash测试脚本 (Linux/macOS)

```bash
# 运行所有测试
./run_tests.sh

# 只运行 Flow 测试
./run_tests.sh flow

# 只运行 API 服务器测试
./run_tests.sh api

# 显示帮助信息
./run_tests.sh -h
```

这两个脚本会自动检查环境，确保已安装 pytest，并可以针对特定测试模块运行测试。

### Upcoming Features: API and Web UI

Work is in progress to provide:
*   An API endpoint to invoke the agent programmatically.
*   A simple web interface to interact with the agent and view invocation steps.

## Project Structure

*   `main.py`: Entry point for command-line interaction.
*   `api_server.py`: (Upcoming) Entry point for the API server.
*   `run.sh`, `run.bat`: Startup scripts.
*   `run_tests.py`, `run_tests.sh`: 测试脚本，用于一键运行项目测试。
*   `flow.py`: Defines the PocketFlow workflow.
*   `nodes/`: Contains different nodes for the workflow.
    *   `mcp_nodes.py`: Handles discovering, deciding, and executing tools using MCP.
    *   `search_answer_nodes.py`: Contains nodes for multi-step thinking and final answer generation.
*   `tools/`: Contains local tool implementations.
*   `utils/`: Contains utility functions.
*   `conf.yaml`: Configuration file for LLM.
*   `mcp.json`: Configuration file for MCP servers.
*   `pyproject.toml`: Project definition and dependency file.
*   `.gitignore`: Specifies files to be ignored by Git.
*   `static/` or `ui/`: (Upcoming) Will contain files for the web interface.


## Architecture Overview

This project implements a tool-calling agent using the PocketFlow framework. The core architecture is a directed acyclic graph (DAG) defined in `flow.py`, orchestrating the interaction between different nodes and the LLM.

The main components and their roles are:

1.  **Tool Discovery (`GetToolsNode`):** Gathers available tools from configured external MCP servers (defined in `mcp.json`) and built-in local tools.
2.  **Tool Decision (`DecideToolNode`):** Sends the user query and available tool information to the LLM (configured in `conf.yaml`) to determine the next action or tool to call.
3.  **Tool Execution (`ExecuteToolNode`):** Calls the selected tool. It routes the call to either the local tool implementation or the appropriate external MCP server.
4.  **Multi-step Reasoning (`ThinkingNode`):** Allows the LLM to perform a sequence of reasoning steps.
5.  **Answer Generation (`AnswerNode`):** Formulates the final response.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[Specify your license here, e.g., MIT](LICENSE)

# MCP Servers Setup

This project uses multiple MCP (Model Control Protocol) servers for different functionalities.

## Prerequisites

- Node.js and npm/npx installed
- Required API keys (see below)
- Playwright browsers installed (`npx playwright install`)

## Required API Keys

1. AMAP Maps API Key: `7897d07c1c16a4da56995e13968b1641`
2. Tavily API Key: `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`

## Installation

1. Install Node.js dependencies:
```bash
npm install
```

2. Install Playwright browsers:
```bash
npx playwright install
```

3. Install Amap Maps MCP Server:
```bash
export AMAP_MAPS_API_KEY="7897d07c1c16a4da56995e13968b1641"
npx -y @amap/amap-maps-mcp-server
```

4. Install Playwright MCP:
```bash
npx -y @playwright/mcp@latest
```

5. Install Tavily MCP:
```bash
export TAVILY_API_KEY="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"
npx -y tavily-mcp@0.1.2
```

## Configuration

The MCP servers are configured in `mcp.json`. Each server has its own configuration including:
- Command to run
- Arguments
- Environment variables

## Usage

Each MCP server runs on stdio (standard input/output) and can be used by your application. The servers are:

1. Amap Maps MCP Server - For map-related functionality
2. Playwright MCP - For browser automation
3. Tavily MCP - For search and information retrieval

## Running the Servers

To run all servers, you can use the following commands in separate terminal windows:

```bash
# Terminal 1 - Amap Maps
export AMAP_MAPS_API_KEY="7897d07c1c16a4da56995e13968b1641"
npx -y @amap/amap-maps-mcp-server

# Terminal 2 - Playwright
npx -y @playwright/mcp@latest

# Terminal 3 - Tavily
export TAVILY_API_KEY="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"
npx -y tavily-mcp@0.1.2
```

## Notes

- Make sure to keep your API keys secure and never commit them to version control
- Each server needs to be running in a separate terminal window
- The servers communicate via stdio, so they should be started before running your main application