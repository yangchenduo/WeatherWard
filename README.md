# WeatherWard - 智能衣服搭配助手

根据天气和衣橱推荐穿搭的 AI 助手，支持一次性推荐和交互式对话两种模式。

## 功能特点

- 🌤️ 实时天气查询（OpenWeatherMap，支持中文城市名）
- 👔 AI 图片分析衣服（款式/颜色/材质/季节/风格）
- 📁 结构化衣橱索引（增量导入，删除检测）
- 🔍 智能候选过滤（根据温度/天气/偏好自动筛选）
- ✨ AI 搭配推荐 + 合理性审查（防止逻辑冲突搭配）
- 💬 交互式对话模式（LangChain Agent 驱动）
- 🔄 多模型支持（MiMo、MiniMax）
- 🤖 MCP Server 集成（供 Hermes 等 Agent 调用）

> **注意**：`weatherward index`（图片分析）需要支持多模态（图片输入）的模型。DeepSeek 标准 API（`deepseek-chat`）为纯文本模型，不支持图片分析，仅可用于 `recommend`/`chat`（基于已建好的文本索引）。推荐使用 MiMo 作为默认模型。

## 安装

```bash
pip install -e ".[dev]"
```

## 配置

复制 `.env.example` 为 `.env`，填入 API Key：

```bash
cp .env.example .env
```

需要配置：
- `MIMO_API_KEY` - AI 模型 API Key
- `OPENWEATHER_API_KEY` - 天气服务 API Key
- `DEFAULT_CITY` - 默认城市（可选）

## 目录结构

```
WeatherWard/
├── my_clothes/          # 衣橱（存放所有已导入的衣服图片 + 索引）
├── import_clothes/      # 导入区（把新衣服图片放这里）
├── src/weatherward/
│   ├── cli.py           # CLI 命令
│   ├── config.py        # 配置管理
│   ├── agent/           # 交互式 Agent（LangChain）
│   ├── chains/          # AI 链（分析/推荐/审查/索引）
│   ├── models/          # 数据模型
│   ├── services/        # 服务（天气/衣橱/索引/LLM）
│   └── mcp/            # MCP Server
└── tests/
```

## 使用

### 1. 导入衣服

把衣服图片放到 `import_clothes/` 文件夹，然后执行：

```bash
weatherward index
```

这会：
- 自动将 `import_clothes/` 中的图片移入 `my_clothes/`
- AI 分析新增图片，生成结构化档案（款式/颜色/材质/保暖度等）
- 检测已删除的衣服并从索引中移除

再次执行时只处理新增内容，不会重复分析。

### 2. 一次性推荐

```bash
# 使用实时天气
weatherward recommend --city 大连

# 手动指定天气
weatherward recommend --city 北京 --weather 晴天 --preference 休闲
```

推荐流程：查天气 → 从索引过滤候选 → AI 搭配 → 合理性审查 → 输出。

### 3. 交互式对话

```bash
weatherward chat
```

启动对话模式，可以自然语言交流：
- "今天穿什么？"
- "天气怎么样？"
- "我衣橱里有什么？"
- "帮我搭配一套正式的"

Agent 会自动判断调用哪些工具（天气/衣橱/推荐）。

### 命令参数

```bash
# 查看帮助
weatherward --help
weatherward index --help
weatherward recommend --help
weatherward chat --help
```

默认路径：
- `--wardrobe` 默认 `./my_clothes`
- `--import-from` 默认 `./import_clothes`
- `--city` 未指定时，chat 模式使用 `.env` 中的 `DEFAULT_CITY`

## Hermes Agent 集成

WeatherWard 提供 MCP Server，可供 Hermes 等 Agent 框架调用。

### 方法一：标准 MCP 配置

在 Hermes 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "weatherward": {
      "command": "python",
      "args": ["-m", "weatherward.mcp.server"],
      "env": {
        "MIMO_API_KEY": "your-api-key",
        "OPENWEATHER_API_KEY": "your-weather-key"
      }
    }
  }
}
```

MCP Server 暴露两个工具：
- `get_outfit_recommendation` - 根据天气和衣橱推荐穿搭
- `get_weather` - 获取指定城市天气

### 方法二：让 Hermes 自己写 Skill

直接告诉 Hermes 项目路径，让它自行读取代码并生成调用方式：

```
请阅读 E:\work\WeatherWard 这个项目的代码，它是一个智能衣橱助手。
MCP Server 入口在 src/weatherward/mcp/server.py，
启动命令是 python -m weatherward.mcp.server。
请为这个工具创建一个 Skill，让你可以帮我推荐穿搭。
```

Hermes 会自动：
1. 读取项目结构和 MCP Server 代码
2. 理解暴露的工具（`get_outfit_recommendation`、`get_weather`）
3. 生成对应的 Skill 配置

这种方式更灵活，Hermes 能根据最新代码自适应。

## 开发

```bash
# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=weatherward
```
