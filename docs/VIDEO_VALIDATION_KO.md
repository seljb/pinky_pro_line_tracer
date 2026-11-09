# 영상 재생부터 주행 명령까지 오프라인 검증하기

**이 브랜치는 저장 영상을 반복 재생해 선 검출 결과를 비교하고, 합성 카메라에서 생성한 정렬 명령을 모의 로봇에 적용하는 개발 환경입니다. 실제 카메라·ROS 전송·모터·외부 mux의 검증은 별도입니다.**

## 목차

1. [먼저 구분할 두 가지 실행](#먼저-구분할-두-가지-실행)
2. [환경과 설치](#환경과-설치)
3. [사진과 영상을 비교하기](#사진과-영상을-비교하기)
4. [결과를 읽는 방법](#결과를-읽는-방법)
5. [합성 주행 명령 검증](#합성-주행-명령-검증)
6. [오류와 반복 실행](#오류와-반복-실행)
7. [실제 Pinky로 이어가는 순서](#실제-pinky로-이어가는-순서)

## 먼저 구분할 두 가지 실행

| 실행 | 입력 | 확인할 수 있는 것 | 확인할 수 없는 것 |
| --- | --- | --- | --- |
| `video_replay` | 저장 사진·영상·이미지 폴더 | 검은 선 마스크, 선택한 중심점, 픽셀 오차, 검출 상태, 처리 시간 | 실제 거리·물리 속도·로봇 주행 성능 |
| `validation_run` | 합성 카메라와 이상적인 오도메트리 | 검출→기존 정렬 제어기→명령 선택→이상적인 이동의 폐루프와 정지 조건 | 실물 센서·모터 지연·슬립·실제 mux·비상정지 |

영상 재생에서 나온 `error_px`는 **픽셀 오차**입니다. 실측 카메라 보정이 없는 영상을 임의의 m·rad 오차나 모터 속도로 바꾸지 않습니다. 합성 검증에서 쓰는 보정값은 가상 모델 전용입니다.

## 환경과 설치

Python 3.12와 저장소 루트를 기준으로 합니다. ROS 노드를 실행하는 시스템 Jazzy 환경과 이 오프라인 가상환경을 분리합니다.

```bash
cd /PATH/TO/pinky_pro_line_tracer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m black --check .
python -m pytest -q
```

설치나 시험이 실패하면 결과를 읽고 원인을 해결한 뒤 다음 단계로 진행합니다. 장치·ROS 없이 재생과 합성 시험을 실행할 수 있습니다. 코드의 단위 시험 통과와 실제 카메라 영상의 품질은 서로 다른 검증입니다.

## 사진과 영상을 비교하기

**같은 입력을 각 방법으로 처리해 마스크와 실패 이유를 비교하세요. 초기 문턱값을 실물 최적값으로 해석하지 않습니다.**

실제 파일이 아직 없다면 합성 입력으로 도구 연결부터 확인할 수 있습니다. 이 이미지는 실제 트랙 사진을 대신하는 성능 평가 자료가 아닙니다.

```bash
python -m pinky_line_alignment.offline_demo \
  --output /tmp/pinky-replay-input.png
python -m pinky_line_alignment.video_replay \
  --input /tmp/pinky-replay-input.png \
  --output-dir /tmp/pinky-synthetic-replay \
  --methods fixed otsu adaptive \
  --save-frames
```

합성 동영상으로 마스크·CSV·영상 저장도 확인할 수 있습니다.

```bash
python scripts/make_synthetic_video.py --output /tmp/pinky-input.avi
python -m pinky_line_alignment.video_replay \
  --input /tmp/pinky-input.avi --output-dir /tmp/pinky-clip-replay \
  --methods fixed otsu adaptive --save-frames --save-video
```

동영상과 함께 생성되는 `.scenes.csv`는 합성 장면 이름이며 실물 정답 데이터가 아닙니다.

### 1. 한 장의 사진

```bash
python -m pinky_line_alignment.video_replay \
  --input /ABS/PATH/track.png \
  --output-dir /tmp/pinky-image-comparison \
  --methods fixed otsu adaptive \
  --save-frames
```

`/ABS/PATH/track.png`는 실제 파일 경로로 바꿉니다. 카메라 번호나 네트워크 주소를 입력하는 도구가 아닙니다. 이 명령은 카메라를 열거나 ROS 속도 명령을 발행하지 않습니다.

### 2. 저장 영상

```bash
python -m pinky_line_alignment.video_replay \
  --input /ABS/PATH/pinky-camera.mp4 \
  --output-dir /tmp/pinky-video-comparison \
  --methods fixed otsu adaptive \
  --max-frames 300 \
  --save-video
```

먼저 짧은 구간을 처리해 프레임 수·해상도·입력 FPS와 코덱 출력이 정상인지 확인합니다. `--max-frames`로 제한한 결과를 영상 전체 처리 결과라고 기록하지 않습니다.

### 3. 순서가 있는 이미지 폴더

```bash
python -m pinky_line_alignment.video_replay \
  --input /ABS/PATH/frames \
  --output-dir /tmp/pinky-frame-comparison \
  --methods fixed \
  --save-frames
```

파일 이름이 순서대로 정렬되도록 `frame_0001.png` 형식을 사용합니다. 이미지 폴더의 재생 시각은 실제 카메라 촬영 시각을 자동 복원한 것이 아닙니다.

이미지 시퀀스의 재생 FPS는 `--image-fps`로 지정하며 기본값은 10입니다. 영상은 사용 가능한 파일 FPS 메타데이터를 우선 사용하고, 유효하지 않으면 이 값을 사용합니다. 처리 시간이 빨라졌다고 입력 영상의 실제 FPS가 높아지는 것은 아닙니다.

### 4. 방법과 관찰 설정

| 방법 | 의미 | 실제 영상에서 확인할 점 |
| --- | --- | --- |
| `fixed` | 낮은 밝기 범위를 검은 선으로 분리 | 그림자·노출 변화에서 선 누락 여부 |
| `otsu` | 영상 밝기 분포로 문턱을 계산 | 흰 면적이 크거나 그림자가 있을 때 선택 결과 |
| `adaptive` | 주변 밝기를 기준으로 어두운 영역을 분리 | 테이블 이음새와 반사 경계의 오검출 |

`--config`는 관찰 설정 JSON을 읽습니다. 정확한 허용 키와 기본값은 [observation.py](../pinky_line_alignment/observation.py)의 `ObservationConfig`를 기준으로 합니다. 처리 방법은 `--methods`에서 지정하므로 설정 JSON에 `method` 키를 넣지 않습니다. 알 수 없는 키는 오류로 거절합니다.

다음은 형식 예제이며 실제 카메라의 최적값이 아닙니다.

```json
{
  "threshold": 100,
  "roi": [0.0, 0.25, 1.0, 1.0],
  "blur_size": 3,
  "open_size": 0,
  "close_size": 0,
  "sample_count": 9,
  "min_support": 5
}
```

파일을 `/ABS/PATH/observation.json`에 저장했다면 재생 명령에 `--config /ABS/PATH/observation.json`을 추가합니다. ROI는 `(left, top, right, bottom)` 순서의 **0~1 정규화 영상 좌표**이며 바닥의 m 좌표가 아닙니다. 필터 크기는 0(비활성) 또는 허용 범위의 홀수입니다.

blur와 morphology 크기는 실제 영상에서 필요성을 확인한 뒤 조정합니다. 강한 잡음 제거가 원거리의 가는 테이프를 지울 수 있습니다. 여러 선 가지가 모호하면 하나의 평균 중심을 만들어 확신하는 대신 무효 결과와 이유를 확인합니다.

연결된 마스크 성분과 원본 회색조의 양측 대비를 함께 검사합니다. `min_contrast_gray` 기본값 10은 개발용 밝기 대비 기준입니다. 넓은 그림자의 한쪽 경계가 adaptive에서 얇은 선으로 보이는 합성 사례를 거부하도록 검사합니다.

모든 코너·분기·그림자가 거부되는 것은 아닙니다. 표본 행 사이의 짧은 가지나 실제 테이프처럼 보이는 다른 검은 물체는 통과할 수 있습니다. 이 검출기는 경로 결정기나 안전 주행 허가기가 아닙니다.

## 결과를 읽는 방법

**검출됨은 정확함을 뜻하지 않습니다. 마스크·중심점·정답 표시를 함께 검토하세요.**

각 처리 방법의 CSV에는 프레임별 관측 결과를 기록하고, 요약 JSON에는 입력 해시·설정·도구 버전·프레임 수와 처리 통계를 기록합니다. 선택한 옵션에 따라 마스크·오버레이 이미지 또는 결과 영상을 저장합니다.

```text
출력 폴더/
├── summary.json
├── fixed/
│   ├── frames.csv
│   ├── annotated.avi                 # --save-video
│   └── frames/                       # --save-frames
│       ├── 000000_mask.png
│       └── 000000_overlay.png
├── otsu/                             # 선택한 방법만 생성
└── adaptive/
```

`summary.json`의 `status`가 `completed`인지 확인합니다. `mode`는 `pixel_only_no_motion`, `accuracy_evaluated`와 `physical_robot_validated`는 false입니다. 프레임 제한을 사용했다면 `frame_limit_reached`도 확인합니다. 처리 중 오류가 난 경우의 `failed` 요약을 정상 완료 결과로 사용하지 않습니다.

| 값 | 의미 | 해석 주의사항 |
| --- | --- | --- |
| `frame_index` | 이번 입력의 프레임 번호 | 실제 카메라 하드웨어 프레임 번호와 다를 수 있음 |
| `timestamp_s` | 입력 재생 순서의 시간(초) | 실제 노출 시각·전송 지연 검증값이 아님 |
| `valid` | 현재 설정에서 유효한 선을 선택했는지 | 실측 정답과 일치했다는 뜻이 아님 |
| `error_px` | 영상 기준과 선택된 선 중심의 가로 차이 | m·cm·rad·주행 속도로 해석하지 않기 |
| `ambiguous` | 여러 가지 등으로 선택이 모호한지 | 원인 확인 없이 주행 명령으로 사용하지 않기 |
| `support` | 선택을 지지한 표본 행의 수 | 성공 확률이나 평가 정확도가 아님 |
| `reason` | 유효/무효 판단 이유 | 선 손실과 입력 오류를 구분해 기록 |
| `processing_ms` | 해당 프레임 처리에 사용한 시간 | 카메라→모터의 종단 지연이 아님 |

같은 프레임에서 비교해야 방법별 차이를 평가할 수 있습니다. 실제 선 중심이나 가지를 정답으로 표시하지 않았다면 검출률만으로 정확도·성공률을 주장하지 않습니다. 반사·이음새·코너·선 손실을 포함한 검증 프레임을 따로 남기세요.

## 합성 주행 명령 검증

**이 실행은 이미지를 입력으로 받는 기존 정렬 제어기와 명령 선택 조건을 함께 시험합니다. 실제 Pinky를 움직이지 않습니다.**

```bash
python -m pinky_line_alignment.validation_run \
  --output-dir /tmp/pinky-command-validation
```

실행 흐름은 다음과 같습니다.

```text
합성 카메라 영상
→ 실측값이 아닌 가상 보정 모델의 LineDetector
→ 기존 AlignmentController
→ CommandGate의 활성화·소유권·시효·정지 조건
→ 이상적인 차동구동 위치 갱신
→ 다음 합성 영상
```

좌·우 8cm 시작 정렬 시나리오와 관측 상실·정지 조건을 구분해 확인합니다. 시나리오 이름은 `align_left`, `align_right`, `camera_dropout`, `operator_stop`이며 실행 결과는 해당 이름의 CSV와 `summary.json`에서 확인합니다. 각 시나리오의 기대 결과를 충족하지 못하면 CLI는 비정상 종료합니다.

`--step-s`는 가상 적분 간격(기본 0.04초), `--max-s`는 시나리오의 가상 시간 예산(기본 55초)입니다. 실제 작업 소요 시간이나 실물 제어 주기를 보장하는 값이 아닙니다. 요약의 `physical_robot_tested`, `ros_transport_tested`, `physical_mux_tested`는 모두 false로 기록됩니다.

명령 게이트는 기본 비활성 상태입니다. 코드에서 `set_enabled(True, now_s)` → `select_owner(...)` → 해당 소유자의 새 `submit(...)` → `decide(now_s)` 순서로 요청을 검사합니다. 소유자는 `alignment` 또는 `follower`이며 follower 선택에는 신선한 준비 상태가 추가로 필요합니다. 정지 요청과 만료된 요청은 0 속도로 처리합니다.

`stop()`은 정지 상태를 유지합니다. `reset_stop()`만으로 이전 명령이 다시 출력되지 않으며 명시적인 재활성화·소유자 선택·새 요청이 필요합니다. 이 API는 코드 연결과 시험을 위한 것이며 CLI에서 실제 모터를 켜는 명령이 아닙니다.

`CommandGate`는 **소프트웨어 요청 선택 로직**입니다. 실제 `/cmd_vel` 토픽에 연결된 mux, 장치의 watchdog, 물리 비상정지 장치가 설치됐다는 뜻은 아닙니다. 팀원이 담당한 선 추종 알고리즘도 이 실행에서 완성됐다고 해석하지 않습니다.

기존 합성 렌더러는 이상적인 단일 직선을 사용하며 슬립·장애물·실제 촬영 지연을 모델링하지 않습니다. 직각 코너 통과나 내부 작업 위치 이동의 성능 시험이 아닙니다.

## 오류와 반복 실행

| 상황 | 다음 행동 |
| --- | --- |
| 입력 파일을 찾지 못함 | 실제 절대경로와 파일 접근 여부 확인 |
| 사진·영상 디코딩 실패 | 원본 손상·지원 코덱·파일 확장자와 내용 확인 |
| 폴더에 처리할 이미지가 없음 | 지원 이미지 파일과 이름 순서 확인 |
| 기존 출력 폴더가 있음 | 기존 결과를 보존하고 새 출력 폴더 이름 사용 |
| 잘못된 JSON·ROI·문턱·필터 크기 | 오류에 나온 설정을 수정하고 다시 실행 |
| 저장 실패·영상 writer 실패 | 저장 공간·경로 권한·코덱 지원 확인 |
| 선이 계속 무효 | 입력 오류와 선 검출 실패를 구분하고 ROI·조명·가지 모호함 확인 |

기존 결과를 성공한 새 결과처럼 재사용하지 않습니다. 실패한 실행에서 남은 파일은 성공 보고 자료로 사용하지 않습니다. 출력물은 `/tmp` 또는 checkout 밖 경로에 저장하고 사용자 영상·실측 보정·토큰을 커밋하지 않습니다.

## 실제 Pinky로 이어가는 순서

**한국 시간 2026-11-11의 첫 현장 목표는 모터 OFF 센서 확인과 실제 영상 수집입니다.**

1. `feat/video-validation`을 받아 기존 정렬 브랜치와 새 개발 브랜치를 구분합니다.
2. 오프라인 재생·단위 시험을 실행해 도구가 작동하는지 확인합니다.
3. 가상환경을 종료한 별도 터미널에서 시스템 ROS 2 Jazzy를 활성화하고 빌드합니다.
4. 모터를 비활성화한 상태로 실제 카메라·`/odom`·토픽 타입·QoS·시각을 확인합니다.
5. 실제 카메라로 직선·좌우 코너·반사·그림자·이음새·선 손실 영상을 수집합니다.
6. 해상도·카메라 높이/각도·테이프 폭과 실측 보정·독립 검증 오차를 기록합니다.
7. 팀 선 추종과의 준비 상태·소유권 계약, 외부 mux·정지·낙하 방지 조건을 검증한 뒤 별도 주행 시험을 계획합니다.

[기존 현장 체크리스트](NEXT_DAY_CHECKLIST_KO.md)는 기존 `feat/line-alignment` 기준의 기록입니다. 새 작업은 이 문서와 [브랜치 안내](BRANCH_WORKFLOW_KO.md)를 함께 읽으세요. 문서를 만들거나 수정해도 Notion에 자동 동기화되지 않습니다.
