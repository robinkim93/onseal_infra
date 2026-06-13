# M1 착수 — docker-compose로 에어갭 스택 뼈대 세우기 (db · ollama)

- **날짜:** 2026-06-13
- **단계:** M1 (에어갭 RAG MVP)
- **모드:** delegate(스캐폴딩) → tutor(compose 개념) → reviewer(작성 검토) → quiz(인출 테스트)

## 한 줄 흐름

M1 산출물을 "뼈대는 위임 / RAG 코어는 직접 작성(reviewer)"으로 분해한 뒤, 첫 산출물로
`docker-compose.yml`을 골라 `db`·`ollama` 두 서비스를 직접 작성→검토→검증까지 한 바퀴 돌렸다.
compose가 처음이라 tutor로 머릿속 모델(네트워크/DNS·에어갭)부터 잡고 들어갔다.

## 헷갈림 → 교정 궤적  ★핵심

| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| 왜 `docker run` 3번이 아니라 compose? | "서로의 호출점을 이어주는 것" (방향만) | compose가 서비스들을 한 가상 네트워크에 묶고 서비스명을 DNS로 등록 → 이름 기반 통신 |
| **에어갭(air-gap)이 뭔지 아예 몰랐음** | (모름) | 외부 인터넷과 단절, 전 과정 사내망 완결. 규제 산업의 핵심 셀링포인트 |
| 외부 주소를 호출하면 에어갭이 깨지나, 막으려면? | "compose 내부 도메인이 아니면 에러 띄우게" | 정확히 `internal: true` 네트워크 = 외부 경로 자체가 없는 망 (이름도 모르고 메커니즘을 유도해냄) |
| pgvector가 뭔지 | "PG의 vector DB를 활용하는 것" (별도 DB로 오해) | 별도 DB 아님. Postgres **확장** — vector 타입 + 유사도 연산자/인덱스를 추가 |
| ollama volume을 어디에 걸지 | `/usr/lib/ollam` (라이브러리 경로 + 오타) | 모델은 `/root/.ollama`에 저장. 틀린 경로면 재생성 시 모델 증발 |
| **왜 하필 `/root/.ollama`인지** | (경로는 찾았으나 이유 모름) | ollama는 `$HOME/.ollama`에 저장 + 컨테이너가 root 실행 → `$HOME=/root` |
| init_db.sql 수정이 왜 반영 안 되나 (퀴즈) | "데이터 디렉토리가 안 비어서" ✅ + 명령은 모름 | `docker compose down -v` (volume 삭제 → 다음 up에서 재init). `-v`=데이터 전삭제 |
| `db` 이름이 어떻게 컨테이너로 연결되나 (퀴즈) | "DNS처럼 매핑" ✅ + 뭘 까는지는 모름 | compose가 **기본 네트워크 자동 생성 + 내장 DNS 서버** → 서비스명을 현재 IP로 실시간 번역 |

## 다룬 개념

| 개념 | 한 줄 핵심 |
|---|---|
| compose의 가치 | 다중 컨테이너를 한 가상 네트워크로 묶고 서비스명을 DNS 등록 → 이름 기반 통신 |
| 에어갭(air-gap) | 외부 네트워크 단절, 전 과정 사내망 완결. 규제 산업 셀링포인트 |
| `internal: true` | 외부로 나가는 경로가 없는 Docker 네트워크 (에어갭의 네트워크 레벨 구현, M3) |
| pgvector | Postgres 확장. vector 타입 + 유사도 연산자(`<=>`)·인덱스. 메타+벡터 단일 DB 통합 |
| 이미지 태그 핀 | `latest` 금지·메이저 명시. 이유=재현성. 에어갭 어플라이언스 버전 드리프트 방지 |
| 호스트 vs 컨테이너 FS | 격리됨. 경로가 두 세계로 나뉨 |
| 바인드 마운트 | 호스트 특정 파일/경로를 컨테이너에 비춤(`호스트:컨테이너`). 내가 편집하는 코드·설정용 |
| named volume | 도커 관리 영속 저장소. 내가 손 안 대는 DB 데이터·모델 가중치용 |
| entrypoint | 컨테이너 부팅 자동 실행 로직. postgres는 `/docker-entrypoint-initdb.d/`를 부팅 시 자동 실행 |
| init 실행 조건 | **데이터 디렉토리가 빌 때만.** 안 비면 스킵 → 수정 init이 안 도는 함정 |
| 멱등성(idempotent) | init은 `CREATE ... IF NOT EXISTS`로. M2 IaC 복선 |
| 시크릿 관리 | compose에 평문 비번 = git 히스토리 영구 노출(오픈코어=전세계). `.env`+`${}` 주입. M3 복선 |

## 막힌 곳 → 해결

- **백지 블록(compose 첫 작성)** — 시작 자체가 안 됨 → tutor로 최상위 구조(services/volumes) + db 빈칸 스캐폴드 받아 돌파.
- **db 작성 오류 (reviewer 지적)** — (1) `POSTGRES_USER` 누락, (2) 비번 평문 하드코딩 → `${...}` 주입으로 수정.
- **ollama volume 경로 오류** — `/usr/lib/ollam` → "모델 저장 위치"를 직접 찾아 `/root/.ollama`로 수정.
- **검증** — `docker compose up -d db` 후 로그에서 `running /docker-entrypoint-initdb.d/init_db.sql` 확인 = 바인드 마운트→entrypoint→init 고리 연결됨을 입증.

## 퀴즈 결과

**통과** (5문항 중 3 완답 / 2 부분). 약한 고리 둘 다 "개념 오해"가 아닌 "기억의 빈칸" → 오답 뱅크 적립.

| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| Q1 init 수정 미반영: 원인/명령/위험 | 데이터 디렉토리 안 비어서 ✅ / 명령 모름 / 데이터 날아감 ✅ | `docker compose down -v` (volume 삭제→재init), `-v`=데이터 전삭제 | 부분 |
| Q2 db의 두 volume 차이 | 위=영속 데이터, 아래=내 호스트 파일 마운트 | named volume vs bind mount | ✅ |
| Q3 `db` 이름→컨테이너 연결, compose가 까는 것 | "DNS처럼 매핑" / 뭘 까는지 모름 | 기본 네트워크 자동생성 + 내장 DNS 서버 | 부분 |
| Q4 pgvector 정체 + 에어갭 이점 | 확장 기능, vector 컬럼, 단일 DB | 정답(연산자·인덱스까지 보강) | ✅ |
| Q5 태그 핀 이유(에어갭 배포) | 버전 드리프트로 설정·코드 틀어짐 | 정답(=재현성) | ✅ |

**퀴즈 뱅크 적립:**
- A큐(오답): Q1·Q3 → `#1·#2` (맞힐 때까지 재출제)
- B큐(얕게 다룬 중요 개념): **멱등성**(1회 언급, M2 복선), **`internal:true`**(개념만) → `B1·B2` (다음 학습 퀴즈에 추가 검증)

## 다음 액션

- [ ] `api` 서비스 작성 (`build:`로 `docker/Dockerfile` 지정, `depends_on`, 포트)
- [ ] `docker/Dockerfile` 작성 (requirements.txt 활용) — 처음이면 tutor
- [ ] `depends_on`만으로 기동 순서가 충분한지 검토 (healthcheck 떡밥)
- [ ] init_db.sql 실제 내용: `CREATE EXTENSION vector` + 청크 테이블 + 인덱스 (reviewer)
