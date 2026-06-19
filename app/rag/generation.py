"""생성 (generation) — 로컬 LLM(Ollama) + 출처 명시. [delegate]

검색된 청크로 프롬프트를 증강 → Ollama HTTP(/api/generate) → 출처 박힌 답.
에어갭: settings.ollama_host 는 사내/로컬. 외부 LLM API 금지.
환각 억제: 컨텍스트에 근거 없으면 "모른다"고 답하게 지시(M4에서 강화).
"""

from __future__ import annotations

import httpx

from app.config import settings

_SYSTEM = (
    "당신은 사내 문서 기반 질의응답 어시스턴트입니다. "
    "아래 '컨텍스트'에 있는 내용만 근거로 한국어 존댓말로 답하세요. "
    "근거로 삼은 출처를 문장 끝에 [번호] 형식으로 표기하세요. "
    "컨텍스트에 근거가 없으면 추측하지 말고 "
    "'제공된 문서에서 찾을 수 없습니다'라고 답하세요."
)


def _format_contexts(contexts: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(contexts, start=1):
        source = c.get("metadata", {}).get("source", "unknown")
        blocks.append(f"[{i}] (출처: {source})\n{c['chunk']}")
    return "\n\n".join(blocks)


def generate(query: str, contexts: list[dict]) -> dict:
    prompt = (
        f"{_SYSTEM}\n\n"
        f"# 컨텍스트\n{_format_contexts(contexts)}\n\n"
        f"# 질문\n{query}\n\n# 답변\n"
    )
    resp = httpx.post(
        f"{settings.ollama_host}/api/generate",
        json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    answer = resp.json()["response"].strip()

    sources = [
        {
            "n": i,
            "id": c["id"],
            "source": c.get("metadata", {}).get("source", "unknown"),
        }
        for i, c in enumerate(contexts, start=1)
    ]
    return {"answer": answer, "sources": sources}
