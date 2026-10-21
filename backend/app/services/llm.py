"""LLM 客户端：OpenAI 兼容协议（GLM / Qwen / DeepSeek / Kimi 均可），强制 JSON 输出。"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .. import config


class LLMError(RuntimeError):
    """模型调用失败。"""


class LLMUnavailable(LLMError):
    """未配置模型或显式关闭（演示模式）。"""


def extract_json(text: str) -> dict[str, Any]:
    """从模型输出里提取 JSON（兼容 ```json 代码块、前后废话）。"""
    if not text or not text.strip():
        raise LLMError("模型返回为空")
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(cleaned[start:end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as exc:
            raise LLMError(f"JSON 解析失败：{exc}") from exc
    raise LLMError("模型未返回合法 JSON")


def _endpoint() -> str:
    base = config.LLM_BASE_URL.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


async def chat_json(system: str, user: str, max_tokens: int = 2000) -> dict[str, Any]:
    """调用模型并返回解析后的 JSON，JSON 不合法时自动重试一次。"""
    if not config.llm_enabled():
        raise LLMUnavailable("未配置 LLM_API_KEY，使用演示模式")

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT_S) as client:
                resp = await client.post(_endpoint(), headers=headers, json=payload)
            if resp.status_code >= 400:
                raise LLMError(f"模型接口返回 HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return extract_json(content)
        except (httpx.HTTPError, LLMError, KeyError, IndexError) as exc:
            last_error = exc
            if attempt == 0:
                payload["messages"].append({
                    "role": "user",
                    "content": "注意：上一次输出不是合法 JSON。请只输出一个 JSON 对象，不要加解释或代码块。",
                })
                continue
    raise LLMError(f"模型调用失败：{last_error}")


def model_label() -> str:
    return f"{config.LLM_MODEL}（演示模式）" if not config.llm_enabled() else config.LLM_MODEL
