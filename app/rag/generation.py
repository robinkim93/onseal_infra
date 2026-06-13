"""생성 (generation) — 로컬 LLM(Ollama) + 출처 명시.

[reviewer 모드 — 당신이 구현, 제가 검토]

검색된 청크로 프롬프트를 증강해 Ollama에 보내고, 출처가 박힌 답을 만든다.
M1 산출물의 핵심: "출처 명시 답변". 결정해야 할 것:
  - 컨텍스트를 프롬프트에 어떻게 넣을지(포맷·길이 제한)
  - 출처(문서명/청크 id)를 답변에 어떻게 강제할지
  - 근거 없을 때 "모른다"고 하게 만드는 장치 (환각 억제 — M4 복선)

⚠️ 에어갭: OLLAMA_HOST 는 사내/로컬. 외부 LLM API 금지.

TODO: 직접 구현.
"""


def generate(query: str, contexts: list[dict]) -> dict:
    raise NotImplementedError
