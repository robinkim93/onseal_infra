# K8s 모델 PVC 오프라인 로드 완주 + 퀴즈 뱅크 프로세스 수정

- **날짜:** 2026-06-28
- **단계:** M1
- **모드:** coach(주) · quiz · delegate(모델 추출·HF 내부) · reviewer

## 한 줄 흐름
누적 퀴즈 백로그가 세션 시작/종료에 안 떠오르는 **구조적 결함**을 먼저 고치고(시작=워밍업·종료=retire 체크포인트 규칙 추가) A/B큐 다수를 출제했다. 이어 어제 9GB로 막혔던 K8s 모델 적재를 완주 — 이미지 9.16G→1.88G 슬림화, 모델은 PVC에 분리 적재, `HF_HOME`/`HF_HUB_OFFLINE` 두 계층 격리. 모델 로드가 **두 snapshot 구조 + `.no_exist` 부정 캐시**로 두 번 깨졌고, 마지막엔 `chunks` 테이블 부재(init이 K8s 이전 때 누락)까지 뚫어 `/ingest` end-to-end(`inserted:1`) 성공.

## 헷갈림 → 교정 궤적  ★핵심
| 헷갈린/몰랐던 것 | 내가 내놓은 답·추론 | 정확한 개념 |
|---|---|---|
| Bound PVC가 consumer를 잃으면 Pending으로 돌아가나 | "internal처럼 마운트 없으면 되돌아갈 듯" | **안 돌아감.** `Pending`=PV 없음 / `Bound`=PV 배정(영속·일방향). consumer 유무는 *마운트 축*이라 별개. 바인딩은 PVC `spec.volumeName`·PV `claimRef`에 기록돼 sticky. 안 그러면 Pod 죽을 때마다 데이터 소실 |
| WaitForFirstConsumer가 "사라지는" 것 | "consumer 나타나면 모드가 없어짐" | 모드는 **StorageClass 정책**이라 새 PVC마다 적용. "이 PVC의 *지연된 1회 바인딩*"이 실행됐을 뿐, 모드가 사라진 게 아님 |
| 호스트 docker에 api 이미지가 왜 남아야 하나 | "전부 이관됐으면 지워도 되지 않나" | 이관된 건 *모델*이지 *api(이미지)*가 아님. 노드는 빌드 못 함 → 호스트 Docker가 이미지 **출생지+선적항**, `kind load`로 노드 containerd에 실어보냄 |
| 모델 다운로드 막는 게 `imagePullPolicy`? | "네트워크 못 나가게 = IfNotPresent" | **계층 혼동.** `imagePullPolicy`=*이미지* 풀(K8s) / `HF_HUB_OFFLINE`=*모델* 다운로드(앱 런타임). 에어갭은 **두 계층 다** 막아야 함 |
| 노드 안 이미지는 kind 명령으로 보나 | "kind get images 같은 게 있을 듯" | kind엔 그런 조회 없음. 노드=Docker 컨테이너+자체 containerd → `docker exec <노드> crictl images`가 정석(CRI=K8s↔런타임 표준 규약) |

## 다룬 개념
| 개념 | 한 줄 핵심 |
|---|---|
| PV/PVC 생명주기 분리 | 데이터는 PV(노드 디스크)에. Pod는 PVC를 *마운트*만 → Pod 삭제해도 데이터 영속 |
| Pending vs Bound | 바인딩 축(PV 유무, 영속) ≠ 마운트 축(누가 쓰나, 휘발). consumer 잃어도 Bound 유지 |
| WaitForFirstConsumer | SC 바인딩 정책. 첫 consumer가 노드를 정할 때까지 바인딩 지연(consumer 없으면 Pending=정상) |
| 일회용 writer Pod(loader) | PVC는 cp 직접 불가 → 마운트할 Pod 필요. 바이트 붓는 깔때기, 끝나면 폐기 |
| 패키징 분리(코드/모델) | 변경 빈도 분리. 코드 한 줄에 9GB 재빌드·USB 재운반 회피. 이미지 슬림, 모델은 PVC |
| 에어갭 2계층 격리 | `imagePullPolicy:IfNotPresent`(이미지) + `HF_HOME`/`HF_HUB_OFFLINE`(모델). 계층마다 따로 |
| HF 캐시 구조 | `refs/main`→커밋, `snapshots/<hash>/`(파일 symlink), `blobs/`(실데이터), `.no_exist`(부정 캐시) |
| `.no_exist` 부정 캐시 | "이 파일 없음"을 기록 → 나중에 파일 넣어도 오프라인 조회가 단락. 삭제해야 재인식 |
| crictl / CRI | 노드 containerd를 다루는 CLI. `docker exec <노드> crictl images`로 적재 확인 |
| postgres init 타이밍 | `docker-entrypoint-initdb.d`는 **빈 PGDATA 첫 init 때만** 실행. 이미 init된 PVC엔 재실행 안 됨 |

## 막힌 곳 → 해결
- **퀴즈 뱅크 결함:** 미통과 항목이 안 떠오름 → 진단: 뱅크가 *세션 종료에 쓰기*만 하고 *시작/종료에 읽기/출제* 트리거가 없어 **write-only graveyard**. A#5~14가 열흘 방치됨이 증거. → learning-mode에 **Spaced-retrieval checkpoints**(시작=워밍업, 종료=retire), learning-log 2.5에 **"먼저 출제→그다음 적립"** 규칙 추가.
- **Docker 데몬 wedged:** `kubectl`은 되는데 `kind get clusters` hang. 가설="완전히 꺼짐"은 kubectl 동작과 모순 → "데몬 wedged(메모리)". `docker ps`로 "꺼짐 vs 멈춤" 판별 → 메모리 풀자 복귀.
- **모델 로드 실패 ①(snapshot):** `OSError: ... no file named pytorch_model.bin or model.safetensors`. 네트워크 에러 아님 → HF_HOME/OFFLINE 배선은 정상, *가중치 파일*만 없음. 원인=모델이 두 snapshot으로 쪼개짐(`5617`=ST설정+.bin / `9a06`=safetensors만), 내가 추출 때 "중복"이라며 .bin 삭제 → `refs/main`이 가리키는 `5617`에 가중치 0. 처방=PVC에 남은 safetensors blob을 `5617`에 symlink 연결.
- **모델 로드 실패 ②(.no_exist):** symlink 넣어도 같은 에러. api Pod는 그 파일을 **보는데도** transformers가 "없음". 원인=`.no_exist/5617/model.safetensors` **부정 캐시**(빌드 때 .bin으로 받으며 기록)가 오프라인 조회를 단락. 처방=`.no_exist` 제거 → 라이브 로드 `LOAD_OK`(가중치 391개 적재).
- **`chunks` 테이블 부재:** embed는 통과, `insert_chunks`에서 `UndefinedTable`. 원인=compose의 `docker-entrypoint-initdb.d` init이 K8s 이전 때 누락 + 이미 init된 PGDATA라 어차피 재실행 안 됨. 처방=멱등 `init_db.sql`을 떠 있는 db에 `psql`로 직접 적용 → `/ingest`=`inserted:1`.
- **자책 메모:** 추출·삭제를 "셋업"이라며 말없이 처리해 ①을 유발했고, 슬림 재빌드가 9GB 태그를 가져가 원본 이미지가 dangling→소멸하는 것도 미예측. delegate 처리의 부작용을 사용자에게 안 보인 게 문제.

## 퀴즈 결과 (A/B큐 백로그)
| 문항 | 내 답 | 정답 | 판정 |
|---|---|---|---|
| #7 도커 레이어 캐시 | "변경점부터 재실행" | 변경 레이어 *이하* 전부 무효화 | ✅ 졸업 |
| #8 구조 vs 규율 | (재출제) internal=all-or-nothing, inbound도 죽어 egress-only 부족 | + 호스트 방화벽/NetworkPolicy 필요 | ✅ 졸업 |
| #11 멤버십=union / #12 DNS=Service명 / #14 RollingUpdate=무중단 | 합집합 / Service+CoreDNS / 무중단 | 동일 | ✅ 졸업 |
| B25 accessMode vs readOnly | 강제는 volumeMount, RWO=노드 단위 | 동일 | ✅ 졸업 |
| #5 lazy singleton(뒷부분) | "외부 _model None 유지" | `UnboundLocalError`(대입문이 이름을 지역으로 확정) | ❌ 재교육 |
| #6 에어갭 실증 | 결론만 | build는 네트워크 *있던* 때라 증명 못 함 | 부분 |
| #9 이벤트 vs 로그 | "pod로그 vs 컨테이너로그" | describe=이벤트(증상) / logs=프로세스 출력(원인) | ❌ 재교육 |
| #10 시크릿 관리 | "configmap/secret" | self-hosted secrets manager(Vault). configmap은 평문/Secret은 base64 | 부분 |
| B23 kind / B24 imagePullPolicy / B26 WaitForFirstConsumer / B27 패키징분리 | 부분·미상 | 각 정답 재교육 | →A큐 이동 추적 |

## 다음 액션
- [ ] **모델 provisioning 재현화(최우선).** 지금 PVC 모델은 docker-cp+수동 symlink+`.no_exist`삭제로 겨우 살림 = fresh 배포 시 동일 파손. 9GB 원본 이미지도 소멸 → 모델 출처가 PVC 단일점. 네트워크 있는 일회성 Job으로 볼륨에 정상 다운로드하는 선언형 경로로 교체.
- [ ] `init_db.sql`을 ConfigMap→`/docker-entrypoint-initdb.d` 배선(fresh 배포용; 현 PGDATA엔 재실행 안 됨 유의).
- [ ] db-config·db-secret 선언형 파일화(원래 복선, 미해결).
- [ ] ollama K8s화 → `/query` end-to-end.
- [ ] 9GB 원본 이미지는 이미 소멸 — 모델 백업 부재 리스크 인지(provisioning 재현화로 해소).
- [ ] 남은 A큐 #5·6·9·10·13·15~18 → 다음 세션 시작 워밍업에서 재출제.
