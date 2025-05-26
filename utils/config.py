import yaml
import logging
from typing import Dict, Any, Optional

class Config:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self):
        """Load configuration from conf.yaml"""
        try:
            with open("conf.yaml", "r") as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        return self._config.get(key, default)

    def get_model_type(self) -> str:
        """Get current model type"""
        return self.get("MODEL_TYPE", "qwen").lower()

    def get_basic_model_config(self) -> Dict:
        """Get basic model configuration"""
        return self.get("BASIC_MODEL", {})

    def get_image_gen_model_config(self) -> Dict:
        """Get image generation model configuration"""
        return self.get("IMAGE_GEN_MODEL", {})

# 创建全局配置实例
config = Config() 