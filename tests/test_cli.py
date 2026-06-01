"""CLI 测试"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner
from PIL import Image

from weatherward.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def wardrobe_dir(tmp_path):
    """创建测试衣橱目录"""
    for i in range(3):
        img_path = tmp_path / f"shirt_{i}.jpg"
        img = Image.new("RGB", (100, 100))
        img.save(img_path)
    return tmp_path


class TestCLI:
    """CLI 命令测试"""

    def test_help(self, runner):
        """测试帮助信息"""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "WeatherWard" in result.output
        assert "recommend" in result.output
        assert "chat" in result.output

    def test_recommend_help(self, runner):
        """测试 recommend 子命令帮助"""
        result = runner.invoke(main, ["recommend", "--help"])
        assert result.exit_code == 0
        assert "--wardrobe" in result.output
        assert "--city" in result.output

    def test_chat_help(self, runner):
        """测试 chat 子命令帮助"""
        result = runner.invoke(main, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--wardrobe" in result.output
        assert "交互式" in result.output

    def test_no_subcommand_shows_help(self, runner):
        """测试无子命令时显示帮助"""
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "recommend" in result.output
        assert "chat" in result.output

    def test_recommend_missing_required_args(self, runner):
        """测试 recommend 缺少必需参数"""
        result = runner.invoke(main, ["recommend"])
        assert result.exit_code != 0

    def test_recommend_wardrobe_not_found(self, runner):
        """测试衣橱目录不存在"""
        result = runner.invoke(main, [
            "recommend",
            "--wardrobe", "/nonexistent/path",
            "--city", "北京",
        ])
        assert result.exit_code != 0

    def test_recommend_json_output_format(self, runner, wardrobe_dir):
        """测试 JSON 输出格式"""
        with (
            patch("weatherward.cli.load_settings") as mock_settings,
            patch("weatherward.cli.WeatherService") as mock_weather,
            patch("weatherward.cli.create_llm") as mock_llm,
        ):
            mock_settings.return_value = MagicMock()
            mock_settings.return_value.weather.api_key = "test"
            mock_settings.return_value.weather.units = "metric"
            mock_settings.return_value.weather.lang = "zh_cn"
            mock_settings.return_value.model = MagicMock()

            mock_weather_instance = AsyncMock()
            mock_weather_instance.get_weather = AsyncMock(return_value=MagicMock(
                summary=lambda: "北京天气：晴，25°C",
                to_dict=lambda: {
                    "city": "北京", "temp": 25.0,
                    "feels_like": 23.0, "humidity": 45,
                    "weather": "晴", "wind_speed": 3.5,
                },
            ))
            mock_weather.return_value = mock_weather_instance

            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke = AsyncMock(return_value=MagicMock(
                content="推荐穿搭：白色T恤 + 牛仔裤"
            ))
            mock_llm.return_value = mock_llm_instance

            result = runner.invoke(main, [
                "recommend",
                "--wardrobe", str(wardrobe_dir),
                "--city", "北京",
                "--output", "json",
            ])
