from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


TZ = dt.timezone(dt.timedelta(hours=8))
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
HISTORY_DIR = DATA_DIR / "history"
USER_AGENT = "ai-daily-briefing/1.0"
NEWS_HOURS = int(os.getenv("AI_BRIEFING_NEWS_HOURS", "48"))
X_HOURS = int(os.getenv("AI_BRIEFING_X_HOURS", "72"))
TRANSLATE_ENGLISH = os.getenv("AI_BRIEFING_TRANSLATE_ENGLISH", "1") == "1"
TRANSLATION_CACHE_PATH = DATA_DIR / "translation_cache.json"


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    kind: str
    target_name: str = ""
    handle: str = ""
    focus: str = ""


@dataclass
class FeedItem:
    title: str
    link: str
    description: str
    published_at: dt.datetime
    source_name: str
    publication: str
    kind: str
    target_name: str = ""
    handle: str = ""


WATCH_TARGETS = [
    {
        "name": "Gemini",
        "handles": ["GeminiApp", "GoogleDeepMind"],
        "focus": "模型能力、工作流入口和开发者生态",
    },
    {
        "name": "Grok",
        "handles": ["grok", "xAI"],
        "focus": "X 集成、实时搜索、多模态和 API 节奏",
    },
    {
        "name": "Claude",
        "handles": ["AnthropicAI"],
        "focus": "推理能力、Artifacts、团队协作和 API 产品化",
    },
    {
        "name": "ChatGPT",
        "handles": ["OpenAI"],
        "focus": "ChatGPT 功能更新、Agents、语音和工作流落地",
    },
]


THEME_RULES = {
    "模型发布": [
        "model",
        "reasoning",
        "multimodal",
        "weights",
        "gpt",
        "gemini",
        "claude",
        "grok",
        "release",
        "launch",
        "ship",
        "模型",
        "发布",
    ],
    "产品更新": [
        "feature",
        "update",
        "rollout",
        "app",
        "voice",
        "agents",
        "agent",
        "workspace",
        "api",
        "插件",
        "更新",
        "上线",
    ],
    "资本与合作": [
        "funding",
        "fundraise",
        "raise",
        "invest",
        "partnership",
        "partner",
        "acquire",
        "acquisition",
        "deal",
        "合作",
        "融资",
    ],
    "监管与安全": [
        "policy",
        "regulation",
        "lawsuit",
        "compliance",
        "safety",
        "copyright",
        "government",
        "监管",
        "安全",
    ],
    "芯片与算力": [
        "nvidia",
        "gpu",
        "chip",
        "chips",
        "semiconductor",
        "inference",
        "datacenter",
        "算力",
        "芯片",
    ],
}


BRAND_RULES = {
    "Gemini": ["gemini", "deepmind", "google ai", "google"],
    "Grok": ["grok", "xai", "x ai"],
    "Claude": ["claude", "anthropic"],
    "ChatGPT": ["chatgpt", "openai", "gpt-5", "gpt 5", "sora"],
    "Nvidia": ["nvidia", "blackwell", "cuda"],
}


TRUSTED_PUBLICATION_HINTS = {
    "reuters",
    "bloomberg",
    "the information",
    "techcrunch",
    "the verge",
    "ars technica",
    "wired",
    "mit technology review",
    "financial times",
    "wall street journal",
    "cnbc",
    "venturebeat",
    "engadget",
    "semafor",
    "404 media",
    "fortune",
    "axios",
    "deepmind",
    "openai",
    "anthropic",
}


NOISY_PUBLICATION_HINTS = {
    "motley fool",
    "yahoo finance",
    "business wire",
    "globenewswire",
    "pr newswire",
    "seeking alpha",
    "investorplace",
    "zacks",
    "benzinga",
}


HIGH_SIGNAL_HINTS = {
    "launch",
    "release",
    "rollout",
    "agent",
    "agents",
    "reasoning",
    "model",
    "api",
    "voice",
    "search",
    "workspace",
    "multimodal",
    "partnership",
    "partner",
    "funding",
    "investment",
    "acquire",
    "regulation",
    "safety",
    "copilot",
    "operator",
    "chatgpt",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "grok",
    "xai",
    "nvidia",
}


LOW_SIGNAL_HINTS = {
    "stocks",
    "stock",
    "portfolio",
    "investor",
    "investors",
    "billionaire",
    "millionaire",
    "sell-off",
    "buy now",
    "teach teachers",
    "classroom",
    "school district",
    "essay",
    "lottery",
    "odds",
}


EXACT_TRANSLATIONS = {
    "OpenAI pushes a more practical agent workflow into ChatGPT": "OpenAI 正在把更实用的 Agent 工作流推入 ChatGPT",
    "Google expands Gemini into search and productivity surfaces": "Google 正在把 Gemini 推进到搜索和生产力入口",
    "Anthropic emphasizes safer enterprise use cases for Claude": "Anthropic 强调 Claude 在企业场景中的安全落地能力",
    "xAI hints at faster Grok rollouts tied to the X platform": "xAI 暗示会加快与 X 平台深度绑定的 Grok 推送节奏",
    "Nvidia supply and inference pricing stay at the center of the AI buildout": "NVIDIA 的供给和推理成本仍是 AI 建设节奏的关键变量",
    "Gemini signals more product integrations across work and search": "Gemini 正在把更多产品集成推向办公与搜索入口",
    "Google DeepMind previews another capability milestone for Gemini": "Google DeepMind 预告 Gemini 的又一项能力升级",
    "Grok continues to lean into real-time answers on X": "Grok 继续强化在 X 上的实时回答能力",
    "Anthropic highlights more team workflows and safer defaults for Claude": "Anthropic 强调 Claude 的团队工作流和更安全的默认设置",
    "OpenAI teases another round of ChatGPT usability improvements": "OpenAI 预告新一轮 ChatGPT 可用性改进",
}


PHRASE_TRANSLATIONS = [
    ("OpenAI", "OpenAI"),
    ("Anthropic", "Anthropic"),
    ("Google DeepMind", "Google DeepMind"),
    ("Google", "Google"),
    ("Gemini", "Gemini"),
    ("Grok", "Grok"),
    ("Claude", "Claude"),
    ("ChatGPT", "ChatGPT"),
    ("NVIDIA", "NVIDIA"),
    ("Nvidia", "NVIDIA"),
    ("AI", "AI"),
    ("launch", "发布"),
    ("launches", "发布"),
    ("launched", "已发布"),
    ("release", "发布"),
    ("released", "已发布"),
    ("update", "更新"),
    ("updates", "更新"),
    ("feature", "功能"),
    ("features", "功能"),
    ("build", "打造"),
    ("builds", "打造"),
    ("safer", "更安全的"),
    ("teens", "青少年"),
    ("developers", "开发者"),
    ("workflow", "工作流"),
    ("workflows", "工作流"),
    ("agent", "Agent"),
    ("agents", "Agents"),
    ("voice", "语音"),
    ("video", "视频"),
    ("search", "搜索"),
    ("business tools", "企业工具"),
    ("productivity", "生产力"),
    ("real-time", "实时"),
    ("partnership", "合作"),
    ("partnerships", "合作"),
    ("approval", "审批"),
    ("approvals", "审批"),
]


def google_news_rss(query: str) -> str:
    encoded = quote_plus(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"


NEWS_SOURCES = [
    FeedSource(
        name="OpenAI / News",
        url="https://openai.com/news/rss.xml",
        kind="news",
    ),
    FeedSource(
        name="Google DeepMind / Blog",
        url="https://deepmind.google/blog/rss.xml",
        kind="news",
    ),
    FeedSource(
        name="Google News / AI headlines",
        url=google_news_rss(
            '(OpenAI OR ChatGPT OR Anthropic OR Claude OR "Google Gemini" OR Grok OR xAI OR "AI agent" OR "AI model") -stocks -portfolio -investors when:2d'
        ),
        kind="news",
    ),
    FeedSource(
        name="Google News / Big model companies",
        url=google_news_rss(
            '(OpenAI OR ChatGPT OR Anthropic OR Claude OR Gemini OR Grok OR xAI OR "model release" OR "API update") -stocks -ETF when:2d'
        ),
        kind="news",
    ),
    FeedSource(
        name="Google News / AI infra and agents",
        url=google_news_rss(
            '("AI agent" OR "reasoning model" OR inference OR Nvidia OR GPU OR datacenter) -stocks -portfolio when:2d'
        ),
        kind="news",
    ),
]


def x_rss_template() -> str:
    return os.getenv("X_RSS_TEMPLATE", "https://nitter.net/{handle}/rss")


def build_x_sources() -> list[FeedSource]:
    template = x_rss_template()
    sources: list[FeedSource] = []
    for target in WATCH_TARGETS:
        for handle in target["handles"]:
            sources.append(
                FeedSource(
                    name=f"X / @{handle}",
                    url=template.format(handle=handle),
                    kind="x",
                    target_name=target["name"],
                    handle=handle,
                    focus=target["focus"],
                )
            )
    return sources


def fetch_text(
    url: str,
    accept: str = "application/rss+xml, application/xml, text/xml, */*",
) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
        },
    )
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_translation_cache() -> dict[str, str]:
    if not TRANSLATION_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(TRANSLATION_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_translation_cache(cache: dict[str, str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TRANSLATION_CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def looks_translatable(text: str) -> bool:
    if not text:
        return False
    ascii_letters = sum(char.isascii() and char.isalpha() for char in text)
    cjk_letters = sum("\u4e00" <= char <= "\u9fff" for char in text)
    return ascii_letters > cjk_letters


def fallback_translate_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped in EXACT_TRANSLATIONS:
        return EXACT_TRANSLATIONS[stripped]

    translated = stripped
    for source, target in PHRASE_TRANSLATIONS:
        translated = translated.replace(source, target)
    return translated


def translate_text(text: str, cache: dict[str, str], allow_remote: bool = True) -> str:
    stripped = clean_text(text)
    if not stripped:
        return ""
    if not TRANSLATE_ENGLISH or not looks_translatable(stripped):
        return stripped

    fallback_translation = fallback_translate_text(stripped)
    if stripped in cache and (not allow_remote or cache[stripped] != fallback_translation):
        return cache[stripped]

    translated = fallback_translation
    if allow_remote:
        try:
            params = urlencode(
                {
                    "client": "gtx",
                    "sl": "auto",
                    "tl": "zh-CN",
                    "dt": "t",
                    "q": stripped,
                }
            )
            response_text = fetch_text(
                f"https://translate.googleapis.com/translate_a/single?{params}",
                accept="application/json, text/plain, */*",
            )
            payload = json.loads(response_text)
            translated = "".join(part[0] for part in payload[0] if part and part[0]).strip() or translated
        except Exception:
            pass

    cache[stripped] = translated or stripped
    return cache[stripped]


def parse_datetime(value: str | None) -> dt.datetime:
    if not value:
        return dt.datetime.now(dt.timezone.utc)
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except (TypeError, ValueError):
        pass
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except ValueError:
        return dt.datetime.now(dt.timezone.utc)


def split_title_and_publication(title: str, fallback: str) -> tuple[str, str]:
    if " - " not in title:
        return title.strip(), fallback
    body, tail = title.rsplit(" - ", 1)
    if 1 < len(tail) < 60:
        return body.strip(), tail.strip()
    return title.strip(), fallback


def parse_rss(xml_text: str, source: FeedSource) -> list[FeedItem]:
    root = ET.fromstring(xml_text)
    entries = root.findall(".//item")
    is_atom = False
    if not entries:
        entries = root.findall(".//{*}entry")
        is_atom = True

    items: list[FeedItem] = []
    for entry in entries:
        title_text = clean_text(entry.findtext("title") or entry.findtext("{*}title") or "")
        if not title_text:
            continue

        publication = source.name
        title = title_text
        if source.kind == "news":
            title, publication = split_title_and_publication(title_text, source.name)

        if is_atom:
            link_node = entry.find("{*}link")
            link = ""
            if link_node is not None:
                link = link_node.attrib.get("href", "") or (link_node.text or "")
        else:
            link = clean_text(entry.findtext("link") or "")

        description = clean_text(
            entry.findtext("description")
            or entry.findtext("{*}summary")
            or entry.findtext("{*}content")
            or ""
        )
        published_at = parse_datetime(
            entry.findtext("pubDate")
            or entry.findtext("{*}published")
            or entry.findtext("{*}updated")
        )

        items.append(
            FeedItem(
                title=title,
                link=link,
                description=description,
                published_at=published_at,
                source_name=source.name,
                publication=publication,
                kind=source.kind,
                target_name=source.target_name,
                handle=source.handle,
            )
        )
    return items


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())


def dedupe_items(items: Iterable[FeedItem]) -> list[FeedItem]:
    seen: set[str] = set()
    ordered: list[FeedItem] = []
    for item in sorted(items, key=lambda value: value.published_at, reverse=True):
        key = normalize_title(item.title)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def is_recent(item: FeedItem, max_hours: int) -> bool:
    now = dt.datetime.now(dt.timezone.utc)
    delta = now - item.published_at.astimezone(dt.timezone.utc)
    return delta <= dt.timedelta(hours=max_hours)


def classify_theme(text: str) -> str:
    lowered = text.lower()
    for theme, keywords in THEME_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            return theme
    return "行业观察"


def classify_brand(text: str) -> str:
    lowered = text.lower()
    for brand, keywords in BRAND_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            return brand
    return "AI 行业"


def shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def format_ts(value: dt.datetime) -> str:
    local = value.astimezone(TZ)
    return local.strftime("%Y-%m-%d %H:%M")


def normalize_brief(text: str, fallback: str, limit: int = 88) -> str:
    base = clean_text(text) or clean_text(fallback)
    return shorten(base, limit)


def make_ai_summary(
    *,
    title_zh: str,
    detail_zh: str,
    theme: str,
    brand: str,
) -> str:
    focus_map = {
        "模型发布": "更值得盯能力边界、开放范围和会不会带动下一轮模型对比。",
        "产品更新": "更值得盯开放人群、入口位置和是否已经进入真实工作流。",
        "资本与合作": "更值得盯接下来几周的资源投入和商业落地速度。",
        "监管与安全": "更值得盯它会不会影响后续发布节奏、合规和训练数据策略。",
        "芯片与算力": "更值得盯成本、供给和推理价格会不会继续变化。",
        "行业观察": "更适合拿来判断市场焦点是不是已经在切换。",
    }
    lead = normalize_brief(detail_zh, title_zh, limit=46).rstrip("。.!！?？")
    subject = brand if brand != "AI 行业" else "这条消息"
    return f"{lead}。AI 判断：{subject} 这条动态属于“{theme}”信号，{focus_map.get(theme, focus_map['行业观察'])}"


def make_source_brief(*, title_zh: str, detail_zh: str, theme: str) -> str:
    detail = normalize_brief(detail_zh, title_zh, limit=72)
    if detail and normalize_title(detail) != normalize_title(title_zh):
        return detail

    fallback_map = {
        "模型发布": "这条消息大概率会影响接下来一周的模型讨论热度。",
        "产品更新": "这条消息更偏落地节奏，适合继续看开放范围和入口变化。",
        "资本与合作": "这条消息更偏资源投入与合作信号，值得看后续动作。",
        "监管与安全": "这条消息更偏合规和安全风向，对发布节奏有影响。",
        "芯片与算力": "这条消息更偏底层算力和成本变化，适合继续跟进。",
        "行业观察": "这条消息能帮助你判断当前市场的关注点。",
    }
    return fallback_map.get(theme, fallback_map["行业观察"])


def build_takeaway(item: FeedItem) -> str:
    theme = classify_theme(f"{item.title} {item.description}")
    detail = shorten(item.description, 84)
    if theme == "模型发布":
        tail = "先看能力边界、开放范围和是否会引发下一轮模型对比。"
    elif theme == "产品更新":
        tail = "这类信号更接近落地，重点看是否已经开放给普通用户或开发者。"
    elif theme == "资本与合作":
        tail = "资金和联盟动作往往意味着接下来几周会有更激进的产品推进。"
    elif theme == "监管与安全":
        tail = "它会直接影响发布节奏、训练数据和商业化路径。"
    elif theme == "芯片与算力":
        tail = "算力侧变化通常会传导到价格、交付周期和模型上线节奏。"
    else:
        tail = "这条更适合拿来判断行业关注点有没有发生转向。"

    if detail and normalize_title(detail) != normalize_title(item.title):
        return f"{detail} {tail}"
    return tail


def score_news_item(item: FeedItem) -> int:
    if item.kind != "news":
        return 0

    text = f"{item.title} {item.description}".lower()
    publication = item.publication.lower()
    theme = classify_theme(text)
    brand = classify_brand(text)

    score = 0
    if brand != "AI 行业":
        score += 4

    score += {
        "模型发布": 4,
        "产品更新": 4,
        "芯片与算力": 3,
        "资本与合作": 2,
        "监管与安全": 3,
        "行业观察": 1,
    }.get(theme, 0)

    if any(hint in text for hint in HIGH_SIGNAL_HINTS):
        score += 2
    if any(hint in publication for hint in TRUSTED_PUBLICATION_HINTS):
        score += 3
    if any(hint in publication for hint in NOISY_PUBLICATION_HINTS):
        score -= 4
    if any(hint in text for hint in LOW_SIGNAL_HINTS):
        score -= 5
    if len(item.title.split()) < 6:
        score -= 1

    return score


def select_top_news(items: list[FeedItem], limit: int = 10) -> list[FeedItem]:
    ranked = [(score_news_item(item), item) for item in dedupe_items(items)]
    ranked.sort(key=lambda row: (row[0], row[1].published_at), reverse=True)
    thresholds = [5, 3]

    for threshold in thresholds:
        brand_counts: Counter[str] = Counter()
        publication_counts: Counter[str] = Counter()
        selected: list[FeedItem] = []

        for score, item in ranked:
            if score < threshold:
                continue

            brand = classify_brand(f"{item.title} {item.description}")
            if brand_counts[brand] >= 3:
                continue
            if publication_counts[item.publication] >= 2:
                continue

            selected.append(item)
            brand_counts[brand] += 1
            publication_counts[item.publication] += 1

            if len(selected) >= limit:
                return selected

        if len(selected) >= min(limit, 6):
            return selected

    return [item for _, item in ranked[:limit]]


def trend_label(items: list[FeedItem]) -> str:
    joined = " ".join(item.title.lower() for item in items)
    if any(token in joined for token in ["launch", "release", "ship", "上线", "发布"]):
        return "发布节奏偏快"
    if any(token in joined for token in ["partner", "合作", "integrat", "workspace"]):
        return "生态动作增多"
    if any(token in joined for token in ["voice", "agent", "api", "feature", "update"]):
        return "产品细节在加密"
    return "持续保持热度"


def build_watch_section(
    target: dict[str, object],
    items: list[FeedItem],
    translation_cache: dict[str, str],
    allow_remote_translation: bool = True,
) -> dict[str, object]:
    if not items:
        return {
            "name": target["name"],
            "focus": target["focus"],
            "trend": "等待最新信号",
            "status_line": "今天没有抓到新的 X 动态，先检查镜像地址或账号可访问性。",
            "updated_at": None,
            "handles": target["handles"],
            "profile_url": f"https://x.com/{target['handles'][0]}",
            "highlights": [],
        }

    themes = Counter(classify_theme(f"{item.title} {item.description}") for item in items)
    dominant_theme = themes.most_common(1)[0][0]
    lead = items[0]
    status_line = (
        f"最近 {len(items)} 条动态主要落在“{dominant_theme}”，更值得盯 {target['focus']}。"
    )
    highlights = []
    for item in items[:3]:
        theme = classify_theme(f"{item.title} {item.description}")
        title_zh = shorten(
            translate_text(item.title, translation_cache, allow_remote_translation) or item.title,
            92,
        )
        detail_zh = item.description if item.description and not looks_translatable(item.description) else ""
        summary_zh = shorten(
            make_source_brief(
                title_zh=title_zh,
                detail_zh=detail_zh,
                theme=theme,
            ),
            100,
        )
        highlights.append(
            {
                "title": title_zh,
                "original_title": shorten(item.title, 92) if title_zh != item.title else "",
                "url": item.link,
                "published_at": format_ts(item.published_at),
                "handle": f"@{item.handle}" if item.handle else "",
                "summary": summary_zh,
            }
        )
    return {
        "name": target["name"],
        "focus": target["focus"],
        "trend": trend_label(items),
        "status_line": status_line,
        "updated_at": format_ts(lead.published_at),
        "handles": target["handles"],
        "profile_url": f"https://x.com/{lead.handle or target['handles'][0]}",
        "highlights": highlights,
    }


def build_overview(
    news_items: list[FeedItem],
    watch_sections: list[dict[str, object]],
    source_health: list[dict[str, str]],
    translation_cache: dict[str, str],
    allow_remote_translation: bool = True,
) -> dict[str, object]:
    brand_counts = Counter(classify_brand(f"{item.title} {item.description} {item.publication}") for item in news_items)
    theme_counts = Counter(classify_theme(f"{item.title} {item.description}") for item in news_items)
    for section in watch_sections:
        if section["highlights"]:
            brand_counts[section["name"]] += len(section["highlights"])

    lead_brands = [name for name, _ in brand_counts.most_common(3) if name != "AI 行业"] or ["AI 圈"]
    lead_themes = [name for name, _ in theme_counts.most_common(3)] or ["产品更新", "模型发布", "行业观察"]
    healthy_sources = sum(1 for item in source_health if item["status"] == "ok")
    headline = f"{dt.datetime.now(TZ):%m月%d日} AI 早报：{'、'.join(lead_brands[:3])}值得先看"

    if news_items:
        first = translate_text(news_items[0].title, translation_cache, allow_remote_translation) or news_items[0].title
        summary = (
            f"今天主线围绕 {' / '.join(lead_themes[:3])} 展开。"
            f"行业新闻抓到 {len(news_items)} 条，X 追踪抓到 {sum(len(section['highlights']) for section in watch_sections)} 条；"
            f"如果只看 3 分钟，先盯住“{shorten(first, 42)}”。"
        )
    else:
        summary = "今天还没有抓到足够的新内容，优先检查新闻源和 X 镜像配置。"

    active_watch = [section["name"] for section in watch_sections if section["highlights"]][:3]
    quick_cards = [
        {
            "title": "今天先看什么",
            "body": "；".join(
                shorten(
                    translate_text(item.title, translation_cache, allow_remote_translation) or item.title,
                    28,
                )
                for item in news_items[:3]
            )
            or "先检查抓取源，当前缺少有效新闻。",
        },
        {
            "title": "圈内风向",
            "body": f"今天更偏 {'、'.join(lead_themes[:3])}，目前 {healthy_sources}/{len(source_health)} 个源刷新正常。",
        },
        {
            "title": "X 上谁更活跃",
            "body": "、".join(active_watch) + " 这几条线更新更密。" if active_watch else "今天 X 侧还没抓到足够信号。",
        },
    ]
    return {
        "headline": headline,
        "summary": summary,
        "watchwords": lead_themes[:4],
        "quick_cards": quick_cards,
    }


def serialize_news(
    items: list[FeedItem],
    translation_cache: dict[str, str],
    allow_remote_translation: bool = True,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in items:
        theme = classify_theme(f"{item.title} {item.description}")
        brand = classify_brand(f"{item.title} {item.description} {item.publication}")
        title_zh = translate_text(item.title, translation_cache, allow_remote_translation) or item.title
        detail_zh = item.description if item.description and not looks_translatable(item.description) else ""
        source_brief = make_source_brief(title_zh=title_zh, detail_zh=detail_zh, theme=theme)
        rows.append(
            {
                "title": title_zh,
                "original_title": item.title if title_zh != item.title else "",
                "url": item.link,
                "published_at": format_ts(item.published_at),
                "source": item.publication,
                "theme": theme,
                "brand": brand,
                "source_brief": source_brief,
                "ai_summary": make_ai_summary(
                    title_zh=title_zh,
                    detail_zh=source_brief,
                    theme=theme,
                    brand=brand,
                ),
            }
        )
    return rows


def generate_live_payload() -> dict[str, object]:
    fetched_news: list[FeedItem] = []
    fetched_watch: defaultdict[str, list[FeedItem]] = defaultdict(list)
    source_health: list[dict[str, str]] = []
    translation_cache = load_translation_cache()

    for source in NEWS_SOURCES + build_x_sources():
        max_hours = NEWS_HOURS if source.kind == "news" else X_HOURS
        try:
            xml_text = fetch_text(source.url)
            items = [item for item in parse_rss(xml_text, source) if is_recent(item, max_hours)]
            items = dedupe_items(items)

            if source.kind == "news":
                fetched_news.extend(items[:8])
            else:
                fetched_watch[source.target_name].extend(items[:5])

            source_health.append(
                {
                    "name": source.name,
                    "kind": source.kind,
                    "status": "ok" if items else "stale",
                    "message": f"{len(items)} 条近 {max_hours} 小时内容" if items else "源可用，但最近没有新内容",
                }
            )
        except Exception as exc:
            source_health.append(
                {
                    "name": source.name,
                    "kind": source.kind,
                    "status": "error",
                    "message": shorten(str(exc), 80) or "抓取失败",
                }
            )

    news_items = select_top_news(fetched_news, limit=10)
    watch_sections = []
    for target in WATCH_TARGETS:
        items = dedupe_items(fetched_watch[target["name"]])[:4]
        watch_sections.append(
            build_watch_section(
                target,
                items,
                translation_cache,
                allow_remote_translation=True,
            )
        )

    save_translation_cache(translation_cache)

    payload = {
        "generated_at": dt.datetime.now(TZ).isoformat(),
        "generated_label": dt.datetime.now(TZ).strftime("%Y年%m月%d日 %H:%M"),
        "timezone": "Asia/Shanghai",
        "mode": "live",
        "overview": build_overview(
            news_items,
            watch_sections,
            source_health,
            translation_cache,
            allow_remote_translation=True,
        ),
        "stats": {
            "news_count": len(news_items),
            "x_count": sum(len(section["highlights"]) for section in watch_sections),
            "healthy_sources": sum(1 for item in source_health if item["status"] == "ok"),
            "total_sources": len(source_health),
        },
        "top_news": serialize_news(
            news_items,
            translation_cache,
            allow_remote_translation=True,
        ),
        "x_watchlist": watch_sections,
        "source_health": source_health,
        "notes": [
            "X 动态默认通过 RSS 镜像获取，请把 X_RSS_TEMPLATE 设置成你可访问的镜像地址，例如 https://nitter.net/{handle}/rss。",
            "英文内容会优先自动翻译成中文；如果翻译接口不可用，页面会回退到原文或半自动翻译结果。",
        ],
    }
    return payload


def demo_item(
    title: str,
    publication: str,
    description: str,
    hours_ago: int,
    kind: str,
    target_name: str = "",
    handle: str = "",
) -> FeedItem:
    published_at = dt.datetime.now(TZ) - dt.timedelta(hours=hours_ago)
    return FeedItem(
        title=title,
        link=f"https://example.com/{normalize_title(title)[:24] or 'item'}",
        description=description,
        published_at=published_at,
        source_name=publication,
        publication=publication,
        kind=kind,
        target_name=target_name,
        handle=handle,
    )


def generate_demo_payload() -> dict[str, object]:
    translation_cache = load_translation_cache()
    news_items = [
        demo_item(
            "OpenAI pushes a more practical agent workflow into ChatGPT",
            "The Information",
            "市场讨论点集中在更低门槛的代理流程和办公自动化能力，这会直接影响普通用户采用速度。",
            2,
            "news",
        ),
        demo_item(
            "Google expands Gemini into search and productivity surfaces",
            "The Verge",
            "这说明 Gemini 的重点不仅是模型本身，还包括默认入口和分发面。",
            4,
            "news",
        ),
        demo_item(
            "Anthropic emphasizes safer enterprise use cases for Claude",
            "TechCrunch",
            "企业协作和治理能力正在成为 Claude 的防守区，也是采购决策最看重的部分。",
            7,
            "news",
        ),
        demo_item(
            "xAI hints at faster Grok rollouts tied to the X platform",
            "Reuters",
            "Grok 继续把实时信息和社交分发绑在一起，打法更像平台级产品而不是单点模型。",
            9,
            "news",
        ),
        demo_item(
            "Nvidia supply and inference pricing stay at the center of the AI buildout",
            "Bloomberg",
            "算力和成本预期仍在决定谁能更快把新模型推向大众市场。",
            12,
            "news",
        ),
    ]

    watch_sections = [
        build_watch_section(
            WATCH_TARGETS[0],
            [
                demo_item(
                    "Gemini signals more product integrations across work and search",
                    "@GeminiApp",
                    "重点不是单次发布，而是默认入口越来越多。",
                    1,
                    "x",
                    "Gemini",
                    "GeminiApp",
                ),
                demo_item(
                    "Google DeepMind previews another capability milestone for Gemini",
                    "@GoogleDeepMind",
                    "新能力通常会在几天内传导到开发者和消费者产品。",
                    6,
                    "x",
                    "Gemini",
                    "GoogleDeepMind",
                ),
            ],
            translation_cache,
            allow_remote_translation=False,
        ),
        build_watch_section(
            WATCH_TARGETS[1],
            [
                demo_item(
                    "Grok continues to lean into real-time answers on X",
                    "@grok",
                    "实时和社交传播依旧是这条产品线最鲜明的差异点。",
                    3,
                    "x",
                    "Grok",
                    "grok",
                )
            ],
            translation_cache,
            allow_remote_translation=False,
        ),
        build_watch_section(
            WATCH_TARGETS[2],
            [
                demo_item(
                    "Anthropic highlights more team workflows and safer defaults for Claude",
                    "@AnthropicAI",
                    "Claude 正在把企业协同和治理能力做得更完整。",
                    5,
                    "x",
                    "Claude",
                    "AnthropicAI",
                )
            ],
            translation_cache,
            allow_remote_translation=False,
        ),
        build_watch_section(
            WATCH_TARGETS[3],
            [
                demo_item(
                    "OpenAI teases another round of ChatGPT usability improvements",
                    "@OpenAI",
                    "面向大众用户的入口体验仍然是 ChatGPT 的核心优势。",
                    8,
                    "x",
                    "ChatGPT",
                    "OpenAI",
                )
            ],
            translation_cache,
            allow_remote_translation=False,
        ),
    ]

    source_health = [
        {"name": "Google News / AI headlines", "kind": "news", "status": "ok", "message": "演示数据"},
        {"name": "Google News / Big model companies", "kind": "news", "status": "ok", "message": "演示数据"},
        {"name": "Google News / AI infra and agents", "kind": "news", "status": "ok", "message": "演示数据"},
        {"name": "X / demo mirror", "kind": "x", "status": "ok", "message": "演示数据"},
    ]

    save_translation_cache(translation_cache)

    return {
        "generated_at": dt.datetime.now(TZ).isoformat(),
        "generated_label": dt.datetime.now(TZ).strftime("%Y年%m月%d日 %H:%M"),
        "timezone": "Asia/Shanghai",
        "mode": "demo",
        "overview": build_overview(
            news_items,
            watch_sections,
            source_health,
            translation_cache,
            allow_remote_translation=False,
        ),
        "stats": {
            "news_count": len(news_items),
            "x_count": sum(len(section["highlights"]) for section in watch_sections),
            "healthy_sources": 4,
            "total_sources": 4,
        },
        "top_news": serialize_news(
            news_items,
            translation_cache,
            allow_remote_translation=False,
        ),
        "x_watchlist": watch_sections,
        "source_health": source_health,
        "notes": [
            "当前页面展示的是演示数据，用来先确认版式和交互。",
            "把 X_RSS_TEMPLATE 指向可访问的镜像后，再运行不带 --demo 的命令就会生成真实日报。",
        ],
    }


def write_payload(payload: dict[str, object]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    latest_path = DATA_DIR / "latest.json"
    history_path = HISTORY_DIR / f"{dt.datetime.now(TZ):%Y-%m-%d}.json"
    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    latest_path.write_text(encoded + "\n", encoding="utf-8")
    history_path.write_text(encoded + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an AI daily briefing JSON payload.")
    parser.add_argument("--demo", action="store_true", help="write demo content instead of live feeds")
    args = parser.parse_args()

    payload = generate_demo_payload() if args.demo else generate_live_payload()
    write_payload(payload)

    latest_path = DATA_DIR / "latest.json"
    print(f"Wrote briefing to {latest_path}")
    print(f"Mode: {payload['mode']}")
    print(f"News items: {payload['stats']['news_count']}")
    print(f"X updates: {payload['stats']['x_count']}")


if __name__ == "__main__":
    main()
