# K8s 입문 — Pod와 Deployment

- **날짜:** 2026-06-21
- **단계:** M2 (Ollama→K8s 오케스트레이션 진입)
- **모드:** tutor (새 개념 operate 깊이 설명 → 직접 실습 검증), 중간 coach식 사고실험

## 한 줄 흐름
compose만 알던 상태에서 K8s의 최소 단위 **Pod**가 컨테이너와 무엇이 다른지부터 시작.
kind로 클러스터를 띄워 맨몸 Pod를 직접 다뤄보며 "Pod는 일회용"을 눈으로 확인했고,
그 빈자리를 메우는 **Deployment(desired state + reconciliation loop)**까지 직접 실습으로 검증.

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| `READY 0/1`의 두 숫자 | "Pod 안 1개 컨테이너 중 떠 있는 게 0개" | (Ready 컨테이너 수)/(전체 컨테이너 수). "떠 있는"이 아니라 **Ready 판정**(→ probe 복선) |
| 지금 띄운 게 compose 기준 뭔가 | (질문) | compose(db/ollama/api)와 무관한 **순수 데모 nginx**. Pod 그릇만 보려고 곁가지 없는 이미지 선택 |
| db/ollama/api를 K8s로 옮기면? | "Pod 1개에 3개 묶는 게 맞을 듯" | **틀림.** 스케일·수명이 다르면 분리 → **3 Pod**. 스스로 사고실험으로 교정 도달 |
| 묶음 판단 기준 | (사고실험 후) "Pod 단위 스케일이 강제되고, api 재시작에 무거운 ollama까지 끌려 죽으면 곤란" | 정확. **"같이 죽고 같이 늘어나도 되는 것"끼리만 한 Pod** (sidecar 패턴이 그 예) |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| Pod | K8s 배포 최소 단위. 컨테이너를 담는 그릇, **IP 1개를 컨테이너가 공유** |
| kind | Docker 컨테이너 안에 K8s 노드를 통째로 넣은 로컬 클러스터 (`get nodes` 노드 = `docker ps` 컨테이너) |
| 맨몸 Pod = 일회용 | `kubectl run`으로 만든 Pod는 죽으면 끝, 아무도 안 되살림 (`No resources found`) |
| Deployment | "Pod N개 유지" desired state 선언 → 컨트롤러가 현재 vs 희망 차이를 계속 메움 |
| reconciliation loop | K8s 심장. 명령이 아니라 **선언 + 끊임없이 맞춤** (self-healing) |
| 계층 | Deployment → (ReplicaSet) → Pod → Container |
| compose 대조 | `restart: always`는 같은 호스트 재시작까지. Deployment는 replicas 유지 + 어느 노드든 재생성 |

## 실습으로 검증한 것
| 실험 | 명령 | 관찰 → 결론 |
|---|---|---|
| Pod ⊃ 컨테이너 | `kubectl run web --image=nginx:alpine`, `describe`, `exec` | `Containers:` 섹션에 컨테이너 노출, `exec hostname -i` IP = Pod IP |
| Pod 일회용 | `kubectl delete pod web` → `get pods` | `No resources found` — 안 되살아남 |
| Deployment self-heal | `create deployment` → `delete pod <name>` → `get pods` | 새 Pod 즉시 재생성 (이름 suffix 다름, AGE 몇 초) |

## 퀴즈 결과
| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| `delete pod web`(맨몸) 하면 되살아나나 | "안 살아남" | 안 살아남 (상위 객체 없음) | ✅ |
| Deployment 밑 Pod를 delete하면? | "살아있고 이름 다름(새로 띄워서)" | 재생성, 이름·AGE 갱신 | ✅ |
| `scale --replicas=3` 시 컨트롤러 동작 | "현재 1 → 희망 3, 차이 2개 Pod 생성" | 정확 (reconciliation) | ✅ |

## 다음 액션
- [ ] Deployment를 YAML 매니페스트로 선언적 작성 (지금은 명령형 `create deployment`만 해봄)
- [ ] Service 개념 — Pod IP가 재생성마다 바뀌는 문제를 어떻게 해결하나
- [ ] Onseal db/ollama/api를 실제 Deployment 3개 + 각자 필요한 Volume/ConfigMap으로 이전
- [ ] probe(readiness/liveness) — `READY` 판정의 실제 기준

> 참고: 이번 실습은 학습용 데모 nginx만 사용. Onseal 실제 서비스 이전은 위 액션에서 진행.
