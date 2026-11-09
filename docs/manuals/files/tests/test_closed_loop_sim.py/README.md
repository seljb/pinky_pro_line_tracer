# `tests/test_closed_loop_sim.py` 사용설명서

**검출기와 제어기의 합성 폐루프 성공 조건을 검사합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

검출기와 제어기의 합성 폐루프 성공 조건을 검사합니다. 원본은 [tests/test_closed_loop_sim.py](../../../../../tests/test_closed_loop_sim.py)입니다.

주요 진입점: `test_detector_and_controller_closed_loop_synthetic`.

## 사용 순서

python -m pytest -q tests/test_closed_loop_sim.py를 실행하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

좌·우 시작 2건에서 READY, 횡오차 15mm 미만, 각도 6도 미만, 시간 50초 미만을 확인합니다.

## 확인 방법

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

허용치는 현재 시험 기준이며 검증된 실물 성능이 아닙니다.

[전체 파일 목차](../../../README.md)
