"""天气服务测试"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from weatherward.services.weather import WeatherService, WeatherInfo


class TestWeatherInfo:
    """WeatherInfo 数据类测试"""

    def test_create_weather_info(self):
        """测试创建天气信息"""
        info = WeatherInfo(
            city="北京",
            temp=25.0,
            feels_like=23.0,
            humidity=45,
            weather="晴",
            wind_speed=3.5,
        )

        assert info.city == "北京"
        assert info.temp == 25.0
        assert info.feels_like == 23.0
        assert info.humidity == 45
        assert info.weather == "晴"
        assert info.wind_speed == 3.5

    def test_weather_info_to_dict(self):
        """测试转换为字典"""
        info = WeatherInfo(
            city="上海",
            temp=28.0,
            feels_like=30.0,
            humidity=70,
            weather="多云",
            wind_speed=5.0,
        )

        result = info.to_dict()

        assert result["city"] == "上海"
        assert result["temp"] == 28.0
        assert result["feels_like"] == 30.0
        assert result["humidity"] == 70
        assert result["weather"] == "多云"
        assert result["wind_speed"] == 5.0

    def test_weather_info_summary(self):
        """测试天气摘要"""
        info = WeatherInfo(
            city="广州",
            temp=32.0,
            feels_like=35.0,
            humidity=80,
            weather="雷阵雨",
            wind_speed=8.0,
        )

        summary = info.summary()

        assert "广州" in summary
        assert "32" in summary
        assert "雷阵雨" in summary


class TestWeatherService:
    """WeatherService 测试"""

    @pytest.fixture
    def service(self):
        """创建天气服务实例"""
        return WeatherService(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_get_weather_success(self, service):
        """测试成功获取天气"""
        mock_response = {
            "main": {
                "temp": 25.0,
                "feels_like": 23.0,
                "humidity": 45,
            },
            "weather": [{"description": "晴"}],
            "wind": {"speed": 3.5},
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            result = await service.get_weather("北京")

            assert isinstance(result, WeatherInfo)
            assert result.city == "北京"
            assert result.temp == 25.0
            assert result.weather == "晴"

    @pytest.mark.asyncio
    async def test_get_weather_city_not_found(self, service):
        """测试城市不存在"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=404,
                json=lambda: {"message": "city not found"},
            )

            with pytest.raises(ValueError, match="城市不存在"):
                await service.get_weather("不存在的城市")

    @pytest.mark.asyncio
    async def test_get_weather_api_error(self, service):
        """测试 API 错误"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )

            with pytest.raises(httpx.HTTPStatusError):
                await service.get_weather("北京")

    @pytest.mark.asyncio
    async def test_get_weather_network_error(self, service):
        """测试网络错误"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(httpx.ConnectError):
                await service.get_weather("北京")

    @pytest.mark.asyncio
    async def test_get_weather_with_units(self, service):
        """测试使用公制单位"""
        mock_response = {
            "main": {"temp": 25.0, "feels_like": 23.0, "humidity": 45},
            "weather": [{"description": "晴"}],
            "wind": {"speed": 3.5},
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            await service.get_weather("北京")

            # 验证请求参数
            call_args = mock_get.call_args
            assert call_args[1]["params"]["units"] == "metric"
            assert call_args[1]["params"]["lang"] == "zh_cn"

    @pytest.mark.asyncio
    async def test_get_weather_imperial_units(self):
        """测试使用英制单位"""
        service = WeatherService(api_key="test-key", units="imperial", lang="en")

        mock_response = {
            "main": {"temp": 77.0, "feels_like": 73.0, "humidity": 45},
            "weather": [{"description": "Clear"}],
            "wind": {"speed": 2.2},
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            await service.get_weather("London")

            call_args = mock_get.call_args
            assert call_args[1]["params"]["units"] == "imperial"
            assert call_args[1]["params"]["lang"] == "en"


class TestWeatherServiceCaching:
    """天气缓存测试"""

    @pytest.mark.asyncio
    async def test_cache_weather(self):
        """测试天气缓存"""
        service = WeatherService(api_key="test-key", cache_ttl=300)

        mock_response = {
            "main": {"temp": 25.0, "feels_like": 23.0, "humidity": 45},
            "weather": [{"description": "晴"}],
            "wind": {"speed": 3.5},
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            # 第一次调用
            result1 = await service.get_weather("北京")

            # 第二次调用（应该使用缓存）
            result2 = await service.get_weather("北京")

            # 验证只调用了一次 API
            assert mock_get.call_count == 1

            # 验证结果相同
            assert result1.temp == result2.temp

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """测试缓存过期"""
        service = WeatherService(api_key="test-key", cache_ttl=0)  # 立即过期

        mock_response = {
            "main": {"temp": 25.0, "feels_like": 23.0, "humidity": 45},
            "weather": [{"description": "晴"}],
            "wind": {"speed": 3.5},
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            # 第一次调用
            await service.get_weather("北京")

            # 第二次调用（缓存已过期）
            await service.get_weather("北京")

            # 验证调用了两次 API
            assert mock_get.call_count == 2
