"""CLI 命令行界面"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from weatherward.config import load_settings
from weatherward.services.wardrobe import WardrobeService
from weatherward.services.weather import WeatherService
from weatherward.services.llm import create_llm
from weatherward.chains.analyzer import ClothingAnalyzer
from weatherward.chains.stylist import OutfitStylist

console = Console()


async def _run(
    wardrobe_path: Path,
    city: str,
    preference: str,
    output_format: str,
    config_file: str | None,
) -> None:
    """核心运行逻辑"""
    # 1. 加载配置
    settings = load_settings(config_file=config_file)

    # 2. 扫描衣橱
    console.print(f"\n👔 扫描衣橱: {wardrobe_path}")
    wardrobe_service = WardrobeService()
    items = wardrobe_service.scan(wardrobe_path)

    if not items:
        console.print("[red]衣橱为空，没有找到衣服图片！[/red]")
        sys.exit(1)

    console.print(f"   找到 {len(items)} 件衣服")

    # 3. 获取天气
    console.print(f"\n🌤️  获取 {city} 的天气...")
    weather_service = WeatherService(
        api_key=settings.weather.api_key,
        units=settings.weather.units,
        lang=settings.weather.lang,
    )
    weather_info = await weather_service.get_weather(city)
    console.print(f"   {weather_info.summary()}")

    # 4. 分析衣服（可选，用于生成描述）
    console.print("\n🔍 分析衣服图片...")
    llm = create_llm(settings.model)
    analyzer = ClothingAnalyzer(llm)

    # 只取前 5 张图片进行分析（避免 token 过多）
    images_to_analyze = items[:5]
    base64_images = [
        wardrobe_service.load_image_as_base64(item)
        for item in images_to_analyze
    ]
    clothing_analysis = await analyzer.analyze(base64_images)
    console.print("   分析完成")

    # 5. 生成搭配推荐
    console.print("\n✨ 生成搭配推荐...")
    stylist = OutfitStylist(llm)
    recommendation = await stylist.recommend(
        weather=weather_info.to_dict(),
        clothing_list=clothing_analysis,
        preference=preference,
    )

    # 6. 输出结果
    if output_format == "json":
        import json
        result = {
            "weather": weather_info.to_dict(),
            "clothing_analysis": clothing_analysis,
            "recommendation": recommendation,
            "preference": preference,
        }
        console.print_json(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        console.print()
        console.print(Panel(
            Markdown(recommendation),
            title="👔 今日穿搭推荐",
            border_style="green",
        ))


@click.command()
@click.option(
    "--wardrobe", "-w",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="衣服图片文件夹路径",
)
@click.option(
    "--city", "-c",
    required=True,
    help="城市名称（如：北京、上海）",
)
@click.option(
    "--preference", "-p",
    default="",
    help="搭配偏好（如：休闲、正式、运动）",
)
@click.option(
    "--output", "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="输出格式",
)
@click.option(
    "--config",
    default=None,
    type=click.Path(exists=True),
    help="配置文件路径",
)
def main(
    wardrobe: Path,
    city: str,
    preference: str,
    output: str,
    config: str | None,
) -> None:
    """WeatherWard - 智能衣服搭配助手

    根据天气和衣橱推荐今天的穿搭。

    示例:

        weatherward --wardrobe ./my_clothes --city 北京 --preference 休闲
    """
    try:
        asyncio.run(_run(wardrobe, city, preference, output, config))
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
