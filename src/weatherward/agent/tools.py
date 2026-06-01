"""Agent 工具定义 - 供 LangChain Agent 调用"""

import asyncio
from pathlib import Path

from langchain_core.tools import tool

from weatherward.config import Settings
from weatherward.services.wardrobe import WardrobeService
from weatherward.services.weather import WeatherService, WeatherInfo
from weatherward.chains.analyzer import ClothingAnalyzer
from weatherward.services.llm import create_llm


_settings: Settings | None = None
_wardrobe_path: Path | None = None


def configure(settings: Settings, wardrobe_path: Path | None = None) -> None:
    global _settings, _wardrobe_path
    _settings = settings
    _wardrobe_path = wardrobe_path


@tool
async def get_weather(city: str) -> str:
    """获取指定城市的当前天气信息。当用户询问天气、或需要根据天气推荐穿搭时使用。

    Args:
        city: 城市名称，如"北京"、"上海"、"大连"
    """
    if not _settings:
        return "错误：未初始化配置"

    try:
        weather_service = WeatherService(
            api_key=_settings.weather.api_key,
            units=_settings.weather.units,
            lang=_settings.weather.lang,
        )
        weather_info = await weather_service.get_weather(city)
        return weather_info.summary()
    except Exception as e:
        return f"查询天气失败: {e}"


@tool
async def scan_wardrobe(folder_path: str = "") -> str:
    """扫描衣橱文件夹，列出所有可用的衣服。当用户想知道衣橱里有什么衣服时使用。

    Args:
        folder_path: 衣服图片文件夹路径。留空则使用默认衣橱路径。
    """
    if not _settings:
        return "错误：未初始化配置"

    try:
        path = Path(folder_path) if folder_path else _wardrobe_path
        if not path or not path.exists():
            return "错误：衣橱路径不存在，请指定有效的衣服文件夹路径"

        wardrobe_service = WardrobeService()
        items = wardrobe_service.scan(path)

        if not items:
            return "衣橱为空，没有找到衣服图片"

        return f"衣橱中共有 {len(items)} 件衣服：\n" + "\n".join(
            f"- {item.name}" for item in items
        )
    except Exception as e:
        return f"扫描衣橱失败: {e}"


@tool
async def analyze_clothing(folder_path: str = "") -> str:
    """分析衣橱中的衣服图片，识别款式、颜色、材质等。当需要了解衣服详细信息以进行搭配推荐时使用。

    Args:
        folder_path: 衣服图片文件夹路径。留空则使用默认衣橱路径。
    """
    if not _settings:
        return "错误：未初始化配置"

    try:
        path = Path(folder_path) if folder_path else _wardrobe_path
        if not path or not path.exists():
            return "错误：衣橱路径不存在，请指定有效的衣服文件夹路径"

        wardrobe_service = WardrobeService()
        items = wardrobe_service.scan(path)

        if not items:
            return "衣橱为空，没有找到衣服图片"

        llm = create_llm(_settings.model)
        analyzer = ClothingAnalyzer(llm)

        images_to_analyze = items[:5]
        base64_images = [
            wardrobe_service.load_image_as_base64(item)
            for item in images_to_analyze
        ]
        result = await analyzer.analyze(base64_images)
        return result
    except Exception as e:
        return f"分析衣服失败: {e}"


@tool
async def recommend_outfit(city: str, preference: str = "") -> str:
    """根据天气和衣橱推荐今日穿搭。这是一个综合工具，会自动查询天气、分析衣橱并给出推荐。

    Args:
        city: 城市名称，如"北京"、"上海"
        preference: 穿搭偏好，如"休闲"、"正式"、"运动"。可为空。
    """
    if not _settings:
        return "错误：未初始化配置"

    if not _wardrobe_path or not _wardrobe_path.exists():
        return "错误：衣橱路径不存在，请先通过 --wardrobe 指定衣橱路径"

    try:
        weather_service = WeatherService(
            api_key=_settings.weather.api_key,
            units=_settings.weather.units,
            lang=_settings.weather.lang,
        )
        weather_info = await weather_service.get_weather(city)

        wardrobe_service = WardrobeService()
        items = wardrobe_service.scan(_wardrobe_path)
        if not items:
            return "衣橱为空，没有找到衣服图片"

        llm = create_llm(_settings.model)
        analyzer = ClothingAnalyzer(llm)

        images_to_analyze = items[:5]
        base64_images = [
            wardrobe_service.load_image_as_base64(item)
            for item in images_to_analyze
        ]
        clothing_analysis = await analyzer.analyze(base64_images)

        from weatherward.chains.stylist import OutfitStylist
        stylist = OutfitStylist(llm)
        recommendation = await stylist.recommend(
            weather=weather_info.to_dict(),
            clothing_list=clothing_analysis,
            preference=preference,
        )
        return recommendation
    except Exception as e:
        return f"生成推荐失败: {e}"


def get_tools() -> list:
    return [get_weather, scan_wardrobe, analyze_clothing, recommend_outfit]
