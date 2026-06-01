"""LangChain 链测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage

from weatherward.chains.analyzer import ClothingAnalyzer
from weatherward.chains.stylist import OutfitStylist
from weatherward.services.llm import create_llm
from weatherward.config import ModelConfig


class TestCreateLLM:
    """LLM 工厂测试"""

    def test_create_mimo_llm(self):
        config = ModelConfig(
            provider="mimo",
            api_key="test-key",
            model_id="mimo-v2.5",
            base_url="https://api.xiaomimimo.com/v1",
        )
        llm = create_llm(config)
        assert llm is not None
        assert llm.model_name == "mimo-v2.5"

    def test_create_deepseek_llm(self):
        config = ModelConfig(
            provider="deepseek",
            api_key="test-key",
            model_id="deepseek-chat",
        )
        llm = create_llm(config)
        assert llm is not None
        assert llm.model_name == "deepseek-chat"

    def test_create_minimax_llm(self):
        config = ModelConfig(
            provider="minimax",
            api_key="test-key",
            model_id="minimax-text-01",
            base_url="https://api.minimax.chat/v1",
        )
        llm = create_llm(config)
        assert llm is not None

    def test_create_unknown_provider(self):
        config = ModelConfig(provider="unknown", api_key="test-key")
        with pytest.raises(ValueError, match="Unknown provider"):
            create_llm(config)


class TestClothingAnalyzer:
    """衣服分析链测试"""

    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(
            content="这是一件白色棉质T恤，适合夏季穿着。"
        ))
        return llm

    @pytest.mark.asyncio
    async def test_analyze_single_image(self, mock_llm):
        analyzer = ClothingAnalyzer(mock_llm)
        result = await analyzer.analyze(["base64_encoded_image_data"])
        assert isinstance(result, str)
        assert len(result) > 0
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_multiple_images(self, mock_llm):
        analyzer = ClothingAnalyzer(mock_llm)
        result = await analyzer.analyze(["img1_base64", "img2_base64", "img3_base64"])
        assert isinstance(result, str)
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_empty_images(self, mock_llm):
        analyzer = ClothingAnalyzer(mock_llm)
        with pytest.raises(ValueError, match="至少需要一张图片"):
            await analyzer.analyze([])


class TestOutfitStylist:
    """搭配推荐链测试"""

    RECOMMENDATION_TEXT = """## 推荐穿搭

### 上衣
白色棉质T恤 - 透气舒适，适合当前温度

### 下装
蓝色牛仔裤 - 经典百搭

### 外套
薄款开衫 - 早晚温差备用

### 鞋子
白色运动鞋 - 舒适休闲

### 搭配理由
今天天气晴朗，温度适中，适合轻薄透气的穿搭。

### 搭配小贴士
可以搭配一顶棒球帽防晒。"""

    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(
            content=self.RECOMMENDATION_TEXT
        ))
        return llm

    @pytest.mark.asyncio
    async def test_recommend_outfit(self, mock_llm):
        stylist = OutfitStylist(mock_llm)
        weather = {
            "city": "北京", "temp": 25.0, "feels_like": 23.0,
            "humidity": 45, "weather": "晴", "wind_speed": 3.5,
        }
        result = await stylist.recommend(
            weather, "1. 白色T恤\n2. 蓝色牛仔裤\n3. 薄款开衫", "休闲"
        )
        assert isinstance(result, str)
        assert "上衣" in result or "T恤" in result
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_without_preference(self, mock_llm):
        stylist = OutfitStylist(mock_llm)
        weather = {
            "city": "上海", "temp": 30.0, "feels_like": 32.0,
            "humidity": 70, "weather": "多云", "wind_speed": 5.0,
        }
        result = await stylist.recommend(weather, "1. 短袖衬衫\n2. 短裤", "")
        assert isinstance(result, str)
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_cold_weather(self, mock_llm):
        stylist = OutfitStylist(mock_llm)
        weather = {
            "city": "哈尔滨", "temp": -15.0, "feels_like": -20.0,
            "humidity": 30, "weather": "雪", "wind_speed": 8.0,
        }
        result = await stylist.recommend(
            weather, "1. 羽绒服\n2. 毛衣\n3. 保暖裤\n4. 雪地靴", "保暖"
        )
        assert isinstance(result, str)
