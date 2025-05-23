# Project Agent

## Introduction

This project is a tool-calling agent built with the PocketFlow framework, integrating local dummy tools and external MCP (Model Context Protocol) servers. It can be invoked via the command line, and soon, via an API and a simple web interface.

## Development Setup

### Prerequisites

*   Python 3.10+
*   uv (for Python environment and package management)
*   Git

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

### Configuration

#### 1. LLM Configuration (`conf.yaml`)

*   Copy the example configuration file:
    ```bash
    cp conf.yaml.example conf.yaml
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

### Upcoming Features: API and Web UI

Work is in progress to provide:
*   An API endpoint to invoke the agent programmatically.
*   A simple web interface to interact with the agent and view invocation steps.

## Project Structure

*   `main.py`: Entry point for command-line interaction.
*   `api_server.py`: (Upcoming) Entry point for the API server.
*   `run.sh`, `run.bat`: Startup scripts.
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