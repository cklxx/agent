import json
from typing import Any, Dict, List

class DictObject(dict):
    """一个字典包装类，支持点号访问属性。"""
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        for key, value in data.items():
            if isinstance(value, dict):
                self[key] = DictObject(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                self[key] = [DictObject(item) for item in value]

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'DictObject' 对象没有属性 '{key}'")

    def __repr__(self) -> str:
        return json.dumps(self, ensure_ascii=False, indent=2) 