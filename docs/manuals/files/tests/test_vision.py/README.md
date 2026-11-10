# `tests/test_vision.py` 사용설명서

**합성 선 검출과 영상 크기·무검출 처리를 검사합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

합성 선 검출과 영상 크기·무검출 처리를 검사합니다. 원본은 [tests/test_vision.py](../../../../../tests/test_vision.py)입니다.

주요 진입점: `test_synthetic_line_location_and_heading`, `test_no_line_returns_none`, `test_image_size_must_match_calibration`, `test_synthetic_calibration_never_marked_real`.

## 사용 순서

python -m pytest -q tests/test_vision.py를 실행하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

4개 시험이 위치/각도, 흰 영상, 크기 불일치, 합성 보정 구분을 확인합니다.

## 확인 방법

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

실제 조명·그림자·노출·카메라 성능의 증거가 아닙니다.

[전체 파일 목차](../../../README.md)
