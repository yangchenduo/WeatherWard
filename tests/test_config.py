"""配置管理模块测试"""

import os
import pytest
import tempfile
from pathlib import Path

from weatherward.config import load_settings, Settings, ModelConfig, WeatherConfig, WardrobeConfig


class TestSettings:
    """Settings 数据类测试"""

    def test_default_settings(self):
        """测试默认配置"""
        settings = Settings()
        assert settings.model.provider == "mimo"
        assert settings.model.model_id == "mimo-v2.5"
        assert settings.weather.units == "metric"
        assert settings.weather.lang == "zh_cn"
        assert ".jpg" in settings.wardrobe.supported_formats


class TestLoadSettings:
    """load_settings 函数测试"""

    def test_load_with_env_vars(self, monkeypatch):
        """测试从环境变量加载配置"""
        monkeypatch.setenv("MIMO_API_KEY", "test-mimo-key")
        monkeypatch.setenv("OPENWEATHER_API_KEY", "test-weather-key")
        monkeypatch.setenv("DEFAULT_CITY", "Shanghai")
        monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
        monkeypatch.setenv("MODEL_ID", "deepseek-chat")

        settings = load_settings()

        assert settings.model.api_key == "test-mimo-key"
        assert settings.model.provider == "deepseek"
        assert settings.model.model_id == "deepseek-chat"
        assert settings.weather.api_key == "test-weather-key"
        assert settings.weather.default_city == "Shanghai"

    def test_load_with_config_file(self, tmp_path):
        """测试从配置文件加载"""
        config_content = """
model:
  provider: minimax
  model_id: minimax-text-01
  base_url: https://api.minimax.chat/v1

weather:
  default_city: Guangzhou
  units: imperial

wardrobe:
  default_path: /path/to/clothes
  max_image_size_mb: 20
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        settings = load_settings(config_file=str(config_file))

        assert settings.model.provider == "minimax"
        assert settings.model.model_id == "minimax-text-01"
        assert settings.weather.default_city == "Guangzhou"
        assert settings.weather.units == "imperial"
        assert settings.wardrobe.default_path == "/path/to/clothes"
        assert settings.wardrobe.max_image_size_mb == 20

    def test_env_vars_override_config_file(self, monkeypatch, tmp_path):
        """测试环境变量覆盖配置文件"""
        config_content = """
model:
  provider: minimax
weather:
  default_city: Guangzhou
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
        monkeypatch.setenv("DEFAULT_CITY", "Beijing")

        settings = load_settings(config_file=str(config_file))

        # 环境变量应该覆盖配置文件
        assert settings.model.provider == "deepseek"
        assert settings.weather.default_city == "Beijing"

    def test_load_missing_config_file(self):
        """测试加载不存在的配置文件"""
        settings = load_settings(config_file="/nonexistent/config.yaml")

        # 应该使用默认值
        assert settings.model.provider == "mimo"
        assert settings.weather.default_city == "Beijing"

    def test_load_missing_env_file(self):
        """测试加载不存在的 .env 文件"""
        settings = load_settings(env_file="/nonexistent/.env")

        # 应该使用默认值
        assert settings.model.api_key == ""
        assert settings.weather.api_key == ""
