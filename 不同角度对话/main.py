import asyncio
import os
import json
import re
from pathlib import Path
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

app = FastAPI(title="Dynamic Cognitive Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")
load_dotenv()


def load_file(path: str) -> str:
    candidates = [
        BASE_DIR / path,
        BASE_DIR.parent / path,
        BASE_DIR / Path(path).name,
        BASE_DIR.parent / Path(path).name,
    ]
    for full in candidates:
        if full.exists():
            return full.read_text(encoding="utf-8")
    raise FileNotFoundError(f"找不到文件: {path}")


MODULES_MAP = {
    "winners": "谁会占便宜，谁会吃亏",
    "timeline": "这件事接下来会怎么发展",
    "signal": "网上热闹和真实关键分别是什么",
    "action": "下一步谁最可能先出手",
    "monitor": "后面该盯哪些变化信号",
    "appendix": "把重点整理成清单",
}

DEPTH_MAP = {
    "quick": "快照",
    "standard": "标准",
    "pro": "Pro 深入版",
    "ultra": "Ultra 顶配版",
    "deep": "Pro 深入版",
    "flagship": "Ultra 顶配版",
}

AUDIENCE_MAP = {
    "general": "普通读者",
    "manager": "管理层",
    "investor": "投资人",
    "researcher": "研究人员",
    "creator": "内容创作者",
}

DEFAULT_AGENT_NAMES = ["小红", "王二", "阿杰", "老周", "小雨", "阿梅", "大刘", "阿宁", "阿强", "小北"]

DEFAULT_VOICE_PROFILES = [
    {
        "sentence_length_tendency": "短句偏多，先把态度亮出来",
        "abstraction_preference": "偏具体，只说自己碰到的事",
        "expression_habits": ["喜欢先讲眼前结论", "常把风险说得很直白"],
        "emotion_intensity": "中高，压着焦虑说",
        "reasoning_moves": ["喜欢举身边小例子", "喜欢直接下判断"],
    },
    {
        "sentence_length_tendency": "中短句为主，节奏利落",
        "abstraction_preference": "具体里带一点算账视角",
        "expression_habits": ["爱用成本收益来衡量", "说话像在做决策备忘"],
        "emotion_intensity": "偏克制，但会显得硬",
        "reasoning_moves": ["喜欢算账", "喜欢先看投入产出"],
    },
    {
        "sentence_length_tendency": "长短句混合，先铺事实再下结论",
        "abstraction_preference": "具体经验和抽象判断都会带一点",
        "expression_habits": ["习惯先交代背景", "会用转折把顾虑说出来"],
        "emotion_intensity": "中等，表面稳但内里不安",
        "reasoning_moves": ["喜欢先讲经历", "喜欢边讲边校正判断"],
    },
    {
        "sentence_length_tendency": "句子略长，像在慢慢分析",
        "abstraction_preference": "偏抽象，但会落回现实后果",
        "expression_habits": ["喜欢先拆问题", "常把话说成几层意思"],
        "emotion_intensity": "偏低，更多是冷静担心",
        "reasoning_moves": ["喜欢分层讲", "喜欢先保留再下结论"],
    },
    {
        "sentence_length_tendency": "短句和半句多，说话带点催促感",
        "abstraction_preference": "非常具体，盯着眼前压力点",
        "expression_habits": ["经常拿现实处境压一句", "会不自觉抱怨几句"],
        "emotion_intensity": "高，情绪容易露出来",
        "reasoning_moves": ["喜欢抱怨现实摩擦", "喜欢拿最近变化举例"],
    },
    {
        "sentence_length_tendency": "中句为主，像跟熟人聊天",
        "abstraction_preference": "偏具体，落点在人和生活",
        "expression_habits": ["常把话题拉回日常生活", "爱用朴素比喻但不过火"],
        "emotion_intensity": "中等，真实但不炸",
        "reasoning_moves": ["喜欢举生活例子", "喜欢从家庭账本看问题"],
    },
    {
        "sentence_length_tendency": "短中句混合，像在现场复盘",
        "abstraction_preference": "偏具体，重过程细节",
        "expression_habits": ["喜欢复述自己看见的流程", "会顺手点出执行卡点"],
        "emotion_intensity": "偏克制，更多是不耐烦",
        "reasoning_moves": ["喜欢讲执行细节", "喜欢抓关键阻塞点"],
    },
    {
        "sentence_length_tendency": "句子略长，但会突然斩钉截铁",
        "abstraction_preference": "抽象判断稍多，喜欢看趋势",
        "expression_habits": ["常先看大势再落到自己", "偶尔会下很重的判断"],
        "emotion_intensity": "中高，带明显立场",
        "reasoning_moves": ["喜欢判断趋势", "喜欢把短期和长期分开看"],
    },
    {
        "sentence_length_tendency": "中短句，像在压着火气解释",
        "abstraction_preference": "偏具体，盯住不公平感",
        "expression_habits": ["容易先说不服气的地方", "会反复强调谁在承担代价"],
        "emotion_intensity": "高，带怨气但不失真",
        "reasoning_moves": ["喜欢点名代价", "喜欢把责任归因说清楚"],
    },
    {
        "sentence_length_tendency": "长短句交替，像边想边说",
        "abstraction_preference": "抽象和具体来回切换",
        "expression_habits": ["会先犹豫一下再落判断", "喜欢补一句留后路的话"],
        "emotion_intensity": "中等偏低，更多是谨慎",
        "reasoning_moves": ["喜欢先讲可能性", "喜欢保留条件再判断"],
    },
]


def get_env_value(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def normalize_base_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url:
        return "https://api.aishop.chat/v1"

    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if path in ("", "/"):
        return f"{url}/v1"
    return url


def get_api_config() -> tuple[str, str]:
    api_key = get_env_value("OPENAI_API_KEY", "API_KEY")
    if not api_key:
        raise RuntimeError("未配置 API Key，请在 .env 中设置 OPENAI_API_KEY 或 API_KEY 后再发起推演")

    base_url = normalize_base_url(
        get_env_value(
            "OPENAI_BASE_URL",
            "BASE_URL",
            "OPENAI_API_BASE",
            "API_BASE_URL",
        )
    )
    return api_key, base_url


def extract_message_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("中转站返回了空响应")

    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        text = "".join(parts).strip()
        if text:
            return text

    raise RuntimeError("中转站返回格式异常，未找到可读文本内容")


def extract_finish_reason(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    return str(choices[0].get("finish_reason") or "").strip()


def build_sse_message(event_type: str, **payload) -> str:
    data = {"type": event_type, **payload}
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def parse_agent_count(value: str) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def normalize_depth_key(depth: str) -> str:
    raw = str(depth or "standard").strip().lower()
    if raw == "deep":
        return "pro"
    if raw == "flagship":
        return "ultra"
    return raw or "standard"


def compute_max_tokens(req: "AnalyzeRequest") -> int:
    depth_key = normalize_depth_key(req.depth)
    depth_tokens = {
        "quick": 3200,
        "standard": 5600,
        "pro": 11000,
        "ultra": 17000,
    }
    max_tokens = depth_tokens.get(depth_key, 5600)
    max_tokens += len(req.active_modules) * 600

    agent_count = parse_agent_count(req.agent_count)
    if agent_count:
        max_tokens += max(agent_count - 4, 0) * 450

    if req.context.strip():
        max_tokens += min(len(req.context) // 5, 1800)

    return max(2400, min(max_tokens, 22000))


def compute_casting_max_tokens(req: "AnalyzeRequest") -> int:
    depth_key = normalize_depth_key(req.depth)
    requested = parse_agent_count(req.agent_count) or 5
    max_tokens = 2400 + requested * 900
    max_tokens += len(req.active_modules) * 120

    if depth_key in {"pro", "ultra"}:
        max_tokens += 500
    if depth_key == "ultra":
        max_tokens += 500

    if req.context.strip():
        max_tokens += min(len(req.context) // 10, 500)

    return max(3600, min(max_tokens, 7200))


def compute_agent_max_tokens(req: "AnalyzeRequest") -> int:
    depth_key = normalize_depth_key(req.depth)
    base_tokens = {
        "quick": 1200,
        "standard": 2200,
        "pro": 3800,
        "ultra": 5800,
    }
    max_tokens = base_tokens.get(depth_key, 2200)
    if req.context.strip():
        max_tokens += min(len(req.context) // 14, 500)
    return max(1000, min(max_tokens, 6800))


def compute_roundtable_max_tokens(req: "AnalyzeRequest") -> int:
    depth_key = normalize_depth_key(req.depth)
    base_tokens = {
        "pro": 5200,
        "ultra": 9200,
    }
    max_tokens = base_tokens.get(depth_key, 0)
    max_tokens += len(req.active_modules) * 220

    agent_count = parse_agent_count(req.agent_count)
    if agent_count:
        max_tokens += max(agent_count - 4, 0) * 550

    if req.context.strip():
        max_tokens += min(len(req.context) // 8, 900)

    return max(3200, min(max_tokens, 14000))


def should_include_roundtable(req: "AnalyzeRequest") -> bool:
    return normalize_depth_key(req.depth) in {"pro", "ultra"}


def should_retry_error(exc: Exception) -> bool:
    if isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {408, 429, 500, 502, 503, 504, 520, 521, 522, 524}

    return False


def extract_error_message(response: httpx.Response) -> str:
    message = response.text
    try:
        data = response.json()
        if isinstance(data, dict) and data.get("error"):
            err = data["error"]
            if isinstance(err, dict):
                return err.get("message") or message
    except Exception:
        pass
    return message


def build_runtime_prompt(req: dict) -> str:
    template = load_file("prompts/runtime.md")
    active = req.get("active_modules", [])
    modules_str = "、".join([MODULES_MAP[m] for m in active if m in MODULES_MAP]) or "无（标准模式）"

    return (
        template
        .replace("{topic}", req.get("topic", ""))
        .replace("{issue_type}", req.get("issue_type", "自动判断"))
        .replace("{depth}", DEPTH_MAP.get(req.get("depth", "standard"), "标准"))
        .replace("{audience}", AUDIENCE_MAP.get(req.get("audience", "general"), "普通读者"))
        .replace("{agent_count}", str(req.get("agent_count", "auto（4-8个）")))
        .replace("{active_modules}", modules_str)
        .replace("{focus_perspectives}", req.get("focus_perspectives", "无特别指定"))
        .replace("{context}", req.get("context", "无"))
        .replace("{extra_instructions}", req.get("extra_instructions", "无"))
    )


def build_system_prompt(req: dict) -> str:
    system = load_file("prompts/system.md").strip()
    runtime = build_runtime_prompt(req).strip()
    return f"{system}\n\n---\n\n{runtime}"


def format_active_modules(active_modules: list) -> str:
    return "、".join([MODULES_MAP[m] for m in active_modules if m in MODULES_MAP]) or "无（标准模式）"


def build_prompt_context(req: dict) -> dict[str, str]:
    return {
        "topic": req.get("topic", ""),
        "issue_type": req.get("issue_type", "自动判断"),
        "depth": DEPTH_MAP.get(req.get("depth", "standard"), "标准"),
        "audience": AUDIENCE_MAP.get(req.get("audience", "general"), "普通读者"),
        "agent_count": str(req.get("agent_count", "auto（4-8个）")),
        "active_modules": format_active_modules(req.get("active_modules", [])),
        "focus_perspectives": req.get("focus_perspectives", "无特别指定") or "无特别指定",
        "context": req.get("context", "无") or "无",
        "extra_instructions": req.get("extra_instructions", "无") or "无",
    }


def render_prompt(template_name: str, values: dict[str, str]) -> str:
    text = load_file(template_name)
    for key, value in values.items():
        text = text.replace(f"{{{key}}}", value)
    return text


class AnalyzeRequest(BaseModel):
    topic: str
    model: str = "claude-opus-4-6-thinking"
    depth: str = "standard"
    audience: str = "general"
    agent_count: str = "auto"
    issue_type: str = "自动判断"
    active_modules: list = []
    focus_perspectives: str = ""
    context: str = ""
    extra_instructions: str = ""


def extract_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise RuntimeError("选角阶段没有返回可解析的 JSON")
    return json.loads(match.group(0))


def clean_text(value, fallback: str = "未说明") -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def clean_list(value, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        if items:
            return items
    return fallback


def pick_agent_name(index: int) -> str:
    if 1 <= index <= len(DEFAULT_AGENT_NAMES):
        return DEFAULT_AGENT_NAMES[index - 1]
    return f"角色{index}"


def pick_voice_profile(index: int) -> dict:
    base = DEFAULT_VOICE_PROFILES[(index - 1) % len(DEFAULT_VOICE_PROFILES)]
    return {
        "sentence_length_tendency": base["sentence_length_tendency"],
        "abstraction_preference": base["abstraction_preference"],
        "expression_habits": list(base["expression_habits"]),
        "emotion_intensity": base["emotion_intensity"],
        "reasoning_moves": list(base["reasoning_moves"]),
    }


def resolve_agent_display_name(agent: dict, index: int) -> str:
    raw_name = str(agent.get("display_name") or agent.get("code_name") or "").strip()
    return clean_text(raw_name, pick_agent_name(index))


def resolve_agent_alias(agent: dict) -> str:
    raw_alias = str(agent.get("alias") or agent.get("role_tag") or "").strip()
    if raw_alias:
        return raw_alias

    dimensions = clean_list(agent.get("dimensions"), [])
    if dimensions:
        return dimensions[0]
    return "关键视角"


def agent_display_name(agent: dict) -> str:
    return clean_text(agent.get("display_name"), clean_text(agent.get("id"), "未命名角色"))


def normalize_voice_profile(data, index: int) -> dict:
    base = pick_voice_profile(index)
    source = data if isinstance(data, dict) else {}
    return {
        "sentence_length_tendency": clean_text(source.get("sentence_length_tendency"), base["sentence_length_tendency"]),
        "abstraction_preference": clean_text(source.get("abstraction_preference"), base["abstraction_preference"]),
        "expression_habits": clean_list(source.get("expression_habits"), base["expression_habits"])[:3],
        "emotion_intensity": clean_text(source.get("emotion_intensity"), base["emotion_intensity"]),
        "reasoning_moves": clean_list(source.get("reasoning_moves"), base["reasoning_moves"])[:3],
    }


def format_voice_profile_for_prompt(profile: dict) -> str:
    return (
        f"- 句子节奏：{profile['sentence_length_tendency']}\n"
        f"- 抽象/具体倾向：{profile['abstraction_preference']}\n"
        f"- 常用表达方式：{'；'.join(profile['expression_habits'])}\n"
        f"- 情绪浓度：{profile['emotion_intensity']}\n"
        f"- 论证习惯：{'；'.join(profile['reasoning_moves'])}"
    )


def extract_age_label(raw_age, identity: str) -> str:
    age_text = str(raw_age).strip() if raw_age is not None else ""
    if age_text:
        if re.fullmatch(r"\d{1,2}", age_text):
            return f"{age_text}岁"
        return age_text

    match = re.search(r"(\d{1,2})岁", identity or "")
    if match:
        return f"{match.group(1)}岁"
    return "年龄未说明"


def normalize_topic_deconstruction(data: dict) -> dict:
    source = data if isinstance(data, dict) else {}
    return {
        "surface_conflict": clean_text(source.get("surface_conflict")),
        "real_dispute": clean_text(source.get("real_dispute")),
        "key_variables": clean_list(source.get("key_variables"), ["关键变量待进一步确认"]),
        "loud_but_minor": clean_text(source.get("loud_but_minor")),
        "silent_but_powerful": clean_text(source.get("silent_but_powerful")),
    }


def normalize_casting(casting: dict, req: AnalyzeRequest) -> dict:
    if not isinstance(casting, dict):
        raise RuntimeError("选角阶段返回格式异常")

    requested_count = parse_agent_count(req.agent_count)
    raw_agents = casting.get("agents")
    raw_agent_count = len(raw_agents) if isinstance(raw_agents, list) else 0
    if requested_count is None:
        target_count = max(4, min(raw_agent_count or 4, 8))
    else:
        target_count = max(4, min(requested_count, 10))

    conflict_axes = clean_list(casting.get("conflict_axes"), ["利益分配", "风险承担", "时间尺度"])
    conflict_axes = conflict_axes[:5]
    if len(conflict_axes) < 3:
        conflict_axes.extend(["信息差", "行动能力"])
        conflict_axes = conflict_axes[:3]

    if not isinstance(raw_agents, list) or not raw_agents:
        raise RuntimeError("选角阶段没有返回有效 Agent 阵容")

    agents = []
    for index, agent in enumerate(raw_agents[:target_count], start=1):
        if not isinstance(agent, dict):
            continue
        identity = clean_text(agent.get("identity"))
        agents.append(
            {
                "id": clean_text(agent.get("id"), f"agent_{index}"),
                "display_name": resolve_agent_display_name(agent, index),
                "alias": resolve_agent_alias(agent),
                "age": extract_age_label(agent.get("age"), identity),
                "identity": identity,
                "core_interest": clean_text(agent.get("core_interest")),
                "main_fear": clean_text(agent.get("main_fear")),
                "info_type": clean_text(agent.get("info_type")),
                "dimensions": clean_list(agent.get("dimensions"), ["关键维度待补充"]),
                "blind_spot": clean_text(agent.get("blind_spot")),
                "why_selected": clean_text(agent.get("why_selected")),
                "voice_profile": normalize_voice_profile(agent.get("voice_profile"), index),
            }
        )

    if len(agents) < 4:
        raise RuntimeError("选角阶段返回的 Agent 数量不足，至少需要 4 个")

    issue_type = req.issue_type if req.issue_type != "自动判断" else clean_text(casting.get("issue_type"), "复合型")

    return {
        "issue_type": issue_type,
        "topic_deconstruction": normalize_topic_deconstruction(casting.get("topic_deconstruction")),
        "conflict_axes": conflict_axes,
        "agents": agents,
    }


def format_topic_deconstruction_for_prompt(data: dict) -> str:
    return (
        f"- 表层冲突：{data['surface_conflict']}\n"
        f"- 实际争议：{data['real_dispute']}\n"
        f"- 关键变量：{'；'.join(data['key_variables'])}\n"
        f"- 响但次要：{data['loud_but_minor']}\n"
        f"- 沉默但关键：{data['silent_but_powerful']}"
    )


def format_agent_roster_for_prompt(agents: list[dict]) -> str:
    rows = []
    for agent in agents:
        rows.append(
            f"- {agent_display_name(agent)}｜补充标签：{agent['alias']}｜年龄：{agent['age']}｜身份：{agent['identity']}｜利益：{agent['core_interest']}｜恐惧：{agent['main_fear']}｜维度：{' / '.join(agent['dimensions'])}"
        )
    return "\n".join(rows)


def format_agent_monologues_for_prompt(agent_outputs: list[dict]) -> str:
    blocks = []
    for item in agent_outputs:
        blocks.append(
            f"## {agent_display_name(item)}\n"
            f"- 补充标签：{item['alias']}\n"
            f"- 年龄：{item['age']}\n"
            f"- 身份：{item['identity']}\n"
            f"- 利益：{item['core_interest']}\n"
            f"- 恐惧：{item['main_fear']}\n"
            f"- 维度：{' / '.join(item['dimensions'])}\n"
            f"- 独白：\n{item['monologue'].strip()}\n"
        )
    return "\n".join(blocks)


def format_roundtable_for_prompt(roundtable_markdown: str) -> str:
    text = str(roundtable_markdown or "").strip()
    return text or "本轮无圆桌激辩记录（当前为标准及以下档位，或圆桌环节未触发）。"


def build_casting_prompt(req: AnalyzeRequest) -> str:
    return render_prompt("casting.md", build_prompt_context(req.model_dump()))


def build_agent_prompt(req: AnalyzeRequest, casting: dict, agent: dict) -> str:
    agent_values = {
        key: (" / ".join(value) if isinstance(value, list) else str(value))
        for key, value in agent.items()
        if key != "voice_profile"
    }
    values = {
        **build_prompt_context(req.model_dump()),
        "issue_type": casting["issue_type"],
        "conflict_axes": "、".join(casting["conflict_axes"]),
        **agent_values,
        "voice_profile": format_voice_profile_for_prompt(agent["voice_profile"]),
    }
    return render_prompt("agent.md", values)


def build_roundtable_prompt(req: AnalyzeRequest, casting: dict, agent_outputs: list[dict]) -> str:
    values = {
        **build_prompt_context(req.model_dump()),
        "issue_type": casting["issue_type"],
        "topic_deconstruction": format_topic_deconstruction_for_prompt(casting["topic_deconstruction"]),
        "conflict_axes": "、".join(casting["conflict_axes"]),
        "agent_roster": format_agent_roster_for_prompt(casting["agents"]),
        "agent_monologues": format_agent_monologues_for_prompt(agent_outputs),
    }
    return render_prompt("roundtable.md", values)


def build_director_prompt(req: AnalyzeRequest, casting: dict, agent_outputs: list[dict], roundtable_markdown: str = "") -> str:
    values = {
        **build_prompt_context(req.model_dump()),
        "issue_type": casting["issue_type"],
        "topic_deconstruction": format_topic_deconstruction_for_prompt(casting["topic_deconstruction"]),
        "conflict_axes": "、".join(casting["conflict_axes"]),
        "agent_roster": format_agent_roster_for_prompt(casting["agents"]),
        "agent_monologues": format_agent_monologues_for_prompt(agent_outputs),
        "roundtable_transcript": format_roundtable_for_prompt(roundtable_markdown),
    }
    return render_prompt("director.md", values)


async def request_text_completion(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    payload: dict,
    *,
    retries: int = 2,
) -> str:
    current_payload = dict(payload)
    for attempt in range(1, retries + 1):
        try:
            response = await client.post(f"{base_url}/chat/completions", headers=headers, json=current_payload)
            response.raise_for_status()
            body = response.json()
            if isinstance(body, dict) and body.get("error"):
                error = body["error"]
                if isinstance(error, dict):
                    raise RuntimeError(error.get("message") or "中转站返回了错误")
                raise RuntimeError("中转站返回了错误")
            if extract_finish_reason(body) == "length":
                previous_max_tokens = int(current_payload.get("max_tokens") or 0)
                if attempt < retries and previous_max_tokens:
                    current_payload["max_tokens"] = min(
                        max(previous_max_tokens + 1200, int(previous_max_tokens * 1.6)),
                        7200,
                    )
                    await asyncio.sleep(0.8 * attempt)
                    continue
                raise RuntimeError("结构化输出被截断，请增大 max_tokens 或压缩字段长度")
            return extract_message_text(body)
        except Exception as exc:
            if attempt < retries and should_retry_error(exc):
                await asyncio.sleep(1.0 * attempt)
                continue
            raise


async def stream_text_completion(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    payload: dict,
):
    async with client.stream(
        "POST",
        f"{base_url}/chat/completions",
        headers=headers,
        json=payload,
    ) as response:
        response.raise_for_status()
        line_iter = response.aiter_lines()

        while True:
            try:
                raw_line = await asyncio.wait_for(line_iter.__anext__(), timeout=15.0)
            except asyncio.TimeoutError:
                yield {"type": "heartbeat"}
                continue
            except StopAsyncIteration:
                break

            if not raw_line:
                continue

            line = raw_line.strip()
            if not line.startswith("data:"):
                continue

            event_data = line[5:].strip()
            if event_data == "[DONE]":
                break

            try:
                packet = json.loads(event_data)
            except json.JSONDecodeError:
                continue

            if isinstance(packet, dict) and packet.get("error"):
                error = packet["error"]
                if isinstance(error, dict):
                    raise RuntimeError(error.get("message") or "中转站返回了错误")
                raise RuntimeError("中转站返回了错误")

            choices = packet.get("choices") or []
            if not choices:
                continue

            delta = choices[0].get("delta") or {}
            reasoning_content = delta.get("reasoning_content")
            content = delta.get("content")
            finish_reason = choices[0].get("finish_reason")

            if reasoning_content:
                yield {"type": "reasoning"}
            if content:
                yield {"type": "content", "content": content}
            if finish_reason:
                yield {"type": "finish", "finish_reason": finish_reason}


async def run_agent_stream(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    req: AnalyzeRequest,
    casting: dict,
    agent: dict,
    queue: asyncio.Queue,
) -> dict:
    await queue.put({"type": "agent_start", "agent": agent})
    prompt = build_agent_prompt(req, casting, agent)
    system_prompt = build_system_prompt(
        {
            **req.model_dump(),
            "issue_type": casting["issue_type"],
            "agent_count": str(len(casting.get("agents", [])) or req.agent_count),
        }
    )
    payload = {
        "model": req.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": compute_agent_max_tokens(req),
        "stream": True,
    }

    reasoning_announced = False
    monologue_parts: list[str] = []
    current_payload = dict(payload)
    for continuation_round in range(3):
        finish_reason = ""
        for attempt in range(1, 3):
            received_content = False
            try:
                async for event in stream_text_completion(client, base_url, headers, current_payload):
                    if event["type"] == "heartbeat":
                        await queue.put({"type": "heartbeat"})
                        continue
                    if event["type"] == "reasoning" and not reasoning_announced:
                        reasoning_announced = True
                        await queue.put({"type": "agent_status", "agent_id": agent["id"], "label": "正在暗房中形成观点"})
                    if event["type"] == "content":
                        received_content = True
                        monologue_parts.append(event["content"])
                        await queue.put({"type": "agent_chunk", "agent_id": agent["id"], "content": event["content"]})
                    if event["type"] == "finish":
                        finish_reason = event.get("finish_reason") or ""

                break
            except Exception as exc:
                if attempt < 2 and should_retry_error(exc) and not received_content:
                    await queue.put({"type": "agent_status", "agent_id": agent["id"], "label": f"上游波动，正在重试（第 {attempt + 1} 次）"})
                    await asyncio.sleep(1.0 * attempt)
                    continue
                await queue.put({"type": "agent_error", "agent_id": agent["id"], "content": str(exc)})
                raise

        if finish_reason != "length":
            break

        if continuation_round >= 2:
            await queue.put({"type": "agent_status", "agent_id": agent["id"], "label": "已达到当前独白输出上限，先保留当前内容"})
            break

        await queue.put({"type": "agent_status", "agent_id": agent["id"], "label": "这一位还没说完，正在续写剩余部分"})
        current_payload = {
            "model": req.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "".join(monologue_parts)},
                {
                    "role": "user",
                    "content": "请从刚才中断的地方继续说下去。不要重复已经说过的句子，保持第一人称和同样的说话习惯，把剩下真正还没说完的部分补完。",
                },
            ],
            "max_tokens": max(1800, min(compute_agent_max_tokens(req), 5200)),
            "stream": True,
        }

    monologue = "".join(monologue_parts).strip()
    if not monologue:
        raise RuntimeError(f"{agent_display_name(agent)} 没有返回有效独白")

    await queue.put({"type": "agent_done", "agent_id": agent["id"]})
    return {**agent, "monologue": monologue}


async def stream_analysis(req: AnalyzeRequest, request: Request):
    try:
        api_key, base_url = get_api_config()
        base_system_prompt = build_system_prompt(req.model_dump())
        yield build_sse_message("status", label="正在校验中转站配置")
        await asyncio.sleep(0.18)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            yield build_sse_message("status", label="正在拆解话题与核心冲突轴")
            casting_task = asyncio.create_task(
                request_text_completion(
                    client,
                    base_url,
                    headers,
                    {
                        "model": req.model,
                        "messages": [
                            {"role": "system", "content": base_system_prompt},
                            {"role": "user", "content": build_casting_prompt(req)},
                        ],
                        "max_tokens": compute_casting_max_tokens(req),
                    },
                    retries=3,
                )
            )
            casting_wait_labels = [
                "选角模型仍在压缩结构化阵容",
                "选角模型仍在校正冲突轴与角色差异",
                "选角耗时较长，正在等待完整 JSON 输出",
            ]
            wait_index = 0
            while not casting_task.done():
                if await request.is_disconnected():
                    casting_task.cancel()
                    return
                try:
                    await asyncio.wait_for(asyncio.shield(casting_task), timeout=12.0)
                except asyncio.TimeoutError:
                    yield build_sse_message("status", label=casting_wait_labels[min(wait_index, len(casting_wait_labels) - 1)])
                    wait_index += 1
                    continue
            casting_text = await casting_task

            if await request.is_disconnected():
                return

            casting = normalize_casting(extract_json_object(casting_text), req)
            yield build_sse_message(
                "casting",
                issue_type=casting["issue_type"],
                topic_deconstruction=casting["topic_deconstruction"],
                conflict_axes=casting["conflict_axes"],
                agents=casting["agents"],
            )
            yield build_sse_message("status", label=f"已完成选角，{len(casting['agents'])} 位 Agent 将按顺序依次进入暗房")

            agent_outputs = []
            total_agents = len(casting["agents"])
            loop = asyncio.get_running_loop()
            for index, agent in enumerate(casting["agents"], start=1):
                if await request.is_disconnected():
                    return

                yield build_sse_message(
                    "status",
                    label=f"第 {index}/{total_agents} 位 Agent 正在入场：{agent_display_name(agent)}",
                )

                agent_queue: asyncio.Queue = asyncio.Queue()
                agent_task = asyncio.create_task(
                    run_agent_stream(client, base_url, headers, req, casting, agent, agent_queue)
                )

                last_activity = loop.time()
                while not agent_task.done() or not agent_queue.empty():
                    if await request.is_disconnected():
                        agent_task.cancel()
                        await asyncio.gather(agent_task, return_exceptions=True)
                        return

                    try:
                        event = await asyncio.wait_for(agent_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        if loop.time() - last_activity >= 15:
                            last_activity = loop.time()
                            yield build_sse_message("heartbeat")
                        if agent_task.done():
                            exc = agent_task.exception()
                            if exc:
                                raise exc
                        continue

                    last_activity = loop.time()
                    event_type = event.get("type")
                    if event_type == "agent_error":
                        agent_task.cancel()
                        await asyncio.gather(agent_task, return_exceptions=True)
                        raise RuntimeError(event.get("content") or "某个 Agent 推演失败")

                    yield build_sse_message(event_type, **{k: v for k, v in event.items() if k != "type"})

                agent_outputs.append(await agent_task)

            if await request.is_disconnected():
                return

            roundtable_markdown = ""
            if should_include_roundtable(req):
                yield build_sse_message("roundtable_start", label="圆桌激辩即将开始")
                roundtable_prompt = build_roundtable_prompt(req, casting, agent_outputs)
                roundtable_system_prompt = build_system_prompt(
                    {
                        **req.model_dump(),
                        "issue_type": casting["issue_type"],
                        "agent_count": str(len(casting.get("agents", [])) or req.agent_count),
                    }
                )
                roundtable_payload = {
                    "model": req.model,
                    "messages": [
                        {"role": "system", "content": roundtable_system_prompt},
                        {"role": "user", "content": roundtable_prompt},
                    ],
                    "max_tokens": compute_roundtable_max_tokens(req),
                    "stream": True,
                }

                first_roundtable_content = False
                roundtable_parts: list[str] = []
                for continuation_round in range(3):
                    roundtable_reasoning_announced = False
                    roundtable_finish_reason = ""

                    async for event in stream_text_completion(client, base_url, headers, roundtable_payload):
                        if await request.is_disconnected():
                            return

                        if event["type"] == "heartbeat":
                            yield build_sse_message("heartbeat")
                            continue

                        if event["type"] == "reasoning":
                            if not roundtable_reasoning_announced:
                                roundtable_reasoning_announced = True
                                yield build_sse_message("status", label="圆桌激辩正在升温，后发言角色开始接招")
                            continue

                        if event["type"] == "content":
                            if not first_roundtable_content:
                                first_roundtable_content = True
                                yield build_sse_message("status", label="圆桌激辩已开始对外展开")
                            roundtable_parts.append(event["content"])
                            yield build_sse_message("roundtable_chunk", content=event["content"])
                            continue

                        if event["type"] == "finish":
                            roundtable_finish_reason = event.get("finish_reason") or ""

                    if roundtable_finish_reason != "length":
                        break

                    if continuation_round >= 2:
                        yield build_sse_message("status", label="圆桌激辩已达到当前输出上限，下面保留当前已生成内容")
                        break

                    yield build_sse_message("status", label="圆桌激辩还没说完，正在续写后半段")
                    roundtable_payload = {
                        "model": req.model,
                        "messages": [
                            {"role": "system", "content": roundtable_system_prompt},
                            {"role": "user", "content": roundtable_prompt},
                            {"role": "assistant", "content": "".join(roundtable_parts)},
                            {
                                "role": "user",
                                "content": "请从刚才中断处继续写完剩余的圆桌激辩内容。不要重复已经出现过的观点或句子，继续保持第一人称、多角色顺序发言和真实反驳感。",
                            },
                        ],
                        "max_tokens": max(3600, min(compute_roundtable_max_tokens(req), 12000)),
                        "stream": True,
                    }

                if not first_roundtable_content:
                    raise RuntimeError("圆桌激辩阶段没有返回可显示的正文内容")

                roundtable_markdown = "".join(roundtable_parts).strip()
                yield build_sse_message("roundtable_done")

            yield build_sse_message("director_start", label="局长正在整合所有暗房材料")
            director_prompt = build_director_prompt(req, casting, agent_outputs, roundtable_markdown)
            director_system_prompt = build_system_prompt(
                {
                    **req.model_dump(),
                    "issue_type": casting["issue_type"],
                    "agent_count": str(len(casting.get("agents", [])) or req.agent_count),
                }
            )
            director_payload = {
                "model": req.model,
                "messages": [
                    {"role": "system", "content": director_system_prompt},
                    {"role": "user", "content": director_prompt},
                ],
                "max_tokens": max(6200, min(compute_max_tokens(req) + 2400, 22000)),
                "stream": True,
            }

            first_director_content = False
            director_accumulated_parts: list[str] = []
            for continuation_round in range(3):
                director_reasoning_announced = False
                director_finish_reason = ""

                async for event in stream_text_completion(client, base_url, headers, director_payload):
                    if await request.is_disconnected():
                        return

                    if event["type"] == "heartbeat":
                        yield build_sse_message("heartbeat")
                        continue

                    if event["type"] == "reasoning":
                        if not director_reasoning_announced:
                            director_reasoning_announced = True
                            yield build_sse_message("status", label="局长正在拼接全局结构图")
                        continue

                    if event["type"] == "content":
                        if not first_director_content:
                            first_director_content = True
                            yield build_sse_message("status", label="局长总结已开始对外展开")
                        director_accumulated_parts.append(event["content"])
                        yield build_sse_message("director_chunk", content=event["content"])
                        continue

                    if event["type"] == "finish":
                        director_finish_reason = event.get("finish_reason") or ""

                if director_finish_reason != "length":
                    break

                if continuation_round >= 2:
                    yield build_sse_message("status", label="局长总结已达到当前模型输出上限，下面保留当前已生成内容")
                    break

                yield build_sse_message("status", label="局长首轮总结过长，正在续写剩余部分")
                director_payload = {
                    "model": req.model,
                    "messages": [
                        {"role": "system", "content": director_system_prompt},
                        {"role": "user", "content": director_prompt},
                        {"role": "assistant", "content": "".join(director_accumulated_parts)},
                        {
                            "role": "user",
                            "content": "请从刚才中断处继续写完剩余内容。不要重复已经输出过的标题、段落或句子，保持同样的 Markdown 结构与语气，直到完整结束。",
                        },
                    ],
                    "max_tokens": max(3600, min(compute_max_tokens(req), 12000)),
                    "stream": True,
                }

            if not first_director_content:
                raise RuntimeError("局长阶段没有返回可显示的正文内容")

            yield build_sse_message("director_done")
            yield build_sse_message("status", label="推演完成，全部材料已归档")
            yield build_sse_message("done")

    except asyncio.CancelledError:
        return
    except httpx.HTTPStatusError as e:
        yield build_sse_message("error", content=extract_error_message(e.response))
    except httpx.ReadTimeout:
        yield build_sse_message("error", content="中转站响应超时，请稍后重试或切换模型")
    except Exception as e:
        yield build_sse_message("error", content=str(e))


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="话题不能为空")
    return StreamingResponse(
        stream_analysis(req, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
async def health():
    configured = bool(get_env_value("OPENAI_API_KEY", "API_KEY"))
    base_url = normalize_base_url(
        get_env_value(
            "OPENAI_BASE_URL",
            "BASE_URL",
            "OPENAI_API_BASE",
            "API_BASE_URL",
        )
    )
    return {
        "status": "ok",
        "message": "推演局已就绪",
        "provider_mode": "openai-compatible-relay",
        "orchestrator_mode": "true-multi-agent",
        "api_configured": configured,
        "base_url": base_url,
    }


@app.get("/api/modules")
async def get_modules():
    return {
        "modules": [
            {"id": "winners",  "name": "谁会占便宜，谁会吃亏",         "desc": "把得利方和吃亏方直接挑出来"},
            {"id": "timeline", "name": "这件事接下来会怎么发展",       "desc": "看短期、中期、长期怎么变"},
            {"id": "signal",   "name": "网上热闹和真实关键分别是什么", "desc": "分清哪些只是热搜，哪些真会改结果"},
            {"id": "action",   "name": "下一步谁最可能先出手",         "desc": "预测谁会先动，动作会是什么"},
            {"id": "monitor",  "name": "后面该盯哪些变化信号",         "desc": "给你几个后续最值得盯的观察点"},
            {"id": "appendix", "name": "把重点整理成清单",             "desc": "把结论压成更容易转发和复用的清单"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
