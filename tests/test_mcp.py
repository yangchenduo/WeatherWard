"""MCP Server 测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from PIL import Image

from weatherward.mcp.server import list_tools, call_tool


class TestMCPTools:
    """MCP 工具测试"""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """测试列出工具"""
        tools = await list_tools()

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "get_outfit_recommendation" in tool_names
        assert "get_weather" in tool_names

    @pytest.mark.asyncio
    async def test_outfit_recommendation_tool_schema(self):
        """测试穿搭推荐工具的 schema"""
        tools = await list_tools()
        outfit_tool = next(t for t in tools if t.name == "get_outfit_recommendation")

        schema = outfit_tool.inputSchema
        assert "wardrobe_path" in schema["properties"]
        assert "city" in schema["properties"]
        assert "preference" in schema["properties"]
        assert "wardrobe_path" in schema["required"]
        assert "city" in schema["required"]

    @pytest.mark.asyncio
    async def test_weather_tool_schema(self):
        """测试天气工具的 schema"""
        tools = await list_tools()
        weather_tool = next(t for t in tools if t.name == "get_weather")

        schema = weather_tool.inputSchema
        assert "city" in schema["properties"]
        assert "city" in schema["required"]

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """测试调用未知工具"""
        with patch("weatherward.mcp.server.load_settings"):
            result = await call_tool("unknown_tool", {})
            assert "未知工具" in result[0].text


class TestOutfitRecommendation:
    """穿搭推荐工具测试"""

    @pytest.fixture
    def wardrobe_dir(self, tmp_path):
        """创建测试衣橱"""
        for i in range(3):
            img_path = tmp_path / f"shirt_{i}.jpg"
            img = Image.new("RGB", (100, 100))
            img.save(img_path)
        return tmp_path

    @pytest.mark.asyncio
    async def test_empty_wardrobe(self, tmp_path):
        """测试空衣橱"""
        with patch("weatherward.mcp.server.load_settings") as mock_settings:
            mock_settings.return_value = MagicMock()

            result = await call_tool("get_outfit_recommendation", {
                "wardrobe_path": str(tmp_path),
                "city": "北京",
            })

            assert "衣橱为空" in result[0].text

    @pytest.mark.asyncio
    async def test_wardrobe_not_found(self):
        """测试衣橱不存在"""
        with patch("weatherward.mcp.server.load_settings") as mock_settings:
            mock_settings.return_value = MagicMock()

            with pytest.raises(FileNotFoundError):
                await call_tool("get_outfit_recommendation", {
                    "wardrobe_path": "/nonexistent/path",
                    "city": "北京",
                })
