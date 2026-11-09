# `pinky_line_alignment/resource_paths.py` 사용설명서

**소스와 설치 환경에서 패키지 보정 JSON의 실제 위치를 찾습니다.**

## 목차

1. [역할](#역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [완료 기준과 주의사항](#완료-기준과-주의사항)

## 역할

소스와 설치 환경에서 패키지 보정 JSON의 실제 위치를 찾습니다. [원본 파일](../../../../../pinky_line_alignment/resource_paths.py)을 확인하세요.

## 사용 순서

calibration_file("synthetic_calibration.json")으로 기존 파일 경로를 구합니다.

명령은 저장소 루트의 오프라인 가상환경에서 실행합니다. ROS 노드는 별도의 시스템 Jazzy 환경을 사용합니다.

## 입력과 출력

checkout config, 설치 distribution share, ROS share 경로를 확인합니다.

## 완료 기준과 주의사항

파일 이름만 받으며 측정값을 다운로드하거나 보정을 임의 생성하지 않습니다.

[전체 파일 목차](../../../README.md)
