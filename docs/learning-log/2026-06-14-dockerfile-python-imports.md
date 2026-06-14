# Dockerfile 작성 — 레이어 캐시 · 빌드 컨텍스트 · Python import 경로

- **날짜:** 2026-06-14
- **단계:** M1 (에어갭 RAG MVP)
- **모드:** tutor(Dockerfile 처음) → reviewer(작성 검토) → tutor(Python import 공백) → quiz(인출 테스트)

## 한 줄 흐름

compose의 `api` 서비스가 가리킬 `docker/Dockerfile`을 처음부터 직접 작성했다. "왜 db·ollama는 `image:` 한 줄인데 api만 `build:`가 필요한가"에서 출발해, **레이어 캐시 순서 → 빌드 컨텍스트 → COPY 문법 → Python 모듈/패키지 import 경로**까지 한 줄로 꿰었다. 특히 `CMD`의 모듈 경로(`app.main:app`)와 WORKDIR의 관계에서 Python 패키징 개념 공백이 드러나 tutor로 바닥부터 다시 세웠다.

## 헷갈림 → 교정 궤적  ★핵심

| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| 왜 api만 `build:`가 필요? | "시작 스크립트·OS 이미지·코드 복사·실행이 필요" (방향 정확) | db·ollama는 메인테이너가 OS+SW+실행을 *이미 구운* 완성 이미지. api는 우리 코드라 굽는 레시피(Dockerfile)를 우리가 씀. **+ 의존성 설치(pip)가 빠져 있었음** |
| Dockerfile 단계 순서 | `FROM`→코드 COPY→`pip install`→`CMD`, "코드를 알아야 의존성을 안다" | **틀린 순서.** 의존성 목록은 `requirements.txt` manifest에 이미 있음(코드 불필요). 캐시 때문에 install을 코드 COPY보다 **앞**에 둬야 함 |
| 코드 한 줄 고치면? (위 순서로) | "의존성 설치 또 돈다, 재배포 너무 느림" ✅ | 정확. 레이어 캐시는 **위→아래로 깨짐**: 코드 COPY 무효화 → 그 아래 `pip install`까지 재실행 |
| 정석 순서 도출 | `FROM`→`COPY requirements`→`pip install`→`COPY 코드`→`CMD` ✅ | 정확히 도출. 코드 수정 시 무효화되는 건 마지막 COPY+CMD뿐, 무거운 install은 캐시 생존 |
| 빌드 컨텍스트가 뭔지 | (모름) | `docker build`에 통째로 건네는 폴더. 도커가 압축해 데몬에 전송, **COPY는 컨텍스트 안 파일만 봄**. compose `build: context: .` = 레포 루트 |
| `COPY . /app`이 끌어오는 범위 | (보안 함의 모름) | `.`=컨텍스트 전부(.env·.git 포함). `.env`가 이미지에 박히면 `docker save`/`history`로 평문 비번 추출 → 오픈코어=전세계 노출. `.dockerignore`로 차단 |
| 전체 말고 `app` 폴더만 COPY? | "그래도 되지 않나?" (본능 정확) | **더 나은 설계.** 화이트리스트(`COPY app`)=secure by default. 블랙리스트(`COPY .`+ignore)는 새 비밀파일 누락 위험 |
| `COPY app /app/app`의 앞 `app` 의미 | (헷갈림) | `COPY <출처> <목적지>`. 앞=로컬 컨텍스트 경로, 뒤=이미지 안 경로. 이름이 우연히 겹쳤을 뿐 무관 |
| **CMD 모듈 경로 `main:app` vs `app.main:app`** | "코드를 알아야…" → 처음엔 `main:app`로 작성 | **WORKDIR `/app`에서 `/app/app/main.py`까지 점 경로 = `app.main`.** `main:app`은 `/app/main.py`를 찾아 `ModuleNotFoundError` |
| **Python module/package 자체** | "파이썬 잘 모름, 더 설명 필요" | `.py` 파일=**모듈**, `__init__.py` 든 폴더=**패키지**. 점(`.`)으로 패키지→모듈 길찾기. import 경로 맨 앞=WORKDIR에서 보이는 최상위 패키지 |
| WORKDIR `/app/app`로 바꾸면? | (보너스 퀴즈에서) 이미 app 안이라 `app.config`=`/app/app/app/config.py` 찾아 에러 ✅ | **정확.** WORKDIR가 패키지 *안*으로 들어가면 `app`이 안 보여 `from app.xxx` 줄줄이 터짐. WORKDIR는 패키지 *밖*(루트)에 둬야 함 |
| 중첩 패키지 import (`api`) | "api.config로?" → "app.api.config / app.config 둘 다 OK?" | **정확히 도달.** 점 경로 맨 앞은 최상위(`app`) 고정, 중첩은 마디 추가. 같은 `config.py`도 전체 점 경로 다르면 다른 모듈, 충돌 없음 |

## 다룬 개념

| 개념 | 한 줄 핵심 |
|---|---|
| `image:` vs `build:` | 완성 이미지를 가져다 쓰면 image, 우리 코드를 구우면 build(+Dockerfile) |
| 레이어 캐시 | 명령어 한 줄=레이어 하나, 캐시됨. 입력 바뀐 줄과 **그 아래 전부** 재실행(위→아래) |
| 캐시 최적 순서 | `requirements.txt`만 먼저 COPY→install→그 다음 코드 COPY. 코드 수정이 install 캐시를 안 깸 |
| `--no-cache-dir` | pip 캐시 안 남겨 이미지 용량↓ (에어갭 이미지 슬림화) |
| 태그 핀 | `python:3.11.15-slim` 패치까지 고정 = 재현성 (전 세션 교훈 적용) |
| 빌드 컨텍스트 | `docker build`에 넘기는 폴더. COPY는 이 안만 봄. `context: .`=레포 루트 |
| `.dockerignore` | 컨텍스트 루트에 위치. `.env`·`.git`·`__pycache__` 제외 = 시크릿 누출·빌드 비대 방지 |
| 화이트리스트 COPY | `COPY app`처럼 필요한 것만 = secure by default (블랙리스트보다 안전) |
| `COPY <출처> <목적지>` | 앞=로컬(컨텍스트 기준), 뒤=이미지 안. 이름 겹침은 우연 |
| module / package | 파일=모듈, `__init__.py` 폴더=패키지. 점으로 연결 |
| import 점 경로 | "WORKDIR에서 보이는 최상위 패키지부터 끝까지 점으로 = 모듈의 유일 주소" |
| WORKDIR ↔ import | WORKDIR는 패키지 밖(루트)에. 안으로 들어가면 절대 import(`from app.x`)가 깨짐 |
| `uvicorn 모듈:변수` | `--host 0.0.0.0` 필수(컨테이너 외부 노출). 모듈경로는 WORKDIR 기준 |

## 막힌 곳 → 해결

- **Dockerfile 작성 오류 (reviewer 지적 3건):** (1) `pip install` 줄 끝 잘못 붙은 백틱(`` ` ``) → 제거, (2) `COPY . /app` → `.env` 노출 위험 → `COPY app /app/app` 화이트리스트 + `.dockerignore` 추가, (3) `CMD main:app` → `ModuleNotFoundError` 유발 → `app.main:app`로 수정.
- **Python import 공백:** "파이썬 잘 모름"으로 막힘 → tutor로 module/package·점 경로·WORKDIR 관계를 디렉토리 트리로 시각화해 돌파. 사용자가 보너스(`/app/app` WORKDIR 시 `/app/app/app/config.py` 에러)와 중첩 패키지(`app.api.config` vs `app.config` 무충돌)를 **스스로 도출**.

## 퀴즈 결과

**통과** (7문항 중 6.5 완답). 오늘 Dockerfile·import 개념 탄탄. 유일 빈칸=멱등성.

| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| T1 캐시 순서 이유 | 코드 바뀌면 의존성 설치 계속 함 | 캐시 위→아래 무효화로 install 재실행 | ✅ |
| T2 화이트리스트 보안 + .env 노출 | 민감정보 이미지 포함, docker history로 습득 | 정확(+ save로 레이어 추출 보강) | ✅ |
| T3 `app.main:app` 이유 + 보너스 | /app엔 app·docs 보임, main:app은 못 찾음 / `/app/app/app/config.py` 에러 | 완벽 | ✅✅ |
| A1 init 재반영 명령+위험 (지난 #1) | `down -v`, 데이터 소실 | 정답 — **지난번 못 맞힌 명령 해결** | ✅ |
| A2 서비스명→컨테이너 (지난 #2) | DNS + 내부 네트워크 | 정답 — **지난번 흔들린 것 해결** | ✅ |
| B2 internal:true | 옵션 사용, 컨테이너끼리는 통신 가능 | 정답 — **졸업** | ✅ |
| B1 멱등성 | "잘 모르겠음" | 몇 번 실행해도 끝 상태 동일. `IF NOT EXISTS`=2회차 무동작, 없으면 already exists 에러 | ❌ |

**퀴즈 뱅크 갱신:**
- A큐: #1·#2 → **✅ 해결**(2026-06-14). B2 → **✅ 졸업**.
- 신규 오답: **멱등성** → A큐 `#3`(❌, 다음 퀴즈 재출제).

## 다음 액션

- [ ] `api` 서비스 작성 (`build: context/dockerfile`, `ports`, `depends_on`) — reviewer
- [ ] **환경변수 런타임 주입** 결정: `.env`를 이미지에서 뺐으니 컨테이너 api는 DB비번·OLLAMA_HOST를 어떻게 받나 (`env_file:` vs `environment:`) — 떡밥
- [ ] `depends_on`만으로 기동 순서 충분한지 (healthcheck 떡밥)
- [ ] `init_db.sql` 실제 내용: `CREATE EXTENSION vector` + 청크 테이블 + 인덱스 (reviewer, **멱등성 적용**)
- [ ] 빌드·기동 검증: `docker compose up --build` 후 `/health` 응답 확인
