# Project Title

## Introduction

This project is a tool-calling agent built with the PocketFlow framework, integrating local dummy tools and external MCP (Model Context Protocol) servers.

## Development Setup

### Prerequisites

*   Python 3.10+
*   uv
*   Git

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository_url>
    cd <project_directory>
    ```

2.  Ensure you have a `pyproject.toml` file defining your project and dependencies.

3.  Create a virtual environment and install dependencies using uv:
    ```bash
    uv venv
    uv sync
    ```

4.  Copy the example configuration file and update it:
    ```bash
    cp conf_template.yaml conf.yaml
    ```
    Edit `conf.yaml` to configure your LLM API key and base URL, as well as any external MCP servers.

### Running the Project

1.  Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    # On Windows use `.venv\Scripts\activate`
    ```

2.  Run the main application:
    ```bash
    python main.py
    ```

## Project Structure

*   `main.py`: Entry point of the application.
*   `flow.py`: Defines the PocketFlow workflow.
*   `nodes/`: Contains different nodes for the workflow.
    *   `mcp_nodes.py`: Handles discovering, deciding, and executing tools using MCP.
    *   `search_answer_nodes.py`: Contains nodes for multi-step thinking and final answer generation.
*   `tools/`: Contains local tool implementations (e.g., `crawler.py`).
*   `utils/`: Contains utility functions (e.g., `call_llm.py`, `mcp_utils.py`, `mcp_config.py`).
*   `conf.yaml`: Configuration file (copy from `conf_template.yaml` and update).
*   `pyproject.toml`: Project definition and dependency file.
*   `.gitignore`: Specifies files to be ignored by Git.

## Architecture Overview

This project implements a tool-calling agent using the PocketFlow framework. The core architecture is a directed acyclic graph (DAG) defined in `flow.py`, orchestrating the interaction between different nodes and the LLM.

The main components and their roles are:

1.  **Tool Discovery (`GetToolsNode`):** Gathers available tools from configured external MCP servers and built-in local tools (managed by `utils/mcp_utils.py`).
2.  **Tool Decision (`DecideToolNode`):** Sends the user query and available tool information to the LLM (`utils/call_llm.py`) to determine the next action or tool to call.
3.  **Tool Execution (`ExecuteToolNode`):** Calls the selected tool based on the LLM's decision. It routes the call to either the local tool implementation or the appropriate external MCP server via `utils/mcp_utils.py`.
4.  **Multi-step Reasoning (`ThinkingNode`):** Allows the LLM to perform a sequence of reasoning steps, maintaining context and building upon previous thoughts. This node can loop within itself or return to the decision node.
5.  **Answer Generation (`AnswerNode`):** Formulates the final response to the user based on the gathered information from tool executions and the reasoning process.

The flow orchestrates these nodes, enabling the agent to understand user requests, utilize tools, reason, and provide comprehensive answers.

## Architecture Diagram (Coming Soon)

A visual representation of the architecture would greatly enhance understanding of the flow and component interactions. Consider creating an architecture diagram illustrating the nodes, their connections, and the role of the LLM and MCP utilities.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[Specify your license here, e.g., MIT](LICENSE) 