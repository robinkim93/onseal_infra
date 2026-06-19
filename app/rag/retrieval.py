"""검색 (retrieval) — pgvector 코사인 유사도 top-k. [delegate]

질문을 임베딩 → `<=>`(코사인 거리) 오름차순으로 가장 가까운 청크 top-k.
연산자 `<=>` 는 init_db.sql 의 hnsw(vector_cosine_ops) 인덱스와 일치해야
인덱스를 탄다. 임베딩이 normalize 돼 있어 코사인 거리로 비교한다.
거리(distance)는 0에 가까울수록 유사(0=동일 방향).
"""

from __future__ import annotations

from app.db.pgvector import get_connection, vector_literal
from app.rag.embedding import embed


def search(query: str, k: int = 5) -> list[dict]:
    qvec = embed([query])[0]
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, chunk, metadata, embedding <=> %s::vector AS distance
            FROM chunks
            ORDER BY distance
            LIMIT %s
            """,
            (vector_literal(qvec), k),
        )
        rows = cur.fetchall()
    return [
        {"id": r[0], "chunk": r[1], "metadata": r[2], "distance": r[3]}
        for r in rows
    ]
