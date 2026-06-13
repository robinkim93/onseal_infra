"""검색 (retrieval) — pgvector 유사도 쿼리.

[reviewer 모드 — 당신이 구현, 제가 검토]

질문 임베딩 → 가장 가까운 청크 top-k. 결정해야 할 것:
  - 유사도 지표: cosine / L2 / inner product — pgvector 연산자(<=>, <->, <#>)와 매핑
  - top-k 값
  - 인덱스 종류(ivfflat / hnsw)와 정확도-속도 트레이드오프

TODO: 직접 구현.
"""


def search(query: str, k: int = 5) -> list[dict]:
    raise NotImplementedError
