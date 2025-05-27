from pydantic import BaseModel, Field
from typing import Dict, Optional, List
import logging
from utils.config import config

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

def get_mcp_config() -> Optional[MCPConfigSchema]:
    """Gets the MCP configuration from the config manager."""
    try:
        mcp_config = config.get_mcp("mcpServers", {})
        if not mcp_config:
            logging.warning("No MCP servers configured")
            return None
        return MCPConfigSchema(mcpServers=mcp_config)
    except Exception as e:
        logging.error(f"Error getting MCP config: {e}")
        return None 