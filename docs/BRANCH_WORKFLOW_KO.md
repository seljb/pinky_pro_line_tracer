# 별도 개발 브랜치와 리뷰·통합 절차

**새 영상 검증 개발은 `feat/video-validation`에서 관리하며, 기존 `feat/line-alignment`는 기준 버전으로 유지합니다. 기능 브랜치를 통합 브랜치에서 검증한 뒤 PR과 팀원 리뷰를 거쳐 반영합니다. `main`에는 직접 push하지 않습니다.**

## 목차

1. [브랜치 역할](#브랜치-역할)
2. [노트북에서 새 작업 받기](#노트북에서-새-작업-받기)
3. [기능별 개발과 통합](#기능별-개발과-통합)
4. [커밋과 PR 규칙](#커밋과-pr-규칙)
5. [리뷰할 검증 결과](#리뷰할-검증-결과)
6. [원격 작업의 범위](#원격-작업의-범위)

## 브랜치 역할

| 브랜치 | 역할 | 반영 원칙 |
| --- | --- | --- |
| `main` | 팀 리뷰를 거친 기준 | 직접 push·강제 push 금지 |
| `feat/line-alignment` | 기존 선 합류·정렬과 사용설명서 기준 | 새 작업으로 이 브랜치를 덮어쓰지 않음 |
| `feat/video-validation` | 새 영상·명령 검증의 통합 개발 | 기능별 변경을 모아 통합 시험 |
| `fix/control-inputs` | 제어 시각·중복 프레임 입력 보강 | 실패 시 정지 요청 시험 |
| `fix/camera-cleanup` | 카메라 초기화 실패 자원 정리 | 모의 수명 계약 시험 |
| `fix/offline-package-data` | 설치 후 보정 파일 검색 | checkout 밖 실행 확인 |
| `feat/video-observation` | 픽셀 공간 검출·선 후보 관찰 | 기능 시험 후 통합 대상으로 검토 |
| `feat/video-replay` | 저장 사진·영상 재생과 비교 출력 | 관찰 API와 호환되는지 통합 시험 |
| `feat/offline-tooling` | 설치 진입점·합성 영상·오프라인 CI 설정 | 실제 로컬 명령과 원격 CI 상태 구분 |
| `docs/video-validation` | 사용설명서·검증 범위·브랜치 절차 | 실행 결과와 문서 대조 |
| `feat/command-validation` | 명령 선택·정지 조건과 합성 폐루프 | 실제 모터 연결과 구분해 시험 |

새 개발의 기준은 기존 브랜치의 `e658e29`입니다. 이 표는 각 브랜치의 목적을 설명하며, 원격 push·PR 생성·리뷰 승인·병합 완료 여부는 실제 GitHub 상태와 작업 결과 보고로 확인합니다.

통합 구조는 다음과 같습니다.

```text
feat/line-alignment (기존 기준)
└── feat/video-validation (새 통합 브랜치)
    ├── feat/video-observation
    ├── feat/video-replay
    └── feat/command-validation
```

구현 의존성 때문에 기능 브랜치가 앞선 기능을 기반으로 할 수 있습니다. 이 구조가 모든 기능이 서로 독립적인 같은 출발점에서 분기됐다는 뜻은 아닙니다. PR의 base와 변경 파일을 확인해 중복 변경을 검토합니다.

## 노트북에서 새 작업 받기

### 처음 clone하는 경우

```bash
git clone --branch feat/video-validation https://github.com/seljb/pinky_pro_line_tracer.git
cd pinky_pro_line_tracer
git branch --show-current
git log -5 --oneline
```

### 기존 clone이 있는 경우

먼저 작업 파일을 보존합니다. 아래 첫 명령에서 변경사항이 보이면 해당 작업을 커밋하거나 안전하게 보관한 뒤 브랜치를 전환합니다. 무조건 reset·clean하거나 다른 브랜치 파일로 덮어쓰지 않습니다.

```bash
git status
git fetch origin
git switch feat/video-validation
git pull --ff-only origin feat/video-validation
```

로컬 브랜치가 없으면 `git switch --track origin/feat/video-validation`로 만듭니다. 이미 로컬 브랜치가 있을 때 중복 생성하지 않습니다. 기존 정렬 버전을 보고 싶다면 작업을 보존한 뒤 `feat/line-alignment`로 전환합니다.

## 기능별 개발과 통합

**작업 의도를 작은 커밋으로 남기고 통합 전후 모두 필요한 시험을 실행합니다.**

1. 저장소의 기존 작업 파일과 브랜치를 확인합니다.
2. 해당 기능 브랜치를 준비하고 관련 파일만 수정합니다.
3. staged diff에서 무관한 변경·비밀정보·영상·산출물 포함 여부를 확인합니다.
4. 단위 시험과 해당 CLI의 실제 출력 파일을 확인합니다.
5. 기능 브랜치를 push하고 통합 대상에 PR을 준비합니다.
6. 리뷰·검사를 거쳐 기능을 통합하고 전체 시험을 다시 실행합니다.
7. 통합 결과를 `main`에 반영할 때도 별도 PR과 팀원 리뷰를 거칩니다.

로컬 통합 이력을 검토 가능하게 남길 때 `--no-ff` 병합을 사용할 수 있습니다. 이것은 팀원 리뷰 승인을 대신하지 않습니다. 최종 PR의 squash merge 여부는 팀 규칙과 리뷰 결과를 따릅니다.

충돌이 생기면 변경 의도를 확인하고 해결한 뒤 시험합니다. 공유 브랜치를 강제 push해 충돌을 숨기지 않습니다. 기존 소비자가 함께 바뀌는 계약 변경에는 관련 모듈과 명세의 영향을 PR에 기록합니다.

## 커밋과 PR 규칙

**커밋 제목·본문과 PR 제목은 영어이며 제목은 `type(scope): description` 형식으로 작성합니다.**

- scope는 `domain`, `session`, `pose`, `ui`, `serial`, `firmware`, `storage`, `data`, `docs`, `tooling`, `repo` 중 하나를 사용합니다.
- 제목은 영어 명령형 현재형, 끝 마침표 없이 72자 이내로 작성합니다.
- 하나의 커밋에는 한 가지 의도를 담습니다. 기능 추가와 무관한 전체 서식 변경을 섞지 않습니다.
- 복잡한 변경의 본문에는 변경 이유·동작·제약을 영어로 기록합니다. 실제 없는 이슈 번호를 만들지 않습니다.
- PR 설명은 한글을 허용하며 목적·변경 내용·실행한 검증·미검증 사항을 기록합니다.
- 팀원 최소 한 명의 리뷰를 받습니다. 작성자가 다른 사람의 승인을 대신하지 않습니다.
- `main` 보호·필수 리뷰·CI는 실제 GitHub 설정으로 적용됐는지 확인합니다. 문서만으로 활성화되지 않습니다.

예시 제목:

```text
feat(domain): add pixel-space black-line observation
feat(tooling): add offline video replay reports
test(domain): validate alignment command ownership and stop
```

위 문구는 형식 예시입니다. 실제 커밋의 변경 내용에 맞춰 제목과 본문을 작성합니다.

## 리뷰할 검증 결과

| 검토 항목 | 근거 |
| --- | --- |
| 선 검출 | 실제 생성된 마스크·오버레이·프레임 CSV |
| 영상 처리 비교 | 같은 입력·설정과 처리 방법별 결과 |
| 상태·정지·소유권 | 관련 단위 시험과 실패 시나리오 |
| 합성 이동 | 현재 실행의 시나리오 결과·허용오차·로그 |
| 실물 미검증 | 실제 카메라·ROS·모터·mux의 남은 점검 명시 |
| 데이터 보호 | 영상·실측 보정·토큰·가상환경·산출물 제외 |

시험 개수만으로 품질을 판단하지 않습니다. 실패·미실시·건너뜀을 성공과 구분하고 0개 시험 실행을 검증 완료로 기록하지 않습니다.

### 나중에 PR로 합치기

새 개발 전체를 기존 정렬 브랜치로 검토하려면 다음 비교 화면에서 PR을 만듭니다.

[기존 정렬 브랜치와 새 통합 브랜치 비교](https://github.com/seljb/pinky_pro_line_tracer/compare/feat/line-alignment...feat/video-validation?expand=1)

권장 PR 제목:

```text
feat(domain): add offline video and command validation
```

PR 본문에는 저장 영상 재생·픽셀 관찰·합성 명령 선택의 목적과 시험 결과를 기록합니다. 실제 로봇·ROS·외부 mux·전체 선 추종·직각 코너·내부 임무가 미검증/후속 범위임을 명시합니다. 팀원이 최소 한 명 리뷰한 뒤 반영합니다. 원격 API 접근이 제한된 현재 환경에서는 이 비교 화면과 문서를 제공하며 PR이 생성됐다고 주장하지 않습니다.

## 원격 작업의 범위

현재 클라우드 작업은 사용자의 개인 컴퓨터가 꺼져도 로컬 컴퓨터 파일·장비에 의존하지 않는 범위에서 진행할 수 있습니다. 응답이 끝난 뒤 계속 감시·개발하는 상시 에이전트를 설정한 것은 아닙니다.

클라우드에서 검증할 수 있는 것은 저장 영상 처리·순수 Python 제어·합성 시험입니다. 사용자의 Pinky 모터를 원격으로 실제 구동하거나 물리 검증을 완료했다고 기록하지 않습니다. 사용량의 특정 5시간 집계 한도만 골라 차감하거나 정확한 소진량을 제어할 수는 없습니다.

[영상 검증 사용법](VIDEO_VALIDATION_KO.md) · [개발 상태와 미완료 항목](DEVELOPMENT_STATUS_KO.md)
