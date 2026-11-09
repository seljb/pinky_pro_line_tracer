# `config/synthetic_calibration.json` 사용설명서

**오프라인 시험 전용 가상 카메라 변환을 제공합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

오프라인 시험 전용 가상 카메라 변환을 제공합니다. 원본은 [config/synthetic_calibration.json](../../../../../config/synthetic_calibration.json)입니다.

## 사용 순서

offline_demo와 closed_loop_sim에서 그대로 사용하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

640×480, calibration_type=synthetic, validated=false입니다.

## 확인 방법

JSON을 읽을 수 있는지 확인한 뒤 보정 종류·해상도·단위를 검토합니다. JSON 문법 통과는 실물 보정 성공을 뜻하지 않습니다. 자세한 실행은 [루트 안내](../../../../../README.md)를 따르세요.

## 오류와 주의사항

ground_rmse_m=0은 가상 모델 값이며 실측 정확도가 아닙니다. 실물 구동에 사용하지 마세요.

[전체 파일 목차](../../../README.md)
