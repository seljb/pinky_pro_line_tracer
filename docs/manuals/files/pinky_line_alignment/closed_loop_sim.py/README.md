# `pinky_line_alignment/closed_loop_sim.py` 사용설명서

**합성 카메라와 이상적인 오도메트리로 정렬 루프를 시험합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

합성 카메라와 이상적인 오도메트리로 정렬 루프를 시험합니다. 원본은 [pinky_line_alignment/closed_loop_sim.py](../../../../../pinky_line_alignment/closed_loop_sim.py)입니다.

주요 진입점: `SimResult`, `render_tape`, `simulate`, `main`.

## 사용 순서

python -m pinky_line_alignment.closed_loop_sim을 실행하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

좌·우 0.08m 출발 결과를 SimResult로 출력합니다. 성공 여부를 자동 검사하려면 pytest를 실행하세요.

## 확인 방법

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

CLI는 결과를 출력하며 실패 상태 자체로 비정상 종료하지 않습니다. 슬립·장애물·지연은 모델링하지 않습니다.

[전체 파일 목차](../../../README.md)
