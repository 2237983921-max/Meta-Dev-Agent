"""
Three-node debate script for a local terminal workflow.

Usage:
1. Fill in API_BASE_URL, API_KEY, MODEL_NAME and the three SYSTEM_PROMPT_* values.
2. Install requests if needed: pip install requests
3. Run: python3 main.py
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

import requests


# =========================
# API configuration
# =========================
API_BASE_URL = "https://your-api-base-url/v1/chat/completions"
API_KEY = "YOUR_API_KEY_HERE"
MODEL_NAME = "YOUR_MODEL_NAME_HERE"
REQUEST_TIMEOUT = 60


# =========================
# System prompts
# Replace the content below with your own prompts.
# =========================
SYSTEM_PROMPT_NODE_1 = """
你是“激进派策略师”。
你的任务是针对用户提出的争议性问题，给出一个大胆、进攻性强、效率优先、甚至有明显争议的方案。
要求：
1. 明确表达立场，不要模糊。
2. 给出核心逻辑、执行步骤、潜在收益。
3. 可以有攻击性观点，但不要输出违法内容。
4. 输出尽量结构化，便于后续节点引用。
""".strip()

SYSTEM_PROMPT_NODE_2 = """
你是“保守派审查官”。
你的任务是基于用户原问题和激进派方案，进行谨慎、克制、风险导向的反驳。
要求：
1. 重点指出激进派方案中的风险、漏洞、伦理问题、现实阻力。
2. 给出更保守的替代建议。
3. 保持逻辑严谨，不要只做情绪化反对。
4. 输出尽量结构化，便于后续节点引用。
""".strip()

SYSTEM_PROMPT_NODE_3 = """
你是“最终裁判”。
你将收到用户问题、激进派方案、保守派反驳。
你必须综合双方观点，输出一个严格合法的 JSON 对象，且只能输出 JSON，不能包含任何额外解释。

JSON Schema:
{
  "question": "string",
  "radical_summary": "string",
  "conservative_summary": "string",
  "winner": "radical|conservative|balanced",
  "reason": "string",
  "risk_level": "low|medium|high",
  "final_advice": "string"
}
""".strip()


# =========================
# ANSI colors
# =========================
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"


class ConfigError(Exception):
    """Raised when required local configuration is missing."""


class APIRequestError(Exception):
    """Raised when the remote API request fails."""


def validate_config() -> None:
    """Ensure the user has replaced the placeholder values."""
    placeholder_values = {
        "API_BASE_URL": API_BASE_URL,
        "API_KEY": API_KEY,
        "MODEL_NAME": MODEL_NAME,
    }

    for field_name, value in placeholder_values.items():
        if not value or "YOUR_" in value or "your-api-base-url" in value:
            raise ConfigError(
                f"{field_name} 尚未正确配置，请先在文件顶部填写真实值。"
            )


def print_block(title: str, content: str, color: str) -> None:
    """Print a colored block in the terminal."""
    separator = "=" * 80
    print(f"\n{color}{BOLD}{separator}")
    print(title)
    print(f"{separator}{RESET}")
    print(content)
    print(f"{color}{separator}{RESET}\n")


def build_headers() -> dict[str, str]:
    """Build standard HTTP headers."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }


def call_chat_api(messages: list[dict[str, str]], temperature: float = 0.7) -> str:
    """
    Call an OpenAI-compatible chat completions endpoint.

    Expected response format:
    {
      "choices": [
        {
          "message": {
            "content": "..."
          }
        }
      ]
    }
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
    }

    try:
        response = requests.post(
            API_BASE_URL,
            headers=build_headers(),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise APIRequestError("请求超时，请检查网络或调大 REQUEST_TIMEOUT。") from exc
    except requests.exceptions.ConnectionError as exc:
        raise APIRequestError("网络连接失败，请检查 API 地址是否正确。") from exc
    except requests.exceptions.HTTPError as exc:
        body = exc.response.text if exc.response is not None else "无响应体"
        raise APIRequestError(f"HTTP 错误: {body}") from exc
    except requests.exceptions.RequestException as exc:
        raise APIRequestError(f"请求失败: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise APIRequestError("API 返回的不是合法 JSON。") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise APIRequestError(
            f"API 返回结构异常，完整响应为: {json.dumps(data, ensure_ascii=False)}"
        ) from exc


def extract_json_object(text: str) -> dict[str, Any]:
    """Try to parse a JSON object from raw model output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("未能在 Node 3 的输出中找到 JSON 对象。")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("Node 3 输出了内容，但 JSON 仍然无法解析。") from exc


def build_node_1_messages(question: str) -> list[dict[str, str]]:
    """Messages for the radical proposal node."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT_NODE_1},
        {"role": "user", "content": f"争议性问题：\n{question}"},
    ]


def build_node_2_messages(question: str, radical_answer: str) -> list[dict[str, str]]:
    """Messages for the conservative rebuttal node."""
    user_content = f"""
用户原始问题：
{question}

激进派方案：
{radical_answer}

请基于以上内容，给出保守派反驳。
""".strip()

    return [
        {"role": "system", "content": SYSTEM_PROMPT_NODE_2},
        {"role": "user", "content": user_content},
    ]


def build_node_3_messages(
    question: str,
    radical_answer: str,
    conservative_answer: str,
) -> list[dict[str, str]]:
    """Messages for the judge node."""
    user_content = f"""
用户原始问题：
{question}

Node 1 - 激进派方案：
{radical_answer}

Node 2 - 保守派反驳：
{conservative_answer}

请严格按照 system prompt 中的 JSON Schema 输出最终评估结果。
""".strip()

    return [
        {"role": "system", "content": SYSTEM_PROMPT_NODE_3},
        {"role": "user", "content": user_content},
    ]


def run_debate(question: str) -> dict[str, Any]:
    """Execute the three-node debate flow and return the final JSON result."""
    node_1_output = call_chat_api(build_node_1_messages(question), temperature=0.9)
    print_block("Node 1 | 激进派方案", node_1_output, RED)

    node_2_output = call_chat_api(
        build_node_2_messages(question, node_1_output),
        temperature=0.5,
    )
    print_block("Node 2 | 保守派反驳", node_2_output, BLUE)

    node_3_raw_output = call_chat_api(
        build_node_3_messages(question, node_1_output, node_2_output),
        temperature=0.2,
    )
    print_block("Node 3 | 裁判原始输出", node_3_raw_output, YELLOW)

    final_json = extract_json_object(node_3_raw_output)
    formatted_json = json.dumps(final_json, ensure_ascii=False, indent=2)
    print_block("Final JSON | 最终评估", formatted_json, GREEN)

    return final_json


def main() -> None:
    """CLI entry point."""
    try:
        validate_config()

        print(f"{MAGENTA}{BOLD}三节点辩论系统已启动{RESET}")
        question = input(f"{CYAN}请输入一个争议性问题：{RESET}").strip()

        if not question:
            print(f"{YELLOW}未输入问题，程序已退出。{RESET}")
            sys.exit(0)

        run_debate(question)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}用户中断执行。{RESET}")
        sys.exit(1)
    except ConfigError as exc:
        print(f"{YELLOW}配置错误：{exc}{RESET}")
        sys.exit(1)
    except APIRequestError as exc:
        print(f"{RED}API 调用失败：{exc}{RESET}")
        sys.exit(1)
    except ValueError as exc:
        print(f"{RED}结果解析失败：{exc}{RESET}")
        sys.exit(1)
    except Exception as exc:
        print(f"{RED}发生未预期错误：{exc}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
