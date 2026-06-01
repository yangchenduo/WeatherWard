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
    for i in range(3):
        img_path = tmp_path / f"shirt_{i}.jpg"
        img = Image.new("RGB", (100, 100))
        img.save(img_path)
    return tmp_path


class TestCLI:

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "WeatherWard" in result.output
        assert "index" in result.output
        assert "recommend" in result.output
        assert "chat" in result.output

    def test_index_help(self, runner):
        result = runner.invoke(main, ["index", "--help"])
        assert result.exit_code == 0
        assert "--wardrobe" in result.output

    def test_recommend_help(self, runner):
        result = runner.invoke(main, ["recommend", "--help"])
        assert result.exit_code == 0
        assert "--wardrobe" in result.output
        assert "--city" in result.output

    def test_chat_help(self, runner):
        result = runner.invoke(main, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--wardrobe" in result.output

    def test_no_subcommand_shows_help(self, runner):
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "index" in result.output
        assert "recommend" in result.output
        assert "chat" in result.output

    def test_recommend_missing_required_args(self, runner):
        result = runner.invoke(main, ["recommend"])
        assert result.exit_code != 0

    def test_recommend_wardrobe_not_found(self, runner):
        result = runner.invoke(main, [
            "recommend",
            "--wardrobe", "/nonexistent/path",
            "--city", "Beijing",
        ])
        assert result.exit_code != 0

    def test_index_wardrobe_not_found(self, runner):
        result = runner.invoke(main, [
            "index",
            "--wardrobe", "/nonexistent/path",
        ])
        assert result.exit_code != 0
