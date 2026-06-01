"""天气服务 - 获取实时天气信息"""

import time
from dataclasses import dataclass, field

import httpx


@dataclass
class WeatherInfo:
    """天气信息"""

    city: str
    temp: float
    feels_like: float
    humidity: int
    weather: str
    wind_speed: float

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "city": self.city,
            "temp": self.temp,
            "feels_like": self.feels_like,
            "humidity": self.humidity,
            "weather": self.weather,
            "wind_speed": self.wind_speed,
        }

    def summary(self) -> str:
        """获取天气摘要"""
        return (
            f"{self.city}天气：{self.weather}，"
            f"温度 {self.temp}°C（体感 {self.feels_like}°C），"
            f"湿度 {self.humidity}%，风速 {self.wind_speed}m/s"
        )


class WeatherService:
    """天气服务"""

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(
        self,
        api_key: str,
        units: str = "metric",
        lang: str = "zh_cn",
        cache_ttl: int = 300,
    ):
        """
        初始化天气服务

        Args:
            api_key: OpenWeatherMap API Key
            units: 单位系统 (metric/imperial)
            lang: 语言
            cache_ttl: 缓存过期时间（秒）
        """
        self.api_key = api_key
        self.units = units
        self.lang = lang
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, WeatherInfo]] = {}

    async def get_weather(self, city: str) -> WeatherInfo:
        """
        获取指定城市的天气

        Args:
            city: 城市名称

        Returns:
            天气信息

        Raises:
            ValueError: 城市不存在
            httpx.HTTPStatusError: API 错误
            httpx.ConnectError: 网络错误
        """
        # 检查缓存
        if city in self._cache:
            cached_time, cached_info = self._cache[city]
            if time.time() - cached_time < self.cache_ttl:
                return cached_info

        # 调用 API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.BASE_URL,
                params={
                    "q": city,
                    "appid": self.api_key,
                    "units": self.units,
                    "lang": self.lang,
                },
            )

            if response.status_code == 404:
                raise ValueError(f"城市不存在: {city}")

            response.raise_for_status()

            data = response.json()

            weather_info = WeatherInfo(
                city=city,
                temp=data["main"]["temp"],
                feels_like=data["main"]["feels_like"],
                humidity=data["main"]["humidity"],
                weather=data["weather"][0]["description"],
                wind_speed=data["wind"]["speed"],
            )

            # 更新缓存
            self._cache[city] = (time.time(), weather_info)

            return weather_info
