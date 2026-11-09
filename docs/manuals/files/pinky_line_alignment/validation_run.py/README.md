# `pinky_line_alignment/validation_run.py` 사용설명서

**합성 영상부터 정렬 명령과 이상적인 이동까지 폐루프를 검증합니다.**

## 목차

1. [역할](#역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [완료 기준과 주의사항](#완료-기준과-주의사항)

## 역할

합성 영상부터 정렬 명령과 이상적인 이동까지 폐루프를 검증합니다. [원본 파일](../../../../../pinky_line_alignment/validation_run.py)을 확인하세요.

## 사용 순서

python -m pinky_line_alignment.validation_run --output-dir /tmp/pinky-command-new

명령은 저장소 루트의 오프라인 가상환경에서 실행합니다. ROS 노드는 별도의 시스템 Jazzy 환경을 사용합니다.

## 입력과 출력

좌·우 합류·카메라 중단·운영자 정지의 CSV 4개와 summary.json을 생성합니다.

## 완료 기준과 주의사항

필수 조건 실패 시 비정상 종료합니다. 실물 카메라·모터·전체 선 추종·코너 주행을 검증하지 않습니다.

[전체 파일 목차](../../../README.md)
