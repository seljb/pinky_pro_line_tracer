# `tests/test_calibration.py` 사용설명서

**가상 대응점으로 보정 계산과 검증 플래그를 확인합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

가상 대응점으로 보정 계산과 검증 플래그를 확인합니다. 원본은 [tests/test_calibration.py](../../../../../tests/test_calibration.py)입니다.

주요 진입점: `test_homography_holdout`.

## 사용 순서

python -m pytest -q tests/test_calibration.py를 실행하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

1개 시험이 호모그래피 계산과 RMSE를 검사합니다.

## 확인 방법

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

합성 점 일부를 보정과 검증에 재사용하는 계산 시험입니다. 독립 실물 보정 절차를 검증한 것은 아닙니다.

[전체 파일 목차](../../../README.md)
