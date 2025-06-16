#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Maps Tools 模块详细测试
"""

import pytest
from unittest.mock import patch, Mock
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.maps import (
    search_location,
    search_location_in_city,
    get_route,
    get_nearby_places,
    Location,
    Route,
)


class TestSearchLocation:
    """测试search_location工具"""

    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_search_location_basic(self, mock_get_api_key, mock_requests_get):
        """测试基本位置搜索"""
        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "pois": [
                {
                    "name": "天安门",
                    "address": "北京市东城区",
                    "location": "116.397000,39.909000",
                },
                {
                    "name": "天安门广场",
                    "address": "北京市东城区",
                    "location": "116.394000,39.906000",
                },
            ],
        }
        mock_requests_get.return_value = mock_response

        result = search_location.func("天安门")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(location, Location) for location in result)
        assert result[0].name == "天安门"
        assert result[0].latitude == 39.909000

    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_search_location_no_results(self, mock_get_api_key, mock_requests_get):
        """测试无搜索结果"""
        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {"status": "1", "pois": []}
        mock_requests_get.return_value = mock_response

        result = search_location.func("不存在的地点")

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_search_location_api_error(self, mock_get_api_key, mock_requests_get):
        """测试API错误"""
        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {"status": "0", "info": "API_KEY错误"}
        mock_requests_get.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            search_location.func("天安门")

        assert "API error" in str(exc_info.value)

    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_search_location_multiple_results(
        self, mock_get_api_key, mock_requests_get
    ):
        """测试多个搜索结果"""
        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        # 模拟多个结果
        pois = []
        for i in range(5):
            pois.append(
                {
                    "name": f"测试地点{i}",
                    "address": f"测试地址{i}",
                    "location": f"116.{i:03d},39.{i:03d}",
                }
            )

        mock_response.json.return_value = {"status": "1", "pois": pois}
        mock_requests_get.return_value = mock_response

        result = search_location.func("测试地点")

        assert isinstance(result, list)
        assert len(result) == 5
        assert all(isinstance(location, Location) for location in result)

    def test_search_location_tool_attributes(self):
        """测试工具属性"""
        assert hasattr(search_location, "name")
        assert hasattr(search_location, "description")
        assert hasattr(search_location, "func")

        assert search_location.name == "search_location"
        assert "keyword" in search_location.description
        assert len(search_location.description) < 500

    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_search_location_special_characters(
        self, mock_get_api_key, mock_requests_get
    ):
        """测试特殊字符搜索"""
        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "pois": [
                {
                    "name": "café & restaurant",
                    "address": "北京市朝阳区",
                    "location": "116.400000,39.900000",
                }
            ],
        }
        mock_requests_get.return_value = mock_response

        result = search_location.func("café & restaurant")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name == "café & restaurant"


class TestGetRoute:
    """测试get_route工具"""

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_get_route_basic(
        self, mock_get_api_key, mock_requests_get, mock_search_location
    ):
        """测试基本路线规划"""
        # 模拟起点和终点位置
        mock_origin = Location(
            name="天安门", address="北京市东城区", longitude=116.397, latitude=39.909
        )
        mock_dest = Location(
            name="故宫", address="北京市东城区", longitude=116.394, latitude=39.917
        )

        mock_search_location.invoke.side_effect = [[mock_origin], [mock_dest]]

        # 模拟路线API响应
        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "1500",
                        "duration": "300",
                        "steps": [
                            {
                                "instruction": "向北走",
                                "distance": "500",
                                "duration": "100",
                            },
                            {
                                "instruction": "右转",
                                "distance": "1000",
                                "duration": "200",
                            },
                        ],
                    }
                ]
            },
        }
        mock_requests_get.return_value = mock_response

        result = get_route.func("天安门", "故宫")

        assert isinstance(result, Route)
        assert result.distance == 1500
        assert result.duration == 300
        assert len(result.steps) == 2

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.get_api_key")
    def test_get_route_no_origin_found(self, mock_get_api_key, mock_search_location):
        """测试找不到起点"""
        mock_get_api_key.return_value = "test_api_key"
        mock_search_location.invoke.side_effect = [
            [],  # 起点搜索无结果
            [Location(name="dest", address="addr", longitude=116.0, latitude=39.0)],
        ]

        with pytest.raises(Exception) as exc_info:
            get_route.func("不存在的起点", "存在的终点")

        assert "Could not find coordinates" in str(exc_info.value)

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.get_api_key")
    def test_get_route_no_destination_found(
        self, mock_get_api_key, mock_search_location
    ):
        """测试找不到终点"""
        mock_get_api_key.return_value = "test_api_key"
        mock_search_location.invoke.side_effect = [
            [Location(name="origin", address="addr", longitude=116.0, latitude=39.0)],
            [],  # 终点搜索无结果
        ]

        with pytest.raises(Exception) as exc_info:
            get_route.func("存在的起点", "不存在的终点")

        assert "Could not find coordinates" in str(exc_info.value)

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_get_route_with_mode(
        self, mock_get_api_key, mock_requests_get, mock_search_location
    ):
        """测试指定交通方式的路线规划"""
        # 模拟基本设置
        mock_origin = Location(
            name="A", address="addr1", longitude=116.0, latitude=39.0
        )
        mock_dest = Location(name="B", address="addr2", longitude=116.1, latitude=39.1)

        mock_search_location.invoke.side_effect = [[mock_origin], [mock_dest]]

        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "route": {"paths": [{"distance": "2000", "duration": "600", "steps": []}]},
        }
        mock_requests_get.return_value = mock_response

        result = get_route.func("A", "B", "driving")

        assert isinstance(result, Route)

    def test_get_route_tool_attributes(self):
        """测试get_route工具属性"""
        assert hasattr(get_route, "name")
        assert hasattr(get_route, "description")
        assert hasattr(get_route, "func")

        assert get_route.name == "get_route"
        assert len(get_route.description) < 500


class TestGetNearbyPlaces:
    """测试get_nearby_places工具"""

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_get_nearby_places_basic(
        self, mock_get_api_key, mock_requests_get, mock_search_location
    ):
        """测试基本周边搜索"""
        # 模拟中心位置搜索
        mock_center = Location(
            name="天安门", address="北京市东城区", longitude=116.397, latitude=39.909
        )
        mock_search_location.invoke.return_value = [mock_center]

        # 模拟周边搜索API响应
        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "pois": [
                {
                    "name": "人民大会堂",
                    "address": "北京市西城区",
                    "location": "116.394000,39.906000",
                },
                {
                    "name": "国家博物馆",
                    "address": "北京市东城区",
                    "location": "116.400000,39.905000",
                },
            ],
        }
        mock_requests_get.return_value = mock_response

        result = get_nearby_places.func("天安门")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(place, Location) for place in result)

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_get_nearby_places_with_radius(
        self, mock_get_api_key, mock_requests_get, mock_search_location
    ):
        """测试指定半径的周边搜索"""
        mock_center = Location(
            name="center", address="addr", longitude=116.0, latitude=39.0
        )
        mock_search_location.invoke.return_value = [mock_center]

        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {"status": "1", "pois": []}
        mock_requests_get.return_value = mock_response

        result = get_nearby_places.func("center", radius=2000)

        # 验证API调用中包含半径参数
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert "2000" in str(call_args)

        assert isinstance(result, list)

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_get_nearby_places_with_types(
        self, mock_get_api_key, mock_requests_get, mock_search_location
    ):
        """测试指定类型的周边搜索"""
        mock_center = Location(
            name="center", address="addr", longitude=116.0, latitude=39.0
        )
        mock_search_location.invoke.return_value = [mock_center]

        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {"status": "1", "pois": []}
        mock_requests_get.return_value = mock_response

        result = get_nearby_places.func("center", types="餐饮服务")

        # 验证API调用中包含类型参数
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert "餐饮服务" in str(call_args)

        assert isinstance(result, list)

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.get_api_key")
    def test_get_nearby_places_center_not_found(
        self, mock_get_api_key, mock_search_location
    ):
        """测试中心位置未找到"""
        mock_get_api_key.return_value = "test_api_key"
        mock_search_location.invoke.return_value = []

        with pytest.raises(Exception) as exc_info:
            get_nearby_places.func("不存在的位置")

        assert "Could not find coordinates" in str(exc_info.value)

    @patch("src.tools.maps.search_location")
    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_get_nearby_places_api_error(
        self, mock_get_api_key, mock_requests_get, mock_search_location
    ):
        """测试API错误"""
        mock_center = Location(
            name="center", address="addr", longitude=116.0, latitude=39.0
        )
        mock_search_location.invoke.return_value = [mock_center]

        mock_get_api_key.return_value = "test_api_key"
        mock_response = Mock()
        mock_response.json.return_value = {"status": "0", "info": "API错误"}
        mock_requests_get.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            get_nearby_places.func("center")

        assert "API error" in str(exc_info.value)

    def test_get_nearby_places_tool_attributes(self):
        """测试get_nearby_places工具属性"""
        assert hasattr(get_nearby_places, "name")
        assert hasattr(get_nearby_places, "description")
        assert hasattr(get_nearby_places, "func")

        assert get_nearby_places.name == "get_nearby_places"
        assert len(get_nearby_places.description) < 500


class TestMapsToolsIntegration:
    """测试地图工具集成功能"""

    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_location_search_to_route_workflow(
        self, mock_get_api_key, mock_requests_get
    ):
        """测试从位置搜索到路线规划的完整工作流"""
        mock_get_api_key.return_value = "test_api_key"

        # 设置多个API调用的响应 - 确保有足够的响应
        mock_responses = []

        # 第一次调用：搜索起点
        origin_response = Mock()
        origin_response.json.return_value = {
            "status": "1",
            "pois": [
                {
                    "name": "起点",
                    "address": "起点地址",
                    "location": "116.000000,39.000000",
                }
            ],
        }
        mock_responses.append(origin_response)

        # 第二次调用：搜索终点
        dest_response = Mock()
        dest_response.json.return_value = {
            "status": "1",
            "pois": [
                {
                    "name": "终点",
                    "address": "终点地址",
                    "location": "116.100000,39.100000",
                }
            ],
        }
        mock_responses.append(dest_response)

        # 第三次调用：再次搜索起点（get_route内部调用）
        mock_responses.append(origin_response)

        # 第四次调用：再次搜索终点（get_route内部调用）
        mock_responses.append(dest_response)

        # 第五次调用：路线规划
        route_response = Mock()
        route_response.json.return_value = {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "10000",
                        "duration": "1800",
                        "steps": [
                            {"instruction": "出发", "distance": "0", "duration": "0"},
                            {
                                "instruction": "到达",
                                "distance": "10000",
                                "duration": "1800",
                            },
                        ],
                    }
                ]
            },
        }
        mock_responses.append(route_response)

        mock_requests_get.side_effect = mock_responses

        # 执行完整工作流
        # 1. 搜索起点
        origins = search_location.func("起点")
        assert len(origins) == 1

        # 2. 搜索终点
        destinations = search_location.func("终点")
        assert len(destinations) == 1

        # 3. 获取路线
        route = get_route.func("起点", "终点")
        assert isinstance(route, Route)
        assert route.distance == 10000
        assert route.duration == 1800

    @patch("src.tools.maps.requests.get")
    @patch("src.tools.maps.get_api_key")
    def test_nearby_places_workflow(self, mock_get_api_key, mock_requests_get):
        """测试周边搜索工作流"""
        mock_get_api_key.return_value = "test_api_key"

        # 设置API响应 - 确保有足够的响应
        responses = []

        # 位置搜索响应（可能被调用2次）
        search_response = Mock()
        search_response.json.return_value = {
            "status": "1",
            "pois": [
                {
                    "name": "中心位置",
                    "address": "中心地址",
                    "location": "116.000000,39.000000",
                }
            ],
        }
        responses.append(search_response)
        responses.append(search_response)  # 添加第二次响应

        # 周边搜索响应
        nearby_response = Mock()
        nearby_response.json.return_value = {
            "status": "1",
            "pois": [
                {
                    "name": "周边1",
                    "address": "地址1",
                    "location": "116.001000,39.001000",
                },
                {
                    "name": "周边2",
                    "address": "地址2",
                    "location": "116.002000,39.002000",
                },
            ],
        }
        responses.append(nearby_response)

        mock_requests_get.side_effect = responses

        # 执行工作流
        center_locations = search_location.func("中心位置")
        assert len(center_locations) == 1

        nearby_places = get_nearby_places.func("中心位置")
        assert len(nearby_places) == 2
        assert all(isinstance(place, Location) for place in nearby_places)


class TestMapsDataModels:
    """测试地图数据模型"""

    def test_location_model(self):
        """测试Location模型"""
        location = Location(
            name="测试地点", address="测试地址", longitude=116.0, latitude=39.0
        )

        assert location.name == "测试地点"
        assert location.address == "测试地址"
        assert location.longitude == 116.0
        assert location.latitude == 39.0

    def test_route_model(self):
        """测试Route模型"""
        steps = [
            {"instruction": "第一步", "distance": 100.0, "duration": 30.0},
            {"instruction": "第二步", "distance": 200.0, "duration": 60.0},
        ]
        route = Route(distance=1500, duration=300, steps=steps)

        assert route.distance == 1500
        assert route.duration == 300
        assert len(route.steps) == 2
        assert route.steps[0]["instruction"] == "第一步"


class TestMapsToolsDocumentation:
    """测试地图工具文档"""

    def test_all_tools_have_documentation(self):
        """测试所有工具都有文档"""
        tools = [search_location, get_route, get_nearby_places]

        for tool in tools:
            doc = tool.description
            assert "Tool that can operate on any number of inputs." not in doc
            assert len(doc) > 10


def test_maps_tools_import():
    """测试地图工具导入"""
    from src.tools.maps import search_location, get_route, get_nearby_places

    assert callable(search_location.func)
    assert callable(get_route.func)
    assert callable(get_nearby_places.func)


def test_maps_tools_basic():
    """测试地图工具基本属性"""
    tools = [search_location, get_route, get_nearby_places]

    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "func")
        assert callable(tool.func)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
