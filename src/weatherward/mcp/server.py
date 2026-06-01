"""MCP Server - 供 Hermes Agent 调用"""

import asyncio
import json
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from weatherward.config import load_settings
from weatherward.services.wardrobe import WardrobeService
from weatherward.services.weather import WeatherService
from weatherward.services.llm import create_llm
from weatherward.chains.analyzer import ClothingAnalyzer
from weatherward.chains.stylist import OutfitStylist

app = Server("weatherward")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="get_outfit_recommendation",
            description="根据天气和衣橱推荐穿搭。传入衣服图片文件夹路径和城市名称，返回穿搭推荐。",
            inputSchema={
                "type": "object",
                "properties": {
                    "wardrobe_path": {
                        "type": "string",
                        "description": "衣服图片文件夹路径",
                    },
                    "city": {
                        "type": "string",
                        "description": "城市名称（如：北京、上海）",
                    },
                    "preference": {
                        "type": "string",
                        "description": "搭配偏好（如：休闲、正式、运动）",
                        "default": "",
                    },
                },
                "required": ["wardrobe_path", "city"],
            },
        ),
        Tool(
            name="get_weather",
            description="获取指定城市的当前天气信息。",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称（如：北京、上海）",
                    },
                },
                "required": ["city"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """调用工具"""
    settings = load_settings()

    if name == "get_outfit_recommendation":
        return await _handle_outfit_recommendation(settings, arguments)
    elif name == "get_weather":
        return await _handle_get_weather(settings, arguments)
    else:
        return [TextContent(type="text", text=f"未知工具: {name}")]


async def _handle_outfit_recommendation(
    settings,
    arguments: dict,
) -> list[TextContent]:
    """处理穿搭推荐请求"""
    wardrobe_path = Path(arguments["wardrobe_path"])
    city = arguments["city"]
    preference = arguments.get("preference", "")

    # 扫描衣橱
    wardrobe_service = WardrobeService()
    items = wardrobe_service.scan(wardrobe_path)

    if not items:
        return [TextContent(type="text", text="衣橱为空，没有找到衣服图片。")]

    # 获取天气
    weather_service = WeatherService(
        api_key=settings.weather.api_key,
        units=settings.weather.units,
        lang=settings.weather.lang,
    )
    weather_info = await weather_service.get_weather(city)

    # 分析衣服
    llm = create_llm(settings.model)
    analyzer = ClothingAnalyzer(llm)

    images_to_analyze = items[:5]
    base64_images = [
        wardrobe_service.load_image_as_base64(item)
        for item in images_to_analyze
    ]
    clothing_analysis = await analyzer.analyze(base64_images)

    # 生成推荐
    stylist = OutfitStylist(llm)
    recommendation = await stylist.recommend(
        weather=weather_info.to_dict(),
        clothing_list=clothing_analysis,
        preference=preference,
    )

    result = {
        "weather": weather_info.to_dict(),
        "clothing_count": len(items),
        "recommendation": recommendation,
    }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_get_weather(settings, arguments: dict) -> list[TextContent]:
    """处理天气查询请求"""
    city = arguments["city"]

    weather_service = WeatherService(
        api_key=settings.weather.api_key,
        units=settings.weather.units,
        lang=settings.weather.lang,
    )
    weather_info = await weather_service.get_weather(city)

    return [TextContent(
        type="text",
        text=json.dumps(weather_info.to_dict(), ensure_ascii=False, indent=2),
    )]


async def main():
    """启动 MCP Server"""
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
