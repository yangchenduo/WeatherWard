"""Agent 工具定义 - 供 LangChain Agent 调用

注意: 当前使用模块级全局变量存储配置，适用于 CLI 单进程场景。
如果未来需要支持多并发 Agent（如 Web 服务），需重构为类模式。
"""

from pathlib import Path

from langchain_core.tools import tool

from weatherward.config import Settings
from weatherward.services.wardrobe import WardrobeService
from weatherward.services.weather import WeatherService, WeatherInfo
from weatherward.services.llm import create_llm


# CLI 单进程场景下使用全局变量是安全的
_settings: Settings | None = None
_wardrobe_path: Path | None = None


def configure(settings: Settings, wardrobe_path: Path | None = None) -> None:
    """初始化工具配置（CLI 启动时调用一次）"""
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
    """查看衣橱索引中有哪些衣服。当用户想知道衣橱里有什么衣服时使用。

    Args:
        folder_path: 衣服图片文件夹路径。留空则使用默认衣橱路径。
    """
    if not _settings:
        return "错误：未初始化配置"

    try:
        from weatherward.services.index import WardrobeIndex

        path = Path(folder_path) if folder_path else _wardrobe_path
        if not path or not path.exists():
            return "错误：衣橱路径不存在，请指定有效的衣服文件夹路径"

        index = WardrobeIndex(path)
        profiles = index.get_all_profiles()

        if not profiles:
            return "衣橱索引为空。请先运行 `weatherward index --wardrobe <路径>` 导入衣服。"

        lines = [f"衣橱中共有 {len(profiles)} 件衣服："]
        for p in profiles:
            lines.append(f"- {p.brief()}")
        return "\n".join(lines)
    except Exception as e:
        return f"查看衣橱失败: {e}"


@tool
async def recommend_outfit(city: str, preference: str = "") -> str:
    """根据天气和衣橱索引推荐今日穿搭。会自动查天气、从索引筛选候选、AI搭配推荐、并审查合理性。

    Args:
        city: 城市名称，如"北京"、"上海"
        preference: 穿搭偏好，如"休闲"、"正式"、"运动"。可为空。
    """
    if not _settings:
        return "错误：未初始化配置"

    if not _wardrobe_path or not _wardrobe_path.exists():
        return "错误：衣橱路径不存在，请先通过 --wardrobe 指定衣橱路径"

    try:
        from weatherward.services.index import WardrobeIndex
        from weatherward.chains.stylist import OutfitStylist
        from weatherward.chains.reviewer import OutfitReviewer

        index = WardrobeIndex(_wardrobe_path)
        profiles = index.get_all_profiles()

        if not profiles:
            return "衣橱索引为空。请先运行 `weatherward index --wardrobe <路径>` 导入衣服。"

        weather_service = WeatherService(
            api_key=_settings.weather.api_key,
            units=_settings.weather.units,
            lang=_settings.weather.lang,
        )
        weather_info = await weather_service.get_weather(city)

        candidates = index.filter_candidates(
            temp=weather_info.temp,
            weather=weather_info.weather,
            preference=preference,
        )

        if not candidates:
            candidates = profiles

        llm = create_llm(_settings.model)
        stylist = OutfitStylist(llm)
        result = await stylist.recommend_from_index(
            weather=weather_info.to_dict(),
            candidates=candidates,
            preference=preference,
        )

        selected_profiles = result["selected_profiles"]
        recommendation = result["recommendation"]

        if selected_profiles:
            reviewer = OutfitReviewer(llm)
            review = await reviewer.review(selected_profiles, weather_info.summary())

            if not review["approved"]:
                issues_text = "；".join(review["issues"])
                result = await stylist.recommend_from_index(
                    weather=weather_info.to_dict(),
                    candidates=candidates,
                    preference=f"{preference}。注意避免：{review['suggestion']}",
                )
                recommendation = result["recommendation"]
                recommendation += f"\n\n> ⚠️ 初次推荐被审查发现问题（{issues_text}），已重新推荐。"

        return f"天气：{weather_info.summary()}\n\n从 {len(profiles)} 件衣服中筛选 {len(candidates)} 件候选后推荐：\n\n{recommendation}"
    except Exception as e:
        return f"生成推荐失败: {e}"


def get_tools() -> list:
    return [get_weather, scan_wardrobe, recommend_outfit]
