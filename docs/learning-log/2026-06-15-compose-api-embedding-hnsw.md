# compose api 서비스 · healthcheck · 임베딩/HNSW · init_db.sql

- **날짜:** 2026-06-15
- **단계:** M1 (에어갭 RAG MVP)
- **모드:** reviewer(api·init_db.sql 작성 검토) · tutor(임베딩·HNSW 바닥부터) · quiz(인출) · delegate(env 배선) · coach(기동 검증)

## 한 줄 흐름

compose에 `api` 서비스를 직접 작성하며 build/healthcheck/환경변수 주입을 닫고, `init_db.sql`을
완성하려다 **벡터 차원 = 임베딩 모델이 정하는 계약**이라는 의존성에 부딪혀 임베딩·유사도·HNSW를
바닥부터 세웠다. RAG 파이프라인(청킹→임베딩→벡터→pgvector→HNSW 검색) 전체가 한 줄로 꿰였고,
BGE-M3(1024차원)로 모델을 확정해 SQL을 마무리했다. 부수적으로 learning-mode 스킬에 "개념 문서"
규칙과 존댓말 규칙을 추가하고 개념 문서 2건을 남겼다.

## 헷갈림 → 교정 궤적  ★핵심

| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| `depends_on`만으로 기동 순서 충분? | (떡밥) | `depends_on`은 "컨테이너 시작"까지만 보장. "연결 받을 준비"는 `condition: service_healthy` + 상대 서비스의 `healthcheck` 필요 |
| healthcheck `test` 형태 `["CMD", "pg_isready -U ..."]` | 공백 포함 문자열을 통째로 넣음 | exec form은 **각 원소가 argv 토큰**. 통짜 문자열은 "그 이름의 실행파일"을 찾다 실패. `["CMD", "a","b"]`로 쪼개거나 `["CMD-SHELL", "a b"]`(쉘이 파싱) |
| ollama healthcheck `["CMD","ollama list"]` | 같은 통짜 실수 반복 | 동일 함정. `["CMD","ollama","list"]`로 토큰 분리 |
| `environment:` vs `env_file:` 선택 근거 | "env 파일이 **이미지 내부로** 흘러간다" | env_file은 **런타임 주입**(이미지에 안 박힘). 진짜 이유는 **범위(화이트리스트)** — env_file은 .env 전부 주입, environment는 나열한 것만. `COPY app` vs `COPY .`과 같은 논리 |
| 서비스별 env 파일로 쪼개면 env_file 안전? | "주입해도 문제 없나?" | 맞음. 파일 단위 화이트리스트로 복원됨. 단 공유 시크릿(DB비번) **중복→drift** 트레이드오프 |
| `VECTOR(EMBEDDING_DIM)` | SQL에 변수 placeholder를 그대로 씀 | SQL 파일은 `${}` 치환 안 함(compose와 다른 층위). **진짜 숫자**(1024) 박아야 함 |
| 벡터 차원 N은 어디서? | (막힘 — 임베딩 지식 0) | **임베딩 모델이 정한다.** 모델 미선정→N 모름→테이블 못 만듦. 이게 M1 숨은 의존성 |
| 임베딩 출력 (퀴즈 Q5) | "텍스트를 **청크로** 변환" | **임베딩 출력 = 벡터(점)**. 청킹은 자르는 전처리(임베딩의 입력). "청크는 입력, 벡터는 출력" |
| `VECTOR(1024)`에 768 넣으면? | "유사도가 다르게 나옴" | **INSERT 거부 에러.** 길이 다른 벡터는 거리 정의 자체가 불성립 → pgvector 하드 제약. "틀린 결과"가 아니라 "거부" |
| HNSW 비유→실제 값 | 비유가 안 잡힘 | 2D 좌표·실제 거리로 greedy walk(9.92→7.38→4.30→0.71 단조감소) + 계층(급행/완행) 시연 후 잡힘 |
| `CREATE EXTENSION/TABLE IF NOT EXISTS` 위치 | `CREATE EXTENSION vector IF NOT EXISTS` (이름 뒤) | **이름 *앞*** 이 규칙. 인덱스 줄은 맞게 써놓고 두 줄만 틀림 → 자기 정답 폼과 비교해 교정 |
| 테이블/컬럼 명명 | 테이블 `documents` + 컬럼 `chunks` | 한 행=청크 하나 → 테이블 `chunks`, 본문 컬럼 `chunk`(단수)로 스왑 |

## 다룬 개념

| 개념 | 한 줄 핵심 |
|---|---|
| `build:` (context/dockerfile) | context=데몬에 보내는 폴더(COPY 기준), dockerfile=그중 읽을 레시피 경로 |
| healthcheck | 컨테이너 안에서 주기 실행하는 `test` 명령의 exit 0/비0으로 health 판정 |
| `service_healthy` | depends_on이 상대 healthcheck 통과까지 기동 보류 |
| CMD vs CMD-SHELL | exec form=토큰 직접 실행(분리 필수) / shell form=`/bin/sh -c`가 한 줄 파싱 |
| environment vs env_file | 둘 다 런타임 주입. environment=화이트리스트(나열만), env_file=파일 전부 |
| 청킹 | 문서를 작은 조각으로 자르는 전처리. 의미 선명도↑ + 검색 정밀도·출처 |
| 임베딩 | 텍스트→고정 길이 벡터(N차원 점). N은 모델이 결정 |
| 유사도/거리척도 | 가까운 점=의미 비슷. 코사인(`<=>`)/L2(`<->`)/내적(`<#>`) |
| 차원 = 계약 | 컬럼 `VECTOR(N)` 고정. 불일치 시 INSERT 거부(거리 불성립) |
| HNSW | 그래프 greedy 탐색 + 계층(급행/완행). 전부 안 보고 빠르게 근접 |
| ANN/approximate | 한 경로만 탐험→가끔 진짜 1등 놓침. recall로 측정, 속도와 트레이드오프 |
| 연산자 클래스 일치 | 인덱스 `vector_cosine_ops` ↔ 검색 `<=>` 일치해야 인덱스 활용. 불일치→full scan 폴백 |
| BGE-M3 | 로컬·에어갭·한국어 임베딩, 1024차원, MIT. M1 확정(M2 벤치/교체) |

## 막힌 곳 → 해결

- **healthcheck test 통짜 문자열 (2건):** `["CMD", "pg_isready -U ..."]`/`["CMD","ollama list"]` → 실행파일을 못 찾아 영원히 unhealthy → exec form 토큰 분리 또는 CMD-SHELL로 교정.
- **init_db.sql 의존성 막힘:** `VECTOR(EMBEDDING_DIM)`을 못 채움 → 원인은 "임베딩 모델 미선정→차원 미정" → 웹 조사로 후보(BGE-M3/e5/Qwen3/ko-sroberta) 비교 후 BGE-M3(1024) 확정 → `.env`·`config.py`·SQL 동기화.
- **IF NOT EXISTS 위치 오류:** 이름 뒤에 둬 문법 에러 → 본인이 맞게 쓴 인덱스 줄과 비교해 이름 앞으로 교정.

## 퀴즈 결과

**5/6 통과.** 오늘 도입 개념(healthcheck·CMD·HNSW·연산자 일치) 탄탄. 유일 약점 = 청크 vs 임베딩 출력.

| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| Q1 build/context | context=대상폴더, dockerfile=빌드 레시피, copy는 context 내부 | 정확 | ✅ |
| Q2 healthcheck | healthcheck test 필요 + 실제 통신 가능 상태 확인 | 정확 | ✅ |
| Q3 CMD vs CMD-SHELL | CMD는 통짜라 못 찾음, 분리 필요 / CMD-SHELL은 한 줄 실행 | 정확(쉘이 파싱) | ✅ |
| Q4 env 화이트리스트 | 불필요 변수 유입 방지, COPY ./COPY app 논리 | 정확 | ✅ |
| Q5 임베딩 출력 | "텍스트를 청크로 변환" | 임베딩→벡터(청크 아님) | ❌ |
| Q6 HNSW/연산자 | 정답 근접한 것 취함(트레이드오프) / 코사인 그래프 못 씀 | 정확 | ✅ |

**퀴즈 뱅크 갱신:** A#3 멱등성 → ✅ 해결(init_db.sql 적용으로 입증). 신규 A#4 = 임베딩 출력(❌, 재출제). B3 = ivfflat vs hnsw, B4 = HNSW recall 파라미터(대기).

## 메타 (학습 도구 개선)

- **learning-mode 스킬에 "개념 문서" 규칙 추가:** tutor 중 이해도 0 감지 시, 가르친 뒤 **먼저 묻고** `docs/concepts/<주제>.md`(날짜 없는 살아있는 레퍼런스)로 정리. learning-log(과정)와 구분.
- **존댓말 규칙:** CLAUDE.md 절대 제약 #3 + 메모리에 "항상 존댓말, 반말 금지" 명시.
- **개념 문서 2건 작성:** `docs/concepts/embedding-similarity.md`, `docs/concepts/rag-pipeline.md`.

## 다음 액션

- [ ] `docker compose up --build` 기동 검증 마무리 — `/health` 200 + db·ollama·api 모두 healthy 확인 (이번 세션 진행 중)
- [ ] ollama healthcheck `ollama list`가 "서버 준비"를 충분히 판정하는지 실제 확인 (포트 응답 방식 비교)
- [ ] BGE-M3 가중치 에어갭 번들 전략 (1회 다운로드→이미지/볼륨) 설계
- [ ] `app/rag/chunking.py`·`embedding.py`·`retrieval.py` 살 붙이기 — 검색은 `<=>`(코사인) 연산자로 (인덱스와 일치)
- [ ] `/ingest`·`/query` 라우트 (`app/api/`)
