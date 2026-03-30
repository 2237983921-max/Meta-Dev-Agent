# MemeRadar Live

一个基于 DEX Screener 官方实时数据的 meme 币跟踪平台。

## 当前能力

- 实时热门 meme 币榜单
- 新币 / Boost / 量能 / 动量信号流
- 价格、24h 涨跌、成交量、流动性、市场值
- 项目社媒入口追踪
- 观察列表和本地设置持久化

## 安装依赖

```bash
cd /Users/dutaorui/Desktop/codex/meme币
/Users/dutaorui/Desktop/codex/.venv/bin/python -m pip install -r requirements.txt
```

## 启动方式

```bash
cd /Users/dutaorui/Desktop/codex
/Users/dutaorui/Desktop/codex/.venv/bin/python -m uvicorn server:app --app-dir "/Users/dutaorui/Desktop/codex/meme币" --host 127.0.0.1 --port 8124
```

然后访问 `http://127.0.0.1:8124`。

## 公网部署

这个目录现在已经带了公开部署所需的文件：

- [Dockerfile](/Users/dutaorui/Desktop/codex/meme币/Dockerfile)
- [render.yaml](/Users/dutaorui/Desktop/codex/meme币/render.yaml)
- [railway.json](/Users/dutaorui/Desktop/codex/meme币/railway.json)

推荐流程：

1. 把 `meme币` 目录单独放到一个 GitHub 仓库。
2. 在 Render 或 Railway 新建项目并连接这个仓库。
3. 平台会自动生成一个公网 URL。
4. 如果你有自己的域名，再把它绑定到这个项目。

Render 启动命令已经配置好，直接识别 [render.yaml](/Users/dutaorui/Desktop/codex/meme币/render.yaml) 就可以。

## 数据源

- DEX Screener 官方 API
- 关键词种子搜索
- 最新 Boost / Token Profile / Community Takeover

## 说明

当前版本已经是真实数据版，不再依赖前端模拟数据。
如果你后面想继续接 X API、链上钱包监控或推送通知，可以在现有后端上继续扩展。
