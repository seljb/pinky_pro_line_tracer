# Python 규칙 적용 현황

**이번 변경은 영어 공개 API docstring·한글 학습 주석·Black 80자 서식과 사용설명서를 적용합니다. 팀 Python 규칙 전체 준수나 ROS/실물 검증 완료를 뜻하지 않습니다.** 기준은 사용자가 이 대화에 제공한 Python 및 모듈화 규칙이며 Notion 원본을 직접 읽었다고 주장하지 않습니다.

## 목차

1. [적용 기준](#적용-기준)
2. [실행 방법](#실행-방법)
3. [이번에 적용한 항목](#이번에-적용한-항목)
4. [추가 정비가 필요한 항목](#추가-정비가-필요한-항목)
5. [설계 경계](#설계-경계)

## 적용 기준

- Python 3.12 / Ubuntu 24.04 / ROS 2 Jazzy를 개발 기준으로 사용합니다.
- 코드 식별자와 공개 API docstring은 영어, 학습용 주석과 설명서는 한글입니다.
- 공개 API 설명은 결론을 첫 문장에 쓰고 필요한 Args·Returns·Raises와 m/rad/s 단위, None 의미를 적습니다.
- 공백 4칸과 80자 기준을 사용합니다. 코드 식별자를 바꾸는 대규모 리팩터링은 이번에 포함하지 않습니다.
- Git 커밋 제목·본문은 영어이며 필수 scope와 72자 제목 제한을 따릅니다.

## 실행 방법

저장소 루트의 오프라인 가상환경에서 실행합니다. ROS 노드 실행은 시스템 Jazzy 환경과 분리합니다.

```bash
python -m pip install -r requirements-dev.txt
python -m black --check .
bash scripts/verify_offline.sh
```

`pyproject.toml`은 포맷터와 린터의 줄 길이를 80자로 맞춥니다. `requirements-dev.txt`에 검증 도구 버전을 고정합니다. 설치된 모든 전이 의존성을 잠그는 lockfile은 아닙니다. CI·branch protection·리뷰 권한 설정을 자동 적용하지 않습니다.

## 이번에 적용한 항목

| 규칙 | 적용 내용 |
| --- | --- |
| PY-02 | Black 80자·Python 3.12 설정과 4칸 들여쓰기 |
| PY-09 | 주요 클래스·함수·ROS 콜백·시험에 영어 요약 docstring 추가. 단위·None·반환·중요 예외 설명 |
| 주석 언어 | 좌표 변환·상태 전이·프레임 중복 방지 등 의도를 한글 학습 주석으로 추가 |
| GIT-03 | 문서/docstring 변경과 서식 변경을 별도 커밋으로 분리 |

기존 docstring은 유지하면서 부족한 함수 설명을 추가합니다. 문법·AST 비교·기존 동작 시험으로 제어 로직이 바뀌지 않았는지 확인합니다.

## 추가 정비가 필요한 항목

| 규칙 | 기존 코드에서 남은 정비 |
| --- | --- |
| PY-01/11 | x/y/H/K/D 같은 수학 표기와 기존 데이터 필드의 명명·단위 계약 검토. 공개 필드 변경은 소비자 영향을 먼저 확인 |
| PY-03 | 상대 import를 절대 import로 바꾸고 표준/외부/프로젝트 그룹 및 모듈 import 기준 정비 |
| PY-04 | ROS 콜백·초기화·CLI 반환형과 ndarray/JSON 경계 타입 보강. mypy 범위와 서드파티 stub 정책 확정 |
| PY-05 | 새 브랜치에서 control.py의 상태 불변식 assert를 명시적 실패 처리로 바꾸고 잘못된 시각·중복 프레임 시험 추가. 다른 입력 경계의 검증도 계속 검토 |
| PY-06 | on_camera의 넓은 Exception 포착을 구체 예외로 분리. KeyboardInterrupt 정상 종료와 예기치 않은 실패를 구분 |
| PY-08 | 새 브랜치에서 카메라 생성자 중간 실패와 반복 종료의 자원 정리 보강. 모의 수명 계약 시험은 실제 카메라·ROS 검증과 구분 |
| PY-10 | ROS rclpy logger는 현재 유지. CLI 결과 출력과 운영 진단 로그의 역할 분리 |
| 검사 | pylint와 mypy를 설치·실행했다고 주장하지 않음. 후속 정비에서 범위를 확정하고 경고를 실제로 해결 |

긴 문자열을 Black이 자동 분할하지 못한 경우 줄 길이 예외로 남을 수 있습니다. 사용자 메시지 문자열은 실행 의미를 보존하며, 아래 서식 예외를 리뷰해야 합니다.

현재 Black 실행 후 남은 긴 기존 메시지·docstring·f-string은 의미와 출력을 보존하기 위한 서식 예외입니다. 정규 린트 정비 때 문구와 줄 분할을 검토합니다.

- `pinky_line_alignment/offline_demo.py:50` (91자)
- `pinky_line_alignment/alignment_node.py:1` (88자)
- `pinky_line_alignment/alignment_node.py:45` (86자)
- `pinky_line_alignment/alignment_node.py:58` (95자)
- `pinky_line_alignment/alignment_node.py:107` (83자)
- `pinky_line_alignment/alignment_node.py:117` (82자)
- `pinky_line_alignment/alignment_node.py:190` (82자)

## 설계 경계

작은 현재 프로젝트에 DDD 폴더를 강제하지 않습니다. `control.py`가 상태를 소유하고 ROS 노드는 입출력을 연결합니다. 그러나 control은 vision의 LineEstimate를 import하고 vision은 OpenCV를 import하므로, 엄격한 domain 독립성은 아직 충족하지 않습니다.

순수 데이터 계약 분리·의존성 주입·카메라 자원 수명 보강은 별도 리팩터링과 시험으로 진행합니다. 설명과 서식 정리를 이유로 상태 전이·토픽·구동 허용 조건을 바꾸지 않습니다.
