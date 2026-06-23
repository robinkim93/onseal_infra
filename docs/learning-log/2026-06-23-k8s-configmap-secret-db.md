# K8s ConfigMap·Secret + 실제 Postgres 이전 — 설정·시크릿을 워크로드에 엮다

- **날짜:** 2026-06-23
- **단계:** M2 (Ollama→K8s 오케스트레이션)
- **모드:** tutor(ConfigMap/Secret·control plane 새 개념, compose 발판) → reviewer(직접 쓴 db.yaml) → coach(CrashLoopBackOff 진단) → quiz(마무리) / 셋업·이스케이프는 delegate
- **메타:** 학습 중 "안 가르친 용어를 아는 척 흘린다"는 사용자 지적 → **"용어 게이트" 규약을 SKILL.md·CLAUDE.md에 신설**(아래 별도 섹션)

## 한 줄 흐름
compose의 `environment:`/`.env`가 K8s에서 ConfigMap(안 민감)·Secret(민감) 두 object로 갈라지는 데서 출발 →
Secret이 암호화가 아니라 base64일 뿐임을 직접 decode로 확인(보안 함정) →
"etcd는 처음 듣는데?"에서 멈춰 **control plane 아키텍처(etcd·controller·reconciliation)** 를 메우고,
나아가 "구멍이 계속 난다"는 지적으로 **용어 게이트 규약**까지 신설 →
db.yaml을 직접 작성해 Secret+ConfigMap+PVC를 postgres에 엮고 apply →
**CrashLoopBackOff**를 만나 coach로 로그까지 내려가 *지난 시간 PVC 잔재가 initdb를 막은* 한 바퀴를 풀고,
PVC를 생명주기 순서대로 재생성해 `Running 1/1` → psql 접속으로 자격증명 주입을 end-to-end 검증. nginx 데모 졸업.

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| Secret이 암호화되나 | "암호화 안 됨. ConfigMap이 암호화해 넘기고 필요한 곳서 복호화" | 방향 맞음(암호화 아님). 단 ConfigMap↔Secret은 암복호 짝이 **아님**. Secret은 그냥 **base64 인코딩**(가역, 비밀 아님). 둘은 "안 민감/민감"으로 **용도만 다른 형제** |
| etcd가 뭔가 | (처음 듣는 용어) | **클러스터의 단일 DB.** apply한 모든 object(Pod·Secret·PVC…)가 레코드로 저장됨. `kubectl get`=API server 거쳐 etcd 읽기. "Secret이 etcd에 base64로 누움"=중앙 DB에 암호화 없이 비번이 있음 |
| self-healing의 행위자 | "Deployment가 etcd 선언 보고 되살림" | Deployment는 **데이터**(etcd 속 desired). 행위자는 **controller**(reconciliation loop): desired↔actual 비교→간극 메움. 명사(Deployment)와 동사(controller)를 분리 |
| env가 Pod 레벨? | "Pod 레벨. 같은 용도 컨테이너를 모은 단위라 공유" | **컨테이너 레벨**(volumeMounts와 같은 층). env=프로세스가 보는 변수, 프로세스는 컨테이너가 돌림. + Pod 정의 교정: "용도 같음"이 아니라 **생명주기·의존성·네임스페이스를 공유(운명 공동체)** |
| POSTGRES_USER는 Secret? | "USER도 민감 → Secret" | **ConfigMap.** 판별 기준 = *"이 값 하나만 유출돼도 피해?"* USER는 식별자(자물쇠 아님)라 No. PASSWORD만 진짜 Secret |
| PVC 비우기 방법 | "storageClassName 바꾼다 / PV를 직접 지운다" | classname=다음에 받을 종류만 바꿈(안 비워짐). 동적 프로비저닝에선 **PVC를 지우면 PV가 cascade(reclaim=Delete)** → PV 손으로 안 지움. 단 Deployment 먼저 지워야(self-healing이 Pod 되살려 PVC 점유) |
| Pod 2개 보임 | "옛 RS와 새 RS가 동시에 도는 순간 찍음" | 맞음(메커니즘). **누락=왜 정상인가**: RollingUpdate가 새 Pod를 `Ready`로 만든 *뒤* 옛 걸 죽임 → **무중단(zero-downtime)** 위해 *일부러* 겹침 |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| ConfigMap | 안 민감한 설정(USER·DB·포트·로그레벨). 평문 저장. compose `environment:` 대응 |
| Secret | 민감 값(PASSWORD·키). **base64 인코딩일 뿐 암호화 아님**. 보호는 RBAC+encryption at rest로 |
| base64 | 가역 인코딩(바이너리도 담으려는 것). 비밀·키 없음 → 보안과 무관 |
| 주입 2방식 | ① env로 꽂기(편함, 샘) ② 볼륨 파일 마운트(permission 가능, 안전·프로덕션 권장) |
| secretKeyRef / configMapKeyRef | env 값의 출처를 object의 특정 key로 지정. 모양 동일, 이름만 다름 |
| 판별 기준 | "이 값 단독 유출 시 피해?" → Yes=Secret, No=ConfigMap |
| etcd | 클러스터의 단일 DB. 모든 object의 desired/status가 여기 저장 |
| control plane | API server(정문)·etcd(DB)·scheduler(배치)·controller-manager(조정)·kubelet(실행) |
| reconciliation loop | controller가 desired↔actual을 끊임없이 비교→맞춤. self-healing·선언형의 정체 |
| ReplicaSet | Deployment→ReplicaSet→Pod. "Pod N개 유지" 담당, self-healing 실무자 |
| RollingUpdate | spec 교체 시 새 Pod를 Ready로 띄운 뒤 옛 걸 죽임 → 무중단. 전환 중 잠깐 2개 |
| RBAC | Role(허용 규칙)+RoleBinding(누구에게)+ServiceAccount(Pod 계정). "누가 Secret 읽나" 통제 |
| encryption at rest | API server가 etcd에 쓰기 전 암호화. 키 관리가 관건 → KMS(에어갭은 사내 KMS) |
| initdb | postgres가 **빈** 데이터 디렉터리에 DB를 처음 세팅. 비어있지 않으면 거부 |
| PGDATA | postgres 데이터 경로 env. 하위 폴더 지정해 마운트 루트 잔재/lost+found 회피(프로덕션 패턴) |
| CrashLoopBackOff | 컨테이너가 켜지자마자 죽고 재시작 반복 → kubelet이 간격 늘리며 대기 |
| 이벤트 vs 로그 ★ | describe=오케스트레이터 시점(증상 "자꾸 죽음") / logs=컨테이너 프로세스가 뱉은 원인. 원인은 logs에만 |
| PVC 생명주기 | 비우기=Deployment 삭제→PVC 삭제(PV cascade)→PVC 생성→Deployment 생성(PVC 먼저) |
| accessMode RWO 한계 | "한 노드 RW"까지만 보장. 단일 노드면 두 워크로드 공존 허용 → 전용은 사람이 설계로 보장 |

## 막힌 곳 → 해결
- **증상:** db.yaml apply 후 postgres가 `Started (x3)` → `Back-off restarting failed container` (CrashLoopBackOff).
  - **진단 원칙(coach):** 이벤트는 "자꾸 죽는다"(증상)까지만 안다 → **원인은 `kubectl logs`** 로 내려가야 함.
  - **가설:** "기동 초기(initdb)에 뭔가 거부. 게다가 이 db-pvc, 지난 시간 영속성 증명하려고 파일을 써뒀다."
  - **로그:** `initdb: error: directory "/var/lib/postgresql/data" exists but is not empty` → 가설 적중.
  - **원인:** 재사용한 db-pvc에 **지난 세션 nginx 잔재**가 남음 → initdb는 빈 디렉터리만 초기화하므로 거부. *영속성이 거꾸로 발목*.
  - **처방(2갈래):** A) PVC 재생성(잔재째 비움) / B) `PGDATA`를 하위 폴더로(프로덕션 패턴). → A 선택해 PVC/PV 생명주기를 직접 체감.
  - **재생성 순서 교정:** "pod 삭제→pv 삭제→pvc 삭제→pod 생성→pvc 생성"의 3오류를 reviewer로 교정 → **Deployment 삭제→PVC 삭제→PVC 생성→Deployment 생성**(self-healing 회피·PV cascade·생성 의존성).
- **Pod 2개 관찰:** apply 직후 Running+ContainerCreating → RollingUpdate 정상 전환(무중단)으로 판명.
- **psql 검증:** `\l` 메타명령이 셸 이스케이프로 깨짐 → 백슬래시 없는 `SELECT current_user, current_database();`로 우회 → onseal/onseal 확인, Secret·ConfigMap 주입 end-to-end 검증.

## 용어 게이트 규약 신설 (메타 — 학습 방식 개선)
- **계기:** etcd·RBAC가 안 배운 채 설명에 등장 → 사용자 "구멍이 계속 발견된다, 방지책을 규약에 박아라."
- **진단:** 커리큘럼 순서(object-first)는 정상. 문제는 **설명에 쓰는 어휘 수준이 가르친 수준을 앞지름**(미정의 용어를 아는 척 사용).
- **처방:** `.claude/skills/learning-mode/SKILL.md`에 **"용어 게이트"** 섹션 + `CLAUDE.md`에 포인터 한 줄.
  - 규칙: 안 가르친 전문용어는 나오는 순간 **(a) 한 줄 정의** 또는 **(b) "나중에 다룰 1차 개념" 명시** 둘 중 하나. 벌거벗겨 흘리지 않음.
  - 비대칭: 아는 용어 표시=한 마디 손해 / 모르는 용어 누락=silent gap 누적 → **애매하면 표시.**
  - 송신 전 self-check, "covered"=docs/learning-log·docs/concepts·이번 세션에 등장한 것.

## 퀴즈 결과
| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| Secret 보안 오해·저장/접근 대책 | "base64는 변환일 뿐, 저장은 암호화·접근은 RBAC" | 동일(+ encryption at rest·KMS 명칭) | ✅ |
| USER가 ConfigMap인 이유 | "USER만으론 접근 불가" | 판별기준 "단독 유출 피해?" No | ✅ |
| etcd·reconciliation으로 self-heal 설명 | "controller가 etcd 선언↔현재 비교, 다르면 desired로 회복" | 동일 | ✅ |
| CrashLoop: describe 아닌 logs를 봐야 한 이유 | "몰라" | 이벤트=오케스트레이터 시점(증상)/로그=프로세스가 뱉은 원인. 원인은 logs에만. 원인=PVC 잔재로 initdb 거부 | ❌ |
| PVC 생명주기: Deployment 먼저·PV 안 지운 이유 | "Deployment 안 지우면 PVC 못 지움 / PVC 지우면 PV 삭제" | 동일(Deployment 먼저=self-healing 회피, PV=cascade) | ✅ |
| RollingUpdate 2개 Pod·정상인 이유 | "옛 RS·새 RS 동시에 도는 순간 찍음" | 메커니즘 맞음. 누락: 무중단 위해 새 Ready 후 옛 종료 = 의도된 겹침 | 부분 |

## 다음 액션
- [ ] **시크릿 파일 마운트(주입 2번 방식)** — env의 누수 약점을 volumeMounts+permission으로 보완. 오늘 개념만, 실습 미검증
- [ ] **RBAC 실습** — Role/RoleBinding/ServiceAccount로 "누가 Secret 읽나" 직접 통제. 오늘 정의만
- [ ] **encryption at rest** — etcd 암호화 켜기 + (사내)KMS. 에어갭 시크릿의 핵심
- [ ] **db를 Service로 노출** — 다른 Pod(api)가 `db:5432`로 붙게. M1 RAG 스택 K8s화의 다음 조각
- [ ] **PGDATA 하위폴더 패턴** — 오늘 B안으로 미적용, 실디스크 lost+found 대비 프로덕션 표준

> 이번 실습으로 nginx 데모 졸업, 실제 pgvector Postgres가 PVC+Secret+ConfigMap으로 가동(M1 RAG 스택의 K8s 이전 시작).
