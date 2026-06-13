"""임베딩 (embedding) — 로컬 모델만.

[reviewer 모드 — 당신이 구현, 제가 검토]

청크 → 벡터. 결정해야 할 것:
  - 어떤 로컬 한국어 임베딩 모델? (.env EMBEDDING_MODEL)
  - 출력 차원(EMBEDDING_DIM)이 pgvector 스키마와 일치하는지
  - 정규화(normalize) 여부 — 유사도 지표 선택과 직결

⚠️ 에어갭: 런타임에 모델을 외부에서 받아오지 않는다. 가중치는 미리 주입.

TODO: 직접 구현.
"""


def embed(texts: list[str]) -> list[list[float]]:
    raise NotImplementedError
