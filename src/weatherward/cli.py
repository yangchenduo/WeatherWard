"""CLI 命令行界面"""

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from weatherward.config import load_settings
from weatherward.services.wardrobe import WardrobeService
from weatherward.services.weather import WeatherService
from weatherward.services.llm import create_llm
from weatherward.chains.stylist import OutfitStylist

if os.name == "nt":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

console = Console(highlight=False)


async def _index_wardrobe(
    wardrobe_path: Path,
    import_path: Path | None,
    config_file: str | None,
) -> None:
    from weatherward.services.index import WardrobeIndex
    from weatherward.chains.indexer import ClothingIndexer
    import shutil

    settings = load_settings(config_file=config_file)

    if import_path and import_path.exists():
        imported = []
        supported = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        for f in import_path.iterdir():
            if f.is_file() and f.suffix.lower() in supported:
                dest = wardrobe_path / f.name
                shutil.move(str(f), str(dest))
                imported.append(f.name)
        if imported:
            console.print(f"\n[cyan][IMPORT][/cyan] Moved {len(imported)} images from {import_path}:")
            for name in imported:
                console.print(f"   - {name}")
        else:
            console.print(f"\n[dim]No new images in {import_path}[/dim]")

    console.print(f"\n[bold][DIR][/bold] wardrobe: {wardrobe_path}")

    index = WardrobeIndex(wardrobe_path)
    new_items, deleted_files = index.detect_changes()

    if deleted_files:
        console.print(f"\n[red][DEL][/red] {len(deleted_files)} items removed:")
        for f in deleted_files:
            console.print(f"   - {f}")
        index.remove_deleted(deleted_files)

    if not new_items:
        console.print("\n[green][OK][/green] No new items to analyze")
        if deleted_files:
            index.save()
            console.print("   Index updated (removed deleted items)")
        console.print(f"\n[bold]Index:[/bold] {len(index.get_all_profiles())} items")
        return

    console.print(f"\n[cyan][NEW][/cyan] {len(new_items)} new items to analyze:")
    for item in new_items:
        console.print(f"   - {item.name}")

    llm = create_llm(settings.model)
    indexer = ClothingIndexer(llm)
    wardrobe_service = WardrobeService()

    console.print("\n[bold]Analyzing (batch size: 3)...[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Analyzing 0/{len(new_items)}...", total=len(new_items)
        )

        batch_size = 3
        all_profiles = []
        for i in range(0, len(new_items), batch_size):
            batch = new_items[i:i + batch_size]
            batch_profiles = await indexer.index_items(
                batch, wardrobe_service, batch_size=batch_size
            )
            all_profiles.extend(batch_profiles)
            progress.update(
                task,
                advance=len(batch),
                description=f"Analyzing {min(i + batch_size, len(new_items))}/{len(new_items)}...",
            )

    index.add_profiles(all_profiles)
    index.save()

    console.print(f"\n[green][DONE][/green] Indexed {len(index.get_all_profiles())} items total")

    for p in all_profiles:
        console.print(f"   [green]+[/green] {p.brief()}")


async def _run(
    wardrobe_path: Path,
    city: str,
    preference: str,
    output_format: str,
    config_file: str | None,
    weather_text: str | None,
) -> None:
    from weatherward.services.index import WardrobeIndex
    from weatherward.chains.reviewer import OutfitReviewer

    settings = load_settings(config_file=config_file)

    index = WardrobeIndex(wardrobe_path)
    profiles = index.get_all_profiles()

    if not profiles:
        console.print("[red]Index is empty! Run `weatherward index` first.[/red]")
        sys.exit(1)

    console.print(f"\n[bold]Wardrobe:[/bold] {wardrobe_path} ({len(profiles)} indexed)")

    if weather_text:
        console.print(f"\n[bold]Weather (manual):[/bold] {weather_text}")
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
        console.print(f"\n[bold]Weather:[/bold] fetching {city}...")
        weather_service = WeatherService(
            api_key=settings.weather.api_key,
            units=settings.weather.units,
            lang=settings.weather.lang,
        )
        weather_info = await weather_service.get_weather(city)
    console.print(f"   {weather_info.summary()}")

    console.print("\n[bold]Filtering candidates...[/bold]")
    candidates = index.filter_candidates(
        temp=weather_info.temp,
        weather=weather_info.weather,
        preference=preference,
    )
    console.print(f"   {len(candidates)}/{len(profiles)} items matched")

    if not candidates:
        console.print("[yellow]No matches, using all items[/yellow]")
        candidates = profiles

    console.print("\n[bold]AI recommending...[/bold]")
    llm = create_llm(settings.model)
    stylist = OutfitStylist(llm)
    result = await stylist.recommend_from_index(
        weather=weather_info.to_dict(),
        candidates=candidates,
        preference=preference,
    )

    selected_profiles = result["selected_profiles"]
    recommendation = result["recommendation"]

    if selected_profiles:
        console.print("\n[bold]Reviewing outfit...[/bold]")
        reviewer = OutfitReviewer(llm)
        review = await reviewer.review(selected_profiles, weather_info.summary())

        if not review["approved"]:
            console.print("[yellow]   [!] Issues found:[/yellow]")
            for issue in review["issues"]:
                console.print(f"      - {issue}")
            if review["suggestion"]:
                console.print(f"   Suggestion: {review['suggestion']}")

            console.print("\n   [bold]Re-recommending...[/bold]")
            result = await stylist.recommend_from_index(
                weather=weather_info.to_dict(),
                candidates=candidates,
                preference=f"{preference}. Avoid: {review['suggestion']}",
            )
            recommendation = result["recommendation"]

    if output_format == "json":
        import json
        output = {
            "weather": weather_info.to_dict(),
            "candidates_count": len(candidates),
            "selected_files": result["selected_files"],
            "recommendation": recommendation,
            "preference": preference,
        }
        console.print_json(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        console.print()
        console.print(Panel(
            Markdown(recommendation),
            title="Today's Outfit",
            border_style="green",
        ))


async def _chat_loop(
    wardrobe_path: Path | None,
    config_file: str | None,
) -> None:
    from weatherward.agent.chat import WardrobeAgent

    settings = load_settings(config_file=config_file)
    agent = WardrobeAgent(settings, wardrobe_path)

    console.print(Panel(
        "[bold green]WeatherWard - Smart Wardrobe Assistant[/bold green]\n\n"
        "Chat with me in natural language:\n"
        "  - What should I wear today?\n"
        "  - How's the weather?\n"
        "  - What's in my wardrobe?\n"
        "  - What to wear on a rainy day?\n\n"
        "Type [bold]exit[/bold] or [bold]quit[/bold] to leave, "
        "[bold]reset[/bold] to start over.",
        title="Welcome",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = console.input("\n[bold cyan]You: [/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Bye![/yellow]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[yellow]Bye![/yellow]")
            break

        if user_input.lower() in ("reset",):
            agent.reset()
            console.print("[green]Conversation reset[/green]")
            continue

        with console.status("[bold green]Thinking...[/bold green]"):
            try:
                response = await agent.chat(user_input)
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                continue

        console.print()
        console.print(Panel(
            Markdown(response),
            title="Assistant",
            border_style="green",
        ))


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """WeatherWard - Smart Wardrobe Assistant

    Recommend outfits based on weather and your wardrobe.

    Commands:
      index      Import clothes into index
      recommend  One-shot outfit recommendation
      chat       Interactive chat mode
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.option(
    "--wardrobe", "-w",
    default="./my_clothes",
    type=click.Path(exists=True, path_type=Path),
    help="Path to clothes image folder (default: ./my_clothes)",
)
@click.option(
    "--import-from", "-i",
    "import_from",
    default="./import_clothes",
    type=click.Path(path_type=Path),
    help="Import folder for new clothes (default: ./import_clothes)",
)
@click.option(
    "--config",
    default=None,
    type=click.Path(exists=True),
    help="Config file path",
)
def index(
    wardrobe: Path,
    import_from: Path,
    config: str | None,
) -> None:
    """Import clothes into index

    1. Move new images from import folder into wardrobe
    2. Analyze new images with AI
    3. Remove deleted items from index

    Example:

        weatherward index
        weatherward index --wardrobe ./my_clothes --import-from ./import_clothes
    """
    try:
        asyncio.run(_index_wardrobe(wardrobe, import_from, config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--wardrobe", "-w",
    default="./my_clothes",
    type=click.Path(exists=True, path_type=Path),
    help="Path to clothes image folder (default: ./my_clothes)",
)
@click.option(
    "--city", "-c",
    required=True,
    help="City name (e.g. Beijing, Dalian)",
)
@click.option(
    "--preference", "-p",
    default="",
    help="Style preference (e.g. casual, formal, sporty)",
)
@click.option(
    "--output", "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option(
    "--config",
    default=None,
    type=click.Path(exists=True),
    help="Config file path",
)
@click.option(
    "--weather",
    default=None,
    help="Manual weather (e.g. sunny, cloudy, rainy), skip API",
)
def recommend(
    wardrobe: Path,
    city: str,
    preference: str,
    output: str,
    config: str | None,
    weather: str | None,
) -> None:
    """One-shot outfit recommendation

    Based on wardrobe index and weather (run index first).

    Examples:

        weatherward recommend --wardrobe ./my_clothes --city Beijing -p casual

        weatherward recommend --wardrobe ./my_clothes --city Dalian --weather sunny
    """
    try:
        asyncio.run(_run(wardrobe, city, preference, output, config, weather))
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--wardrobe", "-w",
    default="./my_clothes",
    type=click.Path(exists=True, path_type=Path),
    help="Path to clothes image folder (default: ./my_clothes)",
)
@click.option(
    "--config",
    default=None,
    type=click.Path(exists=True),
    help="Config file path",
)
def chat(
    wardrobe: Path | None,
    config: str | None,
) -> None:
    """Interactive chat mode (AI Agent)

    Start a conversational wardrobe assistant.

    Examples:

        weatherward chat

        weatherward chat --wardrobe ./my_clothes
    """
    try:
        asyncio.run(_chat_loop(wardrobe, config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
