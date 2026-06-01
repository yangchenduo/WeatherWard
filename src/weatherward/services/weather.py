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


CITY_ZH_TO_EN: dict[str, str] = {
    "北京": "Beijing",
    "上海": "Shanghai",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "大连": "Dalian",
    "天津": "Tianjin",
    "重庆": "Chongqing",
    "成都": "Chengdu",
    "杭州": "Hangzhou",
    "南京": "Nanjing",
    "武汉": "Wuhan",
    "西安": "Xi'an",
    "苏州": "Suzhou",
    "长沙": "Changsha",
    "沈阳": "Shenyang",
    "青岛": "Qingdao",
    "郑州": "Zhengzhou",
    "哈尔滨": "Harbin",
    "济南": "Jinan",
    "厦门": "Xiamen",
    "福州": "Fuzhou",
    "昆明": "Kunming",
    "合肥": "Hefei",
    "长春": "Changchun",
    "石家庄": "Shijiazhuang",
    "贵阳": "Guiyang",
    "南宁": "Nanning",
    "太原": "Taiyuan",
    "南昌": "Nanchang",
    "海口": "Haikou",
    "兰州": "Lanzhou",
    "乌鲁木齐": "Urumqi",
    "拉萨": "Lhasa",
    "呼和浩特": "Hohhot",
    "银川": "Yinchuan",
    "西宁": "Xining",
    "香港": "Hong Kong",
    "澳门": "Macau",
    "台北": "Taipei",
    "无锡": "Wuxi",
    "宁波": "Ningbo",
    "佛山": "Foshan",
    "东莞": "Dongguan",
    "珠海": "Zhuhai",
    "温州": "Wenzhou",
    "大同": "Datong",
    "洛阳": "Luoyang",
    "烟台": "Yantai",
    "威海": "Weihai",
    "三亚": "Sanya",
}


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

        query_city = CITY_ZH_TO_EN.get(city, city)

        # 调用 API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.BASE_URL,
                params={
                    "q": query_city,
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
