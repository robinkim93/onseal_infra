# Onseal

세무·회계 사무소용 **에어갭(air-gapped) 온프레미스 컴플라이언스 RAG 어플라이언스**.
데이터가 외부로 나가지 않는 사내 문서 질의응답 시스템.

> 상세 기획: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)

## 현재 단계: M1 — 에어갭 RAG MVP

문서 인제스트 → 청킹 → 로컬 임베딩 → pgvector → 검색 → 로컬 LLM(출처 포함),
`docker-compose` 원클릭 기동, 외부 네트워크 콜 0.

## 구조

```
app/
  main.py        FastAPI 진입점
  config.py      .env 설정
  api/           라우트 (/ingest, /query, /health)
  rag/           청킹 · 임베딩 · 검색 · 생성
  db/            pgvector 연결/스키마
scripts/init_db.sql   pgvector 초기화
docker/               Dockerfile
sample_docs/          테스트용 세무 문서
```

## 설치 & 실행

> TODO(M1 완료 시 작성): `docker-compose` 기동 절차, 모델 사전 주입(에어갭), 인제스트/질의 예시.

```bash
cp .env.example .env
# docker compose up -d   # (compose 작성 후)
```
