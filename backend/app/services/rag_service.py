"""轻量 RAG：文档切片、向量/关键词检索、基于检索结果的问答。"""
from __future__ import annotations

import json
import math
import re
from typing import Any

import httpx

from .. import config, prompts
from ..models import DocAskResponse, DocCitation
from . import llm


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    """按字符长度切片，尽量在句末/换行处断开。"""
    size = size or config.RAG_CHUNK_SIZE
    overlap = overlap or config.RAG_CHUNK_OVERLAP
    text = re.sub(r"\r\n?", "\n", text or "").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + size, length)
        if end < length:
            window = text[start:end]
            for sep in ("\n", "。", "！", "？", "；", ". "):
                pos = window.rfind(sep)
                if pos > size * 0.5:
                    end = start + pos + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """调用百炼 Embedding 模型（OpenAI 兼容 /embeddings）。"""
    if not texts or not config.llm_enabled():
        raise llm.LLMUnavailable("未启用模型")
    url = config.LLM_BASE_URL.rstrip("/")
    if not url.endswith("/embeddings"):
        url += "/embeddings"
    payload = {"model": config.EMBED_MODEL, "input": texts[:64], "encoding_format": "float"}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
    if resp.status_code >= 400:
        raise llm.LLMError(f"Embedding 接口 HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json().get("data", [])
    ordered = sorted(data, key=lambda item: item.get("index", 0))
    vectors = [item.get("embedding") or [] for item in ordered]
    if len(vectors) != len(texts[:64]):
        raise llm.LLMError("Embedding 返回数量不匹配")
    return vectors


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def _char_bigrams(text: str) -> set[str]:
    text = re.sub(r"\s+", "", text)
    return {text[i:i + 2] for i in range(max(1, len(text) - 1))}


def _keyword_score(question: str, chunk: str) -> float:
    q = _char_bigrams(question)
    c = _char_bigrams(chunk)
    if not q or not c:
        return 0.0
    return len(q & c) / math.sqrt(len(q) * len(c))


def _rank_chunks(question: str, chunks: list[dict[str, Any]], q_embedding: list[float] | None) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        text = chunk.get("text", "")
        if q_embedding and chunk.get("emb"):
            score = _cosine(q_embedding, chunk["emb"])
        else:
            score = _keyword_score(question, text)
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored]


def _table_context(tables: list[dict[str, Any]]) -> str:
    if not tables:
        return "（没有从文档中提取到表格）"
    lines = []
    for table in tables:
        lines.append(
            f"- 「{table.get('name')}」：{table.get('rows')} 行 × {table.get('cols')} 列，"
            f"已保存为可分析数据集（dataset_id={table.get('dataset_id')}）"
        )
    return "\n".join(lines)


def fallback_answer(question: str, chunks: list[dict[str, Any]]) -> tuple[str, list[DocCitation]]:
    if not chunks:
        return "文档中没有检索到与问题相关的内容。", []
    top = chunks[0]
    answer = (
        "（演示模式，未接入大模型）根据文档中检索到的内容：\n"
        f"{top.get('text', '')[:400]}\n\n"
        "配置 LLM_API_KEY 后，将基于检索结果生成更完整的归纳回答。"
    )
    citations = [DocCitation(index=1, text=top.get("text", ""))]
    return answer, citations


async def answer_question(doc: dict[str, Any], question: str,
                          history: list[Any] | None = None) -> DocAskResponse:
    started = __import__("time").perf_counter()
    chunks: list[dict[str, Any]] = json.loads(doc.get("chunks_json") or "[]")
    tables: list[dict[str, Any]] = json.loads(doc.get("tables_json") or "[]")

    if not chunks:
        return DocAskResponse(
            ok=False, question=question,
            answer="这份文档没有可检索的文字内容，可能只包含图片/表格。可以把它提取出的表格作为数据集来分析。",
            error="no_text", model=llm.model_label(),
            elapsed_ms=int((__import__("time").perf_counter() - started) * 1000),
            mock=not config.llm_enabled(),
        )

    q_embedding = None
    if config.llm_enabled() and any(chunk.get("emb") for chunk in chunks):
        try:
            q_embedding = (await embed_texts([question]))[0]
        except Exception:  # noqa: BLE001 - 检索降级为关键词
            q_embedding = None

    ranked = _rank_chunks(question, chunks, q_embedding)
    top_chunks = ranked[: config.RAG_TOP_K]
    context_lines = []
    for index, chunk in enumerate(top_chunks, start=1):
        context_lines.append(f"[{index}] {chunk.get('text', '')}")
    context = "\n\n".join(context_lines)

    if not config.llm_enabled():
        answer, citations = fallback_answer(question, top_chunks)
        return DocAskResponse(
            ok=True, question=question, answer=answer, citations=citations,
            model="演示模式", mock=True,
            elapsed_ms=int((__import__("time").perf_counter() - started) * 1000),
        )

    history_text = ""
    if history:
        recent = history[-3:]
        history_text = "\n".join(f"- 用户：{turn.question}" for turn in recent if getattr(turn, "question", None))

    user_prompt = (
        f"文档名称：{doc.get('name')}\n"
        f"文档中提取到的表格：\n{_table_context(tables)}\n\n"
        f"对话历史（可能为空）：\n{history_text or '（无）'}\n\n"
        f"检索到的文档片段：\n{context}\n\n"
        f"用户问题：{question}\n\n"
        "请只输出 JSON：{\"answer\":\"...\",\"used\":[1,2]}，"
        "used 是实际引用的片段编号（1 起），answer 用中文、先给结论后给依据。"
    )
    try:
        data = await llm.chat_json(prompts.RAG_SYSTEM, user_prompt, max_tokens=1200)
        answer = str(data.get("answer", "")).strip()
        used = data.get("used") or []
        citations: list[DocCitation] = []
        seen: set[int] = set()
        for item in used if isinstance(used, list) else []:
            try:
                number = int(item)
            except (TypeError, ValueError):
                continue
            if 1 <= number <= len(top_chunks) and number not in seen:
                seen.add(number)
                citations.append(DocCitation(index=number, text=top_chunks[number - 1].get("text", "")))
        if not citations:
            citations = [DocCitation(index=1, text=top_chunks[0].get("text", ""))]
        if not answer:
            raise llm.LLMError("模型未返回回答")
        return DocAskResponse(
            ok=True, question=question, answer=answer, citations=citations,
            model=config.LLM_MODEL, mock=False,
            elapsed_ms=int((__import__("time").perf_counter() - started) * 1000),
        )
    except llm.LLMError:
        answer, citations = fallback_answer(question, top_chunks)
        return DocAskResponse(
            ok=True, question=question, answer=answer, citations=citations,
            model="演示模式", mock=True,
            elapsed_ms=int((__import__("time").perf_counter() - started) * 1000),
        )
