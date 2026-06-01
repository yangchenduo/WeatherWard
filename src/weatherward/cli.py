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
    weather_text: str | None,
) -> None:
    """核心运行逻辑"""
    settings = load_settings(config_file=config_file)

    console.print(f"\n👔 扫描衣橱: {wardrobe_path}")
    wardrobe_service = WardrobeService()
    items = wardrobe_service.scan(wardrobe_path)

    if not items:
        console.print("[red]衣橱为空，没有找到衣服图片！[/red]")
        sys.exit(1)

    console.print(f"   找到 {len(items)} 件衣服")

    if weather_text:
        console.print(f"\n🌤️  手动天气: {weather_text}")
        from weatherward.services.weather import WeatherInfo
        weather_info = WeatherInfo(
            city=city,
            temp=25.0,
            feels_like=25.0,
            humidity=50,
            weather=weather_text,
            wind_speed=3.0,
        )
    else:
        console.print(f"\n🌤️  获取 {city} 的天气...")
        weather_service = WeatherService(
            api_key=settings.weather.api_key,
            units=settings.weather.units,
            lang=settings.weather.lang,
        )
        weather_info = await weather_service.get_weather(city)
    console.print(f"   {weather_info.summary()}")

    console.print("\n🔍 分析衣服图片...")
    llm = create_llm(settings.model)
    analyzer = ClothingAnalyzer(llm)

    images_to_analyze = items[:5]
    base64_images = [
        wardrobe_service.load_image_as_base64(item)
        for item in images_to_analyze
    ]
    clothing_analysis = await analyzer.analyze(base64_images)
    console.print("   分析完成")

    console.print("\n✨ 生成搭配推荐...")
    stylist = OutfitStylist(llm)
    recommendation = await stylist.recommend(
        weather=weather_info.to_dict(),
        clothing_list=clothing_analysis,
        preference=preference,
    )

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


async def _chat_loop(
    wardrobe_path: Path | None,
    config_file: str | None,
) -> None:
    """交互式对话循环"""
    from weatherward.agent.chat import WardrobeAgent

    settings = load_settings(config_file=config_file)
    agent = WardrobeAgent(settings, wardrobe_path)

    console.print(Panel(
        "[bold green]WeatherWard 智能衣橱助手[/bold green]\n\n"
        "你可以用自然语言和我对话，例如：\n"
        "  • 今天北京穿什么？\n"
        "  • 上海天气怎么样？\n"
        "  • 我衣橱里有什么衣服？\n"
        "  • 下雨天怎么搭配？\n\n"
        "输入 [bold]exit[/bold] 或 [bold]quit[/bold] 退出，"
        "输入 [bold]reset[/bold] 重置对话。",
        title="👔 欢迎",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = console.input("\n[bold cyan]你：[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]再见！👋[/yellow]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q", "退出"):
            console.print("[yellow]再见！👋[/yellow]")
            break

        if user_input.lower() in ("reset", "重置"):
            agent.reset()
            console.print("[green]对话已重置[/green]")
            continue

        with console.status("[bold green]思考中...[/bold green]"):
            try:
                response = await agent.chat(user_input)
            except Exception as e:
                console.print(f"\n[red]错误: {e}[/red]")
                continue

        console.print()
        console.print(Panel(
            Markdown(response),
            title="🤖 助手",
            border_style="green",
        ))


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """WeatherWard - 智能衣服搭配助手

    根据天气和衣橱推荐今天的穿搭。

    使用 `weatherward recommend` 一次性推荐，或 `weatherward chat` 交互式对话。
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
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
@click.option(
    "--weather",
    default=None,
    help="手动指定天气（如：晴天、多云、小雨），跳过 API 调用",
)
def recommend(
    wardrobe: Path,
    city: str,
    preference: str,
    output: str,
    config: str | None,
    weather: str | None,
) -> None:
    """一次性穿搭推荐（脚本模式）

    示例:

        weatherward recommend --wardrobe ./my_clothes --city 北京 --preference 休闲

        weatherward recommend --wardrobe ./my_clothes --city 大连 --weather 晴天
    """
    try:
        asyncio.run(_run(wardrobe, city, preference, output, config, weather))
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--wardrobe", "-w",
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="衣服图片文件夹路径（可选，也可在对话中指定）",
)
@click.option(
    "--config",
    default=None,
    type=click.Path(exists=True),
    help="配置文件路径",
)
def chat(
    wardrobe: Path | None,
    config: str | None,
) -> None:
    """交互式对话模式（AI Agent）

    启动对话式衣橱助手，你可以用自然语言和 AI 交流。

    示例:

        weatherward chat --wardrobe ./my_clothes

        weatherward chat
    """
    try:
        asyncio.run(_chat_loop(wardrobe, config))
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
