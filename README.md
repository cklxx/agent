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
*   `tools/`: Contains local tool implementations (e.g., `crawler.py`).
*   `utils/`: Contains utility functions (e.g., `call_llm.py`, `mcp_utils.py`, `mcp_config.py`).
*   `conf.yaml`: Configuration file (copy from `conf_template.yaml` and update).
*   `pyproject.toml`: Project definition and dependency file.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[Specify your license here, e.g., MIT](LICENSE) 