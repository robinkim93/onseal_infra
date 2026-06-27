# K8s 스택 전진 → 이미지 슬림화 (모델 가중치 PVC 분리)

- **날짜:** 2026-06-27
- **단계:** M1
- **모드:** coach(주) · reviewer · operate(새 1차개념) · delegate(모델 추출)

## 한 줄 흐름
db를 Service로 노출(CoreDNS+endpoints 검증)하고 api를 K8s로 올리려다, `kind load`가 **9GB 이미지 + 호스트 디스크 98%**로 I/O 에러. 근본 원인이 "모델을 이미지에 구운 것"임을 측정으로 확인 → **모델 가중치(bge-m3)를 PVC로 분리**하는 부트스트랩 설계로 전환. loader Pod 작성까지 진행(적재는 미완).

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| api가 `db:5432`로 닿는 원리 | "Service 필요, label·selector" (절반) | **이름 해석(CoreDNS)** 과 **Pod 선택(selector)** 은 별개 메커니즘. selector는 트래픽을 어느 Pod로, CoreDNS는 `db`→ClusterIP |
| Service 연결을 1초에 검증하는 법 | "모르겠어" | `kubectl get endpoints db` — ENDPOINTS에 Pod IP가 찍히면 selector가 실제로 물린 것. ClusterIP가 떠도 selector 틀리면 `<none>` |
| 빈 PVC에 9GB 모델 채우기 | "Job이 맞다 — 한 번 넣으면 끝" | 직관은 맞으나 **Job도 컨테이너 → 모델이 이미지에 있어야 하고 그 이미지를 노드에 load해야 함 = 막힌 작업과 순환.** 우회 = 이미지 거치지 않는 경로 |
| 모델→PVC 데이터 흐름 | "이미지 > pod > pv > pvc", "host docker api server" | 출처는 `docker cp`로 **호스트에 먼저 추출**. `kubectl cp`는 **K8s API server** 경유로 **실행 중 Pod**에 스트리밍(PVC 직접 불가). 마운트 체인은 **Pod→PVC→PV** |
| `ReadOnlyMany`로 선언 | "여러 Pod가 읽기만 하니 ROX" | 부트스트랩은 **써야** 하므로 ROX면 cp 실패(모순). **accessMode**(PVC가 지원하는 모드, 강제 아님)와 **`volumeMount.readOnly:true`**(실제 쓰기 금지 강제)는 다른 층. 단일 노드면 RWO로도 여러 Pod 공유 → **RWO + 마운트 readOnly** |
| "노드가 뭔 단위인데" | (질문) | **노드 = Pod가 올라가 도는 머신(VM/서버) 1대.** kind에선 노드=Docker 컨테이너 1개(`onseal-control-plane`). 볼륨은 한 머신 커널에 마운트 → accessMode가 "노드" 단위인 이유 |
| loader Pod에 `readOnly:true` 적용 | (작성) | **쓰는 쪽(loader)에 읽기전용을 걸어 cp가 막힘.** readOnly는 **읽는 쪽(운영 api Pod)** 에 갈 줄. 부트스트랩=쓰기 / 운영=읽기 구분을 거꾸로 적용 |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| CoreDNS | 클러스터 내부 DNS. Service 이름→ClusterIP 해석. compose의 서비스명 호출과 같은 역할 |
| Service selector vs DNS | selector=트래픽 보낼 Pod 선택 / DNS=이름 해석. 별개 |
| endpoints | selector가 문 실제 Pod IP 목록. Service↔Pod 연결의 검증 지점 |
| port vs targetPort | port=Service가 받는 포트 / targetPort=Pod 컨테이너가 듣는 포트. 달라도 됨 |
| kind 아키텍처 | Kubernetes IN Docker. **노드 자체가 Docker 컨테이너**, 그 안에 **자체 containerd**. 호스트 Docker와 이미지 저장소 분리 |
| `kind load docker-image` | 호스트 이미지를 노드 containerd로 사이드로드(레지스트리 없이). 에어갭 배포 핵심 패턴 |
| imagePullPolicy 함정 | `:latest`는 기본 `Always` → 노드에 로드해도 외부로 풀려다 `ImagePullBackOff`. 에어갭은 `IfNotPresent`/`Never` 명시 필수 |
| ImagePullBackOff vs CrashLoopBackOff | 전자=이미지 못 받아 **시작도 못 함** / 후자=켜졌다 죽음 |
| 레이어 측정 | `docker history` — 9.16GB 중 4.57GB가 모델 굽는 단 한 줄(11번). torch CPU(786MB)는 이미 최적 |
| 패키징 원칙 | **자주 바뀌는 것(코드) / 거의 안 바뀌는 것(모델)** 분리. 코드 한 줄에 9GB 재빌드·USB운반 회피 |
| node | Pod가 도는 물리/가상 머신 단위. 클러스터=노드 집합 |
| accessMode vs mount readOnly | accessMode=PVC가 지원하는 접근(매칭 힌트, kind는 강제 안 함) / `volumeMount.readOnly`=실제 강제. RWO="한 노드 RW(그 노드 내 여러 Pod 공유 OK)" |
| WaitForFirstConsumer | kind 기본 SC. PVC를 쓰는 Pod가 스케줄될 때까지 바인딩 지연 → 그래서 consumer 없으면 `Pending`(정상) |
| 부트스트랩 우회 | `docker cp`(이미지→호스트, load무관) → 임시 Pod(노드에 이미 있는 pgvector 재활용) → `kubectl cp`(host→Pod→PVC) |

## 막힌 곳 → 해결
- **증상:** `kind load docker-image test-api:latest` → `write .../data: input/output error`. `crictl`·`docker system df`도 같은 I/O error.
  - **가설(coach):** read·write 양쪽에서 I/O error → 일시 오류 아닌 스토리지 레벨 문제. 1순위=디스크 포화.
  - **진단:** `df -h` → 호스트 맥 `/System/Volumes/Data` **98%, 3.9GB 잔여**. Docker.raw는 sparse(1T 할당/29G 실사용) → 9GB 쓰려 확장하다 호스트 공간 없어 실패 = I/O error.
  - **근본:** api 이미지 **9.16GB**(절반이 모델 굽기). 디스크·load·에어갭 USB운반 모두 이 비대함이 원인.
  - **처방:** 디스크 비우기(대증)가 아니라 **이미지 슬림화(근본)** 선택 → 모델을 PVC로 분리.
- **모델 추출(delegate):** 임시 컨테이너에서 `pytorch_model.bin` blob(2.2GB) 제거 → safetensors만(4.3G→2.2G) → `docker cp`로 호스트 `model-export/`. `.gitignore`에 `model-export/` 추가(2.1GB 커밋 방지).
- **선언형 구멍(복선):** `db-config`·`db-secret`이 명령형(`kubectl create`)으로 만들어져 repo에 없음. 만약 클러스터 재생성했다면 **복구 불가** — 디스크 장애가 "선언형 아니면 재현 불가"를 실제 비용으로 드러냄.

## 다음 액션
- [ ] loader Pod 교정 — `readOnly:true` 제거(쓰기 필요), `Deployment→Pod` → apply
- [ ] `kubectl cp model-export/hub loader:/models/hub` 로 PVC 적재 → loader·model-export 삭제
- [ ] Dockerfile 11번 줄 제거 → 슬림 이미지(~1.5GB) 빌드 → `kind load`(이제 통과)
- [ ] api.yaml 보강: model `volumeMount(readOnly:true)` + `POSTGRES_HOST` + `imagePullPolicy:IfNotPresent`
- [ ] (delegate) 코드가 `HF_HOME=/models`로 로컬 모델 오프라인 로드하게 (`HF_HUB_OFFLINE`)
- [ ] **db-config·db-secret 선언형 파일화** (②구멍 — 실제 비용으로 증명됨)
- [ ] db 연결 검증 → api Service 외부 노출 → ollama K8s화
