"""配置管理模块"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class ModelConfig:
    """模型配置"""
    provider: str = "mimo"
    api_key: str = ""
    model_id: str = "mimo-v2.5"
    base_url: str = "https://api.xiaomimimo.com/v1"
    max_tokens: int = 2048


@dataclass
class WeatherConfig:
    """天气服务配置"""
    api_key: str = ""
    default_city: str = "Beijing"
    units: str = "metric"
    lang: str = "zh_cn"


@dataclass
class WardrobeConfig:
    """衣橱配置"""
    default_path: str = ""
    supported_formats: list[str] = field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]
    )
    max_image_size_mb: int = 50


@dataclass
class Settings:
    """应用配置"""
    model: ModelConfig = field(default_factory=ModelConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    wardrobe: WardrobeConfig = field(default_factory=WardrobeConfig)


def load_settings(
    env_file: str | None = None,
    config_file: str | None = None,
) -> Settings:
    """
    加载配置

    优先级：环境变量 > 配置文件 > 默认值
    """
    # 加载 .env 文件
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    # 加载配置文件
    file_config = {}
    if config_file and Path(config_file).exists():
        with open(config_file, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}

    # 构建配置
    model_config = file_config.get("model", {})
    weather_config = file_config.get("weather", {})
    wardrobe_config = file_config.get("wardrobe", {})

    return Settings(
        model=ModelConfig(
            provider=os.getenv("MODEL_PROVIDER", model_config.get("provider", "mimo")),
            api_key=os.getenv("MIMO_API_KEY", model_config.get("api_key", "")),
            model_id=os.getenv("MODEL_ID", model_config.get("model_id", "mimo-v2.5")),
            base_url=model_config.get("base_url", "https://api.xiaomimimo.com/v1"),
            max_tokens=model_config.get("max_tokens", 2048),
        ),
        weather=WeatherConfig(
            api_key=os.getenv("OPENWEATHER_API_KEY", weather_config.get("api_key", "")),
            default_city=os.getenv("DEFAULT_CITY", weather_config.get("default_city", "Beijing")),
            units=weather_config.get("units", "metric"),
            lang=weather_config.get("lang", "zh_cn"),
        ),
        wardrobe=WardrobeConfig(
            default_path=wardrobe_config.get("default_path", ""),
            supported_formats=wardrobe_config.get(
                "supported_formats",
                [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]
            ),
            max_image_size_mb=wardrobe_config.get("max_image_size_mb", 50),
        ),
    )
