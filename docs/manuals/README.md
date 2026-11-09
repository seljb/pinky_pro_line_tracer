# 파일별 사용설명서

**프로젝트 파일 각각의 역할·사용법·입출력·주의사항을 안내합니다.** 실행 전에 루트 안내와 내일 체크리스트를 먼저 읽으세요.

## 목차

1. [처음 읽을 문서](#처음-읽을-문서)
2. [파일별 설명서](#파일별-설명서)
3. [새 문서와 설정](#새-문서와-설정)

## 처음 읽을 문서

- [새 영상·명령 검증 안내](../VIDEO_VALIDATION_KO.md)
- [새 브랜치 받기](../BRANCH_WORKFLOW_KO.md)
- [프로젝트 시작 안내](../../README.md)
- [2026-11-11 노트북 작업 목록](../NEXT_DAY_CHECKLIST_KO.md)
- [Python 규칙 적용 범위](../PYTHON_STYLE_KO.md)

## 파일별 설명서

| 원본 파일 | 역할 |
| --- | --- |
| [`.gitignore`](files/.gitignore/README.md) | 실측 자료와 개발 산출물이 Git에 올라가지 않도록 제외합니다. |
| [`README.md`](files/README.md/README.md) | 프로젝트의 실행 순서와 실물 검증 한계를 안내합니다. |
| [`config/floor_pairs_example.json`](files/config/floor_pairs_example.json/README.md) | 영상 픽셀과 바닥 실측 좌표의 대응점 형식을 보여줍니다. |
| [`config/holdout_example.json`](files/config/holdout_example.json/README.md) | 독립 검증점 파일의 형식을 보여줍니다. |
| [`config/real_calibration_template.json`](files/config/real_calibration_template.json/README.md) | 실측 보정 파일의 필드 형식을 보여줍니다. |
| [`config/synthetic_calibration.json`](files/config/synthetic_calibration.json/README.md) | 오프라인 시험 전용 가상 카메라 변환을 제공합니다. |
| [`docs/GITHUB_REFERENCES.md`](files/docs/GITHUB_REFERENCES.md/README.md) | 구현 때 참고했다고 기록된 외부 출처와 활용 이유를 정리합니다. |
| [`docs/GITHUB_UPLOAD_PREP_KO.md`](files/docs/GITHUB_UPLOAD_PREP_KO.md/README.md) | 초기 개인 저장소 업로드 준비 과정을 보관합니다. |
| [`docs/IMPLEMENTATION_KO.md`](files/docs/IMPLEMENTATION_KO.md/README.md) | 초기 알고리즘 선택과 구현·시험 기록을 설명합니다. |
| [`docs/NOTION_IMPLEMENTATION.md`](files/docs/NOTION_IMPLEMENTATION.md/README.md) | 이전 Notion 구현 기록의 저장소 사본을 제공합니다. |
| [`docs/ROBOT_TEST_CHECKLIST_KO.md`](files/docs/ROBOT_TEST_CHECKLIST_KO.md/README.md) | 실물 연결 전 센서·보정·안전 확인 순서를 제공합니다. |
| [`logs/experiment_template.csv`](files/logs/experiment_template.csv/README.md) | 실물 실험 조건과 결과를 기록할 CSV 헤더를 제공합니다. |
| [`package.xml`](files/package.xml/README.md) | ROS 2 빌드 방식과 런타임 의존성을 선언합니다. |
| [`pinky_line_alignment/__init__.py`](files/pinky_line_alignment/__init__.py/README.md) | Python 패키지 경계를 선언합니다. |
| [`pinky_line_alignment/alignment_node.py`](files/pinky_line_alignment/alignment_node.py/README.md) | ROS 이미지·odom·서비스를 정렬 제어기에 연결합니다. |
| [`pinky_line_alignment/calibration.py`](files/pinky_line_alignment/calibration.py/README.md) | 내부 보정·바닥 변환·독립 오차 검증을 수행합니다. |
| [`pinky_line_alignment/camera_node.py`](files/pinky_line_alignment/camera_node.py/README.md) | Pinky 또는 USB 카메라 영상을 ROS Image로 발행합니다. |
| [`pinky_line_alignment/closed_loop_sim.py`](files/pinky_line_alignment/closed_loop_sim.py/README.md) | 합성 카메라와 이상적인 오도메트리로 정렬 루프를 시험합니다. |
| [`pinky_line_alignment/control.py`](files/pinky_line_alignment/control.py/README.md) | 최신 센서 관측으로 정렬 상태와 속도 요청을 계산합니다. |
| [`pinky_line_alignment/offline_demo.py`](files/pinky_line_alignment/offline_demo.py/README.md) | 가상 선 영상을 만들고 검출 결과 이미지를 저장합니다. |
| [`pinky_line_alignment/vision.py`](files/pinky_line_alignment/vision.py/README.md) | 카메라 영상에서 단일 검은 선의 바닥 위치와 방향을 추정합니다. |
| [`resource/pinky_line_alignment`](files/resource/pinky_line_alignment/README.md) | ament 인덱스에서 패키지를 발견하기 위한 빈 마커입니다. |
| [`scripts/verify_offline.sh`](files/scripts/verify_offline.sh/README.md) | 로봇 없이 문법·테스트·합성 검출·정렬을 차례로 검증합니다. |
| [`setup.cfg`](files/setup.cfg/README.md) | ROS 실행 스크립트의 설치 위치를 지정합니다. |
| [`setup.py`](files/setup.py/README.md) | ROS Python 패키지와 실행 진입점을 등록합니다. |
| [`tests/test_calibration.py`](files/tests/test_calibration.py/README.md) | 가상 대응점으로 보정 계산과 검증 플래그를 확인합니다. |
| [`tests/test_closed_loop_sim.py`](files/tests/test_closed_loop_sim.py/README.md) | 검출기와 제어기의 합성 폐루프 성공 조건을 검사합니다. |
| [`tests/test_control.py`](files/tests/test_control.py/README.md) | 시작·정지·센서 손실·인계 거부 등 상태 전이를 검사합니다. |
| [`tests/test_vision.py`](files/tests/test_vision.py/README.md) | 합성 선 검출과 영상 크기·무검출 처리를 검사합니다. |
| [`pyproject.toml`](files/pyproject.toml/README.md) | Black의 Python 3.12·80자 포맷 기준을 설정합니다. |
| [`requirements-dev.txt`](files/requirements-dev.txt/README.md) | 오프라인 검증에 사용한 직접 의존성 버전을 고정합니다. |
| [`docs/NEXT_DAY_CHECKLIST_KO.md`](files/docs/NEXT_DAY_CHECKLIST_KO.md/README.md) | 11월 11일 노트북에서 할 일을 순서와 완료 기준으로 안내합니다. |
| [`docs/PYTHON_STYLE_KO.md`](files/docs/PYTHON_STYLE_KO.md/README.md) | 사용자가 제공한 Python 규칙의 적용 범위와 미완료 항목을 기록합니다. |
| [`pinky_line_alignment/observation.py`](files/pinky_line_alignment/observation.py/README.md) | 픽셀 공간에서 검은 테이프 후보를 관찰하고 모호한 경로를 거부합니다. |
| [`pinky_line_alignment/video_replay.py`](files/pinky_line_alignment/video_replay.py/README.md) | 저장 사진·동영상을 같은 조건으로 재생해 검출 결과를 비교합니다. |
| [`pinky_line_alignment/command_gate.py`](files/pinky_line_alignment/command_gate.py/README.md) | 소프트웨어 속도 요청의 소유권·유효시간·정지 조건을 선택합니다. |
| [`pinky_line_alignment/validation_run.py`](files/pinky_line_alignment/validation_run.py/README.md) | 합성 영상부터 정렬 명령과 이상적인 이동까지 폐루프를 검증합니다. |
| [`pinky_line_alignment/resource_paths.py`](files/pinky_line_alignment/resource_paths.py/README.md) | 소스와 설치 환경에서 패키지 보정 JSON의 실제 위치를 찾습니다. |
| [`scripts/make_synthetic_video.py`](files/scripts/make_synthetic_video.py/README.md) | 재생 도구 점검용 합성 AVI와 장면 종류 CSV를 만듭니다. |
| [`config/video_observation_example.json`](files/config/video_observation_example.json/README.md) | 영상 관찰 옵션의 JSON 형식과 개발용 기본값을 보여줍니다. |
| [`.github/workflows/offline-validation.yml`](files/.github/workflows/offline-validation.yml/README.md) | PR과 기능/수정 브랜치 push에서 오프라인 검사를 실행하도록 정의합니다. |
| [`docs/VIDEO_VALIDATION_KO.md`](files/docs/VIDEO_VALIDATION_KO.md/README.md) | 재생·합성 명령 검증의 전체 실행 순서와 결과 해석을 안내합니다. |
| [`docs/BRANCH_WORKFLOW_KO.md`](files/docs/BRANCH_WORKFLOW_KO.md/README.md) | 기존 브랜치를 보존하면서 기능 브랜치를 통합하는 방법을 안내합니다. |
| [`docs/DEVELOPMENT_STATUS_KO.md`](files/docs/DEVELOPMENT_STATUS_KO.md/README.md) | 검증된 개발 기능과 실물 미검증·후속 과제를 기록합니다. |
| [`tests/test_observation.py`](files/tests/test_observation.py/README.md) | 분할·ROI·연결성·양측 대비·모호함·시각 역행의 영상 관찰 경계를 검사합니다. |
| [`tests/test_video_replay.py`](files/tests/test_video_replay.py/README.md) | 실제 생성 파일로 재생·CSV·요약·프레임 제한·저장 실패를 검사합니다. |
| [`tests/test_command_gate.py`](files/tests/test_command_gate.py/README.md) | 활성화·소유권·정지 래치·유효시간·잘못된 시각을 검사합니다. |
| [`tests/test_validation_run.py`](files/tests/test_validation_run.py/README.md) | 실제 합성 검출·제어·선택·운동학과 출력 CSV의 결과를 검사합니다. |
| [`tests/test_camera_lifecycle.py`](files/tests/test_camera_lifecycle.py/README.md) | 모의 ROS와 카메라로 초기화 실패·자원 정리 계약을 검사합니다. |
| [`tests/test_control_inputs.py`](files/tests/test_control_inputs.py/README.md) | 중복 프레임·잘못된 제어 시각·누락 입력의 정지 요청을 검사합니다. |
| [`tests/test_resource_paths.py`](files/tests/test_resource_paths.py/README.md) | 패키지 보정 파일 찾기와 경로 입력 거부를 검사합니다. |
| [`tests/test_simulation_inputs.py`](files/tests/test_simulation_inputs.py/README.md) | 0·음수·비유한·빈 시뮬레이션 시간 예산을 거부하는지 검사합니다. |

## 새 문서와 설정

- `docs/manuals/**/README.md`: 각 원본 파일의 설명서입니다. 설명서 자체의 설명서를 재귀 생성하지 않습니다.
- `docs/NEXT_DAY_CHECKLIST_KO.md`: 내일 작업 순서와 완료 기준입니다. Notion에 자동 동기화되지 않습니다.
- `docs/PYTHON_STYLE_KO.md`: 전달받은 팀 Python 기준의 적용 범위·예외·후속 과제입니다.
- `pyproject.toml`: Black의 Python 3.12·80자 설정입니다.
- `requirements-dev.txt`: 문서·주석·서식 변경 검증에 사용한 개발 도구 버전입니다.
