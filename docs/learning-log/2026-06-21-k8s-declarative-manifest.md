# K8s 선언형 manifest — 명령형에서 선언형으로

- **날짜:** 2026-06-21
- **단계:** M2 (Ollama→K8s 오케스트레이션 진입)
- **모드:** tutor(발판 있어 소크라테스) → 클러스터 소실 구간 coach(가설 먼저) → YAML 문법 표면은 delegate(떠먹임)

## 한 줄 흐름
지난 세션의 명령형 `create deployment`가 남긴 한계("정의가 휘발됨")에서 출발.
`-o yaml`로 desired state와 status를 손으로 갈라 최소 manifest 골격을 도출하고,
selector↔labels·YAML 리스트 함정을 일부러 깨뜨려 검증한 뒤, "파일이 진실의 원천"(GitOps 씨앗)까지 닿음.

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| 명령형의 한계 | "선언해둔 공간이 없어 나중에 현재 상태 파악 불가" | 정확. source of truth가 클러스터 안에만 휘발성으로 존재 → 재현 불가. 에어갭 다현장 배포에선 더 치명적(현장마다 손으로 명령 = 불통일) |
| `-o yaml`의 어느 줄이 내 의도인가 | "status가 K8s가 채운 것, 나머진 기본값" / "metadata는 name·namespace 정도만 내가 씀" | 맞음. 가르는 기준 = **"그 값을 내가 미리 정할 수 있나 vs 서버만 아나"**. uid/resourceVersion/generation/creationTimestamp = 서버가 생성 순간에야 부여 |
| selector와 template labels 불일치 시 | "생성은 하되 자식 인식 못 해 reconcile 불가" | 직관은 정확. 단 실제론 K8s가 런타임 폭주를 기다리지 않고 **apply 단계에서 즉시 거부**(API validation). 자기모순 객체는 애초에 못 만들게 설계 |
| YAML 컨테이너가 둘로 쪼개짐 | (막힘) "어떻게 적는지 모르겠다" | 대시 `-` 하나 = 리스트 아이템 하나. `name`과 `image`는 한 컨테이너의 속성이므로 **대시는 첫 줄에만**, 나머지는 대시 없이 같은 들여쓰기. JSON으로 보면 `[{name,image}]` vs 내가 쓴 `[{name},{image}]` |
| 클러스터가 왜 사라졌나 | "짐작 안 감" | 발판 없음 → 설명: restart policy 차이. compose는 `restart: always`로 Docker가 부활, kind 노드는 정책 없거나 클러스터 삭제 → 재부팅에 소멸. **로컬 kind는 휘발성** |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| manifest | K8s에게 "이 객체를 이렇게 띄워줘"라고 적은 선언 파일(YAML). compose 파일의 K8s판, 한 파일이 한 객체 기술 |
| 명령형 vs 선언형 | `create deployment`(휘발) vs `apply -f`(파일=재현 가능). `docker run` vs `compose up`과 같은 대비 |
| `-o yaml` | 클러스터가 객체 정의를 YAML로 역출력. status/metadata 자동값/spec 기본값 등 군더더기 포함 |
| desired state vs status | `spec`=내 의도, `status`=현재 상태 보고서(availableReplicas 등). manifest엔 status 안 씀 |
| 최소 manifest 골격 | apiVersion·kind·metadata.name·spec(replicas·selector·template) — 50줄→15줄 |
| selector ↔ template.labels | Deployment가 "내 자식"을 고르는 라벨 그물. selector와 template 라벨 **반드시 일치**, 아니면 apply 거부 |
| template | "이렇게 Pod를 찍어내라"는 붕어빵 틀 |
| GitOps 씨앗 | 진실은 클러스터가 아니라 Git의 YAML. 클러스터는 거기서 `apply`로 재현되는 사본 |
| kind 휘발성 | 로컬 클러스터는 재부팅에 안 살아남음 → 상태를 클러스터에 의존하면 안 됨 |

## 막힌 곳 → 해결
- **증상:** `kubectl` → `localhost:8080: connection refused` (E0621 memcache).
  - **가설 분기:** (a) kubectl이 context 잃음 vs (b) 클러스터 그릇 자체 소멸.
  - **진단:** `docker ps`(control-plane 컨테이너 부재) → `docker ps -a | grep kind` + `kind get clusters`(둘 다 비어있음) → **(b) 확정: 클러스터 삭제됨**.
  - **원인:** Mac 재부팅/Docker Desktop 정리 과정에서 kind 클러스터 소멸. compose 식구는 `restart: always`로 생존, kind는 정책 부재로 미부활.
  - **수정:** `kind create cluster --name onseal` 재생성(셋업이라 Claude 대행).
- **증상2:** `apply` 시 에러 3줄 — 그중 `containers[0].image: Required` + `containers[1].name: Required`.
  - **원인:** `- name:`과 `- image:` 둘 다 대시 → 컨테이너 2개로 파싱됨.
  - **수정:** 대시 하나로 합치고 `image`를 `name`과 같은 들여쓰기로 정렬.

## 퀴즈 결과
| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| 명령형 deployment의 한계 | "선언 공간 없음·현재 상태 파악 불가" | source of truth 휘발 → 재현 불가 | ✅ |
| `-o yaml`에서 통째로 K8s가 채운 블록 | "status" | status | ✅ |
| metadata 중 내가 쓰는 것 | "name·namespace" | name(+namespace 선택), 나머지는 서버 부여 | ✅ |
| selector와 template label 불일치 시 | "자식 인식 못 해 reconcile 불가" | apply 단계에서 즉시 거부(validation) | ✅(직관 정확, 실제는 더 앞단 차단) |
| YAML 컨테이너 분리 버그 원인 | (스스로 못 풂) | 대시 중복 = 리스트 아이템 분리 | 부분 |

## 다음 액션
- [ ] GitOps 시연 마무리: `delete deployment` → `apply -f`로 부활 직접 눈으로 확인 (이번 세션 미완)
- [ ] Service 개념 — Pod IP가 재생성마다 바뀌는 문제 해결 (지난 액션에서 이월)
- [ ] probe(readiness/liveness) — `READY` 판정의 실제 기준 (지난 액션에서 이월)
- [ ] Onseal db/ollama/api를 실제 Deployment + Volume/ConfigMap 매니페스트로 이전
- [ ] kind 클러스터 휘발성 대비 — 클러스터 재생성 + `apply` 스크립트화(에어갭 배포 패키징 복선)

> 이번 실습은 학습용 데모 nginx만 사용. Onseal 실제 서비스 이전은 위 액션에서 진행.
