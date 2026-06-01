# WeatherWard - 智能衣服搭配助手

根据天气和衣橱推荐穿搭的 CLI 工具。

## 功能特点

- 🌤️ 实时天气查询
- 👔 AI 智能搭配推荐
- 📁 本地衣橱管理
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

## 使用

```bash
weatherward --wardrobe ./my_clothes --city "北京" --preference "休闲"
```

## 开发

```bash
# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=weatherward
```
