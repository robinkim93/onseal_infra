# K8s Service & probe — endpoints로 둘을 잇다

- **날짜:** 2026-06-23
- **단계:** M2 (Ollama→K8s 오케스트레이션)
- **모드:** reviewer(직접 쓴 web-svc.yaml) → tutor(Service·probe 새 개념) → quiz(마무리) / YAML 문법 표면은 delegate

## 한 줄 흐름
직접 초안한 Service manifest의 `selector: app: WEB`(대소문자) 함정에서 출발 —
apply는 통과하지만 endpoints가 비어 통신만 끊기는 걸 직접 관찰하고, "Service 진단=`get endpoints`"를 체득.
이어 probe(readiness/liveness)를 "running ≠ ready" 빈틈에서 도출하고, 실패 시 처방이 정반대(트래픽 제외 vs 재시작)임을
nginx에 일부러 깨진 readinessProbe를 걸어 `READY 0/1`·endpoints 비움으로 눈으로 확인.

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| Service selector 불일치 시 apply | "에러는 안 나지만 통신이 안 된다" | 정확. Deployment selector는 apply 거부, **Service selector는 검증 안 함** → 통과 후 조용히 endpoints 비움. 같은 라벨 메커니즘이지만 성격 정반대(계약 vs 느슨한 질의) |
| 왜 Service는 0개 매칭을 안 막나 | "Service를 먼저 만들었거나, 의도적으로 Pod를 안 띄웠을 수 있어서" | 정확. 0개 매칭도 **합법 상태** → 막을 근거 없음 = 느슨한 결합(loose coupling), 매칭 집합은 런타임에 계속 재평가 |
| 통신 안 됨을 어떻게 보나 | (관찰 후) "endpoints가 null" | 맞음. endpoints 비었다 = Service가 고른 Pod 0개 = 빈 문. **Service 디버깅 1순위 = `kubectl get endpoints`** |
| 안정적 통신 주소 | "Service/Deployment 이름으로 통신" → 채점서 "**Deployment 이름**"으로 좁힘 | ⚠️ **Service 이름**이지 Deployment 아님. DNS 등록은 Service만. api는 `db` **Service**에 접속(`db:5432`). 고정 ClusterIP를 가진 건 Service, Deployment는 Pod 공장. CoreDNS가 Service명→ClusterIP 해석 |
| running = ready 인가 | "다름. readiness 통과해야 endpoints에 넣음" | 맞음. 단 **readiness probe를 정의했을 때만.** 안 적으면 기본값 "running=ready" → 0초에 endpoints 등록 → 30초 로딩 사고. probe=K8s에게 "준비됐는지 묻는 법"을 알려주는 것 |
| readiness 실패 시 행동 | (처음) "통신 재시도" → (교정) "endpoints 제외, 통과까지 probe 재폴링" | **endpoints에서 제외**(트래픽 차단), Pod는 **죽지 않고 Running**. probe는 주기적으로 계속 검사 → 통과하면 재등록. "재시도"가 아니라 "명단 제외" |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| Service (ClusterIP) | 휘발성 Pod IP 앞에 세운 **고정 주소**. 안 바뀜, 클라이언트는 이걸 보고 진입 |
| Service selector | Pod label로 대상을 고르는 그물. Deployment와 같은 메커니즘, 단 apply 검증 없음(느슨) |
| Endpoints | Service가 selector로 실제 골라낸 Pod IP:포트 목록. 비었으면 selector↔label 불일치. **디버깅 1순위** |
| 느슨한 결합 | Service↔Pod 서로 모름. 매칭 집합을 런타임에 계속 재평가 → 0개도 정상 상태 |
| CoreDNS | 클러스터 내 DNS 서버. **Service 이름** → ClusterIP 해석. IP 숫자 박지 말고 이름 사용 |
| readiness probe | "요청 받을 준비됐나" 검사. 실패→endpoints 제외(트래픽 차단), Pod는 계속 Running |
| liveness probe | "살아있나" 검사. 실패→컨테이너 **재시작**(kill→restart) |
| probe 분리 이유 | 못 받는 *종류*가 다름: 일시적(곧 회복)=readiness(재시작 손해) / 영구 정지(데드락)=liveness(재시작 필요). 진단≠처방 |
| 기본 readiness | probe 미정의 시 K8s 기본값 = "running=ready" → 즉시 endpoints 등록 |
| CrashLoopBackOff | Pod STATUS. Crash(죽음)+Loop(반복 재시작)+BackOff(간격 점점 증가 10→20→40초…최대 5분). liveness 반복 실패의 종착점. 진단=`logs`+`describe` |

## 막힌 곳 → 해결
- **증상:** Service apply는 성공인데 ClusterIP 접속 불가. `get endpoints` → `<none>`.
  - **원인:** web-svc.yaml `selector: app: WEB`(대문자) ↔ Pod label `app: web`(소문자) 불일치.
  - **수정:** selector를 `web`으로 교정 → 재apply → endpoints에 Pod IP 채워짐(reviewer 모드, 직접 수정).
- **실습:** nginx에 `readinessProbe.httpGet.path: /wrong-path`(404) 의도적 주입.
  - **관찰:** STATUS=`Running`(살아있음) + `READY 0/1` + endpoints `<none>`. → path를 `/`로 교정 시 `READY 1/1` + endpoints 채워짐.
  - **요지:** readiness 실패는 Pod를 죽이지 않음(STATUS Running 유지) — liveness였다면 RESTARTS↑·CrashLoopBackOff였을 것.

## 퀴즈 결과
| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| endpoints `<none>` 범인·수정 | "label 못 찾음, Deployment label↔Service selector 통일" | selector↔Pod label 불일치 | ✅ |
| 왜 Service는 selector 불일치를 안 막나 | "먼저 생성·의도적 비움 가능" | 0개도 합법 상태=느슨한 결합 | ✅ |
| ClusterIP 숫자 박기 vs 이름 | "IP 바뀔 수 있음, **Deployment 이름**+dnsCore" | **Service 이름** + **CoreDNS** | ⚠️ 부분(개념 맞으나 Service≠Deployment, CoreDNS 명칭) |
| readiness/liveness 처방 + 실패 행동 | a=readiness(제외·재폴링), b=liveness(재시작) | 동일 | ✅ |
| CrashLoopBackOff 의미·진단 | "반복 재시작, backoff=간격 증가, logs/describe" | 동일 | ✅ |

## 다음 액션
- [ ] 실제 Onseal db/ollama/api를 Deployment + Service로 이전 (nginx 데모 졸업) — **Service 이름으로 상호 통신** 적용
- [ ] Volume(PersistentVolume/Claim) — db 데이터·모델 가중치 영속화
- [ ] ConfigMap/Secret — env·설정 주입 (에어갭 시크릿 관리와 연결)
- [ ] CrashLoopBackOff 실제 발생 시 coach 모드로 `logs`+`describe` 진단 깊게
- [ ] kind 휘발성 대비 — 클러스터 재생성 + `apply` 스크립트화(에어갭 배포 패키징 복선)

> 이번 실습도 학습용 nginx 데모. 실제 서비스 이전은 다음 액션에서.
