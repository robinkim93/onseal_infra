# 학습 방향 재조정(build→operate) · 에어갭 모델 패키징 실증 · chunk 경계조건

- **날짜:** 2026-06-17
- **단계:** M1 (에어갭 RAG MVP)
- **모드:** reviewer(chunk_text·Dockerfile/compose) · 메타(학습 방향 재조정) · tutor(에어갭 패키징·HuggingFace) · coach(Dockerfile 순서 버그) · delegate(embedding.py) · quiz(6문항)

## 한 줄 흐름

어제 쓴 `chunk_text`를 reviewer로 마무리(잉여 마지막 조각 제거)하던 중, **"상용 LLM 쓰면 안 되나"**
질문에서 학습 방향을 재조정했다 — 1순위는 *모델을 만드는(build) 게 아니라 운영하는(operate)* 인프라.
그 흐름으로 **에어갭 모델 패키징**(빌드 때 가중치 선다운로드 → 이미지에 굽기 → `--network none`으로 실증)을
깊게 파고, `embedding.py`는 얇게(delegate) 통과시켰다.

## 헷갈림 → 교정 궤적  ★핵심

| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| chunk 마지막 잉여 조각, 버리는 조건 | "마지막 조각이 overlap보다 작으면 버림" | 정확. 단 코드론 `out[-1]`이 1개짜리 리스트의 유일 조각도 잡음 → **`len(out)>=2 and len(out[-1])<overlap`** 로 "앞에 조각이 있을 때만" 가드 필요 |
| 상용 LLM 쓰면 안 되나 | "직접 LLM 구축할 생각 없었다(DevOps가 더 큰 목표)" | 에어갭이 금지하는 건 **모델 가격이 아니라 네트워크 경계**. API 호출(외부로 나감)=금지, 로컬 추론=허용. 그리고 우리는 모델을 *만들지(build)* 않고 *운영(operate)* 만 함 → 그게 LLMOps=사용자 목표 한복판 |
| HuggingFace가 뭔지 | "캐시된다는데 huggingface가 뭔데" | **AI 모델계의 npm/Docker Hub**(중앙 레지스트리). `"BAAI/bge-m3"`=`@org/pkg` ID, `~/.cache/huggingface`=`node_modules`. Hub에서 받는 건 외부 네트워크 호출 → 에어갭 충돌 |
| 가중치를 어떻게 이미지에 넣나 | "의존성 설치 시 같이 다운로드" | `pip install`은 **라이브러리 코드**만 받음(수MB). **가중치(2GB)는 자동으로 안 따라옴.** 별도 `RUN python -c "...SentenceTransformer(...)"` 로 빌드 때 *일부러* 다운로드를 일으켜 캐시에 구워야 함 |
| 다운로드용 코드를 따로 짜나 | "특정 경로에 넣는 코드를 어떻게…" | 별도 코드 불필요. **런타임에 일어날 그 로드 한 줄을 빌드 때 한 번 실행**시키면 됨. 같은 코드, 시점만 다름(빌드=받기, 런타임=읽기) |
| `RUN python -c` 위치 (Dockerfile 버그) | torch 다음·requirements **앞**에 둠 | 그 시점엔 `sentence-transformers` 미설치 → `import` 실패. **requirements 설치 *뒤*** 로 이동해야 함 |
| `HF_HUB_OFFLINE=1` 위치 | "다운로드 뒤 / 런타임이 나음" | 정확. 다운로드 **앞**에 두면 그 RUN이 네트워크 막혀 빌드 실패. 빌드=네트워크 ON 필수, 런타임=OFF 강제 → 상반된 요구라 **compose 런타임 env로 분리** |

## 다룬 개념

| 개념 | 한 줄 핵심 |
|---|---|
| chunk 잉여 조각 가드 | `len(out)>=2 and len(out[-1])<overlap` → 직전 조각에 완전 포함된 꼬리만 제거, 단일 조각은 보존 |
| build vs operate | 모델 *학습/튜닝*(안 함) ≠ 모델 *서빙·패키징·배포·관측*(이게 전부=LLMOps/DevOps) |
| 에어갭 빨간선 | 모델 가격이 아니라 **네트워크 경계**. 추론이 내 망 안에서 일어나면 OK |
| HuggingFace Hub | AI 모델 중앙 레지스트리(=npm/Docker Hub). 모델 ID=`@org/pkg`, HF 캐시=`node_modules` |
| 라이브러리 ≠ 가중치 | `pip install`=코드(수MB, PyPI) / 가중치=데이터(2GB, HF Hub). 별개로 받아야 |
| 시점 분리 | 받기=빌드(네트워크 O) / 읽기=런타임(네트워크 X). **같은 코드 한 줄**, 캐시가 채워졌는지로 갈림 |
| 머신 분리 | 빌드=연결된 CI/개발머신, run=폐쇄망. 이미지가 가중치 싣고 `docker save→load`로 경계 넘음. 폐쇄망에선 빌드조차 못 함 |
| `HF_HUB_OFFLINE=1` | 캐시 있어도 Hub에 "혹시 최신?" 확인하려는 시도 차단 → 조용한 네트워크 대신 시끄럽게 실패. 런타임 env로만 |
| 도커 레이어 캐시 순서 | 변경된 레이어 *아래*는 전부 캐시 무효화 → `requirements→모델다운로드→COPY app` 순서면 코드 수정해도 2GB 재다운로드 안 함 |
| lazy singleton (embedding) | `_get_model()`: 첫 호출만 로드·이후 재사용. 함수 안 로드=매 호출 2GB 재로드(느림), `global` 누락=`UnboundLocalError` |
| `--network none` 실증 | 네트워크 0 + `HF_HUB_OFFLINE=1`로 embed 성공(1024차원) = 폐쇄망 동작의 **실제 증명**(빌드 성공과 다름) |

## 막힌 곳 → 해결

- **Dockerfile 순서 버그(coach):** `RUN python -c "...SentenceTransformer..."` 를 torch 다음·requirements 앞에 배치 → 그 시점 `sentence-transformers` 미설치라 `import` 실패. 증상→어떤 패키지가 언제 깔리나 추적→requirements 설치 뒤로 이동해 해결.
- **에어갭 동작 검증:** `docker compose build api`(#9에서 bge-m3 391샤드 다운로드 294s) → `docker run --rm --network none -e HF_HUB_OFFLINE=1 ... embed(...)` → `벡터개수:1 차원:1024` 성공. 네트워크 물리 차단 상태에서 캐시 로드 확인 = 에어갭 실증.

## 퀴즈 결과

6문항 중 **1·2·3·6 통과, 4·5 미해결**(내일 재풀이).

| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| 1. 폐쇄망 로드 실패 이유 + 두 축 | Hub 다운로드 불가로 터짐 / 빌드 때 받고 캐시서 읽기 | 동일(+`HF_HUB_OFFLINE` 안전장치) | ✅ |
| 2. OFFLINE을 다운로드 앞에 두면? 왜 런타임 env? | 빌드 실패 / 빌드 땐 상관없고 런타임만 차단 | 빌드 실패 맞음. 단 "빌드 땐 네트워크 *필요*"가 정확(상관없음 아님) | 부분 |
| 3. COPY app을 다운로드 앞에 두면? | 매 수정마다 재다운로드로 느림 | 맞음 + **변경 레이어 아래 전부 캐시 무효화** 규칙이 원인 | 부분 |
| 4. 모델 로드 함수 안에 두면? global 빼면? | "에러 발생" / 외부 변수 None 유지 | ❌ 에러 아님 — **매 호출 2GB 재로드(성능)**. global 빼면 **`UnboundLocalError`**(읽기조차 터짐) | ❌ |
| 5. `--network none`이 build 성공과 다른 증명? | "네트워크 상관없이 build는 성공해야" | ❌ 핀트 어긋남. build 성공=가중치 들어감(네트워크 있었음). **network-none=폐쇄망 실제 동작=진짜 에어갭 증명** | ❌ |
| 6. 임베딩 출력? 청킹과 차이? 1024 이유? | 벡터 출력 / 청킹은 전처리 / 1024 그래프 | 출력·전처리 구분 ✅. 1024는 **pgvector `vector(1024)` 스키마 + 유사도는 동일 차원끼리만** | ✅ |

## 다음 액션

- [ ] 퀴즈 **4·5 재풀이**(lazy singleton 이유=재로드 방지 / `global`→`UnboundLocalError`, `--network none`=에어갭 실증)
- [ ] `pgvector` 연결 + chunks 테이블 INSERT(벡터 1024차원 저장) — delegate
- [ ] `retrieval.py` — 질문 임베딩 → `<=>` top-k 검색 — delegate
- [ ] 깊은 학습은 인프라로: 서빙(Ollama→vLLM)·관측·배포 쪽
