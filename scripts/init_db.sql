-- Onseal M1 — pgvector 초기화
-- [reviewer 모드 — 당신이 작성, 제가 검토]
--
-- 여기서 결정/작성할 것:
--   1) CREATE EXTENSION vector;
--   2) 청크 테이블: 본문 + 메타데이터(출처) + vector(EMBEDDING_DIM)
--   3) 유사도 인덱스 (ivfflat / hnsw) — retrieval.py 의 연산자와 일치
--
-- TODO: 직접 작성.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks  (
    id SERIAL PRIMARY KEY,
    chunk TEXT NOT NULL,
    metadata JSONB NOT NULL,
    embedding VECTOR(1024) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);




