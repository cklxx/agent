from pydantic import BaseModel, Field
from typing import Dict, Optional, List
import json
import os
import logging

class CommandServer(BaseModel):
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    fromGalleryId: Optional[str] = None

class URLServer(BaseModel):
    url: str
    token: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    server_script: Optional[str] = None # For consistency, though URL servers are usually standalone

class MCPConfigSchema(BaseModel):
    mcpServers: Dict[str, CommandServer | URLServer]

def load_mcp_config(filepath: str = "mcp.json") -> Optional[MCPConfigSchema]:
    """Loads and parses the MCP configuration from a JSON file."""
    if not os.path.exists(filepath):
        logging.warning(f"MCP config file not found at {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        return MCPConfigSchema(**config_data)
    except Exception as e:
        logging.error(f"Error loading or parsing MCP config file {filepath}: {e}")
        return None 