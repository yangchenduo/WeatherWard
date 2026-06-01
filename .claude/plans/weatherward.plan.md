# Plan: WeatherWard - 智能衣服搭配助手

**复杂度**: Medium

## 需求概述

根据用户衣橱中的衣服图片、当前天气状况和用户偏好，使用 MiMo AI 模型进行智能衣服搭配推荐。项目为 Python CLI 工具，支持未来切换到其他模型（minimax/deepseek）。

## 技术栈

- **语言**: Python 3.10+
- **AI框架**: LangChain（统一模型接口，便于切换）
- **AI模型**: MiMo V2.5（支持图片理解）
- **天气API**: OpenWeatherMap（免费层）
- **图片处理**: Pillow (PIL)
- **HTTP客户端**: httpx
- **CLI框架**: click

## MiMo API 关键信息

- **端点**: `https://api.xiaomimimo.com/v1/chat/completions`
- **认证**: `api-key: $MIMO_API_KEY` 或 `Authorization: Bearer $MIMO_API_KEY`
- **图片格式**: Base64 编码，前缀 `data:{MIME_TYPE};base64,{BASE64_IMAGE}`
- **支持模型**: `mimo-v2.5`（视觉）, `mimo-v2-omni`（视觉）
- **API兼容**: OpenAI 格式，可直接使用 openai SDK

## 项目结构

```
WeatherWard/
├── .env.example              # 环境变量模板
├── .gitignore
├── README.md
├── requirements.txt          # 依赖清单
├── pyproject.toml           # 项目配置
├── src/
│   └── weatherward/
│       ├── __init__.py
│       ├── __main__.py      # CLI 入口
│       ├── cli.py           # CLI 命令定义
│       ├── config.py        # 配置管理（含模型切换）
│       ├── chains/
│       │   ├── __init__.py
│       │   ├── analyzer.py  # 衣服分析链
│       │   └── stylist.py   # 搭配推荐链
│       ├── services/
│       │   ├── __init__.py
│       │   ├── wardrobe.py  # 衣橱管理（读取图片）
│       │   ├── weather.py   # 天气服务
│       │   └── llm.py       # LLM 工厂（LangChain 模型创建）
│       ├── mcp/
│       │   ├── __init__.py
│       │   └── server.py    # MCP Server（供 Hermes 调用）
│       └── utils/
│           ├── __init__.py
│           └── image.py     # 图片处理工具
└── tests/
    ├── __init__.py
    ├── test_wardrobe.py
    ├── test_weather.py
    └── test_stylist.py
```

## 实施阶段

### Phase 1: 项目基础搭建
1. 初始化 Python 项目结构
2. 创建 requirements.txt 和 pyproject.toml
3. 配置 .env.example 和 .gitignore
4. 实现配置管理模块 (config.py)

### Phase 2: 衣橱服务
1. 实现 wardrobe.py - 扫描本地衣服图片文件夹
2. 实现 image.py - 图片转 Base64 编码
3. 支持常见图片格式（JPEG, PNG, WebP）
4. 实现衣服分类（上衣、裤子、外套等）

### Phase 3: 天气服务
1. 实现 weather.py - 调用 OpenWeatherMap API
2. 解析天气数据（温度、天气状况、湿度等）
3. 生成天气描述用于 AI 提示

### Phase 4: LangChain 集成
1. 实现 llm.py - LLM 工厂（根据配置创建不同模型）
2. 实现 analyzer.py - 衣衣服分析链（Chain）
3. 实现 stylist.py - 搭配推荐链（Chain）
4. 使用 PromptTemplate 管理提示词

### Phase 5: 搭配逻辑
1. 整合天气 + 衣服图片 + 用户偏好
2. 构建完整的搭配推荐流程
3. 解析 AI 返回的搭配建议

### Phase 6: CLI 界面
1. 实现 cli.py - 命令行参数解析
2. 支持参数：衣服目录、用户偏好、输出格式
3. 实现 __main__.py 入口
4. 美化终端输出（rich 库）

### Phase 7: Hermes Agent 集成
1. 实现 MCP Server (mcp/server.py)
2. 暴露 `get_outfit_recommendation` 工具
3. 配置 Hermes 连接此 MCP Server
4. 测试 Hermes 调用流程

### Phase 8: 测试与文档
1. 编写单元测试
2. 创建 README.md 使用说明
3. 添加使用示例（含 Hermes 集成说明）

## 核心代码设计

### 1. LLM 工厂 (services/llm.py)

```python
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatDeepSeek
from config import Settings

def create_llm(settings: Settings):
    """根据配置创建 LLM 实例"""
    if settings.model_provider == "mimo":
        return ChatOpenAI(
            model=settings.model_id,
            api_key=settings.api_key,
            base_url="https://api.xiaomimimo.com/v1",
            max_tokens=2048
        )
    elif settings.model_provider == "deepseek":
        return ChatDeepSeek(
            model="deepseek-chat",
            api_key=settings.api_key
        )
    elif settings.model_provider == "minimax":
        return ChatOpenAI(
            model="minimax-text-01",
            api_key=settings.api_key,
            base_url="https://api.minimax.chat/v1"
        )
    else:
        raise ValueError(f"Unknown provider: {settings.model_provider}")
```

### 2. 衣服分析链 (chains/analyzer.py)

```python
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

class ClothingAnalyzer:
    """分析衣服图片的 Chain"""

    def __init__(self, llm):
        self.llm = llm

    async def analyze(self, images_base64: list[str]) -> str:
        """分析多张衣服图片"""
        content = [{"type": "text", "text": "请描述这些衣服的款式、颜色、材质和适合的季节"}]
        for img_b64 in images_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })

        message = HumanMessage(content=content)
        response = await self.llm.ainvoke([message])
        return response.content
```

### 3. 搭配推荐链 (chains/stylist.py)

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class OutfitStylist:
    """搭配推荐 Chain"""

    PROMPT_TEMPLATE = """
    你是一个专业的服装搭配师。根据以下信息推荐今天的穿搭：

    ## 天气信息
    - 城市：{city}
    - 温度：{temp}°C（体感：{feels_like}°C）
    - 天气：{weather}
    - 湿度：{humidity}%
    - 风速：{wind_speed}m/s

    ## 可选衣服
    {clothing_list}

    ## 用户偏好
    {preference}

    请推荐一套完整的穿搭，包括：
    1. 上衣
    2. 下装
    3. 外套（如需要）
    4. 鞋子建议
    5. 搭配理由（结合天气）
    6. 搭配小贴士
    """

    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template(self.PROMPT_TEMPLATE)
        self.chain = self.prompt | self.llm | StrOutputParser()

    async def recommend(self, weather: dict, clothing_list: str, preference: str) -> str:
        """生成搭配推荐"""
        return await self.chain.ainvoke({
            "city": weather["city"],
            "temp": weather["temp"],
            "feels_like": weather["feels_like"],
            "weather": weather["weather"],
            "humidity": weather["humidity"],
            "wind_speed": weather["wind_speed"],
            "clothing_list": clothing_list,
            "preference": preference or "无特殊偏好"
        })
```

### 4. 天气服务 (services/weather.py)

```python
import httpx

class WeatherService:
    """OpenWeatherMap 天气服务"""

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_weather(self, city: str) -> dict:
        """获取当前天气"""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params={
                "q": city,
                "appid": self.api_key,
                "units": "metric",
                "lang": "zh_cn"
            })
            data = response.json()
            return {
                "city": city,
                "temp": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "weather": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"]
            }
```

### 5. MCP Server (mcp/server.py) - 供 Hermes 调用

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import json

app = Server("weatherward")

@app.tool()
async def get_outfit_recommendation(
    wardrobe_path: str,
    city: str,
    preference: str = ""
) -> str:
    """
    根据天气和衣橱推荐穿搭

    Args:
        wardrobe_path: 衣服图片文件夹路径
        city: 城市名称
        preference: 搭配偏好（休闲/正式/运动等）
    """
    # 复用核心逻辑
    from weatherward.services import wardrobe, weather, llm
    from weatherward.chains import stylist

    # 1. 读取衣服图片
    clothes = await wardrobe.scan(wardrobe_path)

    # 2. 获取天气
    weather_info = await weather.get_weather(city)

    # 3. AI 推荐
    recommendation = await stylist.recommend(weather_info, clothes, preference)

    return json.dumps({
        "weather": weather_info,
        "recommendation": recommendation
    }, ensure_ascii=False)

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read, write):
            await app.run(read, write, app.create_initialization_options())

    asyncio.run(main())
```

### 6. CLI 入口 (cli.py)

```python
import click
import asyncio
from pathlib import Path

@click.command()
@click.option("--wardrobe", "-w", required=True, type=click.Path(exists=True), help="衣服图片文件夹路径")
@click.option("--city", "-c", required=True, help="城市名称")
@click.option("--preference", "-p", default="", help="搭配偏好（如：休闲、正式、运动）")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="输出格式")
def main(wardrobe: str, city: str, preference: str, output: str):
    """WeatherWard - 智能衣服搭配助手"""
    asyncio.run(_run(wardrobe, city, preference, output))

async def _run(wardrobe: str, city: str, preference: str, output: str):
    # 1. 读取衣服图片
    # 2. 获取天气
    # 3. 调用 AI 推荐
    # 4. 输出结果
    pass
```

## Hermes Agent 集成

### 方式一：CLI 直接调用（最简单）

Hermes 可以直接执行 CLI 命令：

```bash
# 在 Hermes 中直接调用
weatherward --wardrobe /path/to/clothes --city "北京" --preference "休闲" --output json
```

### 方式二：MCP Server（推荐）

1. 启动 MCP Server：
```bash
python -m weatherward.mcp.server
```

2. 在 Hermes 中配置 MCP：
```yaml
# ~/.hermes/config.yaml 或通过 hermes setup
mcp:
  servers:
    weatherward:
      command: "python"
      args: ["-m", "weatherward.mcp.server"]
      env:
        MIMO_API_KEY: "${MIMO_API_KEY}"
        OPENWEATHER_API_KEY: "${OPENWEATHER_API_KEY}"
```

3. Hermes 中直接使用：
```
> 帮我看看今天北京穿什么衣服合适，我的衣服在 /home/user/clothes 文件夹
```

Hermes 会自动调用 `get_outfit_recommendation` 工具。

## 用户使用流程

```bash
# 1. 设置环境变量
export MIMO_API_KEY="your-api-key"
export OPENWEATHER_API_KEY="your-weather-key"

# 2. 运行搭配推荐
weatherward --wardrobe ./my_clothes --city "北京" --preference "休闲"

# 3. 输出示例
# 🌤️ 今日北京天气：晴，25°C，湿度 45%
#
# 👔 推荐搭配：
# - 上衣：白色棉质T恤（适合当前温度）
# - 下装：蓝色牛仔裤（休闲风格）
# - 外套：薄款开衫（早晚备用）
#
# 💡 搭配小贴士：今天温度适中，建议...
```

## 模型切换设计（基于 LangChain）

使用 LangChain 的统一接口，切换模型只需改配置：

```python
# config.yaml
model:
  provider: "mimo"  # 可选: mimo, minimax, deepseek
  api_key: "${MIMO_API_KEY}"
  model_id: "mimo-v2.5"
```

### 切换示例

```python
# 使用 MiMo
llm = ChatOpenAI(model="mimo-v2.5", base_url="https://api.xiaomimimo.com/v1", api_key=key)

# 切换到 DeepSeek（改一行）
llm = ChatDeepSeek(model="deepseek-chat", api_key=key)

# 切换到 MiniMax（改一行）
llm = ChatOpenAI(model="minimax-text-01", base_url="https://api.minimax.chat/v1", api_key=key)
```

### LangChain 优势

| 特性 | 直接 API | LangChain |
|------|----------|-----------|
| 换模型成本 | 2-4 小时/个 | 30 分钟/个 |
| 提示词管理 | 手动拼接 | PromptTemplate |
| 链式调用 | 手动实现 | LCEL (Chain) |
| 输出解析 | 手动解析 | OutputParser |
| 生态集成 | 无 | 丰富（工具、记忆等） |

## 风险与缓解

| 风险 | 可能性 | 缓解措施 |
|------|--------|----------|
| MiMo API 限流 | 中 | 添加重试机制和请求间隔 |
| 图片过大导致超时 | 低 | 压缩图片至合理大小 |
| 天气 API 不稳定 | 中 | 缓存天气数据，添加降级方案 |
| AI 返回格式不一致 | 中 | 使用结构化提示词，添加输出解析 |

## 环境变量

```env
# MiMo API
MIMO_API_KEY=sk-xxxxx

# OpenWeatherMap
OPENWEATHER_API_KEY=xxxxx

# 可选：默认城市
DEFAULT_CITY=Beijing
```

## 验证方式

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 运行 CLI
weatherward --wardrobe ./test_clothes --city "上海"
```

## 依赖清单 (requirements.txt)

```
# LangChain 核心
langchain>=0.3.0
langchain-core>=0.3.0
langchain-openai>=0.2.0
langchain-community>=0.3.0

# MiMo 支持（通过 OpenAI 兼容）
openai>=1.50.0

# MCP Server（供 Hermes 调用）
mcp>=1.0.0

# HTTP 客户端
httpx>=0.27.0

# 图片处理
Pillow>=10.0.0

# CLI
click>=8.1.0
rich>=13.0.0

# 配置管理
python-dotenv>=1.0.0
pyyaml>=6.0
```

## 预计工时

- Phase 1-2: 2-3 小时
- Phase 3-4: 3-4 小时
- Phase 5-6: 2-3 小时
- Phase 7 (Hermes): 1-2 小时
- Phase 8 (测试): 1-2 小时
- **总计**: 10-14 小时

---

**状态**: 等待用户确认
