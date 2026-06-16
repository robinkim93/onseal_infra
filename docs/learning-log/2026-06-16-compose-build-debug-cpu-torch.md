# docker compose 빌드 디버깅 → CPU torch로 이미지 경량화

- **날짜:** 2026-06-16
- **단계:** M1
- **모드:** coach (빌드 실패 진단) → tutor (GPU/CPU torch 개념) → reviewer/delegate (Dockerfile 수정·검증)

## 한 줄 흐름
"M1 스택 검증(`docker compose`)"이 빌드 단계에서 계속 실패. 표면 증상은 같았지만 원인이 매번 달랐다 —
디스크 풀 → Docker 데몬 종료 → 불필요한 GPU(CUDA) torch 다운로드. 셋을 차례로 걷어내고
`docker compose up`으로 db·ollama·api 3개 서비스가 전부 기동, `/health` 200 OK까지 확인한 뒤 커밋·푸시.

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| 빌드가 왜 실패하나 | (원인 불명) | 호스트 디스크 여유 **69MB** → 모든 빌드/pull이 `ENOSPC`. 환경 문제지 코드 문제 아님 |
| 두 번째 EOF(`rpc error... EOF`)의 원인 | "내가 도커를 끄긴 했는데" | buildkit이 데몬 연결을 잃은 것 = **데몬 종료가 곧 원인**. 디스크/네트워크 후보 기각 |
| 빌드가 받던 `nvidia_cublas`(542MB) 정체 | "뭔 소린지 모르겠다" | `sentence-transformers`→`torch`. pip 기본 torch는 **CUDA(GPU)판**이라 GPU 부품이 줄줄이 딸려옴 |
| 이 프로젝트에 왜 문제인가 | (이해 후) | Mac엔 NVIDIA GPU 없음 + 에어갭 임베딩은 CPU → 안 쓸 GPU 스택 수 GB를 이미지에 굽는 낭비 |
| 수정 위치를 어디에 둘까 | "B(Dockerfile)일 것 같음" | requirements.txt=재료목록(self-contained) vs Dockerfile=조리법(환경별 분기). M2 GPU 전환 대비해 조리법 선택 |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| `ENOSPC` / 디스크 진단 | 빌드 실패 시 코드보다 **환경(디스크) 먼저** 의심. `df -h`, `docker system df` |
| 회수 가능 공간 종류 | 빌드캐시·dangling·미사용 태그 이미지·시스템 캐시는 각각 다른 명령으로 회수 |
| Docker 빌드 = 이미지(도시락) 굽기 | 코드(레시피)→이미지(도시락). 에어갭 배포의 전제 |
| torch CUDA vs CPU 빌드 | pip 기본은 CUDA판(수 GB). CPU판은 별도 인덱스 `download.pytorch.org/whl/cpu` |
| pip 설치 순서 트릭 | 이미 설치된 패키지는 재설치 안 함 → torch를 **먼저 선점**하면 후속 의존성이 GPU판을 못 끌어옴 |
| `depends_on: condition: service_healthy` | api는 db·ollama가 healthcheck 통과한 뒤에야 기동 |

## 막힌 곳 → 해결
| 증상 | 가설 | 진단/수정 | 원인 |
|---|---|---|---|
| build 실패 | 디스크? | `df -h` → 69MB | 디스크 풀. 캐시 23GB 정리 → 30GB 확보 |
| 재빌드 `rpc ... EOF` | VM디스크 / 네트워크 / 데몬 | 호스트 디스크 27GB(정상), 사용자가 "도커 껐다" 진술 | 데몬 종료 |
| `nvidia_cublas` 542MB 다운로드 | torch가 GPU판? | 빌드 로그에서 패키지 출처 확인 | sentence-transformers→CUDA torch. Dockerfile에 CPU torch 선설치로 수정 |

검증: 재빌드 후 `grep -ciE "nvidia|cuda"` = **0건**, `torch-2.12.0+cpu`, 이미지 1.88GB. `compose up`→3서비스 healthy→`/health` 200.

## 다음 액션
- [ ] 안 쓰는 `qdrant` 이미지 정리 (벡터 DB는 pgvector로 확정 — 잔재로 추정)
- [ ] M2 GPU 프로덕션 전환 시 Dockerfile "조리법 분기"(CPU/CUDA) 실제 구성
