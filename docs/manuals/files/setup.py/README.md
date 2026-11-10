# `setup.py` 사용설명서

**ROS Python 패키지와 실행 진입점을 등록합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

ROS Python 패키지와 실행 진입점을 등록합니다. 원본은 [setup.py](../../../../setup.py)입니다.

## 사용 순서

ROS workspace에서 colcon build로 사용하세요. 직접 실행해 로봇을 구동하는 파일이 아닙니다.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

camera_node, alignment_node, calibrate, offline_demo, closed_loop_sim 진입점을 등록합니다.

## 확인 방법

파일을 읽고 위 목적·경로와 일치하는지 확인합니다. 실행을 요구하지 않는 문서·설정 파일은 단독 실행하지 않습니다.

## 오류와 주의사항

pip 의존성만으로 ROS 2가 설치되지는 않습니다. OpenCV는 별도 필요합니다.

[전체 파일 목차](../../README.md)
