# docker-compose 네트워크 격리와 에어갭 구조화

- **날짜:** 2026-06-19
- **단계:** M1 (마무리) → M2/M3 복선
- **모드:** quiz → tutor → coach(직접 실험) → reviewer

## 한 줄 흐름
M1 마무리 인프라 퀴즈로 이해도를 점검하다 **"컨테이너 떠있음 ≠ 격리됨"** 이라는 구멍을 발견 →
네트워크 인/아웃바운드 방향성 → **직접 최소재현 실험으로 `internal: true`의 한계를 증명** →
실제 `docker-compose.yml`에 db/ollama 격리를 적용하고 api 이그레스는 M3 백로그로 남김.

## 학습 범위 재확정 (메타)
- **"모든 교육 계획에서 LLM 관련 학습 제외 → 순수 인프라만."** 추론 엔진(Ollama/vLLM)은
  블랙박스 워크로드로 *배포·운영만*, 내부 원리(PagedAttention·KV캐시·GPU 서빙 튜닝)는 학습 대상 아님.
- 반영(working tree, **아직 미커밋**): `CLAUDE.md`(학습 우선순위·M1 배합·서빙 스택 주석),
  `PROJECT_OVERVIEW.md` §4(M2·M4·M5 학습범위 가드) + §10 요약표.

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| `depends_on`만으로 기동 순서 충분한가 | "먼저 뜨는 게 중요한 게 아니라 *실제 동작 여부*가 중요해서 healthcheck로 구성" (정확) | `container start ≠ service ready`. **기다림은 `condition: service_healthy`가 만들고, healthcheck는 *판정 기준*.** 둘은 짝. |
| api엔 healthcheck가 왜 없어도 되나 | "api에 의존하는 페이지가 생기면 필요할 듯" (부분) | healthcheck는 *남이 나를 gate*하려고 존재. api는 의존 사슬 꼭대기라 무의미. 단 **프로덕션(K8s)에선 readiness/liveness probe 필수** (LB 라우팅·재시작 판단). |
| 지금 이 스택이 에어갭인가 | "내부 네트워크에서 돌고 있어 외부 유출 불가" (**틀림**) | `networks` 미정의 → **기본 bridge → egress 열려 있음.** 안 새는 건 *app 규율*(`HF_HUB_OFFLINE`·모델 선다운로드)이지 *네트워크 구조*가 아님. |
| 인바운드 vs 아웃바운드 충돌? | "방향별 따로 통제 가능, 충돌 아님" (정확, 힌트 후) | ingress/egress는 별개 방향 → 따로 통제 가능. (방화벽·K8s NetworkPolicy가 둘을 분리하는 이유) |
| internal+normal 동시 멤버면 외부 단절? | "단절돼야 하지 않나" (**틀림**) | 네트워크 멤버십은 **union(다중 NIC)**. 외부 라우트 있는 NIC로 나감. `internal`은 *네트워크 속성*이지 *컨테이너 글로벌 락*이 아님. |
| `external: true` 의미 | "외부(인터넷)로 향하는 네트워크" 의도로 사용 (**틀림**) | external = *외부에서 관리되는(이미 존재하는)* 네트워크. compose가 안 만들고 **`up` 시점에 존재 검사**. |
| `docker compose config` 통과 = OK? | "external:true인데 config 에러 안 났다" (발견) | config = **정적 검증/머지만.** 데몬·external 실재는 **`up`에서야** 검사. **config 통과 ≠ up 성공.** |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| `depends_on: condition: service_healthy` | 의존 서비스가 *healthy* 될 때까지 기다리게 하는 게이트 |
| healthcheck | 서비스 readiness 판정 기준; *남이 gate*하려고 존재 → K8s probe로 연결 |
| fail-closed | "안 나간다"를 믿지 말고 "*못* 나가게" 만든다 (`HF_HUB_OFFLINE`=라이브러리 가드: 없으면 조용히 받는 대신 에러) |
| 관측 vs 구조적 통제 | "봤더니 안 나감" < "구조상 못 나감" — 컴플라이언스 증명은 후자 |
| 기본 bridge vs `internal: true` | networks 미지정 = 기본 bridge(egress O); `internal: true` = 외부 라우트 없음 |
| `internal: true`는 네트워크 단위 | **all-or-nothing**: egress도, published port도 같이 죽음 → "인바운드 O·아웃바운드 X"를 한 컨테이너에 표현 불가 |
| 실패 메시지 읽기 | `Network is unreachable`=라우트 자체 없음 / `Connection refused`=경로 O·포트 닫힘 / `timeout`=방화벽 드롭 |
| 네트워크 멤버십 = union | 다중 NIC, 능력의 합집합. 제한 네트워크가 "이기지" 않음 |
| 2-네트워크 분리 패턴 | db/ollama=internal / api=internal+normal(publish·egress 경로) |
| compose config 한계 | 정적 검증만; 데몬·external 리소스 실재 미검사 |

## 직접 실험 (최소 재현)
**가설:** ① egress BLOCKED ② 인그레스 불가(`ports=` 비어있음 단서). → **둘 다 적중.**

```bash
docker network create --internal airgap_test
docker run -d --name airgap_srv --network airgap_test -p 18080:11434 ollama/ollama:0.30.8
# 단서: docker ps의 ports= 칸이 비어 있음 (publish 무효화)

curl -s -m 5 localhost:18080         # 인그레스 → exit 7 (연결 실패)
docker exec airgap_srv bash -c 'echo > /dev/tcp/1.1.1.1/53'  # 이그레스 → Network is unreachable
```

| 테스트 | 결과 | 의미 |
|---|---|---|
| 이그레스 (컨테이너→1.1.1.1:53) | `Network is unreachable` | 라우트 자체 없음 = `internal:true`가 한 일 |
| 인그레스 (호스트→:18080) | `curl exit 7` | internal 네트워크 위 publish는 무효 |

→ **결론: `internal:true`는 egress와 publish를 함께 끊는다(네트워크 단위).**

## 적용 결과 (`docker-compose.yml`, 미커밋)
| 컨테이너 | 네트워크 | 보장 |
|---|---|---|
| `db`, `ollama` | `onseal-internal-network` (`internal:true`) | **외부 단절 = 구조적 보장** ✅ / `ports:` 제거(LAN 노출 0) |
| `api` | `onseal-internal-network` + `onseal-network`(일반) | db/ollama 통신 ✅ + `:8000` publish ✅ |
| **api 아웃바운드** | — | ❌ **compose로 못 막음** → 호스트 방화벽/K8s NetworkPolicy (M3) |

리뷰 중 잡은 버그: ① api가 internal 한쪽에만 있어 db/ollama 통신 불가 → 양쪽 가입으로 수정.
② `onseal-network`를 `external: true`로 선언(=미존재 네트워크 가정) → 평범한 정의로 수정.

## 퀴즈 결과 (M1 마무리, 인프라 층)
| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| 기동 순서/healthcheck | healthcheck로 실제 동작 판정 | + `condition: service_healthy`가 대기를 생성 | ✅ |
| api healthcheck 불필요 이유 | 의존 페이지 생기면 필요 | 남이 gate하려 존재 / 프로덕션은 K8s probe 필수 | 부분 |
| 에어갭 구조 증명 | 내부망이라 유출 불가 | 기본 bridge라 egress 열림, app 규율일 뿐 | ❌→교정 |
| 시크릿 *런타임* 유출 경로 | `docker history`/`save` | 그건 *이미지-타임*; 런타임은 `docker inspect`/`/proc/environ` | 부분 |
| 시크릿 상위 방식 | KMS 외부 주입 | secrets manager(파일마운트·암호화·감사·회전), 단 에어갭→**self-hosted** | 부분 |

> RAG 파이프라인/생성·임베딩 등 LLM 층 문항은 **학습 범위 외**로 의도적으로 얕게 통과.

## 다음 액션
- [ ] **api 이그레스 차단** — 호스트 방화벽 egress-deny (M3)
- [ ] **K8s NetworkPolicy** 로 ingress/egress 분리 표현 (M2/M3) — 오늘 부딪힌 docker 한계를 메우는 지점
- [ ] 기획 문서(`CLAUDE.md`·`PROJECT_OVERVIEW.md`) 및 `docker-compose.yml` 변경 **커밋 여부 결정** (현재 미커밋)
- [ ] 시크릿: `.env`+env → 파일마운트/self-hosted secrets manager 전환 검토 (M3)
