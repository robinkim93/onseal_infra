"""pgvector 연결 + 스키마 헬퍼.

[reviewer 모드 — 당신이 구현, 제가 검토]

결정해야 할 것:
  - 연결 방식(커넥션 풀 vs 단일) — M1은 단순해도 됨
  - documents/chunks 테이블 설계: 본문, 메타데이터(출처), vector(EMBEDDING_DIM)
  - 인덱스 생성 시점 (scripts/init_db.sql 과 역할 분담)

TODO: 직접 구현.
"""


def get_connection():
    raise NotImplementedError
