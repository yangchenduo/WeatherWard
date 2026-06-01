# WeatherWard - 智能衣服搭配助手

根据天气和衣橱推荐穿搭的 AI 助手，支持一次性推荐和交互式对话两种模式。

## 功能特点

- 🌤️ 实时天气查询
- 👔 AI 智能搭配推荐
- 📁 本地衣橱管理 - 实时天气查询（OpenWeatherMap，支持中文城市名）I 图片分析衣服（款式/颜色/材质/季节/风格）
- 🔄 多模型支持（MiMo、DeepSeek、MiniMax）
- 🤖 Hermes Agent 集成

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

## 开发

```bash
# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=weatherward
```
