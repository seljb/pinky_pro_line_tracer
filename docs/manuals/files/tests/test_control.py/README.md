# `tests/test_control.py` 사용설명서

**시작·정지·센서 손실·인계 거부 등 상태 전이를 검사합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

시작·정지·센서 손실·인계 거부 등 상태 전이를 검사합니다. 원본은 [tests/test_control.py](../../../../../tests/test_control.py)입니다.

주요 진입점: `line`, `test_does_not_start_without_sensors`, `test_stale_sensor_stops_immediately`, `test_plan_and_motion_commands_with_explicit_handoff`, `test_operator_stop`, `test_ready_expires_and_cannot_handoff_after_lost_sensors`, `test_handoff_checks_current_alignment_not_only_ready_flag`, `test_ready_timeout_even_with_live_sensors`, `test_invalid_odometry_cannot_drive`, `test_invalid_line_estimate_cannot_handoff`.

## 사용 순서

python -m pytest -q tests/test_control.py를 실행하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

9개 시험이 오래된 센서, READY 만료, NaN/Inf와 인계를 검사합니다.

## 확인 방법

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

장난감 운동학과 가짜 관측값을 사용합니다. 실제 ROS 전송·mux 동작은 검사하지 않습니다.

[전체 파일 목차](../../../README.md)
