import yaml
import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class Config:
    _instance = None
    _config = None
    _env_config = None
    _mcp_config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()
        if self._env_config is None:
            self._load_env()
        if self._mcp_config is None:
            self._load_mcp()

    def _load_config(self):
        """Load configuration from conf.yaml"""
        try:
            with open("conf.yaml", "r") as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Error loading conf.yaml: {e}")
            self._config = {}

    def _load_env(self):
        """Load configuration from .env file"""
        self._env_config = {}
        try:
            env_path = Path(".env")
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            self._env_config[key.strip()] = value.strip()
        except Exception as e:
            logging.error(f"Error loading .env: {e}")

    def _load_mcp(self):
        """Load configuration from mcp.json"""
        try:
            with open("mcp.json", "r") as f:
                self._mcp_config = json.load(f)
        except Exception as e:
            logging.error(f"Error loading mcp.json: {e}")
            self._mcp_config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key from conf.yaml"""
        return self._config.get(key, default)

    def get_env(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key from .env file"""
        return self._env_config.get(key, default)

    def get_mcp(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key from mcp.json"""
        return self._mcp_config.get(key, default)

    def get_model_type(self) -> str:
        """Get current model type"""
        return self.get("MODEL_TYPE", "qwen").lower()

    def get_basic_model_config(self) -> Dict:
        """Get basic model configuration"""
        return self.get("BASIC_MODEL", {})

    def get_image_gen_model_config(self) -> Dict:
        """Get image generation model configuration"""
        return self.get("IMAGE_GEN_MODEL", {})

    def get_mcp_servers(self) -> Dict:
        """Get MCP servers configuration"""
        return self.get_mcp("servers", {})

    def get_mcp_tools(self) -> Dict:
        """Get MCP tools configuration"""
        return self.get_mcp("tools", {})

# 创建全局配置实例
config = Config() 