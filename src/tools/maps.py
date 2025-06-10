# SPDX-License-Identifier: MIT

import os
from typing import Dict, List, Optional, Union
import requests
from pydantic import BaseModel, Field
from langchain_core.tools import tool


def get_api_key() -> str:
    """Get the AMAP API key from environment variable.

    Returns:
        The API key

    Raises:
        Exception: If API key is not set
    """
    # 优先从环境变量获取
    api_key = os.getenv("AMAP_MAPS_API_KEY", "")
    if not api_key:
        # 如果环境变量中没有，尝试从配置文件获取
        try:
            from src.config.loader import load_yaml_config

            config = load_yaml_config("conf.yaml")
            api_key = config.get("AMAP_MAPS_API_KEY", "")
        except Exception:
            pass

    if not api_key:
        raise Exception(
            "AMAP_MAPS_API_KEY is not set in environment variables or conf.yaml"
        )

    return api_key


class Location(BaseModel):
    """Location information."""

    name: str = Field(..., description="Location name")
    address: str = Field(..., description="Full address")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")


class Route(BaseModel):
    """Route information."""

    distance: float = Field(..., description="Route distance in meters")
    duration: float = Field(..., description="Route duration in seconds")
    steps: List[Dict[str, Union[str, float]]] = Field(..., description="Route steps")


@tool
def search_location(keyword: str) -> List[Location]:
    """Search for locations, places, landmarks, or addresses using keywords globally.
    Use this tool when you need to find specific locations, tourist attractions, restaurants, hotels, or any places without city restriction.

    Args:
        keyword: The search keyword (e.g., "故宫", "天安门", "北京大学", "餐厅", "酒店")

    Returns:
        List of locations with names, addresses, and coordinates matching the search criteria

    Examples:
        - search_location("故宫") - Find the Forbidden City
        - search_location("美食街") - Find food streets
        - search_location("机场") - Find airports
    """
    api_key = get_api_key()
    base_url = "https://restapi.amap.com/v3/place/text"
    # log
    print("---------search_location--------")
    print(keyword)
    params = {
        "key": api_key,
        "keywords": keyword,
        "output": "json",
        "extensions": "base",  # 使用基础信息，而不是all
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data["status"] != "1":
        raise Exception(f"API error: {data.get('info', 'Unknown error')}")

    locations = []
    if "pois" in data and data["pois"]:
        for poi in data["pois"]:
            # 确保location字段存在且格式正确
            if "location" in poi and poi["location"]:
                location_parts = poi["location"].split(",")
                if len(location_parts) == 2:
                    # 处理可能为列表的字段
                    name = poi.get("name", "")
                    if isinstance(name, list):
                        name = name[0] if name else ""

                    address = poi.get("address", "")
                    if isinstance(address, list):
                        address = address[0] if address else ""

                    location = Location(
                        name=str(name),
                        address=str(address),
                        latitude=float(location_parts[1]),
                        longitude=float(location_parts[0]),
                    )
                    locations.append(location)

    return locations


@tool
def search_location_in_city(keyword: str, city: str) -> List[Location]:
    """Search for locations, places, landmarks, or addresses using keywords within a specific city.
    Use this tool when you need to find specific locations within a particular city to get more precise results.

    Args:
        keyword: The search keyword (e.g., "故宫", "天安门", "北京大学", "餐厅", "酒店")
        city: City name to limit the search scope (e.g., "北京", "上海", "广州")

    Returns:
        List of locations with names, addresses, and coordinates matching the search criteria within the specified city

    Examples:
        - search_location_in_city("故宫", "北京") - Find the Forbidden City in Beijing
        - search_location_in_city("海滩", "海口") - Find beaches in Haikou
        - search_location_in_city("大学", "上海") - Find universities in Shanghai
    """
    api_key = get_api_key()
    base_url = "https://restapi.amap.com/v3/place/text"
    # log
    print("---------search_location_in_city--------")
    print(keyword)
    print(city)
    params = {
        "key": api_key,
        "keywords": keyword,
        "city": city,
        "citylimit": True,  # 限制在指定城市内搜索
        "output": "json",
        "extensions": "base",  # 使用基础信息，而不是all
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data["status"] != "1":
        raise Exception(f"API error: {data.get('info', 'Unknown error')}")

    locations = []
    if "pois" in data and data["pois"]:
        for poi in data["pois"]:
            # 确保location字段存在且格式正确
            if "location" in poi and poi["location"]:
                location_parts = poi["location"].split(",")
                if len(location_parts) == 2:
                    # 处理可能为列表的字段
                    name = poi.get("name", "")
                    if isinstance(name, list):
                        name = name[0] if name else ""

                    address = poi.get("address", "")
                    if isinstance(address, list):
                        address = address[0] if address else ""

                    location = Location(
                        name=str(name),
                        address=str(address),
                        latitude=float(location_parts[1]),
                        longitude=float(location_parts[0]),
                    )
                    locations.append(location)

    return locations


@tool
def get_route(origin: str, destination: str, mode: str = "driving") -> Route:
    """Get route directions and travel information between two locations.
    Use this tool when you need to plan routes, calculate travel time, or get directions between places.

    Args:
        origin: Starting location name or address (e.g., "北京站", "天安门广场")
        destination: Destination location name or address (e.g., "故宫", "王府井")
        mode: Transportation mode - currently supports "driving" (default)

    Returns:
        Route information including total distance (meters), duration (seconds), and step-by-step directions

    Examples:
        - get_route("天安门", "故宫") - Get driving directions from Tiananmen to Forbidden City
        - get_route("机场", "市中心", "driving") - Get route from airport to city center
    """
    api_key = get_api_key()
    base_url = "https://restapi.amap.com/v3/direction/driving"

    # First get coordinates for origin and destination
    origin_locations = search_location.invoke({"keyword": origin})
    dest_locations = search_location.invoke({"keyword": destination})
    # log
    print("---------get_route--------")
    print(origin)
    print(destination)
    if not origin_locations or not dest_locations:
        raise Exception("Could not find coordinates for origin or destination")

    origin_coords = f"{origin_locations[0].longitude},{origin_locations[0].latitude}"
    dest_coords = f"{dest_locations[0].longitude},{dest_locations[0].latitude}"

    params = {
        "key": api_key,
        "origin": origin_coords,
        "destination": dest_coords,
        "extensions": "all",
        "output": "json",
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data["status"] != "1":
        raise Exception(f"API error: {data.get('info', 'Unknown error')}")

    route_info = data["route"]
    steps = []
    for step in route_info["paths"][0]["steps"]:
        steps.append(
            {
                "instruction": step["instruction"],
                "distance": float(step["distance"]),
                "duration": float(step["duration"]),
            }
        )

    return Route(
        distance=float(route_info["paths"][0]["distance"]),
        duration=float(route_info["paths"][0]["duration"]),
        steps=steps,
    )


@tool
def get_nearby_places(
    location: str, radius: int = 1000, types: str = None
) -> List[Location]:
    """Search for places and points of interest near a specific location.
    Use this tool when you need to find nearby restaurants, hotels, attractions, services, or facilities around a location.

    Args:
        location: Center location name or address (e.g., "天安门", "北京大学", "海口市政府")
        radius: Search radius in meters (default: 1000m, max: 50000m)
        types: Optional POI types to filter results (e.g., "餐饮服务", "住宿服务", "旅游景点")

    Returns:
        List of nearby places with names, addresses, and coordinates

    Examples:
        - get_nearby_places("故宫") - Find all places near the Forbidden City
        - get_nearby_places("海口火车站", 2000, "餐饮服务") - Find restaurants within 2km of Haikou Station
        - get_nearby_places("天安门广场", 500, "旅游景点") - Find tourist attractions within 500m of Tiananmen Square
    """
    api_key = get_api_key()
    base_url = "https://restapi.amap.com/v3/place/around"
    # log
    print("---------get_nearby_places--------")
    print(location)
    print(radius)
    print(types)
    # First get coordinates for the center location
    locations = search_location.invoke({"keyword": location})
    if not locations:
        raise Exception("Could not find coordinates for the center location")

    center_coords = f"{locations[0].longitude},{locations[0].latitude}"

    params = {
        "key": api_key,
        "location": center_coords,
        "radius": radius,
        "extensions": "all",
        "output": "json",
        "offset": 20,  # 返回结果数量
        "page": 1,  # 页码
    }

    if types:
        params["types"] = types

    response = requests.get(base_url, params=params)
    data = response.json()

    if data["status"] != "1":
        raise Exception(f"API error: {data.get('info', 'Unknown error')}")

    locations = []
    if "pois" in data and data["pois"]:
        for poi in data["pois"]:
            # 确保location字段存在且格式正确
            if "location" in poi and poi["location"]:
                location_parts = poi["location"].split(",")
                if len(location_parts) == 2:
                    # 处理可能为列表的字段
                    name = poi.get("name", "")
                    if isinstance(name, list):
                        name = name[0] if name else ""

                    address = poi.get("address", "")
                    if isinstance(address, list):
                        address = address[0] if address else ""

                    location = Location(
                        name=str(name),
                        address=str(address),
                        latitude=float(location_parts[1]),
                        longitude=float(location_parts[0]),
                    )
                    locations.append(location)

    return locations
