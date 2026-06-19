"""pgvector 연결 + INSERT 헬퍼. [delegate — DB 플럼빙]

M1은 단순하게: 호출마다 단일 연결을 연다(커넥션 풀 없음 — M2에서 도입).
embedding 은 vector(EMBEDDING_DIM), metadata(출처)는 JSONB.
스키마/인덱스 생성은 scripts/init_db.sql 이 담당(여기선 적재만).
"""

from __future__ import annotations

import json

import psycopg

from app.config import settings


def get_connection() -> psycopg.Connection:
    """단일 연결을 연다. 호출자가 with 로 닫는다."""
    return psycopg.connect(settings.database_url)


def vector_literal(vec: list[float]) -> str:
    """pgvector 입력 포맷 '[0.1,0.2,...]' 로 직렬화. SQL에서 ::vector 로 캐스팅."""
    return "[" + ",".join(map(str, vec)) + "]"


def insert_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    metadata: dict,
) -> int:
    """한 문서의 청크 + 벡터 + 출처 메타데이터를 적재. 적재 행 수 반환."""
    rows = [
        (chunk, json.dumps(metadata), vector_literal(vec))
        for chunk, vec in zip(chunks, embeddings)
    ]
    with get_connection() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO chunks (chunk, metadata, embedding) "
            "VALUES (%s, %s::jsonb, %s::vector)",
            rows,
        )
        conn.commit()
    return len(rows)
