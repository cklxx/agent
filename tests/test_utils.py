#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utils模块测试
"""

import pytest
import json
import logging # Added for caplog
from src.utils.json_utils import repair_json_output


class TestJsonUtils:
    """JSON工具测试类"""

    def test_repair_json_output_valid_json_object(self):
        """测试有效的JSON对象"""
        content = '{"name": "test", "value": 123}'
        result = repair_json_output(content)
        assert json.loads(result) == {"name": "test", "value": 123}

    def test_repair_json_output_valid_json_array(self):
        """测试有效的JSON数组"""
        content = '[1, 2, 3, "test"]'
        result = repair_json_output(content)
        assert json.loads(result) == [1, 2, 3, "test"]

    def test_repair_json_output_with_json_code_block(self):
        """测试包含```json代码块的内容"""
        content = '```json\n{"name": "test", "value": 456}\n```'
        result = repair_json_output(content)
        assert json.loads(result) == {"name": "test", "value": 456}

    def test_repair_json_output_with_ts_code_block(self):
        """测试包含```ts代码块的内容"""
        content = '```ts\n{"name": "test", "value": 789}\n```'
        result = repair_json_output(content)
        assert json.loads(result) == {"name": "test", "value": 789}

    def test_repair_json_output_with_whitespace(self):
        """测试包含前后空白字符的JSON"""
        content = '  \n {"name": "test"}  \n  '
        result = repair_json_output(content)
        assert json.loads(result) == {"name": "test"}

    def test_repair_json_output_non_json_content(self):
        """测试非JSON内容"""
        content = "This is just a regular string"
        result = repair_json_output(content)
        assert result == content

    def test_repair_json_output_empty_string(self):
        """测试空字符串"""
        content = ""
        result = repair_json_output(content)
        assert result == ""

    def test_repair_json_output_malformed_json(self):
        """测试格式错误的JSON（依赖json_repair库修复）"""
        content = '{"name": "test", "value": 123,}'  # 末尾多余逗号
        result = repair_json_output(content)
        # json_repair应该能修复这个错误
        assert json.loads(result) == {"name": "test", "value": 123}

    def test_repair_json_output_chinese_content(self):
        """测试包含中文的JSON"""
        content = '{"姓名": "测试", "数值": 123}'
        result = repair_json_output(content)
        parsed = json.loads(result)
        assert parsed == {"姓名": "测试", "数值": 123}

    def test_repair_json_output_json_only_prefix(self):
        """测试只有```json前缀没有后缀的情况"""
        content = '```json\n{"name": "test"}'
        result = repair_json_output(content)
        assert json.loads(result) == {"name": "test"}

    def test_repair_json_output_ts_only_prefix(self):
        """测试只有```ts前缀没有后缀的情况"""
        content = '```ts\n{"name": "test"}'
        result = repair_json_output(content)
        assert json.loads(result) == {"name": "test"}

    def test_repair_json_output_invalid_json_fallback(self):
        """测试无法修复的内容返回原内容"""
        content = "This is definitely not JSON and cannot be repaired"
        result = repair_json_output(content)
        # 如果修复失败，应该返回原内容
        assert result == content

    def test_repair_json_output_more_unicode_chars(self):
        """测试包含更多Unicode字符的JSON确保ensure_ascii=False"""
        content = '{"sign": "✔", "currency": "€", "text": "你好世界"}'
        expected = {"sign": "✔", "currency": "€", "text": "你好世界"}
        result = repair_json_output(content)
        # Parse the result back to a Python dict for comparison
        # to avoid issues with key order or whitespace differences in the string representation
        assert json.loads(result) == expected, f"Expected {expected}, got {json.loads(result)}"

    def test_repair_json_output_logs_warning_on_repair_failure(self, caplog):
        """测试在JSON修复失败时记录警告日志"""
        # This content (unpaired high surrogate) should cause json_repair.loads() to raise an exception.
        malformed_content = '{"key": "\uD800"}'

        # Set the level for the specific logger and caplog.
        # Pytest's caplog should capture logs from loggers that propagate to root.
        logging.getLogger("src.utils.json_utils").setLevel(logging.WARNING)
        caplog.set_level(logging.WARNING)

        result = repair_json_output(malformed_content)

        assert result == malformed_content # Should return original content
        assert len(caplog.records) == 1
        assert "JSON repair failed" in caplog.records[0].message
