# K8s Volume (PV/PVC) — 휘발성을 디스크로 묶다

- **날짜:** 2026-06-23
- **단계:** M2 (Ollama→K8s 오케스트레이션)
- **모드:** tutor(PV/PVC 새 개념, docker-compose 발판) → reviewer(직접 쓴 db-pvc.yaml·web.yaml) → coach(403 디버깅) → quiz(마무리) / YAML 표면은 delegate

## 한 줄 흐름
"컨테이너는 휘발성"이라는 빈틈을 K8s에서 메우는 단계. docker-compose `volumes:` 한 줄이
왜 K8s에선 PV/PVC 둘로 쪼개지는지(공급↔수요, 느슨한 결합)에서 출발 →
db-pvc.yaml을 직접 작성해 동적 프로비저닝으로 `Bound` 확인 →
빈 PVC를 nginx html에 마운트했다가 403(masking)을 만나 coach로 가설→검증→처방까지 돌고,
mountPath를 옮겨 영속화(Pod 삭제 후 데이터 생존)를 눈으로 확인.

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| PVC가 PV를 못 찾으면 Pod 상태 | "에러 없이 같은 메커니즘으로 기능 못 함, `READY 0/1` 같은?" | 방향 맞음(에러X·조용히 멈춤=느슨한 결합). 단 상태가 다름: **`Pending`**. `READY 0/1`은 컨테이너가 *떠 있는데* probe 실패. PVC 미바인딩은 마운트할 볼륨이 없어 **컨테이너 시작조차 못 함** → 그 이전 단계 `Pending` |
| `volumes` vs `volumeMounts` 중 바깥(Pod 레벨) | (처음) "volumeMounts가 containers와 형제" → (교정) "volumes가 형제" | **volumes=Pod 레벨**(containers와 형제). 저장소 자체는 Pod가 가진 공유 자원(창고). **volumeMounts=컨테이너 레벨**(컨테이너마다 다른 경로에 내는 문). 한 볼륨을 여러 컨테이너가 다른 경로로 마운트 가능 → 그래서 분리 |
| PV 생성하면 Pod 뜨나 | "pod 하나 뜨는 건지?" | **안 뜸.** PV/PVC는 워크로드가 아니라 **API에 등록되는 저장소 object**. `get pods`엔 안 나옴. Pod는 Deployment를 apply할 때만 뜨고, 그때 PVC를 마운트 |
| Pod가 PV를 갖나 | "하나의 pod가 pv를 가진 형태" | 엄밀히 Pod는 **PVC를 가리킴**(`claimName`). PV·디스크는 모름. 체인: Pod.volumes→PVC→bind→PV→디스크 = 느슨한 결합 |
| 동적 프로비저닝 메커니즘 | "storageClassName이 방아쇠인데 메커니즘은 모름" | **dynamic provisioning**: StorageClass가 가리키는 **프로비저너**(kind=local-path)가 바인딩 안 된 PVC를 감시→조건 맞는 PV를 즉석 생성·바인딩. 그래서 PV 파일을 손으로 안 써도 됨. (정적=PV 직접 작성 ↔ 동적=자동) |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| PersistentVolume (PV) | 실제 저장 공간 그 자체(디스크·NFS·로컬경로). 인프라가 **공급**. 워크로드 아닌 object |
| PersistentVolumeClaim (PVC) | "이만큼 저장소 주세요" **요청서**. 앱이 **요구**. Pod는 이것만 마운트 |
| bind | K8s가 PVC 조건(용량·accessMode)에 맞는 PV를 찾아 묶음. 성공=`Bound`, 실패=`Pending` |
| 공급↔수요 분리 | Service↔Pod와 같은 느슨한 결합 패턴. 앱은 저장소 위치 모르고, 인프라는 앱 모름 |
| accessModes | ReadWriteOnce(RWO)=한 노드에서 읽기·쓰기. db처럼 단독 점유에 적합 |
| storageClassName | 어떤 프로비저너로 저장소를 공급받을지. kind 기본=`standard`(local-path) |
| dynamic provisioning | StorageClass의 프로비저너가 PVC 보고 PV를 자동 생성·바인딩. PV 수기작성 불필요 |
| volumes (Pod 레벨) | "이 Pod가 가진 창고". `containers`와 형제. PVC를 `claimName`으로 가리킴 |
| volumeMounts (컨테이너 레벨) | "그 창고를 이 컨테이너의 이 경로에 붙임". 컨테이너마다 다른 경로 가능. `name`으로 volumes와 연결 |
| masking | 볼륨을 기존 내용 있는 경로에 마운트하면 원래 내용이 가려짐. **docker named volume은 첫 마운트 시 복사하지만 K8s PVC는 복사 안 함** → 빈 채로 덮음 |
| Pending vs READY 0/1 | Pending=컨테이너 시작 전(스케줄·볼륨 미충족) / READY 0/1=컨테이너는 떴고 readiness만 실패. 진단 깊이가 다름 |

## 막힌 곳 → 해결
- **증상:** `web.yaml`에 PVC 마운트 후 apply → `Readiness probe failed: HTTP statuscode: 403`, READY 0/1.
  - **가설(coach):** "빈 PVC 볼륨이 nginx 기본 html 디렉터리를 덮어 `index.html`이 가려진 것 아닐까."
  - **진단:** `kubectl exec deploy/web -- ls -la /usr/share/nginx/html` → **디렉터리 비어있음**(test.txt조차 없음) = 가설 적중.
  - **원인:** 빈 PVC를 nginx 서빙 경로(`/usr/share/nginx/html`)에 마운트 → masking으로 `index.html` 가림 → nginx가 `/`에 줄 게 없음 → 403(404 아닌 Forbidden) → readiness 실패.
  - **처방:** `mountPath`를 nginx가 안 건드리는 경로(`/data` 류)로 이동 → 기본 index.html 생존 → `READY 1/1`. (reviewer로 직접 수정)
- **구조 오류:** `volumes:`를 컨테이너 안(volumeMounts와 같은 깊이)에 둠 → `containers`와 형제(Pod 레벨, 6칸)로 교정.
- **영속화 검증:** 새 경로에 파일 write → `kubectl delete pod`(self-healing 재생성) → 새 Pod에서 `cat`으로 파일 생존 확인. → 맨 처음 "Pod 죽으면 데이터 사라지나?"의 답이 Volume으로 뒤집힘.

## 퀴즈 결과
| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| PV/PVC apply 시 Pod 뜨나·무엇으로 존재 | "Pod 안 뜨고 volume이 뜸" | 워크로드 아닌 저장소 object로 API 등록 | ✅(표현만 보정) |
| volumes/volumeMounts 중 Pod 레벨·이유 | "volumes. 창고는 Pod가, 문은 컨테이너가" | 동일 | ✅ |
| PV 자동생성 메커니즘·방아쇠 필드 | "storageClassName 방아쇠, 메커니즘은 모름" | dynamic provisioning(프로비저너) | ✅(방아쇠 정확, 메커니즘 보강) |
| 403의 현상 이름·docker와 차이 | "masking. named volume은 복사, PVC는 복사 안 함" | 동일 | ✅ |
| PVC Pending 시 Pod 상태 | "아예 안 뜨니 다른 상태" | `Pending` (컨테이너 시작 전) | ✅(이름 Pending 확정) |

## 다음 액션
- [ ] ConfigMap/Secret — db 비번 등 env·시크릿 주입 (에어갭 시크릿 관리와 연결)
- [ ] 실제 db 이전 — PVC(`/var/lib/postgresql/data`) + Secret(POSTGRES_PASSWORD) 둘 다 필요. nginx 데모 졸업
- [ ] 정적 프로비저닝(PV 직접 작성) 1회 — 동적과 대조해 PV의 실체 체감
- [ ] accessModes RWO/ROX/RWX 차이 — 멀티 Pod 공유가 필요해질 때

> 이번 실습도 학습용 nginx 데모(db-pvc를 nginx에 임시 마운트해 바인딩·영속화만 검증). 실제 db 이전은 다음 액션.
