# `pinky_line_alignment/control.py` 사용설명서

**최신 센서 관측으로 정렬 상태와 속도 요청을 계산합니다.**

## 목차

1. [파일 역할](#파일-역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [확인 방법](#확인-방법)
5. [오류와 주의사항](#오류와-주의사항)

## 파일 역할

최신 센서 관측으로 정렬 상태와 속도 요청을 계산합니다. 원본은 [pinky_line_alignment/control.py](../../../../../pinky_line_alignment/control.py)입니다.

주요 진입점: `wrap`, `clamp`, `Pose`, `State`, `Command`, `AlignmentController`.

## 사용 순서

update_pose/update_line 후 start를 호출하고 단조 시각으로 tick을 반복하세요.

명령은 별도 표시가 없으면 저장소 루트 `pinky_pro_line_tracer/`에서 실행합니다. Python 명령은 의존성을 설치한 환경에서 실행합니다. ROS 명령은 Jazzy 환경을 source한 터미널에서 실행합니다.

## 입력과 출력

Pose는 m/rad, now는 monotonic 초입니다. Command는 m/s와 rad/s이며 실제 모터 쓰기는 하지 않습니다.

## 확인 방법

```python
import time
from pinky_line_alignment.control import AlignmentController, Pose

controller = AlignmentController()
now_s = time.monotonic()
controller.update_pose(Pose(0.0, 0.0, 0.0), now_s)
# 선 관측이 없으므로 시작은 거절되고 속도 요청은 0이다.
print(controller.start(now_s))
print(controller.tick(now_s))
```
실제 연결에서는 검출 결과와 odom을 계속 갱신합니다. 예시 관측을 실물 제어에 주입하지 않습니다.

오프라인 확인은 `bash scripts/verify_offline.sh`로 실행합니다. 기존 기준은 16개 시험 통과와 좌·우 합성 시나리오 READY 도달입니다. ROS 노드와 실제 장비 연동은 이 검사에 포함되지 않습니다.

## 오류와 주의사항

READY는 임시 정지 상태입니다. handoff_ack는 현재 정렬을 재확인하며 실제 mux 전환은 하지 않습니다.

[전체 파일 목차](../../../README.md)
