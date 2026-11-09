# `scripts/verify_offline.sh` 사용설명서

**로봇 없이 문법·테스트·합성 검출·정렬을 차례로 검증합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

로봇 없이 문법·테스트·합성 검출·정렬을 차례로 검증합니다. 원본은 [scripts/verify_offline.sh](../../../../../scripts/verify_offline.sh)입니다.

## 사용 순서

가상환경 활성화 후 bash scripts/verify_offline.sh를 실행하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

compileall, pytest, offline_demo, closed_loop_sim 순서이며 오류가 나면 중단합니다.

## 확인 방법

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

python3가 의존성을 설치한 인터프리터인지 확인하세요. ROS/실물은 검증하지 않습니다.

[전체 파일 목차](../../../README.md)
