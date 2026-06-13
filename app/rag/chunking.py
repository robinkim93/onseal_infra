"""문서 청킹 (chunking).

[reviewer 모드 — 당신이 구현, 제가 검토]

원문 텍스트를 임베딩 단위로 쪼갠다. 결정해야 할 것:
  - 청크 크기 / 오버랩 — 너무 크면 검색 정밀도↓, 너무 작으면 문맥 손실
  - 경계 기준 — 문자 수? 토큰 수? 문단/문장 경계 보존?
  - 세무 문서 특성(조항·표·예규 번호)을 어떻게 살릴지

TODO: 직접 구현. 검토 요청 시 reviewer 모드로 봐줌.
"""


def chunk_text(text: str) -> list[str]:
    raise NotImplementedError
