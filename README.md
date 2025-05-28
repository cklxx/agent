# Project Agent

## Introduction

This is a tool-calling agent built on the PocketFlow framework, integrating local tools and external MCP (Model Context Protocol) servers. Users can interact with the agent via command line, API, or a simple web interface.

## Development Setup

### Prerequisites

* Python 3.10+
* uv (for Python environment and package management)
* Git
* Node.js and npm/npx

### Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <project_directory>
   ```

2. Create a virtual environment and install dependencies using uv:
   ```bash
   uv venv
   uv sync
   ```
   This will set up a `.venv` directory with all necessary packages.

3. Install Node.js dependencies and Playwright browsers:
   ```bash
   npm install
   npx playwright install
   ```

### Configuration

#### 1. LLM Configuration (`conf.yaml`)

* Copy the example configuration file:
  ```bash
  cp conf.yaml.example conf.yaml
  ```
* Edit `conf.yaml` to set your LLM API key and base URL:
  ```yaml
  # Example conf.yaml structure
  BASIC_MODEL:
    base_url: <your_llm_api_base_url> # e.g., https://ark.cn-beijing.volces.com/api/v3
    model: "<your_model_name>"       # e.g., "doubao-1-5-pro-32k-250115"
    api_key: <your_llm_api_key>
  ```
  Replace placeholders with your actual credentials and model details.

#### 2. MCP Server Configuration (`mcp.json`)

* This file configures external tools accessible via the Model Context Protocol.
* Copy the example configuration file:
  ```bash
  cp mcp.json.example mcp.json
  ```
* Edit `mcp.json` to define the MCP servers you want to use:
  ```json
  {
    "mcpServers": {
      "amap-maps": { // Example: Map service
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
    }
  }
  ```
  * Update `command` and `args` for each server as per its documentation.
  * Set any required API keys or environment variables for each server.

### Running the Project

You can run the agent in several ways:

#### 1. Simplified Running Scripts (Recommended)

Use the following scripts to run the main program and select from preset questions, without starting any MCP services:

* **For Linux/macOS:**
  ```bash
  ./run_simple.sh
  ```

* **For Cross-Platform (Python):**
  ```bash
  python run_simple.py
  ```

These scripts will:
- Display a list of preset questions for you to choose from
- Support custom question input
- Run the main program directly (without starting any MCP services)

Suitable for simple testing scenarios that don't require MCP services.

#### 2. Using Startup Scripts

These scripts activate the virtual environment and start the application, but do not start MCP servers.

* **For Linux/macOS:**
  ```bash
  ./run.sh
  ```
  (If you get a permission error, run `chmod +x run.sh` first.)

* **For Windows:**
  ```bash
  .\run.bat
  ```

Currently, these scripts run `python main.py` for command-line interaction. This will be updated as the API server is developed.

#### 3. Manual Execution

1. Activate the virtual environment:
   * Linux/macOS: `source .venv/bin/activate`
   * Windows: `.venv\Scripts\activate.bat`

2. Run the main application:
   ```bash
   python main.py
   ```

#### 4. API Server (Under Development)

Run the API server:
```bash
python api_server.py
```

The server will start at http://localhost:5000, providing:
- A simple web interface (accessible at http://localhost:5000)
- REST API endpoints to programmatically invoke the agent

## Project Structure

* `main.py`: Entry point for command-line interaction.
* `api_server.py`: API server entry point.
* `run.sh`, `run.bat`: Startup scripts.
* `run_simple.py`, `run_simple.sh`: Simplified running scripts that only run the main program and select preset questions.
* `agent/flow.py`: Defines the PocketFlow workflow.
* `agent/nodes/`: Contains different nodes for the workflow.
  * `get_tools_node.py`: Handles tool discovery.
  * `decide_tool_node.py`: Decides which tool to use.
  * `execute_tool_node.py`: Executes tool calls.
  * `answer_nodes.py`: Generates the final answer.
* `tools/`: Contains local tool implementations.
* `utils/`: Contains utility functions.
* `conf.yaml`: LLM configuration file.
* `mcp.json`: MCP server configuration file.
* `pyproject.toml`: Project definition and dependency file.
* `.gitignore`: Specifies files to be ignored by Git.
* `ui/`: Web interface files.

## Architecture Overview

This project implements a tool-calling agent using the PocketFlow framework. The core architecture is a directed acyclic graph (DAG) defined in `flow.py`, orchestrating the interaction between different nodes and the LLM.

The main components and their roles are:

1. **Tool Discovery (`GetToolsNode`):** Gathers available tools from configured external MCP servers (defined in `mcp.json`) and built-in local tools.
2. **Tool Decision (`DecideToolNode`):** Sends the user query and available tool information to the LLM (configured in `conf.yaml`) to determine the next action or tool to call.
3. **Tool Execution (`ExecuteToolNode`):** Calls the selected tool. It routes the call to either the local tool implementation or the appropriate external MCP server.
4. **Multi-step Reasoning (`ThinkingNode`):** Allows the LLM to perform a sequence of reasoning steps.
5. **Answer Generation (`AnswerNode`):** Formulates the final response.

## MCP Servers Setup

This project uses multiple MCP (Model Context Protocol) servers for different functionalities.

### Prerequisites

- Node.js and npm/npx installed
- Required API keys
- Playwright browsers installed (`npx playwright install`)

### Configuration

The MCP servers are configured in `mcp.json`. Each server has its own configuration including:
- Command to run
- Arguments
- Environment variables

### Usage

Each MCP server runs on stdio (standard input/output) and can be used by your application. The servers are:

1. Amap Maps MCP Server - For map-related functionality
2. Playwright MCP - For browser automation
3. Tavily MCP - For search and information retrieval

### Running the Servers

To run all servers, you can use the following commands in separate terminal windows:

```bash
# Terminal 1 - Amap Maps
export AMAP_MAPS_API_KEY="YOUR_AMAP_API_KEY"
npx -y @amap/amap-maps-mcp-server

# Terminal 2 - Playwright
npx -y @playwright/mcp@latest

# Terminal 3 - Tavily
export TAVILY_API_KEY="YOUR_TAVILY_API_KEY"
npx -y tavily-mcp@0.1.2
```

### Notes

- Make sure to keep your API keys secure and never commit them to version control
- Each server needs to be running in a separate terminal window
- The servers communicate via stdio, so they should be started before running your main application

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[Specify your license here, e.g., MIT](LICENSE)