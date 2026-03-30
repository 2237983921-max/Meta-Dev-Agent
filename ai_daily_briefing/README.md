# AI Daily Briefing

一个本地可跑的 AI 早报网页项目，目标是每天早上自动汇总：

- AI 圈的大新闻
- X 上 Gemini、Grok、Claude、ChatGPT 的动态变化
- 一页读完的中文摘要

## 现在已经有什么

- `generate_briefing.py`
  - 抓取新闻 RSS
  - 预置 4 条 X 观察线
  - 自动把英文内容优先翻成中文
  - 为每条新闻生成中文 AI 总结
  - 生成 `data/latest.json` 和历史归档
- `index.html` + `app.js` + `styles.css`
  - 展示中文头条、AI 总结、X 监控、源状态、提醒
  - 适合桌面和手机浏览
- `Open_AI_Daily_Briefing.command`
  - 双击即可刷新数据并打开网站

## 一键打开

直接双击这个文件：

- [Open_AI_Daily_Briefing.command](/Users/dutaorui/Desktop/codex/ai_daily_briefing/Open_AI_Daily_Briefing.command)

它会自动：

- 刷新当天数据
- 启动本地网页服务
- 自动打开浏览器

如果是第一次在 macOS 上打开 `.command` 文件，可能需要右键后选“打开”一次。

## 手动预览

先生成一份演示数据：

```bash
python3 /Users/dutaorui/Desktop/codex/ai_daily_briefing/generate_briefing.py --demo
```

再启动一个静态服务：

```bash
python3 -m http.server 8765 -d /Users/dutaorui/Desktop/codex/ai_daily_briefing
```

打开：

[`http://127.0.0.1:8765/index.html`](http://127.0.0.1:8765/index.html)

## 真实抓取

直接运行：

```bash
python3 /Users/dutaorui/Desktop/codex/ai_daily_briefing/generate_briefing.py
```

或者：

```bash
python3 /Users/dutaorui/Desktop/codex/ai_daily_briefing/launch_briefing.py
```

默认策略：

- 新闻：走 Google News RSS 聚合
- X：走 RSS 镜像

建议先配一个可访问的 X RSS 模板：

```bash
export X_RSS_TEMPLATE="https://nitter.net/{handle}/rss"
```

如果你有自己稳定的镜像，也可以直接换掉。

## 数据文件

- 最新日报：[data/latest.json](/Users/dutaorui/Desktop/codex/ai_daily_briefing/data/latest.json)
- 历史归档目录：[data/history](/Users/dutaorui/Desktop/codex/ai_daily_briefing/data/history)
- 翻译缓存：[translation_cache.json](/Users/dutaorui/Desktop/codex/ai_daily_briefing/data/translation_cache.json)

## 适合下一步扩展的方向

- 接入你自己的 LLM API，把摘要从模板版升级成更自然的中文晨报
- 给每条 X 线增加官方博客 / 发布日志作为兜底源
- 再包一层 API，就可以继续做成微信小程序前端
